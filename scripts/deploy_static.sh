#!/bin/sh
# Build the read-only copy and deploy it to Vercel (project: sarvam-website-agent).
# Needs the Vercel CLI, logged in (vercel login). The copy holds no key and no run button.
set -e
cd "$(dirname "$0")/.."
rm -rf dist
python3 app/server.py --export dist
cat > dist/vercel.json <<'JSON'
{"headers": [{"source": "/(.*)", "headers": [{"key": "X-Robots-Tag", "value": "noindex"}]}]}
JSON
printf '.env*\n.vercel\n' > dist/.vercelignore
cd dist
vercel link --yes --project sarvam-website-agent > /dev/null
vercel deploy --prod --yes
