"""Benchmark: real p50/p95 latency, success, field accuracy vs hand-labelled set, for 4 designs.
Labels: hand-checked on 2026-10-14 against the live page / ATS public API / Workday page JSON."""
import os, sys, json, time, statistics
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv; load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
os.environ["JOBOS_NOCACHE"] = "1"
from concurrent.futures import ThreadPoolExecutor
from backend.resolve import resolve, sim, norm
L = json.load(open(os.path.join(os.path.dirname(__file__), "labels.json")))
STRATS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["tiered", "fetch_only", "agent_only", "agent_loose"]
LOOSE_SUBSET = 4

def pct(xs, p):
    xs = sorted(xs); k = (len(xs) - 1) * p; f = int(k); c = min(f + 1, len(xs) - 1); return int(xs[f] + (xs[c] - xs[f]) * (k - f))
def loc_ok(a, b):
    A, B = set(norm(a)), set(norm(b)); return bool(A and B) and len(A & B) / len(B) >= 0.5

def score(lab, r):
    f = r["fields"]; o = {}
    o["is_open"] = f["is_open"]["value"] == lab["is_open"]
    if lab["is_open"]:
        o["title"] = sim(f["title"]["value"], lab["title"]) >= 0.8
        o["location"] = loc_ok(f["location"]["value"], lab["location"])
    return o

def run(strat):
    items = L[:] if strat != "agent_loose" else [l for l in L if l["is_open"]][:LOOSE_SUBSET]
    def one(lab):
        t = time.time()
        try: r = resolve(lab["url"], strat, need_form=False); err = None
        except Exception as e: r, err = None, str(e)[:150]
        ms = int((time.time() - t) * 1000)
        if not r: return {"url": lab["url"], "ms": ms, "ok": False, "err": err}
        s = score(lab, r); conf = r["fields"]["is_open"]["confidence"]
        return {"url": lab["url"], "ms": ms, "ok": all(x.get("ok", True) for x in r["trail"]) and r["fields"]["is_open"]["value"] is not None,
                "score": s, "conf": conf, "steps": len((r.get("agent") or {}).get("steps") or []), "run_id": (r.get("agent") or {}).get("run_id"),
                "streaming_url": (r.get("agent") or {}).get("streaming_url"), "notes": r["notes"], "schema_problems": r["schema_problems"],
                "got": {k: r["fields"][k]["value"] for k in ("is_open", "title", "location")}}
    with ThreadPoolExecutor(6) as ex: rows = list(ex.map(one, items))
    lat = [x["ms"] for x in rows]; acc = {}
    for k in ("is_open", "title", "location"):
        v = [x["score"][k] for x in rows if "score" in x and k in x["score"]]
        acc[k] = round(sum(v) / len(v), 3) if v else None
    steps = sum(x.get("steps", 0) for x in rows)
    # calibration: mean confidence when right vs wrong
    right = [x["conf"] for x in rows if x.get("score", {}).get("is_open")]; wrong = [x["conf"] for x in rows if "score" in x and not x["score"]["is_open"]]
    return {"n": len(rows), "p50_ms": pct(lat, .5), "p95_ms": pct(lat, .95), "mean_ms": int(statistics.mean(lat)),
            "success": round(sum(x["ok"] for x in rows) / len(rows), 3), "acc": acc, "agent_steps": steps, "usd": round(steps * 0.016, 3),
            "conf_when_right": round(statistics.mean(right), 2) if right else None, "conf_when_wrong": round(statistics.mean(wrong), 2) if wrong else None,
            "rows": rows}

if __name__ == "__main__":
    out_p = os.path.join(os.path.dirname(__file__), "results.json")
    res = json.load(open(out_p)) if os.path.exists(out_p) else {"strategies": {}}
    for s in STRATS:
        print("==", s, flush=True); res["strategies"][s] = run(s)
        v = res["strategies"][s]; print({k: v[k] for k in v if k != "rows"}, flush=True)
        res.update(n=len(L), when=time.strftime("%Y-%m-%d %H:%M IST")); json.dump(res, open(out_p, "w"), indent=1)
