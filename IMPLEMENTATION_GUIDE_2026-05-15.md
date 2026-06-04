# PURELEVEN GOOGLE ADS IMPLEMENTATION GUIDE
**Date:** May 15, 2026 | **Status:** IN PROGRESS | **Priority:** CRITICAL

---

## 📋 EXECUTIVE SUMMARY

This guide covers the 4 critical areas of implementation:
1. **Conversion Tracking Fix** (Primary action, value rules, custom variables)
2. **Campaign Performance Review & Optimization** (Search-Kerala-Spices-May2026)
3. **Merchant Center Integration** (Product feed sync with assets)
4. **Audience Setup & Targeting** (Geographic exclusions, demographics, retargeting)

**Timeline:** Implementation should complete by May 18, 2026
**Expected Impact:** +₹100,000-200,000/month revenue increase when all complete

---

## 1️⃣ CONVERSION TRACKING FIXES

### Current Status: 🔴 CRITICAL GAPS
- ✅ Google Ads Pixel: Installed and firing (108 conversions tracked)
- ✅ Conversion Events: 7 events mapped (purchase, add_to_cart, view_item, etc.)
- ❌ **Primary Conversion Action**: NOT SET
- ❌ **Conversion Value**: ₹0.00 (despite 108 conversions)
- ❌ **Value Rules**: NOT CREATED
- ❌ **Custom Variables**: NOT CONFIGURED

### Fix 1.1: Set Purchase as Primary Conversion Action
**Path:** Tools > Goals > Conversions > Settings > Purchase (click edit)

**Steps:**
1. Navigate to Google Ads account (AW-10965185406)
2. Click Goals (trophy icon) in left sidebar
3. Go to Conversions > Settings
4. Find "Purchase" conversion action
5. Click the edit pencil icon
6. Under "Conversion goal" → Check "Primary action"
7. Under "Optimization" → Enable "Use this action for bidding"
8. Save

**Expected Result:** Campaign bidding now has optimization signal

---

### Fix 1.2: Set Conversion Value (STATIC - SAFER FOR NOW)
**Path:** Tools > Goals > Conversions > Settings > Purchase > Edit

**Steps:**
1. In Purchase conversion edit dialog
2. Scroll to "Value" section
3. Select "Use the same value for each conversion"
4. Enter: `800` (your approximate AOV in INR)
5. Currency: `INR`
6. Save

**Expected Result:** ₹800 assigned per conversion for ROAS calculation

---

### Fix 1.3: Create Value Rules (OPTIONAL - ADVANCED)
**Path:** Tools > Goals > Conversions > Value rules

**Why:** To pass ACTUAL order value from Shopify checkout instead of static ₹800

**Steps:**
1. Go to "Value rules" in Conversions menu
2. Click "+ Create value rule"
3. Name: "Shopify Order Value"
4. Condition: "Page URL contains" = `/checkout/thank_you`
5. Set value from: "URL parameter" = `total_price` OR "Data layer variable"
6. Currency: INR
7. Save

**Expected Result:** Dynamic values from Shopify override static value

---

### Fix 1.4: Create Custom Variables (OPTIONAL - FOR TRACKING)
**Path:** Tools > Goals > Conversions > Custom variables

**Why:** To track order details (product name, category, customer segment)

**Steps:**
1. Go to "Custom variables" in Conversions menu
2. Create variable 1:
   - Name: "Product Category"
   - Type: "String"
3. Create variable 2:
   - Name: "Product Name"
   - Type: "String"
4. Create variable 3:
   - Name: "Customer Segment"
   - Type: "String"

**Expected Result:** Enhanced conversion data for analysis

---

## 2️⃣ CAMPAIGN REVIEW: Search-Kerala-Spices-May2026

### Current Status: 🟡 NEWLY CREATED
- Campaign created in previous session: May 15, 2026
- 6 Ad Groups created (Kerala Spices, Black Pepper, Cardamom, Cinnamon, Cloves, Generic Spices)
- 125 negative keywords added (phrase match, campaign level)
- All ads have 15 headlines + 4 descriptions
- Keywords: 50 total (5-10 per ad group)

### Review Task 2.1: Check Campaign Performance Data
**Path:** Campaigns > Search-Kerala-Spices-May2026

**What to Monitor:**
- Impressions: Should see impressions within 24-48 hours
- Clicks: Target >5% CTR
- Cost: Should be ₹400/day as configured
- Conversions: Need 50+ conversions before optimization
- Quality Scores: Target 7+

**Red Flags to Watch:**
- Any keyword with 20+ clicks, 0 conversions → PAUSE
- Quality Score < 5 → Review ad copy and landing pages
- CTR < 3% → Check bid adjustments or keyword match types

### Review Task 2.2: Analyze Search Terms Report
**Path:** Campaigns > Search-Kerala-Spices-May2026 > Keywords > Search terms

**Steps:**
1. Review search terms that triggered ads
2. Add new high-volume, high-conversion searches as keywords
3. Add misspellings/unwanted terms to negative keywords
4. Identify keyword expansion opportunities

