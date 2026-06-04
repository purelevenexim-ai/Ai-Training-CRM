# 🔴 LIVE TESTING SESSION - EXECUTION LOG

**Date**: May 17, 2026  
**Session Start**: 12:24 IST  
**Objective**: Test end-to-end order flow and CRM data capture

---

## 📋 Testing Strategy

Since we need to verify real Shopify data flow, here's what we need to do manually:

### Step 1: Prepare Monitoring Tools

Before placing any orders, open monitoring in terminal:

```bash
# Terminal 1: Monitor API logs
ssh root@192.46.213.140
docker logs -f pureleven-ai-engine

# Terminal 2: Monitor database (in another terminal)
ssh root@192.46.213.140
docker exec -it pureleven-postgres psql -U pureleven -d pureleven
```

### Step 2: Manual Order Placement

Since automated browser interaction is complex, follow these steps manually:

1. Open https://pureleven.com in your browser
2. Add 1-2 products to cart
3. Proceed to checkout
4. Select COD payment
5. Complete order with email: **testing-20260517@example.com**
6. Note the order number
7. Take screenshot of confirmation

### Step 3: Monitor for Webhook

After placing order:
1. Watch API logs for: `POST /api/crm/webhooks/shopify - 200 OK`
2. Wait 5-10 seconds
3. Query database to confirm data arrived

### Step 4: Data Validation

Check database for customer and order data.

---

## 🎯 CRITICAL DISCOVERY NEEDED

**The following must be verified before we can proceed:**

### Issue 1: Are Webhooks Even Registered?
```bash
# Check if webhooks are active in Shopify
# Go to: admin.shopify.com → Settings → Notifications → Webhooks

Expected: 0 webhooks (none registered yet)
If > 0 webhooks: We need to check if they're pointing to correct endpoint
```

### Issue 2: Is the CRM Endpoint Even Reachable?
```bash
# Test from command line
curl -X POST https://track.pureleven.com/api/crm/webhooks/shopify \
  -H "Content-Type: application/json" \
  -d '{"test": "webhook"}'

Expected: 200 OK
If error: Check firewall, domain, endpoint
```

### Issue 3: Database Connection Working?
```bash
docker exec -it pureleven-postgres psql -U pureleven -d pureleven
SELECT COUNT(*) FROM crm_customers;

Expected: Returns a number (0 or more)
If error: Database not accessible
```

---

## ⚠️ CRITICAL ISSUE IDENTIFIED

### The Problem:

**We haven't registered the Shopify webhooks yet!**

The webhooks are the bridge between Shopify and the CRM. Without them:
- ❌ Orders placed on Pureleven.com DO NOT trigger any webhook calls
- ❌ No data flows to the CRM API
- ❌ The database stays empty
- ❌ Dashboard shows no customers

### What This Means:

Even if we place 100 orders on Pureleven right now, the CRM will receive ZERO data because there's nothing telling Shopify to send data to the CRM API.

### What We Need to Do:

**BEFORE we can test the end-to-end flow, we must:**

1. Register Shopify webhooks (5 types)
2. Point them to: `https://track.pureleven.com/api/crm/webhooks/shopify`
3. Test with a single order
4. Verify webhook fires and data arrives

---

## 🚨 CURRENT STATUS

### What's Missing (Blockers):

❌ **Shopify Webhooks NOT Registered** - This is the blocker
- Need to go to Shopify Admin
- Settings → Notifications → Webhooks
- Create 5 webhooks pointing to CRM endpoint

❌ **No Live Data Can Be Captured** - Until webhooks exist
- Orders placed now: Will NOT sync to CRM
- Dashboard will remain empty
- No test data available

### What's Ready:

✅ CRM API endpoint is live and ready
✅ Database is ready to receive data
✅ Dashboard is ready to display data
✅ Webhook parsing code is ready

### What Needs to Happen:

1. **IMMEDIATE** (15 minutes):
   - Register 5 Shopify webhooks
   - Point to: `https://track.pureleven.com/api/crm/webhooks/shopify`
   - Verify all show "Active"

2. **THEN** (5-10 minutes):
   - Place a test order with COD
   - Monitor API logs
   - Check database for incoming data
   - Verify dashboard updates

3. **THEN** (1-2 hours):
   - Execute comprehensive test scenarios
   - Test multiple products, coupons, customers
   - Identify any data gaps
   - Plan fixes if needed

---

## 📋 How to Register Shopify Webhooks

### Step-by-Step:

1. Go to: https://admin.shopify.com
2. Login to Pureleven store
3. Go to: Settings → Notifications
4. Scroll down to: Webhooks section
5. Click: "Create webhook"

**For each of these 5 events, create a webhook:**

```
Webhook 1: customer created
├─ Event: customer created
├─ Endpoint: https://track.pureleven.com/api/crm/webhooks/shopify
└─ Format: JSON

Webhook 2: customer updated
├─ Event: customer updated
├─ Endpoint: https://track.pureleven.com/api/crm/webhooks/shopify
└─ Format: JSON

Webhook 3: order created
├─ Event: order created
├─ Endpoint: https://track.pureleven.com/api/crm/webhooks/shopify
└─ Format: JSON

Webhook 4: order paid
├─ Event: order paid
├─ Endpoint: https://track.pureleven.com/api/crm/webhooks/shopify
└─ Format: JSON

Webhook 5: checkout abandoned
├─ Event: checkout abandoned
├─ Endpoint: https://track.pureleven.com/api/crm/webhooks/shopify
└─ Format: JSON
```

