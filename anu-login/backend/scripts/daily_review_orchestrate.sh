#!/bin/bash
# scripts/daily_review_orchestrate.sh
#
# Daily cron for Review Journey orchestration.
# Runs every day at 5:00 AM UTC (1 hour after main journey cron).
#
# Install:
#   crontab -e
#   0 5 * * * /path/to/anu-login/backend/scripts/daily_review_orchestrate.sh >> /var/log/review_journey.log 2>&1
#
# The script POSTs to the FastAPI endpoint — no Python subprocess needed.

set -euo pipefail

API_BASE="${PURELEVEN_API_BASE:-https://api.pureleven.com}"
ENDPOINT="${API_BASE}/api/review-journey/orchestrate"
LOG_TAG="[review-journey-cron]"

echo "${LOG_TAG} $(date -u '+%Y-%m-%dT%H:%M:%SZ') Starting review journey orchestration..."

RESPONSE=$(curl -s -X POST "${ENDPOINT}" \
  -H "Content-Type: application/json" \
  -w "\n__STATUS_CODE__:%{http_code}" \
  --max-time 120 \
  2>&1)

HTTP_CODE=$(echo "$RESPONSE" | grep -oP '__STATUS_CODE__:\K[0-9]+' || echo "000")
BODY=$(echo "$RESPONSE" | sed 's/__STATUS_CODE__:[0-9]*//')

if [[ "$HTTP_CODE" == "200" ]]; then
    TOTAL_SENT=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total_sent',0))" 2>/dev/null || echo "?")
    echo "${LOG_TAG} $(date -u '+%Y-%m-%dT%H:%M:%SZ') SUCCESS — sent=${TOTAL_SENT}"
    echo "${LOG_TAG} Response: ${BODY}"
else
    echo "${LOG_TAG} $(date -u '+%Y-%m-%dT%H:%M:%SZ') ERROR — HTTP ${HTTP_CODE}"
    echo "${LOG_TAG} Response: ${BODY}"
    exit 1
fi
