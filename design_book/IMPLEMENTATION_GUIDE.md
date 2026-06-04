# PURELEVEN — DESIGN & DEVELOPMENT IMPLEMENTATION GUIDE

## Quick Start: How to Use This Brand Book

This guide shows you how to apply the Pureleven brand system to every design and development task.

---

## FILES PROVIDED

1. **BRAND_BOOK.md** — Complete brand guidelines (colors, typography, voice, values)
2. **design-tokens.json** — Machine-readable design data (for developers/design tools)
3. **design-system.css** — Ready-to-use CSS with all components
4. **IMPLEMENTATION_GUIDE.md** (this file) — Step-by-step instructions

---

## BEFORE YOU START DESIGNING

### 1. Review Brand Personality (5 min)

From BRAND_BOOK.md → Section 4:
- Calm, grounded, premium, warm, intelligent, honest, minimal, natural, modern

**Ask yourself:** Does my design feel calm or frantic? Premium or cheap?

### 2. Set Up Design Tool

**Figma Setup:**
- Create a color palette with all colors from BRAND_BOOK.md → Section 6
- Set up typography styles:
  - H1: Nunito Sans, 48px, 700 weight, line-height 1.2
  - H2: Nunito Sans, 36px, 700 weight, line-height 1.3
  - Body: Inter, 16px, 400 weight, line-height 1.6
- Import design-tokens.json as a reference document
- Create component library:
  - Buttons (primary, secondary, tertiary)
  - Cards (product, blog)
  - Forms (input, checkbox)
  - Badges (category-specific)

### 3. Choose Your Color Palette

