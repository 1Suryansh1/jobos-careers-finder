"""Careers finder: collect (APIs + TinyFish Search/Fetch/Agent) -> normalise -> deterministic match -> dedupe -> verify liveness -> store."""
import re, json, time, sqlite3, os, hashlib, threading
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from . import tf, sources as S, cache
from .resolve import DEAD
from . import insights as I

DB = os.path.join(os.path.dirname(__file__), "..", "data", "listings.db")
_l = threading.Lock()
def db():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.execute("create table if not exists listing(key text primary key, data text, first_seen real, last_seen real, last_verified real, live int)")
    c.execute("create table if not exists run(id text primary key, prefs text, ts real, stats text)")
    return c

INDIA = ["india", "bengaluru", "bangalore", "gurugram", "gurgaon", "noida", "delhi", "new delhi", "mumbai", "hyderabad", "pune", "chennai", "kolkata", "ahmedabad"]
CITY = {"bangalore": "bengaluru", "gurgaon": "gurugram", "new delhi": "delhi", "bombay": "mumbai"}
SYN = {"ml": ["machine learning", "ml", "ai", "deep learning", "data scien", "applied scien", "research engineer", "llm", "computer vision", "nlp"],
       "swe": ["software", "swe", "sde", "developer", "backend", "frontend", "full stack", "fullstack", "engineer"],
       "data": ["data", "analytics", "analyst"], "product": ["product"], "design": ["design"]}
INTERN = re.compile(r"\b(intern|internship|apprentice|trainee|co-?op|summer 20\d\d)\b", re.I)
SENIOR = re.compile(r"\b(senior|sr\.?|staff|principal|lead|manager|director|head|vp|architect|ii+|iv)\b", re.I)
ENTRY = re.compile(r"\b(new grad|graduate|junior|jr\.?|entry|associate|fresher|early career|university|campus|i)\b", re.I)
NOSPONSOR = re.compile(r"(not (be )?able to sponsor|unable to sponsor|no (visa )?sponsorship|must be (legally )?authori[sz]ed to work|without (the need for )?sponsorship)", re.I)

def norm_url(u):
    p = urlparse(u.strip()); h = p.netloc.lower().replace("boards.greenhouse.io", "job-boards.greenhouse.io")
    path = re.sub(r"/(en-US|en-us|en)/", "/", p.path).rstrip("/")
    q = re.search(r"(gh_jid=\d+)", p.query)
    return f"https://{h}{path}" + (f"?{q.group(1)}" if q else "")
def ident(u):
    """Cross-source identity: same requisition on a custom careers domain and on the ATS host collapse to one id."""
    m = re.search(r"gh_jid=(\d+)", u) or re.search(r"greenhouse\.io/[^/]+/jobs/(\d+)", u)
    if m: return "gh:" + m.group(1)
    m = re.search(r"(?:lever\.co|ashbyhq\.com)/[^/]+/([0-9a-f-]{36})", u)
    if m: return "id:" + m.group(1)
    m = re.search(r"myworkdayjobs\.com/.*_((?:JR|R|P)-?[\w-]+?)(?:\?|$|/)", u)
    if m: return "wd:" + urlparse(u).netloc.split(".")[0] + ":" + m.group(1)
    return norm_url(u)

PRETTY = {"gitlab": "GitLab", "mongodb": "MongoDB", "openai": "OpenAI", "inmobi": "InMobi", "fampay": "FamPay", "cred": "CRED", "nvidia": "NVIDIA",
          "merklescience": "Merkle Science", "interview-kickstart": "Interview Kickstart", "arcesiumllc": "Arcesium", "optiverus": "Optiver", "ag": "Airbus"}
def pretty(c):
    c = c or ""; return PRETTY.get(c.lower(), c if (c[:1].isupper() or " " in c) else re.sub(r"[-_]+", " ", c).title())

def company_of(l):
    if l.get("company"): return pretty(l["company"])
    p = urlparse(l["url"]); parts = [x for x in p.path.split("/") if x]
    if "myworkdayjobs" in p.netloc: return pretty(p.netloc.split(".")[0])
    return pretty(parts[0] if parts else p.netloc)
def canon(s): return " ".join(re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split())
def canon_title(t): return re.sub(r"\b(20\d\d|summer|winter|fall|spring|remote|hybrid|india|bengaluru|bangalore)\b", "", canon(t)).split().__str__()
def city(loc):
    c = canon(loc)
    for k, v in CITY.items(): c = c.replace(k, v)
    for x in INDIA[1:] + ["remote"]:
        if x in c: return x
    return c.split(" ")[0] if c else ""
