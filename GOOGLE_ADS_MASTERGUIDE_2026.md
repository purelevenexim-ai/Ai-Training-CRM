# 🏆 GOOGLE ADS MASTER GUIDE — STOP LEAKING MONEY & SCALE PROFITABLY
**Research Date:** May 15, 2026 | **Account:** Pureleven (AW-10965185406) | **Market:** India eCommerce

> **The #1 rule:** Google Ads doesn't waste your money. Wrong settings do. This guide covers every lever that controls traffic quality, budget efficiency, and scaling readiness.

---

## TABLE OF CONTENTS
1. [The Budget Leak Map — Where Money Disappears](#1-budget-leak-map)
2. [Account-Level Setup](#2-account-level-setup)
3. [Conversion Tracking — The Foundation](#3-conversion-tracking)
4. [Campaign Structure](#4-campaign-structure)
5. [Keyword Strategy — Full Playbook](#5-keyword-strategy)
6. [Negative Keywords — The Profit Firewall](#6-negative-keywords)
7. [Bidding Strategy — Phase by Phase](#7-bidding-strategy)
8. [Audience Targeting & Exclusions](#8-audience-targeting)
9. [Geographic Targeting](#9-geographic-targeting)
10. [Ad Copy & Quality Score](#10-ad-copy--quality-score)
11. [Landing Pages — The Conversion Gate](#11-landing-pages)
12. [Assets (Extensions)](#12-assets-extensions)
13. [Search Terms Report — Weekly Routine](#13-search-terms-report)
14. [Reporting & KPI Dashboard](#14-reporting--kpi-dashboard)
15. [Performance Max Settings](#15-performance-max-settings)
16. [Shopping / Merchant Center](#16-shopping--merchant-center)
17. [Scaling Playbook — Phase 1 → 3](#17-scaling-playbook)
18. [Pureleven Account Action Plan](#18-pureleven-specific-action-plan)

---

## 1. BUDGET LEAK MAP

> These are the most common ways Google Ads drains budget on worthless traffic. Audit each one.

### 🔴 HIGH-RISK LEAK POINTS

| Leak Source | How It Wastes Budget | Fix |
|---|---|---|
| **Display Network ON** in Search campaign | Sends budget to banner ads, YouTube, apps — zero purchase intent | Turn OFF immediately |
| **Broad Match without negatives** | Matches completely irrelevant queries | Use Exact/Phrase only until 50+ conversions |
| **"Presence OR Interest" location targeting** | Shows ads to people *researching* your target area, not *in* it | Switch to "Presence only" |
| **Wrong conversion optimization signal** | Smart bidding optimizes for page views / form fills, not purchases | Set Purchase as ONLY primary conversion |
| **Conversion value = ₹0** | Maximize Conversion Value has no signal to optimize toward | Set dynamic value or ₹800 static |
| **Auto-apply recommendations ON** | Google adds broad match, increases budget, expands targeting | Disable all auto-apply |
| **Optimized Targeting ON** | Overrides audience settings — shows to anyone Google thinks might buy | Turn OFF in Search campaigns |
| **Search Partners ON too early** | Partners can include low-quality sites, search engines with bot traffic | Disable until ROAS is proven |
| **Performance Max without data** | PMax guesses everything without training data | Launch last, not first |
| **DSA (Dynamic Search Ads)** | Matches ad to any page on your site, often irrelevant | Don't use until account is mature |
| **Tablet device targeting** | Tablets have worst conversion rate, worst click fraud rate | Reduce bid -100% after data |
| **No audience exclusions** | Shows to people who already bought, or known non-converters | Exclude past purchasers from cold campaigns |
| **Fragmented micro-budgets** | ₹200/day campaigns can't collect enough data for ML | Consolidate: fewer campaigns, higher budgets |
| **No negative keyword lists** | Wastes budget on jobs, recipes, wholesale, DIY queries | Build 5 shared negative lists immediately |

---

## 2. ACCOUNT-LEVEL SETUP

### A. Auto-Apply Recommendations — TURN OFF
**Path:** Tools → Recommendations → Auto-apply

**Disable ALL of these:**
```
✗ Broad match keyword upgrades
✗ Keyword expansions / additions
✗ Budget increases
✗ Target CPA / ROAS auto-changes
✗ Dynamic search ad additions
✗ Display expansion
✗ Responsive search ad auto-creation
✗ Callout / asset suggestions being applied
```
**Keep enabled (safe):**
```
✓ Fix broken ads (policy compliance)
✓ Fix tracking issues
✓ Critical billing alerts
```
**Why:** Google's "recommendations" optimize for Google's revenue metrics (more clicks, more spend, wider reach). Your goal is profit, not impressions. These two are often in conflict.

---

### B. Account-Level Negative Keyword Lists
**Path:** Tools → Shared Library → Negative keyword lists

**Create 5 lists and apply campaign-wide:**

**List 1 — "Research & Information Traffic"**
```
recipe, recipes, uses of, uses for, benefits of, health benefits, 
side effects, history of, origin of, meaning of, what is, how does, 
wiki, wikipedia, youtube, video, images, photos, wallpaper, pictures
```

**List 2 — "DIY & Cultivation Traffic"**
```
how to grow, how to plant, how to make, homemade, diy, plant, 
tree, seed, seedling, seeds, cultivation, farming, agriculture, 
nursery, compost, soil, garden, sow
```

**List 3 — "Jobs & Business Traffic"**
```
jobs, job, careers, career, vacancy, vacancies, salary, 
distributor, distributors, wholesale, bulk, manufacturer, 
exporter, importer, supplier, franchise, dealer, reseller,
minimum order quantity, moq
```

**List 4 — "Free & Low-Cost Seekers"**
```
free, cheapest, cheap, low cost, discount, free sample, 
promo code, coupon, comparison, vs, versus, alternative to,
cheap alternative
```

**List 5 — "Competitors & Irrelevant Brands"**
```
amazon, flipkart, bigbasket, jiomart, blinkit, zepto, 
swiggy instamart, dunzo, grofers, myntra, meesho
```

---

### C. Attribution Settings
**Path:** Tools → Measurement → Attribution

**Recommended:** Data-Driven Attribution (DDA)
- Google uses ML to distribute credit across all touchpoints in the conversion path
- Requires minimum 300 conversions + 3,000 clicks per month to qualify
- If below threshold → use **Position-Based** (40% first, 40% last, 20% middle)
- **Avoid:** Last Click — punishes upper-funnel touchpoints, leads to under-bidding on discovery keywords

**Official guidance:** Google recommends data-driven attribution for accounts meeting volume thresholds (support.google.com/google-ads/answer/6259715).

---

### D. Campaign Naming Convention
**Recommended format:**
```
[Type]_[MatchType]_[ProductGroup]_[Market]_[Goal]_[Date]

Examples:
Search_Exact_BlackPepper_India_Purchase_May2026
Search_Exact_KeralaSpices_India_Purchase_May2026
PMax_Spices_India_ROAS_May2026
Brand_Exact_Pureleven_India_Protect_May2026
RLSA_Remarketing_AllProducts_India_Purchase_May2026
```
**Why:** When you have 10+ campaigns, naming convention is how you stay sane. Filter/sort by type, product, or date instantly.

---

## 3. CONVERSION TRACKING

> **This is the single most important thing in your entire account.** If conversion tracking is wrong, every optimization decision is wrong.

### A. Conversion Action Priority

**PRIMARY Conversion (used for bidding optimization):**
```
✅ Purchase — the actual order completion
```

**SECONDARY Conversions (observation only, never for bidding):**
```
📊 Add to Cart (insight signal only)
📊 Begin Checkout (insight signal only)
📊 WhatsApp click (intent signal)
📊 Page view / scroll (engagement — DO NOT set as primary)
```

**Path to set:**
- Goals → Conversions → [action name] → Edit → "Optimization" → select "Primary action" or "Secondary action (don't use for bidding)"

---

### B. Conversion Value Setup

**Your account issue:** Conversion value = ₹0 (meaning Maximize Conversion Value strategy has ZERO signal)

**Fix — Option A: Dynamic Value (BEST)**
- Shopify already sends `transaction_id` and `value` via the purchase event
- In Shopify Admin → Online Store → Preferences → Google Analytics / Google Ads
- Verify the purchase event sends `value` parameter with order total
- In Google Ads: Goals → Conversions → Purchase → Edit → Value: "Use a different value for each conversion"
- This enables ROAS calculation and smart bidding to optimize for revenue

**Fix — Option B: Static Value (Quick)**
- Value: ₹800 (your average order value)
- Currency: INR
- Use this as fallback if dynamic isn't working

**Verification:**
```
After 2-3 purchases, check:
Goals → Conversions → Summary → "Conv. value" column
If it shows ₹800 or actual order values — working ✅
If it shows ₹0 — still broken ❌
```

---

### C. Enhanced Conversions
**Path:** Goals → Conversions → Settings → Enhanced conversions → Turn ON

**What it does:** Matches hashed customer data (email, phone, name) to signed-in Google accounts. Recovers conversions that would otherwise be lost due to:
- iOS privacy restrictions
- Ad blockers
- Cross-device journeys (desktop search → mobile purchase)

**Impact:** Typically recovers 10–25% of lost conversions. Especially important for Indian mobile users.

**Implementation via Shopify:** Already active per your account ✅ — verify it shows "Active" status.

---

### D. Conversion Windows

| Conversion Type | Recommended Window |
|---|---|
| Purchase (Search) | 30 days |
| Purchase (Display) | 7 days |
| Add to Cart | 7 days |
| Begin Checkout | 7 days |
| WhatsApp Click | 1 day |

**Why shorter for Display/WhatsApp:** These are impulse signals; if someone doesn't buy within 7 days of a WhatsApp click, they won't.

---

### E. Tag Verification
**Quick check:**
1. Install Google Tag Assistant Chrome extension
2. Visit pureleven.com
3. Confirm `AW-10965185406` fires on every page
4. Complete a test purchase (or use Tag Assistant Recording)
5. Verify `conversion_event_purchase` fires on thank-you page with `value` and `transaction_id`

---

## 4. CAMPAIGN STRUCTURE

### The Right Structure for Pureleven (Phase 1)

```
ACCOUNT: AW-10965185406
│
├── CAMPAIGN 1: Brand Protection
│   └── Ad Group: Pureleven Brand
│       Keywords: [pureleven], [pure leven], [pureleven.com], [organic pure leven]
│       Budget: ₹100/day | Bidding: Max Clicks + ₹5 cap
│       Purpose: Protect your brand from competitors; cheapest conversions
│
├── CAMPAIGN 2: High-Intent Exact Match (MAIN REVENUE DRIVER)
│   ├── Ad Group 1: Kerala Spices
│   │   Keywords: [kerala spices online], [buy kerala spices], [kerala masala online]
│   ├── Ad Group 2: Black Pepper
│   │   Keywords: [kerala black pepper online], [black pepper online], [buy black pepper online]
│   ├── Ad Group 3: Cardamom
│   │   Keywords: [cardamom online], [kerala cardamom online], [elaichi buy online]
│   ├── Ad Group 4: Cinnamon
│   │   Keywords: [ceylon cinnamon online], [cinnamon sticks online], [dalchini online]
│   ├── Ad Group 5: Cloves
│   │   Keywords: [cloves online], [whole cloves online], [laung online]
│   └── Ad Group 6: Generic Spices
│       Keywords: [spices online], [organic spices online], [buy spices online]
│   Budget: ₹400/day | Bidding: Max Clicks (start) → Max Conversions (50+ conv.)
│
├── CAMPAIGN 3: Remarketing (after 2+ weeks)
│   └── Ad Group: Cart Abandoners + Visitors
│       Audience: Past visitors (7 days), cart abandoners (30 days)
│       Budget: ₹100/day
│
└── CAMPAIGN 4: Performance Max (after Phase 2)
    Asset Groups by product category
    Budget: ₹300/day
```

**Key structural rules:**
- One theme per ad group (single product/category)
- Matching keyword → ad copy → landing page = higher Quality Score
- Never mix unrelated products in same ad group
- Keep brand campaign separate from non-brand (so you can measure true acquisition cost)

---

### Campaign Settings Checklist

**For EVERY Search Campaign:**
```
Networks:
  ✅ Google Search Network
  ✗ Display Network (OFF)
  ✗ Search Partners (OFF initially — turn on after 30 days if ROAS stable)

Location targeting:
  ✅ "Presence: People in your targeted locations" (NOT presence OR interest)
  Target: India (metro/tier-1 cities initially if budget <₹500/day)

Language:
  ✅ English
  ✅ Hindi (major buyer segment)

Bidding:
  Phase 1: Manual CPC or Maximize Clicks (bid ceiling ₹25)
  Phase 2 (50+ conv.): Maximize Conversions
  Phase 3 (stable ROAS): Target ROAS 300%

Device:
  Keep all enabled. Collect data for 4+ weeks, then adjust.

Ad Schedule:
  Start: All day, 7 days
  After data: Check conversion hours, reduce low-conversion overnight hours

Rotation:
  ✅ Optimize (prefer best-performing ads)
  ✗ Rotate indefinitely (old, less effective)
```

---

## 5. KEYWORD STRATEGY

### A. Match Type Hierarchy (2026 Reality)

| Match Type | Behavior | When to Use |
|---|---|---|
| **[Exact]** | Matches exact phrase + close variants | Phase 1 — your control core |
| **"Phrase"** | Matches phrase + additional words before/after | Phase 1 — expand with some control |
| **Broad** | Matches anything semantically related | Phase 3 only — requires Smart Bidding + 50+ conversions + strong negatives |

**Important 2026 note:** Google has been expanding "close variants" for all match types. Exact match now includes:
- Plurals
- Misspellings
- Abbreviations
- Reordered words with same meaning
- Function words added/removed

Example: [kerala black pepper online] can now match "black pepper kerala buy online" and "kerala pepper online buy"

**Recommendation for Pureleven:**
- Start 70% Exact, 30% Phrase
- Add Broad ONLY after consistently positive ROAS with smart bidding

---

### B. Keyword Research Framework

**Step 1: Seed keywords (you already have these)**
```
Category-level: kerala spices, black pepper online, cardamom online
Product-level: kerala black pepper 200gm, elaichi pods, ceylon cinnamon sticks
Intent-level: buy [product] online, [product] home delivery, order [product]
Hindi variants: kali mirch online, elaichi kharide, dalchini price
```

**Step 2: Expand with Google Tools**
- Keyword Planner (Tools → Planning → Keyword Planner)
- Search Terms Report (after 2+ weeks live)
- Competitor analysis via Auction Insights

**Step 3: Intent Classification**
```
🟢 BUY NOW (Highest Priority):
   buy [product] online, [product] online, order [product] online,
   [product] home delivery, [product] online india

🟡 COMPARISON (Retarget Later):
   best [product] brand, [product] vs [product], top [product] india,
   [product] review, which [product] to buy

🔴 RESEARCH (Exclude):
   benefits of [product], how to use [product], [product] recipe,
   what is [product], [product] cultivation
```

**Step 4: Hindi/Regional Variants (India-Specific)**
```
Cardamom: elaichi, elaichi online, hari elaichi, badi elaichi, 
          choti elaichi, moti elaichi kharidna
Black Pepper: kali mirch, kali mirchi online, gol mirch
Cinnamon: dalchini, dalchini online, tejpatta
Cloves: laung, lavang, laung online kharidna
Ginger: adrak, adrak powder
Turmeric: haldi, turmeric online
```

---

### C. Quality Score Optimization
Quality Score (1–10) is a diagnostic showing: Expected CTR + Ad Relevance + Landing Page Experience

**Target score: 7+**

**How to improve each component:**
```
Expected CTR (most important):
  - Write compelling, keyword-relevant headlines
  - Use the keyword in Headline 1
  - Use emotional triggers: "Direct from Kerala Farms"
  - Include price/offer: "Starting ₹299"
  
Ad Relevance:
  - Each ad group: single theme, tightly related keywords
  - Headline mirrors the keyword exactly
  - Description expands on what headline promises
  
Landing Page Experience:
  - Keyword → Landing page content must match
  - "buy black pepper online" → black pepper product page (NOT homepage)
  - Fast load time (<3 seconds on mobile)
  - Clear purchase path (buy button visible above fold)
  - Mobile-optimized (60%+ of Indian traffic is mobile)
```

**Higher Quality Score = lower CPC for same position.** A QS 8 keyword can outrank QS 5 at 40% lower bid.

---

## 6. NEGATIVE KEYWORDS — THE PROFIT FIREWALL

> Negative keywords are worth more than positive keywords in a new account. You're carving away waste to reveal the signal.

### A. Account-Level vs Campaign-Level vs Ad Group Level

| Level | Use For |
|---|---|
| Account | Universal waste: jobs, free, recipe, wiki, images |
| Campaign | Campaign-specific waste: if black pepper campaign, negate "cardamom" |
| Ad Group | Inter-ad group negatives: prevent keyword cannibalization |

### B. Negative Keyword Process (Weekly)

**Every week for first 3 months:**
1. Reports → Search terms (set date: last 7 days)
2. Sort by "Cost" descending
3. Look at every term that cost >₹50 with 0 conversions
4. Ask: "Would someone using this query buy from pureleven.com?" → No → Add negative
5. Look at every converting term → promote to exact match keyword
6. Export all negatives → maintain master list in this document

**Search Term Categories to Negatives:**

```
Information seekers:
  "benefits of", "side effects of", "uses of", "how to", "why is", "what is"
  
Price researchers without intent:
  "price list", "rate per kg", "market price", "mandi rate", "wholesale price"
  
Location-specific (if not serviceable):
  Any city/state you can't ship to profitably
  
Recipe/cooking context:
  "recipe", "cooking", "dish", "masala recipe", "how much to add"
  
Medical/health context (unless you sell medicinal):
  "medicine", "treatment", "cure", "dosage", "mg", "ayurvedic medicine"
  
Educational:
  "essay", "project", "notes", "class", "school", "college"
```

### C. Cross-Campaign Negation (Prevent Cannibalization)

**Example:** If someone searches "kerala black pepper online":
- You want this to go to your Black Pepper ad group
- NOT to your Kerala Spices general ad group (which would have a less relevant ad)

**Solution:** In Kerala Spices ad group, add negative keywords for specific product searches:
```
Kerala Spices ad group negatives:
  -black pepper, -cardamom, -cinnamon, -cloves, -elaichi, -laung, -dalchini
  
(This forces specific product searches to their dedicated ad groups)
```

### D. Master Negative Keyword List for Spices eCommerce

```
=== CATEGORY: RESEARCH/INFORMATION ===
recipe, recipes, cooking, how to use, uses for, benefits, health benefits,
side effects, nutritional value, nutrition, calories, antioxidants,
medicinal uses, home remedy, home remedies, ayurveda, traditional,
origin, history, wikipedia, wiki, meaning, definition

=== CATEGORY: DIY/CULTIVATION ===
how to grow, plant, planting, seeds, seedling, nursery, cultivation,
farming, harvest, extract, homemade, diy, make at home

=== CATEGORY: WHOLESALE/B2B ===
wholesale, bulk, distributor, manufacturer, supplier, exporter,
minimum order, moq, trader, merchant, import, export

=== CATEGORY: JOBS ===
job, jobs, career, vacancy, employment, salary, hiring, apply

=== CATEGORY: FREE/CHEAP ===
free, free sample, promo, coupon code, comparison, vs, versus, 
alternative, substitute, replacement, similar to

=== CATEGORY: COMPETITORS (IF DESIRED) ===
amazon, flipkart, bigbasket, jiomart, blinkit, zepto, grofers

=== CATEGORY: IRRELEVANT PRODUCTS ===
essential oil, perfume, cologne, aromatherapy, candle, soap, shampoo,
(add anything non-food that matches your product names)
```

---

## 7. BIDDING STRATEGY — PHASE BY PHASE

> **Official Google guidance:** Measure performance over periods with at least 30 conversions. Use Target ROAS only after 50+ conversions per month per campaign. (support.google.com/google-ads/answer/7065882)

### Phase 1: Data Collection (Month 1)
**Goal:** Collect 50+ conversions. Budget: ₹400/day

**Strategy:** Maximize Clicks + CPC Cap
```
Setting:
  Bidding: Maximize Clicks
  Maximum CPC bid limit: ₹20-25
  
Why CPC cap?
  Without cap, Google may bid ₹50-80/click chasing rare high-value clicks
  Cap keeps budget sustainable while gathering data
  
Review weekly:
  If avg CPC stays below ₹15, raise cap to ₹30
  If running out of budget daily before ad schedule ends, raise cap → more clicks
  If burning through budget too fast, lower cap
```

**Alternative for very tight budgets:** Manual CPC
- Full control, but requires manual adjustment
- Set bid for each ad group: ₹12–20 depending on competition
- Increase by 20% for high-performing keywords, decrease for poor CTR

### Phase 2: Optimize for Conversions (Month 2–3)
**Trigger:** 50+ conversions in last 30 days

**Switch to:** Maximize Conversions (no target initially)
```
Why no target immediately?
  Smart bidding needs ~2 weeks "learning period" 
  Adding a ROAS/CPA target restricts learning
  Let it run unconstrained for 2 weeks first
  
Learning period behavior:
  - Expect CPCs to fluctuate
  - Some days higher spend, some days lower
  - DO NOT PAUSE the campaign during this period
  - DO NOT make major changes (budget, bids, keywords)
  
After learning period:
  - Set Target ROAS: start at 250% (2.5x)
  - Gradually raise by 10-15% every 2 weeks if hitting target
  - Goal: 350-400% ROAS (industry benchmark for direct-to-consumer food)
```

### Phase 3: Scale (Month 3+)
**Trigger:** Consistent ROAS 300%+ for 4+ weeks

**Strategy:** Target ROAS 300-350%
```
Optimization tactics:
  - Raise budget in 20% increments every 1-2 weeks
  - Monitor impression share — if below 60%, increase budget or ROAS target
  - Consider adding Phrase/Broad match with smart bidding
  - Launch PMax campaign now (with existing audience data)
  - Test Target CPA on brand campaign for lowest CAC
  
ROAS target by product:
  Kerala Spices (general): 280% target (competitive category)
  Black Pepper: 320% target (higher margin product)
  Cardamom: 350% target (premium product, high AOV)
  Gift combos: 300% target (higher AOV, lower competition)
```

### Smart Bidding Signals Used by Google
According to Google, Smart Bidding factors in:
- Device type + OS version
- Location (city/district level)
- Time of day + day of week
- Search query
- Browser
- Demographic (age, gender)
- Audience list membership
- Historical conversion data
- Landing page quality

The more conversion data you have, the better these signals work. This is why Phase 1 data collection is non-negotiable.

---

## 8. AUDIENCE TARGETING & EXCLUSIONS

### A. Observation Mode (Phase 1)

**Path:** Campaign → Audiences → Add audience segments → Observation

Add all of these in Observation mode first (no reach restriction):
```
IN-MARKET AUDIENCES:
  ✅ Food & Drink — Specialty Foods
  ✅ Food & Grocery Delivery
  ✅ Organic & Natural Foods
  ✅ Health & Wellness (broad)
  ✅ Recipes & Cooking
  
AFFINITY AUDIENCES:
  ✅ Foodies & Gourmets
  ✅ Cooking Enthusiasts
  ✅ Health-Conscious Living
  ✅ Green Living Advocates
  
CUSTOM AUDIENCES:
  Create: "Competitor visitors"
    - People who visited amazon.com/spices, bigbasket.com, etc.
    - Use: Targeting mode on remarketing / separate campaign
```

**After 30 days:** Review audience performance. If Cooking Enthusiasts has 50% lower CPA → add +20% bid adjustment for that audience.

### B. Audience Exclusions (Set Immediately)

**Exclude from ALL acquisition campaigns:**
```
- Recent purchasers (last 30 days) — they already converted, remarketing campaign handles them
- Employees (match by email if needed)
- Very low session quality (if using GA4 audiences — <10 seconds)
```

**Create a Remarketing campaign separately:**
- Budget: ₹100/day
- Audience: All website visitors (30 days) + cart abandoners (30 days)
- Different messaging: "Still thinking about it? 10% off today"

### C. Customer Match

**Process:**
1. Shopify Admin → Customers → Export (CSV)
2. Include: email + phone columns
3. Google Ads → Tools → Audience Manager → Customer lists → Upload
4. Match rate target: 30-50% (Google matches hashed data to Google accounts)

**Uses:**
- Bid adjustment +20% on known customers (higher intent = worth more per click)
- Create Similar Audiences (Google finds people like your customers)
- Exclude from cold traffic campaigns (avoid overlap, more accurate CAC)

### D. Optimized Targeting — TURN OFF

**Path:** Campaign → Audiences → Optimized Targeting → OFF

When enabled, Google will show your ads to anyone it thinks might convert, overriding your audience settings. For a new campaign, this means showing to completely unqualified traffic until it has enough data.

**Exception:** Re-enable after 90 days if you have strong conversion data and want Google to expand reach intelligently.

---

## 9. GEOGRAPHIC TARGETING

### A. The Most Important Location Setting

**Path:** Campaign → Locations → Location options

**WRONG (default):** "People in, or who show interest in, your targeted locations"
```
This targets:
  - Someone in the UK researching "Kerala spices India prices"
  - A tourist in Kolkata searching "Kerala tourism"
  - A student in Chennai researching "Kerala geography"
```

**CORRECT:** "People in or regularly in your targeted locations"
```
This targets:
  - People physically located in your target geography
  - People who regularly visit your target geography
  - Eliminates research/tourist traffic completely
```

### B. India-Specific Geo Strategy for eCommerce

**Phase 1 — Tier 1 Focus (best conversion rates, lowest RTO)**
```
High-Priority Cities/States:
  Bangalore (Bengaluru) — highest online spend, tech-savvy
  Hyderabad — strong food culture, high purchasing power
  Chennai — South India, strong spice affinity
  Pune — large migrant Kerala population
  Mumbai — diaspora population, high AOV
  Delhi/NCR — large population, established eCommerce habit
  Kochi/Kerala — origin state, high brand affinity

Bid adjustment: +15-20% for these locations
```

**Phase 2 — National Rollout with RTO Exclusions**
```
Exclude (high RTO / high cash-on-delivery refusal rate):
  Bihar
  Jharkhand
  UP (large parts)
  Assam
  Manipur
  Nagaland
  Meghalaya
  
Note: You've already excluded 14 states in your campaign ✅
This is the right approach.
```

**Phase 3 — NRI / Diaspora Campaigns**
```
Separate campaign: [Search_NRI_KeralaSpices_US_Purchase]
Target: USA, UK, UAE, Singapore, Australia, Canada
Demographics: South Asian diaspora (use audience targeting)
Message: "Taste of home. Delivered anywhere."
AOV: typically 2-3x higher for NRI orders
```

---

## 10. AD COPY & QUALITY SCORE

### A. RSA (Responsive Search Ad) Best Practices

**Structure:**
- 15 headlines (30 char max each)
- 4 descriptions (90 char max each)
- Google tests up to 43,680 combinations

**Pinning strategy:**
```
Pin Headline 1 (position 1): Keyword-specific
  Example: "Kerala Black Pepper Online"
  
Pin Headline 2 (position 2): Unique value proposition
  Example: "Direct From Kerala Farms"
  
Headline 3 (unpinned): Call to action, rotate
  Options: "Order Now", "Free Delivery ₹649+", "10% Off Today"
```

**Pre-qualification copy (reduces junk clicks):**
```
Instead of: "Black Pepper Online"
Write: "Premium Kerala Black Pepper — Starting ₹299"

Why: Price mention filters out non-buyers.
     "Starting ₹299" tells cheap seekers this isn't free.
     People clicking this have purchase intent.
```

**Psychological triggers for Indian buyers:**
```
Trust signals (critical in India due to fake product concerns):
  "Direct from Kerala farms" — authenticity
  "Lab tested, certified organic" — safety
  "No artificial color added" — purity
  "Export grade quality" — premium positioning
  
Urgency (use sparingly):
  "Today only: 10% off"
  "Dispatched same day"
  "In stock: order now"
  
Local signals:
  "Delivered across India"
  "2-5 day delivery"
  "COD available"
```

### B. Ad Copy Checklist for Each Ad Group
```
✅ Headline 1 contains the exact keyword or close variant
✅ Headline 2 states the primary value proposition
✅ Description 1 expands on product uniqueness
✅ Description 2 includes a call to action with urgency or benefit
✅ Display path mirrors the product: pureleven.com/Kerala-Pepper
✅ Final URL goes to the specific product/category page (not homepage)
✅ Mobile-preferred ad version exists (shorter, punchier)
```

### C. A/B Testing Protocol
- Run minimum 2 RSAs per ad group
- Let each run for minimum 30 days before judging
- Compare: CTR (ad quality) + Conv. Rate (landing page relevance)
- Kill the loser, create a new challenger
- Never test more than 1 variable at a time (headline vs description, not both)

---

## 11. LANDING PAGES — THE CONVERSION GATE

> **The most underinvested area in most Google Ads accounts.** A 1% improvement in landing page conversion rate = 1% improvement in ROAS with zero ad spend increase.

### A. Keyword-to-Landing Page Matching

| Ad Group | Keyword | Landing Page | ✅/❌ |
|---|---|---|---|
| Black Pepper | "kerala black pepper online" | /products/kerala-black-pepper-200gm | ✅ |
| Cardamom | "cardamom online" | /products/kerala-cardamom-8mm-200gm | ✅ |
| Kerala Spices | "buy kerala spices" | / (homepage) | ⚠️ (create /collections/kerala-spices) |
| Cinnamon | "ceylon cinnamon online" | /products/cinnamon | ✅ |
| Cloves | "laung online" | /products/cloves | ✅ |

### B. Landing Page Requirements
```
Above the fold (visible without scrolling on mobile):
  ✅ Product image (high quality, matches ad)
  ✅ Product name including keyword
  ✅ Price clearly visible
  ✅ "Add to Cart" button prominent
  ✅ Trust signals (reviews count, certifications)
  
Below fold:
  ✅ Product description with keyword integration
  ✅ Customer reviews (minimum 5, ideally 15+)
  ✅ Farm origin story (why pureleven is different)
  ✅ FAQs (addresses purchase objections)
  ✅ Related products (increase AOV)
  
Mobile requirements:
  ✅ Load time <3 seconds (critical for India mobile)
  ✅ Button size ≥48px for touch
  ✅ No intrusive popups that block product content
  ✅ COD option visible early in checkout
```

### C. Conversion Rate Benchmarks (India eCommerce)
```
Average food/spices: 1.5–3%
Good: 3–5%
Excellent: 5–8%

If your CR <1.5%, fix the landing page BEFORE increasing ad spend.
Every ₹1 spent on landing page optimization > ₹1 spent on more ads (at low CR).
```

### D. Tools for Landing Page Optimization
```
Microsoft Clarity (FREE) — session recordings, heatmaps, rage clicks
  Install on all product pages
  Watch 10 recordings/week — you'll see exactly where buyers hesitate

Hotjar — similar, paid tier has more features
  
PageSpeed Insights — Google's tool for load time
  Target: LCP <2.5s, CLS <0.1, FID <100ms
```

---

## 12. ASSETS (EXTENSIONS)

> Extensions show additional info without extra cost. They increase ad real estate and CTR by 10–20% on average.

### A. Assets to Add (Pureleven Status)

| Asset Type | Status | Priority |
|---|---|---|
| Sitelinks | ✅ 6 created | Done |
| Callouts | ✅ 6 created | Done |
| Structured Snippets | ✅ 1 created (Types) | Done |
| Price | ✅ Added (Pending review) | Done |
| Image | ✅ Added (Pending review) | Done |
| Business name | ✅ via logo | Done |
| Promotion | ❌ Not created | HIGH |
| Call | ❌ Not created | MEDIUM |
| Location | N/A (online-only) | — |
| Lead form | ❌ Not created | MEDIUM |

### B. Promotion Asset Setup
```
Path: Assets → Create → Promotion

Type: Percentage discount
Occasion: (leave blank for ongoing)
Item: First Order
Discount: 10%
Promo code: PL10OFF
Final URL: https://pureleven.com/

Start: Immediate
End: [leave blank or 3 months out]
```

**Impact:** Promotion assets show a price tag icon below your ad with the offer — dramatically increases CTR for price-sensitive searchers.

### C. Call Asset Setup
```
Phone number: [your business number]
Schedule: 9am–7pm IST, Mon–Sat

Note: Mobile users may click "Call" instead of visiting the site.
This bypasses cart abandonment entirely.
Useful for high-value orders (bulk purchases, gifting)
```

---

## 13. SEARCH TERMS REPORT — WEEKLY ROUTINE

> This single report can reduce wasted spend by 20–40%. Most advertisers ignore it. This is your competitive advantage.

### Weekly Process (30 minutes every Monday)

**Step 1:** Go to Reports → Search terms (filter: last 7 days)

**Step 2:** Sort by "Cost" descending. Look at top 20 terms.

**Step 3:** For each term, ask 3 questions:
```
Q1: "Would someone searching this buy my product?" 
    No → Add as negative keyword

Q2: "Is this term converting at a good rate?"
    Yes + high volume → Add as exact match keyword in its own ad group
    
Q3: "Is this an existing keyword that should perform better?"
    Yes → Check landing page, ad relevance, bid level
```

**Step 4:** Weekly negative additions (keep a log)
```
Date | Term Added as Negative | Level | Reason
2026-05-20 | "kali mirch ke fayde" | Campaign | Information search, no purchase intent
2026-05-20 | "bulk black pepper" | Campaign | B2B/wholesale, not target customer
```

**Step 5:** Winning search terms → Promote to keywords
```
If "buy organic black pepper online" spent ₹120, got 2 conversions:
→ Add [buy organic black pepper online] as exact match keyword
→ Create dedicated ad group if significant volume
→ Set higher bid than current campaign average
```

### Common "Fool's Gold" Search Terms (Add as Negatives)
```
"[product] benefits" — health research, not buying
"best [product] in india" — comparison, not buying yet
"[product] price per kg" — price check, often B2B/wholesale
"[product] for weight loss" — health/diet research
"organic [product] farm" — cultivation research
"[product] recipe" — cooking resource, not buying
"[product] powder homemade" — DIY, not buying
"[product] side effects" — health concern, not buying
```

---

## 14. REPORTING & KPI DASHBOARD

### A. Metrics Hierarchy

**Primary KPIs (affect decisions):**
```
ROAS = Conv. value / Cost (target: 300%+)
CPA = Cost / Conversions (target: <₹350 for ₹800 AOV → 2.3x margin)
Conv. Rate = Conversions / Clicks (target: 2%+)
```

**Secondary KPIs (diagnostic):**
```
CTR = Clicks / Impressions (target: 6%+ for Search)
Avg CPC (monitor for inflation)
Impression Share (target: 50%+ for core keywords)
Quality Score (target: 7+ for exact match keywords)
```

**Ignore (or use carefully):**
```
Impressions alone (vanity metric)
Clicks alone (means nothing without conversion context)
CTR alone (high CTR + low conversion = bad ad copy, not good)
```

### B. Weekly Reporting Template

```
Week of: [Date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERFORMANCE
  Total Spend: ₹_____
  Conversions: _____
  Revenue (Conv. Value): ₹_____
  ROAS: _____x
  CPA: ₹_____

TRAFFIC QUALITY
  Impressions: _____
  Clicks: _____
  CTR: _____%
  Avg CPC: ₹_____

TOP PERFORMERS
  Best keyword (by ROAS): _______________
  Best ad group (by Conv. Rate): _______________
  Best location (by CPA): _______________

WASTE REMOVAL
  New negatives added this week: _____
  Budget saved (est.): ₹_____
  Search terms reviewed: _____

ACTION ITEMS FOR NEXT WEEK:
  1. _______________
  2. _______________
  3. _______________
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### C. Custom Columns to Add in Google Ads
**Path:** Columns → Modify columns → Custom columns

Add these columns to your campaign/ad group view:
```
Conversion value / cost (ROAS ratio)
Cost / conversion (CPA)
Conversion rate
Search impression share
Search lost IS (budget) — shows if you're losing impressions due to budget
Search lost IS (rank) — shows if you're losing due to quality/bid
```

### D. Auction Insights — Competitive Intelligence
**Path:** Reports → Auction Insights

Shows you:
- Which competitors appear alongside your ads
- Their impression share vs yours
- Overlap rate (how often they show when you show)
- Outranking share (how often you rank above them)

**What to do with this data:**
- If a competitor has 80% impression share and you have 20% → they're dominating
- If overlap rate >70% → you're in direct competition for same traffic
- Look at their ad copy and landing pages → find gaps you can exploit

---

## 15. PERFORMANCE MAX SETTINGS

> PMax is powerful but dangerous without proper setup. Launch it LAST, not first.

### Prerequisites Before Launching PMax
```
✅ 50+ conversions/month tracked
✅ Negative keyword list built and tested
✅ Audience lists created (remarketing, customer match)
✅ Profitable search campaign running (proof of ROAS)
✅ Product feed complete and approved in Merchant Center
✅ Creative assets ready (images, logos, videos, headlines, descriptions)
```

### Asset Group Structure
```
Asset Group 1: Premium Whole Spices (core collection)
  Final URL: /collections/all
  Products: All spice singles
  Headlines: Focus on "farm-origin", "premium", "authentic"
  Images: Product photos, farm photos

Asset Group 2: Black Pepper Focus
  Final URL: /products/kerala-black-pepper-200gm
  Products: Black pepper products only
  Headlines: "Kerala Black Pepper", "Malabar Pepper"
  
Asset Group 3: Cardamom Focus
  Final URL: /products/cardamom
  
Asset Group 4: Gift Combos / High AOV
  Final URL: /collections/combo-packs
  Products: Combo packs only
  Headlines: Focus on gifting, value, Diwali/Onam occasions
```

### PMax Settings That Prevent Waste
```
⚠️ Final URL expansion: TURN OFF (or set allowed URLs strictly)
   Otherwise PMax will link to blog posts, contact pages, etc.
   
⚠️ Brand exclusions: ADD YOUR OWN BRAND
   Prevent PMax from stealing credit for organic/direct traffic
   
Account-level negative keywords: APPLY to PMax campaigns
   (PMax doesn't support campaign-level negatives, use account-level)
   
Audience signals:
   Add all custom audiences, customer match, website visitors
   These are "signals" not targeting restrictions — they guide ML
   
Budget:
   Minimum ₹500/day for PMax to have enough data
   Below this, ML can't learn effectively
```

---

## 16. SHOPPING / MERCHANT CENTER

### A. Product Feed Best Practices
```
Title format (most important field):
  [Brand] [Product Name] [Key Feature] [Weight/Size]
  Example: "Organic Pure Leven Kerala Black Pepper Whole Peppercorns 200g"
  NOT: "Black Pepper"
  
Description:
  Include: origin, processing method, certifications, use cases
  Minimum 150 words for best quality score
  Include keywords naturally (don't keyword-stuff)
  
Images:
  Clean white background for product shots (better CTR)
  Minimum 800×800px
  No text overlays (Google policy violation)
  Multiple angles recommended
  
GTINs:
  Add if you have them (barcodes/EANs)
  If not, set "identifier_exists: no" to avoid disapprovals
  
Availability:
  Sync with Shopify inventory in real-time
  "Out of stock" products = wasted impressions
  
Price:
  Must exactly match website at all times
  Price mismatch = product disapproval
```

### B. Shopping Campaign Structure
```
Campaign Priority Setting (prevents budget cannibalization):

Campaign 1 — Brand terms (Priority: HIGH)
  Negatives: All generic terms
  Purpose: Protect brand queries at low CPC

Campaign 2 — Category terms (Priority: MEDIUM)
  Example: "kerala spices", "organic spices"
  Purpose: Category-level discovery

Campaign 3 — Generic (Priority: LOW)
  Broadest terms: "buy spices online", "spices delivery"
  Purpose: Discovery/new customer acquisition
```

---

## 17. SCALING PLAYBOOK

### Phase 1: Stop the Bleeding (Weeks 1-4)
**Goal:** Eliminate waste, establish baseline ROAS

Checklist:
```
□ Add account funds (₹0 balance = no ads running) ⚠️
□ Turn off Display Network expansion
□ Set correct location option (Presence only)
□ Turn off auto-apply recommendations
□ Set Purchase as primary conversion (only)
□ Set conversion value (₹800 or dynamic)
□ Build 5 negative keyword lists
□ Apply all negative lists to campaign
□ Verify Enhanced Conversions active
□ Set up weekly search terms review routine
□ Check Quality Scores — fix anything below 5
```

**Expected outcome:** Cut wasted spend 30–50%, see first conversions.

### Phase 2: Build the Foundation (Weeks 5-12)
**Goal:** Reach 50 conversions/month, build audience data

Checklist:
```
□ Review search terms weekly, add negatives continuously
□ Identify top-converting keywords → increase bids
□ Identify zero-conversion keywords (20+ clicks) → pause/reduce bid
□ Add In-market audiences (Observation mode)
□ Upload customer match list from Shopify
□ Add Promotion asset (10% off first order)
□ Create remarketing campaign (₹100/day budget)
□ Check impression share — if <40%, budget or bid may be limiting
□ Test second RSA variant per ad group
□ Add Hindi keyword variants
□ Switch bidding to Maximize Conversions (when 50+ conv. achieved)
```

**Expected outcome:** 50+ monthly conversions, ROAS 200-250%

### Phase 3: Optimize & Scale (Month 3-6)
**Goal:** Hit 300%+ ROAS, scale budget

Checklist:
```
□ Set Target ROAS 280% initially, raise by 10% every 2 weeks
□ Increase budget 20% every 2 weeks if hitting ROAS target
□ Launch Shopping campaigns (Merchant Center → Shopping)
□ Add Phrase match variants (still with strong negatives)
□ Create city-specific ad groups for top-converting cities
□ Test video assets for Display/YouTube remarketing
□ Build brand keyword protection campaign
□ Separate NRI/diaspora campaign if international shipping possible
□ A/B test landing pages (Shopify themes or sections)
□ Launch Performance Max (with all prerequisites met)
```

**Expected outcome:** ₹80,000–120,000+/month revenue from Google Ads

---

## 18. PURELEVEN-SPECIFIC ACTION PLAN

### 🔴 CRITICAL — Do This Week

| Action | Time | Impact |
|---|---|---|
| **Add ₹10,000+ account balance** | 15 min | Ads start running |
| Verify conversion value is not ₹0 | 30 min | Smart bidding becomes usable |
| Enable Enhanced Conversions | 15 min | Recover 10-25% lost conversions |
| Check Display Network is OFF | 5 min | Stop immediate budget waste |
| Check location targeting = "Presence only" | 5 min | Stop geographic waste |
| Disable all Auto-apply recommendations | 10 min | Prevent Google from widening targeting |
| Create account-level negative keyword lists (5 lists) | 2 hours | Build profit firewall |

### 🟡 HIGH PRIORITY — This Month

| Action | Time | Impact |
|---|---|---|
| Review search terms weekly | 30 min/week | Eliminate 20-40% waste |
| Add Promotion asset (PL10OFF 10% off) | 30 min | +15% CTR |
| Add Call asset | 15 min | Enable direct purchase intent |
| Upload customer match list from Shopify | 45 min | Better audience signals |
| Check Quality Scores; improve below-5 ones | 2 hours | Lower CPC by 15-30% |
| Add Hindi keyword variants to all ad groups | 1 hour | +30% search coverage |
| Set up Microsoft Clarity on product pages | 1 hour | Find conversion barriers |
| A/B test: homepage vs category landing page for "kerala spices" | 2 weeks | Improve Conv. Rate |

### 🟢 NEXT 90 DAYS — Growth

| Action | Time | Impact |
|---|---|---|
| Launch remarketing campaign | 2 hours | Recover cart abandoners |
| Switch to Maximize Conversions (after 50+ conv.) | 10 min | Smart bidding optimization |
| Launch Shopping campaign | 3 hours | Additional revenue channel |
| Create NRI campaign (US/UK/UAE) | 3 hours | Higher AOV orders |
| Launch Performance Max | 4 hours | Omnichannel reach |
| Scale budget to ₹800/day | Gradual | Double revenue |

---

### Current Account Status Summary
```
Campaign: Search-Kerala-Spices-May2026 (ID: 23853350110)
Budget: ₹400/day ✅
Bidding: Maximize Clicks ✅ (appropriate for Phase 1)

Assets:
  Sitelinks: 6 ✅
  Callouts: 6 ✅
  Structured Snippet: 1 (Types) ✅
  Price Asset: 5 products, INR ✅ (Pending review)
  Image Asset: 6 product images ✅ (Pending review)
  Business Logo: ✅
  Promotion: ❌ (add PL10OFF)
  Call: ❌ (add phone number)

Targeting:
  Location: India ✅ (14 RTO states excluded ✅)
  Geographic option: ✅ (confirm Presence only)
  Age exclusion: 18-24 excluded ✅
  Audiences: 7 segments in Observation ✅

Conversion Tracking:
  Purchase (ctId=6694318743): ₹800 default ✅
  Purchase (Page load): ₹800 ✅
  Enhanced Conversions: Active ✅
  Attribution: ✅ (verify data-driven enabled)
  Display Network: ❌ (verify OFF)
  Auto-apply: ❌ (verify OFF)
  
BLOCKER: Account balance = ₹0 ⚠️ — NO ADS RUNNING
```

---

## QUICK REFERENCE: SETTINGS AUDIT CHECKLIST

Run this audit on your account every 30 days:

```
ACCOUNT LEVEL:
□ Auto-apply recommendations: all OFF
□ Attribution model: Data-driven (or position-based)
□ Shared negative lists: 5 lists applied to all campaigns

CAMPAIGN LEVEL:
□ Network: Search ONLY (Display = OFF)
□ Search Partners: OFF (or ON only after proven ROAS)
□ Location option: "Presence only"
□ Bidding: Appropriate for conversion volume phase
□ Optimized Targeting: OFF

CONVERSION SETTINGS:
□ Purchase = Primary (only primary action)
□ Add to cart = Secondary
□ Begin checkout = Secondary
□ Page view = NOT a conversion action
□ Conversion value > ₹0
□ Enhanced Conversions: Active
□ Attribution: Data-driven (if volume qualifies)

AD GROUP LEVEL:
□ Each ad group: single theme
□ Keyword → Ad copy match
□ Ad copy → Landing page match
□ Negative keywords: inter-ad-group negatives applied
□ Quality Scores: target 7+

WEEKLY ROUTINES:
□ Search terms review (Mon morning, 30 min)
□ New negatives added and logged
□ Winning search terms promoted to keywords
□ KPI dashboard filled in
□ Any keywords with 20+ clicks, 0 conversions → paused
```

---

*Guide compiled: May 15, 2026*  
*Based on: Google Ads official documentation, Smart Bidding guidelines (support.google.com/google-ads/answer/7065882), Quality Score best practices (support.google.com/google-ads/answer/6167123), Conversion tracking setup (support.google.com/google-ads/answer/6095821), and industry research on India eCommerce advertising.*
