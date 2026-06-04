# Pure Leven CRM System
## Google Ads Enhanced Conversions Integration
### Design Documentation

**Version:** 1.0  
**Date:** May 18, 2026  
**Application:** Pure Leven CRM API Engine  
**Purpose:** Enhanced conversion tracking for Google Ads  

---

## 1. Executive Summary

Pure Leven is an organic e-commerce platform specializing in premium spices and natural grocery products. The CRM API Engine integrates with Google Ads to provide real-time enhanced conversion tracking, enabling accurate attribution of customer purchases across multiple advertising channels.

This system captures conversion data from multiple sources (Shopify, Google Analytics 4, Facebook Conversions API) and syncs them to Google Ads for improved campaign optimization and audience targeting.

---

## 2. System Architecture

### 2.1 High-Level Overview

```
┌─────────────────────┐
│   Pure Leven Store  │
│   (Shopify)         │
└──────────┬──────────┘
           │
           ├──── Webhooks ────┐
           │                  │
           ├─── GA4 Events ───┤
           │                  │
           └─── CAPI Events ──┤
                              │
                         ┌────▼─────────────┐
                         │  CRM API Engine  │
                         │  (FastAPI)       │
                         └────┬─────────────┘
                              │
                ┌─────────────┼─────────────┬─────────────┐
                │             │             │             │
           ┌────▼────┐  ┌─────▼──────┐  ┌──▼─────┐  ┌───▼──────┐
           │ Google  │  │   Meta     │  │ Wabis  │  │Shiprocket│
           │  Ads    │  │   CAPI     │  │ (WhatsApp)│ (Fulfill)│
           │ (Conv)  │  │ (Tracking) │  │        │  │ (Track)  │
           └─────────┘  └────────────┘  └────────┘  └──────────┘
```

### 2.2 Core Components

#### CRM API Engine (FastAPI)
- **Language:** Python 3.11+
- **Framework:** FastAPI with APIRouter
- **Port:** 8000 (internal), exposed via reverse proxy at track.pureleven.com/api/crm/
- **Database:** PostgreSQL (customer, order, event tables)
- **Container:** Docker (pureleven-ai-engine)

#### API Routes
```
/api/crm/health                    - Health check
/api/crm/webhooks/delivery-status  - Shiprocket delivery tracking
/api/crm/webhooks/shiprocket       - Alternate Shiprocket endpoint
/api/crm/conversions/google-ads    - Google Ads conversion tracking
/api/crm/conversions/meta          - Meta CAPI conversion tracking
/api/crm/events/ga4                - GA4 custom events
/api/crm/webhooks/shopify/*        - Shopify webhook handlers
```

---

## 3. Google Ads Integration

### 3.1 Conversion Tracking Flow

**Trigger Points:**
1. Order created in Shopify
2. Order fulfilled via Shiprocket
3. Customer data from GA4
4. Offline conversion import

**Data Collection:**
- Customer email
- Order ID and amount
- Product category
- Transaction ID
- Timestamp
- Click ID (gclid) from GA4

**Google Ads API Usage:**
- **API Version:** Google Ads API v14+
- **Authentication:** OAuth 2.0 with Service Account
- **Endpoint:** googleads.googleapis.com/v14/
- **Operations:**
  - Create conversion uploads (OfflineUserDataJob)
  - Import conversion events
  - Track first-party data conversions
  - Audience list creation for remarketing

### 3.2 Authentication Details

**OAuth 2.0 Credentials:**
```
Client ID: <GOOGLE_ADS_CLIENT_ID>
Client Secret: [Secured]
Refresh Token: [Secured]
Developer Token: [Required]
Customer ID: 1491516326
Conversion Action ID: 6694318743
```

**Security:**
- All credentials stored in environment variables
- Refresh token automatically handled by client library
- SSL/TLS encryption for all API calls
- Request signing with HMAC for webhook validation

### 3.3 Conversion Data Structure

**Event Type:** Purchase Conversion
```json
{
  "order_id": "12345678",
  "customer_email": "user@example.com",
  "conversion_value": 2500.00,
  "currency_code": "INR",
  "conversion_date_time": "2026-05-18T10:30:00Z",
  "gclid": "[Google Click ID from analytics]",
  "conversion_action_id": "6694318743"
}
```

---

## 4. Integration Points

### 4.1 Shopify Integration
- **Webhook Events:** order/create, order/fulfill, order/update
- **Data:** Customer email, order total, items, fulfillment status
- **Frequency:** Real-time (webhook delivery)
- **Validation:** HMAC-SHA256 signature verification

### 4.2 Google Analytics 4 Integration
- **Events:** purchase, add_to_cart, view_item
- **Measurement Protocol:** Server-side event tracking
- **API Key:** GA4_MEASUREMENT_ID + GA4_API_SECRET
- **Purpose:** Attribution and click ID capture (gclid)

### 4.3 Shiprocket Integration
- **Events:** Delivery status updates
- **Webhook Token:** SHIPROCKET_WEBHOOK_TOKEN
- **Purpose:** Conversion fulfillment confirmation
- **Endpoint:** /api/crm/webhooks/delivery-status

### 4.4 Meta Conversions API
- **Pixel ID:** 609256704464862
- **Access Token:** [Secured]
- **Purpose:** Dual-channel conversion tracking
- **Events:** Purchase, add_to_cart, view_item

