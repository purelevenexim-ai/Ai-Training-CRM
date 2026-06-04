# CRM Activation Guide - Next Steps

**Status**: System is built and ready  
**Your job**: Activate it (45-60 minutes)  
**Result**: Real customer data flowing automatically

---

## 🎯 Overview

The Pureleven CRM system is **100% complete and deployed**. Your job is to activate it by:

1. Registering Shopify webhooks (15 min) - **REQUIRED**
2. Configuring GA4 event feed (45 min) - **OPTIONAL**

After these steps, the system will automatically:
- ✅ Sync Shopify customer data
- ✅ Track GA4 events
- ✅ Store everything in the database
- ✅ Display in the real-time dashboard

---

## Step 1: Verify System is Ready

### Check Dashboard
```
Go to: https://ai.pureleven.com/static/dashboard.html
Expected: Dashboard loads with sample data
Status: ✅ Should work
```

### Check API Health
```bash
curl https://ai.pureleven.com/api/crm/health
Expected Response: {"status":"healthy","module":"crm"}
Status: ✅ Should return 200 OK
```

### Check Database
```bash
ssh root@192.46.213.140
docker exec -it pureleven-postgres psql -U pureleven -d pureleven
SELECT COUNT(*) FROM crm_customers;
Expected: Returns a number (sample data)
Status: ✅ Should show tables exist
```

---

## Step 2: Register Shopify Webhooks (15 minutes)

### What This Does
Activates real-time data sync from Shopify to CRM.

### Time Required
- 10-15 minutes setup
- Automatic after that

### What You'll Do

#### 2.1 Access Shopify Admin
```
1. Go to: https://admin.shopify.com
2. Login to Pureleven Shopify store
3. Navigate to: Settings → Notifications
4. Scroll down to: Webhooks section
```

#### 2.2 Create First Webhook
```
1. Click "Create webhook"
2. Event: customer created
3. Format: JSON
4. Endpoint: https://track.pureleven.com/api/crm/webhooks/shopify
5. Click: "Save"
6. Status should show: ✅ Active (green)
```

#### 2.3 Create Remaining Webhooks
Repeat step 2.2 for these events:
- customer updated
- order created
- order paid
- checkout abandoned

**Total**: 5 webhooks pointing to same endpoint

#### 2.4 Verify All Are Active
```
All 5 webhooks should show:
├─ ✅ customer created (Active)
├─ ✅ customer updated (Active)
├─ ✅ order created (Active)
├─ ✅ order paid (Active)
└─ ✅ checkout abandoned (Active)
```

### 2.5 Test the Connection

#### Test 1: Manual Test
```bash
ssh root@192.46.213.140
docker logs -f pureleven-ai-engine
# Watch for:
# POST /api/crm/webhooks/shopify - 200 OK
```

#### Test 2: Place Real Order
```
1. Go to: https://pureleven.com
2. Place a test order
3. Use a real email address
4. Complete checkout
```

#### Test 3: Verify Data Appears
```
Method 1: Check Dashboard
- Go to: https://ai.pureleven.com/static/dashboard.html
- Look for your customer email
- Should appear within 5-10 seconds

Method 2: Check Database
ssh root@192.46.213.140
docker exec -it pureleven-postgres psql -U pureleven -d pureleven
SELECT * FROM crm_customers WHERE email = 'your@email.com';
# Should show your customer data

Method 3: Check API
curl "https://ai.pureleven.com/api/crm/customers/your@email.com"
# Should return your customer profile
```

#### Test 4: Check Webhook Log
```
Shopify Admin → Settings → Notifications → Webhooks
1. Click on a webhook
2. Look for delivery logs
3. Should show ✅ 200 OK status
4. Timestamp should be recent
```

### Verification Checklist
- [ ] 5 webhooks created
- [ ] All show "Active" status
- [ ] Endpoint URL correct: https://track.pureleven.com/api/crm/webhooks/shopify
- [ ] Test order placed
- [ ] Customer appears in dashboard
- [ ] Data appears in database
- [ ] API returns customer data
- [ ] Webhook log shows 200 status

**Status After Completion**: ✅ **Real Shopify data syncing**

---

## Step 3: Configure GA4 Event Feed (45 minutes, OPTIONAL)

### What This Does
Automatically routes GA4 events to CRM for behavior tracking.

The live storefront now also has a direct relay for the product audience events, so GTM is only required if you want to maintain tag-managed routing instead of the storefront fallback.

### Time Required
- 30-45 minutes setup
- 15 minutes testing
- Total: ~1 hour

### Difficulty
Medium (but well-documented)

### Decision Point
**Should you do this?**
- ✅ YES if: You want behavior tracking (recommended)
- ✅ NO if: You want to focus on Shopify data first (can do later)

### 3.1 Open GTM Container
```
1. Go to: https://tagmanager.google.com
2. Account: Pureleven
3. Container: GTM-TFHBWPLM
4. You should see the workspace
```

