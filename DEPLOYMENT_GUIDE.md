# 🚀 DEPLOYMENT GUIDE - GOOGLE ADS RETARGETING SYSTEM
**Step-by-Step Instructions to Activate Traffic Tracking**

---

## ✅ WHAT'S BEEN DEPLOYED

### **Server-Side (✅ DONE)**
```
✅ CRM Backend: /api/crm/events/page_view endpoint added
   ├─ Location: /opt/pureleven/ai-engine/app/crm_routes.py
   ├─ Status: DEPLOYED & RUNNING
   ├─ Function: Receives page view events with UTM params
   ├─ Database: Stores in crm_events table
   └─ Captures: traffic_source, utm_campaign, page_type, etc.

✅ Docker Container: Restarted successfully
   └─ Status: All endpoints HEALTHY

✅ Backup: Original file backed up before deployment
   └─ Location: /opt/pureleven/ai-engine/app/crm_routes.py.backup_*
```

### **Client-Side (📝 READY TO DEPLOY)**
```
📝 JavaScript Tracking File: TRAFFIC_SOURCE_TRACKING.js
   ├─ Location: /Users/bthomas/Documents/pureleven_dev/TRAFFIC_SOURCE_TRACKING.js
   ├─ Size: ~8KB
   ├─ Dependencies: None (vanilla JS)
   ├─ Browser Support: All modern browsers + IE11
   └─ Status: READY TO UPLOAD TO SHOPIFY

📝 Meta Audiences Template: META_AUDIENCES_TEMPLATE.md
   ├─ Contains: 9 audience types ready to create
   ├─ Status: READY TO USE

📝 Meta Campaigns Template: META_CAMPAIGNS_TEMPLATE.md
   ├─ Contains: 5 campaign templates with exact specs
   ├─ Status: READY TO USE
```

---

## 📋 STEP 1: ADD JAVASCRIPT TO SHOPIFY THEME

### **Option A: Via Shopify Admin (Recommended)**

#### **1.1 Upload tracking script:**

```
1. Go to: Shopify Admin → Online Store → Themes
2. Find: Your active theme (Pureleven)
3. Click: Edit Code
4. Under Assets folder, create NEW file:
   ├─ Name: traffic-source-tracking.js
   ├─ Copy entire content from:
   │  /Users/bthomas/Documents/pureleven_dev/TRAFFIC_SOURCE_TRACKING.js
   └─ Save
```

#### **1.2 Add script tag to theme.liquid:**

```
1. Still in Edit Code
2. Find file: layout/theme.liquid
3. Look for: closing </head> tag
4. Add this line BEFORE </head>:

   <script src="{{ 'traffic-source-tracking.js' | asset_url }}"></script>

5. Save the file
6. Wait 1-2 minutes for deployment
```

**Full example of where to add:**
```liquid
  ...other scripts...
  <script src="{{ 'some-other-script.js' | asset_url }}"></script>
  
  <!-- TRAFFIC SOURCE TRACKING -->
  <script src="{{ 'traffic-source-tracking.js' | asset_url }}"></script>
  
</head>
```

### **Option B: Verify in Theme Settings**

```
1. Shopify Admin → Settings → Files
2. Should see: traffic-source-tracking.js uploaded
3. Status: Active
4. Size: ~8KB
```

---

## ✅ STEP 2: TEST TRACKING IS WORKING

### **Test 1: Check Browser Console**

```
1. Visit: https://www.pureleven.com/?utm_source=google_ads&utm_medium=cpc&utm_campaign=test
2. Open browser DevTools: F12 or Cmd+Option+I
3. Go to Console tab
4. Look for green messages:
   ├─ "[✓ CRM] Page view tracked: google_ads"
   ├─ "[✓ Meta] Pixel fired: PageView"
   └─ "[✓ Email captured]" (if you fill email)
5. No red errors? ✅ Working!
```

### **Test 2: Check CRM Database**

