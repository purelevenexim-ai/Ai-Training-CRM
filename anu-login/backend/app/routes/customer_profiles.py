"""
Basil Commerce OS — Phase 4
routes/customer_profiles.py

Customer identity resolution and profile management.
Endpoints:
  GET  /api/customers?shop_domain=x&email=x  — lookup by email
  POST /api/customers/identify               — upsert profile + merge identities
  GET  /api/customers/{customer_id}          — profile detail
  GET  /api/customers/{customer_id}/history  — event history
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field

from app.storage import get_db_connection

router = APIRouter()


# ─── Models ───────────────────────────────────────────────────────────────────

class IdentifyRequest(BaseModel):
    shop_domain:    str = Field(min_length=1, max_length=200)
    session_id:     str = ""
    customer_id:    str = ""
    email:          str = ""
    phone:          str = ""
    name:           str = ""
    source:         str = "web"          # web, android, ios, import
    traits:         dict[str, Any] = {}  # arbitrary KV


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _sha256(v: str) -> str:
    return hashlib.sha256(v.strip().lower().encode()).hexdigest()


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/customer-profiles", summary="Lookup customer by email or session")
def lookup_customer(
    shop_domain:  str,
    email:        str = Query(default=""),
    session_id:   str = Query(default=""),
    customer_id:  str = Query(default=""),
) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        if email:
            email_hash = _sha256(email)
            rows = conn.execute(
                "SELECT * FROM customer_profiles WHERE shop_domain = ? AND email_hash = ? LIMIT 10",
                (shop_domain, email_hash),
            ).fetchall()
        elif customer_id:
            rows = conn.execute(
                "SELECT * FROM customer_profiles WHERE shop_domain = ? AND shopify_customer_id = ? LIMIT 10",
                (shop_domain, customer_id),
            ).fetchall()
        elif session_id:
            # Look up via identity graph
            rows = conn.execute(
                """
                SELECT cp.* FROM customer_profiles cp
                JOIN customer_identity_graph cig ON cig.profile_id = cp.id
                WHERE cp.shop_domain = ? AND cig.identity_type = 'session_id' AND cig.identity_value = ?
                LIMIT 10
                """,
                (shop_domain, session_id),
            ).fetchall()
        else:
            rows = []

    return [dict(r) for r in rows]


@router.post("/customer-profiles/identify", summary="Upsert customer profile + resolve identity")
def identify_customer(payload: IdentifyRequest) -> dict[str, Any]:
    now    = datetime.now(timezone.utc).isoformat()
    email_hash = _sha256(payload.email) if payload.email else None

    with get_db_connection() as conn:
        # Try to find existing profile
        profile = None
        if email_hash:
            profile = conn.execute(
                "SELECT * FROM customer_profiles WHERE shop_domain = ? AND email_hash = ?",
                (payload.shop_domain, email_hash),
            ).fetchone()
        if not profile and payload.customer_id:
            profile = conn.execute(
                "SELECT * FROM customer_profiles WHERE shop_domain = ? AND shopify_customer_id = ?",
                (payload.shop_domain, payload.customer_id),
            ).fetchone()

        if profile:
            profile_id = profile["id"]
            # Merge traits
            existing_traits = json.loads(profile["traits_json"] or "{}")
            merged_traits   = {**existing_traits, **payload.traits}
            conn.execute(
                """
                UPDATE customer_profiles
                SET name = COALESCE(NULLIF(?, ''), name),
                    phone = COALESCE(NULLIF(?, ''), phone),
                    shopify_customer_id = COALESCE(NULLIF(?, ''), shopify_customer_id),
                    traits_json = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (payload.name, payload.phone, payload.customer_id,
                 json.dumps(merged_traits), now, profile_id),
            )
            status_str = "updated"
        else:
            profile_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO customer_profiles
                  (id, shop_domain, shopify_customer_id, email_hash, email_masked, name, phone, source, traits_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    payload.shop_domain,
                    payload.customer_id or None,
                    email_hash,
                    _mask_email(payload.email) if payload.email else None,
                    payload.name or None,
                    payload.phone or None,
                    payload.source,
                    json.dumps(payload.traits),
                    now,
                    now,
                ),
            )
            status_str = "created"

        # Upsert identity nodes
        identities = []
        if payload.email:
            identities.append(("email_hash", email_hash))
        if payload.phone:
            identities.append(("phone_hash", _sha256(payload.phone)))
        if payload.session_id:
            identities.append(("session_id", payload.session_id))
        if payload.customer_id:
            identities.append(("shopify_customer_id", payload.customer_id))

        for id_type, id_val in identities:
            conn.execute(
                """
                INSERT OR IGNORE INTO customer_identity_graph
                  (id, profile_id, shop_domain, identity_type, identity_value, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), profile_id, payload.shop_domain, id_type, id_val, now),
            )

    return {"profile_id": profile_id, "status": status_str}


@router.get("/customer-profiles/{profile_id}", summary="Customer profile detail")
def get_profile(profile_id: str) -> dict[str, Any]:
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM customer_profiles WHERE id = ?",
            (profile_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    r = dict(row)
    r["traits"] = json.loads(r.pop("traits_json", "{}"))
    return r


@router.get("/customer-profiles/{profile_id}/history", summary="Customer event history")
def get_history(
    profile_id:  str,
    limit:       int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    with get_db_connection() as conn:
        # Get customer identifiers to join events
        identities = conn.execute(
            "SELECT identity_type, identity_value FROM customer_identity_graph WHERE profile_id = ?",
            (profile_id,),
        ).fetchall()

        customer_id_row = next(
            (i["identity_value"] for i in identities if i["identity_type"] == "shopify_customer_id"),
            None,
        )
        session_ids = [i["identity_value"] for i in identities if i["identity_type"] == "session_id"]

        events: list[dict] = []
        if customer_id_row:
            rows = conn.execute(
                "SELECT * FROM event_logs WHERE customer_id = ? ORDER BY created_at DESC LIMIT ?",
                (customer_id_row, limit),
            ).fetchall()
            events = [dict(r) for r in rows]
        elif session_ids:
            placeholders = ",".join("?" * len(session_ids))
            rows = conn.execute(
                f"SELECT * FROM event_logs WHERE session_id IN ({placeholders}) ORDER BY created_at DESC LIMIT ?",
                (*session_ids, limit),
            ).fetchall()
            events = [dict(r) for r in rows]

    return {"profile_id": profile_id, "events": events, "count": len(events)}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _mask_email(email: str) -> str:
    """Returns j***@example.com for display / logging — never stores raw email."""
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    masked_local  = local[0] + "***" if len(local) > 1 else "***"
    return f"{masked_local}@{domain}"
