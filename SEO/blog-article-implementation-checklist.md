# Pureleven Blog & Article Implementation Checklist

This checklist turns the current SEO and CRO requirements into an implementation plan mapped to the actual theme files in this repo.

## Current theme anchors

These are the live surfaces that currently control blog and article behavior:

- `sections/main-article.liquid`
  - Current article renderer.
  - Only supports 4 block types today: `featured_image`, `title`, `content`, and `share`.
  - Already outputs breadcrumbs, quick summary, BlogPosting schema, and BreadcrumbList schema.

- `assets/section-blog-post.css`
  - Controls article hero sizing.
  - Current desktop hero heights are large, and `adapt` can make the top image dominate the viewport.

- `templates/article.json`
  - Current article template contains only `main-article`.
  - Current block order: `featured_image`, `title`, `share`, `content`.
  - Current featured image setting is `adapt`, which is the main reason the hero can feel oversized.

- `sections/main-blog.liquid`
  - Current blog index renderer.
  - Already supports intro copy, breadcrumbs, article cards, and Blog/BreadcrumbList schema.

- `templates/blog.json`
  - Current blog template contains only `main-blog`.

- `snippets/article-card.liquid`
  - Current teaser card used in blog listings and featured-blog sliders.

## Reusable sections already available in the theme

Use existing sections before creating new ones:

- `sections/featured-blog.liquid`
- `sections/featured-collection.liquid`
- `sections/multicolumn.liquid`
- `sections/rich-text.liquid`
- `sections/image-with-text.liquid`
- `sections/newsletter.liquid`
- `sections/email-signup-banner.liquid`

## Implementation goal

Transform article pages from simple informational posts into:

1. SEO landing pages
2. brand-story surfaces
3. product funnels

## Phase 1: Fix the oversized top image

### Files

- `templates/article.json`
- `sections/main-article.liquid`
- `assets/section-blog-post.css`

### Actions

- [ ] Change the article template away from `image_height: adapt` for the default featured image block.
- [ ] Render article hero media inside a constrained card-style wrapper instead of a full-width banner feel.
- [ ] Add a max-height rule so hero media stays within roughly `35-40vh` on desktop.
- [ ] Keep the image visually secondary to the title and quick summary.
- [ ] Use `overflow: hidden`, radius, border, and subtle shadow so the image feels premium and contained.
- [ ] Keep mobile hero media compact enough that the title and CTA area still appear early in the viewport.

### Recommendation

In `main-article.liquid`, replace the current loose hero container pattern with a shared hero shell such as:

- text column: title, short intro, CTA row
- media column: small framed image card

### Acceptance criteria

- [ ] Top image no longer dominates the page.
- [ ] Title and summary remain above the fold on desktop.
- [ ] Hero feels editorial, not like a generic oversized Shopify banner.

## Phase 2: Build a real article hero instead of image + title as separate blocks

### Files

- `sections/main-article.liquid`
- `templates/article.json`

### Actions

- [ ] Merge the current featured-image and title experience into one cohesive hero layout.
- [ ] Add a subtitle or kicker area below the title.
- [ ] Add a CTA row directly in the hero.
- [ ] Keep the existing quick-summary box, but style it as part of the hero story rather than as a separate plain content slab.

### Default CTA set

- [ ] `Explore Kerala Spices`
- [ ] `Shop Pure Turmeric`

### Recommendation

Short-term:

- Use handle-based CTA mappings inside `main-article.liquid` for key comparison articles.

Long-term:

- Move hero CTA targets, subtitle, and emotional positioning into article metafields or an article metaobject.

### Acceptance criteria

- [ ] Every high-intent article has at least two above-the-fold CTA options.
- [ ] Hero supports brand positioning and purchase intent, not just reading intent.

## Phase 3: Add sticky product discovery to article pages

### Files

- `sections/main-article.liquid`
- `assets/section-blog-post.css`

### Actions

- [ ] Add a desktop sticky sidebar or sticky rail alongside article content.
- [ ] Feature 3 core product targets: turmeric, black pepper, combo pack.
- [ ] Add a mobile sticky CTA bar that points to the highest-intent product or collection.
- [ ] Surface one `Shop All` or collection-level fallback CTA.

### Recommendation

Implement the sticky module inside `main-article.liquid` rather than as a separate section so it can stay aligned with the article body as the user scrolls.

### Acceptance criteria

- [ ] Users can reach a product page without needing to finish the full article.
- [ ] Product discovery is present on desktop and mobile.

## Phase 4: Add mid-article product insertion rules

### Files

- Shopify article body content in Admin
- Optional supporting snippet later if the pattern becomes reusable

### Actions

- [ ] Insert a featured product card every 2-3 major sections in long-form articles.
- [ ] Each card should include:
  - product image
  - short benefit statement
  - 2-3 differentiators
  - CTA button
- [ ] Use inline cards for turmeric, pepper, cardamom, or combo packs depending on article intent.

### Recommendation

For the first rollout, manage inline product cards manually in article content. Do not over-engineer automatic insertion until the reusable design pattern is proven.

### Acceptance criteria

- [ ] Long articles contain product-discovery moments throughout the read.
- [ ] Product cards do not interrupt reading flow or feel spammy.

