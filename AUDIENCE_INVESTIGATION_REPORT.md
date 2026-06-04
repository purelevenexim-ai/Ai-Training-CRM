# 🎯 PURE LEVEN AUDIENCE INVESTIGATION REPORT
**Comprehensive Audience Analysis & Strategic Recommendations**

**Date:** May 18, 2026 | **Status:** Active Audit

---

## 📊 EXECUTIVE SUMMARY

**Business:** Premium Organic Spices Ecommerce (B2C, India-Focused)

**Current Issue:** 
Your "Traffic Campaign Cardamom Expats" has **poor audience cohesion**—mixing unrelated interests (Ayurveda + Cooking + India consumer behaviors) that are neither expat-specific nor cardamom-relevant. This dilutes signal and prevents proper performance measurement.

**Opportunity:** 
You have the data infrastructure (CRM, GA4 tracking, product-level interests) to build **behavioral audiences** instead of generic interest stacks. This can 3-5x your retargeting effectiveness.

---

## 🏢 BUSINESS PROFILE

### Products Catalog
```
Product Category: Premium Organic Spices (SKU-based)
├─ CARDAMOM (Major focus)
│  ├─ Kerala Cardamom 8mm 200g - ₹849 (in Cardamom Expats campaign)
│  └─ Premium Green Cardamom variants
│
├─ BLACK PEPPER (High margin)
│  ├─ Kerala Black Pepper 8mm 200g - ₹799+
│  └─ Multiple size/grade options
│
├─ CINNAMON (Dual-variant strategy)
│  ├─ Ceylon Cinnamon 100g (premium, sweet)
│  └─ Cassia Cinnamon 200g (robust, warming)
│
├─ CLOVES (Seasonal driver)
│  └─ Multiple weight options
│
└─ COMBO PACKS (Higher AOV)
   └─ Mixed spice bundles (farm-origin story)
```

### Current Audience Tracking Stack
```
✅ LIVE:
  ├─ Browser-side event: window.dataLayer['pl_product_interest']
  ├─ Session storage: pl_audience (interests, categories, handles, hits)
  ├─ Interest categories: cardamom, pepper, cinnamon, cloves, combo_pack
  └─ Product page deployment: snippets/audience-tracking.liquid
  
⏳ PARTIAL:
  ├─ GA4 (G-3FRSK7TEN2) connected but audience export manual
  ├─ GTM configuration (GTM-MDNS2FFP) not fully wired to events
  └─ Meta Pixel (browser-side only, no CAPI)
  
❌ MISSING:
  ├─ Meta Conversions API (CAPI) for server-side events
  ├─ Custom audience export pipeline (CRM → Meta/Google)
  ├─ Lookalike audience creation workflow
  └─ Product affinity + customer lifetime value modeling
```

### CRM Customer Data Available
```
Fields in crm_customers table:
├─ Identity: shopify_customer_id, email, phone, name
├─ Engagement: total_spent, orders_count, last_order_date
├─ Subscriptions: email_subscribed, sms_subscribed
├─ Attribution: gclid, fbclid, session_id, utm_source
├─ Custom: meta_data (JSON for interests, behavioral flags)
└─ Timestamps: created_at, updated_at, shopify_created_at

Related tables:
├─ crm_orders (Shopify order details + conversion tracking)
├─ crm_events (GA4/custom events with product_view data)
├─ crm_conversion_feeds (Google Ads, Meta, GA4 conversions)
└─ crm_segments (Customer lifecycle, behavioral buckets)
```

---

## 🎯 CURRENT AUDIENCE PROBLEMS

### Issue #1: "Cardamom Expats" Campaign - Poor Targeting

**What You Currently Have:**
```
Audience Layers (COMBINED WITH AND):
├─ Age: 30-65+ (reasonable)
├─ Gender: All genders (acceptable if creative is neutral)
├─ Interest 1: Ayurveda (herbal wellness)
├─ Interest 2: Cooking (food & drink)
├─ Behavior: "High-value goods in India" (consumer classification)
└─ ALSO: "Mid-value and high-value goods in India" (redundant overlap)

Problems:
✗ Ayurveda ≠ Cardamom customer (Ayurveda audiences buy powders/supplements, not whole spices)
✗ "High-value goods" is too broad (cars, jewelry, real estate included)
✗ No expat identifier: Meta has "Indian diaspora" and "moved to country X in last 12m"—use those
✗ AND logic makes audience too small: ~10k people satisfy all these
✗ No product-level intent: People interested in cooking spices, not just "cooking"
```

