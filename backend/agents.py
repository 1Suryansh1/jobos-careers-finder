"""Discovery (Search), Match (Gemini structured), Prefill (TinyFish Agent, stops before submit)."""
import re, time, json, html, hashlib
from concurrent.futures import ThreadPoolExecutor
from . import tf, llm, cache

ATS_SITES = ["job-boards.greenhouse.io", "jobs.lever.co", "jobs.ashbyhq.com", "myworkdayjobs.com"]
JOB_URL = re.compile(r"(greenhouse\.io/[^/]+/jobs/\d+|jobs\.lever\.co/[^/]+/[0-9a-f-]{36}|jobs\.ashbyhq\.com/[^/]+/[0-9a-f-]{36}|myworkdayjobs\.com/.+/job/)")

def discover(role, location="", per_site=6):
    """One Search per ATS domain, in parallel (Search limit 30 req/min)."""
    def one(site):
        c = cache.get("search", f"{site}:{role}:{location}")
        if c: return c
        r = tf.search(f"site:{site} {role} {location}".strip())
        out = [{"url": x["url"].replace("http://", "https://"), "title": x.get("title"), "snippet": x.get("snippet"), "site": site, "ms": r["ms"]}
               for x in r["results"] if JOB_URL.search(x.get("url", ""))][:per_site]
        cache.put("search", f"{site}:{role}:{location}", out); return out
    with ThreadPoolExecutor(4) as ex: lists = list(ex.map(one, ATS_SITES))
    seen, res = set(), []
    from itertools import zip_longest
    for row in zip_longest(*lists):
        for x in row:
            if not x: continue
            k = x["url"].split("?")[0]
            if k not in seen: seen.add(k); res.append(x)
    return res

MATCH_SCHEMA = {"type": "object", "properties": {
    "fit_score": {"type": "integer"}, "verdict": {"type": "string", "enum": ["apply", "stretch", "skip"]},
    "summary": {"type": "string"},
    "reasons": {"type": "array", "items": {"type": "object", "properties": {
        "claim": {"type": "string"}, "jd_evidence": {"type": "string"}, "resume_evidence": {"type": "string"},
        "impact": {"type": "string", "enum": ["+", "-"]}}, "required": ["claim", "jd_evidence", "resume_evidence", "impact"]}},
    "gaps": {"type": "array", "items": {"type": "string"}},
    "answers": {"type": "array", "items": {"type": "object", "properties": {
        "question": {"type": "string"}, "answer": {"type": "string"}, "grounded_in": {"type": "string"},
        "needs_human": {"type": "boolean"}}, "required": ["question", "answer", "grounded_in", "needs_human"]}}},
    "required": ["fit_score", "verdict", "summary", "reasons", "gaps", "answers"]}

def strip_html(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(html.unescape(s or "")))).strip()

def match(profile, job):
    key = f"{job['url']}:{hashlib.md5(json.dumps(profile, sort_keys=True).encode()).hexdigest()[:10]}"
    c = cache.get("match", key)
    if c: return c
    qs = [f["label"] for f in job.get("form_fields", []) if f.get("type") in ("textarea", "input_text", "text", "multi_value_single_select", "other", "select")][:8]
    prompt = f"""You are a rigorous recruiting analyst. Score candidate-job fit 0-100.
Every reason MUST quote a short exact span from the JOB DESCRIPTION (jd_evidence) and from the RESUME (resume_evidence); if there is no resume evidence write "none" and impact "-".
Never invent facts about the candidate. For each application question draft an answer grounded ONLY in the resume/profile; set needs_human=true for legal, visa, salary or anything not in the resume.
JOB: {job['fields']['title']['value']} @ {job['fields']['company']['value']} ({job['fields']['location']['value']})
JOB DESCRIPTION: {strip_html(job.get('description'))[:6000]}
APPLICATION QUESTIONS: {json.dumps(qs)}
CANDIDATE PROFILE: {json.dumps(profile)[:5000]}"""
    out, ms = llm.structured(prompt, MATCH_SCHEMA)
    out["ms"] = ms; out["model"] = out.pop("_model", llm.MODEL)
    # quality gate: drop reasons whose resume evidence isn't actually in the resume
    blob = json.dumps(profile).lower()
    for r in out["reasons"]:
        ev = (r.get("resume_evidence") or "").lower().strip(' ."')
        r["verified"] = ev == "none" or (len(ev) > 3 and (ev in blob or all(w in blob for w in ev.split()[:6])))
    out["unverified_reasons"] = sum(not r["verified"] for r in out["reasons"])
    cache.put("match", key, out); return out

PREFILL_SCHEMA = {"type": "object", "properties": {
    "filled": {"type": "array", "items": {"type": "object", "properties": {
        "label": {"type": "string"}, "value": {"type": "string"}, "status": {"type": "string", "enum": ["filled", "skipped", "not_found"]}},
        "required": ["label", "status"]}},
    "submitted": {"type": "boolean"}, "blocker": {"type": "string", "nullable": True}},
    "required": ["filled", "submitted"]}
SUBMIT_RE = re.compile(r"\b(click|press|tap|hit)\b.*\b(submit|send application|finish application)\b", re.I)
def submit_guard(purpose): return bool(SUBMIT_RE.search(purpose))

def prefill(url, profile, answers, on_event=None):
    p = profile
    lines = [f"First Name: {p['first_name']}", f"Last Name: {p['last_name']}", f"Email: {p['email']}", f"Phone: {p['phone']}",
             f"LinkedIn: {p.get('linkedin','')}"] + [f"{a['question'][:120]}: {a['answer'][:300]}" for a in answers if not a.get("needs_human")][:5]
    goal = ("This is a job application page. If an 'Apply' button is shown, click it to reveal the form. "
            "Fill ONLY these text fields with exactly these values (skip any field not listed, skip file uploads, skip dropdowns you are unsure about):\n- "
            + "\n- ".join(lines) +
            "\nSAFETY RULES: Never click, press or focus any Submit / Send / Submit application button, not even to check it. "
            "Do not create an account or sign in. Do not verify by submitting. As soon as the listed fields are typed, stop and return JSON "
            "listing each field and its status, with submitted=false.")
    r = tf.agent(url, goal, PREFILL_SCHEMA, on_event=on_event, tag="prefill", max_duration=150, guard=submit_guard)
    return r
