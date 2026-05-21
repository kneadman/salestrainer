#!/bin/sh
# Daily token-usage snapshot trigger for 00:00 MSK
# Usage: add to host crontab:
#   0 0 * * * /path/to/deploy/snapshot-cron.sh
# Or run via docker compose:
#   docker compose -f /path/to/docker-compose.yml run --rm snapshot-token-usage

set -e

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

cd "$(dirname "$0")/.."

docker compose -f "$COMPOSE_FILE" run --rm backend \
  python -m app.admin.cli snapshot-token-usage
