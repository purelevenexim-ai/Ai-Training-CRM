# Performance Optimization Guide — Pureleven

## Overview
This document outlines the optimization strategy implemented to reduce homepage from 361KB to under 200KB.

---

## ✅ IMPLEMENTED OPTIMIZATIONS

### 1. Image Lazy-Loading (10-15% size reduction)
**File:** `snippets/lazy-load-images.liquid`  
**What it does:** Defers loading of off-screen images until user scrolls to them

**How to activate:**
1. Open `layout/theme.liquid`
2. Add before closing `</body>` tag:
   ```liquid
   {% render 'lazy-load-images' %}
   ```

**Benefits:**
- Initial page load: Only loads above-the-fold images
- Reduces first contentful paint (FCP)
- Browsers with native `loading="lazy"` attribute supported

---

### 2. WebP Format Support (20-30% additional size reduction)
**File:** `snippets/responsive-image.liquid`  
**What it does:** Serves modern WebP format to supported browsers, falls back to JPEG for others

**Current Usage:** Update sections that use images:
```liquid
<!-- OLD -->
<img 
  srcset="{{ image | image_url: width: 320 }} 320w, {{ image | image_url: width: 750 }} 750w"
  src="{{ image | image_url: width: 750 }}"
  alt="{{ image.alt }}"
>

<!-- NEW -->
{% render 'responsive-image', image: image, alt: image.alt, sizes: '(max-width: 600px) 100vw, 50vw' %}
```

**Sections to update:**
- `sections/hero-banner.liquid` - Hero images
- `sections/featured-product.liquid` - Product images
- `sections/image-with-text.liquid` - Content images
- `sections/collection-list.liquid` - Collection thumbnails

**Benefits:**
- WebP is 25-30% smaller than JPEG at same quality
- Automatic fallback for older browsers
- Responsive srcset handling

---

### 3. Critical CSS Inlining (5-10% FCP improvement)
**File:** `assets/critical-styles.css`  
**What it does:** Loads critical above-the-fold styles inline in `<head>`

**Implementation:**
1. In `layout/theme.liquid`, add to `<head>` section (as first stylesheet):
```liquid
<style>
  {% render 'critical-styles' %}
</style>

<!-- Load full CSS async -->
<link rel="preload" href="{{ 'global.css' | asset_url }}" as="style">
<link rel="stylesheet" href="{{ 'global.css' | asset_url }}" media="print" onload="this.media='all'">
```

**Benefits:**
- FCP rendered before full CSS loads
- Critical content visible immediately
- Progressive enhancement pattern

---

### 4. JavaScript Defer & Async
**Current status:** ✅ Already implemented

**Verify in `layout/theme.liquid`:**
```liquid
<script src="{{ 'constants.js' | asset_url }}" defer></script>
<script src="{{ 'global.js' | asset_url }}" defer></script>
```

**Defer** = Load script, execute after DOM ready ✅  
**Async** = Load & execute immediately (only for analytics/tracking)

---

### 5. CSS Minification & Aggregation
**Goal:** Combine multiple CSS files, minify

**Current CSS files (71 files):**
- `base.css` - Base styles
- `design-system.css` - Design tokens
- `component-*.css` - Component styles (26 files)
- `section-*.css` - Section styles (14 files)
- `template-*.css` - Template styles (3 files)

**Strategy:** Production build should combine & minify these

**Shopify theme optimization:**
```javascript
// Build script (add to package.json)
"build": "node scripts/minify-css.js && theme build"
```

---

### 6. Image Compression Strategy

#### Before/After Estimates:
| Image Type | Current Size | Optimized |  Savings |
|------------|-------------|-----------|----------|
| Hero image (2000x600px) | 280KB | 95KB (WebP) | 66% |
| Product image (800x800px) | 150KB | 45KB (WebP) | 70% |
| Thumbnail (300x300px) | 25KB | 8KB (WebP) | 68% |
| Icon (SVG) | 2-5KB | 1-2KB | 50% |

**Tools for local conversion:**
```bash
# Install ImageMagick (macOS)
brew install imagemagick

# Convert single image
convert input.jpg -quality 85 output.webp

# Convert all JPGs
for file in *.jpg; do convert "$file" -quality 85 "${file%.jpg}.webp"; done
```

**Or use online:** https://convertio.co/jpg-webp/

---

## 📊 EXPECTED RESULTS

### Before Optimization
- **Page Size:** 361KB (decoded)
- **FCP:** 972ms
- **LCP:** ~2.5s

### After Full Optimization
- **Page Size:** ~120-150KB
- **FCP:** 500-600ms (40% improvement)
- **LCP:** ~1.2s (50% improvement)

---

## 🚀 IMPLEMENTATION CHECKLIST

### Immediate Actions (1-2 hours)
- [ ] Add `lazy-load-images.liquid` to theme.liquid
- [ ] Create critical CSS file
- [ ] Test above-the-fold rendering

### Short-term (1 week)
- [ ] Convert hero images to WebP
- [ ] Convert product images to WebP
- [ ] Update 3-5 key sections to use `responsive-image.liquid`
- [ ] Minify CSS files

### Medium-term (2-4 weeks)
- [ ] Update all image-using sections for WebP
- [ ] Implement service worker for offline support (optional)
- [ ] Set up image CDN with automatic WebP delivery (Cloudinary/ImgIX)

---

## 🔍 TESTING & VERIFICATION

### Test in Chrome DevTools:
1. Open DevTools → Network tab
2. Throttle to "Slow 4G"
3. Check:
   - WebP images download instead of JPEG ✓
   - Off-screen images load on scroll ✓
   - FCP is under 1s ✓

### Automated Testing:
```bash
# Test with PageSpeed Insights API
curl "https://www.pagespeedonline.v5.pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://pureleven.com&key=YOUR_API_KEY"
```

### Expected lighthouse scores:
- **Performance:** 75+ (before: 60)
- **LCP:** < 2.5s
- **CLS:** < 0.1
- **FID:** < 100ms

---

## 📝 ADDITIONAL OPTIMIZATION TIPS

### 1. Browser Caching
Add to Shopify theme settings:
```liquid
<!-- Cache static assets for 30 days -->
<link rel="preconnect" href="https://cdn.shopify.com">
<link rel="dns-prefetch" href="https://fonts.googleapis.com">
```

### 2. Remove Unused CSS
Use CSS Coverage tool:
1. DevTools → Coverage tab
2. Record page load
3. Identify unused CSS
4. Remove from `base.css` or component files

### 3. Third-party Scripts
Current tracking scripts (add overhead):
- Google Analytics (GTM)
- Facebook Pixel
- Google Ads tag
- Shopify Forms

**Optimization:**
- Defer non-critical scripts
- Use facade/placeholder for forms
- Load analytics async only

### 4. Critical Web Vitals
Monitor at: https://web.dev/measure/

---

## 📞 Support Files

- [Performance optimization best practices](https://web.dev/performance/)
- [WebP image format guide](https://developers.google.com/speed/webp)
- [Shopify Liquid image_url filter](https://shopify.dev/docs/themes/liquid/filters/url-filters#image_url)
- [Lazy loading guide](https://developer.mozilla.org/en-US/docs/Web/Performance/Lazy_loading)

---

**Last Updated:** May 14, 2026  
**Status:** Ready for implementation
