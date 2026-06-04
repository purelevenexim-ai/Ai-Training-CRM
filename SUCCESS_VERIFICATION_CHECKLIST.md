# ✅ SUCCESS VERIFICATION GUIDE

**Date**: May 18, 2026  
**Goal**: Confirm both Shopify Webhooks and GA4 Event Feed are working correctly

---

## 🎯 WHAT "COMPLETE" LOOKS LIKE

### ✅ Shopify Webhooks - DONE When:

**In Shopify Admin → Settings → Notifications → Webhooks**:

You see this list (with GREEN checkmarks):
```
┌─────────────────────────────────────┐
│ WEBHOOKS REGISTERED                 │
├─────────────────────────────────────┤
│ ✅ customer created                 │
│    URL: https://track.pureleven...  │
│    Status: Active                   │
├─────────────────────────────────────┤
│ ✅ customer updated                 │
│    URL: https://track.pureleven...  │
│    Status: Active                   │
├─────────────────────────────────────┤
│ ✅ order created                    │
│    URL: https://track.pureleven...  │
│    Status: Active                   │
├─────────────────────────────────────┤
│ ✅ order paid                       │
│    URL: https://track.pureleven...  │
│    Status: Active                   │
├─────────────────────────────────────┤
│ ✅ checkout abandoned               │
│    URL: https://track.pureleven...  │
│    Status: Active                   │
└─────────────────────────────────────┘
```

**CHECKPOINTS**:
- [ ] All 5 webhooks visible
- [ ] All showing "Active" (green status)
- [ ] URL ends with: `...api/crm/webhooks/shopify`

---

### ✅ GA4 Event Feed - DONE When:

**In GTM → Workspace (GTM-TFHBWPLM)**:

You see these components created and published:

#### Variables Section:
```
USER-DEFINED VARIABLES:
  ✅ GA4 Event Data for CRM
     Type: Custom JavaScript
     
  ✅ DL - User Email
     Type: Data Layer Variable
```

#### Tags Section:
```
TAGS:
  ✅ CRM - GA4 Event Send
     Type: HTTP Request
     URL: https://track.pureleven.com/api/crm/events/ga4
     Method: POST
```

#### Triggers Section:
```
TRIGGERS:
  ✅ GA4 - All Events
     Type: Event
     Event: gtag.event
```

#### Version Status:
```
In top-right corner shows:
  "Latest Version: GA4-CRM-Event-Feed-v1"
  OR
  "Published • # changes"
```

If GTM publishing is not available yet, the live storefront can still send the product audience events directly to `https://track.pureleven.com/api/crm/events/ga4` as a fallback path.

**CHECKPOINTS**:
- [ ] 2 variables created
- [ ] 1 tag created with GA4 endpoint
- [ ] 1 trigger assigned to tag
- [ ] Published to live (version showing)

---

## 🧪 FUNCTIONAL TESTS (Verify It Works)

### Test 1: Shopify Webhook Health

**In Terminal**:
```bash
# SSH to server
ssh root@192.46.213.140

# Check API logs for webhook receipts
docker logs -f pureleven-ai-engine | grep "webhook"

# Expected output: 
# [2026-05-18 12:34:56] webhook received from shopify
# [2026-05-18 12:34:57] customer_created event processed
```

**Expected**: Logs show incoming webhook calls

---

### Test 2: GA4 API Endpoint Health

**In Terminal**:
```bash
# Test the GA4 API endpoint
curl -X POST https://track.pureleven.com/api/crm/events/ga4 \
  -H "Content-Type: application/json" \
  -d '{"email":"verify@test.com","event_type":"test_event","event_data":{"source":"manual_test"}}' \
  -w '\nHTTP Status: %{http_code}\n'
```

**Expected Response**:
```
{
  "status": "event_recorded",
  "event_type": "test_event"
}
HTTP Status: 200
```

**CHECKPOINT**: [ ] Curl returns HTTP 200 OK

---

### Test 3: Database Has Data

**In Terminal**:
```bash
# SSH to server
ssh root@192.46.213.140

# Connect to database
docker exec -it pureleven-postgres psql -U pureleven -d pureleven

# In database prompt, run:
SELECT COUNT(*) FROM crm_customers;
SELECT COUNT(*) FROM crm_orders;
SELECT COUNT(*) FROM crm_ga4_events;
```

**Expected**: All return numbers > 0 (indicating data exists)

**CHECKPOINT**: [ ] Database contains records

---

### Test 4: Dashboard Displays Data

**In Browser**:
```
URL: https://ai.pureleven.com/static/dashboard.html
```

