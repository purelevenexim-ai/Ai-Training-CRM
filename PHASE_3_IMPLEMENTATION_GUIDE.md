# Phase 3 Implementation Guide
## OTP Login + Shopify Metafields (Deployed May 17, 2026)

---

## ✅ What Was Just Deployed

| Component | Status | Location |
|-----------|--------|----------|
| OTP Login UI | ✅ Live | `/pages/checkout-prep` - Phone + OTP input stages |
| OTP CSS Styling | ✅ Live | `assets/basil-checkout-otp.css` - 520+ lines |
| OTP JavaScript Logic | ✅ Live | `assets/basil-checkout-otp.js` - Complete flow handler |
| Updated Checkout-Prep | ✅ Live | Updated `sections/basil-checkout-prep.liquid` + JS |
| Address Metafield Storage | ✅ Live | Updated `assets/basil-checkout-prep.js` |

---

## 🚀 Required Backend Deployment

### 1. **Deploy OTP Service** (Backend)
Deploy to: `ai.pureleven.com/api/otp`

**File:** `/setup/otp-service.js`

```bash
cd /Users/bthomas/Documents/pureleven_dev
node otp-service.js
```

**Endpoints:**
- `POST /api/otp/send` - Send OTP to phone
- `POST /api/otp/verify` - Verify OTP code
- `GET /api/otp/health` - Health check

**Environment Variables Required:**
```
TWILIO_ACCOUNT_SID=xxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_PHONE=+1234567890
```

### 2. **Deploy Metafields API** (Backend)
Deploy to: `ai.pureleven.com/api/customer`

**File:** `/setup/api/customer-metafields.js`

**Endpoints:**
- `POST /api/customer/save-address` - Save addresses to metafields
- `GET /api/customer/addresses/:phone` - Retrieve saved addresses

**Required Shopify Access:**
```
SHOPIFY_ACCESS_TOKEN=<SHOPIFY_ADMIN_TOKEN> (Admin API token)
SHOPIFY_STORE=rwxtic-gz.myshopify.com
```

---

## 📋 Shopify Admin Configuration

### Step 1: Create Metafield Definitions
Run from terminal:
```bash
cd /Users/bthomas/Documents/pureleven_dev
node setup-metafields.js
```

Then execute the generated GraphQL query in Shopify Admin using:
```bash
shopify store execute --store rwxtic-gz.myshopify.com --query-file metafield_mutation.graphql --variables '...' --json --allow-mutations
```

Or manually create in **Shopify Admin > Settings > Custom data**:

**Metafield 1: Saved Addresses**
- Namespace: `basil`
- Key: `saved_addresses`
- Type: `JSON`
- Owner: `Customer`
- Visibility: Private (Admin), Public (Storefront)

**Metafield 2: Verified Phone**
- Namespace: `basil`
- Key: `phone_verified`
- Type: `Single line text`
- Owner: `Customer`
- Visibility: Private

**Metafield 3: Customer Tier**
- Namespace: `basil`
- Key: `customer_tier`
- Type: `Single line text`
- Owner: `Customer`
- Visibility: Private

### Step 2: Update Theme Settings
In **Shopify Admin > Online Store > Themes > Live Theme > Customize**:
1. Find **"Basil Checkout"** section
2. Toggle **"Enable OTP Login"** → ON
3. Set **"OTP Service URL"** → `https://ai.pureleven.com/api/otp`
4. Set **"Customer API URL"** → `https://ai.pureleven.com/api/customer`
5. Click **Save**

---

## 🔄 User Flow (OTP + Metafields)

```
User visits /pages/checkout-prep
    ↓
[OTP Form Appears]
    ↓
User enters phone number
    ↓
Click "Send OTP"
    ↓ (API call to /api/otp/send)
SMS/WhatsApp OTP arrives
    ↓
User enters 6-digit OTP
    ↓
Click "Verify OTP"
    ↓ (API call to /api/otp/verify)
    ↓
[Address Form Shows]
    ↓
User fills address form
    ↓
Click "Check Pincode" → Shiprocket validation
    ↓
Form validates ✓
    ↓
Click "Continue to Secure Payment"
    ↓ (Saves address to metafields via /api/customer/save-address)
    ↓ (Redirects to /checkout)
    ↓ (Shopify payment processing)
    ↓ (Redirect to /pages/thank-you)
```

