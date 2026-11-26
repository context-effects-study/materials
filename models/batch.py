"""batch.py: sends the closed models' calls through their developers' batch services, which bill half the price.

Each request is the one run.py sends live, under the call's record id. A plan is split into batches; a state
file per model and condition keeps the batch ids, so no call is sent twice. When a batch has ended, its answers
are read with run.py's own parsing and written to the same log, in the order of the plan; a failed answer is
written to the errors file and sent again by the next submit. The services are OpenAI, Google, Anthropic,
Mistral and xAI.

Run: python models/batch.py submit|status|collect --run-id ID --out-dir DIR ...   (real calls, at Stage 2 only)
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run  # noqa: E402

CHUNK_CALLS = 20000                 # requests per batch (every service here takes at least 50,000)
CHUNK_BYTES = 150 * 1024 * 1024     # bytes per batch input (OpenAI's file limit is 200 MB; picture requests are large)
ENDED = {"openai": {"completed", "failed", "expired", "cancelled"},
         "mistral": {"SUCCESS", "FAILED", "TIMEOUT_EXCEEDED", "CANCELLED"}}


def request_body(spec):
    """(record_id, the request, the JSON body the service receives) for one call, exactly as run.py sends it live."""
    req = run.build_request(spec["model_key"], spec["arm"], setting=spec["setting"])
    kwargs = dict(req["kwargs"])
    extra = kwargs.pop("extra_body", {})
    body = {"model": req["model_id"], "messages": run.build_messages(spec, req["route"]), **kwargs, **extra}
    return req, body


# ---------------------------------------------------------------------------------------------------------------
# One class per batch service: submit(lines) -> batch id; ended(batch id) -> (True or False, status);
# results(batch id) -> [(custom id, True, response JSON) or (custom id, False, error text)].
# ---------------------------------------------------------------------------------------------------------------
class OpenAIBatch:
    """OpenAI's Batch API (files with purpose batch, then batches.create on /v1/chat/completions); Google's
    OpenAI-compatible endpoint takes the same calls (a check for the first pre-test batch)."""
    def __init__(self, client):
        self.c = client

    def submit(self, lines):
        content = "\n".join(json.dumps({"custom_id": cid, "method": "POST", "url": "/v1/chat/completions",
                                        "body": body}, ensure_ascii=False) for cid, body in lines) + "\n"
        f = self.c.files.create(file=("requests.jsonl", content.encode("utf-8")), purpose="batch")
        return self.c.batches.create(input_file_id=f.id, endpoint="/v1/chat/completions",
                                     completion_window="24h").id

    def ended(self, bid):
        b = self.c.batches.retrieve(bid)
        return b.status in ENDED["openai"], b.status

    def results(self, bid):
        b = self.c.batches.retrieve(bid)
        out = []
        for fid in (getattr(b, "output_file_id", None), getattr(b, "error_file_id", None)):
            if not fid:
                continue
            for line in self.c.files.content(fid).text.splitlines():
                if not line.strip():
                    continue
                d = json.loads(line)
                resp = d.get("response") or {}
                if resp.get("status_code") == 200:
                    out.append((d["custom_id"], True, resp["body"]))
                else:
                    out.append((d["custom_id"], False, json.dumps(d.get("error") or resp.get("body"))[:500]))
        return out


class AnthropicBatch:
    """Anthropic's Message Batches API: one request per call with its params; results once processing has ended."""
    def __init__(self, client):
        self.c = client

    def submit(self, lines):
        return self.c.messages.batches.create(requests=[{"custom_id": cid, "params": body} for cid, body in lines]).id

    def ended(self, bid):
        b = self.c.messages.batches.retrieve(bid)
        return b.processing_status == "ended", b.processing_status

    def results(self, bid):
        out = []
        for e in self.c.messages.batches.results(bid):
            res = e.result
            if getattr(res, "type", None) == "succeeded":
                msg = res.message
                out.append((e.custom_id, True, msg.model_dump() if hasattr(msg, "model_dump") else msg))
            else:
                err = getattr(res, "error", None)
                out.append((e.custom_id, False, f"{getattr(res, 'type', 'unknown')}: "
                                                f"{err.model_dump() if hasattr(err, 'model_dump') else err}"[:500]))
        return out


