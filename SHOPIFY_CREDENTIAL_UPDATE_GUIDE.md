# Shopify Credential Update Guide

**Updated:** May 20, 2026  
**Tokens Refreshed:** New wabis custom app install

## New Credentials

```text
Shopify Admin API Token:  <SHOPIFY_ADMIN_TOKEN>
API Key (Client ID):      <SHOPIFY_CLIENT_ID>
API Secret:               <SHOPIFY_CLIENT_SECRET>
wabis App ID:             <SHOPIFY_APP_ID>
Store:                    <SHOPIFY_STORE_DOMAIN>
```

---

## ✅ Places These Credentials Are Used

### 1. **VPS Environment Variables** (Production)
**Path:** `/opt/pureleven/ai-engine/.env`  
**Status:** ✅ ALREADY UPDATED (in previous session)

```env
SHOPIFY_STORE_URL=https://<SHOPIFY_STORE_DOMAIN>
SHOPIFY_CLIENT_ID=<SHOPIFY_CLIENT_ID>
SHOPIFY_CLIENT_SECRET=<SHOPIFY_CLIENT_SECRET>
SHOPIFY_ADMIN_TOKEN=<SHOPIFY_ADMIN_TOKEN>
```

**Update Command:**
```bash
ssh root@192.46.213.140
nano /opt/pureleven/ai-engine/.env
# Update the 4 fields above
docker restart pureleven-ai-engine
```

---

### 2. **Anu-Login Admin App** (OAuth-based Shopify embedded app)
**Path:** `anu-login/app/anu-login-admin/.env` or deployment environment  
**Usage:** For customer login via Shopify OAuth

**Variables to set:**
```env
SHOPIFY_API_KEY=<SHOPIFY_API_KEY>
SHOPIFY_API_SECRET=<SHOPIFY_API_SECRET>
SHOPIFY_APP_URL=https://ai.pureleven.com/anu-login  # Or deployment URL
SCOPES=read_products,write_orders,read_customers
```

**Note:** This app uses OAuth, not the admin token. The API key/secret are used for OAuth handshake.

---

### 3. **Local Development Scripts**
All scripts in `/Users/bthomas/Documents/pureleven_dev/scripts/` accept token as CLI argument:

```bash
# Don't hardcode — pass token as argument:
python3 scripts/shopify_setup.py --token "$SHOPIFY_ADMIN_TOKEN"
python3 scripts/export_meta_audience_csv.py --token "$SHOPIFY_ADMIN_TOKEN"
```

---

### 4. **Any Third-Party Apps** (n8n, webhooks handlers, integrations)
If you have integrations with:
- **n8n workflows:** Update Shopify node credentials
- **Zapier/Make:** Update Shopify connection
- **Custom integrations:** Use token from VPS `.env` (read from CRM API)

---

### 5. **Shopify Admin UI** (Verification)
**Path:** Shopify Admin → Settings → Apps → Develop apps → wabis  
**Verify:**
1. Go to [Configuration](https://admin.shopify.com/store/rwxtic-gz/settings/apps/development/272184377345/configuration)
2. Admin API credentials should show the configured API key
3. The displayed token should match the value stored in your private environment

---

## 🔄 Workflow: Using These Credentials

### For Local Development / Scripts:
```bash
# Use the admin token directly
python3 scripts/shopify_setup.py --token "$SHOPIFY_ADMIN_TOKEN"
```

### For Web Apps / VPS Services:
```bash
# Read from VPS environment variables
# They're already loaded in .env on the server
```

### For Customer-Facing OAuth (Anu-Login):
```bash
# Uses API Key + Secret for OAuth flow
# Token is obtained via authorization code
```

---

## 🚨 Security Notes

- ✅ **DO NOT commit `.env` files to git**
- ✅ **DO NOT share tokens in public channels**
- ✅ Tokens should only be in:
  - VPS `.env` file (encrypted in server)
  - Secure environment variables in deployment platforms
  - CLI arguments (for one-off scripts)
- ✅ **Rotate tokens** if ever leaked or compromised

---

## 📋 Verification Checklist

After updating all credentials:

- [ ] VPS `.env` updated
- [ ] Anu-Login `.env` updated (if using)
- [ ] All third-party integrations updated
- [ ] Docker container restarted on VPS
- [ ] Test: Run `python3 scripts/shopify_setup.py` with new token
- [ ] Verify Shopify webhooks are active
- [ ] Test CRM customer/order imports

---

## 📞 Quick Support

**Issue:** Token doesn't work  
**Solution:** Verify token on Shopify Admin → Apps → wabis → Configuration

**Issue:** Webhooks failing  
**Solution:** Check Docker logs: `docker logs -f pureleven-ai-engine`

**Issue:** Third-party app failing  
**Solution:** Ensure `.env` file is reloaded (restart service)
