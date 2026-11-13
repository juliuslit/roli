#!/bin/zsh
# Roli local prototype: start / stop / status / log of the web app on this Mac only (127.0.0.1:8008).
# Usage:  ./roli_local.sh start | stop | status | log | restart
# Keys stay in .env (loaded by the app). No tunnel, no deployment, no token needed in local mode.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE" || exit 1
PORT="${ROLI_PORT:-8008}"
PID_FILE="$HERE/roli_agent/runs/.web.pid"
LOG_FILE="$HERE/roli_agent/runs/web.log"
mkdir -p "$HERE/roli_agent/runs"

running() { [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; }

case "${1:-}" in
  start)
    if running; then echo "Roli is already running (pid $(cat "$PID_FILE")) at http://127.0.0.1:$PORT/"; exit 0; fi
    if [[ ! -x .venv/bin/uvicorn ]]; then echo "No .venv/bin/uvicorn: run  .venv/bin/pip install uvicorn fastapi jinja2 python-multipart"; exit 1; fi
    for k in OPENROUTER_API_KEY TAVILY_API_KEY USDA_FDC_API_KEY; do
      grep -q "^$k=" .env 2>/dev/null || echo "warning: $k is not set in .env"
    done
    nohup .venv/bin/uvicorn roli_agent.mvp.web:app --host 127.0.0.1 --port "$PORT" >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 2
    if running; then
      echo "Roli started (pid $(cat "$PID_FILE")). Open  http://127.0.0.1:$PORT/   Log: $LOG_FILE"
    else
      echo "Roli did not start; last log lines:"; tail -n 20 "$LOG_FILE"; rm -f "$PID_FILE"; exit 1
    fi ;;
  stop)
    if running; then kill "$(cat "$PID_FILE")" && rm -f "$PID_FILE" && echo "Roli stopped."; else echo "Roli is not running."; rm -f "$PID_FILE"; fi ;;
  restart) "$0" stop; "$0" start ;;
  status)
    if running; then echo "Roli is running (pid $(cat "$PID_FILE")) at http://127.0.0.1:$PORT/"; else echo "Roli is not running."; fi ;;
  log) tail -n 50 "$LOG_FILE" ;;
  *) echo "Usage: $0 start | stop | restart | status | log"; exit 2 ;;
esac
