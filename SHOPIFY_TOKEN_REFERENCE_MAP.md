# Shopify Credentials - Quick Reference Map

**Last Updated:** May 20, 2026  
**Tokens:** `<SHOPIFY_ADMIN_TOKEN>` | `<SHOPIFY_CLIENT_ID>` | `<SHOPIFY_CLIENT_SECRET>`

---

## 🗺️ Token Usage Map

### PRODUCTION - VPS Environment

| File | Variables | Usage | Status |
|---|---|---|---|
| `/opt/pureleven/ai-engine/.env` | `SHOPIFY_STORE_URL`, `SHOPIFY_CLIENT_ID`, `SHOPIFY_CLIENT_SECRET`, `SHOPIFY_ADMIN_TOKEN`, `SHOPIFY_API_VERSION`, `SHOPIFY_WEBHOOK_SECRET` | CRM backend for Shopify API calls | ✅ UPDATED |
| Docker Compose | Passed to container via `.env` | Runtime environment for `pureleven-ai-engine` | ✅ ACTIVE |
| `/opt/pureleven/ai-engine/app/crm_routes.py` | Reads from environment | Webhook handlers & API integration | ✅ WORKING |
| PostgreSQL | Stores webhook data | Historical orders/customers/carts | ✅ SYNCED |

---

### LOCAL DEVELOPMENT - Scripts

| File | Variables | Usage | Status |
|---|---|---|---|
| `scripts/shopify_setup.py` | `--token` CLI arg | Register webhooks + import data | ✅ TESTED |
| `scripts/export_meta_audience_csv.py` | `--token` CLI arg | Export customers for Meta | ✅ READY |
| `scripts/create_google_audience_v2.py` | (reads from VPS env) | Google Ads integration | ✅ CONFIGURED |

**How to use locally:**
```bash
python3 scripts/shopify_setup.py --token <SHOPIFY_ADMIN_TOKEN>
python3 scripts/export_meta_audience_csv.py --token <SHOPIFY_ADMIN_TOKEN>
```

---

### WEB APPS - OAuth Integration

| File | Variables | Usage | Status |
|---|---|---|---|
| `anu-login/app/anu-login-admin/app/shopify.server.js` | `SHOPIFY_API_KEY`, `SHOPIFY_API_SECRET` | OAuth handshake for customer login | ⚠️ NEEDS UPDATE if deployed |
| `anu-login/app/anu-login-admin/app/routes/app.jsx` | Reads API key from env | Frontend app configuration | ⚠️ NEEDS UPDATE if deployed |
| `.env` (deployment) | Environment variables | OAuth & app config | ⚠️ NEEDS UPDATE if deployed |

**If deploying anu-login:** Update with:
```env
SHOPIFY_API_KEY=<SHOPIFY_CLIENT_ID>
SHOPIFY_API_SECRET=<SHOPIFY_CLIENT_SECRET>
```

---

### THIRD-PARTY INTEGRATIONS

| Platform | Configuration | Status |
|---|---|---|
| **n8n** (`automations.pureleven.com`) | Shopify node credentials | ⚠️ CHECK if manually configured |
| **Zapier/Make** | Shopify connection settings | ⚠️ CHECK if in use |
| **Custom webhooks** | Use CRM API (`track.pureleven.com`) | ✅ AUTO-MANAGED |
| **Analytics/GA4** | Shopify events relay | ✅ CONFIGURED |

---

### DOCUMENTATION - Reference Only

These are just documentation files (no functional updates needed):

| File | Purpose |
|---|---|
| `PROJECT_COMPLETE_README.md` | Setup guide documentation |
| `PHASE_3_IMPLEMENTATION_GUIDE.md` | Phase 3 instructions |
| `shopify_oauth_server.py` | OAuth flow example code |
| `shopify_oauth_vps_instructions.py` | VPS setup instructions |
| `CRM_MASTER_README.md` | CRM system documentation |

---

## 📊 Token Purpose & Scopes

### Admin API Token (`<SHOPIFY_ADMIN_TOKEN>`)
- **Type:** Custom app access token
- **Scopes:** 130 scopes (all except `read_analytics`)
- **Created:** May 20, 2026 via wabis app reinstall
- **Used for:** 
  - Registering webhooks
  - Fetching orders/customers/carts
  - Admin API read/write operations
- **Rotation:** Requires uninstall/reinstall of wabis app

### API Key/Client ID (`<SHOPIFY_CLIENT_ID>`)
- **Type:** Custom app public identifier
- **Used for:** OAuth flow initiation (anu-login app)
- **Visible in:** Shopify Admin UI settings
- **Paired with:** API Secret for secure OAuth handshake

### API Secret (`<SHOPIFY_CLIENT_SECRET>`)
- **Type:** Custom app private key
- **Used for:** Secure OAuth token exchange
- **Visibility:** Server-side only (never exposed to client)
- **Required with:** API Key for OAuth validation

---

## 🔄 Update Workflow When Tokens Change

1. **Update VPS `.env`**
   ```bash
   ssh root@192.46.213.140
   nano /opt/pureleven/ai-engine/.env
   # Edit: SHOPIFY_ADMIN_TOKEN, SHOPIFY_CLIENT_ID, SHOPIFY_CLIENT_SECRET
   docker restart pureleven-ai-engine
   ```

2. **Test locally** (if modifying scripts)
   ```bash
   python3 scripts/shopify_setup.py --token <SHOPIFY_ADMIN_TOKEN>
   ```

3. **Update anu-login** (if deployed)
   - Update deployment environment variables
   - Redeploy the application

4. **Check third-party integrations**
   - n8n: Shopify node credentials
   - Zapier: Shopify connection
   - Any custom integrations

5. **Verify all systems**
   - Test webhooks
   - Import test order
   - Check CRM database

---

## 🚨 Emergency Token Rotation

If token is compromised:

1. **Disable immediately** in Shopify Admin:
   ```
   Settings → Apps → Develop apps → wabis → Uninstall
   ```

2. **Create new app:**
   ```
   Settings → Apps → Create app → Name: wabis-v2
   Add same scopes, install, get new token
   ```

3. **Update all locations:**
   - VPS `.env`
   - All scripts
   - Deployed apps
   - Third-party integrations

4. **Test thoroughly** before removing old token

---

## ✅ Verification Checklist

After any update, verify:

- [ ] VPS `.env` has correct values
- [ ] Docker container restarted
- [ ] `GET /health` endpoint responds
- [ ] Webhooks are registered
- [ ] Test API call works
- [ ] CRM receives webhook data
- [ ] Third-party apps still working
- [ ] No hardcoded tokens in code

---

## 📍 Current Status (May 20, 2026)

```
Production (VPS):          ✅ UPDATED & VERIFIED
Local scripts:             ✅ READY (pass token as argument)
Anu-login app:             ⚠️  UPDATE IF DEPLOYED
Third-party integrations:  ⚠️  CHECK AS NEEDED
Webhooks:                  ✅ ALL 9 ACTIVE
Historical data:           ✅ 250 orders + 250 customers
```

---

**Maintained by:** Copilot Automation  
**Last verified:** May 20, 2026 05:24 UTC  
**Environment:** Production (192.46.213.140)
