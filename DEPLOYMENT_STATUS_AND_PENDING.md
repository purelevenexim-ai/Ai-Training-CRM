# Pureleven Unified Tracking System — Deployment Status & Pending Tasks

**Last Updated:** 18 May 2026  
**Overall Progress:** 70% Complete (Code Ready → Deployment Phase)

---

## **CURRENT STATUS**

### ✅ **COMPLETED**
- [x] Unified identity resolution engine (`crm_identity.py`)
- [x] Audience classification & segmentation (`crm_audiences.py`)
- [x] Database schema v2 migration (`alembic_migration_crm_v2.py`)
- [x] Browser tracking pixel upgrade (`TRAFFIC_SOURCE_TRACKING.js`)
- [x] CRM API endpoints (Phase 2 & 3):
  - `/api/crm/identify` — unified identity resolution
  - `/api/crm/webhooks/shiprocket` — COD delivery attribution
  - `/api/crm/abandonment/checkout` — N8N polling
  - `/api/crm/abandonment/cart` — N8N polling
  - `/api/crm/abandonment/{event_id}/mark_notified` — dedup flag
  - `/api/crm/audiences/{segment}/export` — audience CSV/JSON
  - `/api/crm/audiences/refresh` — batch reclassification
- [x] Server-side fan-outs wired:
  - Meta CAPI purchase events
  - Google Ads Enhanced Conversions
  - GA4 Measurement Protocol
- [x] N8N workflow JSON files (4 workflows):
  - Checkout abandonment recovery (multi-touch: T+15min, T+1hr, Day 6)
  - Cart abandonment recovery
  - Replenishment reminder (30-50 days)
  - Winback campaign (60+ days lapsed)

---

## **IMMEDIATE ACTION ITEMS (Next 24 hours)**

### 1️⃣ **Get Credentials from Each Platform**

| Platform | What | Where to Get | Status |
|---|---|---|---|
| **Meta CAPI** | Access Token | business.facebook.com → Settings → User token | 🔴 Pending |
| **Google Ads** | OAuth Refresh Token | Google Cloud Console → OAuth 2.0 Client | 🔴 Pending |
| **Google Ads** | Developer Token | Google Ads Manager → Tools & Settings | 🔴 Pending |
| **Google Ads** | Conversion Action ID | ads.google.com → Conversions → Create/select | 🔴 Pending |
| **GA4** | API Secret | analytics.google.com → Admin → Data API | 🔴 Pending |
| **Shiprocket** | Webhook Token | Shiprocket Dashboard → Settings → Webhooks | 🔴 Pending |
| **Wabis** | API Token | wabis.in → Dashboard → API Keys | 🔴 Pending |

**Action:** Collect these 8 credentials and add to server `.env`

---

### 2️⃣ **Deploy to Server**

```bash
# SSH into server
ssh root@192.46.213.140

# Navigate to project directory
cd /root/pureleven_dev

# Copy deploy.sh and run it
# (Or run commands manually from DEPLOYMENT_CHECKLIST.md)

# Run deployment script
bash deploy.sh

# Expected output:
# ✅ DEPLOYMENT COMPLETE!
```

**Time Estimate:** 10 minutes

---

### 3️⃣ **Set Up N8N Workflows**

1. **Import 4 JSON workflow files**
   - Go to: https://automation.pureleven.com
   - Import → Select each JSON file
   - Verify workflows appear in Workflows page

2. **Add Wabis API Credential**
   - Create new credential: `httpHeaderAuth`
   - Password: `Bearer {your-wabis-api-token}`
   - Apply to all 4 workflows

3. **Verify Wabis Templates Exist**
   - Go to: wabis.in → Templates
   - Create 7 templates (as specified in DEPLOYMENT_CHECKLIST.md)
   - Status should be "Approved"

**Time Estimate:** 20 minutes

---

### 4️⃣ **Run Live Order Test**

```bash
# Clear browser cache (incognito window)
# Go to: https://pureleven.com
# 1. Add product to cart
# 2. Proceed to checkout
# 3. Email: test+DATE@example.com
# 4. Phone: 9876543210
# 5. Select COD
# 6. Complete Order

# Verify in:
# ✓ CRM Dashboard → https://ai.pureleven.com (order captured)
# ✓ Meta Ads Manager → Pixels → Events (Purchase event)
# ✓ Google Ads → Conversions (offline conversion)
# ✓ GA4 → Real-time (purchase event)
```

**Time Estimate:** 15 minutes

---

### 5️⃣ **Activate N8N Workflows**

One by one:
1. Checkout Abandonment → **Activate** → Monitor 1 hour
2. Cart Abandonment → **Activate** → Monitor 30 min
3. Replenishment → **Activate** → Monitor 1 day
4. Winback → **Activate** → Monitor 1 day