```
SSH to server and verify:

sshpass -p 'QazPlm123!@#' ssh root@192.46.213.140 << 'EOF'

# Check CRM events table
docker exec pureleven_postgres psql -U pureleven -d pureleven -c \
"SELECT event_type, event_data, created_at FROM crm_events 
 WHERE event_type='page_view' 
 ORDER BY created_at DESC LIMIT 5;"

# Should show your test visit with utm_source=google_ads

EOF
```

**Expected output:**
```
event_type | event_data | created_at
-----------|------------|---------------------
page_view  | {"utm_source": "google_ads", ...} | 2026-05-17 15:23:45
```

### **Test 3: Check Meta Pixel Fired**

```
1. Visit site with UTM params
2. Open Meta Pixel debugging:
   ├─ Go to: facebook.com/events_manager
   ├─ Select: Your pixel (609256704464862)
   ├─ Look for: PageView events
   ├─ Should see custom data: utm_source, utm_medium, etc.
   └─ Status: "Received" ✅
```

---

## 📊 STEP 3: CREATE META AUDIENCES (First Batch)

### **Create First 3 Audiences (Start Here):**

**Audience 1: GA - Checkout Abandoned** (PRIORITY)
```
Meta Ads Manager → Audiences → Create Audience
├─ Type: Custom Audience → Customer List
├─ Name: "GA - Checkout Abandoned"
├─ Description: "Google Ads visitors who started checkout but didn't buy"
├─ Data: Upload CSV with emails from CRM:
│  SELECT email FROM crm_customers 
│  WHERE utm_source='google_ads' 
│  AND event_type='checkout_initiated' 
│  AND status='VISITOR'
├─ Retention: 30 days
└─ Click: Create Audience
```

**Audience 2: GA - Cart Abandoners**
```
Meta Ads Manager → Audiences → Create Audience
├─ Type: Custom Audience → Customer List
├─ Name: "GA - Cart Abandoners"
├─ Description: "Google Ads visitors who added items to cart"
├─ Data: Upload CSV with emails from CRM:
│  SELECT email FROM crm_customers 
│  WHERE utm_source='google_ads' 
│  AND event_type='cart_viewed' 
│  AND status='VISITOR'
├─ Retention: 30 days
└─ Click: Create Audience
```

**Audience 3: GA - Visitors (Non-Converters)**
```
Meta Ads Manager → Audiences → Create Audience
├─ Type: Custom Audience → Customer List
├─ Name: "GA - Visitors (Non-Converters)"
├─ Description: "All Google Ads visitors who haven't purchased yet"
├─ Data: Upload CSV with emails from CRM:
│  SELECT email FROM crm_customers 
│  WHERE utm_source='google_ads' 
│  AND status='VISITOR'
├─ Retention: 30 days
└─ Click: Create Audience
```

### **CSV Format to Use:**

```csv
email,first_name,last_name,phone,utm_source
john@example.com,John,Doe,9876543210,google_ads
jane@example.com,Jane,Smith,9123456789,google_ads
```

---

## 🎬 STEP 4: CREATE FIRST META CAMPAIGN

### **Campaign: "Complete Your Purchase - Urgent"**

```
Meta Ads Manager → Campaigns → Create Campaign

CAMPAIGN DETAILS:
├─ Name: "GA-Recovery-CheckoutAbandoned-Urgent"
├─ Objective: CONVERSIONS
├─ Campaign Budget: ₹1500 (for month)
├─ Duration: Starts today, no end date
└─ Click: Continue

AD SET DETAILS:
├─ Name: "GA-Checkout-Recovery-SameDay"
├─ Daily Budget: ₹500/day
├─ Audience: Select "GA - Checkout Abandoned" (from audiences you created)
├─ Placements: 
│  ├─ ✓ Facebook Feed
│  ├─ ✓ Instagram Feed
│  └─ ✓ Instagram Stories
├─ Optimization: Conversions (set up pixel: 609256704464862)
└─ Click: Continue

CREATIVE:
├─ Create New Creative
├─ Headline: "You forgot to complete your order"
├─ Primary Text: "Your ₹[AMOUNT] spice order is waiting. 
                  Complete now and get FREE shipping."
├─ Image: Your product photo or checkout screenshot
├─ Call-to-Action: "Shop Now" or "Buy Now"
├─ Link: https://www.pureleven.com/checkout
└─ Click: Create Ad

REVIEW & LAUNCH:
├─ Review all settings
├─ Click: Publish & Launch Campaign
├─ Wait: Campaign goes live in 1-2 minutes
└─ Status: Should say "ACTIVE"
```

