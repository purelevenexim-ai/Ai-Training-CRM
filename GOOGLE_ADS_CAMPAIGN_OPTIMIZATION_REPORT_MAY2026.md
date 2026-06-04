# Google Ads Campaign Optimization Report
## Search-Kerala-Spices-May2026

**Report Date:** May 17, 2026  
**Campaign:** Search-Kerala-Spices-May2026  
**Account:** Pureleven - AW-10965185406  
**Author:** Campaign Optimization Audit

---

## EXECUTIVE SUMMARY

This report documents the comprehensive audit and optimization roadmap for the Search-Kerala-Spices-May2026 campaign. The campaign is well-configured at the network level with optimal traffic routing (Search-only strategy). However, significant improvements are needed in bidding strategy, negative keyword management, and keyword quality optimization to prevent budget waste.

**Key Findings:**
- ✅ **Network Configuration:** Optimal (Search Network only, no Display/Partners)
- ✅ **Location Targeting:** India-focused with regional exclusions configured
- ⚠️ **Bidding Strategy:** Suboptimal for zero-conversion accounts (Maximize Conversions problematic)
- ⚠️ **Keyword Quality:** NO negative keywords currently configured
- ⚠️ **Quality Score:** At-risk due to budget waste on low-intent searches

**Business Impact:**
- Current budget (₹400/day): Vulnerable to waste on irrelevant searches
- Without negative keywords: Estimated 15-25% budget leak to non-converting queries
- Projected annual waste: ₹18,000-36,000 without immediate action

---

## PART 1: CAMPAIGN-LEVEL SETTINGS AUDIT

### 1.1 Network Configuration - ✅ OPTIMAL

**Current Settings:**
| Setting | Status | Configuration |
|---------|--------|---|
| Google Search Network | ✅ ENABLED | Primary traffic source - Optimal |
| Display Network | ✅ OFF | Disabled - Prevents low-value conversions |
| Search Partners | ✅ OFF | Unchecked - Reduces spend scatter |

**Audit Status:** ✅ **OPTIMAL** - Network configuration prevents budget waste on non-search placements.

**Why This Matters:**
- Search Network = High-intent users actively searching for spices
- Display Network = Passive viewing (wrong for commerce conversion goals)
- Search Partners = Scattered, low-quality Google partner sites
- Result: 100% of budget targets highest-ROI traffic source

---

### 1.2 Location Targeting - ✅ CONFIGURED (Needs Verification)

**Current Settings:**
```
Targeting Mode: Presence Only (Best Practice)
Primary Target: India (country)
Excluded Regions: Arunachal Pradesh + 13 more regions (14 total)

Excluded States (presumed):
- Arunachal Pradesh (remote, difficult logistics)
- Meghalaya, Manipur, Mizoram, Nagaland (Northeast - high shipping)
- Tripura, Sikkim (remote)
- Jammu & Kashmir (cross-border complexity)
- Lakshadweep, Daman & Diu, Dadra & Nagar Haveli (island/remote)
- Plus 5 more (likely Ladakh, Andaman & Nicobar, etc.)
```

**Audit Status:** ✅ **GOOD** - Presence-only mode targets users actively in India.

**Explanation:**
- "Presence only" = Users physically located in India (not just showing interest)
- Geographic exclusions = Smart cost optimization for remote regions
- This prevents wasting budget on high-delivery-cost regions

**Recommendation:** Keep as-is. This is well-configured for Pureleven's logistics scope.

---

### 1.3 Bidding Strategy - ⚠️ PROBLEMATIC (IMMEDIATE ACTION NEEDED)

**Current Settings:**
```
Strategy Type: Maximize Conversions
Budget: ₹400.00/day
Current Performance: 0 conversions, ₹0.00 spent, 0 clicks, 0 impressions
```

**Audit Status:** ⚠️ **PROBLEMATIC** - Wrong strategy for zero-conversion baseline.

**Why This Is a Problem:**
1. **Maximize Conversions** requires 30+ conversions/month minimum for Google's AI to optimize
2. **With 0 conversions:** Google's algorithm is guessing bid adjustments
3. **Result:** Inefficient bid allocation, budget waste on low-quality clicks
4. **Risk:** Campaign may receive no impressions if bids are too low

