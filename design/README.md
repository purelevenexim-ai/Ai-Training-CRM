# Pureleven Design Audit and Safe Rollout Plan

Date: 10 May 2026
Status: Current design direction

## Purpose

This document is the current design source of truth for Pureleven's next visual phase.

The target is not a flashy redesign. The target is visual confidence through typography, spacing, hierarchy, restraint, trust, and premium clarity.

Pureleven should move toward:

> Modern Kerala luxury commerce.

That means:

- calm
- warm
- sensory
- trustworthy
- premium
- clean
- editorial

Not:

- crowded marketplace UI
- aggressive D2C design
- Amazon-style density
- discount-led visual language

## Executive Summary

Pureleven already has several strong ingredients:

- strong Kerala-origin storytelling
- good trust language around freshness and source
- product architecture that supports merchandising
- SEO and GEO-friendly product content blocks already in the theme

The current weakness is system consistency.

The live storefront, repo documentation, and theme styles are not aligned:

- root docs still describe an older "bright organic living" direction
- `assets/design-system.css` still defines an older Playfair/Cormorant/Inter system with teal-first tokens
- live storefront output currently mixes `Bodoni Moda`, `Times`, and `Inter`
- CTA styling, card rhythm, and hierarchy are inconsistent across homepage, collection, and product templates

This should be treated as a typography-system and UI-rhythm migration, not a single font swap.

## Live Store Audit

Audit basis:

- homepage: `https://pureleven.com/`
- collection sample: `https://pureleven.com/collections/export-quality-cardamom`
- product sample: `https://pureleven.com/products/kerala-black-pepper-200gm`
- repo review of header, cards, product CSS, and existing design docs

### What is already working

- Homepage messaging already leans into farm origin, aroma, and Kerala provenance.
- Navigation is simple on mobile and does not force a complex mega-menu.
- Product pages already include answer-first and trust-oriented content modules such as summaries, quick guides, FAQ, and comparison content.
- Reviews, FAQs, origin language, and delivery cues provide a strong trust base.
- Product cards already have a shared styling layer in the repo, which makes controlled improvement possible.

### What is currently weakening premium perception

#### 1. Typography is fragmented

Observed live behavior:

- Homepage hero heading renders in `Bodoni Moda` at roughly `48px`.
- Homepage supporting copy and primary hero buttons render in `Times`.
- Product title and summary also render in `Times`.
- Add to cart buttons use `Inter`, while the accelerated buy button uses a different visual language.

Result:

- the site feels pieced together instead of intentional
- editorial tone and commerce clarity are competing with each other
- the premium story is stronger than the actual typography system

#### 2. Button hierarchy is inconsistent

Observed live behavior:

- Hero CTA uses a full pill radius and smaller button text than ideal for premium commerce.
- Product `Add to cart` uses a dark green rectangular button.
- Product `Buy it now` uses a different yellow style and another radius language.
- CTA systems do not feel unified across homepage, cards, and product page.

Result:

- purchase flow feels less curated than the brand story
- primary and secondary actions compete visually

#### 3. Mobile commerce flow is still underpowered

Observed live behavior:

- On a `390px` mobile viewport, no clear sticky add-to-cart bar was detected on the sampled product page.
- Product CTA height is about `45px`, which is usable but not as generous as the target premium tap zone.

Result:

- mobile purchase confidence is lower than it should be
- high-intent users must scroll back to act

#### 4. Homepage rhythm is too dense

Observed live behavior:

- The homepage contains many valid sections, but the overall experience stacks a lot of proof, products, reviews, and category content without enough pause.
- The story is good, but the visual pacing is not yet luxurious.

Result:

- the site feels busy before it feels premium
- emotional absorption is reduced by section density

#### 5. Collection pages are functionally correct but not editorial enough

Observed live behavior:

- collection pages are mostly title plus product grid
- they do not yet frame the category with much sensory or trust-led context

Result:

- collections feel transactional rather than premium and guided

#### 6. Design source of truth is split

Observed repo behavior:

- legacy docs say the brand is not luxury and should stay bright, family-friendly, and approachable
- newer theme slices already use more premium type and merchandising patterns
- live output still has fallback fonts and mixed component rules

Result:

- safe implementation requires phasing and scoping, not global replacement

## Recommended Design Direction

### Brand feeling

Pureleven should feel like:

- a Kerala spice journal
- a premium modern pantry brand
- a calm luxury commerce experience

Everything should reinforce the same emotional message:

> Warm spice aroma in a calm Kerala kitchen.

### Typography system

Recommended stack:

- Headings: `Sora`
- Body: `Inter`
- Optional serif accent: `Cormorant Garamond`

Why this combination:

- `Sora` gives clean premium structure without becoming ornate
- `Inter` gives highly reliable commerce readability on desktop and mobile
- `Cormorant Garamond` can be reserved for short accents, quotes, and editorial moments instead of becoming the default heading system

Avoid a global heading serif as the default system if the goal is clarity-first premium commerce.

### Typography rules

- Body text desktop: `18px`
- Body text mobile: `16px` to `17px`
- H1 desktop: `48px` to `64px`, fluid
- H1 mobile: `32px` to `40px`, fluid
- H2 desktop: `36px` to `48px`, fluid
- H2 mobile: `24px` to `32px`, fluid
- Body line height: `1.6` to `1.8`
- Heading line height: `1.05` to `1.2`
- Heading tracking: slightly negative where needed
- Text width target: `60` to `75` characters per line

Use fluid typography, not hard-coded pixel swaps:

```css
:root {
  --pl-font-heading: 'Sora', sans-serif;
  --pl-font-body: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --pl-font-accent: 'Cormorant Garamond', serif;

  --pl-step-h1: clamp(2rem, 4.8vw, 4rem);
  --pl-step-h2: clamp(1.75rem, 3.4vw, 3rem);
  --pl-step-h3: clamp(1.25rem, 2.4vw, 2rem);
  --pl-step-body: clamp(1rem, 1.1vw, 1.125rem);
}

h1,
.h1 {
  font-family: var(--pl-font-heading);
  font-size: var(--pl-step-h1);
  line-height: 1.06;
  letter-spacing: -0.03em;
  text-wrap: balance;
  max-width: 12ch;
}

p,
.rte,
.product__description {
  font-family: var(--pl-font-body);
  font-size: var(--pl-step-body);
  line-height: 1.7;
}
```

### Color direction

Recommended core palette:

- Background: `#F8F4EE`
- Text: `#1F1F1F`
- Primary CTA: `#1E1E1E`
- Secondary earthy accent: `#4A3427`
- Supporting olive accent: `#3E4634`
- Soft border: `#DDD2C4`

Color rule:

- keep the base warm and restrained
- use accent color sparingly
- avoid bright sales colors for primary premium moments

### Button system

Recommended system:

- Font: `Inter SemiBold`
- Height: `52px` to `56px`
- Radius: `16px`
- Primary background: `#1E1E1E`
- Primary text: `#F8F4EE`
- Hover: subtle lift and opacity shift only

Recommended CTA voice:

- `Add Fresh Kerala Pepper`
- `Bring Home True Cinnamon`
- `Build Your Spice Pantry`
- `Start Your Spice Ritual`

Avoid overusing generic `Shop Now` or `Buy Now` language outside payment-specific flows.

### Layout rhythm

The premium shift should come from controlled rhythm:

- more whitespace between sections
- tighter heading widths
- fewer simultaneous visual ideas per viewport
- one dominant CTA at a time
- fewer borders and badges on first view

Rule: remove or soften roughly `30%` of visible chrome before adding anything new.

## Shopify-Safe Implementation Roadmap

### Phase 0: Freeze the source of truth

Goal: stop design drift before making visual changes.

Actions:

- Use this file as the active design brief.
- Treat `design_book/` as legacy implementation reference, not brand direction.
- Keep all new UI work on preview themes first.
- Inventory current fonts, radii, button heights, and card variants before any global swap.

### Phase 1: Build the token layer first

Goal: create a modern design system without breaking templates.

Safe files to start with:

- `assets/design-system.css`
- `assets/base.css`
- `layout/theme.liquid`

Actions:

- add a new Pureleven token layer for typography, spacing, radius, and color
- define a fluid type scale with `clamp()`
- add text-width, text-balance, and overflow-safe defaults
- add a shared button token system before restyling individual templates

Do not:

- change every theme setting font in one pass
- replace fonts globally without testing cards, banners, drawers, and app surfaces

### Phase 2: Unify CTA and form language

Goal: make all commerce actions feel like one brand.

Safe files to target:

- `assets/quick-add.css`
- `assets/component-card.css`
- `assets/component-price.css`
- `assets/section-main-product.css`

Actions:

- normalize primary button height to `52px` to `56px`
- normalize radius to `16px` for branded CTA surfaces
- set button font to `Inter SemiBold`
- align quick-add, product CTA, cart CTA, and homepage CTA behavior
- make the accelerated payment button visually compatible without breaking Shopify functionality

### Phase 3: Fix homepage hierarchy

