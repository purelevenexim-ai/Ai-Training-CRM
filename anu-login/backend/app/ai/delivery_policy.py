from __future__ import annotations

from typing import Any


FREE_DELIVERY_THRESHOLD_KERALA = 600
KERALA_STANDARD_CHARGE = 40
OUTSIDE_KERALA_STANDARD_CHARGE = 120
OUTSIDE_KERALA_CUSTOMER_CHARGE = 60
OUTSIDE_KERALA_SUBSIDY = 60


def normalize_region(region: str | None) -> str:
    value = (region or "").strip().lower()
    if value in {"kerala", "kl", "ker"}:
        return "kerala"
    if value in {"outside_kerala", "outside kerala", "india", "other"}:
        return "outside_kerala"
    return "kerala"


def delivery_breakdown(amount: int, region: str | None = None) -> dict[str, Any]:
    normalized_region = normalize_region(region)
    if normalized_region == "outside_kerala":
        customer_charge = OUTSIDE_KERALA_CUSTOMER_CHARGE
        return {
            "region": normalized_region,
            "customer_charge": customer_charge,
            "internal_standard_charge": OUTSIDE_KERALA_STANDARD_CHARGE,
            "subsidy": OUTSIDE_KERALA_SUBSIDY,
            "is_free_delivery": False,
            "label": "₹60",
            "explanation": "Outside Kerala, customer charge is ₹60 and PureLeven covers the remaining ₹60.",
        }

    if int(amount or 0) >= FREE_DELIVERY_THRESHOLD_KERALA:
        return {
            "region": "kerala",
            "customer_charge": 0,
            "internal_standard_charge": 0,
            "subsidy": 0,
            "is_free_delivery": True,
            "label": "FREE",
            "explanation": "Kerala orders ₹600 and above get free delivery.",
        }

    return {
        "region": "kerala",
        "customer_charge": KERALA_STANDARD_CHARGE,
        "internal_standard_charge": KERALA_STANDARD_CHARGE,
        "subsidy": 0,
        "is_free_delivery": False,
        "label": f"₹{KERALA_STANDARD_CHARGE}",
        "explanation": "Kerala orders below ₹600 carry ₹40 delivery.",
    }


def delivery_label(amount: int, region: str | None = None) -> str:
    breakdown = delivery_breakdown(amount, region=region)
    return "✅ FREE" if breakdown["is_free_delivery"] else str(breakdown["label"])
