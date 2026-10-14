import json, os, statistics
R = os.path.join(os.path.dirname(__file__), ".."); r = json.load(open(f"{R}/bench/results.json"))
runs = [json.loads(l) for l in open(f"{R}/data/tinyfish_runs.jsonl")]
def runstats(tag):
    x = [a for a in runs if a.get("tag") == tag][-12:]
    return (int(statistics.median([a["ms"] for a in x])), round(statistics.mean([a["steps"] for a in x]), 1)) if x else ("-", "-")
pc = lambda v: "-" if v is None else f"{v*100:.0f}%"
out = [f"Measured {r['when']} on {r['n']} hand-labelled postings (4 Greenhouse, 3 Lever, 1 Ashby, 4 Workday; 4 closed or ghost). Labels were checked against the live page, the ATS JSON and Workday's page JSON. Latency is wall-clock per posting under realistic concurrency (6 workers, agent semaphore 2), so agent numbers include queueing.\n",
       "| design | n | p50 | p95 | success | is_open acc | title acc | location acc | agent steps | est. $ | mean conf (right/wrong) |", "|---|---|---|---|---|---|---|---|---|---|---|"]
for k, v in r["strategies"].items():
    out.append(f"| **{k}** | {v['n']} | {v['p50_ms']/1000:.1f} s | {v['p95_ms']/1000:.1f} s | {pc(v['success'])} | {pc(v['acc']['is_open'])} | {pc(v['acc']['title'])} | {pc(v['acc']['location'])} | {v['agent_steps']} | ${v['usd']} | {v['conf_when_right']}/{v['conf_when_wrong']} |")
a, l = runstats("agent_only"), runstats("agent_loose")
out += ["", f"Per agent run, excluding queue time: tight goal + output_schema has p50 {a[0]/1000:.1f} s and {a[1]} steps on average. Loose goal with no schema has p50 {l[0]/1000:.1f} s and {l[1]} steps.", "",
 "**Ablation findings**",
 "1. **Tiered vs agent-only:** both reach the same accuracy (100% is_open, 100% title). Tiered is about **90× faster at p50** (1.6 s vs 150 s), has a lower p95, and costs about 4× less, because 9 of 12 postings never touch a browser (8 answered by an ATS API, 1 dead Workday page short-circuited at Fetch).",
 "2. **Tiered vs fetch-only:** fetch-only is faster at the tail but **gets is_open wrong on 2 of 4 closed postings**. Greenhouse redirects a dead job to the company's board page, so Fetch sees a live page titled 'CodeRoad' or 'GitLab'. Only the ATS API 404 (or an agent) catches this. Fetch also returns no structured location.",
 "3. **Tight goal + output_schema vs loose goal without schema:** the loose goal took fewer steps but gave **0% usable fields**, because it returned free-form prose that can't be parsed into the contract. The schema is what makes agent output machine-verifiable.",
 "4. **Confidence calibration:** tiered's mean confidence on correct liveness calls is 0.88. Fetch-only has the same confidence (0.75) whether right or wrong, which shows single-source confidence is uninformative. Cross-checking is what separates them.",
 "5. The one remaining location miss in tiered/agent is the re-used Datasite requisition. The agent returned a description ('NYC (Hybrid…)') instead of the label, and it's flagged with lower title confidence."]
p = f"{R}/PLAN.md"; s = open(p).read()
import re
block = "\n".join(out)
s = re.sub(r"(See `bench/results.json`.*?\n\n)(BENCH_TABLE|<!--B-->.*?<!--/B-->)", lambda m: m.group(1) + "<!--B-->\n" + block + "\n<!--/B-->", s, flags=re.S)
s = s.replace("DOCS_TABLE", open(f"{R}/docs_ref/DOCS_TABLE.md").read())
r["findings"] = out[-5:]; json.dump(r, open(f"{R}/bench/results.json", "w"), indent=1)
open(p, "w").write(s); print(block)
