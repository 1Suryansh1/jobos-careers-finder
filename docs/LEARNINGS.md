# Learnings from ApplyOS and job-market-intel

Both were studied on 2026-10-14.

## ApplyOS (https://www.applyos.io/)
**What it is:** a hosted "AI operating system for your job search". It is a closed product, so we studied only its public site. It does not discover jobs. It starts from a posting the user brings, either pasted or captured with its one-click browser extension.

**Features and UX flow:** the flow is *grab posting → extract questions → grounded answers → pipeline → deadlines → interview prep*.
- Grab a posting with one click from the job tab: company, requirements and questions are extracted.
- AI answers that are "grounded in your resume, never invented".
- A pipeline board: Draft → Submitted → In review → Interview → Offer.
- Resume keyword match ("which keywords are missing before the bots filter you out").
- Deadline emails at 7, 3 and 1 days.
- A voice mock interviewer, and company question banks.
- Resume/transcript parsing that is reused everywhere.
- Row-level data isolation.

**Adopted (first principles: a finder is only useful if you can act on its results):**
1. **A tracker after discovery.** Each listing has Save, and a Tracker tab with columns saved → applied → interview → offer → rejected, stored locally in SQLite. Statuses are set by the user, so nothing is auto-submitted.
2. **Missing-keyword view per job.** Each card shows skill chips: mint for skills you have, peach for skills you're missing. "Skills to brush up" also appears in *Why this match*.
3. **Grounded, never invented** is already our rule for the optional Gemini explanation. It is cached, and the deterministic matcher stays primary.

**Skipped, and why:** answer drafting at scale and auto-apply flows (the brief is about finding, and our rule is never submit). Voice interviews and email reminders (out of scope, plus a mail dependency). The browser extension (we fetch at the source with TinyFish instead).

## job-market-intel (https://github.com/shikhar818/job-market-intel), MIT License, © 2026 Shikhar
**What it is:** an open-source analytics pipeline for India and remote data roles.
- `python-jobspy` scrapes Indeed and LinkedIn (last 72 h).
- Data lands in MySQL `raw_jobs`, with `UNIQUE(source, job_id)`, salary min/max, `geo_target` and `posted_date`.
- dbt staging and marts: `skill_demand`, `hiring_heatmap` (city × role × month), `role_overlap` and `tool_frequency`.
- KeyBERT skill extraction.
- KMeans role clustering.
- A sentence-transformer resume↔JD match plus `skill_gap()` (top demanded skills not in your resume).
- An Ollama career advisor.
- A Streamlit dashboard, scheduled by Airflow at 08:00 IST.

**Adopted (ideas, re-implemented; no code copied):**
1. **Market pulse:** skill-demand counts and a city "heatmap" over your matched listings, plus the top hiring companies. These follow the `skill_demand` and `hiring_heatmap` marts (`backend/insights.py`).
2. **Skill gap:** the most demanded skills that are not in "Your skills", following `skill_gap()`.
3. **Freshness window:** "Posted within 7/14/30 days", following `HOURS_OLD`. The posted date is normalised from ISO dates, epoch ms and Workday's "Posted N Days Ago".
4. **Data model:** a `(source, job_id)`-style unique identity. Ours is stronger because it works *across* sources: `gh:<id>` / Lever-Ashby UUID / Workday `JR` id, plus a canonical company|title|city key. We also store `first_seen` / `last_verified` and the skills per listing.

**Skipped, and why:**
- **jobspy against LinkedIn/Indeed/Naukri:** their ToS or robots.txt forbid automated access. We use public ATS APIs plus TinyFish on robots-allowed pages instead.
- **Airflow, dbt and MySQL:** too heavy for a personal tool. SQLite plus an in-process 3 h scheduler is enough.
- **KeyBERT and sentence-transformers:** large model downloads and slower. A deterministic dictionary is explainable and cheap. Embeddings are left as future work.
- **Ollama:** we already have optional, cached Gemini.

Attribution is also noted in `backend/insights.py` and the README.
