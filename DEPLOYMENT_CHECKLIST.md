# Pureleven Unified Tracking System — Deployment Checklist

**Status: Ready for Production Deployment**
**Date: 18 May 2026**

---

## **PHASE 1: Environment Variables (Server)**

### Required Credentials

Set these in `.env` on server (IP: 192.46.213.140):

```bash
# Meta Conversions API (CAPI)
META_CAPI_PIXEL_ID=609256704464862
META_CAPI_ACCESS_TOKEN=<get-from-meta-dashboard>
META_CAPI_TEST_CODE=<optional-for-testing>

# Google Ads Offline Conversions
GADS_DEVELOPER_TOKEN=<get-from-google-ads-manager>
GADS_CUSTOMER_ID=1491516326            # Formatted: 149-516-3260
GADS_CONVERSION_ACTION_ID=<get-from-google-ads-conversions>
GADS_OAUTH_CLIENT_ID=<get-from-google-cloud>
GADS_OAUTH_CLIENT_SECRET=<get-from-google-cloud>
GADS_OAUTH_REFRESH_TOKEN=<get-from-oauth-flow>

# GA4 Measurement Protocol
GA4_MEASUREMENT_ID=G-3FRSK7TEN2
GA4_API_SECRET=<get-from-ga4-settings>

# Shiprocket Delivery Webhook
SHIPROCKET_WEBHOOK_TOKEN=<get-from-shiprocket-account>

# N8N / Internal API
INTERNAL_API_KEY=<generate-random-32char>
PURELEVEN_INTERNAL_API_KEY=<same-as-above>

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/pureleven
```

### Where to Get Each Credential

**Meta CAPI:**
- Go to: https://business.facebook.com
- Account Settings → Users and Permissions → System Users
- Create new token or use existing (expires annually)

**Google Ads:**
- Go to: https://myaccount.google.com/device-activity
- Create OAuth2 credentials in Google Cloud Console
- Get Refresh Token via OAuth flow

**GA4:**
- Go to: Admin → Data Streams → View Stream Details
- Find Measurement ID (G-xxxxx)
- Settings → Integrations → Data API
- Create new Data API property and get secret

**Shiprocket:**
- Go to: Shiprocket Dashboard → Settings → Webhooks
- Enable webhook and copy token

---

## **PHASE 2: Database Migration**

```bash
# SSH into server
ssh root@192.46.213.140

# Navigate to project
cd /path/to/pureleven_dev

# Run migration (creates unified_identity table + adds attribution columns)
python alembic_migration_crm_v2.py

# Expected output:
# ✓ Created table unified_identity
# ✓ Added gclid, fbclid, session_id to crm_customers
# ✓ Added gclid, fbclid, payment_method, delivered_at, rto to crm_orders
# ✓ Added session_id, n8n_notified to crm_events
```

### Verify Migration
```bash
psql -U postgres -d pureleven -c "
SELECT table_name FROM information_schema.tables 
WHERE table_name = 'unified_identity';
"
# Should return: unified_identity
```

---

## **PHASE 3: Deploy New Code**

```bash
# Pull latest code
git pull origin main

# Restart FastAPI service
docker compose restart crm-api

# Verify health endpoint
curl https://track.pureleven.com/api/crm/health
# Response: {"status": "healthy", "module": "crm"}
```

---

## **PHASE 4: Test API Endpoints**

### Test 1: Identify Endpoint
```bash
curl -X POST https://track.pureleven.com/api/crm/identify \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-123",
    "email": "test@example.com",
    "phone": "9876543210",
    "utm_source": "google"
  }'

# Expected response:
# {"identity_id": "abc-123-uuid", "is_new": true}
```

### Test 2: Abandonment Endpoints
```bash
# Checkout abandonment
curl https://track.pureleven.com/api/crm/abandonment/checkout?window_minutes=15

# Should return:
# {"count": 0, "candidates": []}
```

### Test 3: Audience Export
```bash
curl https://track.pureleven.com/api/crm/audiences/high_ltv/export?format=meta \
  -H "Authorization: Bearer $INTERNAL_API_KEY"

# Should return hashed audience:
# {"segment": "high_ltv", "count": 12, "data": [...]}
```

---

## **PHASE 5: Import N8N Workflows**

### Step 1: Access N8N Dashboard
```
URL: https://automation.pureleven.com
```

### Step 2: Import Each Workflow
1. Go to **Workflows**
2. Click **+ New** → **Import workflow**
3. Copy entire contents of each JSON file:
   - `n8n/workflow_checkout_abandonment.json`
   - `n8n/workflow_cart_abandonment.json`
   - `n8n/workflow_replenishment.json`
   - `n8n/workflow_winback.json`
