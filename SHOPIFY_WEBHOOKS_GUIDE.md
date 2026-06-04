# Shopify Webhooks Registration Guide

**Objective**: Connect Shopify to Pureleven CRM to automatically sync customer and order data

**Estimated Time**: 10-15 minutes

---

## Prerequisites

- ✅ Shopify store admin access
- ✅ CRM API live at `https://track.pureleven.com/api/crm/webhooks/shopify`
- ✅ Store domain: rwxtic-gz.myshopify.com (Pureleven store)

---

## Step-by-Step Registration

### Option A: Manual Registration (Recommended)

#### Step 1: Access Shopify Admin Settings
1. Log in to Shopify Admin: https://admin.shopify.com
2. Navigate to **Settings** (bottom left of sidebar)
3. Go to **Notifications** (in the settings menu)

#### Step 2: Create First Webhook (customers/create)
1. Scroll down to find **Webhooks** section
2. Click **Create webhook** (or "Add webhook")
3. Fill in the form:
   - **Event**: Select `Customers` → `Customer created`
   - **Webhook URL**: `https://track.pureleven.com/api/crm/webhooks/shopify`
   - **Webhook API version**: Select latest stable (e.g., 2025-01)
   - **Format**: Keep as `JSON`
4. Click **Save webhook**
5. You should see a success message

#### Step 3: Repeat for Remaining 4 Webhooks

Register these 5 webhooks (same URL for all, different events):

| Event | Location in Settings |
|-------|-------------------|
| **Customer created** | Customers → Created |
| **Customer updated** | Customers → Updated |
| **Order created** | Orders → Created |
| **Order updated (paid)** | Orders → Updated |
| **Checkout abandoned** | Checkouts → Abandoned |

**Steps for each**:
1. Click **Create webhook** again
2. Select the event from the list
3. Paste same URL: `https://track.pureleven.com/api/crm/webhooks/shopify`
4. Click **Save webhook**

#### Step 4: Verify Registrations
1. After all 5 are registered, scroll through the **Webhooks** section
2. You should see 5 entries, all pointing to `https://track.pureleven.com/api/crm/webhooks/shopify`
3. Status should show as "Active" (green checkmark)

---

### Option B: Using Shopify CLI (Advanced)

If you have Shopify CLI installed:

```bash
# Authenticate to store
shopify auth login --store rwxtic-gz.myshopify.com

# Create each webhook
shopify webhook trigger customers/create \
  --address https://track.pureleven.com/api/crm/webhooks/shopify

shopify webhook trigger customers/update \
  --address https://track.pureleven.com/api/crm/webhooks/shopify

shopify webhook trigger orders/create \
  --address https://track.pureleven.com/api/crm/webhooks/shopify

shopify webhook trigger orders/paid \
  --address https://track.pureleven.com/api/crm/webhooks/shopify

shopify webhook trigger abandoned_checkouts/create \
  --address https://track.pureleven.com/api/crm/webhooks/shopify

# Verify
shopify webhook list
```

---

## Testing the Integration

### Test 1: Verify Webhook Configuration
```bash
# Check webhook delivery logs in Shopify Admin
# Settings → Notifications → Scroll to Webhooks
# Click on each webhook to see delivery history
```

### Test 2: Trigger a Webhook Event
1. **For customers/create**: Add a new customer manually in Shopify Admin
   - Go to Customers → Add customer
   - Fill in email and name
   - Click **Save**
   - Watch for webhook delivery in settings

2. **For customers/update**: Edit an existing customer
   - Go to Customers → Select any customer
   - Change any field (e.g., phone number)
   - Click **Save**
   - Watch for webhook delivery

3. **For orders/create**: Place a test order
   - Go to your Pureleven store
   - Add product to cart
   - Complete checkout
   - Watch for webhooks in Shopify settings

4. **For orders/paid**: Manually mark order as paid
   - Go to Orders → Select recent order
   - Click "Capture payment"
   - Or use Shopify test payment: `4242 4242 4242 4242`

### Test 3: Verify Data in CRM Dashboard
After triggering events:
1. Open dashboard: https://ai.pureleven.com/static/dashboard.html
2. Click **Customers** tab
3. Look for new customer/order data appearing
4. Check timestamp matches your test action

---

## Expected Webhook Payloads

### Customer Created
```json
{
  "id": 123456789,
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+919876543210",
  "created_at": "2025-05-14T10:30:00Z",
  "tags": ["loyal", "wholesale"],
  "state": "enabled"
}
```

### Order Created
```json
{
  "id": 987654321,
  "email": "john@example.com",
  "created_at": "2025-05-14T10:35:00Z",
  "total_price": "5000.00",
  "currency": "INR",
  "financial_status": "pending",
  "line_items": [
    {
      "id": 1,
      "product_id": 123,
      "title": "Black Pepper 100g",
      "quantity": 2,
      "price": "2500.00"
    }
  ],
  "shipping_address": {
    "address1": "123 Main St",
    "city": "Bangalore",
    "province": "KA",
    "zip": "560001",
    "country": "IN"
  }
}
```

