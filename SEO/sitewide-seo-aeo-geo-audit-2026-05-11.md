# Sitewide SEO / AEO / GEO Audit

Date: 2026-05-11

Scope: Live public storefront only.

Inputs used for this audit:
- Live article URLs from `https://pureleven.com/sitemap_blogs_1.xml`
- Live product URLs reconstructed from Shopify Admin active product handles
- Live homepage at `https://pureleven.com/`
- Crawl and AI discovery surfaces: `robots.txt`, `llms.txt`, `llms-full.txt`, `agents.md`, `sitemap.xml`, `sitemap_agentic_discovery.xml`
- Audit artifacts generated during this pass:
  - `tmp/live_article_audit_output.json`
  - `tmp/live_home_product_audit_output.json`

## Executive Summary

The storefront is now split into three very different quality bands.

Articles are technically strong:
- SEO average: 97.5
- AEO average: 91.5
- GEO average: 93.8

Product pages are structurally good but less polished in metadata and crawl efficiency:
- SEO average: 86.3
- AEO average: 92.0
- GEO average: 80.0

The homepage is the weakest SEO surface on the site:
- SEO: 53
- AEO: 68
- GEO: 54

The strongest current advantage is the shared article renderer. It gives most published articles a high technical floor: canonical tags, BlogPosting schema with `articleBody`, breadcrumbs, answer-first sections, FAQ blocks, and strong internal linking.

The biggest remaining problems are now content packaging and crawl freshness, not missing markup.

## Main Findings

### What is working well

- Public crawl surfaces are healthy.
- `robots.txt`, `sitemap.xml`, `llms.txt`, `llms-full.txt`, `agents.md`, and `sitemap_agentic_discovery.xml` all exist and are publicly fetchable.
- Published article pages are structurally strong for both Google and AI retrieval.
- Product pages already expose `Product`, `BreadcrumbList`, and `FAQPage` schema.
- Recent buyer-intent comparison articles are materially stronger than the legacy content estate.

### Main weaknesses

- Homepage metadata is too generic.
- Homepage has two `h1` tags in raw HTML, with the logo wrapped in the first `h1`.
- Homepage raw HTML exposes zero `/blogs/` links, so the blog hub is not benefiting from homepage authority as much as it should.
- Shopify full-page `page_cache` is active on homepage, article pages, and product pages. This can delay how quickly Google and AI crawlers see updated titles, descriptions, schema, and body content after changes go live.
- Product pages carry a very heavy third-party script footprint in the head.
- Several product pages still have weak or too-short meta descriptions.
- Two flagship buyer-intent articles have overlong title tags that should be fixed immediately.

## Crawl And AI Engine Review

### Good signals for Google and AI engines

- Public storefront pages are fetchable without login.
- Canonicals are present on homepage, article pages, and product pages.
- Sitemap index is live and references blogs, products, collections, pages, and the agentic discovery sitemap.
- AI-oriented discovery surfaces are present:
  - `https://pureleven.com/llms.txt`
  - `https://pureleven.com/llms-full.txt`
  - `https://pureleven.com/agents.md`
  - `https://pureleven.com/sitemap_agentic_discovery.xml`
- Product pages and article pages expose structured data that is useful for both search and retrieval systems.

### Hiccups and risks

1. Shopify full-page cache lag is real.

Live responses for homepage, articles, and product pages are currently served with `etag` values tied to Shopify `page_cache` controllers such as:
- `IndexController`
- `BlogArticleDetailsController`
- `ProductDetailsController`

This does not block crawling, but it can delay how fast engines see recently published changes.

2. The parameterless product sitemap endpoint is misleading.

`https://pureleven.com/sitemap_products_1.xml` returns `400` when hit directly. That is not a Google problem because the sitemap index points to the correct ranged URL:

- `https://pureleven.com/sitemap_products_1.xml?from=9887209783589&to=10089847259429`

This is a manual-audit hiccup, not a search-engine blocker.

3. Homepage metadata is not competitive.

Homepage currently exposes:
- Title: `Organic Pure Leven`
- Meta description: `Organic Pure Leven`

