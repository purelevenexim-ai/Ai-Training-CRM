from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "anu-login" / "backend"

for path in (str(ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.ai.conversation_state_manager import reset_conversation_state, set_conversation_state
from app.runtime_db import ensure_runtime_tables, get_db_connection
from app.services.ai_reply_queue_service import enqueue_ai_reply_job, run_due_ai_reply_jobs
from app.services.customer_journey_service import stop_customer_journeys_for_customer


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cleanup_phone(phone: str) -> None:
    reset_conversation_state(phone)
    ensure_runtime_tables()
    with get_db_connection() as conn:
        for table, column in (
            ("ai_incoming_messages", "customer_phone"),
            ("ai_outgoing_replies", "customer_phone"),
            ("ai_reply_jobs", "customer_phone"),
            ("ai_conversation_sessions", "customer_phone"),
            ("ai_decision_logs", "customer_phone"),
            ("customer_journey_assignments", "customer_phone"),
            ("customer_journey_logs", "customer_phone"),
            ("product_journey_followups", "phone"),
        ):
            conn.execute(f"DELETE FROM {table} WHERE {column} = ?", (phone,))
        conn.commit()


def test_due_ai_reply_job_finishes_without_holding_sqlite_lock(monkeypatch) -> None:
    phone = "919999777001"
    _cleanup_phone(phone)
    source_message_id = str(uuid.uuid4())
    now = _now()

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO ai_incoming_messages
            (id, conversation_id, customer_phone, message_type, body, created_at)
            VALUES (?, ?, ?, 'text', ?, ?)
            """,
            (source_message_id, "queue-test-1", phone, "kurumulak undo?", now),
        )
        conn.commit()

    queued = enqueue_ai_reply_job(
        conversation_id="queue-test-1",
        customer_phone=phone,
        customer_name="Test",
        source_message_id=source_message_id,
        incoming_message="kurumulak undo?",
    )

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE ai_reply_jobs SET scheduled_at = ? WHERE id = ?",
            ((datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(), queued["job_id"]),
        )
        conn.commit()

    from app.routes import wave02_wabis_routes

    calls: list[dict[str, str]] = []

    def fake_generate_and_send_reply(**kwargs):
        calls.append(kwargs)
        return {"status": "sent", "reply_text": "Kurumulak undu", "intent": "availability"}

    monkeypatch.setattr(wave02_wabis_routes, "_generate_and_send_reply", fake_generate_and_send_reply)

    processed = run_due_ai_reply_jobs(limit=10)

    assert calls and calls[0]["customer_phone"] == phone
    assert any(item["job_id"] == queued["job_id"] and item["status"] == "sent" for item in processed)
    with get_db_connection() as conn:
        job = conn.execute("SELECT status FROM ai_reply_jobs WHERE id = ?", (queued["job_id"],)).fetchone()
        session = conn.execute(
            "SELECT status, context_summary FROM ai_conversation_sessions WHERE customer_phone = ? LIMIT 1",
            (phone,),
        ).fetchone()
    assert job["status"] == "sent"
    assert session["status"] == "active"
    assert "kurumulak undo" in (session["context_summary"] or "")


def test_failed_database_locked_job_reconciles_when_reply_exists() -> None:
    phone = "919999777002"
    _cleanup_phone(phone)
    job_id = str(uuid.uuid4())
    reply_id = str(uuid.uuid4())
    created_at = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    sent_at = (datetime.now(timezone.utc) - timedelta(minutes=9)).isoformat()

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO ai_reply_jobs
            (id, conversation_id, customer_phone, customer_name, source_message_id,
             source_message, message_type, status, delay_type, scheduled_at,
             skipped_reason, result_json, metadata_json, created_at, updated_at)
            VALUES (?, 'queue-test-2', ?, 'Test', ?, 'black pepper', 'text',
                    'failed', 'first_learning_60s', ?, 'database is locked', '{}', '{}', ?, ?)
            """,
            (job_id, phone, str(uuid.uuid4()), created_at, created_at, created_at),
        )
        conn.execute(
            """
            INSERT INTO ai_outgoing_replies
            (id, conversation_id, customer_phone, reply_text, intent, escalated,
             send_status, created_at)
            VALUES (?, 'queue-test-2', ?, 'Already sent', 'availability', 0, 'sent', ?)
            """,
            (reply_id, phone, sent_at),
        )
        conn.commit()

    processed = run_due_ai_reply_jobs(limit=0)

    assert any(item["job_id"] == job_id and item["status"] == "sent" for item in processed)
    with get_db_connection() as conn:
        job = conn.execute(
            "SELECT status, skipped_reason, result_json FROM ai_reply_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
    assert job["status"] == "sent"
    assert job["skipped_reason"] == "reconciled_existing_outgoing_reply"
    assert json.loads(job["result_json"])["reconciled_reply_id"] == reply_id


def test_wabis_owned_ai_job_is_skipped_not_sent(monkeypatch) -> None:
    phone = "919999777003"
    _cleanup_phone(phone)
    source_message_id = str(uuid.uuid4())
    now = _now()
    set_conversation_state(
        phone,
        owner="wabis",
        owner_reason="greeting_flow",
        flow_id="greeting",
        flow_step="awaiting_language_selection",
    )

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO ai_incoming_messages
            (id, conversation_id, customer_phone, message_type, body, created_at)
            VALUES (?, ?, ?, 'text', ?, ?)
            """,
            (source_message_id, "queue-test-3", phone, "cardamom", now),
        )
        conn.commit()

    queued = enqueue_ai_reply_job(
        conversation_id="queue-test-3",
        customer_phone=phone,
        customer_name="Test",
        source_message_id=source_message_id,
        incoming_message="cardamom",
    )
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE ai_reply_jobs SET scheduled_at = ? WHERE id = ?",
            ((datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(), queued["job_id"]),
        )
        conn.commit()

    from app.routes import wave02_wabis_routes

    def fail_generate_and_send_reply(**_kwargs):
        raise AssertionError("AI sender should not run while Wabis owns the flow")

    monkeypatch.setattr(wave02_wabis_routes, "_generate_and_send_reply", fail_generate_and_send_reply)

    processed = run_due_ai_reply_jobs(limit=10)

    assert any(item["job_id"] == queued["job_id"] and item["reason"] == "wabis_owns" for item in processed)
    with get_db_connection() as conn:
        job = conn.execute(
            "SELECT status, skipped_reason FROM ai_reply_jobs WHERE id = ?",
            (queued["job_id"],),
        ).fetchone()
    assert job["status"] == "skipped"
    assert job["skipped_reason"] == "wabis_owns"


def test_customer_reply_stops_active_journey_and_pending_followups() -> None:
    phone = "919999777004"
    _cleanup_phone(phone)
    journey_id = str(uuid.uuid4())
    assignment_id = str(uuid.uuid4())
    followup_id = str(uuid.uuid4())
    now = _now()

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO customer_journeys
            (id, name, description, status, applies_to, selected_products_json,
             trigger_type, stop_on_reply, stop_on_order, stop_on_not_interested,
             stop_on_stop, created_at, updated_at)
            VALUES (?, 'Test Journey', '', 'active', 'all_products', '[]',
                    'product_interest', 1, 1, 1, 1, ?, ?)
            """,
            (journey_id, now, now),
        )
        conn.execute(
            """
            INSERT INTO customer_journey_assignments
            (id, journey_id, customer_phone, product_key, status, started_at, context_json)
            VALUES (?, ?, ?, 'black_pepper', 'active', ?, '{}')
            """,
            (assignment_id, journey_id, phone, now),
        )
        conn.execute(
            """
            INSERT INTO product_journey_followups
            (id, phone, conversation_phone, product_key, scenario, reply_style,
             customer_reference, followup_stage, scheduled_at, message_mode,
             context_json, created_at, updated_at)
            VALUES (?, ?, ?, 'black_pepper', 'availability', 'manglish',
                    'black pepper', 'gentle_reminder', ?, 'text', '{}', ?, ?)
            """,
            (followup_id, phone, phone, (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(), now, now),
        )
        conn.commit()

    stopped = stop_customer_journeys_for_customer(
        customer_phone=phone,
        reason="customer_message:delivery undo?",
        stop_flag="stop_on_reply",
    )

    assert stopped == 1
    with get_db_connection() as conn:
        assignment = conn.execute(
            "SELECT status, stop_reason FROM customer_journey_assignments WHERE id = ?",
            (assignment_id,),
        ).fetchone()
        followup = conn.execute(
            "SELECT send_status, send_error FROM product_journey_followups WHERE id = ?",
            (followup_id,),
        ).fetchone()
        journey_log = conn.execute(
            "SELECT event_type, message_text FROM customer_journey_logs WHERE customer_phone = ? ORDER BY created_at DESC LIMIT 1",
            (phone,),
        ).fetchone()
    assert assignment["status"] == "stopped"
    assert "customer_message" in assignment["stop_reason"]
    assert followup["send_status"] == "cancelled"
    assert journey_log["event_type"] == "journey_stopped"
