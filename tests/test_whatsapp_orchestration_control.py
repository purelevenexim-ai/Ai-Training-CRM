from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "anu-login" / "backend"

for path in (str(ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.ai.conversation_state_manager import get_conversation_state, reset_conversation_state, set_conversation_state
from app.ai.intent_router import route_message
from app.ai.wabis_reply_generator import WabisReplyGenerator
from app.routes import wave02_wabis_routes
from app.runtime_db import get_db_connection
from app.services.owner_dashboard_service import get_ai_control_settings


def _control(**overrides):
    payload = get_ai_control_settings()
    payload.update(
        {
            "server_orchestration_enabled": True,
            "flow_break_detection_enabled": True,
            "structured_button_passthrough_enabled": True,
            "wabis_fallback_when_disabled": True,
            "wabis_priority_minutes": 5,
            "ai_running": True,
        }
    )
    payload.update(overrides)
    return payload


def test_ai_control_defaults_include_orchestration_guardrails() -> None:
    settings = get_ai_control_settings()

    assert "server_orchestration_enabled" in settings
    assert "flow_break_detection_enabled" in settings
    assert "structured_button_passthrough_enabled" in settings
    assert "wabis_fallback_when_disabled" in settings
    assert "wabis_priority_minutes" in settings


def test_server_control_off_stands_down_before_routing(monkeypatch) -> None:
    called = {"route": False}

    def fail_if_routed(*args, **kwargs):
        called["route"] = True
        raise AssertionError("route_message should not run when server orchestration is off")

    monkeypatch.setattr(
        wave02_wabis_routes,
        "get_ai_control_settings",
        lambda: _control(server_orchestration_enabled=False),
    )
    monkeypatch.setattr(wave02_wabis_routes, "route_message", fail_if_routed)

    result = wave02_wabis_routes._generate_and_send_reply(
        conversation_id="test-orchestrator-off",
        customer_phone="919999888001",
        customer_name="Test",
        incoming_message="cardamom",
    )

    assert result["status"] == "skipped"
    assert result["reason"] == "server_orchestration_disabled"
    assert result["route"] == "wabis_fallback"
    assert called["route"] is False


def test_wabis_button_click_stays_with_wabis_flow() -> None:
    phone = "919999888002"
    set_conversation_state(
        phone,
        owner="wabis",
        owner_reason="greeting_flow",
        flow_id="greeting",
        expected_responses="english,malayalam,1,2",
    )

    decision = route_message(
        phone,
        "English",
        {
            "message_type": "postback",
            "postback_id": "english",
            "structured_button_click": True,
            "structured_button_passthrough_enabled": True,
            "flow_break_detection_enabled": True,
        },
    )

    assert decision["route"] == "wabis"
    assert "Structured Wabis" in decision["reason"] or "automation active" in decision["reason"]


def test_product_text_stays_with_active_wabis_flow_during_grace_window() -> None:
    phone = "919999888003"
    set_conversation_state(
        phone,
        owner="wabis",
        owner_reason="greeting_flow",
        flow_id="greeting",
        expected_responses="english,malayalam,1,2",
    )

    decision = route_message(
        phone,
        "cardamom",
        {
            "message_type": "text",
            "structured_button_click": False,
            "structured_button_passthrough_enabled": True,
            "flow_break_detection_enabled": True,
        },
    )

    state_after = get_conversation_state(phone)

    assert decision["route"] == "wabis"
    assert "priority" in decision["reason"].lower() or "active" in decision["reason"].lower()
    assert state_after is not None
    assert state_after["owner"] == "wabis"


def test_product_text_handoffs_after_wabis_grace_window() -> None:
    phone = "919999888013"
    set_conversation_state(
        phone,
        owner="wabis",
        owner_reason="greeting_flow",
        flow_id="greeting",
        expected_responses="english,malayalam,1,2",
    )

    stale_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE conversation_state SET updated_at = ?, last_activity = ? WHERE phone = ?",
            (stale_time, stale_time, phone),
        )
        conn.commit()

    decision = route_message(
        phone,
        "cardamom",
        {
            "message_type": "text",
            "structured_button_click": False,
            "structured_button_passthrough_enabled": True,
            "flow_break_detection_enabled": True,
        },
    )

    state_after = get_conversation_state(phone)

    assert decision["route"] == "catalog"
    assert decision["intent"] == "availability"
    assert decision["resolved_product_key"] == "cardamom"
    assert state_after is None or state_after["owner"] == "ai"


def test_product_text_does_not_break_wabis_flow_when_guardrail_disabled() -> None:
    phone = "919999888004"
    set_conversation_state(
        phone,
        owner="wabis",
        owner_reason="greeting_flow",
        flow_id="greeting",
        expected_responses="english,malayalam,1,2",
    )

    decision = route_message(
        phone,
        "cardamom",
        {
            "message_type": "text",
            "structured_button_click": False,
            "structured_button_passthrough_enabled": True,
            "flow_break_detection_enabled": False,
        },
    )

    assert decision["route"] == "wabis"
    assert "active" in decision["reason"].lower()


def test_product_journey_followup_routes_to_catalog_not_wabis() -> None:
    phone = "919999888005"
    set_conversation_state(
        phone,
        owner="wabis",
        owner_reason="product_availability",
        flow_id="product_journey",
        flow_step="awaiting_customer_reply",
        expected_responses="yes,no,price,delivery,order,wholesale",
        context={
            "product_key": "black_pepper",
            "reply_style": "manglish",
            "customer_reference": "black pepper",
        },
    )

    decision = route_message(
        phone,
        "delivery undo?",
        {
            "message_type": "text",
            "structured_button_click": False,
            "structured_button_passthrough_enabled": True,
            "flow_break_detection_enabled": True,
        },
    )

    assert decision["route"] == "catalog"
    assert decision["intent"] == "delivery_time"
    assert decision["product_context"]["product_key"] == "black_pepper"


def test_mixed_greeting_with_product_bypasses_welcome_even_after_old_product_context() -> None:
    phone = "919999888006"
    set_conversation_state(
        phone,
        owner="ai",
        owner_reason="product_availability",
        flow_id="product_journey",
        flow_step="awaiting_customer_reply",
        expected_responses="yes,no,price,delivery,order,wholesale",
        context={
            "product_key": "cardamom",
            "reply_style": "english",
            "customer_reference": "cardamom",
        },
    )

    decision = route_message(
        phone,
        "Hello! Can I get more expa info on cardamom",
        {
            "message_type": "text",
            "structured_button_click": False,
            "structured_button_passthrough_enabled": True,
            "flow_break_detection_enabled": True,
            "wabis_priority_minutes": 5,
        },
    )

    assert decision["route"] == "catalog"
    assert decision["intent"] == "details"
    assert decision["resolved_product_key"] == "cardamom"


def test_plain_text_wabis_button_reply_overrides_stale_product_journey() -> None:
    phone = "919999888007"
    set_conversation_state(
        phone,
        owner="ai",
        owner_reason="product_availability",
        flow_id="product_journey",
        flow_step="awaiting_customer_reply",
        expected_responses="yes,no,price,delivery,order,wholesale",
        context={
            "product_key": "cardamom",
            "reply_style": "english",
            "customer_reference": "cardamom",
        },
    )

    decision = route_message(
        phone,
        "#Button Reply#🇮🇳 മലയാളം",
        {
            "message_type": "text",
            "reply_message_id": "reply-msg-1",
            "structured_button_click": True,
            "structured_button_passthrough_enabled": True,
            "flow_break_detection_enabled": True,
        },
    )

    assert decision["route"] == "wabis"
    assert decision["action_set_owner"]["owner"] == "wabis"
    assert decision["action_set_owner"]["reason"] == "structured_wabis_reply"


def test_contextual_product_journey_delivery_reply() -> None:
    result = WabisReplyGenerator.generate_reply(
        incoming_message="delivery undo?",
        customer_phone="919999888006",
        customer_name="Anu",
        context={
            "product_key": "black_pepper",
            "reply_style": "manglish",
            "customer_reference": "black pepper",
        },
    )

    assert result["intent"] == "delivery_time"
    assert result["message_understanding"]["scenario"] == "delivery_time"
    assert "delivery kittum" in result["reply_text"].lower()
    assert "size     | price" not in result["reply_text"].lower()


def test_contextual_product_journey_order_help_reply() -> None:
    result = WabisReplyGenerator.generate_reply(
        incoming_message="okay engane ayakunath ?",
        customer_phone="919999888007",
        customer_name="Anu",
        context={
            "product_key": "black_pepper",
            "reply_style": "manglish",
            "customer_reference": "black pepper",
        },
    )

    assert result["intent"] == "order_request"
    assert result["message_understanding"]["scenario"] == "order_request"
    assert "name" in result["reply_text"].lower()
    assert "address" in result["reply_text"].lower()
    assert "quantity / size" in result["reply_text"].lower()


def test_customer_deferred_decision_does_not_send_product_fallback() -> None:
    phone = "919999888017"
    set_conversation_state(
        phone,
        owner="ai",
        owner_reason="product_availability",
        flow_id="product_journey",
        flow_step="awaiting_customer_reply",
        expected_responses="yes,no,price,delivery,order,wholesale",
        context={
            "product_key": "cardamom",
            "reply_style": "english",
            "customer_reference": "cardamom",
        },
    )

    result = WabisReplyGenerator.generate_reply(
        incoming_message="I will let you know tomorrow",
        customer_phone=phone,
        customer_name="Customer",
        context={
            "product_key": "cardamom",
            "reply_style": "english",
            "customer_reference": "cardamom",
        },
    )

    reply_lower = result["reply_text"].lower()
    assert result["intent"] == "followup"
    assert "tomorrow" in reply_lower or "later" in reply_lower
    assert "are you referring" not in reply_lower
    assert "just let us know how we can assist" not in reply_lower
    assert "*cardamom*" not in reply_lower
    assert not reply_lower.startswith("cardamom ")


def test_explicit_new_product_overrides_previous_product_context() -> None:
    result = WabisReplyGenerator.generate_reply(
        incoming_message="Patta undo",
        customer_phone="919999888008",
        customer_name="Anu",
        context={
            "product_key": "cardamom",
            "reply_style": "manglish",
            "customer_reference": "cardamom",
        },
    )

    assert result["intent"] == "availability"
    assert "undu" in result["reply_text"].lower()
    assert "*CEYLON CINNAMON*" in result["reply_text"]
    assert "*CARDAMOM*" not in result["reply_text"]


def test_mixed_greeting_with_product_question_is_product_first() -> None:
    phone = "919999999009"
    reset_conversation_state(phone)

    decision = route_message(
        phone,
        "Hello! Can I get more expa info on blackpepper?",
        {
            "message_type": "text",
            "structured_button_click": False,
            "structured_button_passthrough_enabled": True,
            "flow_break_detection_enabled": True,
        },
    )

    assert decision["route"] == "catalog"
    assert decision["intent"] == "details"
    assert decision["resolved_product_key"] == "black_pepper"


def test_short_greeting_still_starts_wabis_flow() -> None:
    phone = "919999999010"
    reset_conversation_state(phone)

    decision = route_message(
        phone,
        "Hello",
        {
            "message_type": "text",
            "structured_button_click": False,
            "structured_button_passthrough_enabled": True,
            "flow_break_detection_enabled": True,
        },
    )

    assert decision["route"] == "wabis"
    assert decision["intent"] == "fallback"


def test_product_text_inside_wabis_flow_captures_latent_handoff() -> None:
    phone = "919999999011"
    set_conversation_state(
        phone,
        owner="wabis",
        owner_reason="greeting_flow",
        flow_id="greeting",
        expected_responses="english,malayalam,1,2",
    )

    decision = route_message(
        phone,
        "cardamom only",
        {
            "message_type": "text",
            "structured_button_click": False,
            "structured_button_passthrough_enabled": True,
            "flow_break_detection_enabled": True,
            "wabis_priority_minutes": 5,
        },
    )

    assert decision["route"] == "wabis"
    assert decision["action_merge_context"]["latent_handoff"]["product_key"] == "cardamom"
    assert decision["action_schedule_latent_handoff"]["detected_intent"] == "availability"
