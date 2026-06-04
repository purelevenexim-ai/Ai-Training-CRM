# Pureleven CRM API Documentation
**Live at**: `https://track.pureleven.com/api/crm/`  
**Server**: 192.46.213.140 (track.pureleven.com)  
**Database**: PostgreSQL (pureleven_db)  
**Status**: ✅ LIVE (2026-05-17)

---

## 📊 API Overview

The Pureleven CRM unifies customer data from **5 sources**:
- 🛒 **Shopify** - customers, orders, checkouts via webhooks
- 📊 **GA4** - product views, purchases, conversions
- 🎯 **Google Ads** - conversion confirmations
- 📱 **Meta Ads** - conversion confirmations  
- 📧 **Email/SMS** - campaign engagement

### Database Tables Created
```
✅ crm_customers        - Unified customer records
✅ crm_orders          - Order history
✅ crm_events          - All interactions (views, clicks, opens)
✅ crm_segments        - Customer audiences/segments
✅ crm_conversion_feeds - Incoming conversions for matching
```

---

## 🔌 API Endpoints

### 1. **Shopify Webhooks** (Incoming)
**Endpoint**: `POST /api/crm/webhooks/shopify`  
**Authentication**: Shopify webhook signature (X-Shopify-HMAC-SHA256 header)

**Supported Topics**:
- `customers/create` - New customer
- `customers/update` - Customer profile update
- `orders/create` - Order placed
- `orders/paid` - Payment confirmed
- `orders/fulfilled` - Order shipped
- `abandoned_checkouts/create` - Cart abandoned

**Example Payload** (from Shopify Admin):
```json
{
  "event_type": "customers/create",
  "data": {
    "id": 123456789,
    "email": "customer@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+911234567890",
    "created_at": "2026-05-17T10:30:00Z"
  }
}
```

**Response**:
```json
{
  "status": "received",
  "topic": "customers/create"
}
```

---

### 2. **GA4 Events** (Incoming)
**Endpoint**: `POST /api/crm/events/ga4`  
**Authentication**: Bearer token (set via GTM Server)

**Event Types**:
- `page_view` - User visited page
- `view_item` - User viewed product
- `add_to_cart` - Item added to cart
- `begin_checkout` - Checkout started
- `purchase` - Order completed

**Example Payload**:
```json
{
  "customer_id": "shopify_12345",
  "email": "customer@example.com",
  "event_type": "purchase",
  "source": "ga4",
  "event_data": {
    "transaction_id": "order_67890",
    "value": 5000,
    "currency": "INR",
    "items": [
      {
        "item_id": "product_123",
        "item_name": "Black Pepper 200GM",
        "price": 849,
        "quantity": 1,
        "item_category": "Spices > Pepper"
      }
    ]
  },
  "timestamp": "2026-05-17T10:30:00Z"
}
```

**Response**:
```json
{
  "status": "event_recorded",
  "event_type": "purchase"
}
```

---

### 3. **Google Ads Conversions** (Incoming)
**Endpoint**: `POST /api/crm/events/google-ads`  
**Authentication**: Bearer token

**Payload**:
```json
{
  "source": "google_ads",
  "external_id": "gads_conv_xyz123",
  "email": "customer@example.com",
  "conversion_type": "purchase",
  "conversion_value": 5000,
  "currency": "INR",
  "campaign_id": "campaign_123",
  "campaign_name": "Spring Campaign",
  "gclid": "CjwKCAjwx...",
  "timestamp": "2026-05-17T10:30:00Z"
}
```

**Response**:
```json
{
  "status": "conversion_recorded",
  "source": "google_ads"
}
```

---

### 4. **Meta Ads Conversions** (Incoming)
**Endpoint**: `POST /api/crm/events/meta`  
**Authentication**: Bearer token

**Payload**:
```json
{
  "source": "meta",
  "external_id": "meta_event_abc123",
  "email": "customer@example.com",
  "conversion_type": "Purchase",
  "conversion_value": 5000,
  "currency": "INR",
  "campaign_id": "campaign_meta_456",
  "fbp": "fb_pixel_id_123",
  "timestamp": "2026-05-17T10:30:00Z"
}
```

