# Phase 3: CRM Backbone Implementation Plan
**Pureleven Custom CRM at prod.pureleven.com**  
**Status**: Architecture & Planning (2026-05-17)

---

## 📊 CRM Overview

The Pureleven CRM will unify customer data across:
- **Shopify**: Customer profiles, orders, shipping data
- **GA4**: Product views, search behavior, conversion events
- **Google Ads**: Conversion confirmations, campaign attribution
- **Meta Ads**: Conversion confirmations, campaign attribution
- **Email/SMS**: Campaign engagement tracking

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│          PURELEVEN CRM (prod.pureleven.com)         │
│  - Customer Data Hub                                │
│  - Event Processing Pipeline                        │
│  - Customer Unification Engine                       │
│  - Segmentation & Audience Manager                   │
└──────┬──────────────┬──────────────┬────────────────┘
       │              │              │
   ┌───▼───┐      ┌───▼───┐     ┌───▼────┐
   │ API   │      │ Webhook│    │ Sync   │
   │Endpoints│    │Listeners│   │Service │
   └───┬───┘      └───┬───┘     └───┬────┘
       │              │             │
       │         ┌────▼─────┐       │
       │         │  Queue   │       │
       │         │(Optional)│       │
       │         └──────────┘       │
       │                            │
       ├────────────────────────────┼─────────────────┐
       │                            │                 │
   ┌───▼───────┐  ┌──────────┐  ┌──▼──┐  ┌─────────┐│
   │ Shopify   │  │   GA4    │  │Ads  │  │   Meta  ││
   │(webhooks) │  │(GTM feed)│  │(API)│  │  (API)  ││
   └───────────┘  └──────────┘  └─────┘  └─────────┘│
                                                      │
                        ┌───────────────────────────┬─┘
                        │
                   ┌────▼──────┐
                   │ PostgreSQL │
                   │  Database  │
                   └────┬───────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   ┌────▼────┐  ┌──────▼──────┐  ┌─────▼──────┐
   │Customers│  │   Orders    │  │  Events    │
   │  Table  │  │    Table    │  │   Table    │
   └────┬────┘  └──────┬──────┘  └─────┬──────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
            ┌──────────▼──────────┐
            │  Segmentation &     │
            │  Audience Builder   │
            └─────────────────────┘