def dkey(l): return hashlib.md5(f"{canon(l['company'])}|{canon_title(l['title'])}|{city(l['location'])}".encode()).hexdigest()[:12]

def classify(l):
    t = l["title"]; blob = f"{t} {l.get('type','')}"
    l["job_type"] = "internship" if INTERN.search(blob) or "intern" in (l.get("type") or "").lower() else "full-time"
    l["seniority"] = "intern" if l["job_type"] == "internship" else "senior" if SENIOR.search(t) else "entry" if ENTRY.search(t) else "mid"
    loc = (l.get("location") or "").lower()
    l["in_india"] = any(c in loc for c in INDIA); l["remote"] = bool(l.get("remote")) or "remote" in loc or "anywhere" in loc
    return l

def role_terms(role):
    terms = []
    for w in canon(role).replace("/", " ").split():
        terms += SYN.get(w, [w])
    return [t for t in terms if t not in ("intern", "internship")] or ["engineer"]

def queries(role, intern):
    """Turn 'ML / SWE' into concrete search phrases."""
    out = []
    for w in canon(role).replace("/", " ").split():
        out.append({"ml": "machine learning", "swe": "software engineer", "sde": "software engineer", "ai": "AI"}.get(w, w))
    out = list(dict.fromkeys(out)) or ["software engineer"]
    return [f"{o} intern" if intern else o for o in out][:2]

def match(l, p):
    """Deterministic, explainable. Returns (score, reasons) or (None, reason_excluded)."""
    t = l["title"].lower(); d = (l.get("desc") or "").lower(); why = []
    jt = p.get("job_type", "both")
    if jt != "both" and l["job_type"] != jt: return None, f"type {l['job_type']} != {jt}"
    sen = p.get("seniority") or []
    if sen and l["seniority"] not in sen: return None, f"seniority {l['seniority']} not in {sen}"
    locs = [x.lower() for x in p.get("locations", [])]; loc_ok = False
    if "remote" in locs and l["remote"]: loc_ok = True; why.append(("+20", "remote role"))
    if any(x in ("india",) for x in locs) and l["in_india"]: loc_ok = True; why.append(("+25", f"in India ({l['location'][:40]})"))
    for x in locs:
        if x not in ("india", "remote") and city(x) and city(x) in city(l["location"]) + canon(l["location"]): loc_ok = True; why.append(("+25", f"in {x}"))
    if locs and not loc_ok and l.get("needs_verify"):
        blob = f"{l['title']} {l.get('desc','')}".lower()
        if any(c in blob for c in INDIA) and "india" in locs: loc_ok = True; l["in_india"] = True; why.append(("+25", "India (from search snippet)"))
        elif "remote" in blob and "remote" in locs: loc_ok = True; l["remote"] = True; why.append(("+20", "remote (from snippet)"))
        else: loc_ok = "unknown"; why.append(("+0", "location to be confirmed by Fetch"))
    if locs and not loc_ok: return None, "location"
    terms = role_terms(p.get("role", "")); hit = [x for x in terms if re.search(r"\b" + re.escape(x), t)]
    if not hit: return None, "role not in title"
    score = 40 + 5 * min(3, len(hit)); why.insert(0, (f"+{40+5*min(3,len(hit))}", f"title matches {', '.join(hit[:3])}"))
    for k in p.get("keywords", []):
        if k.lower() in t or k.lower() in d: score += 5; why.append(("+5", f"mentions '{k}'"))
    for k in p.get("exclude", []):
        if k.lower() in t: return None, f"excluded '{k}'"
    win = p.get("posted_within_days")
    pdays = I.posted_days(l.get("posted"))
    if win and pdays is not None and pdays > win: return None, f"posted {int(pdays)}d ago > {win}d"
    l["posted_days"] = None if pdays is None else int(pdays)
    l["skills"] = I.skills_in(f"{l['title']} {l.get('desc','')}")
    mine = {k.lower() for k in p.get("my_skills", [])}
    have = [k for k in l["skills"] if k in mine]; l["missing"] = [k for k in l["skills"] if k not in mine][:6]
    if have: score += min(15, 3 * len(have)); why.append((f"+{min(15,3*len(have))}", f"you have {', '.join(have[:5])}"))
    if l["missing"] and mine: why.append(("+0", f"skills to brush up: {', '.join(l['missing'][:4])}"))
    score += 25 if loc_ok else 0
    if l["job_type"] == "internship" and jt == "internship": score += 10; why.append(("+10", "internship"))
    if p.get("needs_sponsorship") and not l["in_india"] and not l["remote"]:
        if NOSPONSOR.search(d): return None, "says no visa sponsorship"
        score -= 10; why.append(("-10", "outside India: sponsorship not confirmed"))
    return min(100, score), why