**Expected to see**:
- [ ] Customer list populated (not empty)
- [ ] Recent orders showing
- [ ] Analytics charts loading
- [ ] No red error messages
- [ ] Real-time counter updating

**CHECKPOINT**: [ ] Dashboard shows live data

---

### Test 5: Place Real Test Order (End-to-End)

**In Browser** (Open pureleven.com):
```
1. Go to: https://pureleven.com
2. Add a product to cart
3. Checkout with:
   - Email: testing1@pureleven.com
   - Name: Test User
   - Phone: 9999999999
   - Address: Test Address
   - Payment: COD (Cash on Delivery)
4. Click "Place Order"
5. Wait for confirmation page
```

**Watch Terminal** (in another window):
```bash
docker logs -f pureleven-ai-engine
```

**Expected sequence** (within 5-10 seconds):
```
[2026-05-18 12:45:23] Webhook received: order_created
[2026-05-18 12:45:24] Processing order event
[2026-05-18 12:45:25] Customer stored: testing1@pureleven.com
[2026-05-18 12:45:25] Order stored: ORDER_ID_12345
[2026-05-18 12:45:26] Event complete - success
```

**Check Dashboard**:
```
1. Refresh: https://ai.pureleven.com/static/dashboard.html
2. Look for: testing1@pureleven.com in customer list
3. Should appear within 10 seconds
4. Order details visible
```

**CHECKPOINT**: [ ] Customer appears in dashboard after order

---

## 📊 COMPLETE SUCCESS CHECKLIST

### Shopify Webhooks
- [ ] All 5 webhooks created
- [ ] All showing "Active" (green)
- [ ] Tested: Logs show webhook receipts
- [ ] Working: Test order triggered webhook

### GA4 Event Feed
- [ ] 2 Variables created and saved
- [ ] 1 Tag created with correct URL
- [ ] 1 Trigger created and assigned
- [ ] Published to live
- [ ] Curl test returns 200 OK
- [ ] Dashboard shows GA4 events (if any)

### Database
- [ ] crm_customers table has data
- [ ] crm_orders table has data
- [ ] crm_ga4_events table accessible

### Dashboard
- [ ] Loads at https://ai.pureleven.com/static/dashboard.html
- [ ] Shows customer data
- [ ] Shows order data
- [ ] Updates in real-time

### End-to-End Test
- [ ] Can place test order on pureleven.com
- [ ] Webhook fires within 5 seconds
- [ ] Customer appears in dashboard within 10 seconds
- [ ] No errors in API logs

---

## 🎉 FINAL SIGN-OFF

When you've verified all items above, you can confidently say:

```
✅ Shopify webhooks are LIVE and WORKING
✅ GA4 event feed is CONFIGURED and LIVE
✅ Customer data is FLOWING in real-time
✅ CRM system is PRODUCTION-READY
```

---

## 🚨 IF SOMETHING ISN'T WORKING

### Shopify webhooks not firing?
1. Verify webhook URL: `https://track.pureleven.com/api/crm/webhooks/shopify`
2. Check status: Should be GREEN/Active
3. Test: Place order, watch logs for webhook receipt
4. Fix: Delete and recreate webhook if needed

### GA4 not showing in dashboard?
1. Verify GTM published: Check GTM version
2. Test curl: Does API endpoint return 200?
3. Check GTM console: Any JavaScript errors?
4. Fix: Republish GTM with changes

### Dashboard not updating?
1. Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
2. Clear cache: Ctrl+Shift+Delete
3. Check API: curl https://track.pureleven.com/api/crm/health
4. Fix: Restart API container if needed

### Database errors?
1. Check container: docker ps | grep pureleven
2. Check logs: docker logs pureleven-ai-engine
3. Verify connection: docker logs pureleven-postgres
4. Fix: Restart containers if needed

---

## 📞 SUPPORT

**Check these files for detailed help**:
- [SESSION_WEBHOOK_GA4_EXECUTION.md](SESSION_WEBHOOK_GA4_EXECUTION.md) - Full step-by-step
- [QUICK_CARD_WEBHOOK_GA4.md](QUICK_CARD_WEBHOOK_GA4.md) - Quick reference
- [WEBHOOK_REGISTRATION_MANUAL.md](WEBHOOK_REGISTRATION_MANUAL.md) - Shopify details
- [GA4_GTM_IMPLEMENTATION_CHECKLIST.md](GA4_GTM_IMPLEMENTATION_CHECKLIST.md) - GA4 details

---

**Created**: May 18, 2026  
**Status**: Ready for Verification  
**Expected**: After both tasks complete, all items above should check ✅