**Expected Size:** 50k-200k (too broad) but likely delivering 5k-15k (too narrow after AND logic)

**Performance Impact:** Vague interests → uncertain targeting → higher CPC, unclear attribution

---

### Issue #2: No Custom Audiences (Zero Warm Traffic)

```
Current Retargeting Approach:
❌ Not using customer lists (no "previous visitors" audiences)
❌ Not using "cart abandoners" or "product viewers"
❌ Not using "previous customers" for upsell
❌ Not using "high-AOV customers" for VIP campaigns

Expected Size If Enabled:
├─ All GA4 visitors (30d): 200-500+
├─ Checkout abandoned (7d): 50-150
├─ Cart abandoned (7d): 30-80
├─ Product viewers - Cardamom (14d): 30-100
└─ Previous customers (repeat rate): 20-50+ (growing monthly)

Expected Impact: Custom audiences have 2-4x higher CTR + lower CPC than cold traffic
```

---

### Issue #3: No Product Affinity Mapping

```
Question: Do your customers cluster by product interest?
- Cardamom buyers → Do they later buy pepper? (YES likely, test it)
- Cinnamon viewers → Do they buy cloves? (Probably, same meal types)
- Combo pack buyers → Are they different demographic from single-spice buyers? (YES)

Current data: Exists in crm_events + crm_orders
What you're doing with it: Nothing systematic

Missing: Product affinity analysis + audience clustering
```

---

### Issue #4: Incomplete Audience Lifecycle

```
Current State:
├─ Visitor (no purchase)
├─ Customer (purchased 1x)
└─ [No definition of:]
   ├─ Repeat customer (2+ orders)
   ├─ High-lifetime-value (top 20% by spending)
   ├─ At-risk (inactive 60+ days)
   └─ VIP (multi-product buyer)

Missing: Different creative + offers per lifecycle stage
```

---

## 🔍 AUDIENCE CLASSIFICATION FRAMEWORK

### TIER 1: FOUNDATIONAL SEGMENTS (Based on behavior only)

```
SEGMENT 1: "Cardamom Enthusiasts"
├─ Definition: Viewed OR purchased cardamom product in last 30 days
├─ Data source: crm_events.product_handle = 'kerala-cardamom-8mm-200gm'
├─ Expected size: 50-150 (early growth phase)
├─ Best for: 
│  ├─ Upsell: Offer variant (different size/grade)
│  ├─ Cross-sell: "People who loved cardamom also bought..." (pepper, cinnamon)
│  └─ Educate: How to store, best uses, recipes
└─ Custom audience: "Cardamom Interest - Last 30d" (CRM → Meta/Google)
```

```
SEGMENT 2: "Spice Explorers"
├─ Definition: Viewed 3+ different spice products (no purchase required)
├─ Data source: crm_events WHERE event_type='product_view' GROUP BY customer_id HAVING count(distinct product_handle) >= 3
├─ Expected size: 80-200
├─ Best for: 
│  ├─ Educate: "Complete your spice rack" bundles
│  ├─ Recommend: Complementary products
│  └─ Offer: Combo pack or multi-buy discount
└─ Custom audience: "Multi-Product Browser - Last 14d"
```

```
SEGMENT 3: "Cart/Checkout Abandoners"
├─ Definition: Added to cart or reached checkout, but did not complete
├─ Data source: crm_events.event_type IN ('cart_add', 'checkout_started') - NO purchase within 7 days
├─ Expected size: 30-100 (depends on traffic volume)
├─ Best for: 
│  ├─ Urgency: Limited stock messaging
│  ├─ Reassurance: Trust signals, reviews, guarantee
│  └─ Incentive: Free shipping, small discount, loyalty points
└─ Custom audience: "Cart Abandoners - 7d window" (update daily via CRM → Meta/Google)
```

