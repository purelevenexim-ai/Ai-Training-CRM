#!/usr/bin/env bash
set -euo pipefail

TRACK_BASE="${TRACK_BASE:-https://track.pureleven.com}"
ADS_BASE="${ADS_BASE:-https://adsapi.pureleven.com}"
N8N_BASE="${N8N_BASE:-https://automations.pureleven.com}"
N8N_API_KEY="${N8N_API_KEY:-}"

ok() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; }

check_json_endpoint() {
  local name="$1"
  local url="$2"
  local code
  code=$(curl -sS -o /tmp/integration_check.out -w "%{http_code}" "$url" || true)
  if [[ "$code" =~ ^2 ]]; then
    ok "$name ($code)"
  else
    fail "$name ($code)"
    sed -n '1,30p' /tmp/integration_check.out || true
  fi
}

echo "== Core health =="
check_json_endpoint "track health" "$TRACK_BASE/api/health"
check_json_endpoint "adsapi health" "$ADS_BASE/api/health"
check_json_endpoint "crm health" "$TRACK_BASE/api/crm/health"
check_json_endpoint "crm comprehensive health" "$TRACK_BASE/api/crm/health/comprehensive"
check_json_endpoint "monitoring health" "$ADS_BASE/api/monitoring/health"

echo "== Audience sync runtime =="
code_meta=$(curl -sS -o /tmp/meta_sync.out -w "%{http_code}" -X POST "$TRACK_BASE/api/crm/sync/meta/now" || true)
if [[ "$code_meta" =~ ^2 ]]; then
  ok "meta sync trigger ($code_meta)"
  sed -n '1,40p' /tmp/meta_sync.out
else
  fail "meta sync trigger ($code_meta)"
  sed -n '1,40p' /tmp/meta_sync.out || true
fi

code_google=$(curl -sS -o /tmp/google_sync.out -w "%{http_code}" -X POST "$TRACK_BASE/api/crm/sync/google/now" || true)
if [[ "$code_google" =~ ^2 ]]; then
  ok "google sync trigger ($code_google)"
  sed -n '1,40p' /tmp/google_sync.out
else
  fail "google sync trigger ($code_google)"
  sed -n '1,40p' /tmp/google_sync.out || true
fi

echo "== WhatsApp tracking auth check =="
code_wa=$(curl -sS -o /tmp/wa_tracking.out -w "%{http_code}" \
  -X POST "$ADS_BASE/api/tracking/whatsapp-click" \
  -H "Content-Type: application/json" \
  -d '{"customer_phone":"919999999999","shop_domain":"rwxtic-gz.myshopify.com"}' || true)
if [[ "$code_wa" == "401" || "$code_wa" == "503" ]]; then
  ok "tracking endpoint rejects unsigned payload ($code_wa)"
else
  fail "tracking endpoint hardening regression ($code_wa)"
  sed -n '1,40p' /tmp/wa_tracking.out || true
fi

echo "== N8N wiring =="
if [[ -n "$N8N_API_KEY" ]]; then
  code_n8n=$(curl -sS -o /tmp/n8n_workflows.out -w "%{http_code}" \
    -H "X-N8N-API-KEY: $N8N_API_KEY" \
    "$N8N_BASE/api/v1/workflows" || true)
  if [[ "$code_n8n" =~ ^2 ]]; then
    ok "n8n workflows API ($code_n8n)"
    grep -Eo '"name":"[^"]+"' /tmp/n8n_workflows.out | head -n 20 || true
  else
    fail "n8n workflows API ($code_n8n)"
    sed -n '1,40p' /tmp/n8n_workflows.out || true
  fi
else
  fail "n8n verification skipped (set N8N_API_KEY env var)"
fi

echo "== Done =="
