"""Tiered fact resolution: cache -> ATS public API -> TinyFish Fetch -> TinyFish Agent.
Every field carries {value, confidence, sources[{tier, value, evidence}]} and is cross-checked."""
import re, time, difflib, httpx
from urllib.parse import urlparse, parse_qs, unquote
from . import tf, cache

BASE_CONF = {"ats_api": 0.97, "agent": 0.85, "fetch": 0.75, "search": 0.5, "url": 0.4}
DEAD = re.compile(r"(doesn.t exist|does not exist|no longer (available|accepting|open)|job (is )?not found|position has been filled|"
                  r"this job (has|is) (closed|expired)|page not found|couldn.t find|isn.t available|job posting has expired)", re.I)

JOB_SCHEMA = {"type": "object", "properties": {
    "is_open": {"type": "boolean"},
    "closed_reason": {"type": "string", "nullable": True},
    "title": {"type": "string", "nullable": True},
    "company": {"type": "string", "nullable": True},
    "location": {"type": "string", "nullable": True},
    "posted": {"type": "string", "nullable": True},
    "apply_requires_account": {"type": "boolean"},
    "form_fields": {"type": "array", "maxItems": 25, "items": {"type": "object", "properties": {
        "label": {"type": "string"}, "required": {"type": "boolean"},
        "type": {"type": "string", "enum": ["text", "email", "phone", "file", "select", "checkbox", "textarea", "other"]}},
        "required": ["label", "required"]}}},
    "required": ["is_open", "apply_requires_account"]}

TIGHT_GOAL = ("You are on a job posting page. Do NOT submit anything and do NOT create an account. "
              "1) Decide if the posting is open (it is closed if the page says not found / no longer available / expired or redirects to a search page). "
              "2) Extract title, company, location and posted date text exactly as shown. "
              "3) If an application form is visible on this page or one click away via an 'Apply' button, list its fields (label, required, type). "
              "If applying needs sign-in or account creation, set apply_requires_account=true and stop. Return JSON only.")
LOOSE_GOAL = "Look at this job posting and tell me everything about it and its application form."

def detect(url):
    p = urlparse(url); h = p.netloc.lower(); parts = [x for x in p.path.split("/") if x]
    if "greenhouse.io" in h and "jobs" in parts:
        i = parts.index("jobs"); return {"ats": "greenhouse", "board": parts[i - 1], "id": parts[i + 1].split("?")[0]}
    if "gh_jid" in p.query: return {"ats": "greenhouse_custom", "id": parse_qs(p.query)["gh_jid"][0], "board": h.split(".")[-2]}
    if h == "jobs.lever.co" and len(parts) >= 2: return {"ats": "lever", "board": parts[0], "id": parts[1]}
    if h == "jobs.ashbyhq.com" and len(parts) >= 2: return {"ats": "ashby", "board": parts[0], "id": parts[1]}
    if "myworkdayjobs.com" in h: return {"ats": "workday", "board": h.split(".")[0], "id": parts[-1] if parts else ""}
    return {"ats": "unknown", "board": h, "id": ""}

def norm(s): return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split()
def sim(a, b):
    if not a or not b: return 0.0
    return difflib.SequenceMatcher(None, " ".join(norm(a)), " ".join(norm(b))).ratio()

def ats_api(info):
    a, b, i = info["ats"], info["board"], info["id"]
    t = time.time()
    if a == "greenhouse":
        r = httpx.get(f"https://boards-api.greenhouse.io/v1/boards/{b}/jobs/{i}", params={"questions": "true"}, timeout=15)
        if r.status_code == 404: return {"is_open": False, "closed_reason": "Greenhouse API 404", "ms": ms(t)}
        j = r.json()
        return {"is_open": True, "title": j.get("title"), "company": j.get("company_name") or b, "location": (j.get("location") or {}).get("name"),
                "posted": j.get("updated_at"), "apply_requires_account": False, "ms": ms(t), "evidence": r.url.__str__(),
                "form_fields": [{"label": q["label"], "required": q["required"], "type": (q.get("fields") or [{}])[0].get("type", "other")} for q in j.get("questions", [])],
                "description_html": j.get("content", "")[:20000]}
    if a == "lever":
        r = httpx.get(f"https://api.lever.co/v0/postings/{b}/{i}", timeout=15)
        if r.status_code == 404: return {"is_open": False, "closed_reason": "Lever API 404", "ms": ms(t)}
        j = r.json()
        return {"is_open": True, "title": j.get("text"), "company": b, "location": (j.get("categories") or {}).get("location"),
                "posted": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(j["createdAt"] / 1000)) if j.get("createdAt") else None, "apply_requires_account": False, "ms": ms(t), "evidence": str(r.url),
                "description_html": (j.get("descriptionPlain") or "")[:20000]}
    if a == "ashby":
        r = httpx.get(f"https://api.ashbyhq.com/posting-api/job-board/{b}", timeout=20)
        for j in r.json().get("jobs", []):
            if i in j.get("jobUrl", ""):
                return {"is_open": True, "title": j.get("title"), "company": b, "location": j.get("location"), "posted": j.get("publishedAt"),
                        "apply_requires_account": False, "ms": ms(t), "evidence": str(r.url), "description_html": (j.get("descriptionPlain") or "")[:20000]}
        return {"is_open": False, "closed_reason": "not on Ashby job board", "ms": ms(t)}
    return None