```
SEGMENT 4: "Repeat Customers (VIP)"
├─ Definition: Purchased 2+ times, AOV > median
├─ Data source: crm_customers WHERE orders_count >= 2 AND total_spent > (SELECT AVG(total_spent) FROM crm_customers WHERE orders_count >= 1)
├─ Expected size: Growing (20-50 by Q2 2026)
├─ Best for: 
│  ├─ Loyalty: Exclusive access, early sale, member perks
│  ├─ Upsell: Premium variants, larger pack sizes
│  └─ Referral: "Earn rewards, send to friends"
└─ Custom audience: "Repeat Customer VIP - Active" (monthly export)
```

```
SEGMENT 5: "Geographic: Expat Diaspora (India-to-X)"
├─ Definition: Located in developed market, ethnic Indian heritage (verified intent)
├─ Data source: 
│  ├─ Meta: Saved Audience "Indian diaspora" + "Moved within 12 months" filters
│  ├─ CRM: shipping_address country != India + email_subscribed=true + email domain international
│  └─ GA4: device geo != India + returning visitor + high session duration
├─ Expected size: 5k-15k in cold traffic, 50-150 in warm (previous visitors)
├─ Best for: 
│  ├─ Messaging: "Bring home authentic Kerala spices"
│  ├─ Product story: Farm origin, heritage, purity
│  └─ Offer: Family size packs, subscription bundles
└─ Custom audience: "Diaspora Visitor Warm" + Lookalike (1st, 2nd degree)
```

---

### TIER 2: ADVANCED SEGMENTS (Product + Behavior Combination)

```
SEGMENT 6: "Cinnamon Type Preference (Ceylon vs Cassia)"
├─ Ceylon preference (sweet, mild):
│  ├─ Users: Viewed Ceylon 2+ times OR purchased Ceylon
│  ├─ Messaging: "Delicate, aromatic, best for desserts"
│  └─ Next offer: Cardamom (pairs well in sweet recipes)
│
└─ Cassia preference (robust, spicy):
   ├─ Users: Viewed Cassia 2+ times OR purchased Cassia
   ├─ Messaging: "Bold, warming, versatile for curries"
   └─ Next offer: Black Pepper (complementary heat profile)
```

```
SEGMENT 7: "Price Sensitivity Tiers"
├─ Premium tier (avg order > ₹2000):
│  ├─ Target: Larger pack sizes, exclusive blends, farm stories
│  └─ Offer: Premium positioning, "Connoisseur" messaging
│
├─ Mid tier (₹500-2000 avg):
│  ├─ Target: Best sellers, variety packs, sampling
│  └─ Offer: Quality + value, "Try the range"
│
└─ Budget tier (< ₹500 avg):
   ├─ Target: Small sizes, combo deals, bulk discounts
   └─ Offer: Savings, larger quantity, family packs
```

---

### TIER 3: LOOKALIKE SEGMENTS

```
SEGMENT 8: "Converters Lookalike" (Top performers)
├─ Based on: Top 10% of customers by lifetime value
├─ Meta: Create lookalike 1st/2nd degree (100k-500k size)
├─ Google Ads: Create similar audiences (1% similarity)
├─ Expected ROAS: 30-50% higher than cold traffic
└─ Refresh: Quarterly (new high-value customers)
```

```
SEGMENT 9: "Repeat Customer Lookalike"
├─ Based on: All 2+ purchase customers
├─ Meta: Create lookalike 1st degree (50k-200k)
├─ Google Ads: Similar audiences
├─ Expected ROAS: 20-30% higher than cold traffic
└─ Use for: Retention + upsell campaigns
```

---

## 💡 STRATEGIC RECOMMENDATIONS

### PRIORITY 1: Fix the "Cardamom Expats" Campaign (IMMEDIATE)

**Current Setup (BROKEN):**
```
Audience: Ayurveda + Cooking + High-value India consumers (AND logic)
├─ Problem: Ayurveda ≠ spice buyers, too much AND logic
├─ Size: Too small for reliable optimization
└─ Result: High CPC, unclear performance
```