That is too weak for branded and non-branded search discovery.

4. Homepage heading structure is noisy.

Raw HTML contains 2 `h1` tags. One is the logo wrapper and one is the hero heading. That weakens hierarchy clarity.

5. Homepage does not visibly route authority into the blog estate.

Raw HTML exposed 0 `/blogs/` links during this pass.

6. Product and homepage head sections are heavy.

The homepage audit found 31 third-party head-script markers. Product pages consistently showed around 30. This does not prevent crawling, but it increases parser noise and can slow first-byte-to-meaningful-content for engines and audit tools.

7. Some titles and meta descriptions are still weak at the page level.

This affects CTR and snippet fit more than indexing, but it directly impacts future growth.

### Bottom line on crawlability

There is no major blocker preventing Google or AI systems from discovering, crawling, or reviewing public pages.

The site’s real risk profile is:
- freshness lag after updates
- weak homepage metadata
- some weak product/article metadata packaging
- heavy script overhead

## Article Estate Review

### Best current article cohort

These pages are the strongest AEO/GEO assets on the site right now:

- `https://pureleven.com/blogs/cooking-spices/kerala-spices-farm-origin-vs-retail`
- `https://pureleven.com/blogs/cooking-spices/kerala-spices-online-kso-vs-farm-sourced-kerala-spices-what-buyers-should-know-1`
- `https://pureleven.com/blogs/cooking-spices/best-kerala-spice-brands-online-india`

Why they win:
- stronger buyer intent
- stronger comparison structure
- stronger entity framing around Kerala origin and sourcing trust
- more obvious bridge from answer to product and collection pages

### Immediate article packaging fixes with highest impact

These two are not the weakest by growth score, but they are urgent because they are flagship conversion pages and their title tags are too long.

1. `https://pureleven.com/blogs/cooking-spices/best-kerala-spice-brands-online-india`
- Current title length: 104
- Current meta description length: 217
- Problem: both are too long and likely truncating in SERPs
- Fix: rewrite title to a 55 to 65 character primary intent version; trim meta to 140 to 160 characters

2. `https://pureleven.com/blogs/cooking-spices/kerala-spices-online-kso-vs-farm-sourced-kerala-spices-what-buyers-should-know-1`
- Current title length: 97
- Problem: title likely truncates before the comparison payoff
- Fix: simplify to a tighter KSO vs farm-sourced comparison title with the keyword closer to the front

## Prioritized Fix List For The Bottom 8 Articles

These are the bottom 8 published articles by current relative growth potential from the live audit.

### 1. Star Anise Benefits And Side Effects
URL: `https://pureleven.com/blogs/cooking-spices/star-anise-benefits-and-side-effects`

Why it is low:
- strong structure but weaker commercial and catalog relevance
- generic informational framing rather than buyer-intent framing

Fix next:
- retitle around a clearer user question such as uses, safety, and flavor profile
- add a comparison block linking star anise to adjacent spices Pureleven actually sells
- add stronger “if you like this flavor profile, try...” commerce bridging

### 2. Culinary Journey With Aromatic Herbs
URL: `https://pureleven.com/blogs/herbs/culinary-journey-with-aromatic-herbs`

Why it is low:
- low topical overlap with current live catalog
- good structure, weaker conversion adjacency

Fix next:
- reframe toward herb-and-spice pairing guidance for Indian kitchens
- add stronger internal links to cinnamon, cardamom, clove, and pepper pages
- turn it into a support page for broader kitchen-use authority, not a standalone growth page

### 3. Kerala Black Pepper Varieties
URL: `https://pureleven.com/blogs/cooking-spices/spice-of-kings-kerala-black-pepper-varieties`

Why it is low:
- story-led title is strong editorially but weaker for comparison search intent
- good SEO floor, less explicit answer targeting than the newest comparison pages

Fix next:
- add a direct varieties comparison table near the top
- tighten the title toward Malabar vs other Kerala pepper intent
- add snippet-friendly subheads for grade, taste, and buying use cases

### 4. Star Anise Cultivation In India
URL: `https://pureleven.com/blogs/cooking-spices/star-anise-cultivation-in-india`

