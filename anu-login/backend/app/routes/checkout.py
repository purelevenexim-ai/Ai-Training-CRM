"""
Basil Commerce OS — Phase 2
routes/checkout.py

Address Intelligence endpoints:
  GET  /api/checkout/pincode?code=560001  — pincode lookup (COD, ETA, city/state)
  POST /api/checkout/session              — save address + checkout session
  GET  /api/checkout/config               — per-shop checkout config
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.storage import get_db_connection

router = APIRouter()


# ─── Pincode data ─────────────────────────────────────────────────────────────
# Simplified: real implementation should query a shipping partner API or a
# pre-loaded pincode lookup table.  This fallback table covers metro areas.

_PINCODE_DB: dict[str, dict] = {
    # Karnataka
    "560001": {"city": "Bengaluru", "state": "Karnataka", "cod": True,  "eta": "2-3 days", "ship": 0},
    "560002": {"city": "Bengaluru", "state": "Karnataka", "cod": True,  "eta": "2-3 days", "ship": 0},
    "560003": {"city": "Bengaluru", "state": "Karnataka", "cod": True,  "eta": "2-3 days", "ship": 0},
    "560004": {"city": "Bengaluru", "state": "Karnataka", "cod": True,  "eta": "2-3 days", "ship": 0},
    "560005": {"city": "Bengaluru", "state": "Karnataka", "cod": True,  "eta": "2-3 days", "ship": 0},
    # Tamil Nadu
    "600001": {"city": "Chennai",   "state": "Tamil Nadu", "cod": True,  "eta": "2-3 days", "ship": 0},
    "600002": {"city": "Chennai",   "state": "Tamil Nadu", "cod": True,  "eta": "2-3 days", "ship": 0},
    # Maharashtra
    "400001": {"city": "Mumbai",    "state": "Maharashtra", "cod": True, "eta": "1-2 days", "ship": 0},
    "400051": {"city": "Mumbai",    "state": "Maharashtra", "cod": True, "eta": "1-2 days", "ship": 0},
    "411001": {"city": "Pune",      "state": "Maharashtra", "cod": True, "eta": "2-3 days", "ship": 0},
    # Delhi
    "110001": {"city": "New Delhi", "state": "Delhi",       "cod": True, "eta": "1-2 days", "ship": 0},
    "110011": {"city": "New Delhi", "state": "Delhi",       "cod": True, "eta": "1-2 days", "ship": 0},
    # Telangana
    "500001": {"city": "Hyderabad", "state": "Telangana",   "cod": True, "eta": "2-3 days", "ship": 0},
    "500081": {"city": "Hyderabad", "state": "Telangana",   "cod": True, "eta": "2-3 days", "ship": 0},
    # West Bengal
    "700001": {"city": "Kolkata",   "state": "West Bengal", "cod": True, "eta": "3-4 days", "ship": 0},
    # Gujarat
    "380001": {"city": "Ahmedabad", "state": "Gujarat",     "cod": True, "eta": "2-3 days", "ship": 0},
    # Kerala
    "682001": {"city": "Kochi",     "state": "Kerala",      "cod": True, "eta": "3-4 days", "ship": 0},
}

_DEFAULT_PIN = {"cod": True, "eta": "4-7 days", "ship": 4900}  # 49 INR shipping paise


def _lookup_pincode(pin: str) -> dict:
    if pin in _PINCODE_DB:
        return _PINCODE_DB[pin]
    # State-level fallback by prefix
    prefix_map = {
        "11": {"state": "Delhi",         "cod": True,  "eta": "2-3 days", "ship": 0},
        "40": {"state": "Maharashtra",   "cod": True,  "eta": "2-3 days", "ship": 0},
        "41": {"state": "Maharashtra",   "cod": True,  "eta": "3-4 days", "ship": 0},
        "56": {"state": "Karnataka",     "cod": True,  "eta": "3-4 days", "ship": 0},
        "60": {"state": "Tamil Nadu",    "cod": True,  "eta": "3-5 days", "ship": 0},
        "50": {"state": "Telangana",     "cod": True,  "eta": "3-4 days", "ship": 0},
        "68": {"state": "Kerala",        "cod": True,  "eta": "4-6 days", "ship": 4900},
        "69": {"state": "Kerala",        "cod": True,  "eta": "5-7 days", "ship": 4900},
        "70": {"state": "West Bengal",   "cod": True,  "eta": "3-5 days", "ship": 0},
        "38": {"state": "Gujarat",       "cod": True,  "eta": "3-4 days", "ship": 0},
        "39": {"state": "Gujarat",       "cod": True,  "eta": "3-5 days", "ship": 0},
    }
    for prefix, data in prefix_map.items():
        if pin.startswith(prefix):
            return {**data, "city": ""}
    return {**_DEFAULT_PIN, "city": "", "state": ""}


# ─── Models ───────────────────────────────────────────────────────────────────

class AddressPayload(BaseModel):
    name:     str = ""
    phone:    str = ""
    address1: str = ""
    address2: str = ""
    city:     str = ""
    province: str = ""
    zip:      str = ""
    country:  str = "India"


class CheckoutSessionCreate(BaseModel):
    shop_domain:    str = Field(min_length=1, max_length=200)
    cart_token:     str = ""
    session_id:     str = ""
    customer_id:    str = ""
    pincode:        str = ""
    cod_enabled:    bool = False
    eta_label:      str = ""
    shipping_paise: int = 0
    address:        AddressPayload = AddressPayload()


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/checkout/pincode", summary="Pincode serviceable + COD + ETA check")
def check_pincode(code: str = Query(min_length=6, max_length=6)) -> dict[str, Any]:
    if not code.isdigit():
        raise HTTPException(status_code=422, detail="Pincode must be numeric")
    info = _lookup_pincode(code)
    return {
        "pincode":            code,
        "serviceable":        True,
        "city":               info.get("city", ""),
        "state":              info.get("state", ""),
        "cod_available":      info.get("cod", True),
        "eta_label":          info.get("eta", "4-7 days"),
        "shipping_cost_paise": info.get("ship", 4900),
    }


@router.post("/checkout/session", summary="Save checkout session", status_code=status.HTTP_201_CREATED)
def create_checkout_session(payload: CheckoutSessionCreate) -> dict[str, Any]:
    import json as _json
    session_id = str(uuid.uuid4())
    now        = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO checkout_sessions
              (id, shop_domain, cart_token, external_session_id, customer_id,
               pincode, cod_enabled, eta_label, shipping_paise, address_json, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'initiated', ?, ?)
            """,
            (
                session_id,
                payload.shop_domain,
                payload.cart_token,
                payload.session_id,
                payload.customer_id,
                payload.pincode,
                int(payload.cod_enabled),
                payload.eta_label,
                payload.shipping_paise,
                _json.dumps(payload.address.model_dump()),
                now,
                now,
            ),
        )

    return {"session_id": session_id, "status": "initiated"}


@router.get("/checkout/config", summary="Per-shop checkout configuration")
def get_checkout_config(shop_domain: str) -> dict[str, Any]:
    """Returns the Basil checkout feature flags and thresholds for a shop."""
    with get_db_connection() as conn:
        flags = conn.execute(
            "SELECT flag_name, enabled, rollout_percentage FROM feature_flags WHERE shop_domain = ?",
            (shop_domain,),
        ).fetchall()

    flag_map = {row["flag_name"]: bool(row["enabled"]) for row in flags}

    return {
        "shop_domain": shop_domain,
        "features": {
            "checkout_prep":    flag_map.get("checkout_prep",    True),
            "cod_check":        flag_map.get("cod_check",        True),
            "eta_display":      flag_map.get("eta_display",      True),
            "reward_engine":    flag_map.get("reward_engine",    True),
            "smart_cart":       flag_map.get("smart_cart",       True),
            "event_gateway":    flag_map.get("event_gateway",    True),
        },
    }
