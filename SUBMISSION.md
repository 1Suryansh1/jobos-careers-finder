# JobOS Careers Finder: TinyFish × DTU

**What it is:** a job and internship finder built for a DTU student. You set your role, locations, keywords, seniority, visa needs and internship vs full-time. JobOS then pulls live openings from 22 company job boards, Google Careers, Workday portals (NVIDIA, Walmart) and TinyFish Search across ATS sites. It deduplicates them, checks each link is live, ranks them with an explainable matcher, and keeps the list fresh.

| Requirement | How it is met |
|---|---|
| 1. Working demo | `./start.sh` then open http://localhost:8300 |
| 2. User preferences | Preferences panel: role, locations, keywords, exclude, type, seniority, visa sponsorship |
| 3. Multiple live sources | Greenhouse/Lever/Ashby boards (Groww, Meesho, Paytm, Zeta, FamPay, Sarvam, Rubrik, Stripe, …), Google Careers (Fetch), Workday portals (Agent), long-tail ATS postings (Search). Naukri and Internshala are excluded because their robots.txt disallows crawling |
| 4. Structured, deduplicated listings with apply links | Cross-source identity (gh_jid, Lever/Ashby UUID, Workday JR id) plus a canonical company+title+city key. Merged sources are shown per card. Export to CSV/JSON |
| 5. TinyFish usage | See below |

**How TinyFish is used (each endpoint has a distinct job)**
- **Search (discover):** about 9 parallel `site:` queries across Greenhouse, Lever, Ashby and Workday surface postings from companies we don't crawl directly.
- **Fetch (read and verify):** reads Google Careers, a JavaScript page with no public API. It also batch-verifies up to 10 URLs per call with `ttl=0`. Dead pages ("doesn't exist", redirects) and Agent links whose page title doesn't match are removed.
- **Agent (JS portals plus filters):** Workday sites are single-page apps. The Agent types the keyword, applies the India location filter and returns cards through `output_schema`. Its live browser is embedded in the UI, and results are cached for 24 h to keep spend low.

**Freshness:** a Refresh button re-checks every saved listing. Listings carry a "New since last run" badge, and a background loop re-runs your last search every 3 h (`REFRESH_MINUTES`).

**Demo script:**
1. Set "ML / SWE", "India, Remote", Internship, then click Find.
2. Watch the progress steps and live Workday browsers. Results are ready in about 30 s and the Agent merges in later.
3. Open "Why this match" on a card.
4. Click Export CSV.
5. Click Refresh to re-verify liveness.

**Safety:** form prefill is off by default (`ENABLE_PREFILL=1` turns it on). It never submits: a submit guard cancels the run and no resume is attached.
