# 🎯 META AUDIENCES TEMPLATE - GOOGLE ADS RETARGETING
**Ready-to-Use Audience Configurations for Pureleven**

---

## AUDIENCE SET 1: GOOGLE ADS VISITORS (General)

### **Audience 1A: All Google Ads Visitors**

```
BASIC SETUP:
├─ Name: "GA - All Visitors"
├─ Description: "All people who visited from Google Ads"
├─ Type: Custom Audience (Customer List)
├─ Update Method: Nightly from CRM
│
FILTERS (When importing from CRM):
├─ utm_source = "google_ads"
├─ First visit: Last 30 days
├─ Status: VISITOR (anyone who visited, purchased or not)
│
AUDIENCE SIZE EXPECTATIONS:
├─ Week 1: 50-100
├─ Month 1: 200-500
├─ Month 3: 500-2000+
│
REFRESH STRATEGY:
├─ Add fresh visitors: Daily
├─ Remove converters: Weekly (once they buy, move to "Converters")
└─ Total active size: Continuously growing
```

### **Audience 1B: Google Ads Visitors NOT Yet Converted**

```
BASIC SETUP:
├─ Name: "GA - Visitors (Non-Converters)"
├─ Description: "People from Google Ads who haven't purchased yet"
├─ Type: Custom Audience (Customer List)
├─ Update Method: Nightly from CRM
│
FILTERS (When importing from CRM):
├─ utm_source = "google_ads"
├─ status = "VISITOR" (NOT purchased)
├─ First visit: Last 90 days
│
AUDIENCE SIZE EXPECTATIONS:
├─ Target: 60-80% of all Google Ads visitors
├─ Priority: HIGH (best for retargeting)
│
WHY THIS WORKS:
├─ These people are HIGH INTENT (clicked your Google Ads)
├─ Haven't converted yet (need second touchpoint)
├─ Most likely to convert with retargeting ads
└─ Highest ROI audience
```

### **Audience 1C: Google Ads Visitors WHO Converted**

```
BASIC SETUP:
├─ Name: "GA - Visitors (Converted)"
├─ Description: "People from Google Ads who made a purchase"
├─ Type: Custom Audience (Customer List)
├─ Update Method: Nightly from CRM
│
FILTERS (When importing from CRM):
├─ utm_source = "google_ads"
├─ status = "CUSTOMER" (already purchased)
│
AUDIENCE SIZE EXPECTATIONS:
├─ Target: 20-40% of all Google Ads visitors
├─ Priority: MEDIUM
│
USE FOR:
├─ Cross-sell campaigns (upsell new products)
├─ Loyalty/VIP campaigns (repeat purchase incentives)
├─ Product recommendations (related items)
└─ Win-back campaigns (if inactive > 30 days)
```

---

## AUDIENCE SET 2: GOOGLE ADS PRODUCT PAGE VISITORS (Per Product)

### **Audience 2A: GA Visitors - Cinnamon (Ceylon) 100g**

```
BASIC SETUP:
├─ Name: "GA - Viewed: Ceylon Cinnamon 100g"
├─ Description: "Google Ads visitors who viewed Ceylon Cinnamon product"
├─ Type: Custom Audience (Customer List)
├─ Product SKU: CINNAMON-100G-CEYLON
│
FILTERS (When importing from CRM):
├─ utm_source = "google_ads"
├─ event_type = "product_view"
├─ product_handle = "aromatic-cinnamon-ceylon-100g"
├─ Visited last: 30 days
│
AUDIENCE SIZE EXPECTATIONS:
├─ Week 1: 5-15
├─ Month 1: 30-80
│
USE FOR:
├─ Retarget with same product (but with discount/offer)
├─ Retarget with complementary products (spice blends, etc.)
├─ A/B test different product angles
└─ Test different price points
```

### **Audience 2B: GA Visitors - Cinnamon (Cassia) 200g**

```
BASIC SETUP:
├─ Name: "GA - Viewed: Cassia Cinnamon 200g"
├─ Description: "Google Ads visitors who viewed Cassia Cinnamon product"
├─ Type: Custom Audience (Customer List)
├─ Product SKU: CINNAMON-200G-CASSIA
│
FILTERS (When importing from CRM):
├─ utm_source = "google_ads"
├─ event_type = "product_view"
├─ product_handle = "premium-cassia-cinnamon-200g"
├─ Visited last: 30 days
│
AUDIENCE SIZE EXPECTATIONS:
├─ Week 1: 8-20
├─ Month 1: 40-100
│
USE FOR:
├─ Retarget this specific product
├─ Create lookalike audiences (find similar buyers)
└─ Test premium positioning
```