### Review Task 2.3: Quality Score Improvement
**If any keyword has QS < 7:**
1. Check ad relevance (does ad copy match keyword?)
2. Check landing page (does page contain keyword?)
3. Consider increasing bid by 20-30% to improve placement
4. Review ad extensions (sitelinks, callouts, etc.)

---

## 3️⃣ MERCHANT CENTER INTEGRATION

### Current Status: 🔴 CONNECTED BUT VERIFICATION NEEDED
- Merchant Center ID: 5618477992
- Status: Need to verify product feed sync

### Review Task 3.1: Verify Merchant Center Product Feed
**Path:** https://merchants.google.com/mc/items?a=5618477992

**Check:**
- [ ] All products from Shopify synced (cardamom, pepper, cloves, cinnamon, etc.)
- [ ] No products in "Disapproved" status
- [ ] All required attributes present: image, price, description
- [ ] Prices match Shopify store

### Review Task 3.2: Update Assets in Merchant Center (If Needed)
**For each product, ensure:**
1. **High-quality images** (at least 800x800px)
   - Primary image should show product clearly
   - Multiple images for different angles
2. **Detailed descriptions**
   - Include benefits (organic, farm-origin, whole spice, etc.)
   - Target keywords (black pepper online, cardamom fresh, etc.)
3. **Correct pricing**
   - ₹649 or actual retail price
   - Consistent with Shopify
4. **Custom labels** (optional but useful)
   - Label 0: "organic"
   - Label 1: "farm-origin"
   - Label 2: "best-seller" (if applicable)

### Review Task 3.3: Link Merchant Center to Google Ads Campaigns
**For Performance Max campaign:**
1. Go to Sales-P.Max-Spices-Mar2024 campaign
2. Campaign settings > Product feed
3. Select the Merchant Center feed
4. Ensure all products are eligible (not disapproved)
5. Save

**Expected Result:** Shopping ads can now display in Performance Max

---

## 4️⃣ AUDIENCE SETUP & TARGETING

### 4A: GEOGRAPHIC EXCLUSIONS (TIER 1 PRIORITY)

**High RTO States to EXCLUDE:**
```
TIER 1 EXCLUSIONS (Exclude entirely):
- Jammu & Kashmir
- Ladakh
- Nagaland
- Mizoram
- Arunachal Pradesh
- Manipur

TIER 2 EXCLUSIONS (Restrict with observation):
- Assam
- Meghalaya
- Tripura
- West Bengal
- Odisha
- Chhattisgarh
- Jharkhand
```

**Implementation:**
1. Go to Campaign > Settings > Locations
2. Add exclusions for all 18 states above
3. Set bid adjustments for remaining states:
   - Tier-1 metros (Delhi, Mumbai, Bangalore, Hyderabad): +15%
   - Tier-2 cities (Pune, Chennai, Kolkata, Jaipur): 0% (baseline)
   - Tier-3 cities: -10%
   - Rural areas: -20%

---

### 4B: DEMOGRAPHIC TARGETING

**Setup:**
1. Campaign > Audience > Demographics
2. Age: 27 and above (exclude 18-26)
3. Gender: All (no gender restrictions yet - test first)
4. Household income: Not set (let Google optimize)

**Bid Adjustments:**
- Age 27-34: +10% (most active spice buyers)
- Age 35-54: +15% (highest AOV)
- Age 55+: +5% (lower volume, good value buyers)

---

### 4C: AUDIENCE CREATION (REMARKETING)

**Audience 1: Website Visitors (Last 30 days)**
- Name: `WEB_VISITORS_30D`
- Source: Google Analytics 4
- Condition: Page view on any pureleven.com page
- Duration: 30 days
- Purpose: Retarget with discount ads, lower bid

**Audience 2: Product Viewers**
- Name: `PRODUCT_VIEWERS_CARDAMOM`
- Source: Google Analytics 4
- Condition: Page view on `/products/cardamom`
- Duration: 30 days
- Purpose: Retarget cardamom buyers specifically

**Audience 3: Add to Cart Abandoners**
- Name: `CART_ABANDONERS`
- Source: Google Analytics 4
- Condition: Event `add_to_cart` + NO event `purchase` in last 7 days
- Duration: 7 days
- Purpose: "Complete your order" messaging, 10-15% discount

**Audience 4: Purchase Customers (Customer Match)**
- Name: `CUSTOMER_MATCH_BUYERS`
- Source: Shopify customer export
- Upload emails + phone numbers
- Match rate: 30-50%
- Purpose: Upsell higher-value products, +20% bid boost

---

### 4D: PRODUCT-SPECIFIC AUDIENCES

**Create 4 separate audiences for cross-sell:**

| Audience | Condition | Purpose | Bid Adjustment |
|----------|-----------|---------|-----------------|
| `Cardamom_Viewers` | Viewed /products/cardamom | Show Black Pepper ads | +10% |
| `Pepper_Viewers` | Viewed /products/black-pepper | Show Cardamom ads | +10% |
| `Cloves_Viewers` | Viewed /products/cloves | Show Cinnamon ads | +10% |
| `Cinnamon_Viewers` | Viewed /products/cinnamon | Show Cloves ads | +10% |

