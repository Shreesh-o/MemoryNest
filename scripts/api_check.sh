#!/usr/bin/env bash
# One-command API check for MemoryNest. Usage: bash scripts/api_check.sh
# Starts a throwaway API on port 8010 with TEMP data, calls every endpoint,
# prints a PASS/FAIL table, saves the output to ~/api_check_out.txt, cleans up.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT=8010
TMPD="$(mktemp -d)"
OUT="$HOME/api_check_out.txt"
API_PID=""
exec > >(tee "$OUT") 2>&1

cleanup() {
  if [ -n "$API_PID" ]; then kill "$API_PID" 2>/dev/null; sleep 1; kill -9 "$API_PID" 2>/dev/null; fi
  rm -rf "$TMPD"
}
trap cleanup EXIT

cd "$ROOT" || exit 1
# shellcheck disable=SC1091
source .venv/bin/activate

if ss -ltn 2>/dev/null | grep -q ":$PORT "; then
  echo "Port $PORT is already in use. Stop whatever uses it and retry."; exit 2
fi
if curl -s --max-time 3 localhost:11434/api/tags >/dev/null; then
  echo "Ollama: up"
else
  echo "WARNING: Ollama is not reachable; chat, summary and audio checks will fail with 503."
fi

JWT_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"; export JWT_SECRET
DB_PATH="$TMPD/m.db" CHROMA_DIR="$TMPD/chroma" UPLOAD_DIR="$TMPD/uploads" AUDIO_DIR="$TMPD/audio" \
  uvicorn app.api.main:app --port "$PORT" > "$TMPD/api.log" 2>&1 &
API_PID=$!
for _ in $(seq 1 90); do curl -s "127.0.0.1:$PORT/api/health" >/dev/null && break; sleep 1; done
if ! curl -s "127.0.0.1:$PORT/api/health" >/dev/null; then
  echo "API did not start. Log:"; tail -n 40 "$TMPD/api.log"; exit 3
fi

U="127.0.0.1:$PORT"; J="$TMPD/jar"
DUE="$(date -d '+10 days' '+%-d %B %Y')"
printf 'Project report\nSubmission deadline: %s\nThe MemoryNest project uses ChromaDB for vector search.\n' "$DUE" > "$TMPD/t.txt"

NAMES=(); RESULTS=(); DETAILS=()
record() { NAMES+=("$1"); RESULTS+=("$2"); DETAILS+=("$3"); }

# call NAME EXPECTED_HTTP_REGEX BODY_MUST_MATCH_REGEX(or -) curl-args...
call() {
  local name="$1" exp="$2" must="$3"; shift 3
  echo; echo "--- $name"
  local code
  code=$(curl -s --max-time 300 -b "$J" -c "$J" -o "$TMPD/out" -w "%{http_code}" "$@")
  echo "[HTTP $code]"; head -c 600 "$TMPD/out"; echo
  local ok=1
  [[ "$code" =~ ^($exp)$ ]] || ok=0
  if [ "$must" != "-" ] && ! grep -qiE "$must" "$TMPD/out"; then ok=0; fi
  if [ "$ok" -eq 1 ]; then record "$name" PASS "HTTP $code"; else record "$name" FAIL "HTTP $code"; fi
}
mark_review() { local i=$((${#RESULTS[@]}-1)); [ "${RESULTS[$i]}" = PASS ] && RESULTS[$i]="REVIEW"; }

echo; echo "=== ROUTES"
curl -s "$U/openapi.json" -o "$TMPD/openapi.json"
python - "$TMPD/openapi.json" <<'PY'
import json, sys
paths = json.load(open(sys.argv[1]))["paths"]
for p, v in sorted(paths.items()):
    for m in v:
        print(m.upper(), p)
PY
for need in /api/chat /api/conversations /api/events /api/calendar.ics /api/summaries /api/dashboard /api/reminders; do
  if grep -q "\"$need\"" "$TMPD/openapi.json"; then record "route $need" PASS "present"; else record "route $need" FAIL "MISSING"; fi
done

JSON='content-type: application/json'
call "register"   201     -   -X POST "$U/api/auth/register" -H "$JSON" -d '{"username":"demo","password":"demo1234"}'
call "login"      200     -   -X POST "$U/api/auth/login"    -H "$JSON" -d '{"username":"demo","password":"demo1234"}'
call "upload"     200     '"status":"ready"' -F "files=@$TMPD/t.txt" "$U/api/documents/upload"
call "chat: in-document question (should mention ChromaDB)" 200 'chroma' -X POST "$U/api/chat" -H "$JSON" -d '{"question":"What does the MemoryNest project use for vector search?"}'
call "chat: NOT in documents (should say it does not know)" 200 - -X POST "$U/api/chat" -H "$JSON" -d '{"question":"Who won the 1998 football world cup?"}'; mark_review
call "conversations" 200  -   "$U/api/conversations"
call "extract events" "200|201" -   -X POST "$U/api/documents/1/extract-events"
call "events (should contain a date)" 200 '20[0-9]{2}-[0-9]{2}-[0-9]{2}' "$U/api/events"
call "confirm event 1" 200 -  -X POST "$U/api/events/1/confirm" -H "$JSON" -d '{}'
call "reminders"  200     -   "$U/api/reminders"
call "calendar.ics" 200 'BEGIN:VCALENDAR' "$U/api/calendar.ics"
call "summary"    200     -   -X POST "$U/api/documents/1/summary" -H "$JSON" -d '{}'
call "summaries list" 200 -   "$U/api/summaries"
call "audio create" 200   -   -X POST "$U/api/summaries/1/audio" -H "$JSON" -d '{}'
acode=$(curl -s --max-time 120 -b "$J" -o "$TMPD/a.audio" -w "%{http_code} %{content_type}" "$U/api/summaries/1/audio")
asize=$(stat -c %s "$TMPD/a.audio" 2>/dev/null || echo 0)
echo; echo "--- audio download"; echo "[$acode] size=$asize bytes"
if [[ "$acode" == 200* ]] && [ "$asize" -gt 1000 ]; then record "audio download" PASS "$acode, $asize bytes"; else record "audio download" FAIL "$acode, $asize bytes"; fi
call "dashboard"  200 'total' "$U/api/dashboard"

echo; echo "=== API LOG (error lines)"
grep -iE "traceback|error|exception" "$TMPD/api.log" | head -15

echo; echo "=================== SUMMARY ==================="
FAILS=0
for i in "${!NAMES[@]}"; do
  printf '%-8s %-58s %s\n' "${RESULTS[$i]}" "${NAMES[$i]}" "${DETAILS[$i]}"
  [ "${RESULTS[$i]}" = FAIL ] && FAILS=$((FAILS+1))
done
echo "FAILED: $FAILS"
echo "REVIEW = passed technically; read its answer above yourself."
echo "Full output saved to $OUT"
sleep 1
exit "$FAILS"
