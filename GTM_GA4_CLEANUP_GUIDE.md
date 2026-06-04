# GTM & GA4 Cleanup & Configuration Guide

## Status
- ✅ **COMPLETED**: Audience tracking code deployed and LIVE (5 products confirmed)
- ✅ **COMPLETED**: Custom events firing on product pages
- ⏳ **IN PROGRESS**: GTM cleanup, audience creation, GA4 property deletion

---

## Part 1: Delete Orphaned GA4 Property (G-3JXJPCDV72)

**Why**: This property only captures pageviews with zero ecommerce data. It's orphaned and should be removed.

### Step-by-Step:

1. **Open Google Analytics** → `https://analytics.google.com`
2. **Select Account**: "Pureleven" (or your business account)
3. **Click Admin** (gear icon, bottom-left)
4. **Property Settings** → Look for "G-3JXJPCDV72" in the Properties list
   - Or navigate: Admin → Properties → Find "www.pureleven.com" or "Old Property"
5. **Open Property Settings** → Click the property
6. **Administration** → **Property Settings**
7. **Scroll down** → Click **"Delete this property"**
8. **Confirm deletion** with your password if prompted
9. **Verify**: The property should no longer appear in your properties list

---

## Part 2: Remove Redundant GT Containers from Shopify Pixel Config

**Why**: The Shopify pixel currently has 5 Tag IDs configured, but we only need the primary ones. GT-MQDVK4L2 and GT-K4TGNT3X are redundant/unused.

### Current Shopify Pixel Configuration:
```
Pixel ID: 1548386597
google_tag_ids: [
  "G-3FRSK7TEN2",      ← Primary GA4 (KEEP)
  "G-3JXJPCDV72",      ← Orphaned (DELETE via GA4 above)
  "GT-MQDVK4L2",       ← Redundant (REMOVE)
  "GTM-MDNS2FFP",      ← GTM Container (KEEP)
  "GT-K4TGNT3X"        ← Redundant (REMOVE)
]
```

### Step-by-Step:

**Option A: Via Shopify Admin UI (Recommended)**

1. **Shopify Admin** → `https://rwxtic-gz.myshopify.com/admin`
2. **Apps & Sales Channels** → **Apps and sales channels** → Search "Google"
3. **Google & YouTube** App → Open it
4. **Settings** or **Configuration**
5. **Look for "Connected Tag IDs"** or **"Google Tag Configuration"**
6. **Remove these IDs**:
   - `GT-MQDVK4L2`
   - `GT-K4TGNT3X`
7. **Keep**: `G-3FRSK7TEN2`, `GTM-MDNS2FFP`
8. **Save** and confirm

**Option B: Via Google Tag Manager (More Control)**

1. Open `https://tagmanager.google.com`
2. Find "Shopify Channel App" containers (if editable)
3. Locate GT-MQDVK4L2 and GT-K4TGNT3X
4. Delete or disable them
5. Publish the changes

---

## Part 3: Create GTM Variables, Triggers, and GA4 Event Tags

**Container**: GTM-MDNS2FFP  
**Account**: Pureleven (6307024650)  
**Container ID**: 226640770 (or find via pureleven_shopify2025 in GTM)

### Navigation:
1. `https://tagmanager.google.com`
2. Select **pureleven_shopify2025** container (or find GTM-MDNS2FFP)
3. Go to **Configuration** workspace

---

### Step 3a: Create 6 Data Layer Variables

**Purpose**: Extract product interest data from custom JavaScript events for use in triggers and tags.

**Navigate To**: Configuration → User-Defined Variables → **New**

#### Variable 1: DLV - interest_category
- **Name**: `DLV - interest_category`
- **Type**: Data Layer Variable
- **Data Layer Variable Name**: `interest_category`
- **Save & Tag**

#### Variable 2: DLV - product_handle
- **Name**: `DLV - product_handle`
- **Type**: Data Layer Variable
- **Data Layer Variable Name**: `product_handle`
- **Save & Tag**

#### Variable 3: DLV - product_name
- **Name**: `DLV - product_name`
- **Type**: Data Layer Variable
- **Data Layer Variable Name**: `product_name`
- **Save & Tag**

#### Variable 4: DLV - product_price
- **Name**: `DLV - product_price`
- **Type**: Data Layer Variable
- **Data Layer Variable Name**: `product_price`
- **Save & Tag**

#### Variable 5: DLV - top_category
- **Name**: `DLV - top_category`
- **Type**: Data Layer Variable
- **Data Layer Variable Name**: `top_category`
- **Save & Tag**

#### Variable 6: DLV - categories
- **Name**: `DLV - categories`
- **Type**: Data Layer Variable
- **Data Layer Variable Name**: `categories`
- **Save & Tag**

---

### Step 3b: Create 5 Custom Event Triggers

**Navigate To**: Configuration → Triggers → **New**

#### Trigger 1: Custom Event - Product Interest
- **Name**: `Custom Event - Product Interest`
- **Trigger Type**: Custom Event
- **Event Name**: `pl_product_interest`
- **This trigger fires on**: All Custom Events
- **Save & Publish**