**Time Estimate:** 5 minutes per workflow

---

## **PENDING TASKS (Detailed Breakdown)**

### 🔴 **CRITICAL PATH — Must Complete Before Going Live**

| Task | Owner | Timeline | Blocker? |
|---|---|---|---|
| Collect 8 platform credentials | You | 24 hours | YES |
| Deploy to server | DevOps/You | 30 min | YES |
| Set up N8N + Wabis | You | 30 min | YES |
| Run live order test | You | 30 min | YES |
| Activate N8N workflows | You | 30 min | YES |

**Total Time to Live:** ~3 hours

---

### 🟡 **BEFORE FULL ROLLOUT — Next 48 Hours**

| Task | Description | Status |
|---|---|---|
| Monitor N8N execution logs | Check for errors in workflow runs | 🔴 Pending |
| Test cart abandonment flow | Place order, abandon cart, trigger N8N | 🔴 Pending |
| Test delivery attribution | Simulate Shiprocket delivery webhook | 🔴 Pending |
| Verify audience sync to Meta | Export high_ltv audience to Meta | 🔴 Pending |
| Verify audience sync to Google | Export replenishment audience to Google | 🔴 Pending |
| Test WhatsApp templates | Verify all 7 templates send correctly | 🔴 Pending |
| Load test (optional) | Simulate 100s of concurrent events | 🔴 Optional |

---

### 🟢 **AFTER GOING LIVE — Ongoing Maintenance**

| Task | Frequency | Owner |
|---|---|---|
| Monitor N8N workflow execution | Daily | DevOps |
| Check API error logs | Weekly | DevOps |
| Verify conversion counts (Meta/Google/GA4) | Weekly | Marketing |
| Refresh audience exports to ad platforms | Weekly | Marketing |
| Review CRM dashboard metrics | Weekly | Analytics |
| Update Wabis templates (seasonal offers) | Monthly | Marketing |
| Renew API tokens (Meta CAPI, Google OAuth) | Annually | DevOps |
| Backup CRM database | Weekly | DevOps |

---

## **KNOWN LIMITATIONS & EDGE CASES**

| Issue | Workaround | Fix Timeline |
|---|---|---|
| gclid/fbclid only captured if in URL | Shopify Pixel integration covers this | Phase 5 (future) |
| RTO orders excluded from buyer audience | Manual review required | Phase 6 (future) |
| N8N runs on polling, not real-time | 5-10 min delay acceptable for WhatsApp | Phase 6 (future: webhooks) |
| Wabis API rate limits (5000/day) | Monitor queue; contact Wabis | N/A |
| COD attribution only on delivery | By design (prevents fraud) | N/A |
| Audience export is time-point (not streaming) | Manual refresh daily | Phase 6 (future: real-time sync) |

---

## **ROLLOUT PLAN**

### **Wave 1 (This Week)**
- Deploy to production
- Test with internal orders
- Monitor for 24 hours
- Fix any bugs

### **Wave 2 (Next Week)**
- Enable checkout abandonment workflow
- Enable cart abandonment workflow
- Monitor WhatsApp send rates
- Measure conversion impact

### **Wave 3 (Week 3)**
- Enable replenishment workflow
- Enable winback workflow
- Launch audience retargeting campaigns in Meta/Google
- Track ROAS vs baseline

### **Wave 4 (Ongoing)**
- Optimize WhatsApp message templates based on click rates
- A/B test discount amounts (₹50 vs ₹100)
- Scale budget as ROAS improves

---

## **SUCCESS METRICS**

Track these KPIs after going live:

| Metric | Target | How to Measure |
|---|---|---|
| **Checkout Abandonment Recovery** | 5% recovery rate | Orders from abandoned checkout flow / Total abandonments |
| **Cart Abandonment Recovery** | 3% recovery rate | Orders from cart abandoners / Total cart events |
| **Replenishment Rate** | 15% reorder rate | Repeat orders from replenishment audience / Total sends |
| **Winback Rate** | 8% comeback rate | Orders from lapsed buyers / Total sends |
| **WhatsApp Engagement** | 25% click rate | Clicks / Total messages sent |
| **Cost per Acquisition** | < ₹200 | Wabis cost / Orders attributed to WhatsApp |
| **Attribution Accuracy** | 95%+ | Conversions in Meta/Google / Actual orders |

---

## **DEPENDENCIES & ASSUMPTIONS**

### ✅ **Already in Place**
- Shopify webhooks configured & routing to FastAPI
- GTM Container for GA4 events
- Meta Pixel installed on storefront
- Google Ads campaigns running
- Database backups configured

