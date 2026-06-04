# 🚀 PURELEVEN UNIFIED TRACKING SYSTEM — MASTER DEPLOYMENT GUIDE

**Status:** 70% Code Ready | 30% Deployment Phase  
**Est. Time to Live:** 2.5 hours  
**Date:** 18 May 2026

---

## **📋 COMPLETE CHECKLIST**

### **PHASE 0: PREPARATION (30 min) — DO FIRST**

Get these 8 credentials now:

```bash
☐ 1. META_CAPI_ACCESS_TOKEN
     Go to: https://business.facebook.com/settings/system-users
     
☐ 2. GADS_DEVELOPER_TOKEN
     Go to: https://ads.google.com → Tools → API Center
     
☐ 3. GADS_OAUTH_REFRESH_TOKEN
     Go to: Google Cloud Console → OAuth 2.0 Credentials
     
☐ 4. GADS_CONVERSION_ACTION_ID
     Go to: https://ads.google.com → Conversions → Create/Select
     
☐ 5. GA4_API_SECRET
     Go to: https://analytics.google.com → Admin → Data API
     
☐ 6. SHIPROCKET_WEBHOOK_TOKEN
     Go to: Shiprocket Dashboard → Settings → Webhooks
     
☐ 7. WABIS_API_TOKEN
     Go to: https://app.wabis.in → Dashboard → API Keys
     
☐ 8. INTERNAL_API_KEY
     Generate: Random 32-char string (use: `openssl rand -base64 32`)
```

---

### **PHASE 1: DEPLOY TO SERVER (15 min)**

```bash
# SSH to server
ssh root@192.46.213.140

# Navigate to project
cd /root/pureleven_dev

# Update .env with 8 credentials
nano .env
# Paste all 8 credentials
# Save: Ctrl+X, Y, Enter

# Deploy code
git pull origin main
python alembic_migration_crm_v2.py
docker compose restart crm-api

# Verify
curl https://ai.pureleven.com/api/crm/health
# Should return: {"status": "healthy", "module": "crm"}
```

✅ **Checkpoint:** API returns 200 OK

---

### **PHASE 2: IMPORT N8N WORKFLOWS (15 min)**

1. Open: https://automation.pureleven.com
2. Click: **+ New** → **Import workflow**
3. For each file:
   ```
   ☐ n8n/workflow_checkout_abandonment.json
   ☐ n8n/workflow_cart_abandonment.json
   ☐ n8n/workflow_replenishment.json
   ☐ n8n/workflow_winback.json
   ```
4. Copy → Paste → Click **Import**

✅ **Checkpoint:** 4 workflows visible in N8N

---

### **PHASE 3: CONFIGURE WABIS (20 min)**

1. For **each N8N workflow**, click any "WhatsApp" node
2. Right panel → **Credentials** dropdown
3. Click **Create new credential**:
   ```
   Type: httpHeaderAuth
   Username: (leave blank)
   Password: Bearer {your-wabis-api-token}
   ```
4. Click **Test connection** ✓
5. Click **Create credential**

✅ **Checkpoint:** All workflows have green ✓ credential check

---

### **PHASE 4: CREATE MESSAGE TEMPLATES (20 min)**

Go to: https://app.wabis.in → **Templates**

Create 7 templates (copy from `DEPLOYMENT_CHECKLIST.md`):

```
☐ checkout_recovery_v1      → "Your order is waiting!"
☐ social_proof_v1            → "500+ happy customers..."
☐ discount_offer_v1          → "Use code PL100OFF for ₹100 OFF"
☐ cart_recovery_v1           → "You left something in cart"
☐ replenishment_v1           → "Time to restock your spices!"
☐ winback_v1                 → "We miss you! 15% off"
☐ winback_followup_v1        → "New products just arrived"
```

**Wait for status = "Approved"** ✓ (5-10 min each)

✅ **Checkpoint:** All 7 templates show "Approved"

---

