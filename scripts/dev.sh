#!/usr/bin/env bash
# MemoryNest runner: starts ONLY what the site needs (Ollama if it is down, the API, the web app)
# after preflight checks. It never runs tests.
#   bash scripts/dev.sh             dev mode: hot reload (edit web/src or app/ and see changes)
#   bash scripts/dev.sh --prod      production build + start (smoother, for the final demo)
#   bash scripts/dev.sh --fresh     use a temporary empty database (deleted on exit)
#   bash scripts/dev.sh --stop      stop whatever this script started earlier
#   bash scripts/dev.sh --force     start even if a preflight check failed
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN="$ROOT/.run"
API_PORT=8000
WEB_PORT=3000
API_URL="http://127.0.0.1:$API_PORT"
MODEL="${OLLAMA_MODEL:-qwen2.5:3b-instruct}"
MODE=dev; FRESH=0; STOP_ONLY=0; REBUILD=0; FORCE=0
for a in "$@"; do
  case "$a" in
    --prod) MODE=prod ;;
    --dev) MODE=dev ;;
    --fresh) FRESH=1 ;;
    --rebuild) REBUILD=1 ;;
    --force) FORCE=1 ;;
    --stop) STOP_ONLY=1 ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "Unknown option: $a (try --help)"; exit 1 ;;
  esac
done
mkdir -p "$RUN"

FAILS=0
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$*"; FAILS=$((FAILS+1)); }

# Stop a process group we started earlier (checked by pidfile AND command line, so a reused PID is never killed).
stop_pidfile() {  # $1 name, $2 command-line regex
  local f="$RUN/$1.pid" pid
  [ -f "$f" ] || return 0
  pid="$(cat "$f" 2>/dev/null)"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && ps -o args= -p "$pid" 2>/dev/null | grep -qE "$2"; then
    kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null
    for _ in 1 2 3 4 5; do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
    kill -KILL -- "-$pid" 2>/dev/null || true
  fi
  rm -f "$f"
}
stop_all() {
  stop_pidfile web "npm|next|node"
  stop_pidfile api "uvicorn"
  stop_pidfile ollama "ollama"
}

if [ "$STOP_ONLY" = 1 ]; then stop_all; echo "Stopped everything this script started."; exit 0; fi

FRESH_DIR=""
cleanup() {
  trap - EXIT INT TERM
  echo; echo "Stopping MemoryNest..."
  stop_all
  [ -n "$FRESH_DIR" ] && rm -rf "$FRESH_DIR"
}
trap cleanup EXIT
trap 'exit 0' INT TERM

port_busy() { [ -n "$(ss -ltn "sport = :$1" 2>/dev/null | tail -n +2)" ]; }
wait_for() { local i; for i in $(seq 1 "$2"); do curl -fs --max-time 5 -o /dev/null "$1" && return 0; sleep 1; done; return 1; }

cd "$ROOT" || exit 1
stop_pidfile web "npm|next|node"; stop_pidfile api "uvicorn"   # leftovers from an earlier run of this script

echo "Preflight checks"
if [ ! -f .venv/bin/activate ]; then
  bad "Python venv missing. Create it: python -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"
  exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate
ok "$(python --version 2>&1)"
MISSING="$(python -c 'import importlib.util as u; print(" ".join(m for m in ["fastapi","uvicorn","jwt","multipart","chromadb","sentence_transformers"] if u.find_spec(m) is None))' 2>&1)"
if [ -z "$MISSING" ]; then ok "Core Python packages installed"; else bad "Missing/failed Python packages: $MISSING   (fix: python -m pip install -r requirements.txt)"; fi
OPT="$(python -c 'import importlib.util as u; print(" ".join(m for m in ["bcrypt","dateparser","icalendar","docx","pymupdf","pytesseract"] if u.find_spec(m) is None))' 2>/dev/null)"
[ -n "$OPT" ] && warn "Optional Python packages not found: $OPT"

if command -v node >/dev/null; then
  NV="$(node -p 'process.versions.node.split(".")[0]')"
  if [ "$NV" -ge 20 ]; then ok "Node $(node -v)"; else bad "Node 20+ required (found $(node -v))"; fi
else
  bad "Node is not installed"
fi
if [ ! -d web/node_modules ]; then
  warn "web/node_modules missing: running npm install (one time)"
  if (cd web && npm install > "$RUN/npm_install.log" 2>&1); then ok "npm install done"; else bad "npm install failed (see $RUN/npm_install.log)"; fi
fi
for t in tesseract espeak-ng ffmpeg; do command -v "$t" >/dev/null || warn "$t not found (scans/OCR, offline voice, or mp3 conversion may not work)"; done

for p in "$API_PORT" "$WEB_PORT"; do
  if port_busy "$p"; then bad "Port $p is in use by something else:"; ss -ltnp "sport = :$p" 2>/dev/null | tail -n +2 | sed 's/^/        /'; else ok "Port $p is free"; fi
done

if curl -s --max-time 3 localhost:11434/api/tags >/dev/null; then
  ok "Ollama is running"
elif command -v ollama >/dev/null; then
  setsid ollama serve > "$RUN/ollama.log" 2>&1 &
  echo $! > "$RUN/ollama.pid"
  wait_for "localhost:11434/api/tags" 25 && ok "Ollama started" || bad "Ollama failed to start (see $RUN/ollama.log)"
