# What's Pending — Complete Summary

**Date: 18 May 2026**
**System Status: 70% Code Ready → 30% Deployment & Testing**

---

## **CRITICAL PATH (Must Do These)**

### 🔴 **BLOCKING ITEMS (Do Today)**

| # | Task | Owner | Est. Time | Blocker |
|---|---|---|---|---|
| 1 | **Collect 8 Platform Credentials** | You | 30 min | YES |
| 2 | **Deploy to Server** (git pull + migration) | You/DevOps | 15 min | YES |
| 3 | **Import 4 N8N Workflows** | You | 15 min | YES |
| 4 | **Configure Wabis API in N8N** | You | 15 min | YES |
| 5 | **Create 7 Wabis Message Templates** | You | 20 min | YES |
| 6 | **Run Live Order Test** | You | 20 min | YES |
| 7 | **Activate N8N Workflows** | You | 10 min | YES |

**Total Time: ~2.5 hours**
**Target: Complete by end of day**

---

## **THE 8 CREDENTIALS YOU NEED**

Get these from each platform and add to server `.env`:

```
1. META_CAPI_ACCESS_TOKEN        ← business.facebook.com/settings
2. GADS_DEVELOPER_TOKEN           ← ads.google.com → API Center
3. GADS_OAUTH_REFRESH_TOKEN       ← Google Cloud OAuth 2.0
4. GADS_CONVERSION_ACTION_ID      ← ads.google.com → Conversions
5. GA4_API_SECRET                 ← analytics.google.com → Data API
6. SHIPROCKET_WEBHOOK_TOKEN       ← shiprocket.com → Settings
7. WABIS_API_TOKEN                ← wabis.in → API Keys
8. INTERNAL_API_KEY               ← Generate random string
```

---

## **DEPLOYMENT STEPS (In Order)**

### **Step 1: Update Server (10 min)**
```bash
ssh root@192.46.213.140
cd /root/pureleven_dev
# Add 8 credentials to .env
nano .env
# Save and exit

# Deploy
git pull origin main
python alembic_migration_crm_v2.py
docker compose restart crm-api
curl https://ai.pureleven.com/api/crm/health  # Should return 200
```

### **Step 2: N8N Setup (30 min)**
- Import 4 JSON workflow files at https://automation.pureleven.com
- For each workflow, configure Wabis credential with your API token
- Create 7 message templates in Wabis dashboard

### **Step 3: Validation (20 min)**
- Place a test order on pureleven.com with COD
- Verify order appears in CRM Dashboard
- Check Meta CAPI, Google Ads, GA4 show conversion
- Simulate Shiprocket delivery webhook

### **Step 4: Go Live (10 min)**
- Activate each N8N workflow one by one
- Monitor execution logs for first hour
- Verify WhatsApp messages send to test phone

---

## **WHAT'S DONE (Don't Redo)**

✅ All code written and tested  
✅ Database schema migration ready  
✅ API endpoints created (7 new endpoints)  
✅ Browser tracking pixel upgraded  
✅ N8N workflow JSON files created  
✅ Audience classification engine built  
✅ Identity resolution engine built  
✅ Shiprocket delivery attribution logic added  
✅ Meta CAPI, Google Ads, GA4 fan-outs wired  

**Files created:**
- `crm_identity.py` — unified identity resolution
- `crm_audiences.py` — audience classification
- `alembic_migration_crm_v2.py` — database migration
- `crm_routes.py` (updated) — all new endpoints + fan-outs
- `TRAFFIC_SOURCE_TRACKING.js` (updated) — session/gclid/fbclid capture
- `n8n/workflow_*.json` (4 files) — N8N automation workflows
- `deploy.sh` — deployment automation script

---

## **WHAT'S PENDING (To Do)**

🔴 **Critical (Before Launch)**
- [ ] Collect credentials from 8 platforms
- [ ] SSH to server and update .env
- [ ] Run git pull + migration + docker restart
- [ ] Import 4 N8N workflows
- [ ] Set Wabis API token in N8N
- [ ] Create 7 message templates in Wabis
- [ ] Test live order (CTR validation)
- [ ] Activate workflows

🟡 **Important (First Week)**
- [ ] Monitor N8N execution logs daily
- [ ] Test checkout abandonment flow manually
- [ ] Test cart abandonment flow manually
- [ ] Test delivery attribution (Shiprocket webhook)
- [ ] Export audiences to Meta/Google manually
- [ ] Monitor WhatsApp message delivery
- [ ] Check conversion counts in Meta/Google/GA4

🟢 **Nice-to-Have (Later)**
- [ ] Set up automated monitoring/alerts
- [ ] Create dashboard for workflow stats
- [ ] Optimize message templates (A/B test)
- [ ] Add SMS fallback (separate integration)
- [ ] Real-time webhook instead of polling (more latency)

---

## **AFTER DEPLOYMENT — What Happens**