### ⚠️ **Must Be True**
- All 8 platform credentials are valid & not expired
- Server has internet access to reach Meta/Google/Wabis APIs
- Wabis account has SMS/WhatsApp credits available
- Shiprocket account has webhook capability enabled
- N8N container is running and accessible

### 🚫 **NOT Included (Out of Scope)**
- Email campaign automation (separate tool)
- SMS notifications (use Wabis SMS, not in scope)
- Push notifications to mobile app
- In-app messaging
- Discord/Slack alerts for order events

---

## **TROUBLESHOOTING GUIDE**

### Problem: "Meta CAPI Purchase event not appearing"
```
1. Check: META_CAPI_ACCESS_TOKEN is valid
   - Token expires annually → renew if old
2. Check: Pixel ID is correct (609256704464862)
3. Check: Event is being sent (logs: docker logs crm-api | grep "Meta CAPI")
4. Check: Email/phone are hashed correctly (SHA-256 lowercase)
5. Test: Use Meta's test_event_code in payload
```

### Problem: "Google Ads offline conversion not showing"
```
1. Check: GADS_OAUTH_REFRESH_TOKEN is still valid
   - OAuth tokens expire if account inactive for 6 months
2. Check: GADS_CONVERSION_ACTION_ID matches your setup
   - Go to: ads.google.com → Conversions → verify ID
3. Check: gclid was captured (should be in order record)
4. Check: Conversion date is within last 30 days
5. Test: Manual upload via Google Ads UI to verify action works
```

### Problem: "N8N workflow doesn't execute"
```
1. Check: Workflow is in "Active" state (not paused)
   - N8N UI → Workflow → green toggle should be ON
2. Check: N8N container is running
   - Server: docker ps | grep n8n
3. Check: Wabis credential test passes
   - N8N → Credentials → test connection
4. Check: CRM API endpoint is reachable from N8N
   - N8N → test HTTP request to /api/crm/health
5. Check: Workflow execution logs for errors
   - N8N → Executions → click failed run
```

### Problem: "Wabis WhatsApp message doesn't send"
```
1. Check: Template exists & is Approved
   - wabis.in → Templates → status = "Approved"
2. Check: Phone number is valid format
   - Must be: 91XXXXXXXXXX (with country code)
3. Check: Phone has WhatsApp account
   - Send test via Wabis dashboard manually
4. Check: Account has credits
   - wabis.in → Account → Balance
5. Check: Message parameters match template
   - E.g., if template has {{1}} and {{2}}, both must be provided
```

---

## **COMMUNICATION CHECKLIST**

Before going live, inform:
- [ ] Marketing team (understand WhatsApp campaign schedule)
- [ ] Customer service (explain why customers get WhatsApp)
- [ ] Finance (explain Wabis API costs)
- [ ] Compliance (GDPR/CCPA for SMS/WhatsApp)
- [ ] Legal (WhatsApp terms, opt-in requirements)

---

## **WHAT HAPPENS AFTER DEPLOYMENT**

### **Day 1-7: Monitoring Phase**
- Monitor N8N workflow execution logs
- Check conversion attribution in Meta/Google/GA4
- Verify WhatsApp messages send without errors
- Adjust message templates if needed

### **Week 2: Optimization Phase**
- Analyze WhatsApp click rates
- Optimize discount amounts
- Test different send times
- Review ROAS vs baseline

### **Week 3: Scale Phase**
- Increase ad spend based on ROAS
- Add more audience segments
- Expand to SMS (if Wabis offers)
- Consider Email retargeting integration

### **Ongoing: Maintenance**
- Daily monitoring of N8N execution
- Weekly audience refresh to Meta/Google
- Monthly template optimization
- Quarterly performance review

---

## **FINAL CHECKLIST**

Before marking as "LIVE":

```
Server Infrastructure:
☐ All env vars set and verified
☐ Database migration complete
☐ API health check passing
☐ Docker services running

N8N Automation:
☐ All 4 workflows imported
☐ Wabis credential configured
☐ N8N health check passing
☐ Test execution logs show success

Integration Testing:
☐ Live order test passed
☐ Meta CAPI event captured
☐ Google Ads offline conversion captured
☐ GA4 purchase event captured
☐ Shiprocket delivery webhook tested

Readiness:
☐ Team trained on monitoring
☐ Alert system configured (optional)
☐ Runbooks documented
☐ Rollback plan tested
☐ All stakeholders notified

🚀 **STATUS: READY FOR PRODUCTION DEPLOYMENT**
```

---

**Questions? Issues?**
- Review DEPLOYMENT_CHECKLIST.md for step-by-step instructions
- Check logs: `docker logs crm-api` or `docker logs n8n`
- Review N8N execution history for workflow errors
- Test each integration separately before enabling all workflows