def collect(p, on, on_live, use_agent=True):
    jobs = []
    with ThreadPoolExecutor(4) as ex:
        fb = ex.submit(lambda: cache.get("search", "boards") or (lambda r: (cache.put("search", "boards", r), r)[1])(S.boards(on)))
        fs = ex.submit(S.search, p, on)
        fg = ex.submit(S.google_careers, p, on)
        fw = []
        if use_agent:
            for co, url in S.WORKDAY:
                k = f"wd:{co}:{p.get('job_type')}:{p.get('role')}"
                def wd(co=co, url=url, k=k):
                    c = cache.get("form", k)
                    if c is not None: on("agent", f"{co}: Workday agent result from cache (<24h) - no spend"); return c
                    try: r, _ = S.workday(co, url, p, on, on_live)
                    except Exception as e: on("error", f"{co} agent: {str(e)[:100]}"); return []
                    cache.put("form", k, r); return r
                fw.append(ex.submit(wd))
        parts = {"boards (ATS APIs)": [dict(x) for x in fb.result()], "TinyFish Search": fs.result(), "TinyFish Fetch: Google Careers": fg.result()}
        parts["TinyFish Agent: Workday"] = [x for f in fw for x in f.result()]
    for src, l in parts.items():
        for x in l: x["source"] = src; jobs.append(x)
    return jobs, {k: len(v) for k, v in parts.items()}

def verify(listings, on):
    """TinyFish Fetch, 10 URLs per call (documented max), ttl=0: dead-page phrases or redirects => not live."""
    urls = [l["url"] for l in listings]; res = {}
    def batch(b):
        try: f = tf.fetch(b, ttl=0)
        except Exception as e: return {u: (None, str(e)[:60]) for u in b}
        out = {}
        for x in f["results"]:
            t = (x.get("text") or "")[:5000]; m = DEAD.search(t)
            fu = norm_url(x.get("final_url") or x["url"]); moved = fu != norm_url(x["url"]) and "/job" not in fu
            out[x["url"]] = (not m and not moved and len(t) > 200, (m.group(0) if m else "redirected to listing page" if moved else "live page") , x.get("title"), t)
        for e in f["errors"]: out[e["url"]] = (None, e.get("error"), None, "")
        return out
    with ThreadPoolExecutor(3) as ex:
        for o in ex.map(batch, [urls[i:i + 10] for i in range(0, len(urls), 10)]): res.update(o)
    on("fetch", f"Fetch verified {len(urls)} non-API listings in {max(1,(len(urls)+9)//10)} batch calls")
    return res

def last_run_ts(): return db().execute("select max(ts) from run").fetchone()[0] or 0

