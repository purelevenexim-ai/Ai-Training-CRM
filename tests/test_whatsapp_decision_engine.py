from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "anu-login" / "backend"

for path in (str(ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

tmp = tempfile.NamedTemporaryFile(prefix="pureleven_decision_", suffix=".sqlite3", delete=False)
tmp.close()
os.environ["ANU_LOGIN_DATABASE_PATH"] = tmp.name

from app.ai.customer_state_engine import get_customer_state, update_customer_state
from app.ai.intent_router import route_message
from app.ai.whatsapp_response_pipeline import generate_dynamic_reply
from app.runtime_db import ensure_runtime_tables, get_db_connection
from app.storage import init_database


def _reset() -> None:
    init_database()
    ensure_runtime_tables()
    with get_db_connection() as connection:
        for table in ("conversation_state", "message_processing_locks"):
            connection.execute(f"DELETE FROM {table}")
        connection.commit()


def test_payment_confirmation_is_not_unclear_fallback() -> None:
    _reset()
    reply = generate_dynamic_reply(
        incoming_message="Paid using Google Pay! ✅",
        customer_name="Customer",
        context={},
    )
    assert reply["intent"] == "payment"
    assert "Payment message" in reply["reply_text"] or "Payment message" in reply["reply_text"]
    assert "clear" not in reply["reply_text"].lower()


def test_plant_inquiry_gets_supported_category_reply() -> None:
    _reset()
    reply = generate_dynamic_reply(
        incoming_message="Plants available??",
        customer_name="Customer",
        context={},
    )
    assert reply["intent"] == "plant_inquiry"
    assert "Plants" in reply["reply_text"] or "plants" in reply["reply_text"]
    assert "clear" not in reply["reply_text"].lower()


def test_acknowledgement_does_not_reuse_old_active_product() -> None:
    _reset()
    phone = "919999111222"
    update_customer_state(
        phone,
        inbound_message="black pepper",
        product_key="black_pepper",
        latest_intent="price",
        journey_stage="product_interest",
    )
    reply = generate_dynamic_reply(
        incoming_message="Ok",
        customer_name="Customer",
        context=get_customer_state(phone),
    )
    assert reply["intent"] == "acknowledgement"
    assert "250g" not in reply["reply_text"]
    assert reply["reply_text"].strip().startswith("Okay") or reply["reply_text"].strip().startswith("ശരി")


def test_button_reply_maps_state_but_keeps_wabis_owner() -> None:
    _reset()
    phone = "919999111223"
    decision = route_message(
        phone,
        "#Button Reply#Buy Now",
        message_meta={"structured_button_click": True, "postback_id": "Buy Now"},
    )
    assert decision["route"] == "wabis"
    state = get_customer_state(phone)
    assert state["latest_intent"] == "order_request"
    assert state["journey_stage"] == "order_capture"


if __name__ == "__main__":
    test_payment_confirmation_is_not_unclear_fallback()
    test_plant_inquiry_gets_supported_category_reply()
    test_acknowledgement_does_not_reuse_old_active_product()
    test_button_reply_maps_state_but_keeps_wabis_owner()
