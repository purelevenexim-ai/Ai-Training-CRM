# 🎯 META AUDIENCES TEMPLATE - META ADS VISITOR RETARGETING
**Retarget People Who Clicked Your Meta/Facebook Ads**

---

## AUDIENCE SET 1: META ADS VISITORS (General)

### **Audience 1A: All Meta Ads Visitors**

```
BASIC SETUP:
├─ Name: "Meta - All Visitors"
├─ Description: "All people who visited from Meta/Facebook ads"
├─ Type: Custom Audience (Customer List)
├─ Update Method: Nightly from CRM
│
FILTERS (When importing from CRM):
├─ utm_source = "facebook" OR utm_source = "meta"
├─ First visit: Last 30 days
├─ Status: VISITOR (anyone who visited, purchased or not)
│
AUDIENCE SIZE EXPECTATIONS:
├─ Week 1: 30-80
├─ Month 1: 100-300
├─ Month 3: 300-1000+
│
REFRESH STRATEGY:
├─ Add fresh visitors: Daily
├─ Remove converters: Weekly (once they buy, move to "Converters")
└─ Total active size: Continuously growing
```

### **Audience 1B: Meta Ads Visitors NOT Yet Converted**

```
BASIC SETUP:
├─ Name: "Meta - Visitors (Non-Converters)"
├─ Description: "People from Meta ads who haven't purchased yet"
├─ Type: Custom Audience (Customer List)
├─ Update Method: Nightly from CRM
│
FILTERS (When importing from CRM):
├─ utm_source = "facebook" OR utm_source = "meta"
├─ status = "VISITOR" (NOT purchased)
├─ First visit: Last 90 days
│
AUDIENCE SIZE EXPECTATIONS:
├─ Target: 60-80% of all Meta ads visitors
├─ Priority: HIGH (best for retargeting)
│
WHY THIS WORKS:
├─ These people showed INTEREST (clicked your Meta ad)
├─ Haven't converted yet (need second touchpoint)
├─ Most likely to convert with retargeting ads
└─ Different message = higher conversion rate
```

### **Audience 1C: Meta Ads Visitors WHO Converted**

```
BASIC SETUP:
├─ Name: "Meta - Visitors (Converted)"
├─ Description: "People from Meta ads who made a purchase"
├─ Type: Custom Audience (Customer List)
├─ Update Method: Nightly from CRM
│
FILTERS (When importing from CRM):
├─ utm_source = "facebook" OR utm_source = "meta"
├─ status = "CUSTOMER" (already purchased)
│
AUDIENCE SIZE EXPECTATIONS:
├─ Target: 20-40% of all Meta ads visitors
├─ Priority: MEDIUM
│
USE FOR:
├─ Cross-sell campaigns (upsell new products)
├─ Loyalty/VIP campaigns (repeat purchase incentives)
├─ Product recommendations (related items)
└─ Win-back campaigns (if inactive > 30 days)
```

---

## AUDIENCE SET 2: META ADS PRODUCT PAGE VISITORS (Per Product)

### **Audience 2A: Meta Visitors - Cinnamon (Ceylon) 100g**

```
BASIC SETUP:
├─ Name: "Meta - Viewed: Ceylon Cinnamon 100g"
├─ Description: "Meta ad visitors who viewed Ceylon Cinnamon product"
├─ Type: Custom Audience (Customer List)
├─ Product SKU: CINNAMON-100G-CEYLON
│
FILTERS (When importing from CRM):
├─ utm_source = "facebook" OR utm_source = "meta"
├─ event_type = "product_view"
├─ product_handle = "aromatic-cinnamon-ceylon-100g"
├─ Visited last: 30 days
│
AUDIENCE SIZE EXPECTATIONS:
├─ Week 1: 3-10
├─ Month 1: 20-50
│
USE FOR:
├─ Retarget with same product (but with different angle)
├─ Retarget with complementary products
├─ Show variants/bundle options
└─ Test customer testimonials for this product
```

### **Audience 2B: Meta Visitors - Cinnamon (Cassia) 200g**