4. Paste and click **Import**

### Step 3: Configure Wabis API Credential
For **each workflow**:
1. Click any "WhatsApp" node (e.g., "WhatsApp T+15min")
2. In the right panel, click **Credentials** 
3. Select `httpHeaderAuth`
4. Click **Create new**
5. Fill in:
   - **Username:** `Authorization` (or leave blank)
   - **Password:** `Bearer {your-wabis-api-token}`
   
   Get your Wabis API token:
   - Go to: https://app.wabis.in/dashboard
   - Navigate to **API Keys**
   - Copy your **Bearer token**

6. Click **Save**
7. Click **Test connection** → should show ✓

### Step 4: Update Wabis API Base URL
In each workflow, update the Wabis URL:
- Change from: `https://api.wabis.in/v1/send-template`
- To: `https://api.wabis.in/v1/send-template` (usually correct)
- Or check your Wabis dashboard for custom endpoint

---

## **PHASE 6: Create/Verify Wabis Message Templates**

Go to: https://app.wabis.in/dashboard → **Templates**

Create these 7 templates (or verify they exist):

### Template 1: `checkout_recovery_v1`
```
Category: Marketing
Message:
Hi {{1}}, your order is waiting! 🛒

Complete checkout now with COD available ✓
Limited inventory!

[BUTTON: Continue Shopping]
```

### Template 2: `social_proof_v1`
```
Category: Marketing
Message:
500+ happy customers across India love our Kerala spices 🌶️

{{1}}, join them today!
Free shipping on orders above ₹500

[BUTTON: Shop Now]
```

### Template 3: `discount_offer_v1`
```
Category: Marketing
Message:
Hi {{1}}, we've got a special offer for you! 🎉

Use code: {{2}}
Get ₹100 OFF! 💰

Offer valid for 24 hours only ⏰

[BUTTON: Claim Offer]
```

### Template 4: `cart_recovery_v1`
```
Category: Marketing
Message:
Hi {{1}}, you left something in your cart 👜

Grab your Kerala spices before they run out! 🌶️

[BUTTON: Back to Cart]
```

### Template 5: `replenishment_v1`
```
Category: Marketing
Message:
Time to restock your Kerala spices, {{1}}! 🌶️

Your favorite blends are waiting...
FREE SHIPPING on reorders 🚚

[BUTTON: Reorder Now]
```

### Template 6: `winback_v1`
```
Category: Marketing
Message:
We miss you, {{1}}! 😢

Come back for something special:
Use code {{2}} for 15% OFF

Valid for 48 hours only ⏰

[BUTTON: Shop Now]
```

### Template 7: `winback_followup_v1`
```
Category: Marketing
Message:
{{1}}, exciting news! 🎉

New premium spices just arrived from Kerala 🌶️
Fresh, authentic, direct from farms

[BUTTON: See What's New]
```

**Status Check:**
After creating templates, go to **Templates** and verify all 7 show as "Approved" ✅

---

## **PHASE 7: Test Live Order Flow**

### Pre-Test Checklist
- [ ] All env vars set on server
- [ ] Migration run successfully
- [ ] Code deployed & API health = 200
- [ ] N8N workflows imported & Wabis credentials set
- [ ] Wabis templates created & approved

### Test Order Steps

1. **Clear Browser Cache** (to reset session_id)
   ```
   Open incognito/private window
   ```

2. **Place Test Order on Pureleven**
   ```
   Go to: https://pureleven.com
   - Select any product
   - Add to cart
   - Proceed to checkout
   - Email: test+20260518@example.com
   - Phone: 9876543210
   - Address: Any
   - Payment: Select COD
   - COMPLETE ORDER
   ```

3. **Verify CRM Capture** (CRM Dashboard)
   ```
   Go to: https://ai.pureleven.com/static/dashboard.html
   - Navigate to Customers
   - Search for: test+20260518@example.com
   - Verify order appears with:
     ✓ gclid / fbclid captured
     ✓ payment_method = "cod"
     ✓ status = "pending"
   ```

4. **Verify Meta CAPI** (should fire on orders/paid)
   ```
   Go to: https://business.facebook.com → Pixels → 609256704464862
   - Navigate to Events
   - Should show Purchase event within 30 seconds
   - Check: timestamp, value (₹ amount), currency
   ```

5. **Verify Google Ads** (should show offline conversion)
   ```
   Go to: https://ads.google.com → Conversions
   - Should show new conversion within 1-2 minutes
   - Check: conversion date/time matches order
   ```