**Response**:
```json
{
  "status": "conversion_recorded",
  "source": "meta"
}
```

---

### 5. **Get Customer** (Outgoing)
**Endpoint**: `GET /api/crm/customers/{email}`  
**Authentication**: Bearer token

**Response**:
```json
{
  "id": "uuid-string",
  "shopify_customer_id": "123456789",
  "email": "customer@example.com",
  "phone": "+911234567890",
  "first_name": "John",
  "last_name": "Doe",
  "total_spent": 5000,
  "orders_count": 1,
  "last_order_date": "2026-05-17T10:30:00Z",
  "created_at": "2026-05-17T08:00:00Z"
}
```

---

### 6. **List Customers** (Outgoing)
**Endpoint**: `GET /api/crm/customers?skip=0&limit=100&min_orders=1&min_spent=1000`  
**Authentication**: Bearer token

**Query Parameters**:
- `skip` - Offset for pagination (default: 0)
- `limit` - Max results (default: 100)
- `min_orders` - Filter: minimum order count (default: 0)
- `min_spent` - Filter: minimum total spent (default: 0)

**Response**:
```json
{
  "total": 150,
  "skip": 0,
  "limit": 100,
  "customers": [
    { ... customer 1 ... },
    { ... customer 2 ... }
  ]
}
```

---

### 7. **Create Segment** (Outgoing)
**Endpoint**: `POST /api/crm/segments`  
**Authentication**: Bearer token

**Payload**:
```json
{
  "name": "High-Value Customers",
  "description": "Customers who spent over ₹5000",
  "rule_set": {
    "min_total_spent": 5000,
    "min_orders": 1
  }
}
```

**Response**:
```json
{
  "id": "segment-uuid",
  "name": "High-Value Customers",
  "description": "Customers who spent over ₹5000",
  "customer_count": 150,
  "is_active": true,
  "created_at": "2026-05-17T10:30:00Z"
}
```

---

## 🔗 Setup Instructions

### Step 1: Register Shopify Webhooks

Go to **Shopify Admin > Settings > Notifications > Webhooks**

Register these webhooks to point to your CRM:

```
Event: customers/create
URL: https://track.pureleven.com/api/crm/webhooks/shopify
Topics: customers/create

Event: customers/update  
URL: https://track.pureleven.com/api/crm/webhooks/shopify
Topics: customers/update

Event: orders/create
URL: https://track.pureleven.com/api/crm/webhooks/shopify
Topics: orders/create

Event: orders/paid
URL: https://track.pureleven.com/api/crm/webhooks/shopify
Topics: orders/paid

Event: abandoned_checkouts/create
URL: https://track.pureleven.com/api/crm/webhooks/shopify
Topics: abandoned_checkouts/create
```

**Verification**: After registering, place a test order on your store and check if it appears in:
```bash
curl -s https://track.pureleven.com/api/crm/customers/your-email@example.com
```

---

### Step 2: Configure GA4 Event Feed

Update your GTM Server container (GTM-TFHBWPLM) to forward GA4 events:

1. In GTM, create a new custom webhook/API tag:
   - **Name**: "GA4 to CRM"
   - **Type**: Webhook/HTTP Request
   - **URL**: `https://track.pureleven.com/api/crm/events/ga4`
   - **Method**: POST
   - **Headers**: 
     - `Content-Type: application/json`
     - `Authorization: Bearer YOUR_API_KEY`

2. Trigger on GA4 events:
   - `page_view`
   - `purchase`
   - `add_to_cart`
   - `view_item`

---

### Step 3: Configure Google Ads Conversion Feed

1. In Google Ads, enable **Conversion Tracking**
2. Set up an **Offline Conversion Source**:
   - Go to **Tools > Conversions > Offline conversions**
   - Create new source
   - Provide your CRM API endpoint: `https://track.pureleven.com/api/crm/events/google-ads`

---

### Step 4: Configure Meta Ads Conversion Feed

1. In Meta Business Manager, go to **Events Manager**
2. Create webhook for your Pixel ID (609256704464862)
3. Point to: `https://track.pureleven.com/api/crm/events/meta`

---

## 🧪 Testing

