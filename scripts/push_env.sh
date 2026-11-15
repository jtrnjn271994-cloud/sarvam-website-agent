#!/bin/sh
# Copy the website's settings from .env to the Vercel project (Production and Preview), marked sensitive.
# Each value is piped to the Vercel CLI. Nothing is printed, and nothing is written to the repo.
# Run scripts/deploy_live.sh once first (it links .vercel-stage to the Vercel project), then:
#   scripts/push_env.sh
# Then deploy again so the new values are used.
set -e
cd "$(dirname "$0")/.."
[ -d .vercel-stage/.vercel ] || { echo "run scripts/deploy_live.sh once first"; exit 1; }
KEYS="OPENROUTER_API_KEY SUPABASE_URL SUPABASE_SERVICE_KEY OWNER_TOKEN DAILY_USD_CAP RUNS_PER_VISITOR_PER_DAY MAX_RUN_USD"
for k in $KEYS; do
  v=$(grep "^$k=" .env | tail -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//')
  if [ -z "$v" ]; then echo "skip $k (not in .env; the default is used)"; continue; fi
  for t in production preview; do
    (cd .vercel-stage && vercel env rm "$k" "$t" --yes > /dev/null 2>&1 || true)
    (cd .vercel-stage && printf '%s' "$v" | vercel env add "$k" "$t" --sensitive > /dev/null 2>&1) || { echo "FAILED to set $k for $t"; exit 1; }
  done
  echo "set $k (production, preview)"
done
