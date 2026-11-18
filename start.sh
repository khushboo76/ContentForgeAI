#!/usr/bin/env sh
# Start the API and dashboard together, and stop both when this script exits.
set -eu

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_PID=""

release_backend_port() {
  if command -v fuser >/dev/null 2>&1; then
    fuser -k -TERM "$BACKEND_PORT/tcp" >/dev/null 2>&1 || true
    sleep 1
    fuser -k -KILL "$BACKEND_PORT/tcp" >/dev/null 2>&1 || true
    sleep 1
  elif command -v lsof >/dev/null 2>&1; then
    BACKEND_PORT_PIDS="$(lsof -tiTCP:"$BACKEND_PORT" -sTCP:LISTEN 2>/dev/null || true)"
    if [ -n "$BACKEND_PORT_PIDS" ]; then
      kill $BACKEND_PORT_PIDS 2>/dev/null || true
      sleep 1
    fi
  else
    echo "Cannot release backend port $BACKEND_PORT: install fuser or lsof."
    exit 1
  fi
}

cleanup() {
  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

cd "$PROJECT_DIR/backend"
if [ ! -x .venv/bin/python ]; then
  echo "Backend environment is missing. Run the one-time setup: cd backend && python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"
  exit 1
fi

# A fresh launch always uses the current code and configuration. Reclaim only
# this exact backend port; frontend port 3000 is never touched.
release_backend_port
FRONTEND_URL="http://localhost:$FRONTEND_PORT" \
  .venv/bin/python -m uvicorn main:app --port "$BACKEND_PORT" &
BACKEND_PID=$!
sleep 1
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
  echo "Could not start the backend on port $BACKEND_PORT."
  exit 1
fi

cd "$PROJECT_DIR/frontend"
if [ ! -d node_modules ]; then
  echo "Frontend dependencies are missing. Run the one-time setup: cd frontend && npm install"
  exit 1
fi
NEXT_PUBLIC_API_BASE="http://localhost:$BACKEND_PORT" \
  npm run dev -- -p "$FRONTEND_PORT"
