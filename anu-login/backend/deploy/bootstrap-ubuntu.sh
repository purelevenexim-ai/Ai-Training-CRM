#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

APP_USER="${APP_USER:-anu-login}"
APP_DIR="${APP_DIR:-/opt/anu-login-backend}"
ENV_FILE="${ENV_FILE:-/etc/anu-login-backend.env}"
STATE_DIR="${STATE_DIR:-/var/lib/anu-login-backend}"
PORT="${PORT:-8000}"
SERVER_NAME="${SERVER_NAME:-}"
ENABLE_SSL="${ENABLE_SSL:-0}"

if [[ -z "$SERVER_NAME" ]]; then
  echo "SERVER_NAME is required, for example: SERVER_NAME=anu-api.example.com" >&2
  exit 1
fi

if [[ ! -f "$SCRIPT_DIR/.env.example" ]]; then
  echo "Missing deploy/.env.example next to this script." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y python3 python3-venv python3-pip nginx rsync

if ! id -u "$APP_USER" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
fi

mkdir -p "$APP_DIR" "$STATE_DIR"
chown -R "$APP_USER":www-data "$APP_DIR" "$STATE_DIR"

rsync -a --delete \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'deploy' \
  "$SOURCE_DIR/" "$APP_DIR/"

python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

if [[ ! -f "$ENV_FILE" ]]; then
  install -m 600 "$SCRIPT_DIR/.env.example" "$ENV_FILE"
fi

if ! grep -q '^ANU_LOGIN_DATABASE_PATH=' "$ENV_FILE"; then
  printf '\nANU_LOGIN_DATABASE_PATH=%s/anu_login.sqlite3\n' "$STATE_DIR" >> "$ENV_FILE"
fi

if ! grep -q '^ANU_LOGIN_ALLOWED_ORIGINS=' "$ENV_FILE"; then
  printf 'ANU_LOGIN_ALLOWED_ORIGINS=https://pureleven.com,https://www.pureleven.com\n' >> "$ENV_FILE"
fi

if ! grep -q '^ANU_LOGIN_DEFAULT_COUPON=' "$ENV_FILE"; then
  printf 'ANU_LOGIN_DEFAULT_COUPON=PURE10\n' >> "$ENV_FILE"
fi

sed \
  -e "s|__APP_USER__|$APP_USER|g" \
  -e "s|__APP_DIR__|$APP_DIR|g" \
  -e "s|__ENV_FILE__|$ENV_FILE|g" \
  -e "s|__PORT__|$PORT|g" \
  "$SCRIPT_DIR/anu-login-backend.service" > /etc/systemd/system/anu-login-backend.service

sed \
  -e "s|__SERVER_NAME__|$SERVER_NAME|g" \
  -e "s|__PORT__|$PORT|g" \
  "$SCRIPT_DIR/nginx.anu-login-backend.conf" > /etc/nginx/sites-available/anu-login-backend.conf

ln -sf /etc/nginx/sites-available/anu-login-backend.conf /etc/nginx/sites-enabled/anu-login-backend.conf
nginx -t

systemctl daemon-reload
systemctl enable anu-login-backend.service
systemctl restart anu-login-backend.service
systemctl reload nginx

if [[ "$ENABLE_SSL" == "1" ]]; then
  apt-get install -y certbot python3-certbot-nginx
  certbot --nginx -d "$SERVER_NAME" --non-interactive --agree-tos --register-unsafely-without-email --redirect
  systemctl reload nginx
fi

sleep 2
curl --fail --silent http://127.0.0.1:$PORT/api/health
printf '\nDeployment finished for %s\n' "$SERVER_NAME"