### 4.5 Wabis WhatsApp Integration
- **API Token:** [Secured]
- **Purpose:** Customer confirmation notifications
- **Trigger:** Order confirmation, delivery updates

---

## 5. Data Flow & Processing

### 5.1 Conversion Tracking Flow

```
1. Customer completes purchase on Shopify
   ↓
2. Shopify sends order/create webhook
   ↓
3. CRM API validates webhook signature
   ↓
4. Extract: email, order_id, amount, currency, items
   ↓
5. Query GA4 for gclid (click attribution)
   ↓
6. Create offline conversion event
   ↓
7. Batch upload to Google Ads API
   ↓
8. Confirm conversion in database
   ↓
9. Send confirmation to Meta CAPI (parallel)
   ↓
10. Log to GA4 Measurement Protocol
```

### 5.2 Fulfillment Tracking Flow

```
1. Order fulfilled in Shiprocket
   ↓
2. Shiprocket webhook → /api/crm/webhooks/delivery-status
   ↓
3. Validate HMAC signature using SHIPROCKET_WEBHOOK_TOKEN
   ↓
4. Update order status in database
   ↓
5. Send WhatsApp notification via Wabis (if enabled)
   ↓
6. Track as conversion in Google Ads (if not already tracked)
```

---

## 6. Database Schema

### PostgreSQL Tables

**customers**
```sql
id, email, phone, name, created_at, updated_at
```

**orders**
```sql
id, customer_id, order_id, total, currency, gclid, 
conversion_tracked, tracked_at, created_at
```

**events**
```sql
id, order_id, event_type, event_data, source, 
created_at, processed_at
```

**conversion_logs**
```sql
id, order_id, google_ads_status, meta_status, 
ga4_status, error_message, created_at
```

---

## 7. Security & Compliance

### 7.1 Authentication
- **OAuth 2.0** for Google Ads API
- **API Tokens** for third-party services
- **HMAC-SHA256** for webhook signature validation
- **SSL/TLS** for all external communications

### 7.2 Data Protection
- Environment variables for credential storage
- No hardcoded secrets in source code
- Request/response logging (excluding sensitive data)
- GDPR-compliant data retention policies

### 7.3 Rate Limiting
- Google Ads API: 5,000 requests/day per developer token
- Meta CAPI: 1,000 requests/day
- Implemented queue system for batch processing
- Retry logic with exponential backoff

### 7.4 Error Handling
- Comprehensive logging for all API interactions
- Failed conversions queued for retry
- Admin notifications for critical failures
- Graceful degradation if external APIs unavailable

---

## 8. Performance & Scalability

### 8.1 Throughput
- **Conversion Processing:** Up to 1,000 conversions/minute
- **Batch Size:** 100-1,000 events per Google Ads upload
- **Latency:** <5 seconds from purchase to API submission
- **Availability:** 99.5% uptime SLA

### 8.2 Optimization
- Asynchronous request processing with background tasks
- Database indexing on frequently queried fields (email, order_id)
- Connection pooling for database
- Redis caching for frequently accessed data (optional)

### 8.3 Monitoring
- Health check endpoint at /api/crm/health
- Application logging to CloudWatch/Stackdriver
- Performance metrics (response times, error rates)
- Alert thresholds for system failures

---

## 9. Testing & Validation

### 9.1 Unit Tests
- API endpoint validation
- Authentication token handling
- Data structure validation
- Signature verification

### 9.2 Integration Tests
- End-to-end conversion flow
- Third-party API mock testing
- Webhook signature validation
- Error recovery scenarios

### 9.3 Production Testing
- Staging environment with test Google Ads account
- Webhook payload validation with real platforms
- Performance load testing (1,000 req/min)
- Failure mode testing and recovery

---

## 10. Maintenance & Updates

### 10.1 Version Control
- Git-based source control
- Semantic versioning for releases
- Change logs and documentation updates

### 10.2 Dependency Management
- Regular security updates for Python packages
- Compatibility testing before updates
- Staging environment validation

### 10.3 API Updates
- Google Ads API version monitoring
- Planned deprecation handling
- Documentation updates for breaking changes

---

## 11. Support & Contact

**Development Team:** Pure Leven Engineering  
**API Support Email:** api-support@pureleven.com  
**Documentation:** Internal wiki  
**Incident Response:** On-call rotation with 30-minute SLA  

---

## Appendix A: Environment Variables

```
GADS_DEVELOPER_TOKEN=<required>
GADS_CUSTOMER_ID=1491516326
GADS_CONVERSION_ACTION_ID=6694318743
GADS_OAUTH_CLIENT_ID=<GOOGLE_ADS_CLIENT_ID>
GADS_OAUTH_CLIENT_SECRET=<secured>
GADS_OAUTH_REFRESH_TOKEN=<secured>

META_CAPI_PIXEL_ID=609256704464862
META_CAPI_ACCESS_TOKEN=<secured>

GA4_MEASUREMENT_ID=G-3FRSK7TEN2
GA4_API_SECRET=<secured>

SHIPROCKET_WEBHOOK_TOKEN=<secured>
WABIS_API_TOKEN=<secured>

DATABASE_URL=postgresql://...
ENVIRONMENT=production
```

---

**Document Signature:** This design documentation describes the Pure Leven CRM API system integration with Google Ads for enhanced conversion tracking. All implementations follow Google Ads API policies and GDPR compliance requirements.

**Date Created:** May 18, 2026  
**Last Updated:** May 18, 2026  
**Status:** Final
