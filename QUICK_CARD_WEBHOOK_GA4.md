# ⚡ QUICK REFERENCE CARD - Keep This Open While Executing

---

## 🔴 TASK 1: SHOPIFY WEBHOOKS (15 min)

### ENDPOINT (Copy this - use for ALL 5 webhooks)
```
https://track.pureleven.com/api/crm/webhooks/shopify
```

### THE 5 WEBHOOKS (Check each off as you create them)
```
□ 1. Customers → Customer created → https://track.pureleven.com/api/crm/webhooks/shopify
□ 2. Customers → Customer updated → https://track.pureleven.com/api/crm/webhooks/shopify
□ 3. Orders → Order created → https://track.pureleven.com/api/crm/webhooks/shopify
□ 4. Orders → Order paid → https://track.pureleven.com/api/crm/webhooks/shopify
□ 5. Checkouts → Checkout abandoned → https://track.pureleven.com/api/crm/webhooks/shopify
```

### NAVIGATION PATH
```
admin.shopify.com 
  → Settings (bottom left) 
  → Notifications 
  → Webhooks section 
  → "Create webhook" button
```

### VERIFICATION
```
All 5 should show: ✅ Active (green status)
```

**TIME: 15 min | STATUS: DO THIS FIRST**

---

## 🟡 TASK 2: GA4 EVENT FEED (45 min)

### URLS TO USE
```
GTM Workspace: https://tagmanager.google.com
GTM Container: GTM-TFHBWPLM
API Endpoint: https://track.pureleven.com/api/crm/events/ga4
```

### NAVIGATION PATH
```
tagmanager.google.com 
  → Select Account: Pureleven 
  → Select Container: GTM-TFHBWPLM
  → Work in Workspace
```

### 3 COMPONENTS TO CREATE (In this order)

#### 1️⃣ VARIABLE: GA4 Event Data for CRM
```
Type: Custom JavaScript
Location: Variables → User-Defined Variables → New

Code (COPY-PASTE EXACTLY):
―――――――――――――――――――――――
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
―――――――――――――――――――――――
```

#### 2️⃣ VARIABLE: DL - User Email
```
Type: Data Layer Variable
Location: Variables → User-Defined Variables → New
Data Layer Variable Name: user_email
```

#### 3️⃣ TAG: CRM - GA4 Event Send
```
Type: HTTP Request
Location: Tags → New

Configuration:
  URL: https://track.pureleven.com/api/crm/events/ga4
  Method: POST
  Content-Type: application/json
  Body: {{GA4 Event Data for CRM}}
```

#### 4️⃣ TRIGGER: GA4 - All Events
```
Type: Event
Trigger Type: All Events
Event Name: gtag.event
```

### PUBLISH
```
Click: Submit (top right)
Version Name: GA4-CRM-Event-Feed-v1
Click: Publish
```

### TEST (After publishing)
```bash
curl -X POST https://track.pureleven.com/api/crm/events/ga4 \
  -H "Content-Type: application/json" \
  -d '{"email":"test@pureleven.com","event_type":"test_event"}' \
  -w '\nHTTP Status: %{http_code}\n'

Expected: HTTP 200 OK
```

**TIME: 45 min | STATUS: OPTIONAL BUT RECOMMENDED**

---

## ✅ VERIFICATION CHECKLIST

### After BOTH tasks complete, verify:

**Shopify**:
```
□ All 5 webhooks show ✅ Active (green)
□ Endpoint: https://track.pureleven.com/api/crm/webhooks/shopify
□ API Version: Latest available
```

**GA4**:
```
□ Variables created: 2
□ Tags created: 1
□ Triggers created: 1
□ Published to live
□ Curl test returns: 200 OK
```

**Dashboard**:
```
□ Loads at: https://ai.pureleven.com/static/dashboard.html
□ No console errors
□ Data visible
```

---

## 🚨 COPY-PASTE HELPERS

### If you need the endpoint again:
```
https://track.pureleven.com/api/crm/webhooks/shopify
```

### If you need the GA4 API endpoint:
```
https://track.pureleven.com/api/crm/events/ga4
```

### If you need GTM container ID:
```
GTM-TFHBWPLM
```

---

## ⏱️ TIME BREAKDOWN

```
Task 1 (Shopify): 15 minutes
  - Login: 2 min
  - Create webhooks: 10 min
  - Verify: 3 min

Task 2 (GA4): 45 minutes
  - Login GTM: 2 min
  - Create variables: 10 min
  - Create tag: 5 min
  - Create trigger: 3 min
  - Setup trigger assignment: 2 min
  - Publish: 3 min
  - Verify: 10 min
  - Test: 10 min

TOTAL: ~60 minutes
```

---

## 🎯 FULL EXECUTION CHECKLIST

**START TIME**: ___:___ AM/PM  
**ESTIMATED END**: ___:___ AM/PM

### SHOPIFY WEBHOOKS
- [ ] Logged into Shopify Admin
- [ ] Navigated to Settings → Notifications → Webhooks
- [ ] Webhook #1 Created (Customer created)
- [ ] Webhook #2 Created (Customer updated)
- [ ] Webhook #3 Created (Order created)
- [ ] Webhook #4 Created (Order paid)
- [ ] Webhook #5 Created (Checkout abandoned)
- [ ] All 5 showing ✅ Active status
- [ ] Screenshot taken for verification

### GA4 SETUP
- [ ] Logged into Google Tag Manager
- [ ] Selected GTM-TFHBWPLM container
- [ ] Created Variable #1: GA4 Event Data for CRM
- [ ] Created Variable #2: DL - User Email
- [ ] Created Tag: CRM - GA4 Event Send
- [ ] Created Trigger: GA4 - All Events
- [ ] Assigned trigger to tag
- [ ] Published changes (v1)
- [ ] Curl test successful (200 OK)
- [ ] Dashboard verified

### SIGN-OFF
- [ ] ALL TASKS COMPLETE ✅
- [ ] Time taken: ____ minutes
- [ ] Everything working ✅

---

**Created**: May 18, 2026
**Status**: Ready to Execute
**Est. Duration**: 60 minutes total
