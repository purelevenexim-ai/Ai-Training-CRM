# Google & Pixels Audit Report — pureleven.com
**Date:** May 15, 2026  
**Status:** ✅ **CLEAN** (All critical issues fixed)

---

## 🔴 Critical Issues FIXED Today

| # | Issue | Root Cause | Fix Applied | Status |
|---|-------|-----------|-------------|--------|
| 1 | GTM was **100% non-functional** | `track.pureleven.com` returned HTTP 400 | Switched to `googletagmanager.com` | ✅ **LIVE** |
| 2 | Liquid error on every page | `snippets/lazy-load-images.liquid` missing | Deployed snippet | ✅ **LIVE** |
| 3 | Liquid error on every page | `snippets/critical-styles.liquid` missing | Deployed snippet | ✅ **LIVE** |
| 4 | **GTM firing twice** (duplicate events) | Manual GTM script in `theme.liquid` + Shopify Customer Events both loading GTM-MDNS2FFP | Removed manual script, kept Customer Events only | ✅ **LIVE** |

---

## ✅ What's Working

### Google Tag Manager (GTM-MDNS2FFP)
- **Status:** ✅ **Active & single-load**
- **Load path:** Shopify Google & YouTube Sales Channel → google_tag_ids → fires once per pageview
- **Tags inside GTM:** Check your container — should only have custom/non-standard tags. (Ecommerce events are already handled by Shopify Customer Events)

### Google Analytics (GA4)
| Property ID | Events Tracked | Status |
|------------|----------------|--------|
| `G-3FRSK7TEN2` | page_view, view_item, add_to_cart, begin_checkout, add_payment_info, purchase, search | ✅ All 7 firing |
| `G-3JXJPCDV72` | ⚠️ **Only pageviews** — **NOT** in ecommerce event action_labels | ❌ Orphaned |

**Finding:** `G-3JXJPCDV72` receives zero ecommerce events. It's listed in `google_tag_ids` but ignored in all `gtag_events` `action_label` arrays.

### Google Ads (AW-10965185406)
**Status:** ✅ **All 7 conversion actions active**

| Conversion | Conversion ID | Status |
|-----------|---------------|--------|
| Purchase | `gaHPCLL_9YUbEP7mzewo` | ✅ |
| Add to Cart | `Wt9TCLj_9YUbEP7mzewo` | ✅ |
| Begin Checkout | `PFboCLX_9YUbEP7mzewo` | ✅ |
| View Item | `46aLCL7_9YUbEP7mzewo` | ✅ |
| Page View | `KMEYCLv_9YUbEP7mzewo` | ✅ |
| Add Payment Info | `nDKICMT_9YUbEP7mzewo` | ✅ |
| Search | `EwviCMH_9YUbEP7mzewo` | ✅ |

**Note:** Before May 15, 2026, GTM was broken (400 error), so **purchase conversions recorded before today may be under-reported**. Shopify's direct-to-Google feeds (ecommerce events) were still sending data, so Merchant Center/Ads probably has the full record, but GTM-dependent custom conversions may have gaps.

### Google Merchant Center
**Connected IDs:** `MC-3ECKT6WCYK`, `MC-W1RKG8D3GP` (both receiving events)

| Event | Status |
|-------|--------|
| view_item | ✅ |
| purchase | ✅ |

**Structured Data on Product Pages:** ✅ Present
- Product schema with price (INR)
- BreadcrumbList
- FAQPage
- Organization

