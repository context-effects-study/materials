"""test_batch.py: tests the batch mode end to end against made-up batch services, with no network.

The made-up services answer from batch_fixtures.json, whose shapes follow each service's documentation. The test
checks that every request is the one run.py sends live, that nothing is sent twice, that answers are written in
the order of the plan at half the price, and that failed answers are sent again.

Run: python models/test_batch.py      (exit 0 when every check passes)
"""
import contextlib
import copy
import io
import json
import os
import shutil
import sys
import tempfile
from http.server import BaseHTTPRequestHandler
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run  # noqa: E402
import batch  # noqa: E402

FIX = json.load(open(os.path.join(HERE, "batch_fixtures.json"), encoding="utf-8"))
N = 40


def filled(name, cid, model, answer="B"):
    s = json.dumps(FIX[name]).replace("CUSTOM_ID", cid).replace("MODEL", model).replace("ANSWER", answer)
    return json.loads(s)


def fails(i):
    return i % 7 == 3          # every seventh request fails in the fake


class Services:
    """All five fakes share one record of the requests they received and whether their batches have ended."""
    def __init__(self):
        self.received, self.done, self.files, self.batches = {}, False, {}, {}

    # OpenAI SDK surface (files, batches)
    def client(self, route):
        svc = self
        class Files:
            def create(self, file, purpose):
                fid = f"file-{len(svc.files)}"
                svc.files[fid] = file[1].decode("utf-8")
                return NS(id=fid)
            def content(self, fid):
                return NS(text=svc.files[fid])
        class Batches:
            def create(self, input_file_id, endpoint, completion_window):
                bid = f"batch_{len(svc.batches)}"
                lines = [json.loads(x) for x in svc.files[input_file_id].splitlines() if x.strip()]
                svc.batches[bid] = [(d["custom_id"], d["body"]) for d in lines]
                svc.received[bid] = lines
                return NS(id=bid)
            def retrieve(self, bid):
                if not svc.done:
                    return NS(status="in_progress", output_file_id=None, error_file_id=None)
                ok = [filled("openai_ok", c, b["model"]) for i, (c, b) in enumerate(svc.batches[bid]) if not fails(i)]
                bad = [filled("openai_error", c, b["model"]) for i, (c, b) in enumerate(svc.batches[bid]) if fails(i)]
                svc.files["out-" + bid] = "\n".join(json.dumps(x) for x in ok)
                svc.files["err-" + bid] = "\n".join(json.dumps(x) for x in bad)
                return NS(status="completed", output_file_id="out-" + bid, error_file_id="err-" + bid)
        class MsgBatches:
            def create(self, requests):
                bid = f"msgbatch_{len(svc.batches)}"
                svc.batches[bid] = [(r["custom_id"], r["params"]) for r in requests]
                svc.received[bid] = requests
                return NS(id=bid)
            def retrieve(self, bid):
                return NS(processing_status="ended" if svc.done else "in_progress")
            def results(self, bid):
                out = []
                for i, (c, p) in enumerate(svc.batches[bid]):
                    d = filled("anthropic_error" if fails(i) else "anthropic_ok", c, p["model"])
                    res = d["result"]
                    out.append(NS(custom_id=c, result=NS(type=res["type"], message=res.get("message"),
                                                         error=res.get("error"))))
                return out
        return NS(files=Files(), batches=Batches(), messages=NS(batches=MsgBatches()))

    # HTTP surface (Mistral and xAI)
    def transport(self, method, path, json=None, files=None, data=None):
        if path == "/files" and method == "POST":
            fid = f"mfile-{len(self.files)}"
            self.files[fid] = files["file"][1].decode("utf-8")
            return {"id": fid}
        if path == "/batch/jobs" and method == "POST":
            bid = f"mjob_{len(self.batches)}"
            lines = [__import__("json").loads(x) for x in self.files[json["input_files"][0]].splitlines() if x.strip()]
            self.batches[bid] = [(d["custom_id"], dict(d["body"], model=json["model"])) for d in lines]
            self.received[bid] = dict(job=json, lines=lines)
            return {"id": bid}
        if path.startswith("/batch/jobs/"):
            bid = path.rsplit("/", 1)[1]
            return {"id": bid, "status": "SUCCESS" if self.done else "RUNNING",
                    "output_file": ("mout-" + bid) if self.done else None, "error_file": None}
        if path.startswith("/files/mout-"):
            bid = path.split("mout-")[1].split("/")[0]
            return "\n".join(__import__("json").dumps(filled("mistral_error" if fails(i) else "mistral_ok", c, b["model"]))
                             for i, (c, b) in enumerate(self.batches[bid]))
        if path == "/batches" and method == "POST":
            bid = f"xbatch_{len(self.batches)}"
            self.batches[bid] = []
            self.received[bid] = []
            return {"batch_id": bid}
        if path.endswith("/requests") and method == "POST":
            bid = path.split("/")[2]
            for r in json["batch_requests"]:
                self.batches[bid].append((r["batch_request_id"], r["batch_request"]["chat_get_completion"]))
                self.received[bid].append(r)
            return {}
        if "/results" in path:
            bid = path.split("/")[2]
            return {"results": [filled("xai_error" if fails(i) else "xai_ok", c, b["model"])
                                for i, (c, b) in enumerate(self.batches[bid])], "pagination_token": None}
        if path.startswith("/batches/"):
            return {"state": {"num_pending": 0 if self.done else N}}
        raise AssertionError(f"unexpected {method} {path}")