#### Trigger 2: Custom Event - High Intent
- **Name**: `Custom Event - High Intent`
- **Trigger Type**: Custom Event
- **Event Name**: `pl_high_intent`
- **This trigger fires on**: All Custom Events
- **Save & Publish**

#### Trigger 3: Custom Event - Cross Category
- **Name**: `Custom Event - Cross Category`
- **Trigger Type**: Custom Event
- **Event Name**: `pl_cross_category`
- **This trigger fires on**: All Custom Events
- **Save & Publish**

#### Trigger 4: Custom Event - Combo Interest
- **Name**: `Custom Event - Combo Interest`
- **Trigger Type**: Custom Event
- **Event Name**: `pl_combo_interest`
- **This trigger fires on**: All Custom Events
- **Save & Publish**

#### Trigger 5: Custom Event - Add to Cart Interest
- **Name**: `Custom Event - Add to Cart Interest`
- **Trigger Type**: Custom Event
- **Event Name**: `pl_add_to_cart_interest`
- **This trigger fires on**: All Custom Events
- **Save & Publish**

---

### Step 3c: Create 5 GA4 Event Tags (Forward Custom Events to GA4)

**Navigate To**: Configuration → Tags → **New**

**Purpose**: Each tag forwards a custom event from your website to Google Analytics 4 (G-3FRSK7TEN2).

#### Tag 1: GA4 - Product Interest Event
- **Name**: `GA4 - Product Interest Event`
- **Tag Type**: Google Analytics: GA4 Event
- **Measurement ID**: `G-3FRSK7TEN2`
- **Event Name**: `pl_product_interest`
- **Event Parameters**:
  - `interest_category` → Variable: `{{DLV - interest_category}}`
  - `product_handle` → Variable: `{{DLV - product_handle}}`
  - `product_name` → Variable: `{{DLV - product_name}}`
  - `product_price` → Variable: `{{DLV - product_price}}`
- **Firing Trigger**: `Custom Event - Product Interest`
- **Save & Publish**

#### Tag 2: GA4 - High Intent Event
- **Name**: `GA4 - High Intent Event`
- **Tag Type**: Google Analytics: GA4 Event
- **Measurement ID**: `G-3FRSK7TEN2`
- **Event Name**: `pl_high_intent`
- **Event Parameters**:
  - `interest_category` → Variable: `{{DLV - interest_category}}`
  - `pages_viewed` → Value: `3` (fixed) or dynamic from custom variable
- **Firing Trigger**: `Custom Event - High Intent`
- **Save & Publish**

#### Tag 3: GA4 - Cross Category Event
- **Name**: `GA4 - Cross Category Event`
- **Tag Type**: Google Analytics: GA4 Event
- **Measurement ID**: `G-3FRSK7TEN2`
- **Event Name**: `pl_cross_category`
- **Event Parameters**:
  - `categories_viewed` → Value: `2` (fixed) or dynamic
  - `category_list` → Variable: `{{DLV - categories}}`
- **Firing Trigger**: `Custom Event - Cross Category`
- **Save & Publish**

#### Tag 4: GA4 - Combo Interest Event
- **Name**: `GA4 - Combo Interest Event`
- **Tag Type**: Google Analytics: GA4 Event
- **Measurement ID**: `G-3FRSK7TEN2`
- **Event Name**: `pl_combo_interest`
- **Event Parameters**:
  - `interest_category` → Variable: `{{DLV - interest_category}}`
  - `product_handle` → Variable: `{{DLV - product_handle}}`
- **Firing Trigger**: `Custom Event - Combo Interest`
- **Save & Publish**

#### Tag 5: GA4 - Add to Cart Interest Event
- **Name**: `GA4 - Add to Cart Interest Event`
- **Tag Type**: Google Analytics: GA4 Event
- **Measurement ID**: `G-3FRSK7TEN2`
- **Event Name**: `pl_add_to_cart_interest`
- **Event Parameters**:
  - `interest_category` → Variable: `{{DLV - interest_category}}`
  - `product_handle` → Variable: `{{DLV - product_handle}}`
  - `product_name` → Variable: `{{DLV - product_name}}`
- **Firing Trigger**: `Custom Event - Add to Cart Interest`
- **Save & Publish**

---

### Step 3d: Publish GTM Container

1. **Click "Submit"** (top-right of GTM workspace)
2. **Version Name**: `v5 - Custom Event Tags for GA4 Audiences`
3. **Description**: `Added 6 variables, 5 triggers, and 5 GA4 event tags for product interest tracking and audience creation.`
4. **Publish**

---

## Part 4: Create 8 GA4 Audiences for Remarketing

**Purpose**: Create audiences in GA4 based on custom events so you can retarget users in Google Ads and Meta.

### Navigation:
1. **Google Analytics** → `https://analytics.google.com`
2. **Admin** (gear icon, bottom-left)
3. **Property: pureleven_shopify2025** (or G-3FRSK7TEN2)
4. **Audiences** (or **Audience Builder**)
5. **New Audience** or **+ New Audience**

