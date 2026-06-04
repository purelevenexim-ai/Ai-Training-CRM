#!/usr/bin/env bash
# scripts/daily_orchestrate.sh
#
# Called by cron at 4:30am UTC (10:00am IST) every day.
# Sends today's WhatsApp journey messages for all eligible customers.
#
# Installed by 05_go_live.sh. Runs as: 30 4 * * * /path/to/daily_orchestrate.sh

set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${BACKEND_DIR}/logs/orchestrator.log"
BASE_URL="https://api.pureleven.com"
SHOP="rwxtic-gz.myshopify.com"

mkdir -p "${BACKEND_DIR}/logs"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ── Starting daily orchestration ──" >> "$LOG_FILE"

RESPONSE=$(curl -s -X POST "${BASE_URL}/api/journey/orchestrate" \
  -H "Content-Type: application/json" \
  -d "{\"shop_domain\":\"${SHOP}\",\"dry_run\":false}" \
  --max-time 120 \
  2>&1)

echo "$RESPONSE" >> "$LOG_FILE"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Done." >> "$LOG_FILE"
