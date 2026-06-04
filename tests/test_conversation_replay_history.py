from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "anu-login" / "backend"

for path in (str(ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.ai.audit_logger import get_conversation_history


def _build_legacy_timeline_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row

    conn.execute(
        """
        CREATE TABLE ai_incoming_messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            message_type TEXT NOT NULL DEFAULT 'text',
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE ai_outgoing_replies (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            reply_text TEXT NOT NULL,
            intent TEXT NOT NULL,
            escalated INTEGER NOT NULL DEFAULT 0,
            send_status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE conversation_state (
            phone TEXT PRIMARY KEY,
            owner TEXT NOT NULL DEFAULT 'ai',
            owner_reason TEXT,
            flow_id TEXT,
            flow_step TEXT,
            expected_responses TEXT,
            started_at TEXT,
            expires_at TEXT,
            last_activity TEXT,
            context_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE product_journey_followups (
            id TEXT PRIMARY KEY,
            phone TEXT NOT NULL,
            conversation_phone TEXT NOT NULL,
            product_key TEXT,
            scenario TEXT NOT NULL,
            reply_style TEXT NOT NULL DEFAULT 'english',
            customer_reference TEXT,
            followup_stage TEXT NOT NULL,
            scheduled_at TEXT NOT NULL,
            sent INTEGER NOT NULL DEFAULT 0,
            sent_at TEXT,
            reply_text TEXT,
            send_status TEXT NOT NULL DEFAULT 'queued',
            send_error TEXT,
            context_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        INSERT INTO ai_incoming_messages
        (id, conversation_id, customer_phone, message_type, body, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "incoming-1",
            "conversation-1",
            "918547574028",
            "text",
            "black pepper undo",
            "2026-06-03T10:00:00+00:00",
        ),
    )
    conn.execute(
        """
        INSERT INTO ai_outgoing_replies
        (id, conversation_id, customer_phone, reply_text, intent, escalated, send_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "outgoing-1",
            "conversation-1",
            "918547574028",
            "Yes, black pepper undallo stock.",
            "product_pepper",
            0,
            "sent",
            "2026-06-03T10:01:00+00:00",
        ),
    )
    conn.execute(
        """
        INSERT INTO product_journey_followups
        (id, phone, conversation_phone, product_key, scenario, reply_style,
         customer_reference, followup_stage, scheduled_at, sent, sent_at,
         reply_text, send_status, send_error, context_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "followup-1",
            "918547574028",
            "918547574028",
            "pepper",
            "availability",
            "manglish",
            "black pepper",
            "gentle_reminder",
            "2026-06-03T10:05:00+00:00",
            1,
            "2026-06-03T10:05:30+00:00",
            "Just check cheyyan aanu. Venengil best option suggest cheythu order help cheyyam.",
            "sent",
            None,
            "{}",
            "2026-06-03T10:05:00+00:00",
            "2026-06-03T10:05:30+00:00",
        ),
    )
    conn.execute(
        """
        INSERT INTO conversation_state
        (phone, owner, owner_reason, flow_id, flow_step, expected_responses,
         started_at, expires_at, last_activity, context_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "918547574028",
            "ai",
            "product_availability",
            "product_journey",
            "awaiting_customer_reply",
            "yes,no,price,delivery,order,wholesale",
            "2026-06-03T10:00:00+00:00",
            None,
            "2026-06-03T10:05:30+00:00",
            '{"product_key": "pepper", "reply_style": "manglish", "customer_reference": "black pepper"}',
            "2026-06-03T10:00:00+00:00",
            "2026-06-03T10:05:30+00:00",
        ),
    )
    conn.commit()
    return conn


def test_get_conversation_history_merges_legacy_tables(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "legacy_timeline.sqlite3"
    conn = _build_legacy_timeline_db(db_path)

    monkeypatch.setattr(
        "app.storage.get_db_connection",
        lambda: conn,
    )

    events = get_conversation_history("+91 8547574028", limit=10)

    assert [event["source"] for event in events] == ["customer", "ai", "ai", "system"]
    assert events[0]["message"] == "black pepper undo"
    assert "black pepper undallo stock" in (events[1]["message"] or "").lower()
    assert events[2]["route_decision"] == "sent"
    assert events[3]["message"].startswith("state owner=ai flow=product_journey")