def ms(t): return int((time.time() - t) * 1000)

def jacc(a, b):
    A, B = set(norm(a)), set(norm(b)); return len(A & B) / max(1, len(A | B))

def via_fetch(url):
    f = tf.fetch([url], ttl=0)
    if not f["results"]:
        return {"is_open": False, "closed_reason": f"fetch error {f['errors'][:1]}", "ms": f["ms"], "uncertain": True}
    x = f["results"][0]; text = x.get("text") or ""
    dead = DEAD.search(text[:4000]); final = x.get("final_url") or url
    title = x.get("title")
    m = re.search(r"^#\s+(.+)$", text, re.M)
    if m: title = m.group(1).strip()
    redirected = urlparse(final).path.rstrip("/") != urlparse(url).path.rstrip("/")
    return {"is_open": not dead, "closed_reason": dead.group(0) if dead else None, "title": title, "ms": f["ms"],
            "evidence": (text[max(0, dead.start() - 80): dead.end() + 80] if dead else text[:240]), "final_url": final,
            "redirected": redirected, "text": text[:20000], "uncertain": (len(text) < 300 and not dead)}

def via_agent(url, on_event=None, goal=TIGHT_GOAL, schema=JOB_SCHEMA, tag="resolve"):
    r = tf.agent(url, goal, schema, on_event=on_event, tag=tag)
    res = r["result"] if isinstance(r["result"], dict) else {}
    return {**res, "ms": r["ms"], "run_id": r["run_id"], "streaming_url": r["streaming_url"], "steps": r["steps"],
            "agent_status": r["status"], "usd_est": r["usd_est"], "raw": r["result"]}

def slug_title(url):
    seg = unquote(urlparse(url).path.rstrip("/").split("/")[-1])
    seg = re.sub(r"_?(JR|R)-?\d+.*$", "", seg)
    if re.fullmatch(r"[0-9a-f-]{20,}|\d+", seg): return None
    return seg.replace("-", " ").strip() if re.search(r"[a-zA-Z]{4}", seg) else None

def validate(obj, schema=JOB_SCHEMA):
    """Minimal check of extracted object against our schema subset; returns list of problems."""
    probs = []
    if not isinstance(obj, dict): return ["result is not an object"]
    for k in schema.get("required", []):
        if k not in obj: probs.append(f"missing {k}")
    for k, s in schema["properties"].items():
        v = obj.get(k)
        if v is None: continue
        t = s.get("type")
        ok = {"boolean": isinstance(v, bool), "string": isinstance(v, str), "array": isinstance(v, list)}.get(t, True)
        if not ok: probs.append(f"{k} wrong type")
    return probs

NULLISH = {"not available", "n/a", "unknown", "none", "null", ""}
def clean(d):
    if not isinstance(d, dict): return d
    return {k: (None if isinstance(v, str) and v.strip().lower() in NULLISH else v) for k, v in d.items()}

def merge(sources, url):
    """sources: list of (tier, dict). Produces per-field value + confidence + evidence with cross-checks."""
    fields, notes = {}, []
    sources = [(t, clean(d)) for t, d in sources]
    for f in ["is_open", "title", "company", "location", "posted"]:
        cands = [(t, d.get(f), d.get("evidence") or d.get("closed_reason")) for t, d in sources if d and d.get(f) not in (None, "")]
        if not cands: fields[f] = {"value": None, "confidence": 0.0, "sources": []}; continue
        cands.sort(key=lambda c: -BASE_CONF.get(c[0], .3))
        best = cands[0]; conf = BASE_CONF.get(best[0], .3)
        for t, v, _ in cands[1:]:
            agree = (v == best[1]) if f == "is_open" else sim(str(v), str(best[1])) > 0.6
            conf = min(0.99, conf + 0.08) if agree else conf - 0.2
            if not agree: notes.append(f"{f}: {best[0]}='{best[1]}' disagrees with {t}='{v}'")
        fields[f] = {"value": best[1], "confidence": round(max(conf, 0.05), 2),
                     "sources": [{"tier": t, "value": v, "evidence": (str(e)[:200] if e else None)} for t, v, e in cands]}
    st = slug_title(url)
    if st and fields["title"]["value"] and jacc(st, fields["title"]["value"]) < 0.34:
        fields["title"]["confidence"] = round(max(0.05, fields["title"]["confidence"] - 0.25), 2)
        notes.append(f"title '{fields['title']['value']}' does not match URL slug '{st}' (possible re-used requisition)")
    return fields, notes