def run(p, on, on_live, use_agent=True, max_verify=60, prev=None):
    t0 = time.time(); prev = last_run_ts() if prev is None else prev
    raw, per_src = collect(p, on, on_live, use_agent)
    on("plan", f"Collected {len(raw)} raw openings: " + ", ".join(f"{k} {v}" for k, v in per_src.items()))
    # search hits: fill company from URL, drop ones already covered by our board crawl via URL-normalised identity
    for x in raw: x["company"] = company_of(x); x["nurl"] = ident(x["url"]); classify(x)
    seen_url = {}
    url_dupes = 0
    for x in raw:
        if x["nurl"] in seen_url: seen_url[x["nurl"]]["sources"].add(x["source"]); url_dupes += 1; continue
        x["sources"] = {x["source"]}; seen_url[x["nurl"]] = x
    uniq = list(seen_url.values())
    matched, excluded = [], {}
    for x in uniq:
        s, why = match(x, p)
        if s is None: excluded[why.split(" ")[0]] = excluded.get(why.split(" ")[0], 0) + 1; continue
        x["score"], x["why"] = s, why; matched.append(x)
    merged = {}; key_dupes = 0
    for x in sorted(matched, key=lambda x: (x["source"] != "boards (ATS APIs)", -x["score"])):
        k = dkey(x)
        if k in merged:
            m = merged[k]; m["sources"] |= x["sources"]; m.setdefault("alt_urls", []).append(x["url"]); key_dupes += 1; continue
        x["key"] = k; merged[k] = x
    out = list(merged.values())
    need = sorted([x for x in out if x["source"] not in ("boards (ATS APIs)", "TinyFish Fetch: Google Careers")],
                  key=lambda x: x["source"] != "TinyFish Agent: Workday")[:max_verify]   # agent output verified first (anti-hallucination)
    v = verify(need, on) if need else {}
    now = time.time(); c = db()
    for x in out:
        vv = v.get(x["url"])
        if x["source"] in ("boards (ATS APIs)", "TinyFish Fetch: Google Careers"): x["live"], x["live_evidence"] = True, "listed on live board just now"
        elif vv:
            x["live"], x["live_evidence"] = vv[0], vv[1]
            if x["source"] == "TinyFish Agent: Workday" and vv[0] and vv[3]:
                words = [w for w in canon(x["title"]).split() if len(w) > 3][:3]
                if words and not all(w in canon(vv[3]) for w in words):
                    x["live"], x["live_evidence"] = False, "Fetch: page title differs from agent-extracted title (link rejected)"
                else: x["live_evidence"] = "Agent found it on the portal; Fetch confirmed the page"
        elif x["source"] == "TinyFish Agent: Workday": x["live"], x["live_evidence"] = False, "agent link not verifiable"
        else: x["live"], x["live_evidence"] = None, "not verified (cap)"
        if loc_unknown(x) and vv and vv[3]:
            t = vv[3].lower(); locs = [q.lower() for q in p.get("locations", [])]
            okk = ("india" in locs and any(c in t for c in INDIA)) or ("remote" in locs and "remote" in t)
            if not okk: x["live"], x["live_evidence"] = False, "Fetch: page does not mention preferred location"
            else: x["location"] = next((c.title() for c in INDIA[1:] if c in t), "India" if "india" in t else "Remote")
        if x["live"] and x["source"] == "TinyFish Search" and vv and vv[2]: x["title"] = re.sub(r"^Job Application for | at [^|]+$", "", vv[2]).strip() or x["title"]
        row = c.execute("select first_seen from listing where key=?", (x["key"],)).fetchone()
        x["first_seen"] = row[0] if row else now; x["new"] = (not row) or x["first_seen"] > prev
        x["last_verified"] = now; x["sources"] = sorted(x["sources"]); x.pop("desc", None); x["city"] = city(x.get("location") or "")
        c.execute("replace into listing values(?,?,?,?,?,?)", (x["key"], json.dumps(x), x["first_seen"], now, now, int(bool(x["live"]))))
    out = [x for x in out if x["live"] is not False]
    dead = len(merged) - len(out)
    out.sort(key=lambda x: (-x["score"], not x["new"]))
    stats = {"raw": len(raw), "per_source": per_src, "url_duplicates": url_dupes, "after_url_dedupe": len(uniq), "matched": len(matched),
             "excluded": excluded, "canonical_duplicates": key_dupes, "final": len(out), "dead_filtered": dead,
             "new_since_last_run": sum(x["new"] for x in out), "pulse": I.pulse(out, p.get("my_skills", [])), "multi_source": sum(len(x["sources"]) > 1 for x in out), "seconds": round(time.time() - t0, 1)}
    rid = hashlib.md5(str(now).encode()).hexdigest()[:8]
    c.execute("insert into run values(?,?,?,?)", (rid, json.dumps(p), now, json.dumps(stats))); c.commit()
    return out, stats

def loc_unknown(x): return any(w[1].startswith("location to be confirmed") for w in x.get("why", []))

def refresh(on):
    """Re-check liveness of all stored live listings (boards re-crawled via API; others via Fetch)."""
    c = db(); rows = [json.loads(r[0]) for r in c.execute("select data from listing where live=1")]
    cache.put("search", "boards", None)
    board = {norm_url(x["url"]) for x in S.boards(on)}
    other = [x for x in rows if x["source"] != "boards (ATS APIs)"]
    v = verify(other, on) if other else {}
    now = time.time(); closed = 0
    for x in rows:
        live = norm_url(x["url"]) in board if x["source"] == "boards (ATS APIs)" else (v.get(x["url"], (True,))[0] is not False)
        if not live: closed += 1
        x["live"] = live; x["last_verified"] = now
        c.execute("update listing set data=?, last_verified=?, live=? where key=?", (json.dumps(x), now, int(live), x["key"]))
    c.commit(); return {"checked": len(rows), "closed": closed}

STATUSES = ["saved", "applied", "interview", "offer", "rejected"]
def track_set(key, status, item=None):
    c = db(); c.execute("create table if not exists track(key text primary key, status text, ts real, data text)")
    if status == "remove": c.execute("delete from track where key=?", (key,))
    else:
        row = c.execute("select data from track where key=?", (key,)).fetchone()
        data = json.dumps(item) if item else (row[0] if row else "{}")
        c.execute("replace into track values(?,?,?,?)", (key, status, time.time(), data))
    c.commit()
def track_all():
    c = db(); c.execute("create table if not exists track(key text primary key, status text, ts real, data text)")
    return [dict(json.loads(d), key=k, status=s, status_ts=t) for k, s, t, d in c.execute("select key,status,ts,data from track order by ts desc")]
