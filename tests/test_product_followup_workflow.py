from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "anu-login" / "backend"

for path in (str(ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.ai.conversation_state_manager import get_conversation_state, set_conversation_state
from app.ai.wabis_reply_generator import WabisReplyGenerator
from app.runtime_db import ensure_runtime_tables, get_db_connection
from app.services import product_followup_service as followup_service
from app.services.product_followup_service import queue_latent_handoff_followup, run_due_product_followups


def test_product_followup_is_not_queued_for_simple_price_or_availability_inquiry() -> None:
    ensure_runtime_tables()
    phone = "919999999931"
    WabisReplyGenerator.generate_reply(
        incoming_message="patta undo?",
        customer_phone=phone,
        customer_name="Anu",
    )

    state = get_conversation_state(phone)
    assert state is not None
    assert state["flow_id"] == "product_journey"
    assert state["followups_allowed"] is False

    with get_db_connection() as conn:
        queued_rows = conn.execute(
            """
            SELECT id, followup_stage
            FROM product_journey_followups
            WHERE phone = ? AND send_status = 'queued'
            ORDER BY scheduled_at ASC
            """,
            (phone,),
        ).fetchall()
        assert len(queued_rows) == 0


def test_order_intent_queues_and_processes_followups() -> None:
    ensure_runtime_tables()
    phone = "919999999934"
    started_at = datetime.now(timezone.utc).isoformat()
    WabisReplyGenerator.generate_reply(
        incoming_message="I want to order black pepper",
        customer_phone=phone,
        customer_name="Anu",
    )

    state = get_conversation_state(phone)
    assert state is not None
    assert state["flow_id"] == "product_journey"
    assert state["followups_allowed"] is True

    with get_db_connection() as conn:
        queued_rows = conn.execute(
            """
            SELECT id, followup_stage
            FROM product_journey_followups
            WHERE phone = ? AND created_at >= ? AND send_status = 'queued'
            ORDER BY scheduled_at ASC
            """,
            (phone, started_at),
        ).fetchall()
        assert len(queued_rows) >= 1
        queued_ids = {row["id"] for row in queued_rows}
        due_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        conn.execute(
            "UPDATE product_journey_followups SET scheduled_at = ? WHERE phone = ?",
            (due_time, phone),
        )
        conn.commit()

    original_get_ai_control_settings = followup_service.get_ai_control_settings
    try:
        followup_service.get_ai_control_settings = lambda: {  # type: ignore[assignment]
            "ai_running": True,
            "followup_send_enabled": False,
        }
        processed = run_due_product_followups(limit=200, send_live=False)
    finally:
        followup_service.get_ai_control_settings = original_get_ai_control_settings

    assert any(item["phone"] == phone for item in processed)

    with get_db_connection() as conn:
        processed_rows = conn.execute(
            """
            SELECT id, send_status
            FROM product_journey_followups
            WHERE id IN ({placeholders})
            """.format(placeholders=",".join("?" for _ in queued_ids)),
            tuple(queued_ids),
        ).fetchall()
        assert processed_rows
        assert all(row["send_status"] in {"logged", "sent"} for row in processed_rows)


def test_latent_handoff_waits_for_wabis_then_activates_product_journey() -> None:
    ensure_runtime_tables()
    phone = "919999999932"
    set_conversation_state(
        phone,
        owner="wabis",
        owner_reason="greeting_flow",
        flow_id="greeting",
        flow_step="awaiting_language_selection",
        expected_responses="english,malayalam,1,2",
        context={
            "latent_handoff": {
                "product_key": "black_pepper",
                "detected_intent": "availability",
                "reply_style": "manglish",
                "source_message": "hello black pepper",
            }
        },
    )
    queue_latent_handoff_followup(
        phone=phone,
        product_key="black_pepper",
        detected_intent="availability",
        reply_style="manglish",
        source_message="hello black pepper",
        after_minutes=1,
    )

    stale_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE conversation_state SET updated_at = ?, last_activity = ? WHERE phone = ?",
            (stale_time, stale_time, phone),
        )
        conn.execute(
            "UPDATE product_journey_followups SET scheduled_at = ? WHERE phone = ? AND followup_stage = 'latent_handoff'",
            (stale_time, phone),
        )
        conn.commit()

    original_get_ai_control_settings = followup_service.get_ai_control_settings
    try:
        followup_service.get_ai_control_settings = lambda: {  # type: ignore[assignment]
            "ai_running": True,
            "followup_send_enabled": False,
            "wabis_priority_minutes": 5,
        }
        processed = run_due_product_followups(limit=200, send_live=False)
    finally:
        followup_service.get_ai_control_settings = original_get_ai_control_settings

    assert any(item["phone"] == phone and item["stage"] == "latent_handoff" for item in processed)
    state = get_conversation_state(phone)
    assert state is not None
    assert state["owner"] == "ai"
    assert state["flow_id"] == "product_journey"


def test_followup_suppresses_when_customer_is_no_longer_in_product_journey() -> None:
    ensure_runtime_tables()
    phone = "919999999933"
    set_conversation_state(
        phone,
        owner="human",
        owner_reason="agent_takeover",
    )
    queue_latent_handoff_followup(
        phone=phone,
        product_key="cardamom",
        detected_intent="availability",
        reply_style="english",
        source_message="hello cardamom",
        after_minutes=1,
    )

    stale_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE product_journey_followups SET scheduled_at = ? WHERE phone = ?",
            (stale_time, phone),
        )
        conn.commit()

    original_get_ai_control_settings = followup_service.get_ai_control_settings
    try:
        followup_service.get_ai_control_settings = lambda: {  # type: ignore[assignment]
            "ai_running": True,
            "followup_send_enabled": False,
            "wabis_priority_minutes": 5,
        }
        processed = run_due_product_followups(limit=200, send_live=False)
    finally:
        followup_service.get_ai_control_settings = original_get_ai_control_settings

    assert any(item["phone"] == phone and item["send_status"] == "suppressed" for item in processed)


if __name__ == "__main__":
    test_product_followup_is_not_queued_for_simple_price_or_availability_inquiry()
    test_order_intent_queues_and_processes_followups()
    test_latent_handoff_waits_for_wabis_then_activates_product_journey()
    test_followup_suppresses_when_customer_is_no_longer_in_product_journey()
    print("product_followup_workflow_ok")
