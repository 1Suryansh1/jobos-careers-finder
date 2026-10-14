import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend import finder as F
P = dict(role="ML / SWE", locations=["India", "Remote"], keywords=["python"], exclude=["sales"], seniority=["intern", "entry"], job_type="internship")
def L(**k): return F.classify({"type": "", "desc": "", "company": "acme", "location": "", **k})

def test_ident_cross_source():
    assert F.ident("https://stripe.com/jobs/search?gh_jid=8031833") == F.ident("http://job-boards.greenhouse.io/stripe/jobs/8031833")
    assert F.ident("https://jobs.lever.co/a/6ed76ce8-4156-4b60-b120-403538bd66cd?lever-source=x") == F.ident("https://jobs.lever.co/a/6ed76ce8-4156-4b60-b120-403538bd66cd")
    assert F.ident("https://nvidia.wd5.myworkdayjobs.com/en-US/S/job/Pune/Software-Intern_JR2021484?q=intern") == F.ident("https://nvidia.wd5.myworkdayjobs.com/S/job/Pune/Software-Intern_JR2021484")

def test_norm_url():
    assert F.norm_url("http://boards.greenhouse.io/x/jobs/1/") == "https://job-boards.greenhouse.io/x/jobs/1"

def test_canonical_key_merges_variants():
    a = L(title="Software Engineer Intern (Summer 2027)", location="Bangalore, India")
    b = L(title="Software Engineer Intern", location="Bengaluru")
    assert F.dkey(a) == F.dkey(b)
    assert F.dkey(a) != F.dkey(L(title="Software Engineer Intern", location="Pune"))

def test_classify():
    assert L(title="ML Research Intern")["job_type"] == "internship"
    assert L(title="Senior Software Engineer")["seniority"] == "senior"
    assert L(title="Software Engineer, New Grad")["seniority"] == "entry"
    assert L(title="Engineer", location="Gurugram, Haryana")["in_india"]

def test_match_rules():
    s, why = F.match(L(title="Machine Learning Intern", location="Bengaluru", desc="python"), P); assert s >= 80 and why
    assert F.match(L(title="Senior Software Engineer", location="Bengaluru"), P)[0] is None          # not intern
    assert F.match(L(title="Software Engineer Intern", location="Berlin"), P)[1] == "location"
    assert F.match(L(title="Trainee - Recruitment Coordinator", location="Bangalore"), P)[0] is None  # 'ai' must not match 'trainee'
    assert F.match(L(title="Sales Intern", location="India"), P)[0] is None

def test_visa_rule():
    p = dict(P, locations=["India", "Remote", "London"], needs_sponsorship=True)
    assert F.match(L(title="Software Engineer Intern", location="London", desc="We are unable to sponsor visas"), p)[0] is None
    s, why = F.match(L(title="Software Engineer Intern", location="London"), p); assert any("sponsorship" in w[1] for w in why)

def test_queries():
    assert F.queries("ML / SWE", True) == ["machine learning intern", "software engineer intern"]
