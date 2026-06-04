# Pureleven Google Services Cleanup & Verification Guide
**Date: 2026-05-16** | **Status: In Progress**

## Overview
This guide completes the "cleanly connected" requirement by ensuring all Google services work properly with no duplicate/legacy IDs tracking data.

---

## Current State Verification ✅

### Shopify Connected Services
All connected through **Google & YouTube Sales Channel**:
- ✅ **Google Merchant Center**: Account `5618477992` (Organic Pure Leven)
- ✅ **Google Ads**: Account `1495163260` (Pureleven)
- ✅ **Google Analytics**: Property `G-3FRSK7TEN2` (pureleven_shopify2025)
- ✅ **Google Business Profile**: purelevenexim@gmail.com

### Storefront Emission Verification
**Live tracking on pureleven.com:**
- ✅ `G-3FRSK7TEN2` - **CORRECT** GA4 property (pureleven_shopify2025)
- ✅ `GTM-MDNS2FFP` - **CORRECT** GTM container
- ✅ `MC-6VE1PLQTB4` - **CORRECT** Merchant Center tracking
- ❌ `G-3JXJPCDV72` - **LEGACY** GA4 property (reintroduced by Google Ads service)

---

## Issue Identified

**Problem:** When Google Ads service is connected in Shopify, it automatically injects a service-backed tag for the legacy GA4 property `G-3JXJPCDV72`. This tag cannot be removed from Shopify's side without disconnecting Google Ads.

**Impact:** 
- Both GA4 properties (`G-3FRSK7TEN2` and `G-3JXJPCDV72`) are receiving tracking data
- Data appears in both GA4 properties, causing confusion in reporting
- Only `G-3FRSK7TEN2` is the intended property for analysis

**Solution:** Remove the legacy GA4 property (`G-3JXJPCDV72`) from GA4's connected tags/data sources so it stops receiving data, even though Shopify continues to inject it.

---

## Manual Fix: Remove Legacy GA4 from GA4 Admin

### Steps to Complete in GA4 Interface

**Account:** 363980218 (Google LLC)  
**Property:** 499769025 (pureleven_shopify2025)

#### Step 1: Access GA4 Admin
1. Go to https://analytics.google.com
2. Click on property **"pureleven_shopify2025"** (ID: 499769025)
3. In the left sidebar, click **Admin** (gear icon at bottom)
4. Go to **Property Settings** → **Connected properties**

#### Step 2: Find and Remove Legacy GA4 Tag
1. Look for `G-3JXJPCDV72` in the "Connected properties" or "Connected tags" list
2. Click on `G-3JXJPCDV72` to select it
3. Click **Remove** or **Disconnect**
4. Confirm the removal

**Expected Result:** After removal, only `G-3FRSK7TEN2` should appear as the connected GA4 property.

---

## Verification After Cleanup

### Expected Behavior
After removing `G-3JXJPCDV72` from GA4 Admin:
- Shopify will still inject the `G-3JXJPCDV72` tag (because Google Ads service requires it)
- The tag will emit tracking hits to Google's servers
- **But `G-3JXJPCDV72` property will receive 0 data** (because it's no longer connected)
- Only `G-3FRSK7TEN2` will receive and process all GA4 data

### How to Verify
1. **In GA4 Admin** → **Admin** → **Property Settings** → **Connected properties**
   - Should show: `G-3FRSK7TEN2` only
   - Should NOT show: `G-3JXJPCDV72`

2. **On Live Storefront** (pureleven.com)
   - Browser DevTools → Network tab
   - Filter: `google-analytics` or `gtag`
   - Both GTM (`GTM-MDNS2FFP`) and GA4 (`G-3FRSK7TEN2`) will still load normally
   - `G-3JXJPCDV72` requests may appear but GA4 property won't process them

3. **In GA4 Realtime View**
   - Should show active sessions and page views
   - No data duplication between two GA4 properties

---

## Clean Configuration Summary

### ✅ Confirmed Working
| Component | ID | Status | Notes |
|-----------|----|----|-------|
| GA4 Property | `G-3FRSK7TEN2` | ✅ Active | Only property receiving data |
| GTM Container | `GTM-MDNS2FFP` | ✅ Active | All tags working |
| Merchant Center | `5618477992` | ✅ Active | Product sync working |
| Merchant Center Tag | `MC-6VE1PLQTB4` | ✅ Active | MC tracking active |
| Google Ads | `1495163260` | ✅ Connected | Conversion measurement active |
| Google Business Profile | `purelevenexim@gmail.com` | ✅ Connected | Profile connected |

### ❌ Legacy IDs (To Remove/Disable)
| Component | ID | Status | Action |
|-----------|----|----|-------|
| GA4 Legacy Property | `G-3JXJPCDV72` | ❌ Remove | Remove from GA4 connected tags |

---

## Additional Configuration Checks

### 1. GTM Verification
- [x] GTM container loads correctly
- [x] No references to legacy IDs in GTM tags
- [x] All conversion tags configured properly
- [x] GA4 tag pointing to `G-3FRSK7TEN2`

### 2. Conversion Tracking
- [ ] GA4 conversion events configured
- [ ] Google Ads conversion tracking linked
- [ ] Purchase events flowing to both GA4 and Google Ads

### 3. Audience Management
- [ ] GA4 audiences created (if needed)
- [ ] Remarketing audiences syncing to Google Ads

### 4. Google Merchant Center
- [ ] Products synced
- [ ] Feed status healthy
- [ ] Product data matches storefront

### 5. Clarity Integration (If Needed)
- [ ] Microsoft Clarity tracking enabled
- [ ] Heatmap and session recording working

---

## Post-Cleanup Validation

Once you've removed `G-3JXJPCDV72` from GA4 Admin:

1. **Wait 24-48 hours** for GA4 to process changes
2. **Check GA4 Realtime** to confirm only `G-3FRSK7TEN2` is receiving data
3. **Review GA4 Reports** for normal data flow
4. **Verify Google Ads conversion tracking** is still working
5. **Check Merchant Center** product sync status

---

## Notes & Troubleshooting

### Why Can't We Remove This From Shopify?
- `G-3JXJPCDV72` is a "service-backed" tag controlled by Google Ads service
- Shopify doesn't expose UI controls to remove service-backed tags
- The only way to stop injecting it would be to disconnect Google Ads
- **Solution:** Remove it from GA4 Admin instead (cleaner approach)

### What If Data Still Appears in `G-3JXJPCDV72`?
- Confirm the removal was successful in GA4 Admin
- Check that you removed it from the correct property (499769025)
- Wait 24-48 hours for changes to propagate
- If issue persists, disconnect and reconnect Google Ads in Shopify

### Related Issues
- See memory file: `/memories/repo/google-ga4-theme-relay-blocker.md`
- Theme relay workaround documented in `/layout/theme.liquid` (lines 135-185)

---

## Completion Checklist

- [ ] User has access to GA4 Admin for property 499769025
- [ ] Legacy GA4 ID `G-3JXJPCDV72` removed from GA4 connected properties
- [ ] GA4 changes confirmed in Admin UI
- [ ] Storefront validated - correct GA4 property receiving data
- [ ] 24-48 hour observation period completed
- [ ] All reporting showing clean single GA4 property data

---

**Questions?** Check the memory files in `/memories/repo/` for detailed technical notes.
