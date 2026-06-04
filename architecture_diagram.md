# Server-Side Tracking Architecture

Date: 2026-05-24

## Intended Conversion Flow

```mermaid
flowchart LR
  Visitor[Storefront visitor]
  Storefront[Shopify storefront]
  Attribution[CRM attribution script]
  Shopify[Shopify webhooks]
  CRM[Root CRM / AI Engine :8000]
  DB[(Postgres pureleven)]
  Meta[Meta CAPI]
  GAds[Google Ads API]
  GA4[GA4 Measurement Protocol]
  GTM[GTM Server-Side]

  Visitor --> Storefront
  Storefront --> Attribution
  Attribution -->|page_view, identify, gclid, fbclid, UTMs| CRM
  Storefront -->|checkout and order events| Shopify
  Shopify -->|orders/paid| CRM
  CRM --> DB
  CRM --> Meta
  CRM --> GAds
  CRM --> GA4
  Storefront --> GTM
```

## Actual Live Flow Observed

```mermaid
flowchart LR
  Storefront[Shopify storefront]
  Audience[Product audience snippet]
  MissingAttribution[Missing CRM attribution script]
  TrackHost[track.pureleven.com]
  ApiHost[api.pureleven.com]
  CRM8000[Root CRM :8000]
  Anu8010[anu-login backend :8010]
  Plunk8080[Plunk :8080]
  GTMCloud[GTM Cloud Run]
  Postgres[(Postgres)]
  SQLite[(anu-login SQLite)]
  ShopifyOrderHooks[Shopify order webhooks]
  ShopifyOtherHooks[Shopify cart/checkout/customer hooks]
  Meta[Meta CAPI]
  GAds[Google Ads]
  GA4[GA4 MP]

  Storefront --> Audience
  Audience -->|/api/crm/events/ga4| TrackHost
  TrackHost -->|/api/*| CRM8000
  CRM8000 --> Postgres

  Storefront -. no page_view / identify .-> MissingAttribution

  ShopifyOrderHooks -->|orders/create, orders/paid, orders/fulfilled| ApiHost
  ApiHost --> Plunk8080
  Plunk8080 -. 404 .-> ShopifyOrderHooks

  ShopifyOtherHooks -->|suffixed /api/crm/webhooks/shopify/*| TrackHost
  TrackHost --> CRM8000
  CRM8000 -. 404 for suffixed paths .-> ShopifyOtherHooks

  TrackHost -->|selected WhatsApp paths| Anu8010
  Anu8010 --> SQLite
  SQLite -. 0 rows .-> Anu8010

  TrackHost -->|root /| GTMCloud

  CRM8000 -. not reached for orders/paid .-> Meta
  CRM8000 -. not reached for orders/paid .-> GAds
  CRM8000 -. not reached for orders/paid .-> GA4
```

## Nginx Routing Map

| Host/path | Upstream | Notes |
| --- | --- | --- |
| `track.pureleven.com/api/crm/meta-wa/send` | `127.0.0.1:8010` | WhatsApp send path |
| `track.pureleven.com/api/crm/wabis/send` | `127.0.0.1:8010` | WhatsApp send path |
| `track.pureleven.com/api/crm/ws/` | `127.0.0.1:8010` | WebSocket/WhatsApp path |
| `track.pureleven.com/api/crm/whatsapp/` | `127.0.0.1:8010` | WhatsApp route family |
| `track.pureleven.com/api/journey/` | `127.0.0.1:8010` | Journey route family |
| `track.pureleven.com/api/email/` | `127.0.0.1:8010` | Email route family |
| `track.pureleven.com/api/promo/` | `127.0.0.1:8010` | Promo route family |
| `track.pureleven.com/api/` | `127.0.0.1:8000` | Root CRM/AI Engine |
| `track.pureleven.com/` | GTM Cloud Run | Server-side GTM host root |
| `api.pureleven.com/` | `127.0.0.1:8080` | Plunk, not tracking app |

## Live Shopify Webhook Registration State

