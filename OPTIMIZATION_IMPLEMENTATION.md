# Quick Implementation Guide - Performance Optimizations

**Goal:** Reduce homepage size from 361KB → 120-150KB  
**Expected FCP improvement:** 40-50%  
**Time to implement:** 2-4 hours

---

## 📋 FILES CREATED

| File | Purpose | Status |
|------|---------|--------|
| `snippets/lazy-load-images.liquid` | Enable image lazy-loading | ✅ Ready |
| `snippets/responsive-image.liquid` | WebP format with fallback | ✅ Ready |
| `snippets/critical-styles.liquid` | Critical CSS inlined | ✅ Ready |
| `assets/critical-styles.css` | Minified critical CSS | ✅ Ready |
| `scripts/minify-assets.js` | Minification automation | ✅ Ready |
| `PERFORMANCE_OPTIMIZATION_GUIDE.md` | Full reference guide | ✅ Ready |

---

## 🚀 IMMEDIATE ACTIONS (Do These Now)

### Step 1: Enable Lazy Loading
**File:** `layout/theme.liquid`  
**Find:** The closing `</body>` tag (near end of file)  
**Add before it:**
```liquid
{% render 'lazy-load-images' %}
```

### Step 2: Add Critical CSS
**File:** `layout/theme.liquid`  
**Find:** The `<head>` section (look for `<meta charset=` and other meta tags)  
**Add after the `<meta>` tags and before other stylesheets:**
```liquid
{%- comment -%} Critical above-the-fold styles {%- endcomment -%}
<style>
  {% render 'critical-styles' %}
</style>
```

### Step 3: Async Load Non-Critical CSS
**File:** `layout/theme.liquid`  
**Find:** Where full CSS is loaded (look for lines like `{{ 'base.css' | asset_url }}`)  
**Replace existing stylesheet links with:**
```liquid
{%- comment -%} Async load non-critical CSS {%- endcomment -%}
<link rel="preload" href="{{ 'base.css' | asset_url }}" as="style">
<link rel="stylesheet" href="{{ 'base.css' | asset_url }}" media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="{{ 'base.css' | asset_url }}"></noscript>
```

---

## 🖼️ MEDIUM-TERM ACTIONS (This Week)

### Step 4: Update Key Sections for WebP
Update 5 sections that have the most images:

**Example: `sections/image-banner.liquid`**

**Find:**
```liquid
<img 
  srcset="{{ image | image_url: width: 320 }} 320w, {{ image | image_url: width: 750 }} 750w"
  src="{{ image | image_url: width: 750 }}"
  alt="{{ image.alt }}"
>
```

**Replace with:**
```liquid
{% render 'responsive-image', image: image, alt: image.alt, sizes: '(max-width: 600px) 100vw, 50vw' %}
```

**Sections to update:**
1. `sections/image-banner.liquid` - Hero banner
2. `sections/featured-product.liquid` - Product showcase  
3. `sections/multicolumn.liquid` - Content grid
4. `sections/image-with-text.liquid` - Alternating image/text
5. `sections/collection-list.liquid` - Collection thumbnails

---

## 📊 Step 5: Run Minification Script
**Terminal command:**
```bash
cd /Users/bthomas/Documents/pureleven_dev
node scripts/minify-assets.js
```

**Output:** Creates `.min.css` and `.min.js` versions of all files  
**Expected savings:** 30-50% on CSS/JS

---

## ✅ VERIFICATION CHECKLIST

After implementation, test in Chrome DevTools:

1. **Open DevTools** (F12 or Cmd+Option+I)
2. **Network Tab:**
   - [ ] CSS files load with `media="print"` async pattern
   - [ ] Images show `loading="lazy"`
   - [ ] WebP images download (not JPEG)
   - [ ] Total page size < 180KB

3. **Performance Tab:**
   - [ ] FCP < 800ms (from 972ms)
   - [ ] LCP < 2s
   - [ ] No layout shift (CLS < 0.1)

4. **Lighthouse:**
   - [ ] Run audit
   - [ ] Performance score > 75
   - [ ] Check "Opportunities" section

---

## 🔧 ADVANCED OPTIMIZATION (Optional)

### 1. Image Conversion Tool
Convert your PNG/JPG images to WebP:

**Mac Terminal:**
```bash
# Single file
convert input.jpg -quality 85 output.webp

# Batch convert all JPGs
for file in *.jpg; do 
  convert "$file" -quality 85 "${file%.jpg}.webp"
done

# Resize AND convert
convert input.jpg -resize 750x750 -quality 85 output.webp
```

**Online tool:** https://convertio.co/jpg-webp/  
**Expected savings:** 25-30% per image

### 2. Font Optimization
Current fonts loaded: Cormorant Garamond, Inter, Poppins, Sora  
**Optimize:**
```liquid
<!-- Existing - preconnect to font services -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>

<!-- NEW - Add font-display: swap -->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

### 3. Third-party Script Optimization
Current scripts: GTM, GA4, Facebook Pixel, Google Ads  
**Optimization:** Defer non-essential scripts

```liquid
{%- comment -%} Defer analytics scripts {%- endcomment -%}
<script src="https://www.googletagmanager.com/gtag/js?id=GA_ID" async defer></script>
```

---

## 📈 EXPECTED RESULTS

### Before
- Size: 361KB
- FCP: 972ms
- LCP: ~2.5s

### After (Full Implementation)
- Size: 120-150KB (66% reduction)
- FCP: 500-600ms (45% faster)
- LCP: 1.2-1.5s (50% faster)

### Lighthouse Impact
- Performance: 60 → 80+
- Cumulative Layout Shift: Improved
- First Input Delay: Improved

---

## 🚨 COMMON ISSUES & FIXES

### Issue: Images not loading
**Solution:** Check that `responsive-image.liquid` snippet path is correct

### Issue: WebP not working
**Solution:** Shopify's `image_url` filter automatically supports WebP format
- Verify Shopify theme is up-to-date
- Test in Chrome DevTools Network tab

### Issue: Layout shift when images load
**Solution:** Ensure `responsive-image.liquid` includes width/height attributes

### Issue: Critical CSS not rendering
**Solution:** Make sure `critical-styles.liquid` is called in `<head>` before body content

---

## 📞 RESOURCES

- Full Guide: `PERFORMANCE_OPTIMIZATION_GUIDE.md`
- Minification Script: `scripts/minify-assets.js`
- Shopify Docs: https://shopify.dev/docs/themes/liquid/filters/url-filters#image_url
- Web Vitals: https://web.dev/metrics/
- Performance Testing: https://pagespeed.web.dev

---

**Last Updated:** May 14, 2026  
**Status:** Ready for live implementation
