#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment…"
  python3 -m venv .venv
fi

source .venv/bin/activate

if ! .venv/bin/pip show zeep flask > /dev/null 2>&1; then
  echo "Installing dependencies…"
  pip install -q -r requirements.txt
fi

mkdir -p downloads

PORT=5224

if lsof -ti :"$PORT" > /dev/null 2>&1; then
  echo "Port $PORT in use — killing existing process…"
  lsof -ti :"$PORT" | xargs kill -9
fi

open_browser() {
  sleep 1.5
  local url="http://localhost:$PORT"
  if grep -qi microsoft /proc/version 2>/dev/null; then
    cmd.exe /c start "$url" 2>/dev/null
  elif command -v xdg-open > /dev/null 2>&1; then
    xdg-open "$url"
  elif command -v open > /dev/null 2>&1; then
    open "$url"
  fi
}

open_browser &

echo "Starting kVASy Invoice Tool at http://localhost:$PORT"
FLASK_RUN_PORT=$PORT python3 app.py
