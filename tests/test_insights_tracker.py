import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend import insights as I, finder as F, sources as S

def test_skills_in_word_boundaries():
    s = I.skills_in("We use Python, C++ and PyTorch; Go is a plus. Django, not golangish.")
    assert {"python", "c++", "pytorch", "go", "django"} <= set(s)
    assert "r" not in I.skills_in("Remote role in Bangalore")
    assert "java" not in I.skills_in("javascript only")

def test_posted_days_formats():
    assert I.posted_days("Posted Today") == 0 and I.posted_days("Posted Yesterday") == 1
    assert I.posted_days("Posted 30+ Days Ago") == 30 and I.posted_days(None) is None and I.posted_days("soon") is None
    assert 1.5 < I.posted_days((time.time() - 2 * 86400) * 1000) < 2.5
    assert I.posted_days(time.strftime("%Y-%m-%d")) < 1.01

def test_pulse_gap_and_cities():
    L = [{"company": "A", "city": "bengaluru", "skills": ["python", "cuda"]}, {"company": "A", "city": "", "skills": ["cuda"]}, {"company": "B", "city": "remote", "skills": ["python"]}]
    p = I.pulse(L, ["Python"])
    assert dict(p["skill_demand"]) == {"python": 2, "cuda": 2} and dict(p["skill_gap"]) == {"cuda": 2}
    assert dict(p["cities"])["unknown"] == 1 and dict(p["companies"])["A"] == 2 and p["n"] == 3

def test_find_loc_sources():
    assert S.wd_slug_loc("https://walmart.wd504.myworkdayjobs.com/WalmartExternal/job/IN-KA-BANGALORE-Home-Office-PTPP1/STAFF--SOFTWARE-ENGINEER_R-2615151") == "Bangalore, India"
    assert S.wd_slug_loc("https://nvidia.wd5.myworkdayjobs.com/S/job/India-Pune/CPU-Compiler-Intern---2027_JR2027260-1") == "Pune, India"
    assert F.find_loc("Location\nGurgaon, Haryana\nApply") == "Gurgaon, Haryana"
    assert F.find_loc("Team based in Bangalore") == "Bengaluru" and F.find_loc("nothing here") == ""
    assert F.city("New York, NY") == "new york" and F.city("Bangalore, India") == "bengaluru"

def test_tracker_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "DB", str(tmp_path / "t.db"))
    F.track_set("k1", "saved", {"title": "SWE Intern", "company": "Acme"})
    F.track_set("k2", "saved", {"title": "ML Intern", "company": "Beta"})
    F.track_set("k1", "applied")                     # status change keeps stored item
    rows = {r["key"]: r for r in F.track_all()}
    assert rows["k1"]["status"] == "applied" and rows["k1"]["title"] == "SWE Intern" and rows["k2"]["status"] == "saved"
    F.track_set("k2", "remove")
    assert [r["key"] for r in F.track_all()] == ["k1"]
    assert F.STATUSES[0] == "saved" and "offer" in F.STATUSES