def sent_bodies(route, received):
    """{custom id: body} from what a fake received, whatever the service's own wrapping."""
    out = {}
    for v in received.values():
        if route in ("openai", "google"):
            out.update({d["custom_id"]: d["body"] for d in v})
        elif route == "anthropic":
            out.update({d["custom_id"]: d["params"] for d in v})
        elif route == "mistral":
            out.update({d["custom_id"]: dict(d["body"], model=v["job"]["model"]) for d in v["lines"]})
        else:
            out.update({d["batch_request_id"]: d["batch_request"]["chat_get_completion"] for d in v})
    return out


class SDKCapture(BaseHTTPRequestHandler):
    """A fake API server that records the exact JSON body the real OpenAI or Anthropic SDK sends, and answers."""
    bodies = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SDKCapture.bodies.append(body)
        if self.path.endswith("/messages"):
            out = {"id": "msg_1", "type": "message", "role": "assistant", "model": body["model"],
                   "content": [{"type": "text", "text": "B"}], "stop_reason": "end_turn", "stop_sequence": None,
                   "usage": {"input_tokens": 10, "output_tokens": 1}}
        else:
            out = {"id": "c", "object": "chat.completion", "created": 0, "model": body["model"],
                   "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "B"}}],
                   "usage": {"prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11}}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def sdk_bodies(specs):
    """The JSON each spec's live call actually sends, captured from the real SDKs at a fake server on this computer."""
    import threading
    from http.server import HTTPServer
    srv = HTTPServer(("localhost", 0), SDKCapture)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    saved = dict(run.ROUTE_BASE)
    try:
        for r in ("openai", "google", "xai", "mistral"):
            run.ROUTE_BASE[r] = f"http://localhost:{srv.server_port}/v1"
        run.ROUTE_BASE["anthropic"] = f"http://localhost:{srv.server_port}"
        keys = {k: os.environ.get(k) for ks in run.ROUTE_KEYS.values() for k in ks}
        for ks in run.ROUTE_KEYS.values():
            os.environ.setdefault(ks[0], "test-not-a-key")
        out = []
        for s in specs:
            SDKCapture.bodies.clear()
            res = run.call_model(run.Clients(), s)
            out.append(SDKCapture.bodies[-1] if SDKCapture.bodies else {"error": res["error"]})
        return out
    finally:
        run.ROUTE_BASE.update(saved)
        for k, v in keys.items():
            if v is None:
                os.environ.pop(k, None)
        srv.shutdown()


def review_checks(need, tmp, stimuli, cats):
    import httpx
    # 6.3 (both reviewers): the batch body equals the JSON that the real SDK sends live, compared at the wire, on
    # arms where the request carries extra_body (Anthropic's output_config at a crossed setting) and a temperature
    picks = [("claude-haiku-5-5", "crossed", "HIGH"), ("claude-haiku-5-5", "primary", None),
             ("gpt-6-luna", "temp_0", None), ("gpt-6-luna", "crossed", "HIGH"), ("claude-haiku-5-5", "ladder", "MAX"),
             ("grok-4.7", "crossed", "DEFAULT")]
    specs = [next(run.iter_specs(stimuli, cats, [k], arm=a, setting=s)) for k, a, s in picks]
    wire = sdk_bodies(specs)
    for (k, a, s), spec, sent in zip(picks, specs, wire):
        body = batch.request_body(spec)[1]
        need(sent == body, f"{k}/{a}/{s}: the batch body differs from what the SDK sends live: {sent} vs {body}")
    # the planted fault that this comparison exists to catch: a request body that drops the setting's parameters
    orig = batch.request_body

    def dropped(spec):
        req, body = orig(spec)
        for x in ("output_config", "reasoning_effort", "thinking", "temperature"):
            body.pop(x, None)
        return req, body
    batch.request_body = dropped
    try:
        caught = any(sent != batch.request_body(spec)[1] for spec, sent in zip(specs, wire))
    finally:
        batch.request_body = orig
    need(caught, "planted fault NOT caught: a batch body without the setting's parameters")
    # a crossed arm and a temperature arm go through submit and collect, at half the price, with their setting
    svc = Services()
    out = os.path.join(tmp, "arms")
    with contextlib.redirect_stdout(io.StringIO()):
        for k, a, s in (("claude-haiku-5-5", "crossed", "HIGH"), ("gpt-6-luna", "temp_0", None)):
            batch.submit([k], a, s, "BATCHTEST", out, 5.0, clients=svc, transport=svc.transport, max_calls=6)
        svc.done = True
        globals()["fails"] = lambda i: False
        batch.collect("BATCHTEST", out, clients=svc, transport=svc.transport)
        globals()["fails"] = lambda i: i % 7 == 3
    for k, a, s in (("claude-haiku-5-5", "crossed", "HIGH"), ("gpt-6-luna", "temp_0", None)):
        rows = [json.loads(x) for x in open(run.log_path_for(a, out, s), encoding="utf-8")]
        full = run._usd({"prompt_tokens": 100, "completion_tokens": 5}, run.MODEL_REGISTRY[k])
        need(len(rows) == 6 and all(r["arm"] == a and r["setting"] == run.setting_for(k, a, s)
                                    and abs(r["cost_usd"] - round(full * 0.5, 6)) < 1e-9 for r in rows),
             f"{k}/{a}: rows wrong after submit and collect")
    # the planted fault: answers billed at the full price must be caught by the same check
    orr = run.result_from_response
    run.result_from_response = lambda *x, **kw: orr(*x, **dict(kw, price_factor=1.0))
    try:
        svc2, out2 = Services(), os.path.join(tmp, "fullprice")
        with contextlib.redirect_stdout(io.StringIO()):
            batch.submit(["gpt-6-luna"], "temp_0", None, "BATCHTEST", out2, 5.0, clients=svc2, max_calls=2)
            svc2.done = True
            globals()["fails"] = lambda i: False
            batch.collect("BATCHTEST", out2, clients=svc2)
            globals()["fails"] = lambda i: i % 7 == 3
        rows = [json.loads(x) for x in open(run.log_path_for("temp_0", out2), encoding="utf-8")]
        full = run._usd({"prompt_tokens": 100, "completion_tokens": 5}, run.MODEL_REGISTRY["gpt-6-luna"])
        need(any(abs(r["cost_usd"] - round(full * 0.5, 6)) >= 1e-9 for r in rows),
             "planted fault NOT caught: batch answers billed at the full price")
    finally:
        run.result_from_response = orr
    # 4.1: Mistral's results come back as JSON Lines with a json content type, one or several lines
    for n_lines in (1, 3):
        line = json.dumps(filled("mistral_ok", "CID", "mistral-large-2610"))

        def fake_request(method, url, **kw):
            if url.endswith("/batch/jobs/job1"):
                return httpx.Response(200, request=httpx.Request(method, url), json={"id": "job1", "status": "SUCCESS", "output_file": "out1",
                                                 "error_file": None})
            return httpx.Response(200, request=httpx.Request(method, url), text="\n".join(line.replace("CID", f"c{i}") for i in range(n_lines)) + "\n",
                                  headers={"content-type": "application/jsonl"})
        saved_req, saved_key = httpx.request, os.environ.get("MISTRAL_API_KEY")
        httpx.request = fake_request
        os.environ["MISTRAL_API_KEY"] = "test-not-a-key"
        try:
            got = batch.HTTPBatch("mistral").results("job1")
            need([c for c, ok, _ in got if ok] == [f"c{i}" for i in range(n_lines)],
                 f"Mistral results of {n_lines} line(s) with a jsonl content type were not read: {got}")
        except Exception as e:
            need(False, f"Mistral results of {n_lines} line(s) with a jsonl content type crashed: {type(e).__name__}: {e}")
        finally:
            httpx.request = saved_req
            if saved_key is None:
                os.environ.pop("MISTRAL_API_KEY", None)
    # 4.4: a missing key is a clear error, not a bare StopIteration
    saved_key = os.environ.pop("XAI_API_KEY", None)
    try:
        batch.HTTPBatch("xai")._http("GET", "/batches/x")
        need(False, "a call without its key did not stop")
    except RuntimeError:
        need(True, "")
    except StopIteration:
        need(False, "a missing key raised StopIteration")
    finally:
        if saved_key is not None:
            os.environ["XAI_API_KEY"] = saved_key
    # 4.2 and m3: the cost cap covers the whole submission
    w = [0.5 * run.worst_case_cost(k, "primary", len(next(run.iter_specs(stimuli, cats, [k], arm="primary"))["prompt"]), 0)
         for k in ("gpt-6.2-astra", "claude-fable-5-2")]
    svc3 = Services()
    try:
        batch.submit(["gpt-6.2-astra", "claude-fable-5-2"], "primary", None, "BATCHTEST", os.path.join(tmp, "cap2"),
                     max(w) * 1.01, clients=svc3, max_calls=1)
        need(False, "two models each under the cap, together over it, were submitted")
    except SystemExit:
        need(not svc3.received, "a model was submitted before the whole submission was checked against the cap")
    # 4.3: an arm or setting the model does not run is refused; a call that fails twice is not sent a third time; a
    # batch that ends as failed with no results counts its calls as failed and records why
    for args in ((["gpt-6.2-sol"], "crossed", "MAX"), (["claude-opus-5-5"], "temp_0", None)):
        try:
            batch.submit(args[0], args[1], args[2], "BATCHTEST", os.path.join(tmp, "elig"), 5.0, clients=svc3)
            need(False, f"{args}: an arm or setting the model does not run was submitted")
        except ValueError:
            need(True, "")
    svc4, out4 = Services(), os.path.join(tmp, "retry")
    globals()["fails"] = lambda i: True
    sent = []
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            for _ in range(3):
                svc4.done = False
                rep = batch.submit(["gpt-6-luna"], "primary", None, "BATCHTEST", out4, 5.0, clients=svc4, max_calls=3)
                sent.append(sum(n for _, _, n in rep))
                svc4.done = True
                batch.collect("BATCHTEST", out4, clients=svc4)
    finally:
        globals()["fails"] = lambda i: i % 7 == 3
    first3 = sent[0]
    need(sent[:2] == [3, 3] and sent[2] == 3 and first3 == 3, f"submissions per round {sent}")
    # the third round must send the NEXT calls, never the first three again
    st = batch.load_state(batch.state_path(out4, "BATCHTEST", "gpt-6-luna", "primary", None))
    ids = [b["record_ids"] for b in st["batches"]]
    need(ids[0] == ids[1] and not (set(ids[2]) & set(ids[0])),
         f"a call that failed twice was sent a third time: {[len(x) for x in ids]}")

    class FailedWhole:
        def __init__(self):
            self.svc = Services()

        def client(self, route):
            c = self.svc.client(route)
            c.batches.retrieve = lambda bid: NS(status="failed", output_file_id=None, error_file_id=None)
            return c
    fw, out5 = FailedWhole(), os.path.join(tmp, "whole")
    with contextlib.redirect_stdout(io.StringIO()):
        batch.submit(["gpt-6-luna"], "primary", None, "BATCHTEST", out5, 5.0, clients=fw, max_calls=2)
        batch.collect("BATCHTEST", out5, clients=fw)
    st = batch.load_state(batch.state_path(out5, "BATCHTEST", "gpt-6-luna", "primary", None))
    b = st["batches"][0]
    need(b["collected"] and b.get("failure") and b["failed_ids"] == b["record_ids"],
         f"a batch that failed as a whole was not recorded: {b}")


def main():
    fails_, n = [], 0

    def need(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            fails_.append(msg)

    d = json.load(open(run.STIM, encoding="utf-8"))
    stimuli, cats = d["stimuli"], d["categories"]
    tmp = tempfile.mkdtemp(prefix="batch_test_")
    try:
        for k in ("gpt-6-luna", "gemini-3.5-flash-lite", "claude-haiku-5-5", "mistral-large-4", "grok-4.7"):
            route = run.MODEL_REGISTRY[k]["route"]
            svc = Services()
            out = os.path.join(tmp, k)
            plan = list(run.iter_specs(stimuli, cats, [k], arm="primary"))
            rids = [run.spec_record_id("BATCHTEST", s) for s in plan]
            with contextlib.redirect_stdout(io.StringIO()):
                saved = batch.CHUNK_CALLS
                batch.CHUNK_CALLS = 15
                try:
                    rep = batch.submit([k], "primary", None, "BATCHTEST", out, 5.0, clients=svc,
                                       transport=svc.transport, max_calls=N)
                finally:
                    batch.CHUNK_CALLS = saved
                # 1. the requests are run.py's, under their record ids, in three batches of at most 15
                got = sent_bodies(route, svc.received)
                need([r[2] for r in rep] == [15, 15, 10], f"{k}: batches of {[r[2] for r in rep]}")
                need(list(got) == rids[:N], f"{k}: the custom ids are not the first {N} planned record ids")
                for s in plan[:N]:
                    rid = run.spec_record_id("BATCHTEST", s)
                    # the live request, built here from run.py alone (never from batch.py, so this check is not
                    # comparing batch.py with itself)
                    req = run.build_request(k, "primary", setting=s["setting"])
                    kw = dict(req["kwargs"])
                    live = {"model": req["model_id"], "messages": run.build_messages(s, route), **kw,
                            **kw.pop("extra_body", {})}
                    live.pop("extra_body", None)
                    need(got.get(rid) == live, f"{k}: request {rid} differs from the live request")
                    params = run.MODEL_REGISTRY[k]["settings"][s["setting"]]
                    need(all(got.get(rid, {}).get(x) == v for x, v in params.items()),
                         f"{k}: request {rid} lacks the setting's parameters {params}")
                # 2. nothing is sent twice while waiting: the next submit sends the next N planned calls
                first = set(got)
                saved = batch.CHUNK_CALLS
                batch.CHUNK_CALLS = 15
                try:
                    rep2 = batch.submit([k], "primary", None, "BATCHTEST", out, 5.0, clients=svc,
                                        transport=svc.transport, max_calls=N)
                finally:
                    batch.CHUNK_CALLS = saved
                second = sent_bodies(route, {b: svc.received[b] for b in [r[1] for r in rep2]})
                need(list(second) == rids[N:2 * N] and not (first & set(second)),
                     f"{k}: the second submit sent a waiting call again, or not the next {N} calls")
                # 3. nothing is written before the batch has ended
                st = batch.collect("BATCHTEST", out, clients=svc, transport=svc.transport)
                log = run.log_path_for("primary", out)
                need(not st and not os.path.exists(log), f"{k}: rows written before the batch ended")
                # 4. after it ends: one row per answer, plan order, half price, its batch named; failures not in the data
                svc.done = True
                st = batch.collect("BATCHTEST", out, clients=svc, transport=svc.transport)
                rows = [json.loads(x) for x in open(log, encoding="utf-8")]
            # the fake fails by position inside each batch
            # two rounds of N calls, each in batches of 15, 15 and 10; the fake fails by position inside each batch
            chunks = [rids[a:min(a + 15, start + N)] for start in (0, N) for a in range(start, start + N, 15)]
            answered = {rid for c in chunks for i, rid in enumerate(c) if not fails(i)}
            want = [r for r in rids[:2 * N] if r in answered]
            need([r["record_id"] for r in rows] == want, f"{k}: rows are not the answered calls in plan order")
            need(all(r["raw_response"] == "B" and r["parsed_choice"] for r in rows), f"{k}: an answer was not parsed")
            reg = run.MODEL_REGISTRY[k]
            full = run._usd({"prompt_tokens": 100, "completion_tokens": 5}, reg)
            need(all(abs(r["cost_usd"] - round(full * 0.5, 6)) < 1e-9 for r in rows), f"{k}: a row is not at half price")
            need(all(r["sampling_params_effective"].get("batch", "").startswith(("batch_", "msgbatch_", "mjob_", "xbatch_"))
                     for r in rows), f"{k}: a row does not name its batch")
            ep = log[:-len(".jsonl")] + ".errors.jsonl"
            errs = [json.loads(x) for x in open(ep, encoding="utf-8")] if os.path.exists(ep) else []
            need(len(errs) == 2 * N - len(want) and not ({e["record_id"] for e in errs} & {r["record_id"] for r in rows}),
                 f"{k}: failed answers are not in the errors file alone ({len(errs)})")
            # 5. the next submit sends only the failed calls; after its collect, no call of the first N is left out
            svc.done = False
            with contextlib.redirect_stdout(io.StringIO()):
                rep3 = batch.submit([k], "primary", None, "BATCHTEST", out, 5.0, clients=svc, transport=svc.transport,
                                    max_calls=2 * N - len(want))
                resent = sent_bodies(route, {b: svc.received[b] for b in [r[1] for r in rep3]})
                need(sorted(resent) == sorted(e["record_id"] for e in errs), f"{k}: the resubmit is not the failed calls")
                svc.done = True
                # the second round answers every call (the fake fails by position, so shift the failures away)
                globals()["fails"] = lambda i: False
                batch.collect("BATCHTEST", out, clients=svc, transport=svc.transport)
                globals()["fails"] = lambda i: i % 7 == 3
            rows = [json.loads(x)["record_id"] for x in open(log, encoding="utf-8")]
            need(sorted(rows) == sorted(rids[:2 * N]) and len(rows) == 2 * N, f"{k}: after the resubmit {len(rows)} of {2 * N} calls")
        # 7. the reviewers' findings of 2026-11-24 (REVIEW-gemini.md, REVIEW-opus.md)
        review_checks(need, tmp, stimuli, cats)
        # 6. refusals
        svc = Services()
        for args, why in ((["qwen25-7b"], "the vllm route"), (["qwen4-max"], "the OpenRouter route")):
            try:
                batch.submit(args, "primary", None, "BATCHTEST", tmp, 5.0, clients=svc, transport=svc.transport, max_calls=2)
                need(False, f"a batch was accepted on {why}")
            except ValueError:
                need(True, "")
        try:
            batch.submit(["gpt-6-luna"], "sequential", None, "BATCHTEST", tmp, 5.0, clients=svc, max_calls=2)
            need(False, "a batch of sequential sessions was accepted")
        except ValueError:
            need(True, "")
        try:
            batch.submit(["claude-haiku-5-5"], "primary", None, "BATCHTEST", os.path.join(tmp, "cap"), 1e-9,
                         clients=svc, max_calls=5)
            need(False, "a batch over the cost cap was accepted")
        except SystemExit:
            need(True, "")
        # a picture request carries the registered picture, in each service's own form
        pic = next(s for s in run.iter_specs(stimuli, cats, ["claude-haiku-5-5"], arm="primary") if s["fmt"] == "pictures")
        body = batch.request_body(pic)[1]
        need(body["messages"][-1]["content"][1]["type"] == "image", "Anthropic picture request lacks its image block")
        pic = next(s for s in run.iter_specs(stimuli, cats, ["gpt-6-luna"], arm="primary") if s["fmt"] == "pictures")
        body = batch.request_body(pic)[1]
        need(body["messages"][-1]["content"][1]["type"] == "image_url", "OpenAI picture request lacks its image part")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if fails_:
        print(f"TEST_BATCH FAIL: {len(fails_)} of {n} checks")
        for f in fails_[:30]:
            print("  -", f)
        return 1
    print(f"TEST_BATCH PASS: {n} checks on five batch services (fakes answering from batch_fixtures.json); "
          f"no network, no charge.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
