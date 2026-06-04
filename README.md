# PURELEVEN — Shopify Theme Development

> Current direction: modern Kerala luxury commerce with calm, warm, premium editorial restraint.

This repo contains both the current migration plan and older Pureleven design documentation. Start with the current plan first, then use the older docs only as implementation reference while the theme is being migrated.

---

## ⚠️ IMPORTANT: READ BEFORE MAKING ANY DESIGN CHANGES

**Before you make ANY design or development changes to this theme, read the current design roadmap first.**

### Current Design Roadmap
The active design direction and storefront audit now live in the `design/` folder:

```
design/
└── README.md                  (Current design audit, premium direction, safe rollout plan)
```

### Legacy Design Documentation
The older design system still lives in `design_book/`. Keep using it for implementation detail and component reference until the migration is complete, but do not treat it as the current brand direction.

### Design Book Location
Older design guidelines, brand standards, and implementation instructions are in the `design_book/` folder:

```
design_book/
├── BRAND_BOOK.md              (Comprehensive brand system — START HERE)
├── design-tokens.json         (All design values in JSON)
└── IMPLEMENTATION_GUIDE.md    (Step-by-step instructions)
```

---

## 🎯 CURRENT STRATEGIC SNAPSHOT

### Brand Direction
Pureleven should feel like premium Kerala-origin commerce:

- calm
- warm
- sensory
- trustworthy
- clean
- editorial
- mobile-first

### Core Design Goal
Build visual confidence through:

- typography
- spacing
- rhythm
- hierarchy
- emotional restraint

### What To Avoid
- crowded marketplace UI
- aggressive D2C styling
- generic discount-commerce patterns
- global font swaps without a responsive typography system

### Migration Note
The existing `design_book/` and parts of the live theme still reflect an older "bright organic living" direction. Use `design/README.md` as the current source of truth and treat older docs as legacy implementation context until the new system is rolled out.

## 🎯 LEGACY BRAND SNAPSHOT

### Brand Essence
Pureleven is a **modern organic living brand** focused on natural foods, wellness, and everyday healthy living.

### Brand Tagline
> Pure ingredients for everyday living.

### Core Values
- **Bright** — Clean, optimistic, approachable
- **Natural** — Rooted in organic living
- **Trustworthy** — Honest sourcing and quality
- **Educational** — Ingredient and wellness focused
- **Welcoming** — Family-friendly and accessible
- **Fresh** — Healthy and energizing

### What Pureleven IS
✅ Bright, clean, natural, family-friendly
✅ Educational and approachable
✅ Everyday organic living
✅ Healthy pantry ecosystem
✅ Trustworthy and transparent

### What Pureleven IS NOT
❌ Luxury fashion brand
❌ Dark wellness aesthetic
❌ Ultra-premium editorial
❌ Minimal luxury
❌ Overly complicated

### Core Colors
- **Primary Teal:** #1B5E56 (trust, organic, healthy)
- **Fresh Teal:** #4D9B93 (freshness, wellness)
- **Warm Cream:** #F8F5EE (main background)
- **Soft Sand:** #E8E5DC (cards, layers)
- **Sage Accent:** #7FA89F (badges, tags)
- **Charcoal:** #2C2C2C (typography)

### Typography
- **Headings:** Nunito Sans (approachable, modern, friendly)
- **Body:** Inter (readable, clean, modern)

