"""
crm_identity.py — Unified Identity Resolution Engine
Resolves or creates a unified_identity record for an incoming event.
Matching priority: email_hash → phone_hash → session_id → gclid → fbclid

Usage:
    from crm_identity import IdentityResolver
    resolver = IdentityResolver(db_session)
    identity_id, is_new = resolver.resolve(event_data)
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Tuple
from uuid import uuid4

logger = logging.getLogger("pureleven.identity")


def _sha256(value: str | None) -> str | None:
    """Return SHA-256 hex digest of a normalised string, or None."""
    if not value:
        return None
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


def _normalise_phone(phone: str | None) -> str | None:
    """Strip spaces/dashes, ensure E.164 prefix for Indian numbers."""
    if not phone:
        return None
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) == 10:
        digits = "91" + digits
    elif digits.startswith("0") and len(digits) == 11:
        digits = "91" + digits[1:]
    return digits or None


class IdentityResolver:
    """Resolve or create a unified_identity row in PostgreSQL."""

    def __init__(self, db) -> None:
        self.db = db

    def resolve(self, event: dict[str, Any]) -> Tuple[str, bool]:
        """
        Returns (identity_id: str, is_new: bool).
        Merges new attribution keys into an existing record if found.
        """
        email_hash  = _sha256(event.get("email"))
        phone_hash  = _sha256(_normalise_phone(event.get("phone")))
        session_id  = event.get("session_id") or None
        gclid       = event.get("gclid") or None
        fbclid      = event.get("fbclid") or None
        utm_source  = event.get("utm_source") or None

        conn = self.db  # SQLAlchemy Session

        # Build WHERE clauses — search by any known key
        conditions = []
        params: dict[str, Any] = {}
        if email_hash:
            conditions.append("email_hash = :email_hash")
            params["email_hash"] = email_hash
        if phone_hash:
            conditions.append("phone_hash = :phone_hash")
            params["phone_hash"] = phone_hash
        if session_id:
            conditions.append("session_id = :session_id")
            params["session_id"] = session_id
        if gclid:
            conditions.append("gclid = :gclid")
            params["gclid"] = gclid
        if fbclid:
            conditions.append("fbclid = :fbclid")
            params["fbclid"] = fbclid

        existing = None
        if conditions:
            from sqlalchemy import text
            where = " OR ".join(conditions)
            row = conn.execute(
                text(f"SELECT identity_id FROM unified_identity WHERE {where} LIMIT 1"),
                params,
            ).fetchone()
            if row:
                existing = str(row[0])

        now = datetime.now(timezone.utc)

        if existing:
            # Enrich: fill in any keys we didn't have before
            from sqlalchemy import text as t
            conn.execute(
                t("""
                UPDATE unified_identity SET
                    email_hash  = COALESCE(email_hash,  :email_hash),
                    phone_hash  = COALESCE(phone_hash,  :phone_hash),
                    session_id  = COALESCE(session_id,  :session_id),
                    gclid       = COALESCE(gclid,       :gclid),
                    fbclid      = COALESCE(fbclid,      :fbclid),
                    source_last = COALESCE(:utm_source, source_last),
                    visit_count = visit_count + 1,
                    last_seen   = :now
                WHERE identity_id = :identity_id
                """),
                {
                    "email_hash": email_hash,
                    "phone_hash": phone_hash,
                    "session_id": session_id,
                    "gclid":      gclid,
                    "fbclid":     fbclid,
                    "utm_source": utm_source,
                    "now":        now,
                    "identity_id": existing,
                },
            )
            conn.commit()
            return existing, False

        # Create new identity
        new_id = str(uuid4())
        from sqlalchemy import text as t
        conn.execute(
            t("""
            INSERT INTO unified_identity
                (identity_id, email_hash, phone_hash, session_id, gclid, fbclid,
                 source_first, source_last, first_seen, last_seen)
            VALUES
                (:identity_id, :email_hash, :phone_hash, :session_id, :gclid, :fbclid,
                 :utm_source, :utm_source, :now, :now)
            ON CONFLICT DO NOTHING
            """),
            {
                "identity_id": new_id,
                "email_hash":  email_hash,
                "phone_hash":  phone_hash,
                "session_id":  session_id,
                "gclid":       gclid,
                "fbclid":      fbclid,
                "utm_source":  utm_source,
                "now":         now,
            },
        )
        conn.commit()
        logger.info("New identity created: %s (source=%s)", new_id, utm_source)
        return new_id, True

    def link_customer(self, identity_id: str, customer_id: str) -> None:
        """Set identity_id FK on a crm_customers row."""
        from sqlalchemy import text
        self.db.execute(
            text("UPDATE crm_customers SET identity_id = :iid WHERE id = :cid AND identity_id IS NULL"),
            {"iid": identity_id, "cid": customer_id},
        )
        self.db.commit()

    def mark_buyer(self, identity_id: str, total_orders: int, total_revenue: float,
                   preferred_pay: str | None = None) -> None:
        """Update buyer fields on the unified identity record."""
        from sqlalchemy import text
        self.db.execute(
            text("""
            UPDATE unified_identity SET
                is_buyer      = true,
                total_orders  = :orders,
                total_revenue = :revenue,
                preferred_pay = COALESCE(:pay, preferred_pay),
                updated_at    = NOW()
            WHERE identity_id = :iid
            """),
            {"orders": total_orders, "revenue": total_revenue,
             "pay": preferred_pay, "iid": identity_id},
        )
        self.db.commit()