6. **Verify GA4**
   ```
   Go to: https://analytics.google.com → Real-time
   - Should show purchase event
   - Check: transaction_id = order_id
   ```

7. **Simulate Delivery** (trigger Shiprocket webhook)
   ```bash
   # Manually insert Shiprocket payload (or Shiprocket will send this):
   curl -X POST https://track.pureleven.com/api/crm/webhooks/shiprocket \
     -H "Content-Type: application/json" \
     -H "X-Shiprocket-Hmac-Sha256: $(echo -n '{payload}' | openssl dgst -sha256 -hmac 'token' | cut -d' ' -f2)" \
     -d '{
       "order_id": "YOUR_TEST_ORDER_ID",
       "current_status": "Delivered",
       "tracking_number": "SHP123456"
     }'
   
   # Should see 2nd conversion in Meta CAPI + Google Ads with event_id="delivery_*"
   ```

---

## **PHASE 8: Enable N8N Workflows One-by-One**

### Enable Workflow 1: Checkout Abandonment
1. Go to N8N Dashboard → **Workflows** → **Checkout Abandonment Recovery**
2. Click **Activate** (top right)
3. Expected: Workflow active indicator turns green
4. Test: 
   - Manually insert `checkout_start` event (no purchase after)
   - Wait up to 5 minutes
   - Should see Wabis API logs show WhatsApp sent
5. Monitor for 1 hour, then proceed

### Enable Workflow 2: Cart Abandonment
1. Go to N8N Dashboard → **Workflows** → **Cart Abandonment Recovery**
2. Click **Activate**
3. Monitor for 30 minutes

### Enable Workflow 3: Replenishment
1. Go to N8N Dashboard → **Workflows** → **Replenishment Reminder**
2. Click **Activate**
3. Monitor for 1 day (runs daily at 10am)

### Enable Workflow 4: Winback
1. Go to N8N Dashboard → **Workflows** → **Winback (Lapsed Buyers)**
2. Click **Activate**
3. Monitor for 1 day (runs daily at 11am)

### Monitor Workflow Execution
```
N8N Dashboard → Executions
- Look for green checkmarks (success)
- Look for red X marks (failure)
- Click on execution to see logs
```

---

## **Verification Summary**

| Component | Status | How to Verify |
|---|---|---|
| Server env vars | ✅ Set | `echo $META_CAPI_ACCESS_TOKEN` on server |
| Database migration | ✅ Run | `psql -c "SELECT COUNT(*) FROM unified_identity"` |
| API health | ✅ 200 | `curl https://track.pureleven.com/api/crm/health` |
| N8N workflows | ✅ Imported | Visible in N8N Workflows page |
| Wabis credential | ✅ Tested | Green checkmark in N8N credential list |
| Live order | ✅ Tested | Meta CAPI + Google Ads show conversions |
| N8N active | ✅ Running | Green indicator on all 4 workflows |

---

## **PHASE 9: Monitoring & Observability**

### Daily Checks
```bash
# Check CRM API is running
curl https://track.pureleven.com/api/crm/health

# Check N8N workflows are executing (no errors)
# Go to: automation.pureleven.com → Executions

# Check Wabis API logs for WhatsApp sends
# Go to: wabis.in → Logs
```

### Error Handling

**If Meta CAPI fails:**
- Check: `META_CAPI_ACCESS_TOKEN` expiration
- Token expires annually → renew at business.facebook.com

**If Google Ads conversion doesn't appear:**
- Check: `GADS_OAUTH_REFRESH_TOKEN` still valid
- Verify: `GADS_CONVERSION_ACTION_ID` matches setup
- Check logs: `docker logs crm-api | grep "Google Ads"`

**If N8N workflow doesn't run:**
- Check: N8N container is up: `docker ps | grep n8n`
- Check: Workflow is **Activated** (not paused)
- Check: Wabis credential is valid (test connection)
- Verify: CRM API endpoint is reachable from N8N container

**If Wabis WhatsApp doesn't send:**
- Check: Template exists and is **Approved** in Wabis dashboard
- Verify: Phone number is in international format (91XXXXXXXXXX)
- Check: Wabis account has credit/monthly limit
- Check: N8N logs: `automation.pureleven.com → Executions`

---

## **ROLLBACK Plan**

If critical issue found:

```bash
# Disable all N8N workflows
# (In N8N UI: click Deactivate on each)

# Rollback code to previous version
git revert HEAD

# Restart API
docker compose restart crm-api

# Notify team
```

---

**Next Step:** Execute Phase 1-5, then run test order (Phase 7), then enable workflows (Phase 8).

