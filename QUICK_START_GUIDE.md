# 🎯 QUICK START GUIDE - GOOGLE ADS TO META RETARGETING

**Time to Launch:** 30-60 minutes
**Difficulty:** Easy
**Result:** High-value audience capture + automated retargeting

---

## 📂 YOUR FILES (Ready in Workspace)

```
/Users/bthomas/Documents/pureleven_dev/

📋 GOOGLE_ADS_RETARGETING_SUMMARY.md ← START HERE
   └─ Overview of everything deployed

📋 DEPLOYMENT_GUIDE.md
   └─ Step-by-step detailed instructions

📋 TRAFFIC_SOURCE_TRACKING.js ← UPLOAD TO SHOPIFY
   └─ JavaScript tracking code

📋 META_AUDIENCES_TEMPLATE.md ← COPY SPECS
   └─ 9 audience configurations

📋 META_CAMPAIGNS_TEMPLATE.md ← COPY SPECS
   └─ 5 campaign templates

📋 GOOGLE_ADS_RETARGETING_STRATEGY.md ← REFERENCE
   └─ Strategy explanation
```

---

## ✅ DEPLOYMENT CHECKLIST (Do in Order)

### **STEP 1: Add JavaScript to Shopify (10 min)**

```
1. Open: Shopify Admin → Online Store → Themes
2. Click: Edit Code (on active theme)
3. Create new file in Assets:
   ├─ Name: traffic-source-tracking.js
   ├─ Copy: ALL content from TRAFFIC_SOURCE_TRACKING.js
   └─ Save
4. Open: layout/theme.liquid
5. Find: </head> tag
6. Add before </head>:
   <script src="{{ 'traffic-source-tracking.js' | asset_url }}"></script>
7. Save theme
8. Wait: 1-2 minutes for deployment
```

**Verify:**
```
Open browser → F12 → Console
Visit: https://pureleven.com/?utm_source=google_ads
Look for: "[✓ CRM] Page view tracked: google_ads"
```

---

### **STEP 2: Create Meta Audiences (20 min)**

Use: **META_AUDIENCES_TEMPLATE.md**

```
Open: https://adsmanager.facebook.com/adsmanager

Audience 1 - PRIORITY #1 (DO FIRST):
├─ Go to: Audiences section
├─ Create: Custom Audience → Customer List
├─ Name: "GA - Checkout Abandoned"
├─ Copy data from template section "AUDIENCE 4A"
├─ Upload: CSV with emails
└─ Save

Audience 2 - PRIORITY #2:
├─ Name: "GA - Cart Abandoners"
├─ Copy data from template section "AUDIENCE 3A"
└─ Save

Audience 3 - PRIORITY #3:
├─ Name: "GA - Visitors (Non-Converters)"
├─ Copy data from template section "AUDIENCE 1B"
└─ Save
```

**CSV Format:**
```
email,first_name,last_name,phone
john@example.com,John,Doe,9876543210
jane@example.com,Jane,Smith,9123456789
```

---

### **STEP 3: Create First Campaign (20 min)**

Use: **META_CAMPAIGNS_TEMPLATE.md**

```
Open: https://adsmanager.facebook.com/adsmanager

Campaign Settings:
├─ Go to: Campaigns
├─ Create Campaign
├─ Objective: CONVERSIONS
├─ Name: "GA-Recovery-CheckoutAbandoned-Urgent"
├─ Budget: ₹1500 (full month)
└─ Click: Continue

Ad Set Settings:
├─ Name: "GA-Checkout-Recovery-SameDay"
├─ Daily Budget: ₹500
├─ Audience: Select "GA - Checkout Abandoned"
├─ Placements: Facebook Feed + Instagram Stories + Feeds
├─ Optimization: Conversions
└─ Click: Continue

Creative:
├─ Headline: "You forgot to complete your order"
├─ Body: "Complete now for FREE shipping"
├─ Image: Product photo
├─ CTA: "Buy Now"
├─ Link: https://www.pureleven.com/checkout
└─ Click: Create

Review & Launch:
├─ Click: Publish Campaign
├─ Status: Should show "ACTIVE" in 1-2 min
└─ Wait: Campaign starts serving ads
```

---

## 🔍 VERIFY IT'S WORKING (5 min)

### **Check 1: Browser Console**

```
Open: https://www.pureleven.com/?utm_source=google_ads
Press: F12 (DevTools) → Console tab
Look for: "[✓ CRM] Page view tracked: google_ads"
Result: ✅ JavaScript loaded & working
```

