#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env.production}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[ERROR] Env file not found: $ENV_FILE"
  exit 1
fi

required=(
  "ANU_LOGIN_ADMIN_SECRET"
  "WABIS_WEBHOOK_SECRET"
  "SHOPIFY_WEBHOOK_SECRET"
  "DELHIVERY_WEBHOOK_SECRET"
  "META_WEBHOOK_VERIFY_TOKEN"
  "GMB_ACCESS_TOKEN"
  "GMB_LOCATION_NAME"
)

missing=0
for key in "${required[@]}"; do
  if ! grep -q "^${key}=" "$ENV_FILE"; then
    echo "[MISSING] ${key}"
    missing=1
  fi
done

if [[ "$missing" -eq 1 ]]; then
  echo "[ERROR] Missing required secrets. Add them before deployment."
  exit 2
fi

# Check weak/default values quickly.
weak_patterns=(
  "changeme"
  "password"
  "secret"
  "test"
  "12345"
)

for key in "${required[@]}"; do
  value="$(grep "^${key}=" "$ENV_FILE" | head -n1 | cut -d'=' -f2-)"
  lower="$(echo "$value" | tr '[:upper:]' '[:lower:]')"
  if [[ ${#value} -lt 24 ]]; then
    echo "[WEAK] ${key} is too short (<24 chars)"
    missing=1
  fi
  for pat in "${weak_patterns[@]}"; do
    if [[ "$lower" == *"$pat"* ]]; then
      echo "[WEAK] ${key} contains weak pattern: $pat"
      missing=1
      break
    fi
  done
done

if [[ "$missing" -eq 1 ]]; then
  echo "[ERROR] Hardening checks failed."
  exit 3
fi

echo "[OK] Env hardening checks passed for $ENV_FILE"
