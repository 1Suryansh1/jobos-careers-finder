"""Live sources. ToS/robots checked 2026-10-14:
 - Greenhouse/Lever/Ashby job-board APIs: public, documented for embedding job listings.
 - Google Careers results page: robots.txt allows /about/careers/applications/jobs/results (only ?page= is disallowed) -> TinyFish Fetch, page 1 only.
 - Workday tenant sites (*.myworkdayjobs.com): robots.txt 'User-agent: *' with no Disallow -> TinyFish Agent (JS SPA + filters).
 - EXCLUDED: Naukri (robots Disallow: /), Internshala (Disallow: /), LinkedIn/Wellfound (ToS forbid automated access)."""
import re, time, httpx
from concurrent.futures import ThreadPoolExecutor
from . import tf, cache

BOARDS = {  # company boards with India and/or intern roles (probed live)
 "greenhouse": ["groww", "druva", "rubrik", "databricks", "stripe", "mongodb", "gitlab", "zscaler", "inmobi", "coinbase", "okta", "cloudflare"],
 "lever": ["meesho", "zeta", "paytm", "fampay", "cred"],
 "ashby": ["sarvam", "atlan", "openai", "perplexity", "notion"]}
WORKDAY = [  # (company, url) agent applies keyword + India filter
 ("NVIDIA", "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"),
 ("Walmart Global Tech", "https://walmart.wd5.myworkdayjobs.com/WalmartExternal")]

def L(**k): return {"type": "", "posted": None, "desc": "", **k}

def greenhouse(b):
    j = httpx.get(f"https://boards-api.greenhouse.io/v1/boards/{b}/jobs", params={"content": "true"}, timeout=25).json()
    return [L(title=x["title"], company=b, location=x["location"]["name"], url=x["absolute_url"], posted=x.get("updated_at"),
              desc=re.sub(r"<[^>]+>", " ", re.sub(r"&lt;|&gt;", " ", x.get("content", "")))[:3000], ats="greenhouse") for x in j.get("jobs", [])]
def lever(b):
    j = httpx.get(f"https://api.lever.co/v0/postings/{b}", params={"mode": "json"}, timeout=25).json()
    return [L(title=x["text"], company=b, location=(x.get("categories") or {}).get("location") or "", url=x["hostedUrl"],
              type=(x.get("categories") or {}).get("commitment") or "", posted=time.strftime("%Y-%m-%d", time.gmtime(x["createdAt"] / 1000)),
              desc=(x.get("descriptionPlain") or "")[:3000], ats="lever") for x in j]
def ashby(b):
    j = httpx.get(f"https://api.ashbyhq.com/posting-api/job-board/{b}", timeout=25).json()
    out = []
    for x in j.get("jobs", []):
        locs = [x.get("location") or ""] + [s.get("location", "") for s in x.get("secondaryLocations") or []]
        out.append(L(title=x["title"], company=b, location="; ".join(l for l in locs if l), url=x["jobUrl"], type=x.get("employmentType") or "",
                     remote=(x.get("workplaceType") or "").lower() == "remote" or "remote" in (x.get("location") or "").lower(), posted=(x.get("publishedAt") or "")[:10], desc=(x.get("descriptionPlain") or "")[:3000], ats="ashby"))
    return out
API = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby}

def boards(on=None):
    tasks = [(a, b) for a, bs in BOARDS.items() for b in bs]
    def one(t):
        a, b = t; s = time.time()
        try: r = API[a](b)
        except Exception as e: r = []; on and on("error", f"{a}/{b}: {str(e)[:80]}")
        on and on("board", f"{a}/{b}: {len(r)} openings ({int((time.time()-s)*1000)} ms)"); return r
    with ThreadPoolExecutor(10) as ex: return [x for l in ex.map(one, tasks) for x in l]

JOB_URL = re.compile(r"(greenhouse\.io/[^/]+/jobs/\d+|jobs\.lever\.co/[^/]+/[0-9a-f-]{36}|jobs\.ashbyhq\.com/[^/]+/[0-9a-f-]{36}|myworkdayjobs\.com/.+/job/|google\.com/about/careers/applications/jobs/results/\d+)")
def search(prefs, on=None):
    """TinyFish Search = discovery of postings on boards we DON'T already crawl (long tail)."""
    from .finder import queries
    phr = queries(prefs.get("role", ""), prefs.get("job_type") == "internship")
    locs = [l for l in prefs.get("locations", []) if l.lower() != "remote"][:1] or ["India"]
    qs = [f"site:{d} {ph} {locs[0]}" for d in ("job-boards.greenhouse.io", "jobs.lever.co", "jobs.ashbyhq.com", "myworkdayjobs.com") for ph in phr]
    if "remote" in [l.lower() for l in prefs.get("locations", [])]: qs.append(f"site:jobs.ashbyhq.com {phr[0]} remote")
    def one(q):
        c = cache.get("search", "q:" + q)
        if c is not None: on and on("search", f"Search '{q}': {len(c)} hits (cache <30 min)"); return c
        try: r = tf.search(q)
        except Exception as e: on and on("error", f"search: {e}"); return []
        on and on("search", f"Search '{q}': {len(r['results'])} hits in {r['ms']} ms")
        return [L(title=re.sub(r"^Job Application for | at .*$| - Myworkdayjobs.com$", "", x.get("title") or ""), company="", location="",
                  url=x["url"].replace("http://", "https://"), desc=x.get("snippet") or "", ats="search", needs_verify=True)
                for x in r["results"] if JOB_URL.search(x.get("url", ""))]
    def one_c(q):
        r = one(q); cache.put("search", "q:" + q, r); return r
    with ThreadPoolExecutor(5) as ex: return [dict(x) for l in ex.map(one_c, qs) for x in l]