### 3.2 Create Variables (10 minutes)

#### Variable 1: GA4 Event Data
```
Menu: Variables → New
Name: GA4 Event Data for CRM
Type: Custom JavaScript

Paste this code:
```javascript
function() {
  var eventName = {{Event}};
  var userEmail = {{DL - User Email}};
  var eventData = {
    email: userEmail,
    event_type: eventName,
    event_data: {
      page_title: {{Page Title}},
      page_url: {{Page URL}},
      value: {{Value}},
      currency: {{Currency}}
    }
  };
  return JSON.stringify(eventData);
}
```

Save: Click "Save"
```

#### Variable 2: User Email
```
Menu: Variables → New
Name: DL - User Email
Type: Data Layer Variable
Data Layer Name: user_email

Save: Click "Save"
```

### 3.3 Create HTTP Tag (10 minutes)

```
Menu: Tags → New
Name: CRM - GA4 Event Send
Type: HTTP Request

Configuration:
├─ Method: POST
├─ URL: https://track.pureleven.com/api/crm/events/ga4
├─ Headers:
│  ├─ Content-Type: application/json
│  └─ X-Source: ga4
└─ Body: {{GA4 Event Data for CRM}}

Save: Click "Save"
```

### 3.4 Create Trigger (5 minutes)

```
Menu: Triggers → New
Name: GA4 - All Events
Type: Event

Configuration:
├─ This trigger fires on: All Events
└─ (OR select specific events if desired)

Save: Click "Save"
```

### 3.5 Connect Tag to Trigger (5 minutes)

```
Menu: Tags
1. Find: CRM - GA4 Event Send
2. Click to edit
3. Under "Triggering": Click + icon
4. Select: GA4 - All Events
5. Click: Save
```

### 3.6 Test in Preview Mode (10 minutes)

```
1. GTM: Click "Preview" button (top right)
2. Opens preview mode
3. pureleven.com: Open in another tab
4. Perform actions:
   ├─ View a product
   ├─ Add to cart
   └─ View checkout

5. GTM Preview: Check console
   ├─ Tag "CRM - GA4 Event Send" should show green checkmark
   ├─ Status: "Fired"
   └─ No errors
```

### 3.7 Verify API Response

```bash
ssh root@192.46.213.140
docker logs -f pureleven-ai-engine | grep "events/ga4"

Expected:
POST /api/crm/events/ga4 - 200 OK
```

### 3.8 Publish to Production (5 minutes)

```
GTM: Click "Submit" (top right)
1. Version Name: "GA4 CRM Event Feed v1"
2. Description: "Routes GA4 events to CRM"
3. Click: "Publish"
4. Wait for: "Version published" message
```

### Verification Checklist
- [ ] Variable 1 created: GA4 Event Data for CRM
- [ ] Variable 2 created: DL - User Email
- [ ] Tag created: CRM - GA4 Event Send
- [ ] Trigger created: GA4 - All Events
- [ ] Tag connected to trigger
- [ ] Preview mode tested
- [ ] Tag firing (green checkmark)
- [ ] API receiving events (logs show 200 OK)
- [ ] Published to production
- [ ] Real GA4 events appearing in events table

**Status After Completion**: ✅ **GA4 behavior tracking active**

---

## Step 4: Verify Everything Works

### Quick Verification
```bash
# 1. SSH to server
ssh root@192.46.213.140

# 2. Check API logs
docker logs -f pureleven-ai-engine

# 3. Query database
docker exec -it pureleven-postgres psql -U pureleven -d pureleven
SELECT COUNT(*) FROM crm_customers;
SELECT COUNT(*) FROM crm_events;
SELECT COUNT(*) FROM crm_orders;

# 4. Expected output:
# - crm_customers: > 0 (has customer data)
# - crm_events: > 0 (has event data)
# - crm_orders: > 0 (has order data)
```

### Dashboard Verification
```
1. Go to: https://ai.pureleven.com/static/dashboard.html
2. Should see:
   ├─ Customer list populated
   ├─ Event count > 0
   ├─ Recent orders displayed
   └─ Segments calculated
```

### Full System Status
```
Expected Output:
┌─────────────────────────────┐
│ ✅ API: Running             │
│ ✅ Database: Connected      │
│ ✅ Dashboard: Loaded        │
│ ✅ Customers: Syncing       │
│ ✅ Events: Recording        │
│ ✅ Orders: Tracking         │
└─────────────────────────────┘
```

---

## Troubleshooting

### Issue: Webhooks Not Firing

**Check**:
1. Are all 5 webhooks created?
2. Do all show "Active" status?
3. Is the URL exactly: https://track.pureleven.com/api/crm/webhooks/shopify?

**Fix**:
```bash
ssh root@192.46.213.140
docker logs pureleven-ai-engine

# Look for errors
# If 404: Check endpoint URL
# If connection error: Check firewall
```

