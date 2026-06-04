#!/usr/bin/env bash
set -euo pipefail

# One-shot rollout for tracking ops enhancements:
# - sync backend/frontend files to live app path
# - restart service
# - run smoke checks for replay/retry/health/alerts/events
# - install 15-min cron for production_tracking_validation.py
# - route non-zero validation exits to alert webhook (if provided)

VPS_IP="${VPS_IP:-192.46.213.140}"
VPS_USER="${VPS_USER:-root}"
REMOTE_APP_PATH="${REMOTE_APP_PATH:-/opt/pureleven/ai-engine/app}"
BASE_URL="${BASE_URL:-https://track.pureleven.com}"
ADMIN_SECRET="${ADMIN_SECRET:-}"
ALERT_WEBHOOK_URL="${ALERT_WEBHOOK_URL:-}"
if [[ -z "${ALERT_WEBHOOK_URL}" && -f /opt/pureleven/.env ]]; then
  ALERT_WEBHOOK_URL="$(grep -E '^(ALERT_WEBHOOK_URL|SLACK_WEBHOOK_URL)=' /opt/pureleven/.env | tail -n 1 | cut -d= -f2- | tr -d '\r')"
fi

if [[ -z "${ADMIN_SECRET}" ]]; then
  echo "ERROR: ADMIN_SECRET is required."
  echo "Usage: ADMIN_SECRET=basil bash scripts/deploy_tracking_ops.sh"
  exit 1
fi

for raw in "${BASE_URL}" "${ADMIN_SECRET}" "${ALERT_WEBHOOK_URL}" "${REMOTE_APP_PATH}"; do
  if [[ "${raw}" == *"'"* ]]; then
    echo "ERROR: Values cannot contain a single quote (')."
    exit 1
  fi
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
ARCHIVE="/tmp/pureleven_tracking_ops_${STAMP}.tar.gz"
REMOTE_ARCHIVE="/tmp/pureleven_tracking_ops_${STAMP}.tar.gz"

FILES=(
  "crm_routes.py"
  "src/utils/crmApi.js"
  "src/components/TrackingAttributionPanel.jsx"
  "src/components/CRMDashboard_V2.jsx"
  "scripts/production_tracking_validation.py"
)

echo "[1/6] Packaging changed files..."
cd "${ROOT_DIR}"
for f in "${FILES[@]}"; do
  if [[ ! -f "${f}" ]]; then
    echo "ERROR: Missing required file: ${f}"
    exit 1
  fi
done
tar -czf "${ARCHIVE}" "${FILES[@]}"

echo "[2/6] Uploading package to ${VPS_USER}@${VPS_IP}..."
scp "${ARCHIVE}" "${VPS_USER}@${VPS_IP}:${REMOTE_ARCHIVE}"

echo "[3/6] Deploying files, restarting service, running smoke checks, and installing cron..."
ssh "${VPS_USER}@${VPS_IP}" \
  "REMOTE_APP_PATH='${REMOTE_APP_PATH}' BASE_URL='${BASE_URL}' ADMIN_SECRET='${ADMIN_SECRET}' ALERT_WEBHOOK_URL='${ALERT_WEBHOOK_URL}' REMOTE_ARCHIVE='${REMOTE_ARCHIVE}' bash -s" <<'REMOTE'
set -euo pipefail

mkdir -p "${REMOTE_APP_PATH}"
tar -xzf "${REMOTE_ARCHIVE}" -C "${REMOTE_APP_PATH}"

cd "${REMOTE_APP_PATH}"

# Syntax checks for updated Python files before restart.
python3 -m py_compile crm_routes.py scripts/production_tracking_validation.py

# Build frontend bundle if this runtime serves the dashboard from dist assets.
if command -v npm >/dev/null 2>&1 && [[ -f package.json ]]; then
  npm run build --if-present >/dev/null
fi

# Restart API service with whichever runtime exists.
if docker ps --format '{{.Names}}' | grep -q '^pureleven-ai-engine$'; then
  docker restart pureleven-ai-engine >/dev/null
elif docker compose ps --services 2>/dev/null | grep -q '^crm-api$'; then
  docker compose restart crm-api >/dev/null
elif command -v docker-compose >/dev/null 2>&1 && docker-compose ps --services 2>/dev/null | grep -q '^crm-api$'; then
  docker-compose restart crm-api >/dev/null
else
  echo "ERROR: Could not find pureleven-ai-engine container or crm-api compose service."
  exit 2
fi

sleep 8

python3 - <<'PY'
import json
import os
import sys
import urllib.parse
import urllib.request

base = os.environ["BASE_URL"].rstrip("/")
secret = os.environ["ADMIN_SECRET"]


def get(path, params):
    q = urllib.parse.urlencode(params)
    url = f"{base}{path}?{q}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
      return json.loads(resp.read().decode("utf-8"))