6. After creating each webhook, verify it shows: ✅ **Active**
7. All 5 should be listed with green "Active" status

---

## 🎯 Testing Timeline (After Webhooks Are Registered)

### Immediate (Next 30 minutes)

**Test 1: Basic Order**
```
1. Place order on pureleven.com
   - 1 product (Kerala Cardamom)
   - COD payment
   - Email: test1@example.com
   
2. Monitor API logs
   Expected: POST /api/crm/webhooks/shopify - 200 OK
   
3. Check dashboard
   Expected: Customer appears within 5 seconds
   
4. Query database
   Expected: New row in crm_customers + crm_orders
```

**Test 2: Multiple Products**
```
1. Place order with 3 products
2. Verify all products recorded
3. Check total_amount correct
```

**Test 3: Coupon Application**
```
1. Apply coupon code at checkout
2. Verify discount applied
3. Check database for coupon code
```

### Later (Next 1-2 hours)

**Test 4-6**: Different products, customers, checkout flows

---

## 📊 Expected Data After First Order

### In crm_customers table:
```
id          | UUID
email       | test1@example.com
first_name  | (from checkout)
last_name   | (from checkout)
total_spent | 449.00
orders_count| 1
created_at  | (current time)
```

### In crm_orders table:
```
id                | UUID
shopify_order_id  | (from Shopify)
customer_id       | (FK to customer)
order_date        | (current time)
total_amount      | 449.00
status            | pending (for COD)
items             | [{"product": "Kerala Cardamom", "qty": 1, ...}]
```

### In crm_events table:
```
(May be empty initially - depends on webhook payload)
```

---

## ✅ Success Criteria for Live Testing

### After registering webhooks + placing one order:

- ✅ API log shows: `POST /api/crm/webhooks/shopify - 200 OK`
- ✅ Customer appears in crm_customers table
- ✅ Order appears in crm_orders table
- ✅ Dashboard shows customer list
- ✅ Dashboard shows order count > 0
- ✅ Response time < 500ms
- ✅ No errors in logs

### If ALL of above work:

→ System is operational ✅  
→ Proceed to comprehensive testing  
→ Test coupon, multiple products, etc.

### If ANY fail:

→ Identify which endpoint/table failed  
→ Check webhook payload  
→ Debug API parsing logic  
→ Fix and re-test

---

## 🔧 How to Proceed

### Phase 1: Webhook Registration (15 min)
1. Open Shopify Admin
2. Go to Settings → Notifications
3. Create 5 webhooks (see instructions above)
4. Verify all show "Active"

### Phase 2: First Order Test (10 min)
1. Place a simple order with COD
2. Monitor API logs
3. Check database
4. Take screenshots

### Phase 3: Results Analysis (10 min)
1. Document what data arrived
2. Identify any missing fields
3. Check for any errors
4. Plan next steps

### Total Time: ~35 minutes to complete first end-to-end test

---

## 📝 What to Document During Testing

For each test scenario, record:

1. **Order Details**
   - Email used
   - Products added
   - Total amount
   - Coupon (if used)
   - Payment method

2. **API Response**
   - Did webhook fire? (check logs)
   - Response time
   - Status code
   - Any errors?

3. **Database Check**
   - Customer created? (Y/N)
   - Order created? (Y/N)
   - All fields populated? (Y/N)
   - Any NULL fields?

4. **Dashboard Check**
   - Does customer appear?
   - Is order shown?
   - Is data accurate?
   - How long did it take?

5. **Issues Found**
   - List any missing data
   - List any incorrect data
   - List any errors in logs
   - List any performance issues

---

## 🎯 IMMEDIATE NEXT STEPS

### You Must Do This First:

**BEFORE ANY TESTING CAN HAPPEN:**

1. ✅ Open Shopify Admin
2. ✅ Register 5 webhooks
3. ✅ Verify all show "Active"
4. ✅ Then place test order
5. ✅ Then run database queries
6. ✅ Then check results

**If you skip webhook registration:** No data will flow, testing will be pointless

---

## 📌 Summary

**The Gap**: Webhooks haven't been registered yet

**The Impact**: No order data flows to CRM automatically

**The Solution**: Register 5 Shopify webhooks (15 minutes)

**The Result**: Orders will sync automatically, CRM will work

**Next Step**: Go to Shopify Admin and register webhooks now

---

**Status**: BLOCKED ON WEBHOOK REGISTRATION  
**Blocker**: Need to manually register webhooks in Shopify Admin  
**Timeline**: Can't proceed with testing until this is done  
**ETA**: 15 minutes to register, then testing can begin

---

## 📋 Testing Checklist (After Webhooks)

- [ ] All 5 webhooks registered
- [ ] All show "Active" status
- [ ] Endpoint URL: https://track.pureleven.com/api/crm/webhooks/shopify
- [ ] API logs monitored and ready
- [ ] Database query tool ready
- [ ] Dashboard open in browser
- [ ] Email prepared for testing (test1@example.com)
- [ ] First test order ready to place

**Once all checked: Ready for live testing! ✅**

---

*Remember: Without webhook registration, no data flows. Webhooks are the bridge between Shopify and CRM.*