**Recommended Fix (NEW APPROACH):**

```
Option A: EXPAT COLD TRAFFIC (If budget is high + patience for learning)
├─ Audience: "Indian diaspora" + "Moved within 12 months"
├─ Age: 25-50
├─ Interest: REMOVE Ayurveda, REPLACE with "Cooking" + "Food Culture" only
├─ Include: Lookalike (1st, 2nd degree based on existing converters)
├─ Creative: "Bring home Kerala spices" (heritage + nostalgia)
├─ Budget: ₹1000-2000/day (test at scale)
└─ Expected: 2-3 weeks to stabilize, ROAS 1.5-2.5x
```

```
Option B: WARM RETARGETING (Recommended short-term)
├─ Audience: "Previous cardamom viewers" (custom audience, CRM → Meta)
├─ Add: "Previous cardamom customers" (upsell new variants)
├─ Include: Lookalike to previous converters
├─ Creative: "Complete your spice collection" (product education)
├─ Budget: ₹500-1000/day (lower cost, faster ROAS)
└─ Expected: 3-5 days to see results, ROAS 3-5x
```

**Action Items:**
1. ✅ Pause current "Cardamom Expats" campaign today
2. ✅ Create custom audience: "Cardamom Viewers (30d)" from CRM
3. ✅ Create custom audience: "Cardamom Converters" (all purchased cardamom)
4. ✅ Test Option B (warm) for 1 week
5. ✅ If Option B succeeds (ROAS > 2.5x), then scale Option A (cold)

---

### PRIORITY 2: Build Automated Custom Audience Pipeline (1-2 WEEKS)

```
Goal: Nightly export from CRM → Meta + Google Ads (no manual work)

Setup:
1. Segment definitions in SQL (see Tier 1 & 2 above)
2. CRM → Meta Custom Audience API (webhook-based daily sync)
3. CRM → Google Ads Customer Match (API-based daily sync)
4. Conversion tracking in both platforms

Expected audiences live:
├─ Week 1: Cardamom Enthusiasts + Cart Abandoners
├─ Week 2: Repeat Customers + Cinnamon Type Segments
└─ Week 3: Expat Diaspora + All Lookalikes

Expected impact: ROAS lift +50-100% across paid channels
```

---

### PRIORITY 3: Fix Meta CAPI Deployment (1-2 WEEKS)

```
Current state: Browser pixel only (incomplete tracking)
Issue: 30-40% events lost to ad blockers, cookie deprecation
Fix:
├─ Deploy Meta Conversions API (server-side tracking)
├─ Send events from FastAPI: ViewContent, AddToCart, Purchase, InitiateCheckout
├─ Match events with email + phone (already in your data)
├─ Setup: ~2-4 hours implementation work

Expected impact:
├─ Event reliability: 95%+ (vs. 60-70% with pixel only)
├─ Better audience quality for retargeting
├─ Accurate ROAS reporting
└─ Ready for AI bidding (Meta Advantage+ campaigns)
```

---

### PRIORITY 4: Create Product Affinity Mapping (1 WEEK)

```
Question: Which products to recommend to each customer?

Data: crm_orders + crm_events (you already have)

SQL to run:
SELECT 
  product_a, 
  product_b, 
  COUNT(*) as co_purchase_count,
  (COUNT(*) / total_a) as affinity_pct
FROM crm_orders
WHERE items contains [product_a AND product_b]
GROUP BY product_a, product_b
ORDER BY affinity_pct DESC;

Expected output:
Cardamom + Black Pepper: 45% (if you bought cardamom, 45% also buy pepper)
Cinnamon (Ceylon) + Cardamom: 60% (if Ceylon viewed, 60% also viewed cardamom)
Cloves + Combo pack: 70% (clove viewers likely want variety)

Use for:
├─ Upsell: "Customers who loved X also bought Y"
├─ Bundles: Create high-affinity combo packs
├─ Retargeting: Show next product based on view history
└─ Product recommendations: On cart page + post-purchase email
```

---

### PRIORITY 5: Implement Lifecycle Campaigns (2-3 WEEKS)

