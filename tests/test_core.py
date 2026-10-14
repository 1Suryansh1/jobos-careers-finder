import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["JOBOS_NOCACHE"] = "1"
import pytest
from backend import resolve as R, agents as A

def test_detect_ats():
    assert R.detect("https://job-boards.greenhouse.io/gitlab/jobs/8704363002") == {"ats": "greenhouse", "board": "gitlab", "id": "8704363002"}
    assert R.detect("https://jobs.lever.co/palantir/6ed76ce8-4156-4b60-b120-403538bd66cd")["ats"] == "lever"
    assert R.detect("https://jobs.ashbyhq.com/openai/240d459b-696d-43eb-8497-fab3e56ecd9b")["ats"] == "ashby"
    assert R.detect("https://x.wd5.myworkdayjobs.com/en-US/X/job/Eng_R1")["ats"] == "workday"
    assert R.detect("https://stripe.com/jobs/search?gh_jid=8172508")["ats"] == "greenhouse_custom"

def test_slug_title():
    assert R.slug_title("https://d.wd1.myworkdayjobs.com/en-US/d/job/Sr-Backend-Engineer--Python-_R36375").startswith("Sr Backend Engineer")
    assert R.slug_title("https://jobs.lever.co/a/111d83e5-3276-4cf3-a234-797250cbbacd") is None

def test_dead_regex():
    assert R.DEAD.search("The page you are looking for doesn't exist.")
    assert R.DEAD.search("This job is no longer available")
    assert not R.DEAD.search("We are hiring a backend engineer. Apply now")

def test_merge_crosscheck_and_confidence():
    src = [("agent", {"is_open": True, "title": "AI Engineer - NYC", "location": "NYC"}),
           ("fetch", {"is_open": True, "title": "AI Engineer - NYC"})]
    f, notes = R.merge(src, "https://d.wd1.myworkdayjobs.com/en-US/d/job/Senior-Backend-Engineer--Python-API_R35807")
    assert f["is_open"]["confidence"] > R.BASE_CONF["agent"]          # agreement boosts
    assert any("URL slug" in n for n in notes)                          # re-used requisition flagged
    assert f["title"]["confidence"] < f["is_open"]["confidence"]

def test_merge_disagreement_penalises():
    f, notes = R.merge([("agent", {"is_open": True}), ("fetch", {"is_open": False})], "https://x/y")
    assert f["is_open"]["confidence"] < R.BASE_CONF["agent"] and notes

def test_nullish_cleaned():
    f, _ = R.merge([("agent", {"is_open": False, "title": "not available"})], "https://x/y")
    assert f["title"]["value"] is None

def test_validate_schema():
    assert R.validate({"is_open": True, "apply_requires_account": False}) == []
    assert "missing is_open" in R.validate({"apply_requires_account": False})
    assert R.validate({"is_open": "yes", "apply_requires_account": False}) == ["is_open wrong type"]

def test_job_schema_obeys_tinyfish_rules():
    s = json.dumps(R.JOB_SCHEMA); assert len(s) < 64 * 1024 and R.JOB_SCHEMA["type"] == "object"
    assert '"null"' not in s  # docs: use nullable, not type: [x, null]

def test_submit_guard():
    assert A.submit_guard("Click submit button to check visibility")
    assert A.submit_guard("Press 'Submit application'")
    assert not A.submit_guard("Fill First Name field")
    assert not A.submit_guard("Click Apply button to reveal the application form")

def test_job_url_filter():
    assert A.JOB_URL.search("https://jobs.lever.co/supermove/176fe130-a2cc-40da-b978-8c693fefc510")
    assert not A.JOB_URL.search("https://jobs.lever.co/palantir")

@pytest.mark.skipif(not os.environ.get("LIVE"), reason="set LIVE=1 for live API tests")
def test_live_greenhouse_api_tier():
    from dotenv import load_dotenv; load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    r = R.resolve("https://job-boards.greenhouse.io/gitlab/jobs/1234567")
    assert r["fields"]["is_open"]["value"] is False and r["trail"][0]["tier"] == "ats_api"