### **PHASE 5: TEST LIVE ORDER (20 min)**

1. Open **incognito** window → https://pureleven.com
2. Add product to cart
3. **Proceed to checkout**
   - Email: `test+18may@example.com`
   - Phone: `9876543210`
   - Address: Any valid address
   - **Payment: COD** ⚠️ Important
   - Click **Place Order**

4. **Verify CRM Dashboard**
   ```
   https://ai.pureleven.com/static/dashboard.html
   Search: test+18may
   ✓ Order appears with gclid/fbclid/payment_method=cod
   ```

5. **Verify Meta CAPI**
   ```
   https://business.facebook.com
   Events Manager → Pixels → 609256704464862
   ✓ Purchase event appears within 30 seconds
   Check: value = order amount, currency = INR
   ```

6. **Verify Google Ads**
   ```
   https://ads.google.com → Tools → Conversions
   ✓ Offline conversion appears within 1-2 minutes
   ```

7. **Verify GA4**
   ```
   https://analytics.google.com → Real-time
   ✓ Purchase event appears
   ```

✅ **Checkpoint:** All 3 platforms (Meta, Google, GA4) show conversion

---

### **PHASE 6: ACTIVATE WORKFLOWS (10 min)**

In N8N Dashboard:

```bash
☐ Workflow 1: Checkout Abandonment
  Click: Activate (top right)
  Monitor: 1 hour for execution logs
  
☐ Workflow 2: Cart Abandonment
  Click: Activate
  Monitor: 30 minutes
  
☐ Workflow 3: Replenishment
  Click: Activate
  Monitor: Until next 10am run (daily)
  
☐ Workflow 4: Winback
  Click: Activate
  Monitor: Until next 11am run (daily)
```

Watch: `automation.pureleven.com → Executions`
Look for: ✅ Green checkmarks (success)
No: ❌ Red X (errors)

✅ **Checkpoint:** All 4 workflows show green ✓

---

## **✅ YOU'RE LIVE!**

```
Congratulations! The system is now:

✓ Tracking all visitors (session_id, gclid, fbclid)
✓ Capturing abandonment events
✓ Sending server-side conversions to Meta/Google/GA4
✓ Attributing delivery (COD proof)
✓ Classifying audiences in real-time
✓ Sending WhatsApp retargeting messages
✓ Automating customer recovery
```

---

## **📊 WHAT HAPPENS NOW**

### **Every Minute**
- Visitors tracked in real-time
- Abandonment events captured
- Conversions sent to Meta/Google

### **Every 5 Minutes (N8N)**
- Poll for checkout abandonments
- Send WhatsApp recovery messages
- Mark as notified (prevent duplicates)

### **Every 10 Minutes (N8N)**
- Poll for cart abandonments
- Send WhatsApp cart recovery

### **Daily 10am (N8N)**
- Export replenishment audience (30-50 days)
- Send WhatsApp: "Time to restock!"

### **Daily 11am (N8N)**
- Export lapsed buyer audience (60+ days)
- Send WhatsApp: "We miss you! 15% off"

---

## **📈 EXPECTED RESULTS**

| Metric | Target | Timeline |
|---|---|---|
| Checkout recovery rate | 5% | Within 48 hours |
| Cart recovery rate | 3% | Within 1 week |
| Replenishment rate | 15% | Within 2 weeks |
| Winback rate | 8% | Within 3 weeks |
| WhatsApp click rate | 25% | Within 1 week |
| Avg. cost per order | < ₹200 | Within 2 weeks |

---

## **🔍 DAILY MONITORING**

```bash
# Every morning, check:

☐ API health
  curl https://ai.pureleven.com/api/crm/health

☐ N8N execution logs (no errors)
  automation.pureleven.com → Executions

☐ Wabis WhatsApp sends
  wabis.in → Logs → Recent messages

☐ CRM metrics
  ai.pureleven.com/static/dashboard.html

☐ Conversion attribution
  • Meta: business.facebook.com → Events Manager
  • Google: ads.google.com → Conversions
  • GA4: analytics.google.com → Real-time
```