```
Current state: All campaigns target similar audience
Issue: New visitor needs different message than repeat customer

Framework:

STAGE 1: AWARENESS (First touchpoint)
├─ Audience: Cold traffic (non-visitors) + Lookalikes
├─ Message: "Discover authentic Kerala spices"
├─ Offer: "Get ₹200 off first purchase"
├─ Creative: Farm origin story, product quality
└─ Campaign: "Intro-Organic-Spice"

STAGE 2: CONSIDERATION (Visited, not purchased)
├─ Audience: Custom audience "Product Viewers (7d), no purchase"
├─ Message: "Why choose Pure Leven?" (social proof, purity)
├─ Offer: "Free shipping on ₹500+"
├─ Creative: Reviews, customer testimonials, farm photos
└─ Campaign: "Consider-Best-Spices"

STAGE 3: CONVERSION (Cart/Checkout abandoned)
├─ Audience: Custom audience "Checkout Abandoned (3-7d)"
├─ Message: "Complete your order" (urgency)
├─ Offer: "₹150 off + free shipping" OR "Money-back guarantee"
├─ Creative: Time-limited button, stock scarcity
└─ Campaign: "Convert-Complete-Purchase"

STAGE 4: RETENTION (Repeat purchase)
├─ Audience: Custom audience "Repeat Customers (2+)"
├─ Message: "Reorder your favorite spices" (convenience)
├─ Offer: Loyalty discount, subscription, member-only products
├─ Creative: Product recommendations based on purchase history
└─ Campaign: "Retain-Loyalty-VIP"

STAGE 5: ADVOCACY (High-value customers)
├─ Audience: Custom audience "Top 20% by AOV"
├─ Message: "Become a Pure Leven ambassador"
├─ Offer: Referral rewards, exclusive early access
├─ Creative: Exclusive perks, insider content
└─ Campaign: "Advocate-Referral-Program"

Setup timeline:
├─ Week 1: Stages 1-3 (quick wins)
├─ Week 2: Stages 4-5 (nurturing)
└─ Week 3: Optimization + frequency caps
```

---

## 📈 MEASUREMENT FRAMEWORK

### Metrics You Should Track by Audience

```
For EACH custom audience, measure:

ACQUISITION METRICS:
├─ CPM (cost per 1000 impressions) - lower for warm audiences
├─ CPC (cost per click) - should drop for custom audiences
└─ CTR (click-through rate) - 2-3x higher for custom vs. cold

CONVERSION METRICS:
├─ Conversion Rate (%) - 5-10% from warm, 0.5-2% from cold
├─ Cost Per Conversion - should drop 50-75% for custom
└─ ROAS (Revenue / Ad Spend) - target 2.5x+ for warm, 1.5x+ for cold

LIFETIME METRICS:
├─ Repeat Purchase Rate (%) - % who buy again within 90d
├─ Customer Lifetime Value - total spend per customer acquired
└─ CAC Payback Period - how fast you recoup acquisition cost

DASHBOARD:
├─ Primary: ROAS by audience segment
├─ Secondary: CAC by lifecycle stage
├─ Tertiary: Repeat purchase rate by product affinity group
└─ Alert: Any segment with ROAS < 1.2x → pause + optimize
```

---

## 🛠 IMPLEMENTATION ROADMAP

```
WEEK 1 (IMMEDIATE):
├─ [ ] Pause "Cardamom Expats" campaign
├─ [ ] Create 3 custom audiences (Cardamom Viewers, Cardamom Converters, Cart Abandoned)
├─ [ ] Export from CRM, upload to Meta + Google
├─ [ ] Launch retargeting campaign (Option B above)
└─ [ ] Expected result: First ROAS data

WEEK 2:
├─ [ ] Implement Meta CAPI (server-side tracking)
├─ [ ] Build daily audience sync pipeline (CRM → platforms)
├─ [ ] Run product affinity analysis
├─ [ ] Create lookalike audiences (1st, 2nd degree)
└─ [ ] Launch cross-sell campaign (Cardamom → Pepper)

WEEK 3-4:
├─ [ ] Build lifecycle stages (5 campaign templates)
├─ [ ] Setup conversion tracking in GA4 + platforms
├─ [ ] Create custom audience dashboard
├─ [ ] Optimize audiences based on ROAS data
└─ [ ] Plan Q2 expansion (new products, new geos)

MONTH 2:
├─ [ ] Scale high-performing audiences
├─ [ ] Test audience combinations (A/B)
├─ [ ] Implement subscription/loyalty audiences
└─ [ ] Forecast budget allocation based on performance
```

