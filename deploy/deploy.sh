#!/bin/sh
# Deploy the API to Fly with the Neon connection string and the write token as secrets, from a
# machine with a POSIX shell. Reads FLY_API_TOKEN, TURNAROUND_DATABASE_URL (or DATABASE_URL, then the
# tables go in the `turnaround` schema of that database) and TURNAROUND_WRITE_TOKEN from the
# environment or from .env in the repository root. Uses Fly's remote builder, so no local Docker.
set -eu
cd "$(dirname "$0")/.."
if [ -f .env ]; then
  set -a; . ./.env; set +a
fi
APP="${TURNAROUND_FLY_APP_NAME:-turnaround-flights-api}"
SCHEMA=""
if [ -n "${TURNAROUND_DATABASE_URL:-}" ]; then
  URL="$TURNAROUND_DATABASE_URL"
else
  URL="${DATABASE_URL:?set TURNAROUND_DATABASE_URL or DATABASE_URL to the Neon connection string}"
  SCHEMA="turnaround"
fi
: "${TURNAROUND_WRITE_TOKEN:?set TURNAROUND_WRITE_TOKEN}"
command -v flyctl >/dev/null 2>&1 || { echo "flyctl is not installed: https://fly.io/docs/flyctl/install/"; exit 1; }
if ! flyctl apps list 2>/dev/null | grep -q "^$APP"; then
  flyctl apps create "$APP" --org personal
fi
flyctl secrets set --app "$APP" --stage DATABASE_URL="$URL" TURNAROUND_WRITE_TOKEN="$TURNAROUND_WRITE_TOKEN" TURNAROUND_DB_SCHEMA="$SCHEMA"
flyctl deploy --app "$APP" --remote-only --ha=false
echo "deployed: https://$APP.fly.dev/v1/health"
