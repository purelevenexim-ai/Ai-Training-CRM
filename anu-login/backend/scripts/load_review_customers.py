#!/usr/bin/env python3
"""
scripts/load_review_customers.py

Parse Shopify orders_export CSV → insert delivered/paid customers into
journey_customers for the review journey.

Usage:
    python scripts/load_review_customers.py /path/to/orders_export.csv [--dry-run]

Rules:
    - Only rows with Fulfillment Status = "fulfilled"
    - Financial Status = "paid" (skip voided / pending)
    - One row per order# (de-duplicate multi-item rows)
    - Phone normalisation → +91XXXXXXXXXX (Indian numbers)
    - Customer status: cold (< ₹500), warm (₹500-₹1000), hot (> ₹1000)
    - Marks delivery_status = "delivered" and uses Fulfilled at as delivered_at
    - Sets journey_stage = "delivered" so orchestrator picks them up
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ── allow running from repo root ─────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault(
    "ANU_LOGIN_DATABASE_PATH",
    str(BACKEND_DIR / "anu_login.sqlite3"),
)

from app.storage import get_db_connection  # noqa: E402  (after sys.path fix)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger("load_review_customers")

SHOP_DOMAIN = "rwxtic-gz.myshopify.com"
GOOGLE_REVIEW_URL = "https://g.page/r/CUrWIcPGInbFEBE/review"  # ← real GMB URL

# Product name → handle/sku mapping for cross-sell engine
PRODUCT_HANDLE_MAP: dict[str, str] = {
    "Kerala Cardamom": "kerala-cardamom-100g",
    "Kerala Black Pepper": "kerala-black-pepper-200gm",
    "Aromatic True Cinnamon": "aromatic-true-cinnamon-ceylon-100g",
    "Premium Cassia Cinnamon": "premium-cassia-cinnamon-200g",
    "Kerala Adimali Clove": "kerala-adimali-clove-100gm",
    "Kerala White Pepper": "kerala-white-pepper-100gm",
    "Cardamom": "kerala-cardamom-100g",
    "Black Pepper": "kerala-black-pepper-200gm",
    "Clove": "kerala-adimali-clove-100gm",
    "Cinnamon": "aromatic-true-cinnamon-ceylon-100g",
}


def _normalise_phone(raw: str) -> str | None:
    """Return E.164 Indian number string (e.g. '919876543210') or None."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return "91" + digits
    if len(digits) == 12 and digits.startswith("91"):
        return digits
    if len(digits) == 13 and digits.startswith("091"):
        return digits[1:]
    if len(digits) > 10:
        # Keep the last 10 local digits and convert to 91-prefixed format.
        local = digits[-10:]
        if len(local) == 10:
            return "91" + local
        return None
    return None


def _parse_date(raw: str) -> str | None:
    """Convert Shopify export date string → ISO-8601 UTC string."""
    if not raw or raw.strip() == "":
        return None
    raw = raw.strip()
    for fmt in [
        "%Y-%m-%d %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
    ]:
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except ValueError:
            continue
    return None


def _in_date_window(iso_ts: str | None, start_date: str, end_date: str) -> bool:
    """Check if timestamp date is within inclusive [start_date, end_date] window."""
    if not iso_ts:
        return False
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        date_str = dt.date().isoformat()
        return start_date <= date_str <= end_date
    except Exception:
        return False


def _customer_status(order_total: float) -> str:
    if order_total >= 1000:
        return "hot"
    if order_total >= 500:
        return "warm"
    return "cold"


def _best_product_name(items: list[str]) -> str:
    """Pick the most prominent product from a multi-item order."""
    # Prefer non-combo items, sort by name length (shorter = more specific)
    for item in items:
        if "Cardamom" in item:
            return item
        if "Pepper" in item:
            return item
        if "Clove" in item:
            return item
        if "Cinnamon" in item:
            return item
    return items[0] if items else "Pureleven Spices"


def _product_handle(product_name: str) -> str:
    for key, handle in PRODUCT_HANDLE_MAP.items():
        if key.lower() in product_name.lower():
            return handle
    return "pureleven-spices"