def google_careers(prefs, on=None):
    """TinyFish Fetch reads a JS careers page with no API (Google Careers)."""
    from .finder import queries
    loc = next((l for l in prefs.get("locations", []) if l.lower() != "remote"), "India")
    urls = [f"https://www.google.com/about/careers/applications/jobs/results?q={q}&location={loc}" for q in queries(prefs.get("role", ""), prefs.get("job_type") == "internship")]
    f = tf.fetch(urls, links=True, ttl=0)
    if not f["results"]: on and on("error", f"fetch google: {f['errors']}"); return []
    out = []
    for x in f["results"]: out += _google_parse(x, x.get("url"))
    on and on("fetch", f"Fetch read Google Careers ({len(out)} openings from {len(urls)} pages, {f['ms']} ms) - JS page, no public API")
    return out

def _google_parse(x, url):
    text = x.get("text") or ""
    links = [l.replace("/jobs/jobs/", "/jobs/").split("?")[0] for l in (x.get("links") or []) if re.search(r"/jobs/results/\d+", str(l))]
    out = []
    for i, blk in enumerate(re.split(r"\n\* ### ", "\n" + text)[1:]):
        title = blk.split("\n")[0].strip()
        m = re.search(r"Google \| ([^\n]+)", blk); loc_ = m.group(1).replace("; +", " +") if m else ""
        lvl = "Intern" if "Intern & Apprentice" in blk else ""
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        link = next((l for l in links if slug[:25] in l), links[i] if i < len(links) else url)
        out.append(L(title=title, company="Google", location=loc_, url=link, type=lvl, desc=blk[:1500], ats="google_careers"))
    return out

WD_SCHEMA = {"type": "object", "properties": {"total_results_text": {"type": "string", "nullable": True}, "jobs": {"type": "array", "maxItems": 20,
    "items": {"type": "object", "properties": {"title": {"type": "string"}, "location": {"type": "string"}, "posted": {"type": "string", "nullable": True},
    "url": {"type": "string"}}, "required": ["title", "url"]}}}, "required": ["jobs"]}
def workday(company, url, prefs, on=None, on_live=None):
    """TinyFish Agent: Workday is a JS SPA; filtering by keyword + country needs clicks."""
    from .finder import queries
    kw = "intern" if prefs.get("job_type") == "internship" else queries(prefs.get("role", ""), False)[0]
    loc = next((l for l in prefs.get("locations", []) if l.lower() != "remote"), "India")
    url = f"{url}?q={kw} {loc}"
    goal = (f"This Workday careers page already shows search results for '{kw} {loc}'. Wait for the job list to load. "
            f"Keep only cards whose location is in {loc} (or Remote). "
            "For each kept card extract title, location, posted text and the job link exactly as the card's href attribute (never construct or guess a URL; omit the job if you cannot read its link). "
            "Do not click into jobs, do not apply, do not sign in. Return JSON.")
    def ev(e):
        if e.get("type") == "STREAMING_URL" and on_live: on_live(company, e["streaming_url"])
        if e.get("type") == "PROGRESS" and on: on("agent", f"{company}: {e.get('purpose')}")
    r = tf.agent(url, goal, WD_SCHEMA, on_event=ev, tag="workday_filter", max_duration=150)
    res = r["result"] if isinstance(r["result"], dict) else {}
    base = re.match(r"https://[^/]+/[^/?]+", url).group(0)
    jobs = [L(title=j["title"], company=company, location=j.get("location") or "", posted=j.get("posted"),
              url=(j["url"] if j["url"].startswith("http") else base + j["url"] if j["url"].startswith("/job") else re.match(r"https://[^/]+", base).group(0) + j["url"]), ats="workday", run_id=r["run_id"]) for j in res.get("jobs", [])]
    on and on("agent", f"{company}: Agent applied filters -> {len(jobs)} openings in {r['ms']//1000}s, {len(r['steps'])} steps (~${r['usd_est']})")
    return jobs, r
