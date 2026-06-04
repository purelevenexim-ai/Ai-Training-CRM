# GA4 Event Feed - GTM Implementation Checklist

**Status**: Ready for Implementation  
**Platform**: Google Tag Manager (GTM-TFHBWPLM)  
**Complexity**: Medium (30-45 minutes)  
**Created**: May 17, 2026

---

## Prerequisites

✅ Verified Complete:
- GA4 property linked to GTM
- CRM API endpoint: https://track.pureleven.com/api/crm/events/ga4
- API health check: Passing
- Database: Ready to store events
- Dashboard: Ready to display events

---

## Implementation Overview

You will create 3 components in GTM:

```
1. User-Defined Variables
   ├─ GA4 Event Data for CRM (Custom JavaScript)
   └─ DL - User Email (Data Layer Variable)

2. Tag
   └─ CRM - GA4 Event Send (HTTP Request)

3. Trigger
   └─ GA4 - All Events (Event-based trigger)
```

---

## Step 1: Navigate to GTM Workspace

1. Go to: https://tagmanager.google.com
2. Select: **Pureleven** (Account)
3. Select: **GTM-TFHBWPLM** (Web container)
4. You should see the workspace

---

## Step 2: Create Variables (Part 1)

### Variable 1: GA4 Event Data for CRM

**Location**: Variables → New (under User-Defined Variables section)

**Name**: `GA4 Event Data for CRM`

**Type**: Custom JavaScript

**Code** (copy and paste exactly):

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

**Click**: Save

---

## Step 3: Create Variables (Part 2)

### Variable 2: DL - User Email

**Location**: Variables → New (under User-Defined Variables)

**Name**: `DL - User Email`

**Type**: Data Layer Variable

**Data Layer Variable Name**: `user_email`

**Click**: Save

---

## Step 4: Create HTTP Request Tag

**Location**: Tags → New

**Name**: `CRM - GA4 Event Send`

**Tag Type**: HTTP Request

### Configuration:

**HTTP Method**: POST

**URL**: `https://track.pureleven.com/api/crm/events/ga4`

**Headers** (Click "Add Header" for each):
| Header | Value |
|--------|-------|
| Content-Type | application/json |
| X-Event-Source | ga4 |

**Request Body**: Enable "POST body" and paste:
```json
{{GA4 Event Data for CRM}}
```

Or use this simpler version:
```json
{
  "email": "{{DL - User Email}}",
  "event_type": "{{Event}}",
  "event_data": {
    "page_title": "{{Page Title}}",
    "page_url": "{{Page URL}}",
    "value": "{{Value}}",
    "currency": "{{Currency}}"
  }
}
```

### Advanced Options:
- **Conversion Linker**: Enabled (if using conversion tracking)
- **Execute Tag**: On page load or event
- **Tag Sequencing**: None

**Click**: Save

---

## Step 5: Create Trigger for Events

**Location**: Triggers → New

**Name**: `GA4 - All Events`

**Trigger Type**: Event

### Configuration:

**This trigger fires on**: Select **All Events**

OR (for specific events):
- eventName does NOT start with "gtag."
- eventName does NOT equal "exception"

**Click**: Save

---

## Step 6: Connect Trigger to Tag

1. Go to **Tags** section
2. Find **CRM - GA4 Event Send** tag
3. Click on it to edit
4. Under **Triggering**, click the + icon
5. Select **GA4 - All Events**
6. Click **Save**

---

## Step 7: Test in Preview Mode

1. Click **Preview** button (top right)
2. Open pureleven.com in another tab
3. Perform these actions:
   - View a product
   - Add to cart
   - View checkout

4. Return to GTM preview console
5. Look for:
   - Event names appear
   - Tag "CRM - GA4 Event Send" shows **green checkmark**
   - No errors in the Events section

### Expected Tag Firing:
```
Tag: CRM - GA4 Event Send
Status: ✓ Fired (200)
Time: ~200ms
```

---

## Step 8: Verify API Receives Data

After testing in Preview mode:

```bash
# SSH to server
ssh root@192.46.213.140

# View API logs
docker logs -f pureleven-ai-engine | grep "events/ga4"

# Should see:
# POST /api/crm/events/ga4 - 200 OK
```

---

## Step 9: Test the Full Flow

1. Exit Preview mode
2. Go to pureleven.com
3. Place a test order (or view products)
4. Wait 5 seconds
5. Open CRM Dashboard: https://ai.pureleven.com/static/dashboard.html
6. Should see event data

---

## Step 10: Publish to Production

Once verified:

