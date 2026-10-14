"""TinyFish primitives, raw REST per docs.tinyfish.ai (verified 2026-10-14).
Search GET api.search.tinyfish.ai | Fetch POST api.fetch.tinyfish.ai | Agent POST agent.tinyfish.ai/v1/automation/run-sse
Runs GET agent.tinyfish.ai/v1/runs/{id} | Wallet GET /v1/wallet. Auth header X-API-Key."""
import os, json, time, threading, httpx
from collections import Counter
KEY = lambda: os.environ.get("TINYFISH_API_KEY", "")
H = lambda: {"X-API-Key": KEY(), "Content-Type": "application/json"}
AGENT = "https://agent.tinyfish.ai"
STEP_USD = 0.016
stats = Counter()
LOG = os.path.join(os.path.dirname(__file__), "..", "data", "tinyfish_runs.jsonl")
# pricing page: Agent limit 2 concurrent runs (free tier) -> global semaphore
AGENT_SEM = threading.Semaphore(int(os.environ.get("TF_AGENT_CONCURRENCY", "2")))

def _log(rec):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f: f.write(json.dumps(rec) + "\n")

def _retry(fn, tries=3):
    for i in range(tries):
        try:
            r = fn()
            if r.status_code in (429, 503) and i < tries - 1:
                time.sleep(float(r.headers.get("Retry-After", 2 * (i + 1)))); continue
            r.raise_for_status(); return r
        except httpx.TransportError:
            if i == tries - 1: raise
            time.sleep(1 + i)

def search(query, **kw):
    t = time.time(); stats["search"] += 1
    r = _retry(lambda: httpx.get("https://api.search.tinyfish.ai", params={"query": query, **kw}, headers=H(), timeout=15))
    j = r.json(); ms = int((time.time() - t) * 1000)
    _log({"api": "search", "query": query, "ms": ms, "n": len(j.get("results", []))})
    return {"results": j.get("results", []), "ms": ms}

def fetch(urls, fmt="markdown", ttl=None, **kw):
    t = time.time(); stats["fetch"] += 1
    body = {"urls": urls[:10], "format": fmt, **kw}
    if ttl is not None: body["ttl"] = ttl
    r = _retry(lambda: httpx.post("https://api.fetch.tinyfish.ai", json=body, headers=H(), timeout=150))
    j = r.json(); ms = int((time.time() - t) * 1000)
    _log({"api": "fetch", "urls": urls, "ms": ms, "errors": j.get("errors")})
    return {"results": j.get("results", []), "errors": j.get("errors", []), "ms": ms}

def agent(url, goal, output_schema=None, on_event=None, browser_profile="lite", max_duration=240, tag="", guard=None):
    """SSE run. on_event(ev) gets STARTED/STREAMING_URL/PROGRESS/COMPLETE live."""
    body = {"url": url, "goal": goal, "browser_profile": browser_profile,
            "agent_config": {"max_duration_seconds": max_duration}}
    if output_schema: body["output_schema"] = output_schema
    out = {"url": url, "run_id": None, "streaming_url": None, "steps": [], "result": None, "status": None}
    with AGENT_SEM:
        t = time.time(); stats["agent"] += 1
        with httpx.stream("POST", f"{AGENT}/v1/automation/run-sse", json=body, headers=H(), timeout=httpx.Timeout(30, read=max_duration + 60)) as r:
            if r.status_code >= 400:
                r.read(); raise RuntimeError(f"agent HTTP {r.status_code}: {r.text[:300]}")
            for line in r.iter_lines():
                if not line.startswith("data:"): continue
                try: ev = json.loads(line[5:].strip())
                except Exception: continue
                ty = ev.get("type"); out["run_id"] = ev.get("run_id") or out["run_id"]
                if ty == "STREAMING_URL": out["streaming_url"] = ev.get("streaming_url")
                if ty == "PROGRESS":
                    out["steps"].append(ev.get("purpose"))
                    if guard and out["run_id"] and guard(ev.get("purpose") or ""):
                        c = cancel(out["run_id"]); out["guard_tripped"] = ev.get("purpose"); out["cancel"] = c
                        if on_event: on_event({"type": "GUARD", "purpose": ev.get("purpose"), "cancel": c})
                        out["status"] = "CANCELLED_BY_GUARD"; break
                if on_event:
                    try: on_event(ev)
                    except Exception: pass
                if ty == "COMPLETE":
                    res = ev.get("result")
                    if isinstance(res, str):
                        try: res = json.loads(res)
                        except Exception: pass
                    out.update(result=res, status=ev.get("status"), error=ev.get("error")); break
        out["ms"] = int((time.time() - t) * 1000)
    stats["agent_steps"] += len(out["steps"])
    out["usd_est"] = round(len(out["steps"]) * STEP_USD, 3)
    _log({"api": "agent", "tag": tag, "url": url, "run_id": out["run_id"], "status": out["status"], "steps": len(out["steps"]),
          "ms": out["ms"], "streaming_url": out["streaming_url"], "schema": bool(output_schema)})
    return out

def get_run(run_id):
    return httpx.get(f"{AGENT}/v1/runs/{run_id}", headers=H(), timeout=30).json()

def wallet():
    return httpx.get(f"{AGENT}/v1/wallet", headers=H(), timeout=15).json()

def cancel(run_id):
    try: return httpx.post(f"{AGENT}/v1/runs/{run_id}/cancel", headers=H(), timeout=15).json()
    except Exception as e: return {"error": str(e)[:100]}