### **Audience 2C: GA Visitors - Multiple Products Viewed**

```
BASIC SETUP:
├─ Name: "GA - Multi-Product Browsers"
├─ Description: "Google Ads visitors who viewed 3+ products"
├─ Type: Custom Audience (Customer List)
│
FILTERS (When importing from CRM):
├─ utm_source = "google_ads"
├─ event_type = "product_view"
├─ product_views >= 3
├─ Visited last: 14 days
│
AUDIENCE SIZE EXPECTATIONS:
├─ Target: 10-20% of all Google Ads visitors
│
WHY IMPORTANT:
├─ Showed HIGH ENGAGEMENT (browsed multiple products)
├─ More likely to convert with right offer
├─ Price-sensitive (comparing options)
│
USE FOR:
├─ Offer "Bundle deals" or "Mix & Match" promotions
├─ Retarget with collection/category pages
└─ Test urgency messaging
```

---

## AUDIENCE SET 3: GOOGLE ADS CART ABANDONERS

### **Audience 3A: GA Visitors - Added to Cart**

```
BASIC SETUP:
├─ Name: "GA - Cart Abandoners"
├─ Description: "Google Ads visitors who added items to cart but didn't buy"
├─ Type: Custom Audience (Customer List)
│
FILTERS (When importing from CRM):
├─ utm_source = "google_ads"
├─ event_type = "cart_viewed" OR "cart_added"
├─ status = "VISITOR" (didn't purchase)
├─ Visited last: 7 days
│
AUDIENCE SIZE EXPECTATIONS:
├─ Target: 20-40% of product viewers
├─ Priority: CRITICAL (hot audience!)
│
WHY THIS IS GOLD:
├─ These people DECIDED TO BUY (put in cart)
├─ Only small friction stopped them
├─ Highest conversion rate for retargeting
└─ Typical ROI: 5-10:1 on retargeting spend
```

### **Audience 3B: GA Visitors - High-Value Cart**

```
BASIC SETUP:
├─ Name: "GA - High-Value Cart Abandoners"
├─ Description: "Google Ads visitors with ₹1000+ in abandoned cart"
├─ Type: Custom Audience (Customer List)
│
FILTERS (When importing from CRM):
├─ utm_source = "google_ads"
├─ event_type = "cart_viewed"
├─ cart_value >= 1000
├─ Visited last: 7 days
│
AUDIENCE SIZE EXPECTATIONS:
├─ Target: 5-15% of all cart abandoners
├─ Priority: HIGHEST
│
USE FOR:
├─ Premium messaging ("Complete your ₹X order")
├─ Free shipping incentives
├─ Exclusive discount codes
└─ Direct communication (email + ads)
```

---

## AUDIENCE SET 4: GOOGLE ADS CHECKOUT ABANDONERS

### **Audience 4A: GA Visitors - Checkout Initiated (No Purchase)**

```
BASIC SETUP:
├─ Name: "GA - Checkout Abandoned"
├─ Description: "Google Ads visitors who started checkout but didn't buy"
├─ Type: Custom Audience (Customer List)
│
FILTERS (When importing from CRM):
├─ utm_source = "google_ads"
├─ event_type = "checkout_initiated"
├─ status = "VISITOR" (didn't purchase)
├─ Initiated checkout: Last 3 days
│
AUDIENCE SIZE EXPECTATIONS:
├─ Small but VERY HOT audience
├─ Priority: MAXIMUM (extremely high intent)
│
WHY THIS WORKS:
├─ They were 95% ready to buy
├─ Only final step prevented them
├─ Typical abandonment reasons: Shipping cost, Payment method, Delivery time
│
RETARGETING STRATEGY:
├─ Show lower shipping cost
├─ Show multiple payment options
├─ Add trust signals (reviews, guarantees)
└─ Highest ROI for fast retargeting (within 24 hours)
```

### **Audience 4B: GA Visitors - Checkout Abandoned (High Value)**

```
BASIC SETUP:
├─ Name: "GA - High-Value Checkout Abandoned"
├─ Description: "Google Ads visitors with ₹1500+ order abandoned at checkout"
├─ Type: Custom Audience (Customer List)
│
FILTERS (When importing from CRM):
├─ utm_source = "google_ads"
├─ event_type = "checkout_initiated"
├─ checkout_value >= 1500
├─ Initiated checkout: Last 3 days
│
AUDIENCE SIZE EXPECTATIONS:
├─ Small (5-10 people per week)
├─ Priority: ABSOLUTE PRIORITY
│
USE FOR:
├─ 1-on-1 personalized messaging
├─ Direct message campaigns (urgent)
├─ High-value incentives (₹200+ discount)
└─ Phone follow-up (if you have)
```