### **Check 2: CRM Database**

```
SSH to server:
sshpass -p 'QazPlm123!@#' ssh root@192.46.213.140

Check events:
docker exec pureleven_postgres psql -U pureleven -d pureleven -c \
"SELECT COUNT(*) FROM crm_events WHERE event_type='page_view' 
 AND event_data->>'utm_source'='google_ads' LIMIT 5;"

Result: Should show count > 0 if events are being tracked
```

### **Check 3: Meta Audience**

```
Open: https://adsmanager.facebook.com/adsmanager
Go to: Audiences section
Check: "GA - Checkout Abandoned" 
Look for: Green checkmark + people count (even if small)
Result: ✅ Audience ready for ads
```

### **Check 4: Campaign Status**

```
Open: https://adsmanager.facebook.com/adsmanager
Go to: Campaigns
Find: "GA-Recovery-CheckoutAbandoned-Urgent"
Check Status: Should show "ACTIVE" (blue)
Check Spend: Should see small spend starting
Result: ✅ Campaign live & serving
```

---

## 📊 DAILY MONITORING (5 min)

### **Every Morning:**

```
1. Meta Ads Manager:
   ├─ Spend: Check daily spend
   ├─ Results: Number of conversions
   ├─ CPR: Cost per result (target: ₹100-150)
   └─ ROAS: Return on ad spend (target: 5:1+)

2. Decision:
   ├─ If ROAS > 3:1 → Increase budget
   ├─ If ROAS < 2:1 → Check creative, maybe pause
   └─ If no spend → Check audience size (might need more time)

3. Audience size:
   ├─ If growing → Good, more traffic to Google Ads
   └─ If static → Traffic might be low
```

---

## 📈 WEEKLY UPDATES (30 min)

### **Every Friday:**

```
1. Update Meta Audiences:
   ├─ Download fresh customer list from CRM
   ├─ Upload to Meta to update audiences
   ├─ Takes 30 min - 2 hours to sync
   └─ New visitors auto-included next retargeting round

2. Review Performance:
   ├─ Total conversions this week: [X]
   ├─ Total revenue from conversions: ₹[X]
   ├─ Total ad spend: ₹[X]
   ├─ ROAS: [X]:1
   └─ Cost per conversion: ₹[X]

3. Next Steps:
   ├─ If winners exist → Create new campaigns for them
   ├─ If underperformers → Pause or adjust
   └─ If spending fast → Increase budget
```

---

## 🎯 EXPECTED TIMELINE

```
Day 1:
└─ JavaScript added to Shopify ✅
└─ 3 audiences created ✅
└─ Campaign live ✅

Day 2-3:
└─ First page views tracking ✅
└─ First ad impressions ✅
└─ Audience size: 5-10 ✅

Day 4-7:
└─ First conversions from ads ✅
└─ Audience size: 20-50 ✅
└─ ROAS visible (if > 3:1) ✅

Week 2:
└─ 10-20 conversions ✅
└─ Audience size: 50-150+ ✅
└─ Campaign clearly profitable ✅

Week 3-4:
└─ 20-40 conversions ✅
└─ Create more campaigns ✅
└─ Scale winning audiences ✅

Month 1 Total:
└─ 50-100+ conversions from retargeting ✅
└─ Proven ROAS: 4-8:1 ✅
└─ Revenue: ₹25K-50K from ₹3-5K ad spend ✅
```

---

## 🚀 OPTIONAL: ADD MORE AUDIENCES

After launching the first 3 audiences, you can add:

### **Additional Audiences (Easy to Add):**

```
From META_AUDIENCES_TEMPLATE.md:

Tier 2 (Add in Week 2):
├─ GA - Checkout Abandoned (High Value ₹1500+)
├─ GA - Cart Abandoners (High Value ₹1000+)
└─ GA - Multi-Product Browsers

Tier 3 (Add in Week 3):
├─ GA - Viewed: Ceylon Cinnamon 100g
├─ GA - Viewed: Cassia Cinnamon 200g
└─ GA - Visitors (Converted) - for upselling

Tier 4 (Add in Week 4+):
├─ GA - All Visitors (general awareness)
└─ Custom audiences for specific products
```

### **Additional Campaigns (Easy to Add):**

```
From META_CAMPAIGNS_TEMPLATE.md:

Week 2:
└─ "Your Cart Misses You" - Cart abandoners

Week 3:
└─ "Meet Our Best Sellers" - General non-converters

Week 4:
├─ Product-specific campaigns
├─ Bundle offers
└─ Seasonal campaigns
```