| Topic | Current address | Correctness |
| --- | --- | --- |
| `orders/create` | `https://api.pureleven.com/api/shopify/webhook/order-created` | Wrong host; reaches Plunk |
| `orders/paid` | `https://api.pureleven.com/api/shopify/webhook/order-paid` | Wrong host; reaches Plunk |
| `orders/fulfilled` | `https://api.pureleven.com/api/shopify/webhook/order-fulfilled` | Wrong host; reaches Plunk |
| `orders/cancelled` | `https://track.pureleven.com/api/crm/webhooks/shopify/order-cancelled` | Wrong route shape |
| `carts/create` | `https://track.pureleven.com/api/crm/webhooks/shopify/cart-create` | Wrong route shape |
| `carts/update` | `https://track.pureleven.com/api/crm/webhooks/shopify/cart-update` | Wrong route shape |
| `checkouts/create` | `https://track.pureleven.com/api/crm/webhooks/shopify/checkout-create` | Wrong route shape |
| `checkouts/update` | `https://track.pureleven.com/api/crm/webhooks/shopify/checkout-update` | Wrong route shape |
| `customers/create` | `https://track.pureleven.com/api/crm/webhooks/shopify/customer-create` | Wrong route shape |
| `customers/update` | `https://track.pureleven.com/api/crm/webhooks/shopify/customer-update` | Wrong route shape |

## Data Stores

### Postgres: root CRM

Main tracking tables and fields observed in code/schema:

- `crm_events`: browser/audience events, including `/api/crm/events/page_view` and `/api/crm/events/ga4`.
- `crm_customers`: customer identity fields including email, phone, `gclid`, `fbclid`, session/identity metadata.
- `crm_orders`: order records with `gclid`, `fbclid`, UTM fields, `fraud_score`, `capi_suppressed`, `offline_conversion_sent`.
- `conversion_feed`: intended conversion feed model in code, but recent live rows were 0.
- `crm_offline_conversions`: referenced by code, missing in live DB.

### SQLite: anu-login backend

Active DB path: `/opt/anu-login-backend/backend/data/anu_login.sqlite3`.

Important tables exist but are empty:

- `event_logs`: 0 rows.
- `journey_customers`: 0 rows.
- `journey_messages`: 0 rows.
- `journey_engagement_events`: 0 rows.

The live `journey_customers` table lacks expected attribution columns such as `meta_lead_id`, `google_gclid`, and `fbc`.

## Desired Remediated Architecture

```mermaid
flowchart LR
  Storefront[Shopify storefront]
  Attribution[crm-attribution.js]
  ShopifyHooks[Shopify webhooks]
  TrackHost[track.pureleven.com]
  CRM[Root CRM :8000]
  Queue[(conversion queue)]
  Postgres[(Postgres)]
  Meta[Meta CAPI]
  Google[Google Ads API]
  GA4[GA4 MP]
  Logs[response logs]

  Storefront --> Attribution
  Attribution -->|page_view, identify, fbp, fbc, gclid, UTMs, ga client id| TrackHost
  ShopifyHooks -->|all topics on reachable routes| TrackHost
  TrackHost --> CRM
  CRM --> Postgres
  CRM --> Queue
  Queue --> Meta
  Queue --> Google
  Queue --> GA4
  Meta --> Logs
  Google --> Logs
  GA4 --> Logs
```

The root app should be the system of record for conversion fan-out unless the anu-login service is explicitly migrated and made active.

## Post-Fix Live Routing

As of 2026-05-24, Shopify webhook readback shows the following corrected state:

- `orders/create`, `orders/paid`, and `orders/fulfilled` now have root CRM webhooks at `https://track.pureleven.com/api/crm/webhooks/shopify`.
- `orders/create`, `orders/paid`, and `orders/fulfilled` also retain direct journey webhooks at `https://track.pureleven.com/api/shopify/webhook/order-*`.
- `orders/cancelled`, cart, checkout, and customer webhooks now point to the unified root CRM endpoint.
- There are no remaining webhook addresses on `api.pureleven.com`.
- There are no remaining suffixed `/api/crm/webhooks/shopify/...` webhook addresses.

The currently verified live path is:

```mermaid
flowchart LR
  Shopify[Shopify webhooks]
  Track[track.pureleven.com]
  CRM[Root CRM :8000]
  Journey[Direct order/journey routes]
  Postgres[(Postgres)]
  Meta[Meta CAPI]
  Google[Google Ads]
  GA4[GA4 MP]

  Shopify -->|orders/paid root CRM subscription| Track
  Track -->|/api/crm/webhooks/shopify| CRM
  CRM --> Postgres
  CRM --> Meta
  CRM --> Google
  CRM --> GA4
  Shopify -->|orders/paid direct subscription| Track
  Track -->|/api/shopify/webhook/order-paid| Journey
```

Destination delivery remains pending validation on the next real paid order.
