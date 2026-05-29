#!/bin/bash

# ── Load nvm & node ──────────────────────────────────────
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/src/main"
FRONTEND="$ROOT/src/main/frontend"
PYTHON="/home/rakesh/myenv/bin/python"
UVICORN="/home/rakesh/myenv/bin/uvicorn"

# ── Check .env ───────────────────────────────────────────
if [ ! -f "$ROOT/.env" ]; then
  echo "❌  .env not found. Run: cp .env.example .env  then add your API keys."
  exit 1
fi

# ── Install frontend deps if missing ────────────────────
if [ ! -d "$FRONTEND/node_modules" ]; then
  echo "📦  Installing frontend dependencies..."
  cd "$FRONTEND" && npm install
fi

# ── Start backend ────────────────────────────────────────
echo "🚀  Starting backend on http://localhost:8000 ..."
cd "$BACKEND"
$UVICORN backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# ── Wait for backend to be ready ────────────────────────
echo "⏳  Waiting for backend..."
for i in $(seq 1 15); do
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅  Backend ready."
    break
  fi
  sleep 1
done

# ── Start frontend ───────────────────────────────────────
echo "🎨  Starting React app on http://localhost:3000 ..."
cd "$FRONTEND"
npm run dev &
FRONTEND_PID=$!

# ── Open browser (WSL → Windows) ────────────────────────
sleep 3
powershell.exe -Command "Start-Process 'http://localhost:3000'" 2>/dev/null || true

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅  InterviewMate is running"
echo "  🌐  http://localhost:3000"
echo "  🔌  Backend: http://localhost:8000"
echo "  Press Ctrl+C to stop everything"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Shutdown both on Ctrl+C ──────────────────────────────
trap "echo ''; echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