### Test Shopify Webhook
```bash
curl -X POST https://track.pureleven.com/api/crm/webhooks/shopify \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Topic: customers/create" \
  -d '{
    "id": 12345,
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "Customer",
    "created_at": "2026-05-17T10:30:00Z"
  }'
```

### Test GA4 Event
```bash
curl -X POST https://track.pureleven.com/api/crm/events/ga4 \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "event_type": "purchase",
    "source": "ga4",
    "event_data": {
      "transaction_id": "order_123",
      "value": 5000,
      "currency": "INR"
    },
    "timestamp": "2026-05-17T10:30:00Z"
  }'
```

### Test Customer Retrieval
```bash
curl -s https://track.pureleven.com/api/crm/customers/test@example.com
```

### Test CRM Health
```bash
curl -s https://track.pureleven.com/api/crm/health
# Response: {"status":"healthy","module":"crm"}
```

---

## 📊 Database Schema

### crm_customers
```sql
id (UUID) - Primary key
shopify_customer_id (String) - Unique
email (String) - Unique, indexed
phone (String)
first_name, last_name
total_spent (Float)
orders_count (Integer)
last_order_date (Timestamp)
email_subscribed, sms_subscribed (Boolean)
metadata (JSONB) - Custom fields
created_at, updated_at (Timestamp)
```

### crm_orders
```sql
id (UUID) - Primary key
shopify_order_id (String) - Unique
customer_id (FK to crm_customers)
order_date (Timestamp)
total_amount (Float)
items (JSONB) - Array of {item_id, name, price, quantity, category}
shipping_address (JSONB)
utm_source, utm_medium, utm_campaign (String)
status (String)
created_at, updated_at (Timestamp)
```

### crm_events
```sql
id (UUID) - Primary key
customer_id (FK to crm_customers)
email (String) - Indexed
event_type (String) - Indexed (page_view, purchase, email_open, etc.)
source (String) - Indexed (shopify, ga4, google_ads, meta, email)
event_data (JSONB)
timestamp (Timestamp) - Indexed
created_at (Timestamp) - Indexed
```

### crm_conversion_feeds
```sql
id (UUID) - Primary key
source (String) - Indexed (ga4, google_ads, meta)
external_id (String) - Indexed, from source platform
email, phone, shopify_customer_id (String) - Indexed for matching
conversion_type (String)
conversion_value (Float)
campaign_id, campaign_name (String)
is_matched (Boolean)
matched_customer_id (FK)
timestamp, created_at (Timestamp)
```

---

## 🚀 Next Steps

- [ ] Register all Shopify webhooks (Step 1)
- [ ] Configure GA4 event forwarding (Step 2)
- [ ] Set up Google Ads conversion feed (Step 3)
- [ ] Configure Meta Ads conversion feed (Step 4)
- [ ] Run test payloads to verify data flow
- [ ] Build customer dashboard UI (displays customers, segments, events)
- [ ] Create email/SMS campaign tracking module

---

## 📝 Logs & Monitoring

**Check API logs**:
```bash
ssh root@192.46.213.140
docker logs pureleven-ai-engine | grep crm
```

**Check database queries**:
```bash
docker exec pureleven-postgres psql -U pureleven -d pureleven
SELECT COUNT(*) FROM crm_customers;
SELECT COUNT(*) FROM crm_orders;
SELECT COUNT(*) FROM crm_events;
```

**Monitor webhook delivery**:
```bash
docker exec pureleven-ai-engine tail -f /app/crm_webhooks.log
```

---

## 🔐 Security Notes

- All endpoints require HTTPS
- API endpoints validate Shopify webhook signatures
- Google Ads & Meta conversions should include campaign IDs for attribution
- Customer data is PII - implement rate limiting and access controls
- Database uses SHA-256 password with PostgreSQL SSL

---

## 💬 Support

For issues or questions about the CRM API:
1. Check server logs: `docker logs pureleven-ai-engine`
2. Verify database connectivity: `docker exec pureleven-postgres psql -U pureleven -d pureleven -c "SELECT version()"`
3. Test endpoint directly with curl

**API Status**: ✅ LIVE at https://track.pureleven.com/api/crm/
