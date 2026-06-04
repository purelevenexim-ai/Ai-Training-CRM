# 🚀 META VISITOR RETARGETING - QUICK IMPLEMENTATION GUIDE

## WHAT YOU'RE CREATING TODAY

You're creating **Meta retargeting campaigns specifically for people who clicked your Meta/Facebook ads**.

Think of it like this:
- **Google Ads Visitor Retargeting** (already done): People who searched for cinnamon and clicked your Google ad → see Meta ads
- **Meta Visitor Retargeting** (NEW): People who saw your post and clicked your Meta ad → see more Meta ads with different angles

---

## YOUR 4-STEP LAUNCH CHECKLIST

### ✅ STEP 1: Create Meta Visitor Audiences (1 hour)

**What to do:**
1. Open [Meta Ads Manager](https://adsmanager.facebook.com/)
2. Click **Audiences** (left menu)
3. Click **Create Audience** → **Custom Audience** → **Customer List**
4. Create these 3 audiences first (PRIORITY):

**Audience 1: "Meta - Checkout Abandoned"**
```
File to reference: META_AUDIENCES_TEMPLATE_META_VISITORS.md
Section: AUDIENCE 4A

Copy these specs:
├─ Audience Name: Meta - Checkout Abandoned
├─ Description: People from Meta ads who started checkout
├─ Filter: utm_source = "facebook" (from your CRM)
├─ Event: checkout_initiated, no purchase
├─ Time window: Last 3 days
└─ Expected size: 5-20 people/week

CSV Format:
email,first_name,last_name,phone
john@example.com,John,Doe,9876543210
jane@example.com,Jane,Smith,9123456789
```

**Audience 2: "Meta - Cart Abandoners"**
```
File to reference: META_AUDIENCES_TEMPLATE_META_VISITORS.md
Section: AUDIENCE 3A

Copy these specs:
├─ Audience Name: Meta - Cart Abandoners  
├─ Description: People from Meta ads who added items to cart
├─ Filter: utm_source = "facebook"
├─ Event: cart_added, no purchase
├─ Time window: Last 7 days
└─ Expected size: 20-50 people/week
```

**Audience 3: "Meta - Visitors (Non-Converters)"**
```
File to reference: META_AUDIENCES_TEMPLATE_META_VISITORS.md
Section: AUDIENCE 1B

Copy these specs:
├─ Audience Name: Meta - Visitors (Non-Converters)
├─ Description: People from Meta ads who haven't purchased
├─ Filter: utm_source = "facebook"
├─ Status: VISITOR (not customer)
├─ Time window: Last 90 days
└─ Expected size: 60-80% of all Meta visitors
```

**How to upload CSV:**
1. Go to Meta Ads Manager → Audiences
2. Click "Create Audience" → "Custom Audience"
3. Select "Customer List"
4. Paste CSV data or upload file
5. Map columns: email, first_name, last_name, phone
6. Name the audience and save

---

### ✅ STEP 2: Launch Checkout Recovery Campaign (1 hour)

**What to do:**
1. Open Meta Ads Manager
2. Click **Create** (blue button, top left)
3. Select objective: **Conversions**

**Campaign Details:**

```
Campaign Name: Meta-Recovery-CheckoutAbandoned-Urgent

Budget: ₹500-1,000/week (start smaller for testing)

Audience: Meta - Checkout Abandoned
├─ Audience size: 5-20 people/week
├─ Custom audience: Select "Meta - Checkout Abandoned"
└─ Placement: Instagram Feed + Facebook Feed

Duration: Run for 7+ days to get meaningful data
```

**Ad Set 1: Same-Day Recovery**

```
Name: Meta-Checkout-Recovery-SameDay
Daily Budget: ₹100-150
Optimization: Conversions
Bid Strategy: Lowest cost

CREATIVE:
├─ Image: Product photo with "You Forgot This" overlay
├─ Headline: "Your Order is Still Waiting!"
├─ Primary Text: 
   "Complete your checkout in 2 seconds. 
    Free shipping inside.
    100% money-back guarantee."
├─ CTA Button: "Buy Now" or "Complete Purchase"
└─ Landing Page: https://pureleven.com/checkout

Expected Results (Week 1):
├─ Impressions: 100-200
├─ Conversions: 0-2
└─ Cost per purchase: ₹500-1,000
```

**Ad Set 2: Reassurance (Add if Budget Available)**

```
Name: Meta-Checkout-Recovery-Reassurance  
Daily Budget: ₹75-100
Optimization: Conversions

CREATIVE:
├─ Image: Customer testimonial or 5-star reviews
├─ Headline: "Join 1000+ Happy Customers"
├─ Primary Text: "Why people love our cinnamon"
├─ CTA: "Learn More" → "Buy Now"
└─ Landing Page: https://pureleven.com/products/...
```

---

### ✅ STEP 3: Monitor Performance Daily (10 min/day)

**Daily Checklist:**

```
Morning:
□ Check if campaign is running
□ Check impressions (should be 30-50 per day)
□ Check clicks (should be 3-7 per day)
□ Look for errors or warnings

Weekly:
□ Check conversions
□ Calculate cost per purchase
□ Check ROAS (revenue ÷ spend)
□ Update audiences with new visitors
□ Pause underperforming ad sets
□ Increase budget if ROAS > 2:1
```

**What to expect:**

```
Day 1-2: 50-100 impressions, 0 conversions (normal)
Day 3-5: 200-300 impressions, 1-2 conversions
Day 7+: 400-500 impressions, 2-4 conversions
Week 2: First clear ROAS signal

GOOD ROAS TARGETS:
├─ Checkout abandoners: 2:1 or better = Success
├─ Cart abandoners: 1.5:1 or better = Success  
└─ Non-converters: 1:1 or better = Success
```

---

### ✅ STEP 4: Create Cart Recovery Campaign (Next Day)

**Follow same process as Checkout Recovery but with:**

```
Audience: Meta - Cart Abandoners
Budget: ₹500-750/week

Ad Set 1: Gentle Reminder
├─ Headline: "Your Cart is Waiting"
├─ CTA: "View Cart"
├─ Message: No urgency, friendly tone

Ad Set 2: Incentive (Optional)
├─ Headline: "₹100 Off Your Order"
├─ Message: "Use code: COMEBACK100"
└─ Discount: Small incentive (₹100)

Expected ROAS: 1.5-2.5:1
```

---

## HOW TO EXPORT FROM YOUR CRM

**You need daily CSV exports from your database:**

```
Every day, export:

FILE 1: meta_checkout_abandoned.csv
├─ Filter: utm_source = "facebook"
├─ Event: checkout_initiated (last 3 days)
├─ Status: NOT purchased yet
├─ Columns: email, first_name, last_name, phone
└─ Upload to: Meta Audience "Meta - Checkout Abandoned"

FILE 2: meta_cart_abandoners.csv
├─ Filter: utm_source = "facebook"
├─ Event: cart_added (last 7 days)
├─ Status: NOT purchased
├─ Columns: email, first_name, last_name, phone
└─ Upload to: Meta Audience "Meta - Cart Abandoners"

FILE 3: meta_non_converters.csv
├─ Filter: utm_source = "facebook"
├─ Status: VISITOR (not CUSTOMER)
├─ Visited: Last 90 days
├─ Columns: email, first_name, last_name, phone
└─ Upload to: Meta Audience "Meta - Visitors (Non-Converters)"
```

**CSV Format (Example):**

```csv
email,first_name,last_name,phone
john@example.com,John,Doe,9876543210
jane@example.com,Jane,Smith,9123456789
amit@example.com,Amit,Kumar,9912345678
priya@example.com,Priya,Singh,7712345678
```

---

## BUDGET ALLOCATION (Month 1)

```
RECOMMENDED SPLIT: ₹2,000-3,000/month for Meta Visitor system

Week 1: Checkout Recovery
└─ ₹700 (test, get data)

Week 2: Checkout Recovery (scale) + Cart Recovery  
└─ ₹1,200 (₹800 checkout + ₹400 cart)

Week 3: Both campaigns running + Monitor
└─ ₹1,500 (optimize winning ads)

Week 4: Scale winners, test Non-Converters
└─ ₹2,000 (₹700 checkout + ₹700 cart + ₹600 non-converters)

If ROAS > 2:1 after Month 1:
└─ Increase to ₹4,000-5,000/month (scale aggressively)

If ROAS < 1.5:1 after Month 1:
└─ Test different creatives, keep at ₹2,000/month
```

---

## CREATIVE IDEAS FOR META VISITOR RETARGETING

### **Checkout Abandoners Ads**

**Headline Ideas:**
- "Your Order is Still Waiting!"
- "Complete Your Checkout in 2 Seconds"
- "₹X Order Expires in 24 Hours"
- "We Saved Your Cart"
- "One More Step to Order"

**Primary Text Ideas:**
```
"Complete your ₹X order now
✓ Free shipping inside India
✓ 100% money-back guarantee  
✓ Express delivery (2-3 days)
Don't miss out on your favorite spices!"

OR

"You were 99% done!
Just 2 steps left to complete your order.
Free shipping guaranteed.
→ Click to finish checkout"
```

**Visual Ideas:**
- Product image with clock overlay
- Product + "Complete Now" button graphic
- Customer testimonial + product
- Product close-up with quality badges

### **Cart Abandoners Ads**

**Headline Ideas:**
- "Your Cart is Waiting"
- "We Saved Your Items"
- "₹100 Off Your Order"
- "Come Back and Save"
- "Your Spices Are Reserved"

**Primary Text Ideas:**
```
"Your cart items:
• Ceylon Cinnamon 100g
• [Item 2]

Complete your order now and get free shipping →"

OR

"Use code COMEBACK100
Get ₹100 off your order
Valid for 48 hours only!
→ Secure your order now"
```

---

## TROUBLESHOOTING

**No impressions showing?**
- Check audience size (need minimum 1,000 people)
- Wait 24-48 hours (Meta needs time to build audience)
- Verify CSV upload was successful
- Check budget (need minimum ₹100/day)

**Impressions but no clicks?**
- Test different images (try product close-up, testimonial, lifestyle)
- Change headline (try shorter, more benefit-focused)
- Test different CTA (try "Buy Now" vs "View Cart")
- Check placement settings

**Clicks but no conversions?**
- Test different landing pages (try product page, home page, checkout)
- Test different offers (try free shipping vs discount)
- Add trust signals (guarantees, reviews, delivery badges)
- Check if tracking pixel is firing

**ROAS too low?**
- Pause underperforming ad sets
- Increase budget on winning ads (>2:1 ROAS)
- Test different creative angles
- Check audience is accurate (right utm_source)

---

## REFERENCE FILES

```
For detailed specs, refer to:

Audiences:
→ META_AUDIENCES_TEMPLATE_META_VISITORS.md

Campaigns:
→ META_CAMPAIGNS_TEMPLATE_META_VISITORS.md

Strategy & Comparison:
→ DUAL_RETARGETING_STRATEGY_GUIDE.md

Google Ads System:
→ META_AUDIENCES_TEMPLATE.md
→ META_CAMPAIGNS_TEMPLATE.md
```

---

## SUCCESS TIMELINE

```
Week 1:
├─ Audiences created ✓
├─ Checkout Recovery campaign live ✓
└─ Getting first impressions ✓

Week 2:
├─ 50-150 conversions across all system
├─ Cart Recovery campaign live ✓
└─ Getting clear ROAS picture

Week 3-4:
├─ Optimizing winning ads
├─ Scaling budget if ROAS > 1.5:1
├─ Adding more audiences
└─ Testing new creatives

Month 2+:
├─ Running 5+ campaigns
├─ Budget: ₹4,000-5,000+
├─ Combined ROAS: 2-4:1
└─ Monthly revenue: ₹8,000-20,000+
```

---

**START HERE: Meta Audience 1 (Checkout Abandoned) - Should take 15 minutes**
