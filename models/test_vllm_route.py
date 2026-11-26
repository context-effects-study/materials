"""test_vllm_route.py: tests the route of the open models against a made-up vLLM server on this computer.

It checks that each request names the model by its Hugging Face repository and carries the parameters of its
reasoning setting, that every call records the revision the server loaded and its sampling defaults, that calls
sent several at a time give the same records as calls sent one at a time, and that no call is made without a
server address.

Run: python models/test_vllm_route.py      (exit 0 when every check passes)
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run  # noqa: E402

PROMPT = "Choose a backpack from these options:\n  A. 30 liters capacity, $29.99\n  B. 40 liters capacity, $39.99\n" + run.RESP


class FakeVLLM(BaseHTTPRequestHandler):
    bodies = []
    reply = "B"
    thought = None        # vLLM with a reasoning parser returns the thinking in message.reasoning_content
    fail_next = 0         # this many of the next calls answer with a server error

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeVLLM.bodies.append(dict(body, _path=self.path))
        if FakeVLLM.fail_next > 0:
            FakeVLLM.fail_next -= 1
            self.send_response(400)       # a client error: the SDK does not retry it
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        msg = {"role": "assistant", "content": FakeVLLM.reply}
        if FakeVLLM.thought:
            msg["reasoning_content"] = FakeVLLM.thought
        out = {"id": "chatcmpl-1", "object": "chat.completion", "created": 0, "model": body["model"],
               "choices": [{"index": 0, "finish_reason": "stop", "message": msg}],
               "usage": {"prompt_tokens": 50, "completion_tokens": 1, "total_tokens": 51}}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    fails, n = [], 0

    def need(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            fails.append(msg)

    srv = HTTPServer(("localhost", 0), FakeVLLM)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    tmp = tempfile.mkdtemp(prefix="vllm_route_test_")
    saved = {k: os.environ.get(k) for k in ("VLLM_BASE_URL", "VLLM_SERVED_INFO", "VLLM_API_KEY", "HF_HOME")}
    try:
        os.environ["VLLM_BASE_URL"] = f"http://localhost:{srv.server_port}/v1"
        os.environ.pop("VLLM_API_KEY", None)
        info = os.path.join(tmp, "served.json")
        os.environ["VLLM_SERVED_INFO"] = info
        # 1 and 2: one model of each kind, every arm and setting it runs
        for k in ("qwen35-27b", "gptoss-120b", "qwen25-7b", "deepseek-r1", "glm53-flash", "gemma4-31b"):
            reg = run.MODEL_REGISTRY[k]
            json.dump({"revision": reg["hf_revision"][1], "vllm_version": "0.34.0",
                       "sampling_defaults": {"temperature": 0.7, "top_p": 0.8}}, open(info, "w"))
            for arm, s in run.arm_calls(k):
                if arm in ("sequential", "recognition", "persona"):
                    continue
                FakeVLLM.bodies.clear()
                res = run.call_model(run.Clients(), dict(model_key=k, prompt=PROMPT, arm=arm, setting=s))
                tag = f"{k}/{arm}/{s}"
                need(res["error"] is None, f"{tag}: call failed: {res['error']}")
                if not FakeVLLM.bodies:
                    continue
                b = FakeVLLM.bodies[-1]
                params = reg["settings"][s]
                need(b["_path"] == "/v1/chat/completions", f"{tag}: request went to {b['_path']}")
                need(b["model"] == reg["hf_repo"], f"{tag}: model sent {b['model']}, registered {reg['hf_repo']}")
                sent = {x: b[x] for x in ("chat_template_kwargs", "reasoning_effort") if x in b}
                need(sent == params, f"{tag}: sent {sent}, registered {params}")
                need(b.get("max_tokens") == reg["max_tokens"][s], f"{tag}: ceiling {b.get('max_tokens')}")
                want_t = run.ARM_TEMPERATURE.get(arm)
                need(b.get("temperature") == want_t, f"{tag}: temperature {b.get('temperature')}, want {want_t}")
                sv = res["served"] or {}
                need(sv.get("hf_repo") == reg["hf_repo"] and sv.get("hf_revision") == reg["hf_revision"][1]
                     and sv.get("revision_started") == reg["hf_revision"][1] and sv.get("revision_matches") is True
                     and sv.get("sampling_defaults") == {"temperature": 0.7, "top_p": 0.8}
                     and sv.get("vllm_version") == "0.34.0" and sv.get("model_echoed") == reg["hf_repo"],
                     f"{tag}: the served record is incomplete: {sv}")
                need(res["cost_usd"] == 0 and res["raw_response"] == "B", f"{tag}: cost or answer wrong")
        # planted fault for check 1: a request builder that drops the thinking switch must be caught by the same
        # comparison of the body the server received with the registry
        orig = run.build_request
        def dropped(*a, **kw):
            q = orig(*a, **kw)
            q["kwargs"] = {x: v for x, v in q["kwargs"].items() if x != "extra_body"}
            return q
        run.build_request = dropped
        try:
            FakeVLLM.bodies.clear()
            run.call_model(run.Clients(), dict(model_key="qwen35-27b", prompt=PROMPT, arm="primary"))
            b = FakeVLLM.bodies[-1]
            sent = {x: b[x] for x in ("chat_template_kwargs", "reasoning_effort") if x in b}
            need(sent != run.MODEL_REGISTRY["qwen35-27b"]["settings"]["OFF"],
                 "planted fault NOT caught: a request without the thinking switch")
        finally:
            run.build_request = orig
        # 3: the loop writes the served record on every row, and a wrong revision is flagged
        k = "qwen35-27b"
        json.dump({"revision": "0" * 40, "vllm_version": "0.34.0", "sampling_defaults": {}}, open(info, "w"))
        lp = os.path.join(tmp, "log.jsonl")
        with contextlib.redirect_stdout(io.StringIO()):
            run.run_collection(True, 4, 1.0, [k], "VLLMTEST", clients=run.Clients(), log_path=lp)
        rows = [json.loads(x) for x in open(lp, encoding="utf-8")]
        need(len(rows) == 4 and all(r["provider"] == "vllm" and r["served"]["revision_matches"] is False
                                    and r["setting"] == "OFF" for r in rows),
             "rows do not carry the served record with the revision mismatch flagged")
        # 5: calls in flight at once, spread over one server per node (VLLM_BASE_URLS): the same rows in the same plan
        #    order as one call at a time, every node used, max_calls kept; refused on a closed route and for sessions
        srv2 = HTTPServer(("localhost", 0), FakeVLLM)
        threading.Thread(target=srv2.serve_forever, daemon=True).start()
        try:
            json.dump({"revision": run.MODEL_REGISTRY[k]["hf_revision"][1], "vllm_version": "0.34.0",
                       "sampling_defaults": {}}, open(info, "w"))
            ls, lc = os.path.join(tmp, "one.jsonl"), os.path.join(tmp, "many.jsonl")
            with contextlib.redirect_stdout(io.StringIO()):
                run.run_collection(True, 60, 1.0, [k], "VLLMTEST", clients=run.Clients(), log_path=ls)
                FakeVLLM.bodies.clear()
                os.environ["VLLM_BASE_URLS"] = (f"http://localhost:{srv.server_port}/v1,"
                                                f"http://localhost:{srv2.server_port}/v1")
                ports = []
                orig_handle = FakeVLLM.do_POST
                def counting(self):
                    ports.append(self.server.server_port)
                    return orig_handle(self)
                FakeVLLM.do_POST = counting
                run.run_collection(True, 60, 1.0, [k], "VLLMTEST", clients=run.Clients(), log_path=lc, concurrency=8)
                FakeVLLM.do_POST = orig_handle
            one = [json.loads(x)["record_id"] for x in open(ls, encoding="utf-8")]
            many = [json.loads(x)["record_id"] for x in open(lc, encoding="utf-8")]
            need(len(one) == 60 and many == one, f"concurrent rows differ from one-at-a-time rows ({len(many)}, {len(one)})")
            need(len(FakeVLLM.bodies) == 60, f"{len(FakeVLLM.bodies)} calls made for max_calls 60")
            need(set(ports) == {srv.server_port, srv2.server_port}, "the calls were not spread over both nodes")
            for bad_models, bad_arm in ((["gpt-6-luna"], "primary"), ([k], "sequential")):
                try:
                    run.run_collection(True, 2, 1.0, bad_models, "VLLMTEST", clients=run.Clients(), arm=bad_arm,
                                       log_path=os.path.join(tmp, "bad.jsonl"), concurrency=4)
                    need(False, f"concurrent calls accepted for {bad_models} / {bad_arm}")
                except ValueError:
                    need(True, "")
        finally:
            srv2.shutdown()
            os.environ.pop("VLLM_BASE_URLS", None)
        # 9: a reply that only the fallback pattern reads is unreadable for a
        #   model that reasons with no reasoning parser (Gemma 4 31B), and still read for a model with one (Qwen3.5 27B)
        FakeVLLM.reply = "<think>I need to choose a backpack. Option C is cheaper.</think>\nC"
        try:
            for key, want_excluded in (("gemma4-31b", True), ("qwen35-27b", False)):
                lp9 = os.path.join(tmp, f"leak-{key}.jsonl")
                with contextlib.redirect_stdout(io.StringIO()):
                    run.run_collection(True, 3, 1.0, [key], "VLLMTEST", clients=run.Clients(), log_path=lp9)
                rows9 = [json.loads(x) for x in open(lp9, encoding="utf-8")]
                if want_excluded:
                    need(len(rows9) == 3 and all(r["exclusion_flag"] and r["exclusion_reason"] == "unparseable"
                                                 and r["parse_method"] == "fallback_refused" for r in rows9),
                         f"{key}: a fallback read of a leaked reasoning reply was accepted: "
                         f"{[(r['parse_method'], r['exclusion_reason']) for r in rows9]}")
                else:
                    need(len(rows9) == 3 and all(r["parse_method"] == "fallback_regex" for r in rows9),
                         f"{key}: a model with a reasoning parser lost its fallback read")
        finally:
            FakeVLLM.reply = "B"
        # 8: calls in flight with a call cap and one failed call stop cleanly at the cap
        lm = os.path.join(tmp, "capped.jsonl")
        FakeVLLM.fail_next = 1
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                st = run.run_collection(True, 3, 1.0, ["qwen35-27b"], "VLLMTEST", clients=run.Clients(), log_path=lm,
                                        concurrency=4)
            need(st["written"] == 2 and st["errors"] == 1, f"capped concurrent run: {st}")
        except RuntimeError as e:
            need(False, f"a capped concurrent run with a failed call crashed: {e}")
        finally:
            FakeVLLM.fail_next = 0
        # 6: an OFF call whose reply comes back with thinking (vLLM's reasoning_content, no token count) is flagged;
        #    the same reply on a model with no reasoning mode, or with no thinking, is not
        FakeVLLM.thought = "Let me weigh the options."
        r_on = run.call_model(run.Clients(), dict(model_key="qwen35-27b", prompt=PROMPT, arm="primary"))
        r_none = run.call_model(run.Clients(), dict(model_key="qwen25-7b", prompt=PROMPT, arm="primary"))
        FakeVLLM.thought = None
        r_off = run.call_model(run.Clients(), dict(model_key="qwen35-27b", prompt=PROMPT, arm="primary"))
        need(r_on["reasoning_effective"].get("off_request_reasoned") is True
             and r_on["reasoning_effective"].get("reasoning_chars") == 25,
             "an OFF reply with reasoning_content was not flagged")
        need(not r_none["reasoning_effective"].get("off_request_reasoned")
             and not r_off["reasoning_effective"].get("off_request_reasoned"), "a reply was flagged wrongly")
        # 4: no VLLM_BASE_URL, no call
        os.environ.pop("VLLM_BASE_URL")
        res = run.call_model(run.Clients(), dict(model_key=k, prompt=PROMPT, arm="primary"))
        need(res["error"] is not None and "VLLM_BASE_URL" in res["error"], "the route ran without VLLM_BASE_URL")
        need(run.preflight([k]) and "VLLM_BASE_URL" in run.preflight([k])[0], "preflight passed without VLLM_BASE_URL")
    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)
        for x, v in saved.items():
            if v is None:
                os.environ.pop(x, None)
            else:
                os.environ[x] = v
    if fails:
        print(f"TEST_VLLM_ROUTE FAIL: {len(fails)} of {n} checks")
        for f in fails:
            print("  -", f)
        return 1
    print(f"TEST_VLLM_ROUTE PASS: {n} checks against a fake vLLM server on this computer; no model, no charge.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
