"""SQLite cache with per-kind freshness (TTL). Liveness goes stale fastest."""
import sqlite3, json, time, os, threading
DB = os.path.join(os.path.dirname(__file__), "..", "data", "cache.db")
TTL = {"posting": 6 * 3600, "liveness": 3600, "search": 1800, "form": 24 * 3600, "match": 7 * 86400}
_l = threading.Lock()
def _c():
    c = sqlite3.connect(DB); c.execute("create table if not exists kv(k text primary key, kind text, v text, ts real)"); return c
def get(kind, key):
    if os.environ.get("JOBOS_NOCACHE"): return None
    with _l:
        row = _c().execute("select v, ts from kv where k=?", (f"{kind}:{key}",)).fetchone()
    if row and time.time() - row[1] < TTL.get(kind, 3600): return json.loads(row[0])
def put(kind, key, v):
    with _l:
        c = _c(); c.execute("replace into kv values(?,?,?,?)", (f"{kind}:{key}", kind, json.dumps(v), time.time())); c.commit()