def post(path, payload, params):
    q = urllib.parse.urlencode(params)
    url = f"{base}{path}?{q}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
      return json.loads(resp.read().decode("utf-8"))


def must(cond, msg):
    if not cond:
        print(f"SMOKE_FAIL: {msg}")
        sys.exit(10)


common = {"admin_secret": secret}

health = get("/api/crm/admin/tracking/health", {**common, "hours": 24})
must(health.get("status") == "ok", "health endpoint response invalid")

alerts = get("/api/crm/admin/tracking/alerts", {**common, "hours": 6})
must(alerts.get("status") == "ok", "alerts endpoint response invalid")

events = get("/api/crm/admin/tracking/events", {**common, "limit": 20})
must(events.get("status") == "ok", "events endpoint response invalid")

retry_payload = {
    "statuses": ["failed", "skipped"],
    "destinations": ["meta", "google", "ga4"],
    "lookback_hours": 72,
    "limit": 5,
}
retry_resp = post("/api/crm/admin/tracking/retry", retry_payload, common)
must(retry_resp.get("status") == "queued", "retry endpoint response invalid")

items = events.get("items") or []
order_id = None
for row in items:
    oid = str(row.get("order_id") or "").strip()
    if oid:
        order_id = oid
        break

if order_id:
    replay_payload = {"order_id": order_id, "destinations": ["meta", "google", "ga4"], "force": False}
    replay_resp = post("/api/crm/admin/tracking/replay", replay_payload, common)
    must(replay_resp.get("status") == "queued", "replay endpoint response invalid")
    replay_note = f"ok(order_id={order_id})"
else:
    replay_note = "skipped(no_recent_order_id_in_events)"

print("SMOKE_OK")
print(json.dumps({
    "health_summary": health.get("summary", {}),
    "alerts_severity": alerts.get("severity"),
    "events_count": len(items),
    "retry_queued_count": retry_resp.get("queued_count"),
    "replay": replay_note,
}, ensure_ascii=True))
PY

# Wrapper script for cron validation + alert webhook.
cat > "${REMOTE_APP_PATH}/scripts/run_tracking_validation_with_alert.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-https://track.pureleven.com}"
ADMIN_SECRET="${ADMIN_SECRET:-}"
ALERT_WEBHOOK_URL="${ALERT_WEBHOOK_URL:-}"

if [[ -z "${ADMIN_SECRET}" ]]; then
  echo "TRACKING_VALIDATION_MISCONFIG admin_secret_missing"
  exit 1
fi

python3 "$(dirname "$0")/production_tracking_validation.py" \
  --base-url "${BASE_URL}" \
  --admin-secret "${ADMIN_SECRET}"
rc=0
python3 "$(dirname "$0")/production_tracking_validation.py" \
  --base-url "${BASE_URL}" \
  --admin-secret "${ADMIN_SECRET}" || rc=$?

if [[ ${rc} -ne 0 && -n "${ALERT_WEBHOOK_URL}" ]]; then
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  msg="Pureleven tracking validation failed (exit=${rc}) at ${ts} on $(hostname)"
  curl -sS -X POST -H 'Content-Type: application/json' \
    --data "{\"text\":\"${msg}\"}" \
    "${ALERT_WEBHOOK_URL}" >/dev/null || true
elif [[ ${rc} -ne 0 ]]; then
  logger -t pureleven-tracking-validation "validation failed exit=${rc} base_url=${BASE_URL}"
fi

exit ${rc}
SH
chmod +x "${REMOTE_APP_PATH}/scripts/run_tracking_validation_with_alert.sh"

# Install/replace cron line.
CRON_TAG="# PURELEVEN_TRACKING_VALIDATION"
CRON_CMD="*/15 * * * * BASE_URL='${BASE_URL}' ADMIN_SECRET='${ADMIN_SECRET}' ALERT_WEBHOOK_URL='${ALERT_WEBHOOK_URL}' /bin/bash ${REMOTE_APP_PATH}/scripts/run_tracking_validation_with_alert.sh >> /var/log/pureleven-tracking-validation.log 2>&1 ${CRON_TAG}"
(crontab -l 2>/dev/null | grep -v "${CRON_TAG}" || true; echo "${CRON_CMD}") | crontab -

echo "CRON_OK"
crontab -l | grep "PURELEVEN_TRACKING_VALIDATION" || true
REMOTE

echo "[4/6] Verifying public health endpoint after deployment..."
curl -fsS "${BASE_URL}/api/crm/health" >/dev/null

echo "[5/6] Cleaning up temp archive..."
rm -f "${ARCHIVE}"
ssh "${VPS_USER}@${VPS_IP}" "rm -f '${REMOTE_ARCHIVE}'"

echo "[6/6] Done."
echo "Deployment + restart + smoke + cron setup completed."