Why it is low:
- weak direct path into current live products
- more educational than transactional

Fix next:
- add an answer-first section for “where is star anise grown in India?”
- add a use-case bridge into adjacent Pureleven pantry products
- add FAQ blocks around sourcing, aroma, and substitutes

### 5. Factors Affecting Cardamom Price In Today’s Market
URL: `https://pureleven.com/blogs/cooking-spices/factors-affecting-cardamom-price-todays-market`

Why it is low:
- meta description is short at 95 characters
- topic has buying intent but the packaging is weaker than it should be

Fix next:
- rewrite title and meta for 2026 price intent
- add a table for size, grade, aroma, and pack-value differences
- add a “which cardamom pack should I buy?” decision block tied to live SKUs

### 6. Kerala Spices To Boost Immunity
URL: `https://pureleven.com/blogs/cooking-spices/kerala-spices-to-boost-immunity`

Why it is low:
- meta description is short at 94 characters
- topic borders health-claim territory and should be framed more carefully

Fix next:
- reposition toward daily kitchen use, warmth, and pantry habits rather than outcome-heavy health framing
- add a practical “how to use these in everyday cooking” section near the top
- strengthen FAQ language around food use, not cure language

### 7. Ultimate Honey Purity Test Guide
URL: `https://pureleven.com/blogs/honey/ultimate-honey-purity-test-guide`

Why it is low:
- technically strong, but weaker direct catalog fit than the spice pages
- likely limited growth until honey product coverage is stronger

Fix next:
- add a cleaner authenticity checklist table
- add stronger cluster linking between honey education pages
- move toward “how to judge quality before buying” intent

### 8. The World Of Local Honey Production
URL: `https://pureleven.com/blogs/cooking-spices/the-world-of-local-honey-production`

Why it is low:
- broad educational framing
- weaker buyer intent than comparison, checklist, or quality-verification topics

Fix next:
- reposition as an origin and sourcing trust page
- add sections on harvest method, traceability, and how buyers can judge local honey quality
- connect it more clearly to any honey collection or future honey product line

## Homepage Review

Current score:
- SEO: 53
- AEO: 68
- GEO: 54

Current issues found in live HTML:
- Title tag is too short: `Organic Pure Leven`
- Meta description is too short: `Organic Pure Leven`
- 2 `h1` tags are present
- no raw `/blogs/` links were detected
- heavy third-party script footprint in the head

What the homepage already does well:
- canonical is correct
- organization and website schema are present
- FAQ schema is present
- product linking is strong

Recommended homepage fixes in order:

1. Rewrite homepage title and meta description.
- Title should include brand + core category + origin signal.
- Meta should explain Kerala, spices, pantry use, and key category coverage.

2. Keep only one semantic `h1`.
- Move the logo wrapper out of `h1` and keep the hero message as the single page `h1`.

3. Add an answer-first homepage summary block above the fold.
- One short paragraph answering what Pureleven is, what it sells, and why the store is distinct.

4. Add direct homepage links into the article hub.
- Link to the strongest comparison and buyer-intent articles.

5. Reduce or defer third-party head scripts where possible.
- Especially non-critical marketing or checkout-adjacent scripts that do not need to execute before content is parsed.

## Product Page Review

Average live product scores:
- SEO: 86.3
- AEO: 92.0
- GEO: 80.0

What product pages already do well:
- `Product` schema is present
- `BreadcrumbList` schema is present
- `FAQPage` schema is present
- answer-first summary / quick guide content is present
- internal linking to collections and blogs exists

Main product-page weaknesses:

1. Heavy third-party script footprint on all 12 audited product pages.

2. Short meta descriptions on these SKUs:
- `kerala-white-pepper-100gm` (28)
- `kerala-clove-100gm` (104)
- `kerala-clove-200gm` (104)
- `premium-cassia-cinnamon-100g` (102)
- `aromatic-true-cinnamon-ceylon-100g` (99)

