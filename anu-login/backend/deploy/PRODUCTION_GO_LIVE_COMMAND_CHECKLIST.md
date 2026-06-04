# Production Go-Live Command Checklist (Server Team)

This checklist assumes backend code is on the server and systemd is used.

## 0) Preconditions
- SSH access to production server
- DNS and TLS already configured
- `.env` has all required values

Required env checks:
- META_PHONE_NUMBER_ID
- META_ACCESS_TOKEN
- META_WEBHOOK_VERIFY_TOKEN
- META_OWNER_PHONE
- SHOPIFY_SHOP_DOMAIN
- SHOPIFY_ADMIN_API_TOKEN
- OPENROUTER_API_KEY
- DELHIVERY_API_TOKEN
- DELHIVERY_WEBHOOK_SECRET
- ANU_LOGIN_ADMIN_SECRET

## 1) Connect and deploy code
```bash
ssh <user>@<server>
cd /opt/anu-login-backend/backend
git fetch --all
git checkout main
git pull --ff-only
```

## 2) Python environment and dependencies
```bash
cd /opt/anu-login-backend/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3) Environment load and syntax sanity
```bash
cd /opt/anu-login-backend/backend
set -a
source .env
set +a
python -m py_compile app/main.py app/routes/ai_dispatch.py app/routes/monitoring.py app/intelligence/shopify_sync.py
```

## 4) Initialize database schema
```bash
cd /opt/anu-login-backend/backend
set -a
source .env
set +a
python - <<'PY'
from app.storage import init_database
init_database()
print('init_database ok')
PY
```

## 5) Run a one-time Shopify sync
```bash
cd /opt/anu-login-backend/backend
set -a
source .env
set +a
python - <<'PY'
from app.intelligence.shopify_sync import run_full_sync
print(run_full_sync())
PY
```

## 6) Restart service and confirm
```bash
sudo systemctl daemon-reload
sudo systemctl restart anu-login-backend.service
sudo systemctl status anu-login-backend.service --no-pager
journalctl -u anu-login-backend.service -n 100 --no-pager
```

## 7) API smoke tests
```bash
curl -s https://adsapi.pureleven.com/api/health
curl -s https://adsapi.pureleven.com/api/monitoring/health
curl -s https://adsapi.pureleven.com/api/ai/catalog
curl -s -X POST https://adsapi.pureleven.com/api/journey/orchestrate/preview \
  -H 'Content-Type: application/json' \
  -d '{"shop_domain":"rwxtic-gz.myshopify.com"}'
```

## 8) Webhook verification tests
```bash
# Meta webhook verify
curl -i "https://adsapi.pureleven.com/api/webhooks/meta/whatsapp?hub.mode=subscribe&hub.verify_token=<token>&hub.challenge=12345"

# Delhivery endpoint reachability
curl -i -X POST https://adsapi.pureleven.com/api/delhivery/webhook \
  -H 'Content-Type: application/json' \
  -H 'x-delhivery-signature: sha256=test' \
  -d '{"packages":[]}'
```

## 9) n8n activation order
1. Activate `01_shopify_catalog_sync`
2. Activate `02_daily_journey_preview`
3. Activate `03_daily_journey_orchestrate`
4. Activate webhook workflows 05, 06, 07
5. Activate `08_health_daily_report`
6. Activate `04_ai_followup_dispatch_webhook`

## 10) Rollout gates
- Gate A: 100-customer soft launch for 24h
- Gate B: 500-customer rollout after stable metrics
- Gate C: Full rollout after 48h stable operation

## 11) Rollback commands
```bash
# Stop n8n workflows (manual in n8n UI)
# Keep backend up, pause orchestrator calls

sudo systemctl restart anu-login-backend.service
curl -s https://adsapi.pureleven.com/api/monitoring/health
```

## 12) Post-go-live daily checks
```bash
curl -s https://adsapi.pureleven.com/api/monitoring/health
curl -s https://adsapi.pureleven.com/api/monitoring/dashboard
curl -s https://adsapi.pureleven.com/api/journey/orchestrate/status?shop_domain=rwxtic-gz.myshopify.com
```