---

## 📈 STEP 5: MONITOR PERFORMANCE

### **Daily Checks (Morning):**

```
Meta Ads Manager:
├─ Go to: Campaigns tab
├─ Look for: GA-Recovery-CheckoutAbandoned-Urgent
├─ Check metrics:
│  ├─ Reach: Audience size
│  ├─ Results: How many conversions
│  ├─ CPR: Cost per result (₹100-150 is good)
│  ├─ Spend: Total spend so far
│  └─ ROAS: Return on ad spend (5:1 is excellent)
│
├─ If ROAS > 3:1: Increase budget
├─ If ROAS < 2:1: Pause & check creative
└─ If no spend: Check audience size (might be too small)
```

### **Weekly Checks (Fridays):**

```
CRM Dashboard:
├─ Go to: https://ai.pureleven.com/static/dashboard.html
├─ Check:
│  ├─ "GA - Checkout Abandoned" audience: [X] new people
│  ├─ "GA - Cart Abandoners" audience: [X] new people
│  ├─ "GA - Visitors (Non-Converters)" audience: [X] new people
│  └─ Conversions from Google Ads visitors: [X] purchases
│
├─ Update audiences in Meta:
│  └─ Download new CSV with this week's visitors
│  └─ Upload to Meta (update audience)
│
└─ Review costs vs conversions:
   ├─ Calculate ROAS: (Revenue from retargeting) / (Ad spend)
   ├─ If profitable: Increase budget
   └─ If not: Adjust creative or offer
```

### **Monthly Review (Last Friday of Month):**

```
Performance Analysis:
├─ Total spend: ₹[X]
├─ Total conversions: [X]
├─ Total revenue: ₹[X]
├─ ROAS: [X]:1
├─ Cost per conversion: ₹[X]
│
├─ By audience:
│  ├─ Checkout Abandoned: ROAS = [X]:1 (best?)
│  ├─ Cart Abandoners: ROAS = [X]:1
│  └─ Non-Converters: ROAS = [X]:1
│
├─ Decisions:
│  ├─ Which audience performs best? (scale it)
│  ├─ Which ads have highest CTR? (duplicate them)
│  ├─ Which ads are unprofitable? (pause them)
│  └─ What to test next month?
│
└─ Next month adjustments:
   ├─ Increase budget for winners
   ├─ Add new audiences
   ├─ Test new creatives
   └─ Refine targeting
```

---

## 🔍 TROUBLESHOOTING

### **Problem: JavaScript not loading**

**Symptoms:** Console shows errors like "fetch is not defined"

**Solution:**
```
1. Clear browser cache: Cmd+Shift+Delete (Chrome)
2. Hard refresh: Cmd+Shift+R
3. Check console for actual errors
4. Verify file exists: 
   Shopify → Settings → Files → search "traffic-source-tracking"
5. Check theme.liquid includes the script tag
```

### **Problem: No events in CRM database**

**Symptoms:** Visit site with UTM params, but no page_view events recorded

**Solution:**
```
1. Check CRM API is responding:
   curl -X GET https://track.pureleven.com/api/crm/health
   └─ Should return: {"status": "healthy"}

2. Check page_view endpoint exists:
   sshpass -p 'QazPlm123!@#' ssh root@192.46.213.140 \
   "grep -n 'page_view' /opt/pureleven/ai-engine/app/crm_routes.py"
   └─ Should show: line number with /events/page_view

3. Check server logs:
   sshpass -p 'QazPlm123!@#' ssh root@192.46.213.140 \
   "docker logs -f pureleven-ai-engine --tail=20"
   └─ Look for POST /api/crm/events/page_view 200

4. If still not working: Restart container
   sshpass -p 'QazPlm123!@#' ssh root@192.46.213.140 \
   "docker restart pureleven-ai-engine"
```