**Action Needed:**  
⚠️ Check your Merchant Center dashboard for product **disapprovals**. Common spice product issues:
- Missing GTIN/UPC (spices often don't have standard codes)
- Insufficient product identifiers
- Missing/invalid target countries

### Facebook Pixel (609256704464862)
**Status:** ✅ **Active**  
**Firing path:** Shopify Customer Events → Facebook pixel (OPEN runtime)  
**Events:** PageView, ViewContent, AddToCart, Purchase

### Microsoft Clarity
**Status:** ✅ **Active** (session recording)  
**Type:** Custom pixel (LAX runtime)

---

## ⚠️ Manual Actions Required (3 Dashboard Changes)

### 1️⃣ Shopify Admin — Google & YouTube Sales Channel Settings

**Location:** Settings & Pixels → Google & YouTube Sales Channel → Google Tag IDs

**Current list:**
- `G-3FRSK7TEN2` ✅ Keep (primary GA4, receives all ecommerce)
- `G-3JXJPCDV72` ❌ **REMOVE** (orphaned — no ecommerce events)
- `GT-MQDVK4L2` ❌ **CHECK & LIKELY REMOVE** (Google Tag container, likely redundant)
- `GT-K4TGNT3X` ❌ **CHECK & LIKELY REMOVE** (Google Tag container, likely redundant)
- `GTM-MDNS2FFP` ✅ Keep (primary GTM container)

**Action:**
1. Remove `G-3JXJPCDV72` (split traffic, unusable)
2. Test by viewing an ecommerce event in Google Analytics → check if GTM container fires. If it does and action labels have all 7 events without the GT- containers, remove those too.

---

### 2️⃣ Google Tag Manager (tagmanager.google.com)

**Container:** GTM-MDNS2FFP

**Check:**
1. Open your tags list
2. Look for any tags with type "Google Analytics" or "Google Ads Conversion"
3. **If found:** These are **DUPLICATES** — Shopify Customer Events already fires GA4 & Ads events directly
4. **Action:** Pause or delete the duplicate GA4/Ads tags

**What should remain in GTM:**
- Custom event tracking (beyond the 7 standard ecommerce events)
- Custom variables or triggers not available in Shopify's pixel system
- Tag manager internal tags (GA, Ads, etc. that DON'T duplicate Customer Events)

---

### 3️⃣ Google Business Profile (business.google.com)

**Business:** Pure Leven Exim (Rating: 4.9★, 45 reviews ✅)

**Current status:**
- ✅ Place ID working, embeds on homepage
- ✅ NAP visible on site
- ⚠️ Missing: Business hours, product catalog link, GMB posts

**3 quick actions:**

| Action | Impact | Effort |
|--------|--------|--------|
| **Set Business Hours** | Local search ranking signal | 2 min |
| **Add Product Catalog to GMB** | Better product-level search results | 5 min |
| **Post 1x/week** (offers, new SKUs, seasonal) | SMB engagement + recency signal | 5 min recurring |

**Setup steps (business.google.com):**
1. Left menu → Info → Hours → Set your actual business hours (India Standard Time, Mon-Sun)
2. Left menu → Products → Connect your Shopify product feed
3. Left menu → Posts → Create post (text + image) about new/featured products

---

## 📊 Inventory Summary

### Google Properties
| Property | ID | Type | Status |
|----------|----|----|--------|
| GA4 (Primary) | `G-3FRSK7TEN2` | Analytics | ✅ Active |
| GA4 (Secondary) | `G-3JXJPCDV72` | Analytics | ❌ Orphaned |
| GTM | `GTM-MDNS2FFP` | Tag Manager | ✅ Active |
| Google Ads | `AW-10965185406` | Conversion Tracking | ✅ Active |
| Merchant Center (A) | `MC-3ECKT6WCYK` | Product Feed | ✅ Active |
| Merchant Center (B) | `MC-W1RKG8D3GP` | Product Feed | ✅ Active |

### 3rd Party Pixels
| Pixel | ID | Type | Status |
|-------|----|----|--------|
| Facebook Pixel | `609256704464862` | Conversion | ✅ Active |
| Microsoft Clarity | (Session Recording) | Analytics | ✅ Active |

---

## 📋 Technical Summary

**Deployment date:** 2026-05-15 14:30 UTC  
**Files modified:**
- ✅ `layout/theme.liquid` — Removed duplicate GTM script, cleaned comments
- ✅ `snippets/lazy-load-images.liquid` — Deployed (performance optimization)
- ✅ `snippets/critical-styles.liquid` — Deployed (performance optimization)

**Live status:** All 3 fixes deployed, Liquid errors cleared, tracking stack clean

---

## 🎯 Best Practices Applied

1. ✅ Single GTM load via Shopify Customer Events (no duplication)
2. ✅ All ecommerce events flow through both direct Shopify feeds + GTM
3. ✅ Structured data present on product pages (Product, BreadcrumbList, FAQPage)
4. ✅ Canonical tags present (no SEO duplicate content issues)
5. ✅ No broken endpoints or 400 errors on tracking
6. ⚠️ Some consolidation needed (remove orphaned GA4 property, check GTM for dupes)

---

## 🚀 Next Steps (In Priority Order)

1. **TODAY:** Remove `G-3JXJPCDV72` from Shopify Settings
2. **TODAY:** Open GTM-MDNS2FFP and check for duplicate GA4/Ads tags (pause/delete if found)
3. **THIS WEEK:** Set GMB business hours + add product catalog link
4. **ONGOING:** Post to GMB 1-2x per week (customer acquisition + SEO signal)

---

**Questions?** Check your:
- Google Analytics → Acquisition → All traffic → Source/Medium (should show organic, direct, google-shopping, etc.)
- Google Ads → Conversions → All → Settings (conversion value, verification status)
- Google Merchant Center → Products → All → Status (disapprovals, feed health)