```

---

## 📡 Data Flows

### 1. **Shopify Webhook Feed** (Push)
**Endpoint**: `POST /api/crm/webhooks/shopify`

**Events to capture**:
- `customers/create` → New customer record
- `customers/update` → Customer profile changes
- `orders/create` → New order
- `orders/paid` → Payment confirmed
- `orders/fulfilled` → Shipment confirmation
- `abandoned_checkouts/create` → Cart abandonment

**Data Payload Schema**:
```json
{
  "event_type": "customers/create",
  "source": "shopify",
  "timestamp": 1715856000000,
  "data": {
    "customer_id": "12345",
    "email": "customer@example.com",
    "first_name": "Name",
    "last_name": "Customer",
    "phone": "+91xxxxxxxxxx",
    "default_address": {
      "address1": "",
      "address2": "",
      "city": "",
      "province": "",
      "zip": "",
      "country": "IN"
    },
    "total_spent": 5000,
    "orders_count": 3,
    "tags": []
  }
}
```

---

### 2. **GA4 Events Feed** (Pull via GTM Server)
**Endpoint**: `POST /api/crm/events/ga4`

**Events to capture**:
- `page_view` → Product interest tracking
- `view_item` → Specific product viewed
- `add_to_cart` → Cart addition
- `begin_checkout` → Checkout initiated
- `purchase` → Order confirmed

**Data Payload Schema**:
```json
{
  "event_type": "purchase",
  "source": "ga4",
  "timestamp": 1715856000000,
  "customer_email": "customer@example.com",
  "customer_id": "shopify_customer_id",
  "data": {
    "event_id": "purchase_20260517_001",
    "transaction_id": "shopify_order_12345",
    "value": 5000,
    "currency": "INR",
    "items": [
      {
        "item_id": "product_9906763989285",
        "item_name": "Black Pepper 200GM",
        "price": 849,
        "quantity": 1,
        "item_category": "Spices > Pepper"
      }
    ],
    "session_id": "ga4_session_xyz"
  }
}
```

---

### 3. **Google Ads Conversion Feed** (Pull via Conversion API)
**Endpoint**: `POST /api/crm/events/google-ads`

**Events to capture**:
- Conversion confirmations linked to customer email
- Campaign attribution data

**Data Payload Schema**:
```json
{
  "event_type": "conversion",
  "source": "google_ads",
  "timestamp": 1715856000000,
  "customer_email": "customer@example.com",
  "data": {
    "conversion_id": "gads_conversion_xyz",
    "conversion_action": "purchase",
    "conversion_value": 5000,
    "currency": "INR",
    "campaign_id": "campaign_123",
    "campaign_name": "Spring Campaign",
    "gclid": "CjwKCAjwx...",
    "conversion_date_time": "2026-05-17T10:30:00Z"
  }
}
```

---

### 4. **Meta Conversions API Feed** (Pull via Meta Events Manager)
**Endpoint**: `POST /api/crm/events/meta`

**Events to capture**:
- Conversion confirmations linked to customer email/phone
- Campaign attribution data

**Data Payload Schema**:
```json
{
  "event_type": "conversion",
  "source": "meta",
  "timestamp": 1715856000000,
  "customer_email": "customer@example.com",
  "data": {
    "event_id": "meta_event_abc123",
    "event_name": "Purchase",
    "event_source_url": "https://pureleven.com/checkout/success",
    "event_source_type": "website",
    "value": 5000,
    "currency": "INR",
    "campaign_id": "campaign_meta_456",
    "ad_id": "ad_789",
    "fbp": "fb_pixel_id_123",
    "conversion_timestamp": "2026-05-17T10:30:00Z"
  }
}
```

---

### 5. **Email/SMS Campaign Tracking** (Pull from Email Platform)
**Endpoint**: `POST /api/crm/events/email-engagement`

**Events to capture** (from Klaviyo, SendGrid, or custom):
- `email_sent` → Email delivered
- `email_opened` → Customer opened email
- `email_clicked` → Customer clicked link
- `email_unsubscribed` → Unsubscribe event

**Data Payload Schema**:
```json
{
  "event_type": "email_opened",
  "source": "email_platform",
  "timestamp": 1715856000000,
  "customer_email": "customer@example.com",
  "data": {
    "campaign_id": "email_campaign_001",
    "campaign_name": "May Newsletter",
    "message_id": "msg_123",
    "event_timestamp": "2026-05-17T10:45:00Z"
  }
}
```

---

## 🔧 Implementation Phases

### Phase 3a: **Data Architecture & API Foundation** (2-3 days)
- [x] Design data schema
- [ ] Set up PostgreSQL database
- [ ] Create API endpoint stubs
- [ ] Document field mapping

### Phase 3b: **Shopify Integration** (2-3 days)
- [ ] Register webhook subscriptions in Shopify Admin
- [ ] Build webhook handler `/api/crm/webhooks/shopify`
- [ ] Implement customer record creation/update
- [ ] Test with real Shopify events

### Phase 3c: **GA4 Event Integration** (2-3 days)
- [ ] Configure GTM Server container to forward events to `/api/crm/events/ga4`
- [ ] Build event processor
- [ ] Link GA4 customer email to Shopify customer ID
- [ ] Test with real product/purchase events

### Phase 3d: **Google Ads & Meta Ads Integration** (2-3 days)
- [ ] Build API endpoint for Google Ads conversion import
- [ ] Build API endpoint for Meta Ads conversion import
- [ ] Implement conversion attribution logic
- [ ] Test with campaign data

### Phase 3e: **Customer Unification Engine** (2-3 days)
- [ ] Implement customer ID matching (email, phone, Shopify ID)
- [ ] Build deduplication logic
- [ ] Create unified customer profile queries
- [ ] Handle multi-account/multi-email cases

### Phase 3f: **Segmentation & Audience Builder** (3-4 days)
- [ ] Design segmentation rule engine
- [ ] Build audience creation endpoints
- [ ] Implement RFM (Recency-Frequency-Monetary) scoring
- [ ] Create campaign-ready audience exports

---

## 📋 Database Schema (PostgreSQL)

### `customers` Table
```sql
CREATE TABLE customers (
  id UUID PRIMARY KEY,
  shopify_customer_id BIGINT UNIQUE,
  email VARCHAR(255) UNIQUE,
  phone VARCHAR(20),
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  last_order_date TIMESTAMP,
  total_spent DECIMAL(10, 2),
  orders_count INT,
  tags JSONB,
  metadata JSONB
);
```

### `orders` Table
```sql
CREATE TABLE orders (
  id UUID PRIMARY KEY,
  shopify_order_id BIGINT UNIQUE,
  customer_id UUID REFERENCES customers(id),
  email VARCHAR(255),
  order_date TIMESTAMP,
  total_amount DECIMAL(10, 2),
  currency VARCHAR(3),
  status VARCHAR(50),
  items JSONB,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### `events` Table
```sql
CREATE TABLE events (
  id UUID PRIMARY KEY,
  customer_id UUID REFERENCES customers(id),
  event_type VARCHAR(100),
  source VARCHAR(50), -- 'shopify', 'ga4', 'google_ads', 'meta', 'email'
  event_data JSONB,
  timestamp TIMESTAMP,
  created_at TIMESTAMP,
  
  INDEX idx_customer_id (customer_id),
  INDEX idx_event_type (event_type),
  INDEX idx_source (source),
  INDEX idx_timestamp (timestamp)
);
```

### `segments` Table
```sql
CREATE TABLE segments (
  id UUID PRIMARY KEY,
  name VARCHAR(255),
  description TEXT,
  rule_set JSONB, -- Segmentation rules
  customer_count INT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

---

## 🔗 Integration Checklist

### Shopify Setup
- [ ] Go to `Admin > Settings > Notifications > Webhooks`
- [ ] Register webhook subscriptions:
  - [ ] `customers/create` → `prod.pureleven.com/api/crm/webhooks/shopify`
  - [ ] `customers/update` → same endpoint
  - [ ] `orders/create` → same endpoint
  - [ ] `orders/paid` → same endpoint
  - [ ] `orders/fulfilled` → same endpoint
  - [ ] `abandoned_checkouts/create` → same endpoint
- [ ] Test webhook delivery

### GTM Server Configuration
- [ ] Update GTM Server container (GTM-TFHBWPLM) to forward events:
  ```
  transport_url: https://track.pureleven.com → prod.pureleven.com/api/crm/events/ga4
  ```
- [ ] Add GA4 event tags for:
  - `page_view`
  - `view_item`
  - `add_to_cart`
  - `begin_checkout`
  - `purchase`

### Google Ads Integration
- [ ] Get Google Ads API credentials
- [ ] Create custom conversion import endpoint
- [ ] Set up daily sync job

### Meta Integration
- [ ] Use existing pixel ID: `609256704464862`
- [ ] Get Meta API access (already have token)
- [ ] Set up conversion API endpoint

---

## 🎯 Success Metrics

- ✅ 100% of Shopify customers synced to CRM within 24 hours
- ✅ 95%+ of GA4 purchase events matched to Shopify customer
- ✅ Google Ads conversions attributed to correct customer
- ✅ Meta conversions attributed to correct customer
- ✅ Email engagement tracked for all campaigns
- ✅ Customer segmentation accuracy: 99%+
- ✅ API response time: <500ms for most endpoints
- ✅ Zero data loss: 100% event delivery rate

---

## 📅 Timeline

**Week 1 (May 17-23)**:
- Mon-Tue: Database schema & API setup
- Wed-Thu: Shopify webhook integration
- Fri: GA4 event feed

**Week 2 (May 24-30)**:
- Mon-Tue: Google Ads & Meta integration
- Wed-Thu: Customer unification engine
- Fri: Initial testing & QA

**Week 3 (May 31 - Jun 6)**:
- Mon-Tue: Segmentation & audience builder
- Wed-Thu: Performance optimization
- Fri: Production deployment & monitoring

---

## 🚀 Next Immediate Step

**Build Phase 3a**: Database schema + API foundation
- Create PostgreSQL database
- Define customer/order/event/segment tables
- Build API endpoint stubs in Node.js/Express
- Document all field mappings

Ready to start? ✅
