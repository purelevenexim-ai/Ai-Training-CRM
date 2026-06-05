from __future__ import annotations

import os
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "anu-login" / "backend"

for path in (str(ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

tmp = tempfile.NamedTemporaryFile(prefix="pureleven_wabis_outbound_", suffix=".sqlite3", delete=False)
tmp.close()
os.environ["ANU_LOGIN_DATABASE_PATH"] = tmp.name

from app.ai.conversation_state_manager import get_conversation_state, reset_conversation_state, set_conversation_state
from app.runtime_db import ensure_runtime_tables, get_db_connection
from app.services.ai_reply_queue_service import enqueue_ai_reply_job
from app.services.wabis_outbound_event_service import ingest_wabis_outbound_event
from app.storage import init_database


def _reset(phone: str) -> None:
    init_database()
    ensure_runtime_tables()
    reset_conversation_state(phone)
    with get_db_connection() as connection:
        for table, column in (
            ("ai_incoming_messages", "customer_phone"),
            ("ai_reply_jobs", "customer_phone"),
            ("conversation_audit_log", "phone"),
            ("conversation_state", "phone"),
            ("product_journey_followups", "phone"),
            ("wabis_outbound_messages", "customer_phone"),
            ("wabis_message_status_events", "customer_phone"),
            ("wabis_human_locks", "customer_phone"),
        ):
            try:
                connection.execute(f"DELETE FROM {table} WHERE {column} = ?", (phone,))
            except Exception:
                pass
        try:
            connection.execute("DELETE FROM wabis_webhook_deliveries")
        except Exception:
            pass
        connection.commit()


def _insert_incoming_and_queue(phone: str, source_message: str = "black pepper") -> str:
    source_message_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO ai_incoming_messages
            (id, conversation_id, customer_phone, message_type, body, created_at)
            VALUES (?, 'wabis-outbound-test', ?, 'text', ?, ?)
            """,
            (source_message_id, phone, source_message, now),
        )
        connection.commit()
    queued = enqueue_ai_reply_job(
        conversation_id="wabis-outbound-test",
        customer_phone=phone,
        customer_name="Test Customer",
        source_message_id=source_message_id,
        incoming_message=source_message,
    )
    return queued["job_id"]


def test_admin_reply_event_locks_human_and_cancels_ai_jobs() -> None:
    phone = "919888777001"
    _reset(phone)
    job_id = _insert_incoming_and_queue(phone)

    result = ingest_wabis_outbound_event(
        payload={
            "event": "live_chat.admin_reply.sent",
            "event_id": "evt-admin-lock-1",
            "message_id": "wamid.admin.1",
            "phone": phone,
            "conversation_id": "conv-admin-lock-1",
            "message": "Sure, I will check and reply.",
            "actor_type": "admin",
            "agent_id": "agent-1",
        },
        headers={"x-wabis-test": "1"},
        auth_verified=True,
    )

    assert result["normalized"]["event_type"] == "conversation.admin_reply.sent"
    assert result["projection"]["lock_applied"] is True
    with get_db_connection() as connection:
        job = connection.execute("SELECT status, skipped_reason FROM ai_reply_jobs WHERE id = ?", (job_id,)).fetchone()
        audit = connection.execute(
            """
            SELECT source, direction, route_decision
            FROM conversation_audit_log
            WHERE phone = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (phone,),
        ).fetchone()
    state = get_conversation_state(phone)
    assert job["status"] == "cancelled"
    assert job["skipped_reason"] == "cancelled_by_human_outbound_event"
    assert state["owner"] == "human"
    assert state["flow_id"] == "human_review"
    assert audit["source"] == "human"
    assert audit["direction"] == "outbound"
    assert audit["route_decision"] == "conversation.admin_reply.sent"


def test_status_only_callback_does_not_lock_human() -> None:
    phone = "919888777002"
    _reset(phone)

    result = ingest_wabis_outbound_event(
        payload={
            "statuses": [
                {
                    "id": "wamid.status.1",
                    "status": "delivered",
                    "recipient_id": phone,
                }
            ],
            "event_id": "evt-status-1",
        },
        headers={},
        auth_verified=True,
    )

    assert result["normalized"]["event_type"] == "conversation.message.delivered"
    assert result["projection"]["lock_applied"] is False
    state = get_conversation_state(phone)
    assert state is None or state["owner"] == "ai"
    with get_db_connection() as connection:
        status = connection.execute(
            "SELECT delivery_status FROM wabis_message_status_events WHERE customer_phone = ? LIMIT 1",
            (phone,),
        ).fetchone()
    assert status["delivery_status"] == "delivered"


def test_bot_resumed_event_releases_human_lock() -> None:
    phone = "919888777003"
    _reset(phone)
    set_conversation_state(
        phone,
        owner="human",
        owner_reason="conversation.bot_paused",
        flow_id="human_review",
        flow_step="paused",
        context={
            "human_lock_until": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        },
    )

    result = ingest_wabis_outbound_event(
        payload={
            "event": "bot_resumed",
            "event_id": "evt-resume-1",
            "phone": phone,
            "conversation_id": "conv-resume-1",
        },
        headers={},
        auth_verified=True,
    )

    assert result["normalized"]["event_type"] == "conversation.bot_resumed"
    assert result["projection"]["released"] is True
    assert get_conversation_state(phone)["owner"] == "ai"