1. Click **Submit** button (top right in GTM)
2. **Version Name**: `GA4 CRM Event Feed v1`
3. **Description**: `Routes GA4 events to CRM for behavior tracking`
4. Click **Publish**
5. Wait for "Version published" confirmation

---

## Troubleshooting

### Tag Not Firing in Preview

**Check**:
1. Is trigger connected to tag?
   - Go to tag, look for trigger under "Triggering"
2. Is trigger condition correct?
   - Should be "All Events" or specific event names
3. Are there any preview warnings?
   - Check the "Summary" tab in preview console

**Fix**:
```
1. Edit tag → Check "Triggering" section
2. Make sure trigger is selected
3. Click Save
4. Exit and re-enter Preview mode
```

### API Returning 400/401 Error

**Check**:
1. Is JSON valid?
   - Check quotation marks and commas
2. Is Content-Type header correct?
   - Should be: application/json
3. Is endpoint URL correct?
   - Should be: https://track.pureleven.com/api/crm/events/ga4

**Fix**:
```
1. Edit tag
2. Check JSON body syntax
3. Check headers match exactly
4. Verify URL has no typos
5. Test manually:
   curl -X POST https://track.pureleven.com/api/crm/events/ga4 \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","event_type":"test"}'
```

### Events Not Appearing in Database

**Check**:
1. SSH to server and check logs:
   ```bash
   docker logs pureleven-ai-engine | tail -50
   ```
2. Query database:
   ```bash
   docker exec -it pureleven-postgres psql -U pureleven -d pureleven
   SELECT COUNT(*) FROM crm_events;
   ```

**Fix**:
1. Verify email field is populated
2. Check server logs for errors
3. Verify customer exists in crm_customers table
4. Check database connection is active

---

## Performance Testing

After going live, monitor:

```bash
# Check event throughput
docker exec pureleven-postgres psql -U pureleven -d pureleven \
  -c "SELECT event_type, COUNT(*) FROM crm_events GROUP BY event_type;"

# Check API response time
docker logs pureleven-ai-engine | grep "200 OK"

# Monitor memory usage
docker stats pureleven-ai-engine
```

---

## Expected Results

### After Implementation

✅ GA4 events automatically captured  
✅ Events sent to CRM API  
✅ Events stored in PostgreSQL  
✅ Dashboard displays events  
✅ Customer profiles enriched with event data  

### Timeline

| Phase | Time | Status |
|-------|------|--------|
| GTM configuration | 30-45 min | Manual |
| Testing & verification | 10-15 min | Manual |
| Publication | 5 min | Click to publish |
| **Total** | **45-65 min** | - |

---

## Quick Reference

### GTM Workspace
- **URL**: https://tagmanager.google.com
- **Account**: Pureleven
- **Container**: GTM-TFHBWPLM
- **Workspace**: Default Workspace

### API Details
- **Endpoint**: https://track.pureleven.com/api/crm/events/ga4
- **Method**: POST
- **Headers**: Content-Type: application/json
- **Auth**: None (public endpoint)

### Server Access
```bash
ssh root@192.46.213.140
# Password: QazPlm123!@#

# View logs
docker logs -f pureleven-ai-engine

# Check database
docker exec -it pureleven-postgres psql -U pureleven -d pureleven
SELECT * FROM crm_events ORDER BY created_at DESC LIMIT 10;
```

---

## Configuration Summary

After completing all steps, you will have:

✅ GA4 Event Variable (Custom JavaScript)  
✅ User Email Variable (Data Layer)  
✅ HTTP Request Tag sending to CRM API  
✅ Event-based Trigger for all GA4 events  
✅ Tag published to production  

---

## Next Steps

1. ✅ Create variables in GTM (Step 2-3)
2. ✅ Create HTTP tag (Step 4)
3. ✅ Create trigger (Step 5-6)
4. ✅ Test in Preview mode (Step 7)
5. ✅ Verify API response (Step 8)
6. ✅ Test full flow (Step 9)
7. ✅ Publish to production (Step 10)

---

## Support

### Reference Documents
- **Full Configuration Guide**: GA4_EVENT_FEED_CONFIGURATION.md
- **CRM API Reference**: CRM_API_DOCUMENTATION.md
- **System Overview**: COMPREHENSIVE_README.md

### Getting Help
- Check GTM preview for event firing status
- Check server logs for API errors
- Verify endpoint URL matches exactly
- Ensure JSON is valid

---

**Status**: Ready to Implement  
**Time to Complete**: 45-65 minutes  
**Difficulty**: Medium  
**Next Action**: Follow Steps 1-10 above in GTM interface

**Last Updated**: May 17, 2026