class HTTPBatch:
    """The services without an SDK here (Mistral, xAI), over HTTP. transport(method, path, json=None, files=None)
    returns the decoded JSON or text; the default sends it with httpx to the route's pinned base URL and key."""
    def __init__(self, route, transport=None):
        self.route = route
        self.t = transport or self._http

    def _http(self, method, path, json=None, files=None, data=None):
        import httpx
        key = next((os.environ.get(k) for k in run.ROUTE_KEYS[self.route] if os.environ.get(k)), None)
        if not key:                                   # review finding 4.4: a clear error, not a bare StopIteration
            raise RuntimeError(f"{' or '.join(run.ROUTE_KEYS[self.route])} not in environment")
        r = httpx.request(method, run.ROUTE_BASE[self.route].rstrip("/") + path, json=json, files=files, data=data,
                          headers={"Authorization": f"Bearer {key}"}, timeout=120)
        r.raise_for_status()
        # a file's content (a batch's results: JSON Lines) is returned as text whatever its content type, which may
        # be application/jsonl or application/x-ndjson; other answers are one JSON object
        if path.endswith("/content"):
            return r.text
        return r.json() if r.headers.get("content-type", "").split(";")[0].strip() == "application/json" else r.text

    def submit(self, lines):
        if self.route == "mistral":
            model = lines[0][1]["model"]
            content = "\n".join(json.dumps({"custom_id": cid, "body": {k: v for k, v in body.items() if k != "model"}},
                                           ensure_ascii=False) for cid, body in lines) + "\n"
            f = self.t("POST", "/files", files={"file": ("requests.jsonl", content.encode("utf-8"))},
                       data={"purpose": "batch"})
            return self.t("POST", "/batch/jobs", json={"input_files": [f["id"]], "model": model,
                                                       "endpoint": "/v1/chat/completions"})["id"]
        b = self.t("POST", "/batches", json={"name": f"lce-{int(time.time())}"})
        bid = b["batch_id"]
        self.t("POST", f"/batches/{bid}/requests", json={"batch_requests": [
            {"batch_request_id": cid, "batch_request": {"chat_get_completion": body}} for cid, body in lines]})
        return bid

    def ended(self, bid):
        if self.route == "mistral":
            j = self.t("GET", f"/batch/jobs/{bid}")
            return j["status"] in ENDED["mistral"], j["status"]
        j = self.t("GET", f"/batches/{bid}")
        st = j.get("state") or {}
        return st.get("num_pending", 1) == 0, f"pending {st.get('num_pending')}"

    def results(self, bid):
        out = []
        if self.route == "mistral":
            j = self.t("GET", f"/batch/jobs/{bid}")
            for fid in (j.get("output_file"), j.get("error_file")):
                if not fid:
                    continue
                for line in str(self.t("GET", f"/files/{fid}/content")).splitlines():
                    if line.strip():
                        d = json.loads(line)
                        resp = d.get("response") or {}
                        if resp.get("status_code") == 200:
                            out.append((d["custom_id"], True, resp["body"]))
                        else:
                            out.append((d["custom_id"], False, json.dumps(d.get("error") or resp)[:500]))
            return out
        token = None
        while True:
            j = self.t("GET", f"/batches/{bid}/results" + (f"?pagination_token={token}" if token else ""))
            for r in j.get("results", []):
                resp = ((r.get("batch_result") or {}).get("response") or {}).get("chat_get_completion")
                if resp:
                    out.append((r["batch_request_id"], True, resp))
                else:
                    out.append((r["batch_request_id"], False, str(r.get("error_message") or r)[:500]))
            token = j.get("pagination_token")
            if not token:
                return out


def service_for(route, clients=None, transport=None):
    if route in ("openai", "google"):
        return OpenAIBatch((clients or run.Clients()).client(route))
    if route == "anthropic":
        return AnthropicBatch((clients or run.Clients()).client("anthropic"))
    if route in ("mistral", "xai"):
        return HTTPBatch(route, transport)
    raise ValueError(f"the {route} route has no batch service")


