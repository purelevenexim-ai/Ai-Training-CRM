from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "anu-login" / "backend"

for path in (str(ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.ai.pricing_formatter import PricingFormatter
from app.ai.wabis_reply_generator import WabisReplyGenerator


def test_core_product_reply_is_canonical_cardamom_table() -> None:
    reply = PricingFormatter.build_core_product_reply("cardamom")

    assert reply is not None
    assert "*CARDAMOM*" in reply
    assert "8.5mm A+ grade cardamom" in reply
    assert "100g" in reply
    assert "₹460" in reply
    assert "₹3350" in reply
    assert "Size     | Price" in reply
    assert "Size     | Price    | Delivery" not in reply
    assert "Which size would you like" not in reply
    assert "I’ll share the price details below." not in reply


def test_plain_cardamom_message_returns_neat_product_reply() -> None:
    result = WabisReplyGenerator.generate_reply(
        incoming_message="cardamom",
        customer_phone="919999999999",
        customer_name="Anu",
    )

    assert result["intent"] == "availability"
    assert result["should_escalate"] is False
    assert result["suggested_action"] == "send_reply"
    assert "*CARDAMOM*" in result["reply_text"]
    assert "₹460" in result["reply_text"]
    assert "₹3350" in result["reply_text"]
    assert "Size     | Price    | Delivery" not in result["reply_text"]
    assert "Which size" not in result["reply_text"]
    assert result["extra_messages"]
    assert "Name, full address, phone number, and pincode" in result["extra_messages"][0]
    assert "Yes, we have cardamom in stock." not in result["reply_text"]
    assert "I’ll share the price details below." not in result["reply_text"]


def test_elakka_maps_to_same_cardamom_catalog() -> None:
    elakka_result = WabisReplyGenerator.generate_reply(
        incoming_message="elakka",
        customer_phone="919999999997",
        customer_name="Anu",
    )

    assert elakka_result["intent"] == "availability"
    assert "*CARDAMOM*" in elakka_result["reply_text"]
    assert "₹460" in elakka_result["reply_text"]


def test_complaint_message_with_product_routes_to_complaint_flow() -> None:
    result = WabisReplyGenerator.generate_reply(
        incoming_message="I have not received my cardamom order yet",
        customer_phone="919999999996",
        customer_name="Anu",
    )

    assert result["intent"] == "complaint"
    assert result["should_escalate"] is True
    assert result["suggested_action"] == "escalate"
    assert "support" in result["reply_text"].lower()
    assert "*CARDAMOM*" not in result["reply_text"]


def test_multi_product_message_returns_catalog_reply() -> None:
    result = WabisReplyGenerator.generate_reply(
        incoming_message="cardamom and pepper rate pls",
        customer_phone="919999999995",
        customer_name="Anu",
    )

    assert result["intent"] == "details"
    assert "*CARDAMOM*" in result["reply_text"]
    assert "*BLACK PEPPER*" in result["reply_text"]


def test_wholesale_message_returns_b2b_reply() -> None:
    result = WabisReplyGenerator.generate_reply(
        incoming_message="wholesale price for cardamom",
        customer_phone="919999999994",
        customer_name="Anu",
    )

    assert result["intent"] == "wholesale"
    assert result["should_escalate"] is True
    assert "product name" in result["reply_text"].lower()
    assert "approx quantity" in result["reply_text"].lower()


def test_manglish_prompt_keeps_manglish_tone() -> None:
    result = WabisReplyGenerator.generate_reply(
        incoming_message="kurumulak undo ?",
        customer_phone="919999999993",
        customer_name="Anu",
    )

    assert result["intent"] == "availability"
    reply_lower = result["reply_text"].lower()
    assert "undu" in reply_lower
    assert "*black pepper*" in reply_lower
    assert "yes, we have" not in reply_lower
    assert "details ayakk" not in reply_lower
    assert result["extra_messages"]
    assert "peru, address, phone number, pincode" in result["extra_messages"][0].lower()


def test_typoed_clove_aliases_map_to_clove_reply() -> None:
    grampu_result = WabisReplyGenerator.generate_reply(
        incoming_message="grampu undo?",
        customer_phone="919999999992",
        customer_name="Anu",
    )
    gampoo_result = WabisReplyGenerator.generate_reply(
        incoming_message="Gampoo undo?",
        customer_phone="919999999991",
        customer_name="Anu",
    )

    assert grampu_result["intent"] == "availability"
    assert gampoo_result["intent"] == "availability"
    assert "*CLOVE*" in grampu_result["reply_text"]
    assert "*CLOVE*" in gampoo_result["reply_text"]
    assert "how much are you looking for" not in grampu_result["reply_text"].lower()
    assert "yes, we have clove in stock" not in grampu_result["reply_text"].lower()
    assert "Size     | Price    | Delivery" not in grampu_result["reply_text"]


def test_product_negation_stops_sales_pitch() -> None:
    result = WabisReplyGenerator.generate_reply(
        incoming_message="kurumulak venda",
        customer_phone="919999999990",
        customer_name="Anu",
    )

    assert result["intent"] == "product_negation"
    assert "വേറെ എന്തെങ്കിലും" in result["reply_text"]
    assert "*BLACK PEPPER*" not in result["reply_text"]


def test_delivery_question_gets_delivery_specific_reply() -> None:
    result = WabisReplyGenerator.generate_reply(
        incoming_message="patta delivery ethra divasam?",
        customer_phone="919999999989",
        customer_name="Anu",
    )

    assert result["intent"] == "delivery_time"
    assert result["message_understanding"]["scenario"] == "delivery_time"
    reply_lower = result["reply_text"].lower()
    assert "delivery kittum" in reply_lower
    assert "pincode" in reply_lower
    assert "size     | price" not in reply_lower


def test_generic_delivery_question_stays_product_neutral() -> None:
    result = WabisReplyGenerator.generate_reply(
        incoming_message="ethra days delivery",
        customer_phone="919999999987",
        customer_name="Anu",
    )

    assert result["intent"] == "delivery_time"
    reply_lower = result["reply_text"].lower()
    assert "4-7 days" in reply_lower
    assert "pincode" in reply_lower
    assert "cardamom" not in reply_lower
    assert "black pepper" not in reply_lower


def test_value_objection_gets_quality_response() -> None:
    result = WabisReplyGenerator.generate_reply(
        incoming_message="patta rate kooduthal aanu",
        customer_phone="919999999988",
        customer_name="Anu",
    )

    assert result["intent"] == "price_objection"
    assert result["message_understanding"]["scenario"] == "price_objection"
    reply_lower = result["reply_text"].lower()
    assert "ceylon cinnamon" in reply_lower
    assert "sweeter aroma" in reply_lower or "cleaner profile" in reply_lower


def test_unmatched_non_product_message_uses_clean_fallback() -> None:
    result = WabisReplyGenerator.generate_reply(
        incoming_message="Need help with my order",
        customer_phone="919999999986",
        customer_name="Anu",
    )

    assert result["intent"] == "fallback"
    assert "products, delivery, payment, or orders" in result["reply_text"]


def test_media_marker_gets_media_aware_reply() -> None:
    result = WabisReplyGenerator.generate_reply(
        incoming_message="[[media:video]]",
        customer_phone="919999999985",
        customer_name="Anu",
    )

    assert result["intent"] == "media_received"
    assert "video" in result["reply_text"].lower()
    assert "one line" in result["reply_text"].lower()
