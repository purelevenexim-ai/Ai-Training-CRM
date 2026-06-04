"""Deterministic customer identity graph helpers for Pureleven CRM.

The resolver is intentionally conservative. It auto-links only exact deterministic
identifiers and leaves probabilistic matching to a future manual review queue.
"""

from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime
from typing import Any

from crm_models import Customer, CustomerIdentity, IdentityMergeHistory


IDENTITY_TYPES = (
    "email",
    "phone",
    "shopify_customer_id",
    "gclid",
    "gbraid",
    "wbraid",
    "fbclid",
    "fbp",
    "fbc",
    "ga_client_id",
    "ga_session_id",
    "session_id",
)


class IdentityResolver:
    def __init__(self, db: Any, write_enabled: bool | None = None) -> None:
        self.db = db
        if write_enabled is None:
            write_enabled = (os.getenv("IDENTITY_GRAPH_WRITE_ENABLED", "false") or "false").lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
        self.write_enabled = write_enabled

    @staticmethod
    def normalize(identity_type: str, value: Any) -> str | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        if identity_type == "email":
            lowered = raw.lower()
            return lowered if "@" in lowered else None
        if identity_type == "phone":
            digits = re.sub(r"\D", "", raw)
            if len(digits) < 7:
                return None
            if len(digits) == 10:
                digits = f"91{digits}"
            return digits
        return raw

    @staticmethod
    def identity_hash(identity_type: str, normalized_value: str) -> str:
        return hashlib.sha256(f"{identity_type}:{normalized_value}".encode("utf-8")).hexdigest()

    def collect_identities(self, **kwargs: Any) -> list[dict[str, str]]:
        identities: list[dict[str, str]] = []
        for identity_type in IDENTITY_TYPES:
            normalized = self.normalize(identity_type, kwargs.get(identity_type))
            if not normalized:
                continue
            identities.append({
                "identity_type": identity_type,
                "identity_value": normalized,
                "identity_hash": self.identity_hash(identity_type, normalized),
            })
        return identities

    def find_customer_id(self, identities: list[dict[str, str]]) -> str | None:
        if not identities:
            return None
        hashes = [item["identity_hash"] for item in identities]
        row = (
            self.db.query(CustomerIdentity)
            .filter(CustomerIdentity.identity_hash.in_(hashes))
            .order_by(CustomerIdentity.confidence_score.desc(), CustomerIdentity.last_seen_at.desc())
            .first()
        )
        if row:
            return row.canonical_customer_id

        by_type = {item["identity_type"]: item["identity_value"] for item in identities}
        if by_type.get("shopify_customer_id"):
            customer = self.db.query(Customer).filter(Customer.shopify_customer_id == by_type["shopify_customer_id"]).first()
            if customer:
                return customer.id
        if by_type.get("email"):
            customer = self.db.query(Customer).filter(Customer.email == by_type["email"]).first()
            if customer:
                return customer.id
        if by_type.get("phone"):
            customer = self.db.query(Customer).filter(Customer.phone == by_type["phone"]).first()
            if customer:
                return customer.id
        return None

    def attach_identities(self,
                          customer_id: str,
                          identities: list[dict[str, str]],
                          source: str = "identity_resolver") -> int:
        if not self.write_enabled or not customer_id or not identities:
            return 0
        attached = 0
        now = datetime.utcnow()
        for item in identities:
            existing = (
                self.db.query(CustomerIdentity)
                .filter(
                    CustomerIdentity.identity_type == item["identity_type"],
                    CustomerIdentity.identity_hash == item["identity_hash"],
                )
                .first()
            )
            if existing:
                existing.last_seen_at = now
                existing.source = existing.source or source
                if existing.canonical_customer_id != customer_id:
                    self.db.add(IdentityMergeHistory(
                        from_customer_id=existing.canonical_customer_id,
                        to_customer_id=customer_id,
                        merge_method="deterministic_identity_link",
                        confidence_score=1.0,
                        matched_fields=[item["identity_type"]],
                        reason=f"Identity {item['identity_type']} re-linked to canonical customer",
                        status="suggested",
                        created_by="identity_resolver",
                    ))
                continue

            self.db.add(CustomerIdentity(
                canonical_customer_id=customer_id,
                identity_type=item["identity_type"],
                identity_value=item["identity_value"],
                identity_hash=item["identity_hash"],
                confidence_score=1.0,
                source=source,
                first_seen_at=now,
                last_seen_at=now,
            ))
            attached += 1
        return attached

    def resolve(self, source: str = "identity_resolver", **kwargs: Any) -> dict[str, Any]:
        identities = self.collect_identities(**kwargs)
        customer_id = self.find_customer_id(identities)
        attached = 0
        if customer_id:
            attached = self.attach_identities(customer_id, identities, source=source)
        return {
            "customer_id": customer_id,
            "identity_count": len(identities),
            "attached_count": attached,
            "write_enabled": self.write_enabled,
            "identities": identities,
        }