---

## 💾 Data Flow

### Saved Addresses in Metafields
```json
{
  "name": "John Doe",
  "phone": "+919876543210",
  "pincode": "560034",
  "city": "Bangalore",
  "state": "Karnataka",
  "address1": "123 MG Road",
  "address2": "Apt 5B"
}
```

### Session Storage Keys
- `basil_verified_phone` - Phone verified via OTP
- `basil_customer_token` - Shopify customer access token
- `basil_saved_addresses` - Fallback localStorage for addresses

---

## 🧪 Testing Checklist

- [ ] **OTP Send**
  - [ ] Enter valid 10-digit phone
  - [ ] Click "Send OTP"
  - [ ] Verify message "OTP sent to your phone"
  - [ ] 10-minute countdown timer starts

- [ ] **OTP Verify**
  - [ ] Enter 6-digit OTP from SMS
  - [ ] Click "Verify OTP"
  - [ ] Address form appears
  - [ ] sessionStorage has `basil_verified_phone`

- [ ] **Address Form**
  - [ ] Form fields pre-populate if user has saved addresses
  - [ ] Pincode check works (Shiprocket API call)
  - [ ] City + State auto-fill from pincode
  - [ ] COD badge shows/hides based on serviceability
  - [ ] ETA displays correctly

- [ ] **Metafield Saving**
  - [ ] Complete checkout flow
  - [ ] Check Shopify Admin > Customers > Customer detail
  - [ ] Verify `basil.saved_addresses` metafield populated
  - [ ] Return to checkout-prep on same customer
  - [ ] Saved address appears in "Saved Addresses" section

- [ ] **Cross-Device Persistence**
  - [ ] Save address on Device A
  - [ ] Load checkout-prep on Device B with same phone
  - [ ] Verify saved address appears (fetched from metafields)

---

## 🐛 Troubleshooting

### OTP Not Sending
- **Check:** Twilio credentials in backend
- **Check:** Phone number format (must be +91XXXXXXXXXX)
- **Check:** API endpoint is reachable (test with `curl -s http://localhost:8001/api/otp/health`)

### OTP Expired Too Fast
- **Solution:** Increase `OTP_EXPIRY` in `otp-service.js` (default: 600 seconds)

### Metafields Not Saving
- **Check:** Shopify Access Token is valid and has `write_customers` scope
- **Check:** Customer exists in Shopify (checked by phone matching)
- **Fallback:** Addresses still save to localStorage; metafield save is async

### Address Not Auto-Filling from Metafields
- **Check:** `basil_verified_phone` is in sessionStorage
- **Check:** Metafield query succeeds (check browser console)
- **Fallback:** User can manually enter address

---

## 📊 Analytics Hooks

Phase 3 includes tracking for:
- `otp_sent` - User requested OTP
- `otp_verified` - OTP verification successful
- `pincode_validated` - Shiprocket validation passed
- `address_saved_metafields` - Address persisted to Shopify
- `prep_completed` - Ready for checkout

---

## 🎯 Next Steps (Phase 4+)

1. **Customer Data Enrichment**
   - Store purchase history in metafields
   - Track repeat customer tier
   - Personalize post-purchase offers

2. **Advanced Address Intelligence**
   - Same-day delivery zones
   - Standard vs Premium COD availability
   - Area-based shipping cost optimization

3. **Loyalty Integration**
   - Referral rewards in thank-you page
   - Repeat customer discounts
   - VIP tier benefits

4. **Analytics & Optimization**
   - Track drop-off by pincode
   - Monitor OTP success rate
   - Measure address-to-checkout conversion

---

## 📞 Support

For issues, check:
1. Browser console (Ctrl+Shift+I → Console)
2. Network tab (failed API calls)
3. Backend logs (`ai.pureleven.com` server)
4. Shopify Admin > Apps > Events (Customer events logging)

---

**Deployed:** May 17, 2026
**Version:** Phase 3.0
**Status:** Ready for Production Testing
