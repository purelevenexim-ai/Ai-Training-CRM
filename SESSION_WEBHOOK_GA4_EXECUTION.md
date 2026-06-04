# 🚀 EXECUTION PLAN: Shopify Webhooks + GA4 Setup
**Date**: May 18, 2026  
**Total Time**: ~60 minutes (15 min webhooks + 45 min GA4)  
**Status**: Ready for immediate execution

---

## ✅ PRE-FLIGHT CHECKLIST

Before starting, verify you have:
- [ ] Shopify store admin access (hello@pureleven.com)
- [ ] Google account access for GTM
- [ ] Google Analytics 4 access
- [ ] This checklist open in a browser tab
- [ ] 60 minutes uninterrupted time

---

# 🔴 TASK 1: SHOPIFY WEBHOOKS (15 minutes)

## Phase 1A: Setup Access

### Step 1: Log Into Shopify Admin
```
URL: https://admin.shopify.com
Action:
  1. Enter email: hello@pureleven.com
  2. Continue with email
  3. Complete authentication
  4. Select store: Organic Pure Leven (rwxtic-gz)
```

### Step 2: Navigate to Webhooks
```
Once in admin dashboard:
  1. Click Settings (bottom left sidebar)
  2. Click Notifications
  3. Scroll down to "Webhooks" section
  4. You'll see "Create webhook" button
```

---

## Phase 1B: Create 5 Webhooks

### COPY-PASTE ENDPOINT (Use this for all 5)
```
https://track.pureleven.com/api/crm/webhooks/shopify
```

---

### ✅ WEBHOOK #1: Customer Created

**Action**: Click "Create webhook"

**Fill in form**:
```
Event:        Customers > Customer created
URL:          https://track.pureleven.com/api/crm/webhooks/shopify
Format:       JSON (default)
API Version:  Use latest available
```

**Result**: Click Save → Should show ✅ Active (green status)

**Verification**: You should see a success message

---

### ✅ WEBHOOK #2: Customer Updated

**Action**: Click "Create webhook" again

**Fill in form**:
```
Event:        Customers > Customer updated
URL:          https://track.pureleven.com/api/crm/webhooks/shopify
Format:       JSON
API Version:  Same as above
```

**Result**: Click Save → Verify ✅ Active

---

### ✅ WEBHOOK #3: Order Created

**Action**: Click "Create webhook" again

**Fill in form**:
```
Event:        Orders > Order created
URL:          https://track.pureleven.com/api/crm/webhooks/shopify
Format:       JSON
API Version:  Same as above
```

**Result**: Click Save → Verify ✅ Active

---

### ✅ WEBHOOK #4: Order Paid

**Action**: Click "Create webhook" again

**Fill in form**:
```
Event:        Orders > Order paid
URL:          https://track.pureleven.com/api/crm/webhooks/shopify
Format:       JSON
API Version:  Same as above
```

**Result**: Click Save → Verify ✅ Active

---

### ✅ WEBHOOK #5: Checkout Abandoned

**Action**: Click "Create webhook" again

**Fill in form**:
```
Event:        Checkouts > Checkout abandoned
URL:          https://track.pureleven.com/api/crm/webhooks/shopify
Format:       JSON
API Version:  Same as above
```

**Result**: Click Save → Verify ✅ Active

---

## Phase 1C: Final Verification

**In Webhooks section, you should now see ALL 5**:
- [ ] ✅ Customer created — Active
- [ ] ✅ Customer updated — Active
- [ ] ✅ Order created — Active
- [ ] ✅ Order paid — Active
- [ ] ✅ Checkout abandoned — Active

**Status**: 🟢 SHOPIFY WEBHOOKS COMPLETE

**Time elapsed**: 15 minutes

**What this enables**: 
- Real-time customer data sync from Shopify to CRM
- Order tracking
- Abandoned checkout monitoring

---

# 🟡 TASK 2: GA4 EVENT FEED (45 minutes)

## Phase 2A: GTM Setup Access

### Step 1: Log Into Google Tag Manager
```
URL: https://tagmanager.google.com
Action:
  1. Click email field
  2. Enter your Google account email
  3. Click Next
  4. Complete authentication
```

### Step 2: Select Pureleven GTM Container
```
Once logged in:
  1. Click "Accounts" in the left sidebar
  2. Find and select: Pureleven (Account)
  3. Select: GTM-TFHBWPLM (Web container)
  4. You're now in the GTM workspace
```

---

## Phase 2B: Create Variables

### VARIABLE #1: GA4 Event Data for CRM

**Location**: In GTM workspace → Variables (left menu) → User-Defined Variables

**Action**: Click "New" button

**Form**:
```
Name: GA4 Event Data for CRM
Type: Custom JavaScript
```

