# Quick Start: Deploy in 3 Hours

**Timeline: 18 May 2026**
**Estimated Duration:** 3 hours total

---

## **STEP 0: Prerequisites (Do Now)**

Before starting deployment, collect these 8 credentials:

1. **Meta CAPI Access Token**
   - Go to: https://business.facebook.com/settings/system-users
   - Create or copy existing token
   - Expiration: Usually 1 year

2. **Google Ads Developer Token**
   - Go to: https://ads.google.com → Tools → API Center
   - Developer Token (admin approval required)

3. **Google Ads Conversion Action ID**
   - Go to: https://ads.google.com → Tools → Conversions
   - Select or create a conversion for "Offline purchases"
   - Copy the ID (looks like: 123456789)

4. **Google OAuth Refresh Token**
   - Need: OAuth2 credentials from Google Cloud Console
   - Get Refresh Token via OAuth flow

5. **GA4 API Secret**
   - Go to: https://analytics.google.com → Admin → Data API
   - Create API property access and get secret

6. **Shiprocket Webhook Token**
   - Go to: Shiprocket Dashboard → Settings → Webhooks
   - Enable and copy token

7. **Wabis API Token**
   - Go to: https://app.wabis.in/dashboard → API Keys
   - Copy your Bearer token

8. **Generate Internal API Key**
   - Generate a random 32-character string
   - Use for authenticating audience exports

⏱️ **Time: 30 minutes**

---

## **STEP 1: Prepare Server (.env)**

```bash
# SSH into server
ssh root@192.46.213.140

# Create/edit .env file in project root
cd /root/pureleven_dev
nano .env

# Add these lines (replace with your credentials):
META_CAPI_PIXEL_ID=609256704464862
META_CAPI_ACCESS_TOKEN=your_token_here
GADS_DEVELOPER_TOKEN=your_token_here
GADS_CUSTOMER_ID=1491516326
GADS_CONVERSION_ACTION_ID=123456789
GADS_OAUTH_REFRESH_TOKEN=your_refresh_token
GADS_OAUTH_CLIENT_ID=your_client_id
GADS_OAUTH_CLIENT_SECRET=your_client_secret
GA4_MEASUREMENT_ID=G-3FRSK7TEN2
GA4_API_SECRET=your_secret_here
SHIPROCKET_WEBHOOK_TOKEN=your_token_here
INTERNAL_API_KEY=randomly_generated_32_chars
PURELEVEN_INTERNAL_API_KEY=randomly_generated_32_chars

# Save and exit (Ctrl+X, Y, Enter)
```

⏱️ **Time: 5 minutes**

---

## **STEP 2: Deploy Code & Run Migration**

```bash
# SSH into server (if not already connected)
ssh root@192.46.213.140
cd /root/pureleven_dev

# Pull latest code
git pull origin main

# Run database migration
python alembic_migration_crm_v2.py

# Verify migration
psql -U postgres -d pureleven -c "SELECT COUNT(*) FROM unified_identity;"
# Should return: 0

# Restart API service
docker compose restart crm-api

# Wait 5 seconds for service to start
sleep 5

# Test API health
curl https://ai.pureleven.com/api/crm/health
# Should return: {"status": "healthy", "module": "crm"}
```

⏱️ **Time: 10 minutes**

---

## **STEP 3: Import N8N Workflows**

1. **Open N8N Dashboard**
   ```
   https://automation.pureleven.com
   ```

2. **Import Workflow 1: Checkout Abandonment**
   - Click: **+ New** → **Import workflow**
   - Copy entire contents of: `/Users/bthomas/Documents/pureleven_dev/n8n/workflow_checkout_abandonment.json`
   - Paste into N8N
   - Click **Import**

3. **Import Workflow 2: Cart Abandonment**
   - Repeat with: `workflow_cart_abandonment.json`

4. **Import Workflow 3: Replenishment**
   - Repeat with: `workflow_replenishment.json`

5. **Import Workflow 4: Winback**
   - Repeat with: `workflow_winback.json`

**Verify:** All 4 workflows appear in "Workflows" page

⏱️ **Time: 10 minutes**

---

## **STEP 4: Configure Wabis Credential**

For each workflow:

1. **Open Workflow** (e.g., Checkout Abandonment)
2. **Click any "WhatsApp" node** (e.g., "WhatsApp T+15min")
3. **Right panel → Credentials**
4. **Click** `httpHeaderAuth` dropdown
5. **Select** "Create new credential"
6. **Fill in:**
   - **Username:** `Authorization` (or blank)
   - **Password:** `Bearer {your-wabis-api-token}`
   
   (Get token from: https://app.wabis.in/dashboard → API Keys)

7. **Click** "Create credential"
8. **Click** "Test connection" → should show ✅

**Repeat for all 4 workflows**

⏱️ **Time: 15 minutes**

---

## **STEP 5: Create Wabis Message Templates**

Go to: https://app.wabis.in/dashboard → **Templates**

Create these 7 templates (copy-paste from DEPLOYMENT_CHECKLIST.md):

- [ ] `checkout_recovery_v1` — checkout recovery message
- [ ] `social_proof_v1` — social proof message
- [ ] `discount_offer_v1` — ₹100 discount offer
- [ ] `cart_recovery_v1` — cart abandonment reminder
- [ ] `replenishment_v1` — time to restock message
- [ ] `winback_v1` — 15% off comeback offer
- [ ] `winback_followup_v1` — new products follow-up

After creating each:
1. Click **Review**
2. Submit for approval
3. Wait for status = **"Approved"** (usually 5-10 min)

⏱️ **Time: 20 minutes**

---

## **STEP 6: Test Live Order**

1. **Open incognito/private browser window**
   ```
   https://pureleven.com
   ```

2. **Place test order:**
   - Add any product to cart
   - Click checkout
   - Email: `test+18may@example.com`
   - Phone: `9876543210`
   - Address: Any valid address
   - **Payment Method: COD** ⚠️ Important
   - Click **Place Order**

3. **Verify CRM captured order**
   ```
   https://ai.pureleven.com/static/dashboard.html
   → Search: test+18may@example.com
   → Should show order with gclid/fbclid/payment_method
   ```

4. **Verify Meta CAPI**
   ```
   https://business.facebook.com
   → Events Manager → Pixels → 609256704464862
   → Should show Purchase event within 30 seconds
   → Check: value = order amount, currency = INR
   ```

5. **Verify Google Ads**
   ```
   https://ads.google.com
   → Tools & Settings → Conversions
   → Should show offline conversion within 1-2 minutes
   → Check: conversion date/time matches order
   ```

6. **Verify GA4**
   ```
   https://analytics.google.com
   → Real-time
   → Should show purchase event
   → Check: value = order amount
   ```

✅ **All 3 platforms should show conversion within 2 minutes**

⏱️ **Time: 15 minutes**

---

## **STEP 7: Activate N8N Workflows**

### Workflow 1: Checkout Abandonment

1. Go to N8N → Workflows → **Checkout Abandonment Recovery**
2. Click **Activate** (top right)
3. Indicator should turn **green**
4. Monitor execution logs for 1 hour

### Workflow 2: Cart Abandonment

1. Go to N8N → Workflows → **Cart Abandonment Recovery**
2. Click **Activate**
3. Monitor for 30 minutes

### Workflow 3: Replenishment

1. Go to N8N → Workflows → **Replenishment Reminder**
2. Click **Activate**
3. Monitor for 1 day (runs daily at 10am)

### Workflow 4: Winback

1. Go to N8N → Workflows → **Winback (Lapsed Buyers)**
2. Click **Activate**
3. Monitor for 1 day (runs daily at 11am)

**Monitor Execution Logs:**
```
N8N Dashboard → Executions
Watch for:
✓ Green checkmarks = success
✗ Red X = error (click to see logs)
```

⏱️ **Time: 10 minutes**

---

## **SUMMARY**

| Step | Task | Time | Status |
|---|---|---|---|
| 0 | Collect credentials | 30 min | 🔴 DO FIRST |
| 1 | Set up server .env | 5 min | 🟡 Required |
| 2 | Deploy code & migration | 10 min | 🟡 Required |
| 3 | Import N8N workflows | 10 min | 🟡 Required |
| 4 | Configure Wabis credentials | 15 min | 🟡 Required |
| 5 | Create message templates | 20 min | 🟡 Required |
| 6 | Test live order | 15 min | 🟡 Validation |
| 7 | Activate workflows | 10 min | 🟡 Go-Live |
| **TOTAL** | | **~3 hours** | ✅ Ready |

---

## **MONITORING AFTER DEPLOYMENT**

### Daily Checks

```bash
# Check API is running
curl https://ai.pureleven.com/api/crm/health

# Check N8N workflows executed (no errors)
# Go to: automation.pureleven.com → Executions

# Check Wabis API logs for WhatsApp sends
# Go to: wabis.in → Logs → see recent messages
```

### Success Indicators

After workflows are active, you should see:
- ✅ N8N executions with green checkmarks
- ✅ WhatsApp messages in Wabis logs
- ✅ Customer responses in CRM
- ✅ Revenue tracking in Shopify

---

## **TROUBLESHOOTING QUICK LINKS**

| Issue | Check | Fix |
|---|---|---|
| API returns 500 | Docker logs | `docker logs crm-api` |
| N8N workflow fails | Execution log | Click failed run in N8N |
| WhatsApp doesn't send | Wabis logs | Check template status, phone format |
| Meta CAPI no event | Event Manager | Verify token, pixel ID, email hash |
| Google Ads no conversion | Conversions page | Verify gclid captured, action ID correct |

---

**Ready? Start with Step 0 now! 🚀**