3. Title / H1 mismatch on these SKUs:
- `kerala-cardamom-8mm-200gm`
- `kerala-black-pepper-300gm`
- `cardamom-50g-black-pepper-100g-clove-100g-3-in-1-spice-combo-pack`
- `cardamom-100g-black-pepper-200g-clove-100g-3-in-1-spice-combo-pack`
- `aromatic-true-cinnamon-ceylon-100g`

4. Product pages are also served through Shopify `page_cache`, so updates may take time to appear in raw fetches.

Recommended product fixes in order:

1. Rewrite the five short meta descriptions first.

2. Normalize title tags and `h1` text so commercial qualifiers such as `Free Delivery`, `OFFER`, or pack breakdowns are consistent.

3. Reduce head-script noise where possible.

4. Keep strengthening buyer-decision content with comparisons, storage guidance, and “best for” language tied to each SKU.

## Next 10 Article Roadmap For AEO And GEO Growth

Every article below should follow the newer pattern:
- answer-first summary at the top
- comparison table or checklist
- 4 to 6 FAQ entries
- clear Kerala-origin or quality entity framing
- direct links to live products and collections

### 1. Malabar vs Tellicherry Pepper: What Is The Difference For Home Cooks?
Primary intent: comparison
Why it matters: high buyer intent, direct fit to black pepper SKUs, strong snippet potential

### 2. Which Cardamom Size Should You Buy? 50g vs 100g vs 200g Guide
Primary intent: purchase decision
Why it matters: maps directly to live pack sizes and supports product comparison snippets

### 3. Ceylon vs Cassia Cinnamon: Which One Is Better For Tea, Baking, And Daily Use?
Primary intent: comparison + use-case
Why it matters: strong AEO format and directly aligned to both cinnamon SKUs

### 4. White Pepper vs Black Pepper: When Should You Use Each One?
Primary intent: comparison + cooking use
Why it matters: supports white pepper growth and creates a direct product bridge

### 5. How To Tell If Cloves Are Fresh: Aroma, Oil, Color, And Storage Checklist
Primary intent: quality verification
Why it matters: strong checklist format and ideal for snippet extraction

### 6. Best Kerala Spice Combo Packs For Gifting vs Daily Cooking
Primary intent: comparison + conversion
Why it matters: maps directly to both combo products and supports gift-intent search

### 7. Kerala Cardamom Price Guide 2026: What Changes Cost And What Is Worth Paying For?
Primary intent: price + value comparison
Why it matters: extends the existing price topic into a more buyer-ready article

### 8. How To Store Whole Spices In Humid Weather Without Losing Aroma
Primary intent: how-to + preservation
Why it matters: strong practical AEO topic with clear checklist and FAQ structure

### 9. What Makes Idukki Spices Different? Elevation, Rainfall, And Aroma Explained
Primary intent: origin / entity education
Why it matters: strong GEO value because it ties the brand to a specific place and quality story

### 10. Best Spices For Homemade Chai: Cardamom, Clove, Cinnamon, And Pepper Guide
Primary intent: use-case bundle
Why it matters: naturally links multiple live SKUs and supports broader pantry entry traffic

## Recommended Order Of Work

### Highest impact this month

1. Fix homepage title, meta description, and heading structure.
2. Fix the two overlong flagship article titles.
3. Rewrite the five weak product meta descriptions.
4. Improve the three thin legacy articles.

### Next content sprint

1. Publish the first three roadmap pieces:
   - Malabar vs Tellicherry Pepper
   - Cardamom Size Buying Guide
   - Ceylon vs Cassia Cinnamon
2. Add homepage links to those articles.
3. Tighten head-script loading where possible.

## Overall Forecast

If the current technical floor stays in place and the next round focuses on metadata fit, homepage cleanup, and more buyer-intent content, the site should be able to grow from a technically sound content layer into a stronger acquisition channel.

Directional forecast:
- low-intervention path: modest growth driven by the already-improved article template
- focused optimization path: stronger organic growth through better CTR, better homepage routing, and more comparison-led AEO/GEO content

The next biggest upside is not adding more generic content. It is making homepage and product metadata sharper, then publishing more comparison-led pages that map tightly to the live SKU set.