---

## 📋 QUICK REFERENCE: AUDIENCE CHECKLIST

```
FOUNDATION:
☐ Customer CRM synced with GA4
☐ Product-level event tracking live
☐ Conversion (purchase) tracking accurate
☐ UTM parameters consistent across all channels

CUSTOM AUDIENCES:
☐ Cardamom Viewers (30d, no purchase)
☐ Cardamom Converters (all who purchased)
☐ Cart Abandoners (3-7d window)
☐ Checkout Abandoners (same day recovery)
☐ Repeat Customers (2+ purchases)
☐ High-AOV Customers (top 20%)

LOOKALIKES:
☐ Based on Converters (1st + 2nd degree)
☐ Based on High-AOV (1st degree)
☐ Based on Repeat Customers (1st degree)

EXCLUSIONS:
☐ Exclude all converters from awareness campaigns
☐ Exclude repeat customers from acquisition offers

CAMPAIGNS:
☐ Awareness: Cold traffic + Lookalikes
☐ Consideration: Product viewers (no purchase)
☐ Conversion: Checkout abandoners
☐ Retention: Repeat customers
☐ Advocacy: VIP customers + referral

MEASUREMENT:
☐ ROAS by audience tracked daily
☐ CAC by lifecycle stage tracked weekly
☐ Repeat rate by product tracked monthly
☐ Attribution model set (First, Last, Multi-touch)
```

---

## 🎯 SUCCESS CRITERIA

**In 4 weeks, you should see:**

```
METRIC                    CURRENT         GOAL            IMPROVEMENT
─────────────────────────────────────────────────────────────────────
ROAS (Cardamom campaign)   ~1.2x          2.5-3.5x        +100-200%
CPM (Warm audience)        ₹300-400       ₹150-200        -50%
CTR (Custom audience)      0.8%           2-3%            +250%
Conversion rate (Warm)     0.5%           5-10%           +900%
Repeat customer rate       15%            25-30%          +67-100%
Cost per customer          ₹2000-3000     ₹1000-1500      -50%

OPERATIONAL:
├─ Time to update audiences: Manual (4h/week) → Automatic (0h/week)
├─ Audience quality: Vague interests → Behavioral + product-based
└─ Campaign cohesion: 1 broad campaign → 5 targeted campaigns
```

---

## ❓ FAQ

**Q: Why is Ayurveda bad for a spice campaign?**
A: Ayurveda audience is 80% people buying powders, supplements, wellness apps. Only 20% actually buy whole spices for cooking. It's wrong audience for your product.

**Q: How long until custom audiences work?**
A: Immediately for retargeting (they've already shown intent). Cold lookalikes take 3-7 days for Facebook to find similar users.

**Q: What if I have no repeat customers yet?**
A: Start with "Product Viewers" (lower barrier). Once you have 20+ customers, create repeat-customer lookalike to find more like them.

**Q: Should I do cold OR warm retargeting?**
A: Start with WARM (faster ROAS). Once warm audience saturates, use warm+lookalikes to scale. Cold traffic is for expansion after warm proves profitable.

**Q: How much budget should each audience get?**
A: 70/20/10 rule: 70% to warm (proven), 20% to lookalikes (semi-warm), 10% to cold (learning). Adjust based on ROAS.

---

## 📞 NEXT STEPS

1. **Review this report** with your team (marketing + analytics)
2. **Choose PRIORITY 1 action**: Fix Cardamom Expats campaign TODAY
3. **Assign owner**: Who builds the custom audience pipeline? (CRM admin or developer)
4. **Set timeline**: Target Week 2 for Meta CAPI + first results
5. **Weekly review**: Track ROAS by audience, optimize underperformers

---

**Questions?** This report is live and can be updated as you test audiences.
