import os, json, time, uuid, threading, asyncio, csv, io
from dotenv import load_dotenv
ROOT = os.path.join(os.path.dirname(__file__), "..")
load_dotenv(os.path.join(ROOT, ".env"))
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx
from . import tf, finder, agents as A, llm, cache

app = FastAPI(title="JobOS Careers Finder")
JOBS = {}
ENABLE_PREFILL = os.environ.get("ENABLE_PREFILL", "0") == "1"   # OFF by default; never submits
REFRESH_MIN = int(os.environ.get("REFRESH_MINUTES", "180"))
STATE = {"last_prefs": None, "last_results": [], "last_stats": {}, "last_refresh": None, "next_refresh": None}

class Prefs(BaseModel):
    role: str = "ML / SWE"; locations: list[str] = ["India", "Remote"]; keywords: list[str] = ["python"]; exclude: list[str] = []
    seniority: list[str] = ["intern", "entry"]; job_type: str = "internship"; needs_sponsorship: bool = False; use_agent: bool = True

class Job:
    def __init__(s, kind): s.id = uuid.uuid4().hex[:8]; s.kind = kind; s.events = []; s.done = False; s.t0 = time.time(); s.result = None; s.lives = {}
    def emit(s, stage, msg, data=None): s.events.append({"i": len(s.events), "t": round(time.time() - s.t0, 1), "stage": stage, "msg": msg, "data": data or {}})

def _find(j, p):
    try:
        def live(co, url): j.lives[co] = url; j.emit("live", f"{co}: live TinyFish browser", {"company": co, "streaming_url": url})
        prev = finder.last_run_ts()
        out, stats = finder.run(p, j.emit, live, use_agent=False, prev=prev)        # fast pass: APIs + Search + Fetch (~30 s)
        STATE.update(last_prefs=p, last_results=out, last_stats=stats)
        j.emit("partial", f"{stats['final']} listings ready; Workday agent still running", stats)
        if p.get("use_agent", True):
            out, stats = finder.run(p, j.emit, live, use_agent=True, prev=prev)     # agent pass merges Workday results
            STATE.update(last_results=out, last_stats=stats)
        j.result = {"listings": out, "stats": stats}; j.emit("done", f"{stats['final']} listings ({stats['new_since_last_run']} new) in {stats['seconds']}s", stats)
    except Exception as e:
        j.emit("error", f"{type(e).__name__}: {str(e)[:200]}")
    j.done = True

@app.post("/api/find")
def find(p: Prefs):
    j = Job("find"); JOBS[j.id] = j; threading.Thread(target=_find, args=(j, p.model_dump()), daemon=True).start(); return {"id": j.id}

@app.get("/api/job/{jid}")
def job(jid: str):
    j = JOBS.get(jid)
    if not j: raise HTTPException(404)
    return {"id": j.id, "done": j.done, "events": j.events, "result": j.result, "lives": j.lives}

@app.get("/api/job/{jid}/stream")
async def stream(jid: str):
    j = JOBS[jid]
    async def gen():
        i = 0
        while True:
            while i < len(j.events): yield f"data: {json.dumps(j.events[i])}\n\n"; i += 1
            if j.done: yield 'data: {"stage":"eof"}\n\n'; break
            await asyncio.sleep(0.3)
    return StreamingResponse(gen(), media_type="text/event-stream")

@app.get("/api/listings")
def listings(): return {"listings": STATE["last_results"], "stats": STATE["last_stats"], "prefs": STATE["last_prefs"],
                        "last_refresh": STATE["last_refresh"], "next_refresh": STATE["next_refresh"], "refresh_minutes": REFRESH_MIN}

def _refresh(j):
    try:
        r = finder.refresh(j.emit); STATE["last_refresh"] = time.time()
        live = {x["key"]: x for x in STATE["last_results"]}
        rows = {k: v for k, v in ((json.loads(d)["key"], json.loads(d)) for (d,) in finder.db().execute("select data from listing"))}
        STATE["last_results"] = [dict(x, live=rows.get(k, x).get("live"), last_verified=rows.get(k, x).get("last_verified")) for k, x in live.items()]
        STATE["last_results"] = [x for x in STATE["last_results"] if x["live"] is not False]
        j.result = r; j.emit("done", f"Re-checked {r['checked']} listings; {r['closed']} closed since last check", r)
    except Exception as e: j.emit("error", str(e)[:200])
    j.done = True

