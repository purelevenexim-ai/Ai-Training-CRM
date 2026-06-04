from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "anu-login" / "backend"

for path in (str(ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.ai.pricing_formatter import PRODUCT_REPLY_LIBRARY, PricingFormatter
from app.ai.wabis_reply_generator import WabisReplyGenerator
from app.services.product_followup_service import _render_followup_payload


def test_product_journey_reply_payload_includes_images() -> None:
    product_key = "pytest_pepper"
    original_entry = PRODUCT_REPLY_LIBRARY.get(product_key)
    PRODUCT_REPLY_LIBRARY[product_key] = {
        "display_name": "Test Pepper",
        "aliases": ["test pepper"],
        "origin": "Idukki",
        "description": "Washed & Cleaned",
        "recommended_pack": "500g",
        "recommendations": {
            "english": "500g is the best value pack for this test product.",
            "manglish": "500g aanu ivide value pack.",
            "malayalam": "500g pack നല്ല value option ആണ്.",
        },
        "reply_cta": "Reply with the size you want and we’ll help you order.",
        "variants": [
            {"size": "250g", "price": 300, "delivery": "₹40"},
            {"size": "500g", "price": 540, "delivery": "Free"},
        ],
        "images": [
            {
                "id": "img-primary",
                "url": "https://cdn.example.com/test-pepper-primary.jpg",
                "caption": "Primary view",
                "is_primary": True,
                "sort_order": 0,
            },
            {
                "id": "img-secondary",
                "url": "https://cdn.example.com/test-pepper-secondary.jpg",
                "caption": "Secondary view",
                "is_primary": False,
                "sort_order": 1,
            },
        ],
    }

    try:
        payload = PricingFormatter.build_product_journey_reply_payload(
            product_key,
            style="manglish",
            scenario="availability",
            customer_reference="Test Pepper",
        )
        assert payload is not None
        assert payload["media_mode"] == "image"
        assert payload["primary_image_url"] == "https://cdn.example.com/test-pepper-primary.jpg"
        assert payload["image_urls"] == [
            "https://cdn.example.com/test-pepper-primary.jpg",
            "https://cdn.example.com/test-pepper-secondary.jpg",
        ]
        assert "Undu" in payload["reply_text"]
        assert "Size     | Price" in payload["reply_text"]
        assert "Size     | Price    | Delivery" not in payload["reply_text"]
        assert payload["extra_messages"]
        assert "Peru, address, phone number, pincode" in payload["extra_messages"][0]
    finally:
        if original_entry is None:
            PRODUCT_REPLY_LIBRARY.pop(product_key, None)
        else:
            PRODUCT_REPLY_LIBRARY[product_key] = original_entry


def test_product_followup_ladder_and_media_modes() -> None:
    plan = WabisReplyGenerator._build_follow_up_plan("availability")
    assert plan == [
        {"after_minutes": 5, "stage": "gentle_reminder"},
        {"after_minutes": 30, "stage": "combo_offer"},
        {"after_minutes": 240, "stage": "image_only"},
        {"after_minutes": 360, "stage": "soft_nudge"},
        {"after_minutes": 1380, "stage": "final_followup"},
    ]

    image_only_payload = _render_followup_payload(
        {
            "reply_style": "manglish",
            "followup_stage": "image_only",
            "product_key": "black_pepper",
            "customer_reference": "Black Pepper",
            "scenario": "availability",
        }
    )
    assert image_only_payload["reply_text"] == ""
    assert image_only_payload["media_mode"] == "image_only"

    combo_payload = _render_followup_payload(
        {
            "reply_style": "english",
            "followup_stage": "combo_offer",
            "scenario": "availability",
        }
    )
    assert "COMBO PACKS" in combo_payload["reply_text"]
    assert combo_payload["media_mode"] == "text"

    delivery_payload = PricingFormatter.build_product_journey_reply_payload(
        "black_pepper",
        style="manglish",
        scenario="delivery",
        customer_reference="Black Pepper",
    )
    assert delivery_payload is not None
    assert "4-7 days" in delivery_payload["reply_text"]
    assert "Size     | Price" not in delivery_payload["reply_text"]
    assert "Njan price thazhe kodukkam." not in delivery_payload["reply_text"]

    payment_payload = _render_followup_payload(
        {
            "reply_style": "manglish",
            "followup_stage": "payment_reminder",
            "scenario": "order_request",
        }
    )
    assert "payment pending" in payment_payload["reply_text"].lower()
    assert payment_payload["media_mode"] == "text"

    confirmation_payload = _render_followup_payload(
        {
            "reply_style": "manglish",
            "followup_stage": "order_confirmation",
            "scenario": "order_confirm",
        }
    )
    assert "order details kitti" in confirmation_payload["reply_text"].lower()
    assert confirmation_payload["media_mode"] == "text"


if __name__ == "__main__":
    test_product_journey_reply_payload_includes_images()
    test_product_followup_ladder_and_media_modes()
    print("product_media_followups_ok")