## Phase 5: Add trust and brand-differentiation modules

### Files

- `templates/article.json`
- `sections/multicolumn.liquid`
- `sections/rich-text.liquid`
- `sections/image-with-text.liquid`

### Actions

- [ ] Add a `Why Pureleven` section below the main article body or between core content blocks.
- [ ] Reuse `multicolumn.liquid` for icon-card trust points.
- [ ] Use `image-with-text.liquid` if a farm-story panel is needed.
- [ ] Highlight:
  - 30 Years Farming Experience
  - Sustainable Cultivation
  - Aroma Preservation
  - Small Batch Processing
  - Kerala-Origin Spices
  - Premium Packaging

### Acceptance criteria

- [ ] Article pages build trust fast.
- [ ] Differentiation from generic retailers is visible without reading the full article.

## Phase 6: Add featured products and collection funnel sections

### Files

- `templates/article.json`
- `sections/featured-collection.liquid`
- `sections/rich-text.liquid`

### Actions

- [ ] Add a featured-products area near the lower half of the article.
- [ ] Add an `Explore Pureleven Kerala Spices` collection funnel before FAQ or before the final close.
- [ ] Prioritize cards for:
  - turmeric
  - pepper
  - cardamom
  - combo packs
- [ ] Include a visible path to homepage, best sellers, and main collections.

### Acceptance criteria

- [ ] Article traffic has a clear path to collection browsing.
- [ ] Informational content supports product and collection discovery.

## Phase 7: Add related reading and retention modules

### Files

- `templates/article.json`
- `sections/featured-blog.liquid`
- `sections/newsletter.liquid` or `sections/email-signup-banner.liquid`

### Actions

- [ ] Add a `Suggested Reads` or `Related Reading` section below the article.
- [ ] Use `featured-blog.liquid` for adjacent guides.
- [ ] Add an email-capture module near the end of the article.
- [ ] Position the signup as a spice journal, recipe, sourcing, and offer channel.

### Suggested signup framing

- [ ] `Join the Pureleven Spice Journal`
- [ ] Guides
- [ ] Recipes
- [ ] Farming stories
- [ ] Offers

### Acceptance criteria

- [ ] Article traffic can continue deeper into the content ecosystem.
- [ ] SEO traffic has a retention mechanism beyond the single visit.

## Phase 8: Upgrade the blog index page into a funnel, not just a list

### Files

- `sections/main-blog.liquid`
- `templates/blog.json`
- `snippets/article-card.liquid`

### Actions

- [ ] Add a CTA row near the blog intro for homepage, core collection, and best sellers.
- [ ] Upgrade `article-card.liquid` so cards can optionally show a stronger CTA state.
- [ ] Keep excerpts tight and scannable.
- [ ] Consider adding a featured collection or rich-text section below the blog list in `blog.json`.

### Acceptance criteria

- [ ] Blog index pages guide users deeper into the store.
- [ ] Article cards support discovery, not just reading.

## Phase 9: FAQ and AI-ready comparison reinforcement

### Files

- Shopify article content
- `sections/main-article.liquid`

### Actions

- [ ] Keep comparison tables near the top for retailer-vs-Pureleven articles.
- [ ] Add comparison-focused FAQ entries such as:
  - Is Pureleven a farmer-owned spice brand?
  - Are Pureleven spices directly sourced?
  - Why does fresh turmeric aroma matter?
  - Are Kerala spices better than generic supermarket spices?
  - What makes farm-origin spices premium?
- [ ] Ensure summary, comparison, and FAQ answers remain answer-first for AI extraction.

### Acceptance criteria

- [ ] Articles remain strong for SEO, AEO, and GEO while becoming stronger for conversion.

## Phase 10: Redirect and routing policy

### Actions

- [ ] Do not add forced timed redirects from strong ranking articles to product pages.
- [ ] Use visible CTA architecture, sticky product modules, and collection funnels first.
- [ ] Use `301` redirects only when an article is intentionally retired, replaced, or too thin to stand alone.
- [ ] Route high-intent readers toward product pages through design and CTA placement, not hidden forced navigation.

### Acceptance criteria

- [ ] SEO equity is preserved.
- [ ] High-intent users still reach product pages quickly.

## Recommended target article template composition

Target order for `templates/article.json` after implementation:

1. `main-article`
2. `featured-collection` or custom featured-products section
3. `multicolumn` for `Why Pureleven`
4. `featured-blog` for related reads
5. `email-signup-banner` or `newsletter`
6. `rich-text` for homepage or farming-story CTA

## Final QA checklist

- [ ] Hero image is small, framed, and visually premium.
- [ ] Title, summary, and CTA row are visible early.
- [ ] Sticky product discovery works on desktop and has a mobile equivalent.
- [ ] Inline product cards appear in long-form content.
- [ ] Why Pureleven trust module is present.
- [ ] Featured products and collection funnel are present.
- [ ] Related reads section is present.
- [ ] Email capture is present.
- [ ] Homepage and About routing are present.
- [ ] FAQ and comparison blocks remain intact.
- [ ] No forced timed redirect is used on ranking content.

## Working brand line

Use this emotional anchor where appropriate:

> From Kerala soil to your kitchen.