@app.post("/api/refresh")
def refresh():
    j = Job("refresh"); JOBS[j.id] = j; threading.Thread(target=_refresh, args=(j,), daemon=True).start(); return {"id": j.id}

def scheduler():
    while True:
        STATE["next_refresh"] = time.time() + REFRESH_MIN * 60; time.sleep(REFRESH_MIN * 60)
        if STATE["last_prefs"]:
            j = Job("scheduled"); JOBS[j.id] = j
            p = dict(STATE["last_prefs"]); _find(j, p)   # Workday agent results cached 24h -> scheduled runs cost $0 in agent steps
threading.Thread(target=scheduler, daemon=True).start()

COLS = ["score", "new", "title", "company", "location", "job_type", "seniority", "url", "sources", "posted", "live_evidence", "last_verified"]
@app.get("/api/export.json")
def export_json(): return Response(json.dumps(STATE["last_results"], indent=1, default=str), media_type="application/json",
                                   headers={"Content-Disposition": "attachment; filename=jobos_listings.json"})
@app.get("/api/export.csv")
def export_csv():
    b = io.StringIO(); w = csv.writer(b); w.writerow(COLS)
    for x in STATE["last_results"]:
        w.writerow([("; ".join(x[c]) if isinstance(x.get(c), list) else time.strftime("%Y-%m-%d %H:%M", time.localtime(x[c])) if c == "last_verified" else x.get(c)) for c in COLS])
    return Response(b.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=jobos_listings.csv"})

@app.post("/api/explain/{key}")
def explain(key: str):
    """Optional Gemini explanation, cached 7 days; deterministic matcher remains the primary path."""
    x = next((l for l in STATE["last_results"] if l["key"] == key), None)
    if not x: raise HTTPException(404)
    c = cache.get("match", f"explain:{key}")
    if c: return c
    sch = {"type": "object", "properties": {"summary": {"type": "string"}, "tips": {"type": "array", "items": {"type": "string"}}}, "required": ["summary", "tips"]}
    try: out, ms = llm.structured(f"In 2 sentences, explain to a DTU student why this opening fits these preferences, then give 2 short application tips. Prefs: {json.dumps(STATE['last_prefs'])}. Job: {x['title']} at {x['company']}, {x['location']}.", sch)
    except Exception as e: return {"summary": "LLM unavailable (free-tier quota); deterministic reasons shown above.", "tips": [], "error": str(e)[:100]}
    cache.put("match", f"explain:{key}", out); return out

class PF(BaseModel): key: str
@app.post("/api/prefill")
def prefill(req: PF):
    if not ENABLE_PREFILL: raise HTTPException(403, "Prefill is disabled (set ENABLE_PREFILL=1). It never submits.")
    x = next((l for l in STATE["last_results"] if l["key"] == req.key), None)
    if not x: raise HTTPException(404)
    j = Job("prefill"); JOBS[j.id] = j; prof = json.load(open(os.path.join(ROOT, "data", "profile.json")))
    def go():
        def ev(e):
            if e.get("type") == "STREAMING_URL": j.lives["prefill"] = e["streaming_url"]; j.emit("live", "live browser", {"streaming_url": e["streaming_url"]})
            elif e.get("type") == "PROGRESS": j.emit("agent", e.get("purpose"))
            elif e.get("type") == "GUARD": j.emit("error", f"SAFETY GUARD cancelled run at '{e.get('purpose')}'")
        try: r = A.prefill(x["url"], prof, [], on_event=ev); j.result = r["result"]; j.emit("done", "Filled; stopped before submit. Review & submit yourself.", {"result": r["result"]})
        except Exception as e: j.emit("error", str(e)[:200])
        j.done = True
    threading.Thread(target=go, daemon=True).start(); return {"id": j.id}

@app.get("/api/health")
def health(): return {"ok": True, "gemini": llm.available(), "tinyfish": bool(tf.KEY()), "prefill_enabled": ENABLE_PREFILL, "refresh_minutes": REFRESH_MIN}
@app.get("/api/wallet")
def wallet(): return tf.wallet()
@app.get("/api/bench")
def bench():
    p = os.path.join(ROOT, "bench", "results.json"); return json.load(open(p)) if os.path.exists(p) else {}

app.mount("/", StaticFiles(directory=os.path.join(ROOT, "web"), html=True), name="web")