**Code** (copy-paste exactly):
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
      referrer: {{Referrer}},
      user_agent: {{User Agent}},
      value: {{Value}},
      currency: {{Currency}},
      transaction_id: {{Transaction ID}},
      items: {{Items}}
    }
  };
  return JSON.stringify(eventData);
}
```

**Action**: Click Save

**Result**: You should see it in the User-Defined Variables list

---

### VARIABLE #2: DL - User Email

**Location**: Variables → User-Defined Variables

**Action**: Click "New" button

**Form**:
```
Name: DL - User Email
Type: Data Layer Variable
Data Layer Variable Name: user_email
```

**Action**: Click Save

**Result**: Variable saved successfully

---

## Phase 2C: Create Tag

### TAG: CRM - GA4 Event Send

**Location**: Tags (left menu) → New

**Form**:
```
Name: CRM - GA4 Event Send
Type: HTTP Request
```

**Configuration**:
```
URL: https://track.pureleven.com/api/crm/events/ga4
Method: POST
Content Type: application/json
```

**Request Body** (copy-paste exactly):
```
{{GA4 Event Data for CRM}}
```

**Click**: Save

---

## Phase 2D: Create Trigger

### TRIGGER: GA4 - All Events

**Location**: Triggers → New

**Form**:
```
Name: GA4 - All Events
Trigger Type: Event
Event Name: gtag.event
This trigger fires on: All Events
```

**Action**: Click Save

---

## Phase 2E: Assign Trigger to Tag

**Back in GTM workspace**:

1. Click on the tag you just created: "CRM - GA4 Event Send"
2. Under "Triggering" section, click the trigger box
3. Select: "GA4 - All Events"
4. Click Save

---

## Phase 2F: Publish Changes

**Location**: Top right of GTM

**Action**:
1. Click "Submit" button (top right)
2. Add version name: `GA4-CRM-Event-Feed-v1`
3. Click "Publish"

**Result**: 
- You'll see "Version published" message
- Changes are now live

---

## Phase 2G: Verification

### Check 1: Verify GTM Container
```
Go to: https://tagmanager.google.com
Workspace should show:
  ✅ Variables:
    - GA4 Event Data for CRM
    - DL - User Email
  ✅ Tags:
    - CRM - GA4 Event Send
  ✅ Triggers:
    - GA4 - All Events
```

### Check 2: Test API Endpoint
```bash
# Open Terminal and run:
curl -X POST https://track.pureleven.com/api/crm/events/ga4 \
  -H "Content-Type: application/json" \
  -d '{"email":"test@pureleven.com","event_type":"test_event"}' \
  -w '\nHTTP Status: %{http_code}\n'

# Expected response: HTTP 200 OK
```

### Check 3: Verify Dashboard
```
Go to: https://ai.pureleven.com/static/dashboard.html
You should see:
  ✅ Dashboard loads
  ✅ Data visible
  ✅ No errors in console
```

---

## Status: 🟢 GA4 EVENT FEED COMPLETE

**Time elapsed**: 45 minutes

**What this enables**:
- Real-time GA4 event tracking
- Event data flowing to CRM
- Dashboard updates with GA4 events
- Advanced analytics

---

# ✅ FINAL VERIFICATION (All Tasks Complete)

## Shopify Webhooks
- [ ] All 5 webhooks created
- [ ] All showing ✅ Active status
- [ ] Endpoint: https://track.pureleven.com/api/crm/webhooks/shopify

## GA4 Event Feed
- [ ] GTM variables created (2)
- [ ] GTM tag created (1)
- [ ] GTM trigger created (1)
- [ ] Published to live
- [ ] API test returns 200 OK
- [ ] Dashboard accessible

---

# 🎯 WHAT'S NEXT (After Both Tasks Complete)

## Immediate (Today):
```
1. Place a test order on pureleven.com
   - Email: testing1@example.com
   - Use COD payment
   
2. Monitor:
   - Terminal: docker logs -f pureleven-ai-engine
   - Database: Check for new customer
   - Dashboard: Watch for real-time update

3. Expected flow:
   Customer places order
        ↓
   Shopify webhook fires → CRM API receives data
        ↓
   Database stores customer/order
        ↓
   Dashboard updates in real-time
        ↓
   GA4 events flow in
```

## This Week:
```
1. Run 4-5 more test orders
2. Test different products
3. Test coupon application
4. Document any issues
5. Go live with real customers
```

---

# 📞 TROUBLESHOOTING

## If Shopify Webhooks Show "Inactive"
```
✓ Check endpoint URL (copy-paste to avoid typos)
✓ Verify HTTPS (must be https://, not http://)
✓ Wait 30 seconds - sometimes takes time to activate
✓ Refresh page in Shopify admin
```

## If GA4 Events Not Flowing
```
✓ Verify GTM container is published
✓ Check browser console for JavaScript errors
✓ Verify GA4 data layer has "user_email" value
✓ Test curl command for API endpoint
```

## If Dashboard Not Updating
```
✓ Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
✓ Clear browser cache
✓ Check API health: curl https://track.pureleven.com/api/crm/health
✓ Verify database is running: docker exec -it pureleven-postgres psql...
```

---

# 📊 SUMMARY

| Task | Duration | Status |
|------|----------|--------|
| Shopify Webhooks (5 total) | 15 min | 🔴 PRIORITY |
| GA4 Event Feed Setup | 45 min | 🟡 OPTIONAL |
| **TOTAL** | **60 min** | Ready |

**Expected Outcome**: 
- ✅ Real-time customer data flowing from Shopify
- ✅ GA4 events tracked in CRM
- ✅ Dashboard showing live updates
- ✅ System ready for production testing

---

**Created**: May 18, 2026  
**Ready**: YES  
**Estimated Completion Time**: 60 minutes (including verification)