**Messaging Strategy:**
- Show complementary products
- Offer bundle discount ("Buy together, save ₹100")

---

### 4E: RETARGETING STRATEGY & BID MANAGEMENT

**Tier 1: High-Intent Retargeting**
- Audience: Cart abandoners
- Bid: +30% (highest ROI)
- Ad Copy: "You left something behind - Complete your ₹XXX order"
- Offer: Free shipping OR 10% discount

**Tier 2: Medium-Intent Retargeting**
- Audience: Product page viewers (last 7 days)
- Bid: +15% (good ROI)
- Ad Copy: "Fresh [Product] - Order Today for Free Delivery"
- Offer: None (standard offer)

**Tier 3: Low-Intent Retargeting**
- Audience: Website visitors (8-30 days ago)
- Bid: -20% (test efficiency)
- Ad Copy: "Save ₹100 on Your First Order"
- Offer: First-order coupon code

**Tier 4: Customer Upsell**
- Audience: Purchased customers (past 6 months)
- Bid: Baseline
- Ad Copy: "Customers Also Love..." (cross-sell)
- Offer: Bundle discount

---

## 5️⃣ IMPLEMENTATION CHECKLIST

### Phase 1 (This Week - May 15-17)
- [ ] Set Purchase as primary conversion action
- [ ] Set ₹800 static conversion value
- [ ] Verify Merchant Center product feed (all 11+ products approved)
- [ ] Create geographic exclusions (18 states)
- [ ] Create demographic targeting (27+, India, Tier-1 bias)
- [ ] Create 4 product-specific audiences

### Phase 2 (Week of May 18-24)
- [ ] Create remarketing audiences (visitors, cart abandoners, purchases)
- [ ] Set up value rules (if Shopify integration ready)
- [ ] Create custom variables
- [ ] Implement bid adjustments for all audiences
- [ ] Test product-specific retargeting ads

### Phase 3 (Week of May 25-31)
- [ ] Monitor campaign performance (50+ conversions needed)
- [ ] Review search terms report
- [ ] Pause low-performing keywords
- [ ] Increase bids on 7+ QS keywords
- [ ] Prepare for bidding strategy switch (Maximize Conversions)

---

## 6️⃣ KEY METRICS & TARGETS

| Metric | Week 1-2 | Month 1 | Month 2 | Month 3 |
|--------|----------|---------|---------|---------|
| Daily Budget | ₹400 | ₹400-500 | ₹500-700 | ₹700+ |
| Daily Clicks | 30-50 | 100-150 | 150-200 | 200+ |
| CTR | 3-5% | 6-8% | 7-9% | 8-10% |
| Conversions/Day | 3-5 | 10-15 | 20-30 | 30+ |
| Conv. Rate | 3-7% | 5-10% | 8-12% | 10%+ |
| Avg CPC | ₹8-12 | ₹6-10 | ₹5-8 | ₹4-6 |
| ROAS | 2.0-2.5x | 2.5-3.0x | 3.0-3.5x | 3.5-4.0x |

---

## 7️⃣ TROUBLESHOOTING

### Issue: Zero Impressions (After 24-48 hours)
**Cause:** Account balance exhausted, bid too low, or targeting too restrictive
**Fix:** 
1. Check billing (Tools > Billing)
2. Increase bid ceiling from ₹25 to ₹35
3. Reduce geographic exclusions temporarily
4. Check landing page quality score

### Issue: Low CTR (< 3%)
**Cause:** Poor ad copy, weak offer, or wrong targeting
**Fix:**
1. Review competitor ads
2. Add "Free Delivery" to headline
3. Increase bid to improve position
4. Test new ad copy variant

### Issue: High CPC but Low Conversions
**Cause:** Landing page mismatch, wrong audience, or product-market fit
**Fix:**
1. Review landing page (does it match ad?)
2. Add more specific keywords
3. Reduce bid, focus on efficiency
4. Check conversion pixel (might not be firing)

### Issue: Conversion Value Still ₹0.00
**Cause:** Value not set OR Shopify not passing value through pixel
**Fix:**
1. Verify value rule (Tools > Conversions > Value rules)
2. Check Shopify Web Pixels configuration
3. Test checkout page conversion tracking
4. Consider manual value import (Offline conversions)

---

## 8️⃣ SUCCESS CRITERIA

✅ **Implementation is successful when:**

1. Purchase conversion = Primary action (YES/NO: ____)
2. All 18 high-RTO states excluded (YES/NO: ____)
3. Age 27+ demographic targeting active (YES/NO: ____)
4. Merchant Center products all approved (YES/NO: ____)
5. 4 product-specific audiences created (YES/NO: ____)
6. Cart abandoner audience created (YES/NO: ____)
7. Campaign shows 50+ conversions/month (YES/NO: ____)
8. ROAS > 2.5x (YES/NO: ____)

---

**Last Updated:** May 15, 2026 at 5:30 AM IST
**Next Review:** May 18, 2026
**Owner:** Google Ads Optimization Team
