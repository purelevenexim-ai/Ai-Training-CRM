"""
Shopify intelligence sync worker for PureLeven.

Fetches REAL data from Shopify Admin API and stores locally.
This is the single source of truth — AI NEVER generates data, only reads this.

Syncs:
  - Products (title, price, description, images, tags)
  - Inventory (per variant, real-time quantity)
  - Discount codes (active offers, validity)
  - Blog content (educational articles, harvest notes)
  - Product reviews (if metafields available)

Schedule: Every 30 minutes via n8n or startup call.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings
from app.storage import get_db_connection

logger = logging.getLogger(__name__)

SHOPIFY_API_VERSION = "2026-07"


def _shopify_headers() -> dict[str, str]:
    return {
        "X-Shopify-Access-Token": settings.shopify_admin_api_token,
        "Content-Type": "application/json",
    }


def _shopify_base_url() -> str:
    domain = settings.default_shop_domain
    return f"https://{domain}/admin/api/{SHOPIFY_API_VERSION}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# Products
# ─────────────────────────────────────────────────────────────────────────────

def sync_products() -> int:
    """
    Fetch all active products from Shopify and upsert into shopify_products.
    Returns count of products synced.
    """
    if not settings.shopify_admin_api_token or not settings.default_shop_domain:
        logger.warning("Shopify credentials not set — product sync skipped")
        return 0

    synced = 0
    url = f"{_shopify_base_url()}/products.json"
    params = {"status": "active", "limit": 250, "fields": "id,title,body_html,vendor,product_type,tags,variants,images,metafields"}

    try:
        with httpx.Client(timeout=30.0) as client:
            while url:
                resp = client.get(url, headers=_shopify_headers(), params=params if "?" not in url else {})
                resp.raise_for_status()
                data = resp.json()
                products = data.get("products", [])

                with get_db_connection() as conn:
                    for p in products:
                        _upsert_product(conn, p)
                        synced += 1

                # Pagination
                link_header = resp.headers.get("Link", "")
                url = _extract_next_page_url(link_header)
                params = {}  # already included in paginated url

    except httpx.HTTPStatusError as e:
        logger.error("Shopify product sync HTTP error %s: %s", e.response.status_code, e.response.text[:300])
    except Exception as exc:
        logger.error("Shopify product sync failed: %s", exc)

    logger.info("Shopify product sync complete: %d products", synced)
    return synced


def _upsert_product(conn: Any, p: dict[str, Any]) -> None:
    """Upsert a single Shopify product into the local DB."""
    now = _now()
    shopify_product_id = str(p["id"])

    existing = conn.execute(
        "SELECT id FROM shopify_products WHERE shopify_product_id = ?",
        (shopify_product_id,),
    ).fetchone()
    row_id = str(existing["id"]) if existing else str(uuid.uuid4())

    # Pick lowest price from variants (most common price)
    variants = p.get("variants") or []
    prices = [float(v.get("price") or 0) for v in variants if v.get("price")]
    compare_prices = [float(v.get("compare_at_price") or 0) for v in variants if v.get("compare_at_price")]
    price = min(prices) if prices else 0.0
    compare_at_price = min(compare_prices) if compare_prices else None

    # Images
    images = p.get("images") or []
    featured_image = images[0]["src"] if images else None
    images_json = json.dumps([img["src"] for img in images[:5]])

    # Tags
    tags = p.get("tags") or ""
    # Strip HTML from description
    body_html = p.get("body_html") or ""
    description = _strip_html(body_html)[:1000]

    # Collections stored as tags for now
    conn.execute(
        """
        INSERT INTO shopify_products
          (id, shopify_product_id, title, description, price, compare_at_price,
           tags, featured_image_url, images_json, synced_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
          title              = excluded.title,
          description        = excluded.description,
          price              = excluded.price,
          compare_at_price   = excluded.compare_at_price,
          tags               = excluded.tags,
          featured_image_url = excluded.featured_image_url,
          images_json        = excluded.images_json,
          synced_at          = excluded.synced_at
        """,
        (row_id, shopify_product_id, p["title"], description, price, compare_at_price,
         tags, featured_image, images_json, now, now),
    )

    # Store a single inventory summary row per product.
    _upsert_inventory_summary(conn, row_id, variants)


def _upsert_inventory_summary(conn: Any, local_product_id: str, variants: list[dict[str, Any]]) -> None:
    """Upsert a simplified inventory summary row for a product."""
    now = _now()

    quantities = [int(v.get("inventory_quantity") or 0) for v in variants]
    qty = sum(quantities)
    variant_id = ",".join(str(v.get("id", "")) for v in variants if v.get("id"))
    size_label = ", ".join(str(v.get("title") or "") for v in variants if v.get("title"))

    if qty <= 0:
        status = "out_of_stock"
    elif qty <= 5:
        status = "critical"
    elif qty <= 20:
        status = "medium"
    else:
        status = "plenty"

    existing = conn.execute(
        "SELECT id FROM shopify_inventory WHERE product_id = ?",
        (local_product_id,),
    ).fetchone()
    row_id = str(existing["id"]) if existing else str(uuid.uuid4())

    conn.execute(
        """
        INSERT INTO shopify_inventory (id, product_id, variant_id, size_label, quantity, status, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          quantity   = excluded.quantity,
          status     = excluded.status,
          variant_id  = excluded.variant_id,
          size_label  = excluded.size_label,
          updated_at = excluded.updated_at
        """,
        (row_id, local_product_id, variant_id, size_label, qty, status, now),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Discount Codes / Offers
# ─────────────────────────────────────────────────────────────────────────────

def sync_offers() -> int:
    """
    Fetch active discount codes from Shopify and store in shopify_offers.
    Returns count synced.
    """
    if not settings.shopify_admin_api_token or not settings.default_shop_domain:
        return 0

    synced = 0
    now = _now()

    try:
        with httpx.Client(timeout=30.0) as client:
            # Fetch price rules (parent of discount codes)
            url = f"{_shopify_base_url()}/price_rules.json"
            resp = client.get(url, headers=_shopify_headers(), params={"limit": 250})
            resp.raise_for_status()
            rules = resp.json().get("price_rules", [])

            with get_db_connection() as conn:
                for rule in rules:
                    # Fetch codes for this rule
                    rule_id = rule["id"]
                    codes_url = f"{_shopify_base_url()}/price_rules/{rule_id}/discount_codes.json"
                    codes_resp = client.get(codes_url, headers=_shopify_headers())
                    if codes_resp.status_code != 200:
                        continue
                    codes = codes_resp.json().get("discount_codes", [])

                    for code_obj in codes:
                        code = code_obj.get("code", "").upper()
                        if not code:
                            continue

                        # Discount type + value
                        value_type = rule.get("value_type", "percentage")
                        value = abs(float(rule.get("value") or 0))

                        # Validity
                        valid_from = rule.get("starts_at")
                        valid_until = rule.get("ends_at")

                        # Usage
                        uses_limit = rule.get("usage_limit")
                        uses_count = int(code_obj.get("usage_count") or 0)

                        # Is active: not expired, not depleted
                        is_active = 1
                        if valid_until and valid_until < now:
                            is_active = 0
                        if uses_limit and uses_count >= uses_limit:
                            is_active = 0

                        conn.execute(
                            """
                            INSERT INTO shopify_offers
                              (id, code, discount_type, discount_value, valid_from, valid_until,
                               applicable_products, max_uses, uses_so_far, is_active, synced_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(code) DO UPDATE SET
                              discount_type  = excluded.discount_type,
                              discount_value = excluded.discount_value,
                              valid_until    = excluded.valid_until,
                              max_uses       = excluded.max_uses,
                              uses_so_far    = excluded.uses_so_far,
                              is_active      = excluded.is_active,
                              synced_at      = excluded.synced_at
                            """,
                            (
                                str(uuid.uuid4()), code, value_type, value,
                                valid_from, valid_until, "[]",
                                uses_limit, uses_count, is_active, now,
                            ),
                        )
                        synced += 1

    except httpx.HTTPStatusError as e:
        logger.error("Shopify offers sync HTTP error %s: %s", e.response.status_code, e.response.text[:300])
    except Exception as exc:
        logger.error("Shopify offers sync failed: %s", exc)

    logger.info("Shopify offers sync complete: %d offers", synced)
    return synced


# ─────────────────────────────────────────────────────────────────────────────
# Blog / Educational Content
# ─────────────────────────────────────────────────────────────────────────────

def sync_blogs() -> int:
    """
    Fetch all published blog articles from Shopify and store in shopify_content.
    Used for educational messaging, story building, recipe ideas.
    """
    if not settings.shopify_admin_api_token or not settings.default_shop_domain:
        return 0

    synced = 0
    now = _now()

    try:
        with httpx.Client(timeout=30.0) as client:
            # Get all blogs
            blogs_resp = client.get(f"{_shopify_base_url()}/blogs.json", headers=_shopify_headers())
            blogs_resp.raise_for_status()
            blogs = blogs_resp.json().get("blogs", [])

            with get_db_connection() as conn:
                for blog in blogs:
                    blog_id = blog["id"]
                    # Get articles for this blog
                    articles_url = f"{_shopify_base_url()}/blogs/{blog_id}/articles.json"
                    art_resp = client.get(
                        articles_url,
                        headers=_shopify_headers(),
                        params={"limit": 250, "published_status": "published"},
                    )
                    if art_resp.status_code != 200:
                        continue

                    for article in art_resp.json().get("articles", []):
                        content_id = f"blog_{article['id']}"
                        title = article.get("title") or ""
                        body = _strip_html(article.get("body_html") or "")[:2000]
                        tags = article.get("tags") or ""
                        published_at = article.get("published_at")
                        source_url = f"https://pureleven.com/blogs/{blog.get('handle','news')}/{article.get('handle','')}"

                        # Determine product relevance from tags + title
                        product_tags = _extract_product_tags(f"{title} {tags} {body}")

                        conn.execute(
                            """
                            INSERT INTO shopify_content
                              (id, content_type, title, body, product_tags, published_at, source_url, synced_at)
                            VALUES (?, 'blog_article', ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(id) DO UPDATE SET
                              title       = excluded.title,
                              body        = excluded.body,
                              product_tags = excluded.product_tags,
                              synced_at   = excluded.synced_at
                            """,
                            (content_id, title, body, json.dumps(product_tags),
                             published_at, source_url, now),
                        )
                        synced += 1

    except httpx.HTTPStatusError as e:
        logger.error("Shopify blog sync HTTP error %s: %s", e.response.status_code, e.response.text[:300])
    except Exception as exc:
        logger.error("Shopify blog sync failed: %s", exc)

    logger.info("Shopify blog sync complete: %d articles", synced)
    return synced


# ─────────────────────────────────────────────────────────────────────────────
# Query helpers (used by AI renderer and routes)
# ─────────────────────────────────────────────────────────────────────────────

def get_active_products(conn: Any, limit: int = 20) -> list[dict[str, Any]]:
    """Return active products with inventory status."""
    rows = conn.execute(
        """
        SELECT p.*, i.quantity, i.status as inventory_status
        FROM shopify_products p
        LEFT JOIN shopify_inventory i ON p.id = i.product_id
        WHERE i.status != 'out_of_stock' OR i.status IS NULL
        ORDER BY p.synced_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_product_by_id(conn: Any, product_id: str) -> dict[str, Any] | None:
    """Fetch a single product by its local DB id (not Shopify id)."""
    row = conn.execute(
        """
        SELECT p.*, i.quantity, i.status as inventory_status
        FROM shopify_products p
        LEFT JOIN shopify_inventory i ON p.id = i.product_id
        WHERE p.id = ?
        """,
        (product_id,),
    ).fetchone()
    return dict(row) if row else None


def get_active_offer_for_product(conn: Any, product_id: str | None = None) -> dict[str, Any] | None:
    """
    Return the best active offer. Optionally filtered by product.
    ONLY returns offers that are currently valid in Shopify.
    """
    now = _now()
    row = conn.execute(
        """
        SELECT * FROM shopify_offers
        WHERE is_active = 1
          AND (valid_until IS NULL OR valid_until > ?)
          AND (max_uses IS NULL OR uses_so_far < max_uses)
        ORDER BY discount_value DESC
        LIMIT 1
        """,
        (now,),
    ).fetchone()
    return dict(row) if row else None


def get_educational_content(conn: Any, product_tag: str | None = None, limit: int = 3) -> list[dict[str, Any]]:
    """Return educational blog articles, optionally filtered by product."""
    if product_tag:
        rows = conn.execute(
            """
            SELECT * FROM shopify_content
            WHERE content_type = 'blog_article'
              AND (product_tags LIKE ? OR product_tags LIKE '%"all"%')
            ORDER BY synced_at DESC
            LIMIT ?
            """,
            (f'%"{product_tag}"%', limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM shopify_content WHERE content_type = 'blog_article' ORDER BY synced_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def build_product_url(product: dict[str, Any], customer_id: str, campaign: str) -> str:
    """Build a UTM-tracked Shopify product URL using REAL product data."""
    base = "https://pureleven.com"
    # Use shopify handle if available, else fallback to title slug
    title_slug = (product.get("title") or "products").lower().replace(" ", "-")
    path = f"/products/{title_slug}"
    utm = (
        f"utm_source=whatsapp"
        f"&utm_medium=meta"
        f"&utm_campaign={campaign}"
        f"&utm_customer={customer_id}"
        f"&utm_product={title_slug}"
    )
    return f"{base}{path}?{utm}"


# ─────────────────────────────────────────────────────────────────────────────
# Full sync (call this on a schedule)
# ─────────────────────────────────────────────────────────────────────────────

def run_full_sync() -> dict[str, int]:
    """Run all sync tasks in order. Safe to call repeatedly."""
    results = {
        "products": sync_products(),
        "offers": sync_offers(),
        "blogs": sync_blogs(),
    }
    logger.info("Full Shopify sync complete: %s", results)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def _strip_html(html: str) -> str:
    """Remove HTML tags from a string."""
    import re
    return re.sub(r"<[^>]+>", " ", html).strip()


def _extract_product_tags(text: str) -> list[str]:
    """Detect which PureLeven products are mentioned in text."""
    text_lower = text.lower()
    keywords = ["cardamom", "pepper", "cinnamon", "cloves", "nutmeg", "turmeric", "ginger", "spice"]
    found = [k for k in keywords if k in text_lower]
    return found or ["spice"]


def _extract_next_page_url(link_header: str) -> str | None:
    """Parse Shopify's Link header to find the next page URL."""
    import re
    match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
    return match.group(1) if match else None
