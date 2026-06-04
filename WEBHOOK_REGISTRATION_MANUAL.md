# Shopify Webhooks - Manual Registration Guide

**Status**: Ready for manual registration  
**Date**: May 17, 2026  
**Endpoint**: https://track.pureleven.com/api/crm/webhooks/shopify  
**Store**: Organic Pure Leven (rwxtic-gz.myshopify.com)

---

## Quick Reference

| Webhook Event | Webhook Topic | Location in Admin |
|--------------|---------------|------------------|
| **1. Customer Created** | customers/create | Settings → Notifications → Webhooks |
| **2. Customer Updated** | customers/update | Settings → Notifications → Webhooks |
| **3. Order Created** | orders/create | Settings → Notifications → Webhooks |
| **4. Order Paid** | orders/paid | Settings → Notifications → Webhooks |
| **5. Checkout Abandoned** | checkouts/abandon | Settings → Notifications → Webhooks |

**All 5 webhooks point to the same endpoint**: `https://track.pureleven.com/api/crm/webhooks/shopify`

---

## Step-by-Step Manual Registration

### Step 1: Access Shopify Admin
1. Go to https://admin.shopify.com
2. Log in with your Shopify account (hello@pureleven.com)
3. Select the store: **Organic Pure Leven** (rwxtic-gz.myshopify.com)

### Step 2: Navigate to Webhooks Settings
1. In the left sidebar, click **Settings** (bottom option)
2. Click **Notifications** (in the settings menu)
3. Scroll down to the **Webhooks** section
4. Click **Create webhook** (or "Add webhook" button)

### Step 3: Register First Webhook - Customer Created

**Form Fields**:
- **Event**: Select from dropdown: `Customers` → `Customer created`
- **Webhook URL**: Paste exactly: `https://track.pureleven.com/api/crm/webhooks/shopify`
- **Webhook API version**: Select the latest (e.g., `2025-01` or `2026-04`)
- **Format**: Keep as `JSON` (default)

**Click**: Save webhook

**Expected Result**: Success message, webhook appears in the list

---

### Step 4: Register Second Webhook - Customer Updated

1. Click **Create webhook** again
2. **Event**: `Customers` → `Customer updated`
3. **Webhook URL**: `https://track.pureleven.com/api/crm/webhooks/shopify` (same)
4. **Webhook API version**: Same as above
5. **Format**: JSON
6. Click **Save webhook**

---

### Step 5: Register Third Webhook - Order Created

1. Click **Create webhook** again
2. **Event**: `Orders` → `Order created`
3. **Webhook URL**: `https://track.pureleven.com/api/crm/webhooks/shopify` (same)
4. **Webhook API version**: Same as above
5. **Format**: JSON
6. Click **Save webhook**

---

### Step 6: Register Fourth Webhook - Order Paid

1. Click **Create webhook** again
2. **Event**: `Orders` → `Order paid` (or `Order updated`)
3. **Webhook URL**: `https://track.pureleven.com/api/crm/webhooks/shopify` (same)
4. **Webhook API version**: Same as above
5. **Format**: JSON
6. Click **Save webhook**

---

### Step 7: Register Fifth Webhook - Checkout Abandoned

1. Click **Create webhook** again
2. **Event**: `Checkouts` → `Checkout abandoned`
3. **Webhook URL**: `https://track.pureleven.com/api/crm/webhooks/shopify` (same)
4. **Webhook API version**: Same as above
5. **Format**: JSON
6. Click **Save webhook**

---

### Step 8: Verify All Webhooks Registered

After registering all 5 webhooks:

1. Go back to **Settings** → **Notifications** → **Webhooks** section
2. You should see **5 entries** in the webhooks list
3. All should show status as **"Active"** (green checkmark)
4. All should point to: `https://track.pureleven.com/api/crm/webhooks/shopify`

**Expected Display**:
```
✓ Customer created → https://track.pureleven.com/api/crm/webhooks/shopify
✓ Customer updated → https://track.pureleven.com/api/crm/webhooks/shopify
✓ Order created → https://track.pureleven.com/api/crm/webhooks/shopify
✓ Order paid → https://track.pureleven.com/api/crm/webhooks/shopify
✓ Checkout abandoned → https://track.pureleven.com/api/crm/webhooks/shopify
```

---

## Testing the Integration

### Test 1: Verify Webhook Configuration
After registering all 5 webhooks:

1. In Shopify Admin, go to **Settings** → **Notifications**
2. Scroll to **Webhooks** section
3. Click on one of the webhooks
4. You should see a **"Recent deliveries"** section
5. (No deliveries yet - that's normal until we trigger an event)

### Test 2: Trigger a Webhook
To test that webhooks are actually working:

1. **Option A**: Place a test order on pureleven.com
   - Go to https://pureleven.com
   - Add a product to cart
   - Proceed to checkout
   - Complete the purchase
   - Check webhook logs for "Order created" delivery

2. **Option B**: Create a test customer in Shopify Admin
   - Go to **Customers** in Shopify Admin
   - Click **Add customer**
   - Fill in test customer details
   - Save
   - Check webhook logs for "Customer created" delivery

### Test 3: Monitor Webhook Deliveries
After triggering a webhook event:

1. Go to **Settings** → **Notifications** → **Webhooks**
2. Click on the webhook that should have fired (e.g., "Order created")
3. Look for **"Recent deliveries"** section
4. You should see an entry with:
   - **Status**: 200 (Success) - shown as green
   - **Timestamp**: Recent time
   - **Response**: Shows the API response

**Expected webhook response**:
```json
{
  "status": "received",
  "type": "shopify_webhook",
  "customer_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Test 4: Verify Data in CRM Dashboard
After a successful webhook delivery:

1. Open the CRM dashboard: https://ai.pureleven.com/static/dashboard.html
2. The customer from your test order should appear in the customer list
3. You should see:
   - Email address
   - First name / Last name
   - Phone number (if provided)
   - Order count updated
   - Total spent updated

---

## Troubleshooting

### Issue: Webhook Not Firing
**Symptoms**: Orders placed but webhook not showing in "Recent deliveries"

**Solutions**:
1. Verify webhook URL is exactly: `https://track.pureleven.com/api/crm/webhooks/shopify` (check for typos)
2. Verify webhook is marked as **"Active"** in Shopify Admin
3. Check that the API version selected exists
4. Verify the event type is correct for the webhook

### Issue: Webhook Showing Error Status (Not 200)
**Symptoms**: Webhook shows status code other than 200 (e.g., 404, 500)

**Solutions**:
1. **404 error**: The endpoint URL is wrong. Check for typos.
2. **500 error**: API server error. Check server logs at https://192.46.213.140:8000
3. **Connection refused**: Server not running. SSH to server and check Docker containers

### Issue: Webhook Fired But No Data in Dashboard
**Symptoms**: Webhook shows 200 status, but customer doesn't appear in dashboard

**Solutions**:
1. Refresh the dashboard: https://ai.pureleven.com/static/dashboard.html (Ctrl+R or Cmd+R)
2. Check that the customer has an email address (required field)
3. Check server logs for any data processing errors

### Issue: Event Not Appearing at All
**Symptoms**: Webhook not triggering even after placing order

**Solutions**:
1. Verify you're logged into the correct Shopify store
2. Verify the webhook event type matches what you're doing
   - If placing an order, use "Order created"
   - If creating a customer, use "Customer created"
3. Try placing another test order with different data
4. Check Shopify app permissions (webhooks might be disabled)

---

## API Endpoint Details

### Webhook Endpoint
```
URL: https://track.pureleven.com/api/crm/webhooks/shopify
Method: POST
Content-Type: application/json
Authentication: None (public endpoint)
```

### Webhook Payload Example (Customer Created)
```json
{
  "id": 123456789,
  "email": "customer@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+919876543210",
  "created_at": "2026-05-17T10:00:00Z",
  "updated_at": "2026-05-17T10:00:00Z"
}
```

### Expected API Response
```json
{
  "status": "received",
  "type": "shopify_webhook",
  "customer_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Verification Checklist

After completing all webhook registrations:

- [ ] 5 webhooks visible in Shopify Admin → Settings → Notifications → Webhooks
- [ ] All webhooks marked as "Active" (green status)
- [ ] All webhooks point to: `https://track.pureleven.com/api/crm/webhooks/shopify`
- [ ] API endpoint is responding to health check: https://ai.pureleven.com/api/crm/health
- [ ] Dashboard is loading: https://ai.pureleven.com/static/dashboard.html
- [ ] Test order placed on pureleven.com
- [ ] Webhook delivery visible in Shopify Admin (Status: 200)
- [ ] Test customer appears in CRM dashboard
- [ ] Customer data includes email, name, phone

---

## Performance Expectations

After webhooks are registered:

| Action | Expected Time | Notes |
|--------|---------------|-------|
| Place order on pureleven.com | N/A | User action |
| Webhook fired by Shopify | 1-5 seconds | Automatic |
| API processes webhook | 0.5-2 seconds | CRM backend |
| Customer appears in dashboard | 2-5 seconds | After page refresh |
| **Total delay** | **3-10 seconds** | From order placement to dashboard |

---

## Next Steps After Webhooks Are Active

Once all 5 webhooks are registered and working:

### Immediate (Today)
1. Monitor webhook deliveries in Shopify Admin
2. Place test orders to verify flow
3. Check CRM dashboard updates in real-time

### Optional - GA4 Integration (Next Week)
- Route GA4 events to `/api/crm/events/ga4` endpoint
- Update GTM container GTM-TFHBWPLM

### Optional - Google Ads Integration (Next Week)
- Create offline conversion source in Google Ads
- Point to `/api/crm/events/google-ads` endpoint

### Optional - Meta Integration (Next Week)
- Set up webhook in Meta Events Manager
- Point to `/api/crm/events/meta` endpoint

---

## Support

### Quick Commands for Testing

```bash
# Test API health
curl https://ai.pureleven.com/api/crm/health

# View API logs (from server)
ssh root@192.46.213.140
docker logs -f pureleven-ai-engine

# Test webhook endpoint manually
curl -X POST https://ai.pureleven.com/api/crm/webhooks/shopify \
  -H "Content-Type: application/json" \
  -d '{
    "id": 123,
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User"
  }'
```

### Questions?
- Check **SHOPIFY_WEBHOOKS_GUIDE.md** for original setup instructions
- Check **CRM_API_DOCUMENTATION.md** for detailed API reference
- Check **COMPREHENSIVE_README.md** for full system guide

---

## Summary

You now have:
- ✅ CRM API running and ready at `https://ai.pureleven.com/api/crm/`
- ✅ Dashboard deployed at `https://ai.pureleven.com/static/dashboard.html`
- ✅ Database ready with 6 tables
- ✅ Webhook endpoint ready to receive Shopify data
- ⏳ **5 webhooks need manual registration in Shopify Admin** (follow steps above)

**Time to complete registration**: 10-15 minutes

Once webhooks are registered, real-time customer data will flow automatically from Shopify to your CRM dashboard.

---

**Last Updated**: May 17, 2026  
**Status**: ✅ API Ready, ⏳ Webhooks Pending Registration
