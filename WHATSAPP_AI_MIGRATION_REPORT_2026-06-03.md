# WhatsApp AI Migration Report

Date: 2026-06-03  
Project: PureLeven WhatsApp AI Assistant

## Goal

Move runtime behavior away from duplicate FAQ matching and into a deterministic pipeline:

`Product Detection → Intent Detection → Knowledge Retrieval → Dynamic Response Generation`

## Runtime Sources Audited

The refactor was based on these existing sources:

1. `anu-login/backend/app/ai/product_catalog.json`
2. `cleaned_training_data.json` and related training artifacts used by the older matching system
3. `sync_product_catalog_from_wabis_upload.py`
4. Wabis upload-derived pricing and combo definitions already present in the repo
5. Existing live catalog/image data under the product media workflow
6. Customer examples and correction notes provided during live WhatsApp review

## Main Problems Found In The Old Runtime

1. Welcome flow could trigger ahead of product detection.
2. Mixed greeting + product messages could be treated like greetings.
3. White Pepper did not exist as a separate canonical product.
4. Delivery facts were embedded inside product-specific variants.
5. Old FAQ/training-match style answers still leaked into customer-facing replies.
6. Saved legacy state could contain old product keys like `pepper`, which no longer mapped cleanly after refactor work.
7. Some messages were logged but not always answered with a clear customer reply.

## Migration Decisions

### Canonical Product Model

The runtime catalog now uses one normalized schema per product:

- `id`
- `name`
- `aliases`
- `origin`
- `story`
- `quality`
- `use_cases`
- `sizes`
- `recommended_pack`
- `media_links`

### Canonical Products Added / Preserved

- `black_pepper`
- `white_pepper`
- `cardamom`
- `clove`
- `turmeric`
- `ceylon_cinnamon`
- `star_anise`

### Legacy Key Mapping

Old / legacy references are now normalized to canonical ids at runtime:

- `pepper` → `black_pepper`
- `cinnamon` / `patta` / `karuvapatta` → `ceylon_cinnamon`
- `elakka` / `elaichi` → `cardamom`
- `grambu` / `grampu` / `gampoo` → `clove`
- `manjal` / `manjal podi` → `turmeric`
- `vella kurumulak` → `white_pepper`
- `thakkolam` → `star_anise`

## Duplicate Q&A Consolidation

The old style of “one wording = one answer” was not kept as a runtime dependency.

Instead, duplicate phrasing was consolidated into:

- canonical product aliases
- canonical intents
- shared response scenarios

Examples:

- `kurumulak undo?`
- `black pepper undo?`
- `pepper available?`

now resolve through:

- product: `black_pepper`
- intent: `availability`
- language: `manglish` / `english` / `malayalam`

## Canonical Intent Layer

Runtime intent detection now uses a single multilingual registry for:

- `availability`
- `price`
- `details`
- `quality`
- `origin`
- `processing`
- `usage`
- `benefits`
- `best_pack`
- `budget`
- `combo`
- `comparison`
- `price_objection`
- `delivery_charge`
- `delivery_time`
- `free_delivery`
- `order_request`
- `order_confirm`
- `wholesale`
- `gift`
- `stock_check`
- `complaint`
- `return_refund`
- `followup`
- `negation`
- `human_handoff`
- `business_info`
- `payment`
- `fallback`

## Delivery Policy Migration

Delivery is now computed from a single shared rule source.

### Kerala

- order total `₹600+` → free delivery
- below `₹600` → `₹40`

### Outside Kerala

- standard charge `₹120`
- customer charge `₹60`
- PureLeven subsidy `₹60`

Product sizes now store only product price. Delivery is no longer treated as a hardcoded product fact.

## Wabis Ownership Migration

The runtime now follows the chosen ownership model:

- pure new-customer greeting with no prior interaction → Wabis welcome flow
- product-first message → catalog/AI directly
- active Wabis flow + typed product message → latent handoff stored
- Wabis completion/timeout → deferred product reply can be sent once

Welcome flow is no longer supposed to interrupt product-first messages like:

- `white pepper undo?`
- `kurumulak undo?`
- `clove`
- `Hello! Can I get more expa info on cardamom`

## Response Generation Migration

Customer-facing replies now come from:

- canonical product data
- canonical intent
- delivery policy
- reply language / tone

Gemini is now used only for guarded phrasing support and not as the source of truth for:

- price
- stock logic
- delivery rules
- product facts

If Gemini does not provide safe bridge text, deterministic rendering still produces a complete answer.

## Logging Improvements

Routing and response flow now records:

- incoming message
- normalized message
- detected language
- detected product
- detected intent
- route decision
- generated response metadata
- Wabis/AI owner transitions

## Verified-Only Product Notes

The catalog additions followed the “verified only” rule:

- White Pepper pricing was added from the supplied reference:
  - `100g ₹160`
  - `200g ₹300`
  - `250g ₹400`
- Star Anise was kept only with verified sizes already available in project artifacts:
  - `100g ₹180`
  - `500g ₹455`

## Result

The runtime is now structured around:

- canonical product ids
- canonical intent detection
- single delivery policy
- deterministic product knowledge retrieval
- human-style dynamic rendering

The old duplicate-Q&A style remains useful only as offline reference material, not as the primary live response engine.
