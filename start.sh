#!/usr/bin/env bash
# One command: JobOS API + UI on :8300
cd "$(dirname "$0")"; mkdir -p logs
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
[ -f logs/app.pid ] && kill "$(cat logs/app.pid)" 2>/dev/null; [ "$1" = stop ] && exit 0; sleep 1
setsid nohup ${PY:-.venv/bin}/uvicorn backend.app:app --host 0.0.0.0 --port 8300 > logs/app.log 2>&1 & echo $! > logs/app.pid
for i in $(seq 1 30); do curl -sf localhost:8300/api/health >/dev/null && break; sleep 1; done
echo "JobOS UI + API: http://localhost:8300   (docs: /docs)"
