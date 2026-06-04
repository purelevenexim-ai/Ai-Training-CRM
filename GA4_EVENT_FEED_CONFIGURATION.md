# GA4 Event Feed Configuration Guide

**Objective**: Route GA4 events to Pureleven CRM for behavior tracking  
**Endpoint**: `https://track.pureleven.com/api/crm/events/ga4`  
**Platform**: Google Tag Manager (GTM-TFHBWPLM)  
**Status**: Configuration Guide (Requires GTM Access)

---

## Overview

GA4 events will be forwarded to the CRM to track customer behavior and create a complete event history.

The storefront also now includes a lightweight direct relay for the product audience events (`pl_product_interest`, `pl_high_intent`, `pl_cross_category`, `pl_combo_interest`, `pl_add_to_cart_interest`) so those signals can reach the CRM even if GTM is not yet publishing the custom event tags.

### What Gets Tracked
- Page views
- Add to cart
- Begin checkout
- Purchase
- View item
- Search
- Custom events

### Data Flow
```
GA4 Event → GTM Container → CRM API → PostgreSQL
   (on-site)   (filter/tag)    (store)    (persist)
```

Fallback direct relay for product audience events:
```
Storefront audience snippet → CRM API → PostgreSQL
```

---

## Prerequisites

- ✅ GA4 property linked (already done in Phase 2)
- ✅ GTM-TFHBWPLM container active
- ✅ CRM API endpoint ready: `https://track.pureleven.com/api/crm/events/ga4`
- ✅ GTM access: https://tagmanager.google.com

---

## Configuration Steps

### Step 1: Open GTM Container

1. Go to: https://tagmanager.google.com
2. Select Account: **Pureleven**
3. Select Container: **GTM-TFHBWPLM** (Web container)
4. You should see the workspace

### Step 2: Create GA4 Event Custom JavaScript Variable

This variable will capture GA4 event data for sending to CRM.

**Steps**:
1. Click **Variables** in left menu
2. Under "User-Defined Variables", click **New**
3. Name: `GA4 Event Data for CRM`
4. Variable Type: **Custom JavaScript**
5. Paste the following code:

```javascript
function() {
  // Get the GA4 event data from GTM
  var eventName = {{Event}};
  var userEmail = {{user_email}}; // Custom user email variable
  var eventData = {
    event_type: eventName,
    timestamp: new Date().toISOString(),
    user_id: {{Google Analytics ID}},
    event_data: {
      page_title: {{Page Title}},
      page_url: {{Page URL}},
      referrer: {{Referrer}},
      user_agent: {{User Agent}}
    }
  };
  
  // Add event-specific data
  if (eventName === 'purchase') {
    eventData.event_data.value = {{Value}};
    eventData.event_data.currency = {{Currency}};
    eventData.event_data.transaction_id = {{Transaction ID}};
    eventData.event_data.items = {{Items}};
  } else if (eventName === 'add_to_cart') {
    eventData.event_data.value = {{Value}};
    eventData.event_data.currency = {{Currency}};
    eventData.event_data.items = {{Items}};
  } else if (eventName === 'view_item') {
    eventData.event_data.item_id = {{Item ID}};
    eventData.event_data.item_name = {{Item Name}};
    eventData.event_data.item_category = {{Item Category}};
    eventData.event_data.value = {{Value}};
    eventData.event_data.currency = {{Currency}};
  }
  
  return eventData;
}
```

6. Click **Save**

---

### Step 3: Create User Email Variable (Data Layer)

This captures customer email from your data layer.

**Steps**:
1. Click **Variables** → **New**
2. Name: `DL - User Email`
3. Variable Type: **Data Layer Variable**
4. Data Layer Variable Name: `user_email`
5. Click **Save**

---

### Step 4: Create CRM Event Tag

This tag sends GA4 events to the CRM API.

**Steps**:
1. Click **Tags** in left menu
2. Click **New**
3. Name: `CRM - GA4 Event Send`
4. Tag Type: **HTTP Request**
5. Configure the following:

**HTTP Method**: POST
**URL**: `https://track.pureleven.com/api/crm/events/ga4`

**Headers** (add these headers):
| Key | Value |
|-----|-------|
| Content-Type | application/json |
| X-Source | ga4 |

**Request Body** (select "POST body" type):
```
{{GA4 Event Data for CRM}}
```

Or paste this JSON directly:
```json
{
  "email": "{{DL - User Email}}",
  "event_type": "{{Event}}",
  "event_data": {
    "page_url": "{{Page URL}}",
    "page_title": "{{Page Title}}",
    "value": "{{Value}}",
    "currency": "{{Currency}}"
  }
}
```

6. Click **Save**

---

### Step 5: Create Trigger for GA4 Events

This trigger fires the tag when GA4 events occur.