### **Problem: Small audience sizes in Meta**

**Symptoms:** Audience shows < 10 people

**Solution:**
```
1. This is normal for Checkout Abandoned (small, hot audience)
2. For Non-Converters audience, it should be 50-500+ after 1-2 weeks
3. Check CRM has customers:
   SELECT COUNT(*) FROM crm_customers WHERE utm_source='google_ads';
   └─ Should show number > 0

4. If no customers yet:
   ├─ Ensure Google Ads traffic is actually coming
   ├─ Verify UTM params on Google Ads campaign
   ├─ Check Google Ads is funded and running
   └─ Give it 24-48 hours for traffic

5. If audiences not growing:
   ├─ Re-upload CSV to Meta (might be cached)
   ├─ Check CSV format (needs email + headers)
   └─ Ensure CRM is properly tracking
```

---

## 📱 QUICK REFERENCE: FILES CREATED

```
DEPLOYED FILES:

1. CRM Endpoint:
   Location: /opt/pureleven/ai-engine/app/crm_routes.py
   Endpoint: POST /api/crm/events/page_view
   Status: ✅ LIVE

2. JavaScript Tracking:
   File: /Users/bthomas/Documents/pureleven_dev/TRAFFIC_SOURCE_TRACKING.js
   Deploy to: Shopify theme assets
   Status: 📝 READY (not yet in Shopify)

3. Meta Audiences Template:
   File: /Users/bthomas/Documents/pureleven_dev/META_AUDIENCES_TEMPLATE.md
   Status: 📝 READY (use as reference)

4. Meta Campaigns Template:
   File: /Users/bthomas/Documents/pureleven_dev/META_CAMPAIGNS_TEMPLATE.md
   Status: 📝 READY (use as reference)
```

---

## 🎯 SUCCESS CHECKLIST

```
✅ Step 1: JavaScript Uploaded to Shopify
   □ File uploaded: traffic-source-tracking.js
   □ Script tag added to theme.liquid
   □ Theme deployed (wait 1-2 min)

✅ Step 2: Traffic Tracking Verified
   □ Visit site with UTM params
   □ Console shows "[✓ CRM] Page view tracked"
   □ Database shows page_view events
   □ Meta Pixel shows PageView events

✅ Step 3: Meta Audiences Created
   □ "GA - Checkout Abandoned" created
   □ "GA - Cart Abandoners" created
   □ "GA - Visitors (Non-Converters)" created
   □ Audiences show people in them

✅ Step 4: First Campaign Launched
   □ Campaign "GA-Recovery-CheckoutAbandoned" created
   □ Campaign status: ACTIVE
   □ Budget: ₹500/day
   □ Campaign is spending money

✅ Step 5: Monitoring Started
   □ Checking Meta dashboard daily
   □ Tracking conversions
   □ Monitoring ROAS
   □ Ready to scale
```

---

## 🚀 NEXT STEPS

### **Immediately (Today):**
- [ ] Add JavaScript to Shopify theme
- [ ] Test tracking with console
- [ ] Create 3 Meta audiences
- [ ] Launch first campaign

### **This Week:**
- [ ] Monitor campaign performance
- [ ] Check if audiences are growing
- [ ] Create 2nd campaign (Cart Abandoners)
- [ ] Test different ad creatives

### **Next Week:**
- [ ] Create 3rd campaign (Non-Converters)
- [ ] Add product-specific audiences
- [ ] Scale winning audiences
- [ ] Test new targeting

### **Month 2:**
- [ ] Review ROAS metrics
- [ ] Scale top performers
- [ ] Add lookalike audiences
- [ ] Test seasonal campaigns

---

## 💬 SUPPORT

**If you get stuck:**

1. Check browser console for JavaScript errors
2. Verify endpoint exists: `grep page_view /opt/pureleven/ai-engine/app/crm_routes.py`
3. Check server logs: `docker logs -f pureleven-ai-engine`
4. Verify Meta pixel ID is correct: 609256704464862
5. Double-check CSV format matches Meta requirements

---

**Ready? Let's start with Step 1: Adding JavaScript to Shopify! 🚀**
