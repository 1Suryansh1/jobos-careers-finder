# JobOS Careers Finder: TinyFish × DTU

**What it is:** a job and internship finder for a DTU student.
- You set role, locations, keywords, your skills, seniority, visa sponsorship, internship vs full-time, and how recently the job was posted.
- JobOS pulls live openings from 22 company job boards, Google Careers, NVIDIA and Walmart Workday, and TinyFish Search across ATS sites.
- It deduplicates them, checks every link is live, ranks them with an explainable matcher, shows a market pulse with your skill gap, and lets you track applications.

| Requirement | How it is met |
|---|---|
| 1. Working demo | `./start.sh`, then open http://localhost:8300 |
| 2. User preferences | Preferences panel: role, locations, keywords, your skills, exclude, type, posted-within, seniority, visa sponsorship |
| 3. Multiple live sources | Greenhouse/Lever/Ashby boards (Groww, Meesho, Paytm, Zeta, FamPay, Sarvam, Rubrik, Stripe, …), Google Careers (Fetch), NVIDIA and Walmart Workday (Search + Fetch, Agent filter), long-tail ATS postings (Search). Naukri and Internshala are excluded because their robots.txt disallows crawling. LinkedIn and Wellfound are excluded because of their terms of service |
| 4. Structured, deduplicated listings with apply links | Cross-source identity (gh_jid, Lever/Ashby UUID, Workday tenant + JR id) plus a company + title + city key. Each card shows every source it was found on. Export to CSV or JSON |
| 5. TinyFish usage | See below |

**How TinyFish is used (each endpoint has a distinct job)**
- **Search (discover):**
  - `site:` queries across Greenhouse, Lever, Ashby and Workday find postings from companies we don't crawl directly.
  - Per-tenant queries (`site:nvidia.wd5.myworkdayjobs.com …`, `Walmart Global Tech … myworkdayjobs`) find individual Workday postings without spending on the Agent.
- **Fetch (read and verify):**
  - Reads Google Careers, a JavaScript page with no public API.
  - Verifies up to 10 URLs per call with `ttl=0`. Dead pages and redirects are dropped. Thin or empty pages, common on Workday, are re-checked once.
  - Reads the location from the page when the search snippet doesn't give one.
- **Agent (filtering only):**
  - On each Workday portal, the Agent opens the keyword search and keeps only cards in your location. It returns them through `output_schema` and its live browser is shown in the UI.
  - It must copy each card's real link. Every Agent link is then Fetch-verified and title-checked, and links that can't be verified are dropped.
  - Results are cached for 24 h.
  - **Debugged from step screenshots:** NVIDIA's free-text query "intern India" matched 0 jobs, and Walmart's portal is on `wd504`, not `wd5` (wd5 showed a maintenance page). Both are fixed.

**Freshness:** Refresh re-checks every saved listing. Cards show a "New since last run" badge, and the last search re-runs every 3 h (`REFRESH_MINUTES`).

**Ideas borrowed from other projects** (`docs/LEARNINGS.md`): the market pulse, skill gap and posted-within filter come from shikhar818/job-market-intel (MIT), re-implemented without copying code. The application tracker and missing-skill chips come from ApplyOS.

**Demo script:**
1. Set "ML / SWE", "India, Remote", Internship, with your skills, then click Find.
2. Fast results arrive in about 60–80 s, and Workday Agent results merge in afterwards.
3. Read the Market pulse and skill gap, then open "Why this match" on a card.
4. Save a few roles and open the Tracker tab.
5. Click Export CSV, then Refresh.

**Safety:** form prefill is off by default (`ENABLE_PREFILL=1` turns it on). It never submits: a submit guard cancels the run and no resume is attached.
