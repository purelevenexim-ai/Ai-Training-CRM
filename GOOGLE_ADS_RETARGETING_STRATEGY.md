# 🎯 GOOGLE ADS → META RETARGETING STRATEGY
**Complete Guide to Capturing & Retargeting High-Value Google Ads Visitors**

---

## 📖 STRATEGY OVERVIEW

Your Google Ads bring **high-value, high-intent traffic** to Pureleven. Many visitors don't convert on first visit, but they've already shown they're interested. 

**This strategy captures those visitors and retargets them with Meta ads multiple times until they convert.**

---

## 🎯 THE PROBLEM YOU'RE SOLVING

```
Current Situation:
├─ Google Ads brings interested visitors
├─ Some convert immediately ✅
└─ Many DON'T convert on first visit ❌
   └─ Lost opportunity!
   └─ No way to reach them again
   └─ No second chance to sell

Cost:
├─ Each click costs you (₹5-10 per click on average)
├─ Only 10-20% convert immediately
└─ 80-90% leave without buying
   └─ Wasted spend!
```

---

## ✅ THE SOLUTION: RETARGETING

```
With Retargeting:
├─ Google Ads brings interested visitors
├─ JavaScript captures them: "This person came from Google Ads"
├─ CRM records: Email + traffic source + actions
├─ Meta retargeting campaigns show ads again
│  ├─ Day 1: "You seemed interested..."
│  ├─ Day 3: "Here's a special offer..."
│  └─ Day 7: "Last chance..."
└─ More conversions from same visitor
   └─ Second touch = higher conversion rate
   └─ Same person, different message = better result
```

---

## 💰 EXPECTED FINANCIAL IMPACT

### **Before Retargeting:**
```
Google Ads spend:    ₹10,000/month
Google Ads clicks:   1,000 clicks
Conversion rate:     15% (150 conversions)
Revenue:             ₹75,000 (₹500 AOV × 150)
ROAS:                7.5:1

Visitors lost:       850 people (didn't convert)
Potential lost revenue: ₹42,500 (850 × ₹500 avg)
```

### **After Retargeting:**
```
Google Ads spend:    ₹10,000/month (same)
Google Ads clicks:   1,000 clicks (same)
Direct conversions:  150 (same as before)

Retargeting spend:   ₹3,000/month (new investment)
Retargeting conversions: 30-50 (from the 850 who didn't convert)
Additional revenue:  ₹15,000-₹25,000

Total spend:         ₹13,000
Total revenue:       ₹90,000-₹100,000 (vs ₹75,000 before)
Additional profit:   ₹12,000-₹22,000 per month! 🎉

New ROAS:
├─ Google Ads: Still 7.5:1 ✅
└─ Retargeting: 5:1-8:1 (excellent!)
```

---

## 🔄 HOW IT WORKS (The Flow)

### **Step 1: Visitor Lands from Google Ads**

```
User clicks your Google Ads ad (with UTM params):
https://pureleven.com/?utm_source=google_ads&utm_campaign=search_kerala_spices

Page loads...
```

### **Step 2: JavaScript Captures Data**

```
TRAFFIC_SOURCE_TRACKING.js fires automatically:
├─ Reads URL: UTM params
│  └─ utm_source = "google_ads"
│  └─ utm_campaign = "search_kerala_spices"
├─ Detects page type: Product page, checkout, etc.
├─ Captures email: If customer logged in
└─ Records device: Browser, OS, resolution
```

### **Step 3: CRM Receives & Stores Data**

```
POST https://track.pureleven.com/api/crm/events/page_view

Data stored in PostgreSQL:
├─ Customer record created
├─ Marked: traffic_source = "google_ads"
├─ Tracked: All actions (view, cart, checkout)
└─ Timestamp: When they visited
```

### **Step 4: Nightly Sync to Meta**

```
CRM exports audiences:
├─ "GA - Checkout Abandoned" (⚠️ hot audience)
├─ "GA - Cart Abandoners" (warm audience)
└─ "GA - Visitors (Non-Converters)" (cold audience)

Meta receives audience:
├─ Email list updated
├─ Match rate: 70-90% (Meta matches to Facebook users)
├─ Size: Grows daily as more visitors arrive
```