**Steps**:
1. Click **Triggers** in left menu
2. Click **New**
3. Name: `GA4 - All Events`
4. Trigger Type: **Event**
5. Event Name: `gtag.event` (or your GA4 event name)
6. Configure:
   - **This trigger fires on**: All Events
   - Or select specific events:
     - `purchase`
     - `add_to_cart`
     - `begin_checkout`
     - `view_item`
     - `page_view`
     - `search`

7. Click **Save**

---

### Step 6: Connect Trigger to Tag

1. Go to **Tags**
2. Find **CRM - GA4 Event Send** tag
3. Under "Triggering", click the + icon
4. Select **GA4 - All Events** trigger
5. Click **Save**

---

### Step 7: Add Exception Rules (Optional)

To avoid sending certain events to CRM (e.g., internal test events):

**Steps**:
1. In the trigger configuration
2. Under "This trigger fires on"
3. Add exception conditions:
   - Event Name does not contain "gtag.exception"
   - Event Name does not contain "test"

---

### Step 8: Preview & Test

1. Click **Preview** button (top right)
2. Open pureleven.com in a new tab
3. Perform actions:
   - View a page (should send page_view event)
   - Add item to cart (should send add_to_cart event)
   - Complete purchase (should send purchase event)
4. Check GTM preview panel for events
5. Verify events appear in CRM endpoint logs

---

### Step 9: Publish to Production

Once testing confirms events are flowing:

1. Click **Submit** button (top right)
2. Add version name: `GA4 CRM Event Feed v1`
3. Add description: `Routes GA4 events to CRM for behavior tracking`
4. Click **Publish**
5. Wait for confirmation

---

## Testing the Integration

### Test 1: Verify GTM Tag Fires

**Steps**:
1. Go to GTM Preview mode (Preview button)
2. Open pureleven.com in another tab
3. Perform action (e.g., view product)
4. In GTM preview console, look for:
   - Event name appears
   - Tag "CRM - GA4 Event Send" fires (shows as green)
   - Tag shows in the "Tags Fired On This Page" section

**Expected Result**: Tag fires without errors

---

### Test 2: Verify CRM Receives Events

**Steps**:
1. SSH to server:
   ```bash
   ssh root@192.46.213.140
   docker logs -f pureleven-ai-engine
   ```
2. Perform action on pureleven.com (e.g., place order)
3. Watch the server logs
4. Look for:
   ```
   POST /api/crm/events/ga4 - 200 OK
   Event received: {event_type: "purchase", email: "..."}
   ```

**Expected Result**: API logs show 200 status for event

---

### Test 3: Verify Data in CRM Dashboard

**Steps**:
1. Open CRM dashboard: https://ai.pureleven.com/static/dashboard.html
2. Wait 5-10 seconds for data to refresh
3. Look for:
   - Customer email populated
   - Event count increased
   - Recent events listed

**Expected Result**: Event appears in dashboard

---

### Test 4: Verify Database Storage

**Steps**:
1. SSH to server:
   ```bash
   ssh root@192.46.213.140
   docker exec -it pureleven-postgres psql -U pureleven -d pureleven
   ```
2. Run query:
   ```sql
   SELECT event_type, COUNT(*) FROM crm_events 
   GROUP BY event_type 
   ORDER BY COUNT(*) DESC;
   ```
3. Should see event counts for:
   - page_view
   - add_to_cart
   - purchase
   - etc.

**Expected Result**: Events stored in database

---

## Expected Event Payloads

### Purchase Event

```json
{
  "email": "customer@example.com",
  "event_type": "purchase",
  "event_data": {
    "value": 5000,
    "currency": "INR",
    "transaction_id": "TXN-12345",
    "items": [
      {
        "item_id": "prod-123",
        "item_name": "Kerala Cardamom",
        "quantity": 1,
        "price": 5000
      }
    ]
  }
}
```

### Add to Cart Event

```json
{
  "email": "customer@example.com",
  "event_type": "add_to_cart",
  "event_data": {
    "value": 240,
    "currency": "INR",
    "items": [
      {
        "item_id": "prod-456",
        "item_name": "Kerala Pepper",
        "quantity": 1,
        "price": 240
      }
    ]
  }
}
```

### Page View Event

```json
{
  "email": null,
  "event_type": "page_view",
  "event_data": {
    "page_url": "https://pureleven.com/products/kerala-cardamom",
    "page_title": "Kerala Cardamom - Organic Pure Leven",
    "referrer": "https://google.com"
  }
}
```

---

## Troubleshooting

### Issue: Tag Not Firing

**Symptoms**: GTM preview shows trigger firing but tag doesn't fire

**Solutions**:
1. Verify trigger is connected to tag
2. Check trigger condition (make sure it matches your events)
3. Check if there are any blocking conditions
4. Verify tag configuration is correct

### Issue: API Returning 400/401

**Symptoms**: Tag fires but API shows error