# ---------------------------------------------------------------------------------------------------------------
# State: one JSON file per run, model, arm and setting under <out-dir>/batches/<run-id>/, listing each batch's id and
# the record ids it holds, so a collect in another session knows what to read and a submit never sends a call twice.
# ---------------------------------------------------------------------------------------------------------------
def state_path(out_dir, run_id, model, arm, setting):
    name = f"{model}__{arm}" + (f"_{setting}" if arm in run.SETTING_ARMS else "") + ".json"
    return os.path.join(out_dir, "batches", run_id, name)


def load_state(path):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {"batches": []}


def save_state(path, st):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:       # closed before the replace
        json.dump(st, f, indent=1)
    os.replace(tmp, path)


def logged_ids(log_path):
    ids = set()
    if os.path.exists(log_path):
        for line in open(log_path, encoding="utf-8"):
            if line.strip():
                ids.add(json.loads(line)["record_id"])
    return ids


MAX_ATTEMPTS = 2        # a call that fails is sent again once (REVIEW-BRIEF: "a failed answer is sent again once")


def submit(models, arm, setting, run_id, out_dir, cost_cap, clients=None, transport=None, max_calls=0):
    """Submit every planned call of the models that is neither logged, nor waiting in an open batch, nor failed in
    MAX_ATTEMPTS batches already. The cost cap covers the whole submission, all models together; a model that does not run the arm at the setting is refused (finding 4.3). Returns [(model, batch id,
    calls)]; calls given up after MAX_ATTEMPTS failures are printed."""
    if arm == "sequential":
        raise ValueError("sequential sessions are conversations: each call waits on the answer before it")
    d = json.load(open(run.STIM, encoding="utf-8"))
    stimuli, cats = d["stimuli"], d["categories"]
    planned, worst, given_up = [], 0.0, []
    for k in models:
        reg = run.MODEL_REGISTRY[k]
        if not reg["batch"]:
            raise ValueError(f"{k}: the {reg['route']} route has no batch service")
        run.setting_for(k, arm, setting)              # raises ValueError for an arm or setting the model does not run
        log = run.log_path_for(arm, out_dir, setting)
        sp = state_path(out_dir, run_id, k, arm, setting)
        st = load_state(sp)
        waiting = {rid for b in st["batches"] if not b.get("collected") for rid in b["record_ids"]}
        failures = {}
        for b in st["batches"]:
            for rid in b.get("failed_ids", []):
                failures[rid] = failures.get(rid, 0) + 1
        done = logged_ids(log)
        lines = []
        for spec in run.iter_specs(stimuli, cats, [k], arm=arm, setting=setting):
            rid = run.spec_record_id(run_id, spec)
            if rid in done or rid in waiting:
                continue
            if failures.get(rid, 0) >= MAX_ATTEMPTS:
                given_up.append((k, rid))
                continue
            req, body = request_body(spec)
            worst += 0.5 * run.worst_case_cost(k, arm, len(spec["prompt"]), int(spec["fmt"] == "pictures"),
                                               setting=spec["setting"])
            lines.append((rid, body))
            if max_calls and len(lines) >= max_calls:
                break
        planned.append((k, reg, sp, st, lines))
    if worst > cost_cap:
        raise SystemExit(f"[batch] REFUSING: the {sum(len(p[4]) for p in planned):,} calls of {len(models)} model(s) "
                         f"could cost up to ${worst:,.2f} at batch prices, over the ${cost_cap:,.2f} cap")
    for k, rid in given_up:
        print(f"[batch] {k}: call {rid} failed in {MAX_ATTEMPTS} batches; not sent again (see the errors file)")
    report = []
    for k, reg, sp, st, lines in planned:
        ad = service_for(reg["route"], clients, transport)
        chunk, size = [], 0

        def send():
            bid = ad.submit(chunk)
            st["batches"].append({"batch_id": bid, "route": reg["route"], "model": k, "arm": arm, "setting": setting,
                                  "record_ids": [c for c, _ in chunk], "submitted": time.strftime(
                                      "%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "collected": False})
            save_state(sp, st)                  # written after each batch, so a crash loses no batch id
            report.append((k, bid, len(chunk)))
        for cid, body in lines:
            n = len(json.dumps(body))
            if chunk and (len(chunk) >= CHUNK_CALLS or size + n > CHUNK_BYTES):
                send()
                chunk, size = [], 0
            chunk.append((cid, body))
            size += n
        if chunk:
            send()
    return report


def collect(run_id, out_dir, clients=None, transport=None):
    """Read every ended, uncollected batch of the run into its log through run_collection. A batch that ended without
    results (failed, expired or cancelled as a whole) is recorded with its status, and its calls count as failed
    once."""
    root = os.path.join(out_dir, "batches", run_id)
    stats = []
    for name in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        sp = os.path.join(root, name)
        st = load_state(sp)
        for b in st["batches"]:
            if b.get("collected"):
                continue
            ad = service_for(b["route"], clients, transport)
            ended, status = ad.ended(b["batch_id"])
            b["status"] = status
            if not ended:
                save_state(sp, st)
                continue
            k, arm, setting = b["model"], b["arm"], b["setting"]
            d = json.load(open(run.STIM, encoding="utf-8"))
            specs = {run.spec_record_id(run_id, s): s for s in run.iter_specs(d["stimuli"], d["categories"], [k],
                                                                                arm=arm, setting=setting)}
            held = set(b["record_ids"])                  # a set: one look-up per result
            res = {}
            for cid, ok, payload in ad.results(b["batch_id"]):
                spec = specs.get(cid)
                if spec is None or cid not in held:
                    continue                    # never a row for a call this batch did not hold
                req = run.build_request(k, arm, setting=spec["setting"])
                res[cid] = (run.result_from_response(spec, req, run.as_attrs(payload), None, price_factor=0.5,
                                                     batch=b["batch_id"]) if ok else
                            run.result_from_error(spec, req, f"batch error: {payload}", None, batch=b["batch_id"]))
            s = run.run_collection(True, 0, 1e12, [k], run_id, arm=arm, setting=setting,
                                   log_path=run.log_path_for(arm, out_dir, setting), results=res)
            answered = {c for c, r in res.items() if r["error"] is None}
            b["failed_ids"] = [c for c in b["record_ids"] if c not in answered]
            if not res:
                b["failure"] = f"the batch ended as {status!r} with no results"
            b["collected"], b["n_results"], b["n_written"], b["n_errors"] = True, len(res), s["written"], s["errors"]
            save_state(sp, st)
            stats.append((k, b["batch_id"], s["written"], len(b["failed_ids"])))
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("submit", "status", "collect"))
    ap.add_argument("--arm", default="primary", choices=run.ARMS)
    ap.add_argument("--setting", default=None, choices=run.SETTINGS)
    ap.add_argument("--models", default="")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--cost-cap", type=float, default=5.0)
    ap.add_argument("--max-calls", type=int, default=0)
    a = ap.parse_args()
    run.load_prompt_materials()
    run.load_env_file_if_present()
    if a.run_id == "DRYRUN":
        sys.exit("[batch] a batch is a live run: give it its own --run-id")
    if a.cmd == "submit":
        models = [m.strip() for m in a.models.split(",") if m.strip()]
        if not models:
            sys.exit("[batch] name the models (--models)")
        for k, bid, n in submit(models, a.arm, a.setting, a.run_id, a.out_dir, a.cost_cap, max_calls=a.max_calls):
            print(f"[batch] {k}: batch {bid} with {n:,} calls")
    elif a.cmd == "collect":
        for k, bid, w, e in collect(a.run_id, a.out_dir):
            print(f"[batch] {k}: batch {bid} read, {w:,} rows written, {e:,} errors left for the next submit")
    else:
        root = os.path.join(a.out_dir, "batches", a.run_id)
        for name in sorted(os.listdir(root)) if os.path.isdir(root) else []:
            for b in load_state(os.path.join(root, name))["batches"]:
                print(f"{b['model']:<22}{b['arm']:<10}{b['setting'] or '':<8}{b['batch_id']:<40}"
                      f"{len(b['record_ids']):>8,}  {'collected' if b.get('collected') else b.get('status', 'submitted')}")


if __name__ == "__main__":
    main()