### Product Categories
1. **Spices** — Terracotta accent (#B45E3C)
2. **Honey** — Honey Gold accent (#C89A3D)
3. **Tea** — Fresh Teal accent (#4D9B93)
4. **Coffee** — Coffee Brown accent (#5A3E36)
5. **Grains** — Soft Sand accent (#E8E5DC)
6. **Wellness** — Sage Accent (#7FA89F)

---

## 📖 REQUIRED READING BEFORE ANY CHANGES

### 1. **design/README.md** (START HERE)
Current design source of truth covering:
- the new Kerala premium commerce direction
- live storefront audit findings
- typography, color, CTA, and spacing recommendations
- phased rollout plan
- high-risk changes to avoid

**Critical for:** All design and frontend decisions

### 2. **BRAND_BOOK.md** (LEGACY REFERENCE)
Comprehensive brand system covering:
- Brand positioning and personality
- Visual identity and color system
- Typography and photography style
- UI philosophy and component systems
- Homepage structure and SEO strategy

**Use for:** Legacy reference and implementation context

### 3. **IMPLEMENTATION_GUIDE.md** (LEGACY HOW-TO)
Practical implementation covering:
- Color usage and the 70-20-10 rule
- Button and card systems
- Mobile UX rules
- Accessibility requirements
- Shopify architecture

**Use for:** Existing theme patterns that have not yet been migrated

### 4. **design-tokens.json** (LEGACY REFERENCE)
Machine-readable design values for:
- All colors with hex codes
- Typography scales
- Spacing system
- Component specifications
- Category definitions

**Use for:** Existing tokens and transition planning

---

## 🚀 GETTING STARTED

### First Time?
1. Read `design/README.md`
2. Review `design_book/BRAND_BOOK.md` for legacy context
3. Skim `design_book/IMPLEMENTATION_GUIDE.md`
4. Reference `design-tokens.json` only when working inside legacy token patterns

### Key Principle: The 70-20-10 Rule
- **70%** Neutral backgrounds (Warm Cream, White, Soft Sand)
- **20%** Brand colors (Primary Teal, Fresh Teal)
- **10%** Accent colors (Terracotta, Honey Gold, Sage)

Keep the site clean, bright, organic, and approachable.
3. Keep `design_book/design-tokens.json` handy
4. Review the Quality Checklist before launching anything

### Making Changes?
1. **Before:** Check `design_book/IMPLEMENTATION_GUIDE.md` for relevant section
2. **Reference:** Look up color/spacing/typography in `design_book/BRAND_BOOK.md`
3. **Verify:** Use Quality Checklist before submitting changes
4. **When stuck:** Search the design book for your question

### Unsure About a Design Decision?
→ Check `IMPLEMENTATION_GUIDE.md` section "Common Design Decisions"

---

## 📁 FOLDER STRUCTURE

```
pureleven_dev/
├── design/                     (👈 CURRENT DESIGN DIRECTION + SAFE ROLLOUT PLAN)
│   └── README.md
├── design_book/                (👈 ALL DESIGN DOCS HERE)
│   ├── BRAND_BOOK.md
│   ├── design-tokens.json
│   └── IMPLEMENTATION_GUIDE.md
├── assets/
│   ├── design-system.css       (Production CSS with all components)
│   └── ...
├── sections/
├── snippets/
├── templates/
├── config/
├── layout/
└── README.md                   (This file)
```

---

## ⚡ QUICK REFERENCE

### Color Palette
```
Forest Green:    #1E4B43
Deep Olive:      #556B57
Cream White:     #F8F5EE
Warm Sand:       #DDD0B8
Honey Gold:      #C89B3C
Coffee Brown:    #4B362F
Charcoal:        #1F1F1F
```

### Spacing Scale
```
xs: 4px   | sm: 8px   | md: 16px  | lg: 24px
xl: 40px  | 2xl: 64px | 3xl: 96px
```

### Font Sizes
```
H1: 56px (desktop) / 32px (mobile)
H2: 42px (desktop) / 24px (mobile)
H3: 32px (desktop) / 20px (mobile)
Body: 16px (always)
Small: 14px
```

### Button Colors
```
Primary:   Forest Green (#1E4B43) with white text
Secondary: Transparent bg, Forest Green border
Tertiary:  Text only, gold on hover
```

### Contrast Ratios (WCAG AA)
```
Dark text on light bg:  7:1+ ✅
Body text on light:     4.5:1+ ✅
Large text minimum:     3:1 ✅
```

---

## 🔍 BEFORE YOU CODE

### Pre-Design Checklist
- [ ] Read BRAND_BOOK.md sections 1-6
- [ ] Review relevant page type in IMPLEMENTATION_GUIDE.md
- [ ] Check color palette for your section type
- [ ] Define typography hierarchy
- [ ] Plan responsive breakpoints

### Pre-Development Checklist
- [ ] HTML is semantic
- [ ] CSS uses variables from design-system.css
- [ ] Focus states visible on all interactive elements
- [ ] Images optimized and have alt text
- [ ] Mobile responsive (tested at 320px, 768px, 1920px)
- [ ] Contrast tested (WCAG AA minimum)
- [ ] Forms accessible (labels, proper focus)

### Pre-Launch Checklist
- [ ] Lighthouse score 85+
- [ ] Mobile usability passed
- [ ] Copy reviewed for brand voice
- [ ] All links tested
- [ ] No console errors
- [ ] Meta tags present
- [ ] Schema markup valid

---

## 📞 COMMON QUESTIONS

**Q: What color should I use for this button?**
→ Read BRAND_BOOK.md → Section 7 (Color System) and IMPLEMENTATION_GUIDE.md → "What color should I use?"

**Q: How much padding should this card have?**
→ See BRAND_BOOK.md → Section 9 (Spacing System), default is --space-lg (24px)

**Q: What font should the heading be?**
→ Always Playfair Display. Check size in BRAND_BOOK.md → Section 8 (Typography Hierarchy)

**Q: How do I make this accessible?**
→ See IMPLEMENTATION_GUIDE.md → "Developing a Component" → "Step 3: Ensure Accessibility"

**Q: What's the focus state style?**
→ Check design-system.css or BRAND_BOOK.md → Section 10 (Button System)

**Q: Is my design mobile responsive?**
→ Use checklist in IMPLEMENTATION_GUIDE.md → "Quality Checklist"

---

## 📚 DESIGN SYSTEM FILES

### design-system.css
Production-ready CSS with:
- 60+ CSS custom properties
- Button component styles
- Form input styles
- Card components
- Badge system
- Layout utilities
- Accessibility features
- 900+ lines of code

**Location:** `assets/design-system.css`
**Usage:** Already linked in theme.liquid

### Figma Component Library
(To be created — reference dimensions in IMPLEMENTATION_GUIDE.md)

---

## 🎨 BRAND VOICE RULES

**ALWAYS:**
- Use warm, friendly tone
- Be honest and transparent
- Educate the customer
- Use calm, short sentences
- Focus on quality over sales

**NEVER:**
- Use aggressive language
- Make exaggerated claims
- Create fake urgency
- Overuse exclamation marks
- Use spammy wellness language

**Example:**
❌ "BUY NOW!!! LIMITED TIME OFFER!!!"
✅ "Carefully sourced from trusted Kerala farms."

---

## 🚢 DEPLOYMENT

Before deploying any theme changes:

1. ✅ Run through Pre-Launch Checklist
2. ✅ Test on actual Shopify store preview
3. ✅ Check all 6 product categories render correctly
4. ✅ Test on mobile, tablet, desktop
5. ✅ Verify all forms are functional
6. ✅ Check Lighthouse score (target: 85+)
7. ✅ Validate schema markup
8. ✅ Review with brand team if major changes

---

## 📝 KEEPING DOCUMENTATION UPDATED

If you:
- Add a new component → Update BRAND_BOOK.md Section 10
- Change colors → Update BRAND_BOOK.md Section 7 AND design-tokens.json
- Add spacing system changes → Update both files
- Create new pattern → Add to IMPLEMENTATION_GUIDE.md examples

**Keep all three files in sync.**

---

## 🔗 USEFUL TOOLS

- **Contrast Checker:** https://webaim.org/resources/contrastchecker/
- **Lighthouse:** Built into Chrome DevTools
- **Schema Validator:** https://validator.schema.org/
- **Responsive Tester:** https://responsively.app/

---

## 📧 QUESTIONS?

Before asking, check:
1. `design_book/BRAND_BOOK.md` (search for keyword)
2. `design_book/IMPLEMENTATION_GUIDE.md` (search for keyword)
3. `assets/design-system.css` (check component code)

---

## 📅 VERSION HISTORY

- **v1.0** — May 7, 2026
  - Initial brand book creation
  - Design system implementation
  - Complete documentation

---

**Last Updated:** May 7, 2026  
**Maintained By:** Pureleven Design Team  
**Status:** Active

⚠️ **REMEMBER:** Always read the design book before making changes!