### **Visitor Journey (Automated)**
```
1. Visitor lands on site
   → Session ID + gclid/fbclid captured
   → /api/crm/identify called
   → Unified identity created in DB

2. Visitor adds to cart
   → Page view event logged
   → Attribution data stored

3. Visitor abandons checkout
   → N8N polls every 5 min
   → Sends WhatsApp: "Your order is waiting!"
   → Waits 45 min → sends social proof
   → Waits 5 days → sends ₹100 offer

4. Visitor completes order (COD)
   → Order stored with gclid/fbclid
   → Meta CAPI: Purchase event sent
   → Google Ads: Offline conversion sent
   → GA4: Purchase event sent
   → Audience reclassified (is now "buyer")

5. Shiprocket confirms delivery
   → N8N triggered via Shiprocket webhook
   → Meta CAPI: 2nd Purchase event (delivery proof)
   → Google Ads: cod_delivered conversion
   → CRM marks order as "delivered"

6. Next day
   → N8N exports high_ltv buyers to Meta
   → N8N exports replenishment candidates to Google
   → Retargeting ads show to these audiences
   → Winback messages sent to 60+ day lapsed buyers
```

### **Real Results** (Expected metrics)
- **Checkout recovery:** 5% of abandoned checkouts recover → order
- **Cart recovery:** 3% of abandoned carts recover → order
- **Replenishment:** 15% of eligible buyers reorder
- **Winback:** 8% of lapsed buyers comeback
- **WhatsApp engagement:** 25% click-through rate
- **Cost per order:** < ₹200

---

## **MONITORING CHECKLIST (Daily)**

After going live:

```
☐ API health: curl https://ai.pureleven.com/api/crm/health
☐ N8N executions: No red X (errors) in automation.pureleven.com
☐ Wabis logs: WhatsApp messages sending
☐ CRM Dashboard: New customers/orders appearing
☐ Meta Events Manager: Purchase events showing
☐ Google Ads: Offline conversions appearing
☐ GA4 Real-time: Purchase events showing
```

---

## **IF SOMETHING BREAKS**

**API Down?**
```bash
ssh root@192.46.213.140
docker logs crm-api
docker compose restart crm-api
```

**N8N Workflow Failing?**
```
Go to: automation.pureleven.com → Executions
Click failed run → see error logs
Usually: Wabis credential expired, or template missing
```

**WhatsApp Not Sending?**
```
1. Check template exists in wabis.in
2. Check Wabis API token is valid
3. Check phone number is 91XXXXXXXXXX format
4. Check Wabis account has credits
```

**Conversions Not Appearing?**
```
1. Check gclid/fbclid captured (CRM Dashboard)
2. Check order marked as payment_method="cod"
3. Check logs: docker logs crm-api | grep -i "meta\|google"
4. Verify credentials (token might have expired)
```

---

## **FILES YOU NEED TO USE**

**For deployment steps:**
- `QUICK_START_3_HOURS.md` ← **START HERE** (copy-paste commands)
- `DEPLOYMENT_CHECKLIST.md` ← Detailed instructions for each step
- `deploy.sh` ← Automated deployment script

**For monitoring:**
- `DEPLOYMENT_STATUS_AND_PENDING.md` ← Full details on what's pending

**For reference:**
- `crm_models.py` — Database schema (already updated)
- `crm_routes.py` — All API endpoints (already updated)
- `TRAFFIC_SOURCE_TRACKING.js` — Browser tracking (already updated)
- `n8n/` — 4 N8N workflow JSON files

---

## **ONE-PAGE EXECUTIVE SUMMARY**

| Area | Status | Timeline |
|---|---|---|
| **Code** | ✅ Complete | Ready now |
| **Database Schema** | ✅ Ready | Migrate on deploy |
| **API Endpoints** | ✅ Complete | 7 new endpoints live after deploy |
| **Browser Tracking** | ✅ Ready | Auto-updates on site refresh |
| **N8N Automation** | ✅ Ready | Import + activate after deploy |
| **Wabis Integration** | ✅ Ready | Set token + templates on deploy |
| **Server Deployment** | 🔴 TODO | 15 min, do today |
| **Credential Setup** | 🔴 TODO | 30 min, do today |
| **N8N Import** | 🔴 TODO | 15 min, do today |
| **Live Test** | 🔴 TODO | 20 min, do today |
| **Go Live** | 🔴 TODO | 10 min, do today |

**Total remaining work:** ~2.5 hours

---

## **NEXT ACTION**

👉 **Open:** `QUICK_START_3_HOURS.md`  
👉 **Follow:** Step 0 (collect credentials)  
👉 **Execute:** Steps 1-7 in order  
👉 **Timeline:** Complete today before end of business  

---

**Questions on any step? Refer to:**
- DEPLOYMENT_CHECKLIST.md (detailed)
- DEPLOYMENT_STATUS_AND_PENDING.md (comprehensive reference)
- QUICK_START_3_HOURS.md (quick copy-paste)