### **Step 5: Meta Serves Retargeting Ads**

```
Meta Ads Manager automatically:
├─ Shows ads to "GA - Checkout Abandoned" TODAY
│  └─ Message: "You forgot to complete your order"
├─ Shows ads to "GA - Cart Abandoners" (Day 1-7)
│  └─ Message: "Your items are waiting"
├─ Shows ads to "GA - Visitors (Non-Converters)" (Day 2-30)
│  └─ Message: "Here's why our spices are special"
└─ Tracks which people click + convert
```

### **Step 6: Conversions Recorded**

```
Customer clicks retargeting ad and buys:
├─ Meta tracks: Conversion event
├─ CRM records: Purchase from traffic_source="google_ads"
├─ Revenue: Attributed to Google Ads (actually assisted by Meta)
└─ ROI calculated: Shows retargeting is profitable
```

---

## 🎯 WHY THIS WORKS

### **Psychological Reason:**

```
First Visit (Google Ads):
├─ Visitor is AWARE but maybe not READY
├─ Needs time to decide
├─ May have comparison shopping

Retargeting Ads (Meta - Day 1-3):
├─ Visitor sees your ad again
├─ Reduces psychological friction
├─ Creates "social proof" (everyone's buying it)
├─ Triggers FOMO (fear of missing out)
└─ Result: More likely to buy NOW

Retargeting Ads (Meta - Day 4-7):
├─ If still not converting
├─ Show testimonials
├─ Show special offer
├─ Show free shipping
└─ Remove last objection to purchase
```

### **Statistical Reason:**

```
Conversion Rate by Touch:
├─ 1st touch (Google Ads): 10-15%
├─ 2nd touch (Meta retarget): +5-10%
├─ 3rd touch (Meta retarget): +2-5%
├─ Total: 17-30% conversion rate! 🎉

This is why multi-touch marketing works:
└─ Most purchases need multiple touches
```

---

## 📊 AUDIENCE BREAKDOWN

### **Audience 1: Checkout Abandoners (GOLD 🏆)**

```
Who are they?
├─ Entered checkout
├─ Added payment/shipping info
└─ Didn't click "Complete Purchase"

Why they matter:
├─ 99% ready to buy
├─ Only small friction stopped them
├─ Recovery rate: 20-30% (highest!)
├─ AOV: Same as your average (₹500+)

Recovery rate typical obstacles:
├─ Unexpected shipping cost (40%)
├─ Complicated checkout (20%)
├─ Wanted to compare more (20%)
├─ Preferred different payment method (20%)

ROAS for this audience: 5-10:1 ⭐⭐⭐⭐⭐
```

### **Audience 2: Cart Abandoners (SILVER 🥈)**

```
Who are they?
├─ Added items to cart
├─ Didn't proceed to checkout
└─ Left the site

Why they matter:
├─ 50% ready to buy
├─ Need reassurance or incentive
├─ Recovery rate: 15-20%
├─ AOV: Usually same as average

Reasons for abandonment:
├─ Wanted to think about it (40%)
├─ Price too high (30%)
├─ Found competitor (15%)
├─ Distracted, forgot (15%)

ROAS for this audience: 4-6:1 ⭐⭐⭐⭐
```

### **Audience 3: Non-Converters (BRONZE 🥉)**

```
Who are they?
├─ Visited from Google Ads
├─ Didn't add to cart or checkout
└─ Just browsed

Why they matter:
├─ 10% ready to buy
├─ Need education or inspiration
├─ Conversion rate: 4-10%
├─ Largest audience size

Reasons for non-conversion:
├─ Comparison shopping (40%)
├─ Need more info about product (30%)
├─ Not urgent/impulse buy (20%)
├─ Wrong offer or positioning (10%)

ROAS for this audience: 2-4:1 ⭐⭐⭐
```

---

## 🎬 CAMPAIGN STRUCTURE

### **Campaign 1: "Complete Your Purchase" (Checkout Abandoners)**

**Timeline: Days 0-7**