---

## SUMMARY: AUDIENCE HIERARCHY

```
TIER 1 - HIGHEST PRIORITY (Retarget first):
├─ GA - Checkout Abandoned (₹1500+) ← DO THIS FIRST
├─ GA - Checkout Abandoned (all amounts)
└─ GA - Cart Abandoners (₹1000+)

TIER 2 - HIGH PRIORITY (Retarget next day):
├─ GA - Visitors (Non-Converters)
├─ GA - Cart Abandoners (all)
└─ GA - Multi-Product Browsers

TIER 3 - MEDIUM PRIORITY (Retarget throughout month):
├─ GA - Viewed: [Product Name]
├─ GA - All Visitors
└─ GA - Visitors (Converted - for upsell)

AUDIENCE MANAGEMENT:
├─ Update daily: Checkout & Cart abandonments (hot)
├─ Update daily: Non-converters (growing audience)
├─ Update weekly: Product viewers (steady)
├─ Remove after: 30 days of last visit (warm audiences)
├─ Remove after: 90 days for cold audiences
└─ Keep converted customers separate (upsell strategy)
```

---

## HOW TO CREATE IN META ADS MANAGER

### **Step-by-Step:**

```
1. Go to Meta Business Suite → Ads Manager
2. Click Audiences (left menu)
3. Click Create Audience
4. Select "Custom Audience"
5. Choose "Customer List"
6. Upload CSV with emails from your CRM
7. Fill details:
   ├─ Audience Name: Copy from template above
   ├─ Description: Add context (which filter used)
   ├─ Data source: Your CRM/database
   ├─ Retention time: 30-90 days (until next upload)
   └─ Privacy: Keep data private
8. Click Create Audience
9. Repeat for each audience type
```

### **CSV Format Example:**

```
email,first_name,last_name,phone,creation_date
john@example.com,John,Doe,9876543210,2026-05-17
jane@example.com,Jane,Smith,9123456789,2026-05-16
...
```

---

## AUTOMATION WORKFLOW (Future)

Once you have the page view tracking running:

```
CRM Database:
├─ Tracks: utm_source, event_type, product_handle, cart_value, etc.
│
Nightly Job (11 PM):
├─ Export "GA - Checkout Abandoned" (last 3 days)
├─ Upload to Meta
├─ Export "GA - Cart Abandoners" (last 7 days)
├─ Upload to Meta
├─ Export "GA - Visitors (Non-Converters)" (last 30 days)
├─ Upload to Meta
└─ Export "GA - Viewed: [Product]" for each top product
│
Meta Ads:
├─ Automatically retarget these audiences
├─ Refresh audiences daily
├─ Track conversions back to CRM
└─ Measure ROI by audience
```

---

## EXPECTED RESULTS

```
Week 1-2:
├─ Checkout Abandoners: 5-10 people
│  └─ Expected conversions: 1-3 (20-30% recovery)
├─ Cart Abandoners: 15-30 people
│  └─ Expected conversions: 2-5 (15-20% recovery)
└─ Spend: ₹300-500

Week 3-4:
├─ Checkout Abandoners: 10-20 people
│  └─ Expected conversions: 2-6 (20-30%)
├─ Cart Abandoners: 30-60 people
│  └─ Expected conversions: 5-12 (15-20%)
├─ Non-Converters: 50-100 people
│  └─ Expected conversions: 2-5 (4-10%)
└─ Spend: ₹800-1200

Month 1 Total:
├─ Retargeting conversions: 12-28
├─ Retargeting revenue: ₹6,000-₹14,000 (depending on AOV)
├─ Retargeting cost: ₹1200-1700
└─ ROAS: 5:1 to 10:1 ✅ (excellent)
```

---

## NOTES

- **Key Point**: Checkout & Cart abandoners are your GOLD audiences (highest conversion rates)
- **Frequency Cap**: Consider capping ads at 3-5 per person per day (avoid fatigue)
- **Duration**: Different audiences need different retargeting duration:
  - Checkout abandoned: 3 days (urgent)
  - Cart abandoned: 7 days (still interested)
  - Product viewers: 14 days (warming up)
  - General visitors: 30 days (awareness building)
- **Creative**: Use different creatives for each audience (what they abandoned/viewed)
- **Offer**: Match offer to reason for abandonment (shipping costs → show free shipping, etc.)

---

**Ready to create these audiences in Meta? I'll help you set them up!**