def load_csv(
    csv_path: Path,
    dry_run: bool = False,
    start_date: str = "2026-04-01",
    end_date: str = "2026-05-31",
    all_dates: bool = False,
) -> None:
    orders: dict[str, dict] = {}  # order# → aggregated order row

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            order_name = row.get("Name", "").strip()
            if not order_name or not order_name.startswith("#"):
                continue

            fulfillment = row.get("Fulfillment Status", "").strip().lower()
            financial = row.get("Financial Status", "").strip().lower()

            # skip unfulfilled, voided, cancelled
            if fulfillment not in ("fulfilled", "partial"):
                continue
            if financial in ("voided", "refunded", ""):
                continue

            if order_name not in orders:
                # First row for this order — capture master fields
                raw_phone = (
                    row.get("Billing Phone", "")
                    or row.get("Shipping Phone", "")
                    or row.get("Phone", "")
                    or ""
                )
                phone = _normalise_phone(raw_phone)

                email = row.get("Email", "").strip() or None
                name = (
                    row.get("Billing Name", "")
                    or row.get("Shipping Name", "")
                    or "Customer"
                ).strip()

                order_total = float(row.get("Total", "0") or "0")
                fulfilled_at = _parse_date(row.get("Fulfilled at", ""))
                created_at = _parse_date(row.get("Created at", ""))
                shopify_order_id = order_name

                orders[order_name] = {
                    "shopify_order_id": shopify_order_id,
                    "name": name,
                    "phone": phone,
                    "email": email,
                    "order_total": order_total,
                    "fulfilled_at": fulfilled_at,
                    "created_at": created_at,
                    "line_items": [],
                }

            # Accumulate line items (even continuation rows)
            line_name = row.get("Lineitem name", "").strip()
            if line_name:
                orders[order_name]["line_items"].append(line_name)

    # ── Write to DB ───────────────────────────────────────────────────────────
    eligible = [o for o in orders.values() if o["phone"] and o["fulfilled_at"]]
    if not all_dates:
        eligible = [o for o in eligible if _in_date_window(o["fulfilled_at"], start_date, end_date)]
    skipped = len(orders) - len(eligible)

    logger.info(
        "CSV parsed: %d orders total, %d eligible, %d skipped (filters applied)",
        len(orders), len(eligible), skipped,
    )
    if not all_dates:
        logger.info("Date filter: fulfilled_at between %s and %s", start_date, end_date)
    else:
        logger.info("Date filter: disabled (--all-dates)")

    if dry_run:
        for o in eligible:
            product_name = _best_product_name(o["line_items"]) if o["line_items"] else "Pureleven Spices"
            status = _customer_status(o["order_total"])
            logger.info("  DRY-RUN: %s  %s  %s  %s  %s  %s",
                        o["shopify_order_id"], o["name"], o["phone"],
                        o["fulfilled_at"], product_name, status)
        logger.info("Dry-run complete. No DB writes.")
        return

    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    updated = 0
    skipped_db = 0

    with get_db_connection() as conn:
        for o in eligible:
            product_name = _best_product_name(o["line_items"]) if o["line_items"] else "Pureleven Spices"
            product_handle = _product_handle(product_name)
            cstatus = _customer_status(o["order_total"])
            order_paise = int(o["order_total"] * 100)

            # Check for existing record
            existing = conn.execute(
                "SELECT id, customer_status FROM journey_customers WHERE shop_domain = ? AND shopify_order_id = ?",
                (SHOP_DOMAIN, o["shopify_order_id"]),
            ).fetchone()

            if existing:
                # Update delivery info + product name if needed
                conn.execute(
                    """
                    UPDATE journey_customers SET
                        delivery_status = 'delivered',
                        delivered_at = COALESCE(delivered_at, ?),
                        purchased_product_name = COALESCE(purchased_product_name, ?),
                        purchased_product_handle = COALESCE(purchased_product_handle, ?),
                        customer_status = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (o["fulfilled_at"], product_name, product_handle,
                     cstatus, now, existing[0]),
                )
                updated += 1
                logger.info("  UPDATED: %s  %s", o["shopify_order_id"], o["name"])
                continue

            cid = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO journey_customers (
                    id, shop_domain, phone, name, email,
                    shopify_order_id,
                    delivery_status, delivered_at,
                    order_value_paise,
                    journey_stage, journey_started_at,
                    whatsapp_subscription_status,
                    customer_segment, customer_status,
                    purchased_product_name, purchased_product_handle,
                    is_responsive,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?,
                          ?,
                          'delivered', ?,
                          ?,
                          'delivered', ?,
                          'subscribed',
                          'new', ?,
                          ?, ?,
                          0,
                          ?, ?)
                """,
                (
                    cid, SHOP_DOMAIN,
                    o["phone"], o["name"], o["email"],
                    o["shopify_order_id"],
                    o["fulfilled_at"],
                    order_paise,
                    o["fulfilled_at"] or now,
                    cstatus,
                    product_name, product_handle,
                    now, now,
                ),
            )
            inserted += 1
            logger.info("  INSERTED: %s  %s  %s  %s  [%s]",
                        o["shopify_order_id"], o["name"], o["phone"],
                        product_name, cstatus)

    logger.info("\n=== DONE ===")
    logger.info("  Inserted : %d", inserted)
    logger.info("  Updated  : %d", updated)
    logger.info("  Skipped  : %d", skipped_db)
    logger.info("  Total    : %d", inserted + updated)


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Shopify order CSV into journey_customers")
    parser.add_argument("csv_path", type=Path, help="Path to orders_export_*.csv")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be inserted, don't write to DB")
    parser.add_argument("--start-date", default="2026-04-01", help="Inclusive start date YYYY-MM-DD (default: 2026-04-01)")
    parser.add_argument("--end-date", default="2026-05-31", help="Inclusive end date YYYY-MM-DD (default: 2026-05-31)")
    parser.add_argument("--all-dates", action="store_true", help="Disable default date-range filter")
    args = parser.parse_args()

    if not args.csv_path.exists():
        logger.error("File not found: %s", args.csv_path)
        sys.exit(1)

    load_csv(
        args.csv_path,
        dry_run=args.dry_run,
        start_date=args.start_date,
        end_date=args.end_date,
        all_dates=args.all_dates,
    )


if __name__ == "__main__":
    main()