```
Ad Set 1 - DAY 0-1 (ASAP):
├─ Message: "You forgot to complete your order"
├─ Offer: Free shipping
├─ Creative: Product image + checkout button
├─ Frequency: 2-3 ads/person/day
└─ Expected conversion: 20-30% of audience

Ad Set 2 - DAY 2-3 (Reassurance):
├─ Message: "Trusted by 500+ customers | 5-star reviews"
├─ Offer: Same
├─ Creative: Customer testimonials
├─ Frequency: 2 ads/person/day
└─ Expected conversion: +5-10% (incremental)

Ad Set 3 - DAY 4-7 (Urgency):
├─ Message: "Limited stock | Order within 24 hours"
├─ Offer: ₹200 discount
├─ Creative: Time-limited banner
├─ Frequency: 1-2 ads/person/day
└─ Expected conversion: +2-5% (last chance)
```

**Expected Results:**
```
Audience size: 20 people/week
Conversions: 5-6 people (27% rate)
Revenue: ₹2,500-₹3,000
Cost: ₹150 (₹500/week budget)
ROAS: 17:1 ⭐⭐⭐⭐⭐
```

### **Campaign 2: "Your Cart Misses You" (Cart Abandoners)**

**Timeline: Days 1-14**

```
Ad Set 1 - DAY 1-3 (Gentle reminder):
├─ Message: "Your cart has great items"
├─ Offer: Free shipping ₹500+
├─ Frequency: 2 ads/person/day
└─ Expected conversion: 10-12%

Ad Set 2 - DAY 4-10 (Incentive):
├─ Message: "Exclusive ₹150 off your order"
├─ Offer: ₹150 discount code
├─ Frequency: 2 ads/person/day
└─ Expected conversion: +3-5%

Ad Set 3 - DAY 11-14 (Final call):
├─ Message: "Final chance | Prices changing tomorrow"
├─ Offer: Lock in current price
├─ Frequency: 1 ad/person/day
└─ Expected conversion: +2-3%
```

**Expected Results:**
```
Audience size: 50 people/week
Conversions: 8-10 people (18% rate)
Revenue: ₹4,000-₹5,000
Cost: ₹200 (₹1000/week budget)
ROAS: 20-25:1 ⭐⭐⭐⭐⭐
```

### **Campaign 3: "Meet Our Best Sellers" (Non-Converters)**

**Timeline: Days 1-30**

```
Ad Set 1 - WEEK 1 (Education):
├─ Message: "Why pure organic cinnamon matters"
├─ Content: Benefits, sourcing, quality
├─ Frequency: 1-2 ads/person/day
└─ Expected conversion: 2-3%

Ad Set 2 - WEEK 2 (Collection):
├─ Message: "Browse our complete spice collection"
├─ Content: Carousel of 5-8 products
├─ Frequency: 1-2 ads/person/day
└─ Expected conversion: +1-2%

Ad Set 3 - WEEK 3 (Social Proof):
├─ Message: "Trusted by 1000+ Indian households"
├─ Content: Customer reviews, ratings
├─ Frequency: 1-2 ads/person/day
└─ Expected conversion: +2-3%

Ad Set 4 - WEEK 4 (Offer):
├─ Message: "First-time customers: ₹100 off"
├─ Content: Special promo code
├─ Frequency: 1-2 ads/person/day
└─ Expected conversion: +1-2%
```

**Expected Results:**
```
Audience size: 150 people/week
Conversions: 9-15 people (8% rate)
Revenue: ₹4,500-₹7,500
Cost: ₹500 (₹2000/week budget)
ROAS: 9-15:1 ⭐⭐⭐⭐⭐
```

---

## 📈 MONTHLY PROJECTIONS

### **Month 1:**
```
Google Ads spend:            ₹10,000
Google Ads conversions:      150
Google Ads revenue:          ₹75,000

Retargeting spend:           ₹3,000
Retargeting conversions:     35
Retargeting revenue:         ₹17,500

TOTAL:
├─ Spend: ₹13,000
├─ Revenue: ₹92,500
├─ Profit: ₹79,500
└─ ROAS: 7.1:1
```

