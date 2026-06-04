"""
Shopify Customer Import Service

Fetches customers from Shopify and manages promotional campaigns.
Supports direct API access and CSV file uploads.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests

from app.config import settings
from app.storage import get_db_connection

logger = logging.getLogger(__name__)


class ShopifyCustomerImporter:
    """Imports customers from Shopify store."""

    SHOPIFY_API_VERSION = "2024-01"

    def __init__(self):
        raw_store = settings.default_shop_domain or "rwxtic-gz.myshopify.com"
        parsed = urlparse(raw_store if raw_store.startswith(("http://", "https://")) else f"https://{raw_store}")
        self.store = parsed.netloc or parsed.path or "rwxtic-gz.myshopify.com"
        self.access_token = settings.shopify_access_token
        self.base_url = f"https://{self.store}/admin/api/{self.SHOPIFY_API_VERSION}"

    @staticmethod
    def _split_tags(raw_tags: Any) -> list[str]:
        if not raw_tags:
            return []
        if isinstance(raw_tags, list):
            return [str(tag).strip() for tag in raw_tags if str(tag).strip()]
        return [tag.strip() for tag in str(raw_tags).split(",") if tag.strip()]

    def _normalise_customer(self, customer: dict[str, Any]) -> dict[str, Any]:
        default_address = customer.get("default_address") or {}
        first_name = (customer.get("first_name") or "").strip()
        last_name = (customer.get("last_name") or "").strip()
        return {
            "id": customer.get("id"),
            "email": (customer.get("email") or "").strip(),
            "first_name": first_name,
            "last_name": last_name,
            "name": " ".join(part for part in [first_name, last_name] if part).strip(),
            "phone": (customer.get("phone") or default_address.get("phone") or "").strip(),
            "tags": self._split_tags(customer.get("tags")),
            "created_at": customer.get("created_at"),
            "updated_at": customer.get("updated_at"),
        }

    def _normalise_order_contact(self, order: dict[str, Any]) -> dict[str, Any] | None:
        customer = order.get("customer") or {}
        billing = order.get("billing_address") or {}
        shipping = order.get("shipping_address") or {}
        first_name = (
            customer.get("first_name")
            or shipping.get("first_name")
            or billing.get("first_name")
            or ""
        ).strip()
        last_name = (
            customer.get("last_name")
            or shipping.get("last_name")
            or billing.get("last_name")
            or ""
        ).strip()
        email = (
            order.get("email")
            or order.get("contact_email")
            or customer.get("email")
            or ""
        ).strip()
        phone = (
            order.get("phone")
            or shipping.get("phone")
            or billing.get("phone")
            or customer.get("phone")
            or ""
        ).strip()
        if not email and not phone:
            return None
        return {
            "id": order.get("id"),
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "name": " ".join(part for part in [first_name, last_name] if part).strip(),
            "phone": phone,
            "tags": ["shopify", "shopify_order"],
            "created_at": order.get("created_at"),
            "updated_at": order.get("updated_at") or order.get("processed_at"),
        }

    def get_all_customers(self, limit: int = 250, status: str = "any") -> list[dict[str, Any]]:
        """
        Fetch all customers from Shopify store.

        Args:
            limit: Number of customers per page (max 250)
            status: "any", "enabled", "disabled"

        Returns:
            List of customer dicts with id, email, first_name, last_name, phone, tags
        """
        if not self.access_token:
            raise RuntimeError("SHOPIFY_ACCESS_TOKEN or SHOPIFY_ADMIN_API_TOKEN is not configured")

        customers: list[dict[str, Any]] = []
        url = f"{self.base_url}/customers.json"
        headers = {"X-Shopify-Access-Token": self.access_token}
        params: dict[str, Any] | None = {
            "limit": min(limit, 250),
            "status": status,
            "fields": "id,email,first_name,last_name,phone,default_address,tags,created_at,updated_at",
        }

        while url:
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
            except Exception as exc:
                logger.error("Failed to fetch Shopify customers page from %s: %s", url, exc)
                if customers:
                    break
                raise

            data = response.json()
            page_rows = data.get("customers", [])
            customers.extend(self._normalise_customer(customer) for customer in page_rows if isinstance(customer, dict))

            next_link = response.links.get("next", {}).get("url")
            url = next_link or ""
            params = None

        logger.info("Fetched %s customers from Shopify store %s", len(customers), self.store)
        return customers

    def get_order_contacts(self, days: int = 365, limit_pages: int = 20) -> list[dict[str, Any]]:
        """Fetch distinct contact rows from Shopify orders for phone fallback."""
        if not self.access_token:
            raise RuntimeError("SHOPIFY_ACCESS_TOKEN or SHOPIFY_ADMIN_API_TOKEN is not configured")

        from datetime import timedelta

        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        headers = {"X-Shopify-Access-Token": self.access_token}
        params = {
            "limit": 250,
            "status": "any",
            "created_at_min": since,
            "fields": "id,email,phone,contact_email,customer,billing_address,shipping_address,created_at,updated_at,processed_at",
        }
        url = f"{self.base_url}/orders.json"
        contacts_by_key: dict[str, dict[str, Any]] = {}

        for _ in range(limit_pages):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
            except Exception as exc:
                logger.error("Failed to fetch Shopify order contacts page from %s: %s", url, exc)
                break

            data = response.json()
            for order in data.get("orders", []):
                if not isinstance(order, dict):
                    continue
                contact = self._normalise_order_contact(order)
                if not contact:
                    continue
                key = (contact.get("email") or contact.get("phone") or f"order:{contact.get('id')}").strip().lower()
                if not key:
                    continue
                existing = contacts_by_key.get(key)
                if existing is None:
                    contacts_by_key[key] = contact
                    continue
                if not existing.get("phone") and contact.get("phone"):
                    existing["phone"] = contact["phone"]
                if not existing.get("name") and contact.get("name"):
                    existing["name"] = contact["name"]
                merged_tags = list(dict.fromkeys([*(existing.get("tags") or []), *(contact.get("tags") or [])]))
                existing["tags"] = merged_tags

            next_link = response.links.get("next", {}).get("url")
            if not next_link:
                break
            url = next_link
            params = None

        contacts = list(contacts_by_key.values())
        logger.info("Fetched %s order contacts from Shopify store %s", len(contacts), self.store)
        return contacts

    def get_customer_orders(self, customer_id: str) -> list[dict[str, Any]]:
        """Get all orders for a specific customer."""
        try:
            url = f"{self.base_url}/customers/{customer_id}/orders.json"
            headers = {"X-Shopify-Access-Token": self.access_token}
            params = {"limit": 250, "status": "any"}

            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            return response.json().get("orders", [])

        except Exception as e:
            logger.error(f"Failed to fetch orders for customer {customer_id}: {e}")
            return []

    @staticmethod
    def import_customers_to_db(customers: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Import fetched customers into promotional_customers table.

        Returns:
            {
              "imported": int,
              "updated": int,
              "skipped": int,
              "total": int,
            }
        """
        imported = 0
        updated = 0
        skipped = 0

        with get_db_connection() as conn:
            for customer in customers:
                if not customer.get("email"):
                    skipped += 1
                    continue

                customer_id = f"shopify_{customer.get('id', '')}"
                email = customer.get("email", "").strip().lower()
                first_name = customer.get("first_name", "")
                last_name = customer.get("last_name", "")
                phone = customer.get("phone", "")
                tags = ",".join(customer.get("tags", []))

                # Check if customer exists
                existing = conn.execute(
                    "SELECT id FROM promotional_customers WHERE email = ?",
                    (email,),
                ).fetchone()

                if existing:
                    # Update existing
                    conn.execute(
                        """
                        UPDATE promotional_customers
                        SET customer_id = ?, first_name = ?, last_name = ?, 
                            phone = ?, tags = ?, updated_at = ?
                        WHERE email = ?
                        """,
                        (
                            customer_id,
                            first_name,
                            last_name,
                            phone,
                            tags,
                            datetime.now(timezone.utc).isoformat(),
                            email,
                        ),
                    )
                    updated += 1
                else:
                    # Insert new
                    conn.execute(
                        """
                        INSERT INTO promotional_customers
                        (customer_id, email, first_name, last_name, phone, tags,
                         segment, status, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            customer_id,
                            email,
                            first_name,
                            last_name,
                            phone,
                            tags,
                            "general",
                            "active",
                            datetime.now(timezone.utc).isoformat(),
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                    imported += 1

            conn.commit()

        return {
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "total": len(customers),
        }

    @staticmethod
    def mark_customers_as_purchased() -> int:
        """Mark all customers with orders as 'purchased' segment."""
        count = 0

        with get_db_connection() as conn:
            # Get all customers who have entries in campaign_sends
            cursor = conn.execute(
                """
                UPDATE promotional_customers
                SET segment = 'purchased'
                WHERE email IN (
                    SELECT DISTINCT email FROM promotional_customers
                    WHERE tags LIKE '%purchased%' OR tags LIKE '%customer%'
                )
                """
            )
            count = cursor.rowcount
            conn.commit()

        logger.info(f"Marked {count} customers as 'purchased' segment")
        return count

    @staticmethod
    def get_import_stats() -> dict[str, Any]:
        """Get stats on imported customers."""
        with get_db_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM promotional_customers"
            ).fetchone()["cnt"]

            by_segment = {}
            for row in conn.execute(
                "SELECT segment, COUNT(*) as cnt FROM promotional_customers GROUP BY segment"
            ).fetchall():
                by_segment[row["segment"]] = row["cnt"]

            by_status = {}
            for row in conn.execute(
                "SELECT status, COUNT(*) as cnt FROM promotional_customers GROUP BY status"
            ).fetchall():
                by_status[row["status"]] = row["cnt"]

        return {
            "total_customers": total,
            "by_segment": by_segment,
            "by_status": by_status,
        }