def resolve(url, strategy="tiered", on_event=None, need_form=True):
    """strategy: tiered | agent_only | fetch_only | agent_loose"""
    emit = on_event or (lambda *a, **k: None)
    t0 = time.time(); info = detect(url); trail = []; sources = []
    key = f"{strategy}:{url}"
    c = cache.get("posting", key)
    if c:
        emit("cache", f"cache hit (fresh < {cache.TTL['posting']//3600}h)", {}); c["from_cache"] = True; c["ms"] = ms(t0); return c
    emit("detect", f"ATS = {info['ats']}", info)
    form, agent_meta = None, None
    def step(tier, why, fn):
        emit("tier", f"{tier}: {why}", {"tier": tier})
        try: d = fn()
        except Exception as e:
            d = {"error": str(e)[:200]}; emit("error", f"{tier} failed: {str(e)[:120]}", {})
        trail.append({"tier": tier, "why": why, "ms": d.get("ms"), "ok": "error" not in d}); return d
    if strategy in ("agent_only", "agent_loose"):
        g = TIGHT_GOAL if strategy == "agent_only" else LOOSE_GOAL
        d = step("agent", "ablation: agent for everything", lambda: via_agent(url, lambda ev: emit("agent_event", ev.get("type"), ev), goal=g,
                 schema=JOB_SCHEMA if strategy == "agent_only" else None, tag=strategy))
        sources.append(("agent", d)); agent_meta = d; form = d.get("form_fields")
    elif strategy == "fetch_only":
        d = step("fetch", "ablation: fetch only", lambda: via_fetch(url)); sources.append(("fetch", d))
    else:
        api = None
        if info["ats"] in ("greenhouse", "lever", "ashby"):
            api = step("ats_api", f"{info['ats']} exposes a free public job-board API: cheapest + authoritative", lambda: ats_api(info))
            if api and "error" not in api: sources.append(("ats_api", api)); form = api.get("form_fields")
        if not api or "error" in api:
            fd = step("fetch", "no public API for this ATS -> TinyFish Fetch renders JS and returns clean text (free)", lambda: via_fetch(url))
            sources.append(("fetch", fd))
            closed_sure = fd.get("is_open") is False and not fd.get("uncertain")
            if closed_sure:
                emit("decide", f"Fetch shows dead posting: '{fd.get('closed_reason')}' -> skip Agent, saved ~$0.05 and ~60s", {})
            elif need_form or fd.get("uncertain"):
                why = "Fetch can't read the application form / login gate" if need_form else "Fetch result ambiguous"
                ad = step("agent", f"{why} -> TinyFish Agent with tight goal + output_schema",
                          lambda: via_agent(url, lambda ev: emit("agent_event", ev.get("type"), ev)))
                sources.append(("agent", ad)); agent_meta = ad; form = ad.get("form_fields")
        elif need_form and info["ats"] == "ashby":
            emit("decide", "Ashby API has no question list; form fields deferred to prefill agent", {})
    sources.append(("url", {"title": slug_title(url)}))
    probs = []
    for t, d in sources:
        if t == "agent" and d.get("raw") is not None: probs += [f"agent: {p}" for p in validate(d.get("raw"))]
    fields, notes = merge([s for s in sources if s[0] != "url"], url)
    out = {"url": url, "ats": info, "strategy": strategy, "fields": fields, "notes": notes, "schema_problems": probs,
           "form_fields": form or [], "trail": trail, "ms": ms(t0),
           "agent": {k: agent_meta.get(k) for k in ("run_id", "streaming_url", "steps", "usd_est", "agent_status")} if agent_meta else None,
           "description": next((d.get("description_html") or d.get("text") for t, d in sources if d and (d.get("description_html") or d.get("text"))), "")[:20000],
           "apply_requires_account": next((d.get("apply_requires_account") for t, d in sources if d and d.get("apply_requires_account") is not None), None)}
    for n in notes: emit("crosscheck", n, {})
    emit("done", f"resolved in {out['ms']} ms; is_open={fields['is_open']['value']} (conf {fields['is_open']['confidence']})", {})
    if all(x["ok"] for x in trail): cache.put("posting", key, out)
    return out
