from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "anu-login" / "backend"

for path in (str(ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.ai.pricing_formatter import PricingFormatter
from app.ai.whatsapp_delivery_service import send_whatsapp_reply_with_fallback


def test_order_delivery_cta_uses_new_human_copy() -> None:
    english = PricingFormatter.build_order_delivery_cta("english")
    manglish = PricingFormatter.build_order_delivery_cta("manglish")
    malayalam = PricingFormatter.build_order_delivery_cta("malayalam")
    hindi = PricingFormatter.build_order_delivery_cta("hindi")

    assert "To place the order, please send" in english
    assert "Combo orders and orders above ₹600 have free delivery." in english
    assert "please pay ₹40" in english
    assert "₹120" not in english
    assert "only ₹60" not in english
    assert "₹60 from the customer" not in english

    assert "Order cheyyan please ayakkane" in manglish
    assert "₹40 delivery charge mathi" in manglish
    assert "Order ചെയ്യാൻ ദയവായി അയക്കൂ" in malayalam
    assert "₹40 delivery charge" in malayalam
    assert "Order place karne ke liye please bhejiye" in hindi
    assert "sirf ₹40" in hindi


def test_product_price_payload_includes_all_catalog_images(monkeypatch) -> None:
    original_get_entry = PricingFormatter.get_product_catalog_entry

    def fake_entry(product_key: str):
        entry = original_get_entry(product_key)
        if product_key != "black_pepper" or not entry:
            return entry
        return {
            **entry,
            "images": [
                {"url": "/api/product-media/pepper/one.jpg"},
                {"url": "/api/product-media/pepper/two.jpg"},
                {"url": "/api/product-media/pepper/three.jpg"},
            ],
            "primary_image_url": "/api/product-media/pepper/one.jpg",
        }

    monkeypatch.setattr(PricingFormatter, "get_product_catalog_entry", staticmethod(fake_entry))

    payload = PricingFormatter.build_product_journey_reply_payload(
        "black_pepper",
        style="english",
        scenario="price",
    )

    assert payload is not None
    assert payload["image_urls"] == [
        "/api/product-media/pepper/one.jpg",
        "/api/product-media/pepper/two.jpg",
        "/api/product-media/pepper/three.jpg",
    ]


def test_text_with_images_sends_text_first_then_all_images(monkeypatch) -> None:
    events: list[str] = []

    def fake_text_message(phone_number: str, message_text: str, conversation_id: str = ""):
        events.append(f"text:{message_text}")
        return {"success": True, "message_id": "text-1"}

    def fake_image_message(phone: str, image_url: str, caption: str = ""):
        events.append(f"image:{image_url}")
        return {"messages": [{"id": image_url.rsplit("/", 1)[-1]}]}

    monkeypatch.setattr(
        "app.ai.whatsapp_delivery_service.WabisAPIClient.send_text_message",
        fake_text_message,
    )
    monkeypatch.setattr(
        "app.ai.whatsapp_delivery_service.send_meta_image_message",
        fake_image_message,
    )

    result = send_whatsapp_reply_with_fallback(
        phone_number="919999000111",
        message_text="250g - ₹300\n500g - ₹540",
        conversation_id="media-order-test",
        reply_result={"intent": "price", "message_understanding": {"normalized_message": "black pepper price"}},
        media_urls=["https://example.com/one.jpg", "https://example.com/two.jpg", "https://example.com/three.jpg"],
    )

    assert result["success"] is True
    assert events == [
        "text:250g - ₹300 500g - ₹540",
        "image:https://example.com/one.jpg",
        "image:https://example.com/two.jpg",
        "image:https://example.com/three.jpg",
    ]
