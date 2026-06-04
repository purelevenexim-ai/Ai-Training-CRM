#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env.production}"
BACKUP_FILE="${ENV_FILE}.bak.$(date +%Y%m%d%H%M%S)"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[ERROR] Env file not found: $ENV_FILE"
  exit 1
fi

cp "$ENV_FILE" "$BACKUP_FILE"
echo "[INFO] Backup created: $BACKUP_FILE"

generate_secret() {
  openssl rand -hex 32
}

replace_or_add() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i '' "s|^${key}=.*$|${key}=${value}|" "$ENV_FILE"
  else
    echo "${key}=${value}" >> "$ENV_FILE"
  fi
}

# Rotate internal/shared secrets only.
replace_or_add "ANU_LOGIN_ADMIN_SECRET" "$(generate_secret)"
replace_or_add "WABIS_WEBHOOK_SECRET" "$(generate_secret)"
replace_or_add "SHOPIFY_WEBHOOK_SECRET" "$(generate_secret)"
replace_or_add "DELHIVERY_WEBHOOK_SECRET" "$(generate_secret)"
replace_or_add "META_WEBHOOK_VERIFY_TOKEN" "$(generate_secret)"

echo "[OK] Secret rotation completed for internal webhook/admin secrets."
echo "[ACTION REQUIRED] Rotate third-party credentials manually in provider dashboards (Meta, Google, Shopify, Wabis), then update $ENV_FILE."
