"""Market pulse + skill gap. Idea adapted from shikhar818/job-market-intel (MIT): skill-demand and hiring-heatmap marts,
and resume skill_gap(). Re-implemented from scratch with a deterministic skill dictionary instead of KeyBERT/embeddings."""
import re, time
from collections import Counter
SKILLS = ["python", "java", "c++", "c#", "go", "golang", "rust", "javascript", "typescript", "react", "node", "sql", "postgresql", "mysql", "mongodb",
 "redis", "kafka", "spark", "hadoop", "airflow", "dbt", "aws", "gcp", "azure", "docker", "kubernetes", "linux", "git", "rest", "graphql",
 "pytorch", "tensorflow", "jax", "scikit-learn", "pandas", "numpy", "machine learning", "deep learning", "nlp", "computer vision", "llm",
 "transformers", "rag", "reinforcement learning", "statistics", "data structures", "algorithms", "distributed systems", "cuda", "gpu",
 "android", "ios", "kotlin", "swift", "flutter", "html", "css", "next.js", "django", "flask", "fastapi", "spring", "microservices",
 "tableau", "power bi", "excel", "r", "matlab", "verilog", "embedded", "networking", "security", "devops", "ci/cd", "terraform"]
_RX = {s: re.compile(r"(?<![a-z0-9+#])" + re.escape(s) + r"(?![a-z0-9+#])", re.I) for s in SKILLS}

def skills_in(text):
    t = text or ""; return [s for s, rx in _RX.items() if rx.search(t)]

def posted_days(v):
    """'2026-10-01T..' | 1786469891368 | 'Posted 7 Days Ago' | 'Posted Today' | '30+' -> days or None."""
    if v is None or v == "": return None
    if isinstance(v, (int, float)): return max(0, (time.time() - v / 1000) / 86400)
    s = str(v)
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    if m: return max(0, (time.time() - time.mktime(time.strptime(m.group(1), "%Y-%m-%d"))) / 86400)
    if re.search(r"today|just", s, re.I): return 0
    if re.search(r"yesterday", s, re.I): return 1
    m = re.search(r"(\d+)\+?\s*day", s, re.I)
    return int(m.group(1)) if m else None

def pulse(listings, my_skills):
    mine = {s.lower() for s in my_skills}
    demand = Counter(s for x in listings for s in x.get("skills", []))
    cities = Counter((x.get("city") or "unknown") for x in listings)
    comp = Counter(x["company"] for x in listings)
    gap = [(s, n) for s, n in demand.most_common() if s not in mine][:8]
    return {"skill_demand": demand.most_common(12), "skill_gap": gap, "cities": cities.most_common(8),
            "companies": comp.most_common(8), "n": len(listings)}