---

### Audience 1: Black Pepper Shoppers

- **Name**: `Black Pepper Shoppers`
- **Audience Source**: Google Analytics 4
- **Create new audience**
- **Audience Builder** → **Event-based**
- **Condition 1**: 
  - **Event**: `pl_product_interest`
  - **Parameter**: `interest_category`
  - **Condition**: `equals`
  - **Value**: `pepper`
- **Lookback Window**: 30 days (or your preference)
- **Save**

### Audience 2: Cardamom Shoppers

- **Name**: `Cardamom Shoppers`
- **Event-based**
- **Event**: `pl_product_interest`
- **Parameter**: `interest_category`
- **Condition**: `equals`
- **Value**: `cardamom`
- **Lookback Window**: 30 days
- **Save**

### Audience 3: Cinnamon Shoppers

- **Name**: `Cinnamon Shoppers`
- **Event**: `pl_product_interest`
- **Parameter**: `interest_category`
- **Value**: `cinnamon`
- **Lookback Window**: 30 days
- **Save**

### Audience 4: Cloves Shoppers

- **Name**: `Cloves Shoppers`
- **Event**: `pl_product_interest`
- **Parameter**: `interest_category`
- **Value**: `cloves`
- **Lookback Window**: 30 days
- **Save**

### Audience 5: Combo Pack Shoppers

- **Name**: `Combo Pack Shoppers`
- **Event**: `pl_product_interest`
- **Parameter**: `interest_category`
- **Value**: `combo_pack`
- **Lookback Window**: 30 days
- **Save**

### Audience 6: High Intent Browsers (3+ Product Pages)

- **Name**: `High Intent Browsers`
- **Event**: `pl_high_intent`
- **Lookback Window**: 30 days
- **Save**

### Audience 7: Category Explorers (Multi-Category Viewers)

- **Name**: `Category Explorers`
- **Event**: `pl_cross_category`
- **Lookback Window**: 30 days
- **Save**

### Audience 8: Cart Abandoners (Viewed but Did Not Purchase)

- **Name**: `Cart Abandoners`
- **Event-based**
- **Event**: `pl_add_to_cart_interest`
- **Lookback Window**: 7 days (recent activity)
- **Add Condition**:
  - **AND NOT**: Event `purchase` within the same period
- **Save**

---

## Part 5: Optional - Force Shopify Pixel Sync

If audiences don't populate immediately, you may need to refresh the Shopify-GA4 connection:

1. **Shopify Admin** → `https://rwxtic-gz.myshopify.com/admin`
2. **Apps** → **Google & YouTube**
3. **Settings** → **Disconnect** GA4
4. **Reconnect** GA4
5. This will force a pixel refresh

---

## Summary: What's Ready

| Component | Status | Notes |
|-----------|--------|-------|
| Audience Tracking Code | ✅ LIVE | Deployed to 5 products, events firing |
| Custom Events | ✅ LIVE | pl_product_interest, pl_high_intent, pl_cross_category, pl_combo_interest, pl_add_to_cart_interest |
| Session Tracking | ✅ LIVE | sessionStorage accumulation working |
| Interest Categories | ✅ MAPPED | cardamom, pepper, cinnamon, cloves, combo_pack |
| GTM Variables | ⏳ TODO | Create 6 DLVs |
| GTM Triggers | ⏳ TODO | Create 5 custom event triggers |
| GA4 Event Tags | ⏳ TODO | Create 5 tags forwarding events to G-3FRSK7TEN2 |
| GA4 Audiences | ⏳ TODO | Create 8 remarketing audiences |
| Cleanup: G-3JXJPCDV72 | ⏳ TODO | Delete orphaned GA4 property |
| Cleanup: GT-* Tags | ⏳ TODO | Remove GT-MQDVK4L2, GT-K4TGNT3X |

---

## Testing: How to Verify

1. **Visit a product page** on rwxtic-gz.myshopify.com
2. **Open DevTools** (F12) → **Network** → Filter `gtag` or `analytics`
3. **Refresh page** and look for `pl_product_interest` event in:
   - **Console**: `window.dataLayer` array should show custom events
   - **Network**: Google Analytics requests with event parameters
4. **Check Real Time** in GA4 Admin:
   - Go to **Reports** → **Real Time**
   - Custom events should appear within 10-20 seconds
5. **After 24-48 hours**: Audiences should start populating

---

## Support & Troubleshooting

- **Events not firing?** Check `snippets/audience-tracking.liquid` is deployed
- **Variables not found?** Verify data layer keys match exactly (case-sensitive)
- **Audiences empty?** Give GA4 24-48 hours to process events, then check Real Time report
- **Shopify sync issues?** Clear browser cache or reconnect Google & YouTube app

---

**Last Updated**: 2026-05-15  
**Created By**: GitHub Copilot  
**Store**: rwxtic-gz.myshopify.com  
**Primary GA4**: G-3FRSK7TEN2  
**GTM Container**: GTM-MDNS2FFP