else
  bad "Ollama is not installed (chat and summaries need it)"
fi
if curl -s --max-time 3 localhost:11434/api/tags | grep -qF "\"$MODEL\""; then ok "Model $MODEL is available"; else bad "Model $MODEL not found. Run: ollama pull $MODEL"; fi

if [ "${MOCK_LLM:-}" = "1" ]; then warn "MOCK_LLM=1 was set in your shell; ignoring it for this run"; fi
unset MOCK_LLM

if [ "$FRESH" = 1 ]; then
  FRESH_DIR="$(mktemp -d)"
  export DB_PATH="$FRESH_DIR/memorynest.db" CHROMA_DIR="$FRESH_DIR/chroma" UPLOAD_DIR="$FRESH_DIR/uploads" AUDIO_DIR="$FRESH_DIR/audio"
  ok "Using a temporary EMPTY database (deleted on exit)"
else
  ok "Using your real data folder: $ROOT/data"
fi

if [ "$FAILS" -gt 0 ] && [ "$FORCE" = 0 ]; then
  echo; echo "Fix the ✗ items above and run again (or add --force to start anyway)."; exit 1
fi

SECRET_FILE="$ROOT/.jwt_secret"
[ -f "$SECRET_FILE" ] || python -c 'import secrets; print(secrets.token_hex(32))' > "$SECRET_FILE"
chmod 600 "$SECRET_FILE"
JWT_SECRET="$(cat "$SECRET_FILE")"; export JWT_SECRET
printf 'API_URL=%s\n' "$API_URL" > "$ROOT/web/.env.local"

if [ "$MODE" = prod ]; then
  MARK="$ROOT/web/.next/.built_api_url"
  if [ ! -f "$MARK" ] || [ "$(cat "$MARK")" != "$API_URL" ] || [ "$REBUILD" = 1 ]; then
    echo; echo "Building the web app (about a minute)..."
    (cd "$ROOT/web" && npm run build > "$RUN/build.log" 2>&1) || { echo "Build failed:"; tail -n 30 "$RUN/build.log"; exit 3; }
    printf '%s' "$API_URL" > "$MARK"
  fi
fi

echo; echo "Starting services ($MODE mode)"
cd "$ROOT" || exit 1
API_ARGS=(app.api.main:app --host 127.0.0.1 --port "$API_PORT")
[ "$MODE" = dev ] && API_ARGS+=(--reload --reload-dir app)
setsid uvicorn "${API_ARGS[@]}" > "$RUN/api.log" 2>&1 &
API_PID=$!
echo "$API_PID" > "$RUN/api.pid"
if wait_for "$API_URL/api/health" 120; then
  HEALTH="$(curl -s "$API_URL/api/health")"
  ok "API is healthy: $HEALTH"
  echo "$HEALTH" | grep -q '"mock_llm":true' && bad "API is in MOCK mode (answers would be fake)"
  echo "$HEALTH" | grep -q '"ollama":"down"' && bad "API cannot reach Ollama"
else
  echo "API did not start. Last log lines:"; tail -n 30 "$RUN/api.log"; exit 4
fi

cd "$ROOT/web" || exit 1
if [ "$MODE" = dev ]; then
  API_URL="$API_URL" setsid npm run dev -- -p "$WEB_PORT" > "$RUN/web.log" 2>&1 &
else
  API_URL="$API_URL" setsid npm run start -- -p "$WEB_PORT" > "$RUN/web.log" 2>&1 &
fi
WEB_PID=$!
echo "$WEB_PID" > "$RUN/web.pid"
if wait_for "http://127.0.0.1:$WEB_PORT/login" 240; then
  ok "Web app is up"
else
  echo "Web app did not start. Last log lines:"; tail -n 30 "$RUN/web.log"; exit 5
fi
if [ "$FAILS" -gt 0 ] && [ "$FORCE" = 0 ]; then
  echo; echo "A health check failed (see ✗ above). Stopping."; exit 6
fi

# Warm-ups in the background so the first page and the first chat are not slow.
( curl -s -o /dev/null --max-time 120 "http://127.0.0.1:$WEB_PORT/register"\; curl -s -o /dev/null --max-time 120 "http://127.0.0.1:$WEB_PORT/dashboard" ) &
curl -s -o /dev/null --max-time 300 localhost:11434/api/generate \
  -d "{\"model\":\"$MODEL\",\"prompt\":\"hi\",\"stream\":false,\"keep_alive\":\"30m\",\"options\":{\"num_predict\":1}}" &

echo
echo "MemoryNest is ready  ->  http://localhost:$WEB_PORT      (mode: $MODE)"
echo "API docs             ->  $API_URL/docs"
if [ "$MODE" = dev ]; then echo "Hot reload is ON: edit files in web/src or app/ and the change appears."; fi
echo "Logs: tail -f $RUN/api.log    tail -f $RUN/web.log"
echo "Press Ctrl+C to stop everything."

while kill -0 "$API_PID" 2>/dev/null && kill -0 "$WEB_PID" 2>/dev/null; do sleep 2; done
echo
if ! kill -0 "$API_PID" 2>/dev/null; then echo "The API stopped unexpectedly. Last log lines:"; tail -n 20 "$RUN/api.log"; fi
if ! kill -0 "$WEB_PID" 2>/dev/null; then echo "The web app stopped unexpectedly. Last log lines:"; tail -n 20 "$RUN/web.log"; fi
exit 1