**For Homepage/General Pages:**
- Primary Teal (#1B5E56) - Primary
- Warm Cream (#F8F5EE) - Background
- Sage Green (#7FA89F) - Accent
- Charcoal (#2C2C2C) - Text

**For Category Pages:**
- Use primary Teal
- Add category accent color:
  - Spices: Terracotta (#B45E3C)
  - Honey: Honey Gold (#C89A3D)
  - Tea: Fresh Teal (#4D9B93)
  - Coffee: Coffee Brown (#5A3E36)
  - Grains: Soft Sand (#E8E5DC)
  - Wellness: Sage Green (#7FA89F)

---

## DESIGNING A PAGE

### Step 1: Define the Hero Section

Every Pureleven page should have a strong hero.

**Requirements:**
- Large background image (1920px × 600px minimum)
- Headline in Nunito Sans (48px+, 700 weight)
- Subheading in Inter (18px, calm tone)
- 1-2 CTAs as primary buttons
- Overlay: 40% dark teal for text contrast

**Example:**
```
Hero Image (bright, fresh photography)
Overlay (Primary Teal, 40% opacity)
Headline: "Pure ingredients for everyday living."
Subheading: "Bright, clean, natural, and welcoming."
CTA: "Explore Collections" (Primary Button)
```

### Step 2: Content Layout

**Typography Hierarchy:**
- H1: Page title, Nunito Sans, 48px (desktop)
- H2: Section titles, Nunito Sans, 36px
- H3: Subsections, Nunito Sans, 28px
- Body: Inter, 16px
- Small text: Inter, 14px

**Spacing:**
- Top section padding: 96px (--space-3xl)
- Between sections: 64px (--space-2xl)
- Card padding: 24px (--space-lg)
- Text line-height: 1.6

### Step 3: Add Components

**Product Cards:**
- Image: Aspect ratio 1:1, cover mode
- Title: Inter 16px bold
- Price: 18px bold, primary green
- Button: Primary button, full width
- Border: 1px light stone beige
- Shadow: --shadow-xs (subtle)
- Hover: Lift 4px, increase shadow

**Buttons:**
- Primary: Forest Green bg, white text, 8px radius, 14px vert padding
- Secondary: Transparent bg, forest green border/text
- Tertiary: Text only, gold on hover

**Form Inputs:**
- Border: 1.5px warm sand color
- Radius: 8px
- Focus: Green border, light green shadow
- Label: Inter 600, 12px, above input

### Step 4: Colors & Contrast

**WCAG AA Compliance Required:**
- Primary text on light bg: 7:1+ contrast
- Body text on light bg: 4.5:1+ contrast
- Large text: 3:1+ minimum

**Use this tool:** https://webaim.org/resources/contrastchecker/

**Safe combinations:**
- Dark text (#1F1F1F) on cream (#F8F5EE): ✅ 9:1
- White text on teal green (#1B5E56): ✅ 7:1
- Gold accent (#C89B3C) on white: ⚠️ 4.5:1 (okay for large text only)

### Step 5: Mobile Responsiveness

**Breakpoints:**
- Mobile: < 640px
- Tablet: 641px - 1024px
- Desktop: > 1025px

**Mobile Rules:**
- Full width with 16px padding
- Single column layout
- Touch targets minimum 44×44px
- Text sizes: H1 32px, body 16px
- Buttons stack vertically
- Cards 1 column grid

**Example:**
```css
/* Desktop */
.grid { grid-template-columns: repeat(4, 1fr); }

/* Tablet */
@media (max-width: 1024px) {
  .grid { grid-template-columns: repeat(2, 1fr); }
}

/* Mobile */
@media (max-width: 640px) {
  .grid { grid-template-columns: 1fr; }
}
```

---

## DEVELOPING A COMPONENT

### Step 1: Structure the HTML

```html
<!-- Product Card Example -->
<article class="product-card">
  <img src="product.jpg" alt="Organic Cardamom" class="product-card__image">
  <div class="product-card__content">
    <h3 class="product-card__title">Organic Cardamom</h3>
    <p class="product-card__description">Premium green cardamom</p>
    <p class="product-card__price">₹299</p>
    <button class="btn btn-primary btn-small">Add to Cart</button>
  </div>
</article>
```

### Step 2: Apply CSS Variables

```css
.product-card {
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: all var(--duration-medium) ease;
  box-shadow: var(--shadow-xs);
}

.product-card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-4px);
}

.product-card__title {
  font-family: var(--font-body);
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.product-card__price {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-primary);
  margin: var(--space-md) 0;
}
```

### Step 3: Ensure Accessibility

```html
<!-- Accessible Form Example -->
<form>
  <label for="email-input">Email Address</label>
  <input 
    id="email-input"
    type="email" 
    placeholder="Enter your email"
    required
    aria-describedby="email-help"
  >
  <small id="email-help">We'll never share your email.</small>
  <button type="submit" class="btn btn-primary">Subscribe</button>
</form>
```

**Checklist:**
- [ ] All inputs have labels
- [ ] Labels associated with `for` attribute
- [ ] Focus styles visible (handled by design-system.css)
- [ ] Color not only indicator (use icons + text)
- [ ] Sufficient contrast (4.5:1+)
- [ ] Semantic HTML (button, form, etc.)

### Step 4: Add to Theme

**File structure:**
```
sections/
  └─ product-card.liquid

snippets/
  └─ product-item.liquid

assets/
  └─ design-system.css (already included in theme.liquid)
```

**Example Liquid snippet:**
```liquid
{% # snippets/product-item.liquid %}
<article class="product-card">
  <img 
    src="{{ product.featured_image | image_url: width: 400 }}" 
    alt="{{ product.featured_image.alt | escape }}"
    class="product-card__image"
    loading="lazy"
  >
  <div class="product-card__content">
    <h3 class="product-card__title">{{ product.title }}</h3>
    <p class="product-card__price">{{ product.price | money }}</p>
    <form action="/cart/add" method="post">
      <input type="hidden" name="id" value="{{ product.selected_or_first_available_variant.id }}">
      <button type="submit" class="btn btn-primary btn-small">
        Add to Cart
      </button>
    </form>
  </div>
</article>
```

---

## CONTENT & COPYWRITING

### Brand Voice Checklist

Before publishing any text:

- [ ] Is it warm and human?
- [ ] Is it honest (no exaggerated claims)?
- [ ] Is it educational?
- [ ] Is it calm (no urgency)?
- [ ] Are sentences short?

**Example:**

❌ **Bad:**
> "BEST ORGANIC SPICES!!! LIMITED TIME!!!"

✅ **Good:**
> "Hand-selected cardamom from Kerala farms. Naturally pure. Lab-tested."

### Product Descriptions

**Formula:**
1. What it is
2. Where it's from
3. Why it matters
4. How to use it

**Example:**
> "**Ceylon Cinnamon** — Premium, lab-tested cinnamon from organic farms in Sri Lanka. Warmer and more delicate than cassia cinnamon. Perfect for morning coffee, baking, and wellness rituals. Sourced directly from trusted partners."

### Category Page Copy

Focus on education, not selling.

**Formula:**
1. Category name & introduction
2. Benefits/why it matters
3. How to choose
4. Popular uses

**Example:**
> "**Our Honey Collection**
>
> Raw, unpasteurized honey from trusted beekeepers. Each jar tells a story of mindful beekeeping and natural nectar collection.
>
> **Why Pure Honey Matters:** Natural enzymes, pollen, and minerals are preserved. No additives. No processing. Just honey.
>
> **How to Choose:** Lighter colors = lighter, floral flavors. Darker = deeper, robust flavors.
>
> **Popular Uses:** Morning wellness ritual, natural sweetener, skincare ingredient."

---

## PHOTOGRAPHY DIRECTION

### What to Shoot

✅ **DO:**
- Natural lighting, golden hour preferred
- Hands interacting with products
- Farm/ingredient-focused
- Editorial composition
- Warm, inviting atmosphere
- Lifestyle moments (not product shots)

❌ **DON'T:**
- Harsh studio lighting
- Isolated white backgrounds
- Stock photo aesthetic
- Over-saturated colors
- Cluttered compositions

### Image Optimization

All images must be:
- Optimized to < 100KB
- High quality (at least 1500px wide)
- Exported as WebP + JPEG fallback
- Include descriptive alt text

**Alt Text Examples:**
- "Organic cardamom pods from Kerala farms"
- "Hands preparing loose leaf green tea"
- "Fresh honey in glass jar from local beekeepers"

---

## SEO IMPLEMENTATION

### Meta Tags for Product Pages

```html
<title>Organic Cardamom from Kerala – Farm-Fresh Quality | Pureleven</title>
<meta name="description" content="Organic green cardamom from Kerala farms – Lab-tested purity, rich flavor. 100% traceable sourcing. Shop premium spices.">
<meta property="og:title" content="Organic Cardamom from Kerala | Pureleven">
<meta property="og:description" content="Premium organic cardamom with guaranteed purity.">
<meta property="og:image" content="https://example.com/cardamom.jpg">
```

### Product Schema (JSON-LD)

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "Product",
  "name": "Organic Cardamom",
  "image": "https://example.com/cardamom.jpg",
  "description": "Premium organic green cardamom from Kerala",
  "brand": {
    "@type": "Brand",
    "name": "Pureleven"
  },
  "offers": {
    "@type": "Offer",
    "priceCurrency": "INR",
    "price": "299",
    "availability": "https://schema.org/InStock"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.8",
    "reviewCount": "127"
  }
}
</script>
```

### Keyword Research

**Core Keywords by Page Type:**

| Page | Keywords | Title Template |
|------|----------|---|
| Spices | organic spices, Kerala cardamom, pure black pepper | "[Product] – Organic Spices from Kerala | Pureleven" |
| Honey | organic honey India, raw honey, natural honey | "[Product] – Premium Organic Honey | Pureleven" |
| Tea | organic tea, green tea India, herbal tea | "[Product] – Organic Tea from India | Pureleven" |
| Collection | buy [category] online, [category] products | "Organic [Category] Online | Pureleven" |

---

## QUALITY CHECKLIST

### Pre-Launch Design

- [ ] Color contrast tested (WCAG AA)
- [ ] Mobile responsive at 320px, 768px, 1920px
- [ ] All interactive elements focusable
- [ ] All images optimized & alt-text added
- [ ] Typography hierarchy clear (H1, H2, H3, body)
- [ ] Spacing consistent with design tokens
- [ ] Brand colors used correctly
- [ ] No spelling/grammar errors
- [ ] Links tested & working
- [ ] Forms tested & submitting

### Pre-Launch Development

- [ ] No console errors
- [ ] Lighthouse score 85+
- [ ] PageSpeed Insights 80+
- [ ] Mobile usability passed
- [ ] CSS validated
- [ ] HTML semantic
- [ ] No unused CSS/JS
- [ ] Images lazy-loaded
- [ ] Fonts preloaded
- [ ] Meta tags present
- [ ] Canonical URLs set
- [ ] Schema markup valid

### Pre-Launch Content

- [ ] Copy reviewed for brand voice
- [ ] No exaggerated claims
- [ ] Educational tone
- [ ] Product descriptions complete
- [ ] Call-to-actions clear
- [ ] Contact info accessible

---

## COMMON DESIGN DECISIONS

### "What color should I use?"

**Decision Tree:**

Is it a CTA or primary action?
→ Teal Green (#1B5E56)

Is it a secondary action?
→ White bg + Forest Green border

Is it an accent/highlight?
→ Sage Green (#7FA89F)

Is it a category badge?
→ Use category color (Spices: Terracotta, etc.)

Is it a warning/error?
→ Error Red (#C62828)

Is it background/section divider?
→ Warm Sand or Cream White

### "What font size should I use?"

**Decision Tree:**

Is it a page title?
→ H1: 56px desktop, 32px mobile

Is it a section title?
→ H2: 42px desktop, 24px mobile

Is it body text?
→ 16px (always)

Is it small/helper text?
→ 14px

### "How much padding should I use?"

**Decision Tree:**

Small component (button, badge)?
→ 8px (--space-sm)

Medium component (card)?
→ 16px (--space-md)

Large section?
→ 24px (--space-lg)

Between major sections?
→ 64px (--space-2xl) or 96px (--space-3xl)

---

## DESIGN SYSTEM RESOURCES

### Figma Components Library
(To be created — Copy these dimensions)

- **Buttons:** 44px height minimum
- **Input fields:** 44px height minimum
- **Product cards:** 300px wide × 400px tall
- **Hero section:** Min 500px tall

### Reusable Snippets

Available in `snippets/`:
- product-card.liquid
- breadcrumbs.liquid
- star-rating.liquid
- newsletter-signup.liquid
- review-badge.liquid

### CSS Variable Reference

Quick copy-paste for common styles:

```css
/* Colors */
background: var(--color-background);
color: var(--color-primary);
border: var(--color-border);

/* Spacing */
padding: var(--space-lg);
margin-bottom: var(--space-md);
gap: var(--space-md);

/* Typography */
font-family: var(--font-heading);
font-family: var(--font-body);

/* Shadows */
box-shadow: var(--shadow-md);

/* Radius */
border-radius: var(--radius-lg);

/* Transitions */
transition: all var(--duration-default) ease;
```

---

## GETTING HELP

### Questions About Brand?
→ See BRAND_BOOK.md (sections 1-6)

### Questions About Design Tokens?
→ See design-tokens.json or BRAND_BOOK.md (sections 7-10)

### Questions About Implementation?
→ See design-system.css or this guide

### Need to Update Brand?
→ Update all three files (maintain consistency)

---

## GLOSSARY

**Design Token:** A reusable value (color, spacing, font size) defined once and used everywhere.

**Semantic HTML:** Using HTML tags that describe meaning (button, form, nav) instead of generic divs.

**WCAG AA:** Web Content Accessibility Guidelines Level AA — standard for accessible web design.

**Contrast Ratio:** Measurement of how different two colors are (higher = more readable).

**Breakpoint:** Screen width where layout changes (320px mobile, 1024px desktop, etc.).

**Brand Voice:** The personality and tone of how we communicate (Pureleven: warm, honest, calm).

---

**Last Updated:** May 7, 2026
**Version:** 1.0
**Maintained By:** Pureleven Design Team