Goal: keep the story, reduce the noise.

Safe files to target:

- `sections/image-banner.liquid`
- `assets/section-image-banner.css`
- `templates/index.json`
- homepage-specific sections already in the repo

Actions:

- simplify hero hierarchy to one premium promise, one proof line, and one primary CTA
- keep one secondary CTA only if it supports exploration, not distraction
- reduce section density and visual repetition below the fold
- preserve farm-origin, freshness, and Kerala cues, but distribute them with more pause

Recommended homepage order:

1. Hero
2. Featured products
3. Why it is different
4. Sensory or origin story
5. Pairings or bundle logic
6. Reviews
7. FAQ

### Phase 4: Upgrade product-page conversion flow

Goal: improve premium feel and mobile conversion without harming SEO or content coverage.

Primary files:

- `sections/main-product.liquid`
- `assets/section-main-product.css`
- `templates/product.json`

Actions:

- keep the current answer-first summary, quick guide, comparison, dossier, and FAQ modules
- tighten above-the-fold spacing
- make title, subtitle, price, trust strip, CTA, and review proof feel like one composed panel
- add a proper sticky mobile purchase rail after scoped QA
- reduce competing actions above the fold
- keep one main purchase CTA and one adjacent upsell/bundle prompt

Important note:

The product page already contains strong SEO and GEO merchandising blocks. Redesign should simplify their presentation, not remove them.

### Phase 5: Elevate collection pages

Goal: make collection pages feel editorial and trust-led.

Primary files:

- `sections/main-collection-product-grid.liquid`
- shared card styles in `assets/component-card.css`

Actions:

- add a short collection intro with origin or sensory framing
- improve spacing above the grid
- keep cards smaller and calmer, with more breathing room
- use shared card CSS only; avoid per-section drift

### Phase 6: Navigation and footer cleanup

Goal: keep navigation calm and useful.

Primary files:

- `sections/header.liquid`
- `assets/component-menu-drawer.css`
- `sections/footer.liquid`

Actions:

- keep mobile navigation simple
- do not introduce a complex mega-menu unless the catalog meaningfully expands
- reduce footer duplication and visual clutter where possible

### Phase 7: Rollout and QA

Goal: ship safely.

Validation checklist:

- desktop at 1440px
- tablet around 768px
- mobile around 390px
- no heading overflow
- no button wrapping
- no fixed-height content clipping
- product cards stable across homepage, collection, search, article, and related products
- add-to-cart and accelerated checkout still functional
- CLS and readability remain stable

## High-Risk Changes To Avoid

- Do not globally change fonts in theme settings without rebuilding the type scale.
- Do not use fixed heights on hero cards, product content panels, or collection cards.
- Do not restyle third-party purchase widgets aggressively in the first pass.
- Do not redesign homepage, collection, and product pages simultaneously.
- Do not add more upsell surfaces before simplifying current CTA hierarchy.
- Do not remove FAQ, trust, comparison, or summary content that already supports SEO and conversion.
- Do not introduce a mega-menu to manufacture premium feel.

## Priority File Map

Use these as the main implementation anchors:

- `assets/design-system.css` - token layer and shared design language
- `layout/theme.liquid` - global variable and asset loading behavior
- `sections/header.liquid` - navigation structure
- `assets/component-card.css` - shared product card presentation
- `assets/component-price.css` - shared price presentation
- `assets/quick-add.css` - shared quick-add button behavior
- `sections/image-banner.liquid` - homepage hero structure
- `assets/section-image-banner.css` - homepage hero presentation
- `sections/main-product.liquid` - product-page structure
- `assets/section-main-product.css` - product-page spacing, CTA, and trust presentation
- `templates/product.json` - block order and page rhythm
- `sections/main-collection-product-grid.liquid` - collection grid structure

## Success Criteria

The redesign is working if:

- typography feels consistent across homepage, collection, and product pages
- primary CTA hierarchy becomes obvious in one glance
- mobile purchase flow becomes easier without adding visual noise
- pages feel calmer even when they still carry trust and SEO content
- the brand reads as premium Kerala-origin commerce rather than a generic spice marketplace

## Final Direction

Pureleven does not need louder design.

Pureleven needs:

- better typography
- fewer competing visual signals
- stronger spacing rhythm
- more controlled CTA hierarchy
- warmer and more restrained color use
- a safer phased rollout through shared CSS and scoped template updates

The opportunity is real because most category competitors still look dated, crowded, or purely SEO-led.

Pureleven can own:

> premium modern Kerala-origin commerce

if the implementation is phased, system-led, and disciplined.