```
BASIC SETUP:
├─ Name: "Meta - Viewed: Cassia Cinnamon 200g"
├─ Description: "Meta ad visitors who viewed Cassia Cinnamon product"
├─ Type: Custom Audience (Customer List)
├─ Product SKU: CINNAMON-200G-CASSIA
│
FILTERS (When importing from CRM):
├─ utm_source = "facebook" OR utm_source = "meta"
├─ event_type = "product_view"
├─ product_handle = "premium-cassia-cinnamon-200g"
├─ Visited last: 30 days
│
AUDIENCE SIZE EXPECTATIONS:
├─ Week 1: 2-8
├─ Month 1: 15-40
│
USE FOR:
├─ Retarget with premium positioning
├─ Show quality certification
├─ Bundle with complementary products
└─ Test upsell angles
```

### **Audience 2C: Meta Visitors - Multiple Products Viewed**

```
BASIC SETUP:
├─ Name: "Meta - Multi-Product Browsers"
├─ Description: "Meta ad visitors who viewed 3+ products"
├─ Type: Custom Audience (Customer List)
│
FILTERS (When importing from CRM):
├─ utm_source = "facebook" OR utm_source = "meta"
├─ event_type = "product_view"
├─ product_views >= 3
├─ Visited last: 14 days
│
AUDIENCE SIZE EXPECTATIONS:
├─ Target: 20-40% of all Meta ads visitors
│
WHY IMPORTANT:
├─ Showed HIGH ENGAGEMENT (browsed multiple products)
├─ More likely to convert with right offer
├─ Already interested in multiple items
│
USE FOR:
├─ Bundle/combo deals ("Get 3 spices at 20% off")
├─ Collection pages retargeting
├─ "Complete your set" messaging
└─ Variety/diversity positioning
```

---

## AUDIENCE SET 3: META ADS CART ABANDONERS

### **Audience 3A: Meta Visitors - Added to Cart**

```
BASIC SETUP:
├─ Name: "Meta - Cart Abandoners"
├─ Description: "Meta ad visitors who added items but didn't buy"
├─ Type: Custom Audience (Customer List)
│
FILTERS (When importing from CRM):
├─ utm_source = "facebook" OR utm_source = "meta"
├─ event_type = "cart_viewed" OR "cart_added"
├─ status = "VISITOR" (didn't purchase)
├─ Visited last: 7 days
│
AUDIENCE SIZE EXPECTATIONS:
├─ Target: 25-40% of product viewers
├─ Priority: CRITICAL (hot audience!)
│
WHY THIS IS GOLD:
├─ These people DECIDED TO BUY (put in cart)
├─ Already took action (high intent)
├─ Just need final nudge
├─ Typical ROI: 4-8:1 on retargeting spend
```

### **Audience 3B: Meta Visitors - High-Value Cart**

```
BASIC SETUP:
├─ Name: "Meta - High-Value Cart Abandoners"
├─ Description: "Meta ad visitors with ₹1000+ in abandoned cart"
├─ Type: Custom Audience (Customer List)
│
FILTERS (When importing from CRM):
├─ utm_source = "facebook" OR utm_source = "meta"
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
├─ Free shipping guarantee
├─ Money-back guarantee
└─ Exclusive VIP discount codes
```

---

## AUDIENCE SET 4: META ADS CHECKOUT ABANDONERS

### **Audience 4A: Meta Visitors - Checkout Initiated (No Purchase)**

```
BASIC SETUP:
├─ Name: "Meta - Checkout Abandoned"
├─ Description: "Meta ad visitors who started checkout but didn't buy"
├─ Type: Custom Audience (Customer List)
│
FILTERS (When importing from CRM):
├─ utm_source = "facebook" OR utm_source = "meta"
├─ event_type = "checkout_initiated"
├─ status = "VISITOR" (didn't purchase)
├─ Initiated checkout: Last 3 days
│
AUDIENCE SIZE EXPECTATIONS:
├─ Small but VERY HOT audience
├─ Priority: ABSOLUTE PRIORITY
│
WHY THIS WORKS:
├─ They were 99% ready to buy
├─ Only final step prevented them
├─ Typical abandonment reasons: Payment issues, last-minute hesitation
│
RETARGETING STRATEGY:
├─ Show multiple payment options (UPI, card, wallet)
├─ Add security badges
├─ Add delivery speed info
└─ Highest ROI for immediate retargeting (within 24 hours)
```

