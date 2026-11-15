#!/bin/sh
# Start the local agent console at http://127.0.0.1:8765 (Ctrl+C to stop).
# Any older console still holding the port is stopped first, so you always run the latest code.
# Needs python3 with playwright installed (pip install -r requirements.txt; python3 -m playwright install chromium)
# and OPENROUTER_API_KEY in .env or the environment for the "Start a run" button.
cd "$(dirname "$0")" || exit 1
PORT=8765
prev=""
for a in "$@"; do [ "$prev" = "--port" ] && PORT="$a"; prev="$a"; done
OLD=$(lsof -ti tcp:"$PORT" -sTCP:LISTEN 2>/dev/null)
if [ -n "$OLD" ]; then
  echo "Stopping the older console on port $PORT (process $OLD) so the latest code runs."
  kill $OLD 2>/dev/null; sleep 1
fi
exec python3 app/server.py "$@"