---

## Troubleshooting

### Webhook Not Showing as Active
**Issue**: Webhook shows "Inactive" or "Queued"
**Cause**: Shopify testing the endpoint
**Solution**: 
1. Wait 5-10 minutes
2. Shopify will retry automatically
3. If still failing, check:
   - URL is correct: `https://track.pureleven.com/api/crm/webhooks/shopify`
   - Domain is reachable: `curl https://track.pureleven.com/api/crm/health`
   - No typos in domain

### Webhook Delivery Failed
**Issue**: "Failed delivery" showing in webhook history
**Root Cause**: One of several possible issues
**Debugging Steps**:
1. Click on failed webhook entry
2. View the response/error details
3. Check server logs:
   ```bash
   ssh root@192.46.213.140
   docker logs pureleven-ai-engine | tail -50
   ```
4. Look for error messages related to the CRM route

### No Data Appearing in Dashboard
**Issue**: Webhooks are marked active, but no customers showing in dashboard
**Cause**: Events delivered but not processed by CRM
**Solution**:
1. Verify webhook delivery logs show "Successful"
2. Manually test API:
   ```bash
   curl -s https://ai.pureleven.com/api/crm/customers
   ```
3. If empty, check database:
   ```bash
   ssh root@192.46.213.140
   docker exec pureleven-postgres psql -U pureleven -d pureleven -c "SELECT COUNT(*) FROM crm_customers;"
   ```

---

## What Happens After Registration

### Data Flow
```
Shopify Event (customer created)
         ↓
Shopify Webhook Service
         ↓
POST https://track.pureleven.com/api/crm/webhooks/shopify
         ↓
FastAPI: POST /api/crm/webhooks/shopify handler
         ↓
Validation + Data Extraction
         ↓
INSERT into PostgreSQL crm_customers table
         ↓
Dashboard reads from crm_customers table
         ↓
Customer appears in UI instantly
```

### Automatic Data Population
Once webhooks are registered, these events trigger automatic CRM updates:

1. **New Customer Added**
   - Email, name, phone → crm_customers
   - Created_at timestamp recorded
   - Ready for campaigns

2. **Customer Updated**
   - Changes to name, phone → crm_customers
   - Updated_at timestamp updated
   - Metadata preserved

3. **Order Created**
   - Order ID, total, items → crm_orders
   - Customer linked via email/ID
   - Order count incremented
   - Total spent updated

4. **Order Paid**
   - Order status updated to "paid"
   - Revenue confirmed
   - Customer metrics recalculated

5. **Checkout Abandoned**
   - Recorded as recovery opportunity
   - Email available for follow-up
   - ROI tracking for email campaigns

---

## Next Steps After Registration

Once all 5 webhooks are active and delivering:

1. **Verify Data Flow**: Place 2-3 test orders → Dashboard shows customers
2. **Configure GA4 Events** (optional): Route page_view, add_to_cart, purchase to CRM
3. **Set Up Google Ads Conversion Feed** (optional): Import offline conversions
4. **Launch Email Campaign**: Use CRM segments to target high-value customers
5. **Monitor Metrics**: Track cohort performance, LTV, retention rates

---

## FAQs

**Q: Can I modify webhook URLs later?**  
A: Yes. Go to Settings → Notifications → Webhooks → Click webhook → Edit URL → Save

**Q: What if I delete a webhook by mistake?**  
A: Just create it again following the same steps. No data is lost.

**Q: How far back does Shopify send historical data?**  
A: Webhooks only send new events going forward. Historical orders need separate API import.

**Q: Are there webhook delivery retries?**  
A: Yes, Shopify retries failed webhooks for 48 hours with exponential backoff.

**Q: Can I test webhook payloads without real events?**  
A: Yes, use Shopify test tools or manually trigger via Shopify Admin.

**Q: Is there a limit on number of webhooks?**  
A: No, you can have unlimited webhooks pointing to same URL.

---

## Support Contacts

**CRM Backend Issues**: Check FastAPI logs
```bash
ssh root@192.46.213.140
docker logs pureleven-ai-engine
```

**Database Issues**: Check PostgreSQL directly
```bash
docker exec pureleven-postgres psql -U pureleven -d pureleven
```

**Shopify Questions**: Shopify Help Center → Webhooks docs

---

## Webhook Reference

**Endpoint**: `https://track.pureleven.com/api/crm/webhooks/shopify`  
**Method**: POST  
**Content-Type**: application/json  
**Headers**: Shopify-Hmac-SHA256 (for verification)  
**Retry Policy**: 48 hours, exponential backoff  
**Timeout**: 30 seconds  

---

**Status**: Ready to implement  
**Time to complete**: 10-15 minutes  
**Difficulty**: Easy (no coding required)  
**Value**: Unlocks real-time CRM functionality