**Solutions**:
1. Check JSON payload formatting
2. Verify email field is included
3. Check Content-Type header is "application/json"
4. Verify endpoint URL has no typos

### Issue: Events Not Appearing in Dashboard

**Symptoms**: API shows 200 OK but events don't appear in dashboard

**Solutions**:
1. Verify email field is populated (required for customer matching)
2. Check database query: `SELECT COUNT(*) FROM crm_events;`
3. Refresh dashboard (hard refresh: Ctrl+Shift+R)
4. Check server logs for any processing errors

### Issue: High Volume of Events

**Symptoms**: API responding slowly, server CPU high

**Solutions**:
1. Add filter in trigger to send only key events
2. Filter out page_view events if too frequent
3. Increase API instance if needed
4. Set up log rotation to prevent disk fill

---

## Performance Expectations

### Event Processing

| Metric | Value | Notes |
|--------|-------|-------|
| API response time | ~150-200ms | Fast processing |
| Event storage latency | ~100-500ms | Depends on DB query |
| Dashboard update | 2-5 seconds | After refresh |
| Event query response | ~50-100ms | Fast lookup |

### Scaling

| Users | Events/Day | Expected Latency | Status |
|-------|-----------|-----------------|--------|
| 100 | 10K | <500ms | ✅ Fine |
| 500 | 50K | <500ms | ✅ Fine |
| 1,000 | 100K | ~500-800ms | ✅ Acceptable |
| 5,000+ | 500K+ | >1s | ⚠️ May need optimization |

---

## Security Considerations

### ✅ Currently Implemented

- HTTPS/TLS encryption for all traffic
- Event data stored in secure PostgreSQL
- No API authentication (internal use only)

### ⏳ Optional Enhancements

- API key requirement for event endpoint
- Rate limiting per IP
- HMAC request signing
- IP whitelisting

---

## Next Steps

### Immediate (After Configuration)

1. Configure GA4 tags in GTM (follow steps above)
2. Test with real customer actions
3. Monitor event flow
4. Verify data appears in CRM dashboard

### Optional Future

1. Create custom event types
2. Add advanced segmentation based on events
3. Create behavior-based customer journeys
4. Add predictive models using event history

---

## Reference Documentation

### API Endpoint Details

```
Endpoint: POST /api/crm/events/ga4
URL: https://track.pureleven.com/api/crm/events/ga4
Headers: Content-Type: application/json
Method: POST
Authentication: None (public endpoint)
Rate Limit: None (currently)
Timeout: 30 seconds
```

### Required Fields

- `email` (string) - Customer email for matching
- `event_type` (string) - Type of event (purchase, add_to_cart, etc)
- `event_data` (object) - Event-specific data

### Optional Fields

- `timestamp` (datetime) - When event occurred
- `user_id` (string) - GA4 user ID
- `transaction_id` (string) - For purchase events
- `items` (array) - Product items in event

---

## Verification Checklist

Before moving to production:

- [ ] GTM variables created (GA4 Event Data, User Email)
- [ ] CRM Event tag created with correct payload
- [ ] Trigger created for GA4 events
- [ ] Tag connected to trigger
- [ ] Preview mode tested (events fire)
- [ ] Manual test completed (placed test order)
- [ ] API logs show 200 responses
- [ ] Events appear in database
- [ ] Dashboard displays events
- [ ] Tag published to production

---

## Support

### Quick Commands

```bash
# View API logs
ssh root@192.46.213.140
docker logs -f pureleven-ai-engine | grep "events/ga4"

# Query events in database
docker exec -it pureleven-postgres psql -U pureleven -d pureleven
SELECT * FROM crm_events ORDER BY created_at DESC LIMIT 10;

# Test API endpoint manually
curl -X POST https://track.pureleven.com/api/crm/events/ga4 \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "event_type": "purchase",
    "event_data": {"value": 1000, "currency": "INR"}
  }'
```

### Reference Links

- GTM Container: https://tagmanager.google.com/?pli=1#/container/accounts/6194985495/containers/165231797/workspaces/9
- GA4 Property: https://analytics.google.com/analytics/web/#/a245646597p429219662
- CRM API: https://ai.pureleven.com/api/crm/health
- CRM Dashboard: https://ai.pureleven.com/static/dashboard.html

---

## Summary

Once configured, the GA4 event feed will:
- ✅ Capture all user interactions on pureleven.com
- ✅ Send event data to CRM in real-time
- ✅ Store events in database for analysis
- ✅ Display in CRM dashboard with 2-5 second latency
- ✅ Create complete behavior history per customer

**Time to configure**: 30-45 minutes  
**Time to verify**: 15-20 minutes  
**Total**: ~1 hour

---

**Last Updated**: May 17, 2026  
**Status**: Configuration Guide Ready  
**Next Action**: Implement in GTM (requires GTM access)