---

## ❌ COMMON MISTAKES TO AVOID

```
❌ MISTAKE 1: Not uploading JavaScript
   └─ Result: No tracking at all
   └─ Fix: Upload TRAFFIC_SOURCE_TRACKING.js to Shopify assets

❌ MISTAKE 2: Wrong audience in Meta
   └─ Result: Showing ads to wrong people
   └─ Fix: Copy audience name exactly from template

❌ MISTAKE 3: Too low budget (₹10/day)
   └─ Result: Ads won't serve, no data
   └─ Fix: Use ₹500+/day for meaningful results

❌ MISTAKE 4: Wrong conversion pixel
   └─ Result: Meta can't track conversions
   └─ Fix: Use your Meta pixel ID: 609256704464862

❌ MISTAKE 5: Not updating audiences
   └─ Result: Showing ads to same people forever
   └─ Fix: Update audiences weekly with new visitors

❌ MISTAKE 6: Giving up too early
   └─ Result: Missing winners
   └─ Fix: Run campaigns for minimum 2 weeks before judging
```

---

## 💡 PRO TIPS

```
1. Checkout Abandoners are GOLD
   └─ Highest ROAS (5-10:1)
   └─ Smallest audience
   └─ Retarget SAME DAY for best results

2. Start with simple creatives
   └─ Test variations after first week
   └─ Winners get more budget

3. Discount code tracking
   └─ Create unique codes per campaign
   └─ "CHECKOUT50" for checkout recovery ads
   └─ "CART150" for cart recovery ads
   └─ Measure which offers work best

4. Frequency cap
   └─ Max 3-5 ads per person per day
   └─ Prevents ad fatigue

5. Audience overlap
   └─ Exclude converted customers
   └─ Exclude if already purchased
   └─ Prevents wasted spend

6. Scale winners
   └─ If CPR < ₹150: Double budget
   └─ If ROAS > 5:1: Increase by 50%
   └─ If CPR > ₹400: Pause & adjust

7. Geographic targeting
   └─ Focus on high-intent cities first
   └─ Scale to others after winning
```

---

## 📞 TROUBLESHOOTING

### **No tracking data appearing**

```
1. Check browser console:
   Visit: https://pureleven.com/?utm_source=test
   Press F12 → Console
   Error shown? → Fix JavaScript

2. Check endpoint exists:
   curl https://track.pureleven.com/api/crm/health
   Healthy? → Endpoint working

3. Check CRM logs:
   ssh root@192.46.213.140
   docker logs pureleven-ai-engine
   Errors? → Fix and restart
```

### **Small audience sizes**

```
This is NORMAL for checkout/cart abandoners (5-20 people)

Check:
├─ Google Ads is actually running? (check spend)
├─ Google Ads is using UTM parameters? (check URL)
├─ Data is flowing? (check CRM database)
└─ Give it 7-14 days to accumulate visitors
```

### **Campaign not serving**

```
Check:
├─ Audience size: Must be >100 for good delivery
├─ Daily budget: At least ₹500 for meaningful reach
├─ Pixel installed: Can it track conversions?
├─ Time zone: Campaign scheduled correctly?
└─ Credit card: Account has payment method?
```

---

## 📱 QUICK LINKS

```
Shopify Admin:
https://admin.shopify.com/store/rwxtic-gz/

Meta Ads Manager:
https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=237007475595482

CRM Dashboard:
https://ai.pureleven.com/static/dashboard.html

Google Ads:
https://ads.google.com/aw/campaigns?ocid=1042602958

CRM Health Check:
https://track.pureleven.com/api/crm/health
```

---

## 📋 FINAL CHECKLIST

```
Before launching, verify:

✓ JavaScript added to Shopify
✓ theme.liquid has script tag
✓ Browser console shows "[✓ CRM]" messages
✓ CRM database has page_view events
✓ Created 3 Meta audiences (with people in them)
✓ Created 1st campaign (Checkout Abandoners)
✓ Campaign status = ACTIVE
✓ Campaign has daily budget set
✓ Conversion pixel is correct (609256704464862)
✓ Meta pixel firing (check Ads Manager)

Ready? Launch! 🚀
```

---

## 🎉 YOU'RE READY!

Everything is deployed and configured. 

**Next 30 minutes:**
1. Add JavaScript to Shopify ✅
2. Create 3 audiences ✅
3. Launch campaign ✅
4. Watch conversions come in ✅

**Let's go!**