---

## **🆘 IF SOMETHING BREAKS**

### **API Returns Error 500**
```bash
ssh root@192.46.213.140
docker logs crm-api | tail -50
docker compose restart crm-api
```

### **N8N Workflow Failed**
```
1. Go to automation.pureleven.com → Executions
2. Click failed workflow
3. See error logs
Usually: Wabis token expired or template missing
```

### **WhatsApp Not Sending**
```
1. Check: Template exists in wabis.in and status = "Approved"
2. Check: Phone number is 91XXXXXXXXXX format
3. Check: Wabis account has credits (wabis.in → Balance)
4. Check: N8N credential test passes (green ✓)
```

### **Conversions Not Appearing in Meta/Google**
```
1. Check: gclid/fbclid captured in order (CRM Dashboard)
2. Check: Credentials not expired (token, refresh token)
3. Check: Logs: docker logs crm-api | grep "Meta\|Google"
4. Verify: Conversion action ID is correct
```

---

## **📚 REFERENCE DOCUMENTS**

| Document | Use For |
|---|---|
| `QUICK_START_3_HOURS.md` | Step-by-step deployment |
| `DEPLOYMENT_CHECKLIST.md` | Detailed instructions for each phase |
| `DEPLOYMENT_STATUS_AND_PENDING.md` | Full reference guide |
| `SYSTEM_ARCHITECTURE_COMPLETE.md` | Data flow & architecture |
| `WHATS_PENDING_SUMMARY.md` | What needs to be done |

---

## **🎯 SUCCESS METRICS TO TRACK**

After going live, measure:

```
Week 1:
├─ Orders from checkout recovery: target 2-3 orders
├─ WhatsApp message delivery rate: target 95%+
└─ No API errors: target 99.9% uptime

Week 2:
├─ Total recovery orders: target 5-8 orders
├─ WhatsApp click rate: target 20-30%
├─ Cost per recovered order: target < ₹250
└─ N8N workflow success rate: target 100%

Week 3:
├─ Replenishment orders: target 15-20 orders
├─ Lapsed buyer returns: target 5-10 orders
├─ Total revenue from automation: target ₹5,000+
└─ ROAS on WhatsApp spend: target > 300%
```

---

## **🚀 TIMELINE**

```
START: Phase 0 (collect credentials)
       ↓ 30 min
       ↓
       Phase 1 (deploy to server)
       ↓ 15 min
       ↓
       Phase 2 (import N8N workflows)
       ↓ 15 min
       ↓
       Phase 3 (configure Wabis)
       ↓ 20 min
       ↓
       Phase 4 (create templates)
       ↓ 20 min
       ↓
       Phase 5 (test live order)
       ↓ 20 min
       ↓
       Phase 6 (activate workflows)
       ↓ 10 min
       ↓
🎉 LIVE! (~2.5 hours total)
```

---

## **THE 3 NEXT STEPS**

### **STEP 1: NOW**
👉 Open `QUICK_START_3_HOURS.md`

### **STEP 2: COLLECT CREDENTIALS**
👉 Get the 8 platform credentials (30 min)

### **STEP 3: EXECUTE PHASES 1-6**
👉 Follow the checklist above (2 hours)

---

## **QUESTIONS?**

- **Deployment issue?** → See `DEPLOYMENT_CHECKLIST.md`
- **Architecture question?** → See `SYSTEM_ARCHITECTURE_COMPLETE.md`
- **What's pending?** → See `DEPLOYMENT_STATUS_AND_PENDING.md`
- **Quick reference?** → See `QUICK_START_3_HOURS.md`

---

**Status:** ✅ All code ready | 🔴 Waiting on credentials & deployment  
**Target:** Live by end of business today  
**Timeline:** 2.5 hours

🚀 **Let's go!**