### Issue: Data Not Appearing in Dashboard

**Check**:
1. Did you place a test order?
2. Has it been more than 10 seconds?
3. Are there API errors in logs?

**Fix**:
1. Hard refresh dashboard: Ctrl+Shift+R
2. Check API is returning data:
   ```bash
   curl https://ai.pureleven.com/api/crm/customers
   ```
3. Check database directly:
   ```bash
   docker exec -it pureleven-postgres psql -U pureleven -d pureleven
   SELECT * FROM crm_customers LIMIT 1;
   ```

### Issue: GA4 Tag Not Firing

**Check**:
1. Is the trigger connected to the tag?
2. Are you in Preview mode?
3. Are there any variable errors?

**Fix**:
1. Edit tag → Check "Triggering" section
2. Make sure trigger is selected
3. Click Save
4. Exit Preview and re-enter

---

## Timeline

### Today (30 minutes)
- [ ] Read this guide (5 min)
- [ ] Verify system ready (5 min)
- [ ] Register Shopify webhooks (15 min)
- [ ] Test webhook (5 min)

### This Week (1 hour, optional)
- [ ] Configure GA4 in GTM (45 min)
- [ ] Test GA4 integration (15 min)

### Result
✅ Real customer data flowing automatically  
✅ GA4 events tracking behavior (optional)  
✅ Dashboard displaying live data  

---

## Quick Reference Commands

```bash
# SSH to server
ssh root@192.46.213.140

# View API logs
docker logs -f pureleven-ai-engine

# View last 50 lines
docker logs pureleven-ai-engine | tail -50

# Query database
docker exec -it pureleven-postgres psql -U pureleven -d pureleven

# Check customers
SELECT * FROM crm_customers ORDER BY created_at DESC LIMIT 5;

# Check events
SELECT * FROM crm_events ORDER BY created_at DESC LIMIT 5;

# Check orders
SELECT * FROM crm_orders ORDER BY created_at DESC LIMIT 5;

# Count records
SELECT COUNT(*) FROM crm_customers;
SELECT COUNT(*) FROM crm_events;
SELECT COUNT(*) FROM crm_orders;

# Test API endpoint
curl https://ai.pureleven.com/api/crm/health

# Test customer endpoint
curl https://ai.pureleven.com/api/crm/customers
```

---

## Support Resources

### Documentation
- **Quick Reference**: QUICK_REFERENCE.md
- **Shopify Setup**: WEBHOOK_REGISTRATION_MANUAL.md
- **GA4 Setup**: GA4_GTM_IMPLEMENTATION_CHECKLIST.md
- **Full Guide**: COMPREHENSIVE_README.md
- **API Reference**: CRM_API_DOCUMENTATION.md

### Getting Help
1. Check the relevant documentation file
2. Look at troubleshooting section above
3. Check API logs: `docker logs pureleven-ai-engine`
4. Query database directly to verify data
5. Review FINAL_VERIFICATION_REPORT.md for expected behavior

---

## Final Checklist

### System Ready? ✅
- [ ] Dashboard loads
- [ ] API health check works
- [ ] Database has sample data

### Shopify Webhooks Active? ⏳
- [ ] 5 webhooks registered
- [ ] All show "Active"
- [ ] Test order placed
- [ ] Data appears in dashboard

### GA4 Active? ⏳ (Optional)
- [ ] Variables created
- [ ] Tag created
- [ ] Trigger created
- [ ] Tag connected to trigger
- [ ] Published to production

### Everything Working? ✅
- [ ] Dashboard shows data
- [ ] API responds with 200 OK
- [ ] Database has records
- [ ] No errors in logs

---

## Next Steps

**Right Now** (5 min):
1. Read QUICK_REFERENCE.md
2. Verify dashboard loads

**Within 15 minutes**:
1. Follow WEBHOOK_REGISTRATION_MANUAL.md
2. Register Shopify webhooks

**Within 1 hour**:
1. Place test order
2. Verify data appears

**This week** (optional):
1. Follow GA4_GTM_IMPLEMENTATION_CHECKLIST.md
2. Configure GA4 event routing
3. Verify events flowing

---

## Success Criteria

**Minimum Success** (after Shopify webhooks):
- ✅ Customer appears in dashboard
- ✅ Order syncs from Shopify
- ✅ API returns customer data
- ✅ Database shows records

**Full Success** (after GA4 setup):
- ✅ All of above
- ✅ GA4 events recorded
- ✅ Event data in dashboard
- ✅ Behavior tracking active

---

**Status**: Ready to Activate  
**Estimated Time**: 45-60 minutes total  
**Your Next Step**: Follow WEBHOOK_REGISTRATION_MANUAL.md

**Everything is built and ready. You just need to activate it!**

---

*Questions? Check the relevant documentation file or review the troubleshooting section above.*