**Recommendation:** ⚠️ **SWITCH TO MANUAL CPC IMMEDIATELY**
```
Action: Change bidding strategy from "Maximize Conversions" to "Manual CPC"

Target CPC Calculation (for Kerala Spices):
- Estimated AOV (Average Order Value): ₹1,200-1,800
- Target conversion rate: 2-3% (for search traffic)
- Estimated revenue per 100 clicks: ₹2,400-5,400
- Safe max CPC: ₹60-90 per click
- Starting recommendation: ₹75/click

Implementation Timeline:
- Change to Manual CPC immediately
- Set initial max CPC: ₹75 (test)
- Monitor CTR and conversion rate for 2 weeks
- Adjust to ₹50-100 based on performance data
- Once 30+ conversions achieved: Switch back to Maximize Conversions
```

---

### 1.4 Campaign Basics Configuration - ✅ GOOD

**Current Settings:**
| Setting | Value | Status |
|---------|-------|--------|
| Campaign Name | Search-Kerala-Spices-May2026 | ✅ |
| Status | Enabled (Green) | ✅ |
| Type | Search | ✅ |
| Budget | ₹400.00/day | ✅ |
| Start Date | May 14, 2026 | ✅ |
| End Date | Not set | ⚠️ Open-ended |
| Optimization Goal | Purchases | ✅ |
| Language | English, Malayalam | ✅ |
| Asset Optimization | Text customization ON | ✅ |

**Audit Status:** ✅ **GOOD**

---

### 1.5 Additional Configuration Review

**Feature Status Table:**
| Setting | Status | Notes |
|---------|--------|-------|
| Dynamic Search Ads | Enabled | Can help expand keyword coverage |
| Ad Rotation | Optimize (Best performing) | ✅ Prefers high-performing ads |
| AI Max for Search | Enabled | Beta feature - fine for keyword expansion |
| Smart Bidding Exploration | Beta | Can help with initial conversion data |
| Customer Acquisition | Bid equally | ✅ Good for new market launch |
| Value Rules | None set | Not needed at current stage |
| Conversion Goal | Campaign-specific: Purchases | ✅ Recently optimized (9→8 primary actions) |
| Page Feeds | Not configured | Optional - low priority |
| IP Exclusions | None set | ✅ No known competitors to block |
| URL Tracking | No options set | ✅ OK for now |

---

### 1.6 Auto-Apply Recommendations Setting

**Investigation Result:** ⚠️ **NOT FOUND AT CAMPAIGN LEVEL**

**Finding:** The campaign settings dialog does not contain an "auto-apply recommendations" toggle at the campaign level. This is typical Google Ads behavior:

**Explanation:**
- Auto-apply recommendations is usually an **account-level setting** (not campaign-level)
- Located in: Admin > Account settings > Auto-apply recommendations
- Current status: **ASSUMED ENABLED** (Google's default)
- **RECOMMENDED ACTION:** Verify and disable at account level if enabled

**Why Disable Auto-Apply:**
- Account has 0 conversions currently
- Auto-apply with zero conversion data = High risk of budget waste
- Could auto-enable Display Network, adjust bids poorly, etc.

**Verification Needed:** Check account-level settings (Admin section)

---

## PART 2: COMPREHENSIVE NEGATIVE KEYWORD STRATEGY

### 2.1 Strategic Approach

**Problem Identified:** Campaign has ZERO negative keywords configured.

**Risk Assessment:**
- **Budget Leak Rate:** 15-25% of budget wasted on irrelevant searches
- **Low-intent clicks:** Generic terms, competitors, how-tos, recipes
- **Annual cost at 20% leak:** ₹400/day × 365 × 0.20 = ₹29,200 wasted
- **Search Term Visibility:** Need to audit 2-4 weeks of real search data to refine further

**Strategy:** Build 5 shared negative keyword lists covering major waste categories

---

### 2.2 Negative Keyword Lists (Ready for Implementation)

#### **LIST 1: Generic & Irrelevant Intent**
**Purpose:** Block searches for cooking tips, how-tos, health benefits (low-conversion queries)

```
Negative Keywords (Broad Match):
- tips
- how to
- how-to  
- recipe
- recipes
- health benefits
- medicinal uses
- nutritional value
- uses of

Negative Keywords (Phrase Match):
- "spice tips"
- "cooking tips"
- "health benefits of"
- "how to use"
- "spice recipes"

Search Terms This Blocks:
❌ "how to use turmeric for health"
❌ "best spice recipes for cooking"
❌ "cumin health benefits"
❌ "cardamom medicinal properties"
❌ "spice tips for beginners"
```

**Rationale:** Users searching for "how-to" content rarely convert to purchases. These are informational, not commercial searches.

---

#### **LIST 2: Competitor Brand Names**
**Purpose:** Block searches for competitor brands that may trigger our ads

```
Negative Keywords (Exact Match - Most Effective for Brands):
- MDH
- Everest
- Badshah
- Shan
- Natco
- Aachi
- Priya
- Eastern
- Asha
- Tata Sampann

Additional Variations (Phrase Match):
- "MDH spices"
- "Everest spices"
- "Badshah masala"
- "Shan masala"

Why Exact Match for Brands?
- Prevents "MDH vs Pureleven" comparison searches
- Stops "buy MDH [spice]" keyword triggers
- Reduces wasted clicks on competitor-intent searches
- Cost per click is high but conversion = 0%
```

**Business Case:** When someone searches "buy MDH turmeric," they want MDH, not Pureleven. Exact match blocks these high-cost, zero-conversion clicks.

---

#### **LIST 3: Low-Intent Modifiers**
**Purpose:** Block searches with discount/free intent, quantity/samples (low-value customers)

```
Negative Keywords (Broad Match):
- free
- cheap
- lowest price
- discount
- offer
- sale
- coupon
- samples
- sample
- trial

Negative Keywords (Phrase Match):
- "free shipping"
- "cheap spices"
- "lowest price"
- "bulk discount"
- "trial pack"
- "free sample"

Search Terms This Blocks:
❌ "cumin seeds free shipping"
❌ "cheapest online spices"
❌ "turmeric powder bulk discount"
❌ "spice sample pack free"
❌ "cinnamon lowest price online"

Why Include These:
- Free/cheap seekers = Low margins
- Discount hunters = Not loyal customers
- Sample requests = No revenue potential
- High search volume but 0% conversion value
```

**Margin Protection:** Pureleven's premium positioning doesn't benefit from discount-seeking traffic.

---

#### **LIST 4: Brand Protection (Discount Combos)**
**Purpose:** Prevent budget waste on searches combining brand + discount/competitor

```
Negative Keywords (Phrase Match - Highly Targeted):
- "pureleven sale"
- "pureleven discount"
- "pureleven offer"
- "pureleven cheap"
- "pureleven low price"
- "pureleven free shipping"
- "pureleven vs MDH"
- "pureleven vs Everest"
- "pureleven vs competitor" (for each main competitor)
- "pureleven sample"
- "pureleven free trial"

Negative Keywords (Broad Match - Defensive):
- pureleven coupon
- pureleven deal
- pureleven offer code

Why Critical:
- Protects brand from low-intent searchers
- Prevents "Pureleven sale" searchers (if no sale running)
- Blocks competitor comparison searches
- Example: Someone searches "pureleven vs MDH price" - they're comparison shopping, not ready to buy Pureleven at full price
```

**Brand Health:** Prevents bidding against brand name on discount-intent searches.

---

#### **LIST 5: Unrelated Categories & Cross-Domains**
**Purpose:** Block searches for spices in non-food/kitchen contexts or completely unrelated categories

```
Negative Keywords (Broad Match - Expansive):
- chaat
- chaat masala (unless that's your product)
- baking
- dessert
- cake
- synthetic
- artificial
- plastic
- decor
- incense
- perfume
- medicine
- pharmacy
- homeopathy

Negative Keywords (Phrase Match - Category-Specific):
- "spices for chaat" (if not selling chaat masala)
- "baking spices"
- "cake decorating"
- "home decor"
- "room fragrance"
- "ayurvedic medicine"
- "herbal medicine"

Search Terms This Blocks:
❌ "chaat masala recipe" (informational)
❌ "baking spices for cakes"
❌ "spices as home decor"
❌ "synthetic spices suppliers"
❌ "medicinal spice powder"

Why Include:
- Spice keyword ambiguity (culinary vs. medical vs. decorative)
- Baking context = Different customer, different spices
- Unrelated products with "spice" keywords
- Synthetic = Wrong positioning (Pureleven = organic)
```

**Category Protection:** Ensures budget targets food-quality culinary spices only.

---

### 2.3 Negative Keyword Implementation Plan

**Step 1: Create Shared Negative Keyword Lists**
```
In Google Ads:
1. Go to Tools & Settings > Shared Keyword Lists
2. Click "+" to create new list
3. Create 5 lists:
   - "Negative Keywords - Generic Intent"
   - "Negative Keywords - Competitors"
   - "Negative Keywords - Discount Intent"
   - "Negative Keywords - Brand Protection"
   - "Negative Keywords - Unrelated Categories"
4. Add keywords from above to each list
```

**Step 2: Apply Lists to Campaign**
```
1. Go to Campaign Settings
2. Under "Keyword & Exclusions" section
3. Add all 5 shared lists as Negative Keyword Lists
4. Set match types according to recommendations:
   - Competitor brands: Exact match (most restrictive)
   - Generic terms: Broad match (catches variations)
   - Phrase match for specific combinations
```

**Step 3: Monitor & Refine (Weeks 1-4)**
```
Week 1:
- Check Search Terms report weekly
- Document what negative keywords are working
- Look for missed low-intent terms

Week 2-4:
- Review search term performance
- Add 10-20 negative keywords per week as you identify patterns
- Monitor "Quality Score" by keyword (should improve)
- Check CTR and conversion rate trend (should improve)

Metrics to Track:
- Impressions (should decrease, which is good)
- Click-through rate (should increase - fewer wasted clicks)
- Cost per click (may increase slightly - better quality)
- Quality Score (should trend upward)
```

---

### 2.4 Additional Negative Keywords to Add After Data Review

**These require 2-4 weeks of actual search data:**

```
After reviewing Search Term Report, add negatives for:

1. Misspellings of competitor brands
2. Frequently-searched spices NOT offered (e.g., if you don't sell fenugreek, add: fenugreek)
3. Bulk/wholesale intent (if you're retail-only): "bulk", "wholesale", "corporate"
4. B2B intent: "supplier", "distributor", "wholesale price", "bulk order"
5. Non-English variations: Common misspellings in Indian languages
6. Regional incorrectness: Spice spellings for regions you don't ship to

Timeline: Add these in week 3-4 after campaign data accumulates
```

---

## PART 3: COMPREHENSIVE RECOMMENDATIONS

### 3.1 Priority Actions (This Week)

**CRITICAL - Must Do:**

1. **Change Bidding Strategy (URGENT)**
   - ❌ Current: Maximize Conversions (wrong for 0 conversions)
   - ✅ Change to: Manual CPC
   - 💰 Set initial max CPC: ₹75
   - 📅 Timeline: TODAY
   - 💡 Reason: Protect budget from AI guessing without data

2. **Create 5 Negative Keyword Lists**
   - ✅ Lists defined above (sections 2.2)
   - 📅 Timeline: TODAY
   - 💰 Expected impact: Reduce budget waste by 15-25%
   - 📊 Monitor: Search Terms report after 2 weeks

3. **Verify Account-Level Auto-Apply**
   - ❌ Check: Admin > Account settings
   - ✅ If enabled: DISABLE
   - 📅 Timeline: TODAY
   - 💡 Reason: Prevent auto-enable of Display Network or other changes on zero-conversion account

### 3.2 High-Priority Actions (Next 2 Weeks)

4. **Audit Ad Group Keywords**
   - 📋 Task: Review keyword list for Kerala Spices campaign
   - 🔍 Check: Keyword match types, bids, Quality Scores
   - 📊 Flag: Any keywords with Quality Score < 5/10
   - 📅 Timeline: Week 1
   - ⚠️ Note: May require separate audit

5. **Monitor Search Term Report**
   - 📊 Generate: Search Terms report
   - 🎯 Review: Top 20 searches with clicks but no conversions
   - ❌ Add to negatives: Low-intent terms
   - 📅 Timeline: Week 1 (after 100+ clicks accumulated)
   - 📈 Frequency: Weekly review x 4 weeks

6. **Implement Negative Keywords**
   - 📋 Task: Add all 5 lists from Section 2.2 to campaign
   - 🎯 Priority: Competitor brands (exact match)
   - 📅 Timeline: Week 1
   - 📊 Expected improvement: Quality Score +1-2 points within 2 weeks

### 3.3 Medium-Priority Actions (Weeks 3-4)

7. **Quality Score Improvement Campaign**
   - 📊 Metric: Average Quality Score target = 7/10 or higher
   - 🔧 Levers: Ad copy, landing page, keyword relevance
   - 📅 Timeline: Weeks 2-4
   - 📈 Check: Quality Score trending upward

8. **Bidding Strategy Reassessment**
   - 📊 Data point: Once 30+ conversions achieved
   - ✅ Consider: Switching back to Maximize Conversions
   - ⚠️ Only if: CPC costs are reasonable
   - 📅 Timeline: End of week 4 or later

9. **Keyword Bid Optimization**
   - 📊 High-performing keywords: Increase bid by 10-25%
   - 📊 Low-performing keywords: Reduce bid by 10-25%
   - 💰 Focus on: Keywords with conversions (rare at this stage)
   - 📅 Timeline: Week 3

### 3.4 Optional/Future Actions

10. **Dynamic Search Ads Setup**
    - 📋 Task: Configure Dynamic Search Ads
    - 🎯 Purpose: Fill gaps in keyword coverage
    - 📅 Timeline: After initial campaign stabilizes (week 4+)

11. **Page Feed Setup**
    - 📋 Task: Upload page feed from product catalog
    - 🎯 Purpose: Improve ad relevance, landing page matching
    - 📅 Timeline: Week 4+

12. **Geographic Bid Adjustments**
    - 📊 Analysis: Which states converting best?
    - 🎯 Action: +20-30% bid for high-converting states
    - 📅 Timeline: After 30+ conversions (week 3+)

---

## PART 4: IMPLEMENTATION SUMMARY

### 4.1 Campaign Optimization Timeline

```
TODAY (May 17):
  ✅ Change bidding strategy to Manual CPC (₹75)
  ✅ Create 5 negative keyword lists
  ✅ Add competitor brand negatives (exact match)
  ✅ Check account auto-apply settings

WEEK 1-2 (May 20-31):
  ✅ Monitor Search Terms report
  ✅ Apply negative keyword lists to campaign
  ✅ Add 10-20 weekly negative keywords from search data
  ✅ Check Quality Score trends
  ✅ Track CTR and cost metrics

WEEK 3-4 (June 1-14):
  ✅ Bid optimization based on performance
  ✅ Add location-specific bids if data permits
  ✅ Continue negative keyword refinement
  ✅ Prepare for bidding strategy change (if 30+ conversions)

WEEK 5+ (June 15+):
  ✅ Evaluate for Maximize Conversions switch
  ✅ Dynamic Search Ads optimization
  ✅ Geographic scaling based on performance
```

---

## PART 5: SUCCESS METRICS & MONITORING

### 5.1 Key Performance Indicators

**Metrics to Track Weekly:**

| Metric | Current | Target (2 weeks) | Target (4 weeks) |
|--------|---------|------------------|------------------|
| Impressions | 0 | 500+ | 1,500+ |
| Clicks | 0 | 50+ | 150+ |
| CTR (Click-through Rate) | N/A | 3-5% | 5-7% |
| Avg CPC | N/A | ₹50-80 | ₹60-90 |
| Conversions | 0 | 1-2 | 5-10 |
| Quality Score (Avg) | Unknown | 6-7 | 7-8 |
| Cost per Conversion | N/A | ₹3,000-5,000 | ₹2,000-4,000 |
| ROAS (Return on Ad Spend) | N/A | 0.5-1.0x | 1.0-2.0x |

### 5.2 Negative Keyword Effectiveness

**Expected Outcomes:**
- Wasted budget reduced: 15-25% → saves ₹20-30k/year
- Quality Score improvement: +1-2 points
- CTR improvement: +20-30%
- Cost per click stability with better quality

**Measurement Method:**
- Week 0 baseline (current)
- Week 2 snapshot (after initial negatives)
- Week 4 review (after refinement)

---

## PART 6: AUDIT FINDINGS SUMMARY

### ✅ What's Working Well:
1. Network configuration (Search-only) - Optimal for conversion campaigns
2. Location targeting - India-focused, excludes high-cost regions
3. Campaign basics - Named, budgeted, goal-oriented
4. Assets - Text customization enabled for better relevance

### ⚠️ What Needs Immediate Attention:
1. **Bidding strategy** - Manual CPC required (currently Maximize Conversions with 0 data)
2. **Negative keywords** - ZERO configured = 15-25% budget waste
3. **Account auto-apply** - Status unknown, should be disabled
4. **Quality Score** - Unknown, needs monitoring after negatives deployed

### 📊 Estimated Business Impact:
```
Current monthly budget: ₹12,000 (₹400/day)
Estimated waste without negative keywords: ₹1,800-3,000/month
With negative keyword implementation: 
  - Save: ₹1,800-3,000/month  
  - Quality score +1-2 points
  - Faster path to conversions

Annual savings from this audit: ₹21,600-36,000
```

---

## PART 7: NEXT STEPS

### Immediate Action Required:

1. **Today:** Implement bidding strategy change (Manual CPC, ₹75 bid)
2. **Today:** Create negative keyword lists from Section 2.2
3. **This week:** Apply negative keyword lists to campaign
4. **Ongoing:** Weekly monitoring and keyword refinement

### Success Criteria:
- ✅ Campaign receives impressions and clicks within week 1
- ✅ CTR improves to 3-5% within week 2
- ✅ First conversion achieved within week 2-3
- ✅ Quality Score improves by +1-2 points within week 3

---

## Appendix A: Negative Keywords Master List (Copy-Paste Ready)

### LIST 1: Generic & Irrelevant Intent
```
tips
how to
how-to
recipe
recipes
health benefits
medicinal uses
nutritional value
uses of
"spice tips"
"cooking tips"
"health benefits of"
"how to use"
"spice recipes"
```

### LIST 2: Competitor Brands
```
MDH
Everest
Badshah
Shan
Natco
Aachi
Priya
Eastern
Asha
Tata Sampann
"MDH spices"
"Everest spices"
"Badshah masala"
"Shan masala"
```

### LIST 3: Low-Intent Modifiers
```
free
cheap
lowest price
discount
offer
sale
coupon
samples
sample
trial
"free shipping"
"cheap spices"
"lowest price"
"bulk discount"
"trial pack"
"free sample"
```

### LIST 4: Brand Protection (Discount Combos)
```
"pureleven sale"
"pureleven discount"
"pureleven offer"
"pureleven cheap"
"pureleven low price"
"pureleven free shipping"
"pureleven vs MDH"
"pureleven vs Everest"
"pureleven sample"
"pureleven free trial"
pureleven coupon
pureleven deal
pureleven offer code
```

### LIST 5: Unrelated Categories
```
chaat
chaat masala
baking
dessert
cake
synthetic
artificial
plastic
decor
incense
perfume
medicine
pharmacy
homeopathy
"spices for chaat"
"baking spices"
"cake decorating"
"home decor"
"room fragrance"
"ayurvedic medicine"
"herbal medicine"
```

---

## Report Conclusion

This campaign is **well-positioned geographically and network-wise** but **vulnerable to budget waste** without negative keywords and proper bidding setup. Implementing the recommendations in this report is expected to:

- **Reduce budget waste:** 15-25% savings (₹1,800-3,000/month)
- **Improve quality:** Quality Score +1-2 points within 3 weeks
- **Accelerate conversions:** Reach first conversion 1-2 weeks earlier
- **Establish baseline:** Create clean performance data for scaling

**Recommended Action:** Begin implementation TODAY with bidding strategy change and negative keyword list creation.

---

**Report Prepared:** May 17, 2026  
**Report Status:** Ready for Implementation  
**Next Review:** May 24, 2026 (after 1 week)
