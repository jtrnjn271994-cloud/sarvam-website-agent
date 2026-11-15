#!/bin/sh
# Build the website and deploy it to Vercel (project: sarvam-website-agent).
#   scripts/deploy_live.sh          -> a preview URL (test here first)
#   scripts/deploy_live.sh --prod   -> https://sarvam-website-agent.vercel.app
#
# What is deployed (built in .vercel-stage/, never committed):
#   public/  the pages people see (the read-only copy of finished runs, served as static files)
#   api/     one Python function that runs the agent (app/hosted.py)
#   bundle/  the agent's code, rules, knowledge and pages. Only the function can read it; it is not served.
# No key is in any deployed file. Keys live in the Vercel project settings (scripts/push_env.sh).
set -e
cd "$(dirname "$0")/.."
ROOT=$(pwd)
STAGE="$ROOT/.vercel-stage"
python3 -I - "$STAGE" <<'PY'
import os, shutil, sys
s = sys.argv[1]
os.makedirs(s, exist_ok=True)
for n in os.listdir(s):
    if n == ".vercel":
        continue
    p = os.path.join(s, n)
    shutil.rmtree(p) if os.path.isdir(p) and not os.path.islink(p) else os.remove(p)
PY
mkdir -p "$STAGE/api" "$STAGE/bundle"
python3 app/server.py --export "$STAGE/public"
for x in agent app rules knowledge library skills templates schemas docs submission tests pages README.md; do
  [ -e "$x" ] && rsync -a --exclude '__pycache__' --exclude '*.pyc' --exclude '.env*' "$x" "$STAGE/bundle/"
done
cat > "$STAGE/api/index.py" <<'PY'
import os
import sys

BUNDLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bundle")
os.environ.setdefault("AGENT_BUNDLE", BUNDLE)
sys.path.insert(0, os.path.join(BUNDLE, "app"))
import hosted  # noqa: E402


class handler(hosted.handler):   # Vercel looks for a top-level class named handler in this file
    pass
PY
cat > "$STAGE/vercel.json" <<'JSON'
{
  "framework": null,
  "buildCommand": "",
  "outputDirectory": "public",
  "fluid": true,
  "functions": {"api/index.py": {"maxDuration": 300, "includeFiles": "bundle/**"}},
  "rewrites": [{"source": "/api/:p*", "destination": "/api/index?p=:p*"}],
  "headers": [{"source": "/(.*)", "headers": [{"key": "X-Robots-Tag", "value": "noindex"}]}]
}
JSON
printf '.env*\n' > "$STAGE/.vercelignore"
if grep -rlE "sk-or-v1-|sb_secret_" "$STAGE" --exclude-dir=.vercel >/dev/null 2>&1; then
  echo "STOP: a key-like string is in the files to deploy. Nothing was deployed."; exit 1
fi
cd "$STAGE"
[ -d .vercel ] || vercel link --yes --project sarvam-website-agent > /dev/null
# Linking from inside the git repo can connect the project to GitHub; a push would then deploy the repo. Always disconnect.
vercel git disconnect --yes > /dev/null 2>&1 || true
if [ "$1" = "--prod" ]; then vercel deploy --prod --yes; else vercel deploy --yes; fi
