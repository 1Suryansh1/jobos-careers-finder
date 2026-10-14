"""Scripted demo: hunt -> ghost filter -> ranked fit -> prefill (stops before submit). Needs ./start.sh running."""
import httpx, time, json, sys
B = "http://localhost:8300"
def wait(hid, show=True):
    seen = 0
    while True:
        h = httpx.get(f"{B}/api/hunt/{hid}", timeout=30).json()
        for e in h["events"][seen:]:
            if show and e["stage"] not in ("detect", "job"): print(f"{e['t']:7.1f}s {e['stage']:>10}  {e['msg'][:140]}")
        seen = len(h["events"])
        if h["done"]: return h
        time.sleep(1)
role = sys.argv[1] if len(sys.argv) > 1 else "backend engineer python"
hid = httpx.post(f"{B}/api/hunt", json={"role": role, "location": "remote", "limit": 12}).json()["id"]
print("hunt", hid, f"-> open {B}/#{hid}")
h = wait(hid)
ranked = sorted([j for j in h["jobs"].values() if j.get("match")], key=lambda j: -j["match"]["fit_score"])
print("\nRANKED:"); [print(f"  {j['match']['fit_score']:3d} {j['status']:8} {j['resolved']['fields']['title']['value'][:60]}  [{j['site']}]") for j in ranked]
print("GHOSTS:", [j["url"] for j in h["jobs"].values() if j["status"] == "closed"])
gh = next((j for j in ranked if "greenhouse" in j["url"]), None)
if gh and "--prefill" in sys.argv:
    pid = httpx.post(f"{B}/api/prefill", json={"hunt": hid, "job": gh["id"]}).json()["id"]
    print("\nPREFILL", gh["url"]); p = wait(pid)
    print(json.dumps(p["jobs"]["prefill"].get("result"), indent=1))
