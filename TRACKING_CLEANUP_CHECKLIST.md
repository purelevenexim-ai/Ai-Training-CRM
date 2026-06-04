# PURELEVEN.COM — TRACKING CLEANUP CHECKLIST
**Date:** 2026-05-15 | **Status:** Ready for execution

---

## PART 1: Remove Orphaned GA4 Property (G-3JXJPCDV72)

### Current State
- **Property ID:** `G-3JXJPCDV72` (pureleven_shopify — old/orphaned)
- **Status:** Still firing on live site (pageviews only, zero ecommerce events)
- **Location:** Google Analytics
- **Action:** DELETE

### Steps to Remove
1. **Sign in** → [https://analytics.google.com](https://analytics.google.com)
2. **Select Account:** Click account switcher (top left) → "Pureleven" (purelevenexim@gmail.com)
3. **Find Property:** Look for "pureleven_shopify" or "G-3JXJPCDV72" in property list
4. **Open Admin:**
   - Click ⚙️ **Admin** (bottom left sidebar)
   - In **Property** column (middle) → find the orphaned property
5. **Delete:**
   - Click **Property Settings** (under Property column)
   - Scroll to bottom → Click **Move to Trash** (or **Delete Property**)
   - Confirm deletion

### Expected Result
- ✅ Property G-3JXJPCDV72 no longer appears in GA4
- ✅ Only G-3FRSK7TEN2 (active primary property) remains
- ✅ Orphaned pageviews stop being counted

---

## PART 2: Clean Up GTM Container (GTM-MDNS2FFP) — Remove Orphaned Tags

### Current State
- **Container:** GTM-MDNS2FFP (active, controls all Shopify tracking)
- **Tags to Remove:**
  - `GT-K4TGNT3X` (secondary Google Tag container — redundant)
  - `GT-MQDVK4L2` (verify if it duplicates G-3FRSK7TEN2 function — likely remove)

### Steps to Remove Tags

#### Step A: Open GTM Container
1. **Sign in** → [https://tagmanager.google.com](https://tagmanager.google.com)
2. **Select Container:** GTM-MDNS2FFP
3. **Navigate to Tags:** Left sidebar → **Tags**

#### Step B: Find & Delete GT-K4TGNT3X
1. **Search or scroll** through tag list for `GT-K4TGNT3X`
2. **Click the tag** to open it
3. **Review:** Confirm it's a secondary Google Tag container (look for "Google Tag" or "GT-" in the tag name)
4. **Delete:** Click the ⋮ menu (top right) → **Delete**
5. **Confirm:** Click "Delete Tag"

#### Step C: Find & Delete or Keep GT-MQDVK4L2
1. **Search or scroll** for `GT-MQDVK4L2`
2. **Click the tag** to open it
3. **Check Configuration:**
   - If it only forwards data to Google Tag (duplicate of what G-3FRSK7TEN2 does) → **DELETE**
   - If it has unique Ads conversion mappings → **KEEP**
4. **Decision:** Based on your review above
   - **If DELETE:** Click ⋮ menu → **Delete** → **Confirm**
   - **If KEEP:** Close this tag and move to next step

### Expected Result
- ✅ GT-K4TGNT3X completely removed from container
- ✅ GT-MQDVK4L2 removed (if redundant) or confirmed necessary
- ⚠️ Do NOT publish yet — see Part 3 below

---

## PART 3: Add 5 New Custom Event Tags (for audience tracking)

### Context
- Live audience tracking code is **already deployed** (`snippets/audience-tracking.liquid`)
- Fires 5 custom events: `pl_product_interest`, `pl_high_intent`, `pl_cross_category`, `pl_combo_interest`, `pl_add_to_cart_interest`
- **GTM must forward these to GA4** via new tags

### Step A: Create Data Layer Variables
**In GTM (same container):**

1. **Left sidebar** → **Variables** → **User-Defined Variables**
2. Click **New** → **Data Layer Variable**
3. **Create these 6 variables:**

| Variable Name | Data Layer Key | Notes |
|---|---|---|
| `DLV - interest_category` | `interest_category` | Product interest type (cardamom, pepper, etc.) |
| `DLV - product_handle` | `product_handle` | Product slug |
| `DLV - product_name` | `product_name` | Product title |
| `DLV - product_price` | `product_price` | Variant price |
| `DLV - top_category` | `top_category` | Most-viewed spice category in session |
| `DLV - categories` | `categories` | All viewed categories (comma-separated) |

**For each variable:**
- Name: (from table above)
- Variable Type: **Data Layer Variable**
- Data Layer Variable Name: (from table above)
- Data Layer Version: Version 2
- Save: Click **Save**

### Step B: Create Custom Event Triggers
**In GTM (same container):**

1. **Left sidebar** → **Triggers**
2. Click **New** → **Custom Event**
3. **Create these 5 triggers:**

| Trigger Name | Event Name |
|---|---|
| `PL — Product Interest` | `pl_product_interest` |
| `PL — High Intent` | `pl_high_intent` |
| `PL — Cross Category` | `pl_cross_category` |
| `PL — Combo Interest` | `pl_combo_interest` |
| `PL — ATC Interest` | `pl_add_to_cart_interest` |

**For each trigger:**
- Name: (from table above)
- Trigger Type: **Custom Event**
- Event Name: (from table above)
- This trigger fires on: All Custom Events
- Save: Click **Save**

### Step C: Create GA4 Event Tags
**In GTM (same container):**

1. **Left sidebar** → **Tags**
2. Click **New** → **Google Analytics: GA4 Event**
3. **Create these 5 tags:**

#### Tag 1: PL — Product Interest Event
- **Tag Configuration:**
  - Tag Type: Google Analytics: GA4 Event
  - Measurement ID: `G-3FRSK7TEN2`
  - Event Name: `pl_product_interest`
- **Event Parameters:**
  - `interest_category` → Variable: `{{DLV - interest_category}}`
  - `product_handle` → Variable: `{{DLV - product_handle}}`
  - `product_name` → Variable: `{{DLV - product_name}}`
  - `product_price` → Variable: `{{DLV - product_price}}`
- **Trigger:** `PL — Product Interest`
- **Name:** `PL — GA4 Product Interest`
- **Save:** Click **Save**

#### Tag 2: PL — High Intent Event
- **Tag Configuration:**
  - Tag Type: Google Analytics: GA4 Event
  - Measurement ID: `G-3FRSK7TEN2`
  - Event Name: `pl_high_intent`
- **Event Parameters:**
  - `top_category` → Variable: `{{DLV - top_category}}`
  - `pages_viewed` → {{Event Data - pages_viewed}} (or manual value if not in dataLayer)
- **Trigger:** `PL — High Intent`
- **Name:** `PL — GA4 High Intent`
- **Save:** Click **Save**

#### Tag 3: PL — Cross Category Event
- **Tag Configuration:**
  - Tag Type: Google Analytics: GA4 Event
  - Measurement ID: `G-3FRSK7TEN2`
  - Event Name: `pl_cross_category`
- **Event Parameters:**
  - `categories` → Variable: `{{DLV - categories}}`
  - `category_count` → {{Event Data - category_count}}
- **Trigger:** `PL — Cross Category`
- **Name:** `PL — GA4 Cross Category`
- **Save:** Click **Save**

#### Tag 4: PL — Combo Interest Event
- **Tag Configuration:**
  - Tag Type: Google Analytics: GA4 Event
  - Measurement ID: `G-3FRSK7TEN2`
  - Event Name: `pl_combo_interest`
- **Event Parameters:**
  - `product_handle` → Variable: `{{DLV - product_handle}}`
  - `product_price` → Variable: `{{DLV - product_price}}`
- **Trigger:** `PL — Combo Interest`
- **Name:** `PL — GA4 Combo Interest`
- **Save:** Click **Save**

#### Tag 5: PL — ATC Interest Event
- **Tag Configuration:**
  - Tag Type: Google Analytics: GA4 Event
  - Measurement ID: `G-3FRSK7TEN2`
  - Event Name: `pl_add_to_cart_interest`
- **Event Parameters:**
  - `interest_category` → Variable: `{{DLV - interest_category}}`
  - `product_handle` → Variable: `{{DLV - product_handle}}`
  - `product_price` → Variable: `{{DLV - product_price}}`
- **Trigger:** `PL — ATC Interest`
- **Name:** `PL — GA4 ATC Interest`
- **Save:** Click **Save**

### Step D: Publish Container
1. **Top right** → **Submit**
2. Enter **Version Name:** `Custom Audience Events - 2026-05-15`
3. Enter **Version Description:** `Added 5 custom product interest events (pl_product_interest, pl_high_intent, pl_cross_category, pl_combo_interest, pl_add_to_cart_interest) for GA4 audience building. Removed GT-K4TGNT3X redundant tag.`
4. Click **Publish**

### Expected Result
- ✅ GTM container updated with 5 new event tags
- ✅ All custom events now forward to GA4 G-3FRSK7TEN2
- ✅ Data Layer variables available for event parameters

---

## PART 4: Create GA4 Audiences (Auto-Remarketing)

### Current State
- **GA4 Property:** G-3FRSK7TEN2 (active primary)
- **New Events:** Now flowing from GTM (via tags in Part 3)
- **Task:** Create 8 audiences based on custom events

### Steps to Create Audiences

1. **Sign in** → [https://analytics.google.com](https://analytics.google.com)
2. **Select Property:** G-3FRSK7TEN2 (pureleven_shopify2025 — the active one)
3. **Navigate:** Left sidebar → **Admin** → **Audiences** (under Data section)
4. **Create New Audience:** Click **+ New Audience**

### Audience 1: Interest: Black Pepper
- **Audience Name:** `Interest: Black Pepper`
- **Audience Source:** Google Analytics
- **Audience Definition:** Custom audience
- **Conditions:**
  - Event name = `pl_product_interest`
  - AND parameter `interest_category` = `pepper`
- **Duration:** 30 days (or your preferred window)
- **Save**

### Audience 2: Interest: Cardamom
- **Audience Name:** `Interest: Cardamom`
- **Conditions:**
  - Event name = `pl_product_interest`
  - AND parameter `interest_category` = `cardamom`
- **Save**

### Audience 3: Interest: Cinnamon
- **Audience Name:** `Interest: Cinnamon`
- **Conditions:**
  - Event name = `pl_product_interest`
  - AND parameter `interest_category` = `cinnamon`
- **Save**

### Audience 4: Interest: Cloves
- **Audience Name:** `Interest: Cloves`
- **Conditions:**
  - Event name = `pl_product_interest`
  - AND parameter `interest_category` = `cloves`
- **Save**

### Audience 5: Combo Pack Shoppers
- **Audience Name:** `Combo Pack Shoppers`
- **Conditions:**
  - Event name = `pl_combo_interest`
  - (matches any)
- **Save**

### Audience 6: High Intent Browsers
- **Audience Name:** `High Intent Browsers`
- **Conditions:**
  - Event name = `pl_high_intent`
  - (matches any)
- **Save**

### Audience 7: Category Explorers
- **Audience Name:** `Category Explorers`
- **Conditions:**
  - Event name = `pl_cross_category`
  - (matches any)
- **Save**

### Audience 8: Cart Abandoners
- **Audience Name:** `Cart Abandoners`
- **Conditions:**
  - Event name = `add_to_cart` (past 7 days)
  - AND NOT event name = `purchase` (past 7 days)
- **Duration:** 7 days
- **Save**

### Expected Result
- ✅ 8 audiences created in GA4
- ✅ All audiences auto-sync to Google Ads account (AW-10965185406)
- ✅ Audiences available for remarketing campaigns

---

## PART 5: Force Pixel Sync (Optional — Shopify Only)

If G-3JXJPCDV72 still appears on live product pages after Tasks 1-4:

1. **Shopify Admin** → **Apps → Google & YouTube Sales Channel**
2. Click **Settings**
3. Under "Google Analytics" → Click **Disconnect** next to G-3FRSK7TEN2
4. Wait 30 seconds
5. Click **Reconnect** → authorize
6. This forces Shopify to refresh its pixel config and drop orphaned IDs

---

## SUMMARY CHECKLIST

- [ ] **Task 1:** Remove GA4 property G-3JXJPCDV72
- [ ] **Task 2a:** Remove GTM tag GT-K4TGNT3X
- [ ] **Task 2b:** Remove GTM tag GT-MQDVK4L2 (if redundant)
- [ ] **Task 3a:** Create 6 Data Layer Variables in GTM
- [ ] **Task 3b:** Create 5 Custom Event Triggers in GTM
- [ ] **Task 3c:** Create 5 GA4 Event Tags in GTM
- [ ] **Task 3d:** Publish GTM container
- [ ] **Task 4:** Create 8 GA4 Audiences
- [ ] **Task 5:** (Optional) Force Shopify pixel sync

---

## VERIFICATION

After completing all tasks, verify by:

1. **Live Product Page Check:**
   ```javascript
   // Open https://pureleven.com/products/kerala-cardamom-50gm
   // In DevTools console:
   window.dataLayer.filter(e => e.event && e.event.startsWith('pl_'))
   ```
   Should show: `pl_product_interest` with `interest_category: "cardamom"`

2. **GA4 Real-time Report:**
   - Analytics → Reports → Real-time
   - Visit a product page → check Events
   - Should see `pl_product_interest`, `pl_high_intent`, etc. flowing in

3. **GTM Preview:**
   - GTM container → **Preview** mode
   - Visit product page → check "Tags Fired"
   - Should show all 5 new PL — GA4 event tags firing

---

**Status:** Ready to execute. Follow steps in order.