### **Month 2-3 (Scaling):**
```
Same Google Ads
Same base conversions: 150

Optimized Retargeting:
├─ Bigger audience (accumulated visitors)
├─ Better targeting
├─ Higher conversion rates
├─ Conversions: 50-60
└─ Revenue: ₹25,000-₹30,000

TOTAL:
├─ Spend: ₹13,000
├─ Revenue: ₹100,000-₹105,000
├─ Profit: ₹87,000-₹92,000
└─ ROAS: 7.7-8:1
```

---

## 🚀 IMPLEMENTATION CHECKLIST

### **Week 1: Setup**
- [ ] Add JavaScript to Shopify theme
- [ ] Test tracking with UTM params
- [ ] Verify CRM is recording events
- [ ] Create 3 Meta audiences

### **Week 2: Launch**
- [ ] Create "Complete Your Purchase" campaign
- [ ] Set budget: ₹500/day
- [ ] Launch campaign
- [ ] Monitor daily conversions

### **Week 3: Expand**
- [ ] Create "Your Cart Misses You" campaign
- [ ] Create "Meet Our Best Sellers" campaign
- [ ] Monitor ROAS by campaign
- [ ] Pause underperformers

### **Week 4+: Optimize**
- [ ] Scale winners (double budget if ROAS > 5:1)
- [ ] Add product-specific audiences
- [ ] Test new creatives
- [ ] Measure attribution

---

## ⚡ QUICK WINS

### **Quick Win #1: Checkout Abandoners (Day 1)**
```
Setup: 30 minutes
Expected revenue: ₹2,500-₹3,000
Cost: ₹150
ROI: 1600-2000%
Time to payoff: Same day!
```

### **Quick Win #2: Cart Abandoners (Week 1)**
```
Setup: 30 minutes
Expected revenue: ₹4,000-₹5,000
Cost: ₹200
ROI: 1900-2400%
Time to payoff: Same week!
```

### **Quick Win #3: Non-Converters (Week 2)**
```
Setup: 45 minutes
Expected revenue: ₹4,500-₹7,500
Cost: ₹500
ROI: 800-1400%
Time to payoff: 3-4 days
```

---

## 🎯 SUCCESS METRICS

```
Track these numbers:

Weekly:
├─ Audience growth: How many new visitors?
├─ Conversions: How many from retargeting?
├─ Revenue: How much did they spend?
├─ ROAS: (Revenue ÷ Spend)
└─ CPR: Cost Per Result

Monthly:
├─ Total conversions from retargeting
├─ Total revenue from retargeting
├─ Comparison: Google Ads vs Retargeting
├─ Which audience performs best?
└─ Which creative gets best results?

Targets:
├─ Checkout Abandoned ROAS: 5:1+
├─ Cart Abandoned ROAS: 4:1+
├─ Non-Converters ROAS: 2:1+
└─ Overall: 3:1+ average
```

---

## 💡 KEY INSIGHTS

```
1. Speed matters (Checkout Abandoners)
   └─ Retarget within 24 hours for best results

2. Audience size grows over time
   └─ Week 1: Tiny audiences (10-20 people)
   └─ Week 4: Larger audiences (50-200 people)
   └─ Week 8+: Significant audiences (300-1000 people)

3. Test and optimize relentlessly
   └─ Winners get more budget
   └─ Losers get paused
   └─ New creatives tested constantly

4. Different audiences need different messages
   └─ Checkout abandoned: "Complete your order"
   └─ Cart abandoned: "Items waiting"
   └─ Non-converters: "Here's why we're great"

5. Frequency cap prevents ad fatigue
   └─ Max 3-5 ads per person per day
   └─ Remove after 30 days inactive
   └─ Clean audiences = better ROI

6. Attribution is complex
   └─ Someone may click Google Ads, think about it
   └─ See Meta retargeting ad, convert
   └─ Both should get credit (assisted conversion)
   └─ Track both channels together
```

---

## 🎉 FINAL THOUGHT

**You're not losing money with Google Ads - you're buying awareness.**

With retargeting, you're converting that awareness into sales.

**This strategy turns window shoppers into customers.**

---

**Ready to implement? Start with QUICK_START_GUIDE.md!**