### **Audience 4B: Meta Visitors - Checkout Abandoned (High Value)**

```
BASIC SETUP:
├─ Name: "Meta - High-Value Checkout Abandoned"
├─ Description: "Meta ad visitors with ₹1500+ order abandoned at checkout"
├─ Type: Custom Audience (Customer List)
│
FILTERS (When importing from CRM):
├─ utm_source = "facebook" OR utm_source = "meta"
├─ event_type = "checkout_initiated"
├─ checkout_value >= 1500
├─ Initiated checkout: Last 3 days
│
AUDIENCE SIZE EXPECTATIONS:
├─ Small (5-10 people per week)
├─ Priority: ABSOLUTE PRIORITY
│
USE FOR:
├─ Direct message campaigns (urgent follow-up)
├─ Highest incentive offers (₹300+ discount)
├─ Personal touch (1-on-1 messaging)
└─ Phone follow-up (if you have contacts)
```

---

## SUMMARY: AUDIENCE HIERARCHY FOR META VISITORS

```
TIER 1 - HIGHEST PRIORITY (Retarget immediately):
├─ Meta - Checkout Abandoned (₹1500+) ← SAME-DAY RETARGETING
├─ Meta - Checkout Abandoned (all amounts)
└─ Meta - Cart Abandoners (₹1000+)

TIER 2 - HIGH PRIORITY (Retarget next day):
├─ Meta - Visitors (Non-Converters)
├─ Meta - Cart Abandoners (all)
└─ Meta - Multi-Product Browsers

TIER 3 - MEDIUM PRIORITY (Retarget throughout month):
├─ Meta - Viewed: [Product Name]
├─ Meta - All Visitors
└─ Meta - Visitors (Converted - for upsell)

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
   ├─ Description: Add which utm_source filter used
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

## DIFFERENCE: Meta Visitors vs Google Ads Visitors

### **Why Create Both?**

```
Google Ads Visitors:
├─ High-intent searchers
├─ Looking for specific solutions
├─ Convert at: 15-20% on first visit
├─ Retarget with: Solution-focused messaging
└─ Best for: Problem-solving positioning

Meta Ads Visitors:
├─ Interest-based, awareness-focused
├─ May not have been actively searching
├─ Convert at: 5-10% on first visit
├─ Retarget with: Lifestyle/benefit messaging
└─ Best for: Lifestyle/inspiration positioning
```

### **Different Messages for Different Audiences:**

```
Google Ads Retargeting Message:
"Complete your ₹500 order now - Free shipping inside"
(Urgency, price, convenience)

Meta Ads Retargeting Message:
"Discover why 1000+ people love our cinnamon"
(Social proof, lifestyle, benefits)
```

---

## EXPECTED RESULTS (Meta Visitor Retargeting)

```
Month 1:
├─ Meta visitor checkout abandonments: 10-15
│  └─ Direct conversions: 2-4 (20-30%)
│  └─ Revenue: ₹1,000-₹2,000
│
├─ Meta visitor cart abandoners: 20-30
│  └─ Direct conversions: 3-5 (15-20%)
│  └─ Revenue: ₹1,500-₹2,500
│
├─ Meta visitor non-converters: 50-80
│  └─ Direct conversions: 2-6 (4-10%)
│  └─ Revenue: ₹1,000-₹3,000
│
└─ TOTAL Meta Visitor Retargeting:
   ├─ Conversions: 7-15
   ├─ Revenue: ₹3,500-₹7,500
   ├─ Cost: ₹800-₹1200 (retargeting spend)
   └─ ROAS: 3-6:1 ✅ (excellent)
```

---

## NOTES

- **Key Point**: Meta visitor checkout abandoners are also gold (20-30% recovery)
- **Frequency Cap**: Consider capping ads at 3-5 per person per day
- **Duration**: Different audiences need different retargeting duration:
  - Checkout abandoned: 3 days (urgent)
  - Cart abandoned: 7 days (still interested)
  - Product viewers: 14 days (warming up)
  - General visitors: 30 days (awareness building)
- **Creative**: Use lifestyle/benefit messaging (different from Google Ads)
- **Offer**: Match to psychology (Social proof > Urgency > Discount)

---

**Ready to create these audiences for Meta visitor retargeting? Follow the same process as Google Ads visitors!**
