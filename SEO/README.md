# Pureleven SEO Workspace

This folder stores the working SEO, AEO, GEO, and conversion-planning docs for Pureleven product pages plus blog and article landing-page strategy.

## Files

- [seo.md](seo.md) - master implementation guide covering live product inventory, current gaps, per-product optimization briefs, blog/article conversion requirements, and repo-specific implementation notes.
- [product_readme.md](product_readme.md) - operational checklist for product discovery, article-to-product funneling, redirect policy, and image treatment rules after the recent live push.
- [blog-article-implementation-checklist.md](blog-article-implementation-checklist.md) - file-mapped checklist for upgrading the live article template, blog index, hero image treatment, product funnel modules, and conversion sections.
- [pureleven-top-10-blog-upgrade-briefs.md](pureleven-top-10-blog-upgrade-briefs.md) - execution pack for the first 10 blog-topic upgrades, including live refresh targets, gap briefs, FAQ seeds, internal-link plans, and CTA routing.
- [pureleven-blog-master-upgrade-prompt.md](pureleven-blog-master-upgrade-prompt.md) - reusable prompt for turning an existing Pureleven article or future topic brief into Shopify-ready SEO/AEO/GEO copy without inventing facts.

## Latest live follow-up priorities

The latest live push surfaced three immediate content and CRO follow-ups:

1. Top-of-article imagery is too large. Hero media should be visually constrained, framed inside a card, and limited to a small premium visual rather than a full banner.
2. Every blog and article now needs a defined upsell plan so informational traffic also supports product discovery, collection discovery, and brand storytelling.
3. Product-page routing needs to be clearer. Articles should drive users toward the best-fit product or collection path without hurting SEO or readability.
4. The first 10 blog-topic upgrades should consolidate overlapping intents into stronger existing URLs before new articles are created, especially for storage, aroma-loss, pepper quality, and cardamom sourcing topics.

## Blog implementation pack

Use the new blog-upgrade docs when you are working on content before touching the theme:

1. Start with [pureleven-top-10-blog-upgrade-briefs.md](pureleven-top-10-blog-upgrade-briefs.md) to decide whether the topic belongs in a live refresh, a folded-in section, or a future net-new article.
2. Use [pureleven-blog-master-upgrade-prompt.md](pureleven-blog-master-upgrade-prompt.md) to generate the article body while staying inside verified brand facts and the current Shopify article contract.
3. Keep [blog-article-implementation-checklist.md](blog-article-implementation-checklist.md) nearby when the content brief needs theme-level support such as merchandising, hero treatment, or FAQ rendering changes.
4. The first article-specific rollout now lives in [difference-between-green-and-black-cardamom-shopify-blueprint.md](difference-between-green-and-black-cardamom-shopify-blueprint.md) and [difference-between-green-and-black-cardamom-shopify-body.html](difference-between-green-and-black-cardamom-shopify-body.html).
5. The storage article rollout now lives in [how-to-store-spices-shopify-blueprint.md](how-to-store-spices-shopify-blueprint.md) and [how-to-store-spices-shopify-body.html](how-to-store-spices-shopify-body.html).
6. The black-pepper quality fold-in package now lives in [spice-quality-black-pepper-fold-in-blueprint.md](spice-quality-black-pepper-fold-in-blueprint.md) and [spice-quality-black-pepper-fold-in-body.html](spice-quality-black-pepper-fold-in-body.html).
7. The remaining product-line batch is tracked in [product-line-blog-rollout-matrix.md](product-line-blog-rollout-matrix.md), with full packages now added for white pepper, cinnamon, cloves, combo packs, turmeric, and ginger.

## Current live product inventory

1. `/products/kerala-cardamom-online-100gm`
2. `/products/kerala-cardamom-200gm`
3. `/products/kerala-black-pepper-200gm`
4. `/products/kerala-black-pepper-350gm`
5. `/products/kerala-clove-100gm`
6. `/products/kerala-clove-200gm`
7. `/products/kerala-white-pepper`
8. `/products/cardamom-pepper-clove-combo-pack-special-offer-100-off`
9. `/products/cardamom-50g-black-pepper-100g-clove-100g-3-in-1-spice-combo-pack-copy`
10. `/products/premium-cassia-cinnamon-100g`
11. `/products/aromatic-true-cinnamon-ceylon-100g`

## Highest-priority catalog issues found on the live store

- Two cardamom pages have a title-to-handle pack-size mismatch. The `kerala-cardamom-online-100gm` handle currently resolves to a 200gm title, while `kerala-cardamom-200gm` resolves to a 100gm title.
- `kerala-black-pepper-350gm` currently resolves to a `300gm (OFFER)` title. Handle and title should match exactly.
- One combo page handle still ends in `-copy`, which is weak for SEO and brand trust.
- `product_type` is empty across the live catalog, which weakens taxonomy, filters, schema, and internal search quality.
- Vendor naming is inconsistent. Some products still use `My Store` instead of `Organic Pure Leven`.
- The current product template exposes Product structured data and reviews, but product pages still need dedicated FAQ, comparison, certification, and related-article content blocks.

## Repo implementation anchors

- `sections/main-product.liquid` already outputs Product schema through `{{ product | structured_data }}` and supports `collapsible_tab` blocks that can be used for FAQ content.
- `templates/product.json` currently renders a lean layout: main product, one custom liquid storytelling section, and related products.
- The store already exposes AI-facing discovery files on the live domain: `/llms.txt`, `/llms-full.txt`, `/agents.md`, and `/sitemap_agentic_discovery.xml`.

Use [seo.md](seo.md) as the source of truth before editing Shopify product metadata, adding product metafields, expanding the product template, or revising blog/article layout patterns. Use [product_readme.md](product_readme.md) as the quick execution guide for content funnel and product-routing updates.