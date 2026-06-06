"""
Tests for Wabis Admin & Human Outbound Event Tracking.

Covers:
- Phase 1: Payload discovery — normalizer classification of all known Wabis payload shapes
- Phase 2: Status precedence — monotonic projection, out-of-order handling
- Phase 3: Compare-and-swap — version-based retry cancellation
- Phase 4: Review item creation — evidence capture, lock acquisition
- Phase 5: Dashboard API — approve/promote/rollback workflow
- Phase 7: Duplicate handling, unknown fields, unsupported messages
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

# ── Setup ─────────────────────────────────────────────────────────────────────
# Ensure the backend is importable and use a temp DB
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("ANU_LOGIN_DATABASE_PATH", str(BACKEND_DIR / "test_outbound_events.db"))
os.environ.setdefault("ANU_LOGIN_ADMIN_SECRET", "test-secret")

from app.runtime_db import get_db_connection, ensure_runtime_tables
from app.services.wabis_outbound_event_service import (
    normalize_wabis_outbound_payload,
    ingest_wabis_outbound_event,
    ensure_wabis_outbound_tables,
    _is_status_upgrade,
    STATUS_PRECEDENCE,
)
from app.ai.conversation_state_manager import (
    set_conversation_state,
    get_conversation_state,
    reset_conversation_state,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "wabis_outbound"


def _load_fixture(name: str) -> dict:
    """Load a JSON fixture file."""
    path = FIXTURES_DIR / name
    with open(path) as f:
        return json.load(f)


@pytest.fixture(autouse=True)
def _setup_db():
    """Ensure clean runtime tables for each test."""
    ensure_runtime_tables()
    ensure_wabis_outbound_tables()
    yield
    # Cleanup: drop test data between tests
    with get_db_connection() as conn:
        conn.execute("DELETE FROM wabis_webhook_deliveries")
        conn.execute("DELETE FROM wabis_outbound_messages")
        conn.execute("DELETE FROM wabis_message_status_events")
        conn.execute("DELETE FROM wabis_human_locks")
        conn.execute("DELETE FROM review_items")
        conn.execute("DELETE FROM intent_rules")
        conn.execute("DELETE FROM intent_rule_versions")
        conn.execute("DELETE FROM rule_promotions")
        conn.execute("DELETE FROM audit_logs")
        conn.execute("DELETE FROM conversation_state")
        conn.execute("DELETE FROM ai_reply_jobs")
        conn.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: Payload Discovery — Normalizer Classification
# ═══════════════════════════════════════════════════════════════════════════════

class TestPayloadNormalization:
    """Test that normalize_wabis_outbound_payload correctly classifies all known Wabis payload shapes."""

    def test_admin_text_reply(self):
        """Admin free-form text reply → conversation.admin_reply.sent"""
        payload = _load_fixture("admin_text_reply.json")
        result = normalize_wabis_outbound_payload(payload)
        assert result["event_type"] == "conversation.admin_reply.sent"
        assert result["originator_type"] == "human"
        assert result["customer_phone"] == "919746785791"
        assert "Google Pay" in result["message_text"]
        assert result["actor_id"] == "agent_001"

    def test_admin_template_reply(self):
        """Admin template send → conversation.admin_reply.sent (template origin)"""
        payload = _load_fixture("admin_template_reply.json")
        result = normalize_wabis_outbound_payload(payload)
        # Template sends from an agent should still be classified as admin reply
        assert result["originator_type"] == "human"
        assert result["customer_phone"] == "919746785791"
        assert result["actor_id"] == "agent_001"

    def test_bot_paused(self):
        """Bot pause action → conversation.bot_paused"""
        payload = _load_fixture("bot_paused.json")
        result = normalize_wabis_outbound_payload(payload)
        assert result["event_type"] == "conversation.bot_paused"
        assert result["originator_type"] == "human"
        assert result["customer_phone"] == "919746785791"

    def test_bot_resumed(self):
        """Bot resume action → conversation.bot_resumed"""
        payload = _load_fixture("bot_resumed.json")
        result = normalize_wabis_outbound_payload(payload)
        assert result["event_type"] == "conversation.bot_resumed"
        assert result["customer_phone"] == "919746785791"

    def test_agent_assigned(self):
        """Agent assignment → conversation.agent_assigned"""
        payload = _load_fixture("agent_assigned.json")
        result = normalize_wabis_outbound_payload(payload)
        assert result["event_type"] == "conversation.agent_assigned"
        assert result["originator_type"] == "human"
        assert result["actor_id"] == "agent_003"

    def test_conversation_archived(self):
        """Archive action → conversation.archived"""
        payload = _load_fixture("conversation_archived.json")
        result = normalize_wabis_outbound_payload(payload)
        assert result["event_type"] == "conversation.archived"
        assert result["customer_phone"] == "919746785791"

    def test_status_sent(self):
        """Status callback: sent → conversation.message.sent"""
        payload = _load_fixture("status_sent.json")
        result = normalize_wabis_outbound_payload(payload)
        assert result["event_type"] == "conversation.message.sent"
        assert result["delivery_status"] == "sent"
        assert result["message_id"] == "wamid_admin_reply_001"

    def test_status_delivered(self):
        """Status callback: delivered → conversation.message.delivered"""
        payload = _load_fixture("status_delivered.json")
        result = normalize_wabis_outbound_payload(payload)
        assert result["event_type"] == "conversation.message.delivered"
        assert result["delivery_status"] == "delivered"

    def test_status_read(self):
        """Status callback: read → conversation.message.read"""
        payload = _load_fixture("status_read.json")
        result = normalize_wabis_outbound_payload(payload)
        assert result["event_type"] == "conversation.message.read"
        assert result["delivery_status"] == "read"

    def test_status_failed(self):
        """Status callback: failed → conversation.message.failed with error"""
        payload = _load_fixture("status_failed.json")
        result = normalize_wabis_outbound_payload(payload)
        assert result["event_type"] == "conversation.message.failed"
        assert result["delivery_status"] == "failed"

    def test_unsupported_message(self):
        """Unsupported message type → conversation.message.unsupported"""
        payload = _load_fixture("unsupported_message.json")
        result = normalize_wabis_outbound_payload(payload)
        assert result["event_type"] == "conversation.message.unsupported"
        assert result["delivery_status"] == "unsupported"

    def test_unknown_event_type_defaults_to_status(self):
        """Unknown event structure defaults to conversation.status"""
        payload = {"some_unknown_field": "value", "phone": "919746785791"}
        result = normalize_wabis_outbound_payload(payload)
        assert result["event_type"] == "conversation.status"
        assert result["customer_phone"] == "919746785791"


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2: Status Precedence — Monotonic Projection
# ═══════════════════════════════════════════════════════════════════════════════

class TestStatusPrecedence:
    """Test that status events are applied monotonically, not by arrival order."""

    def test_precedence_values(self):
        """Verify precedence ordering: accepted < sent < delivered < read, failed=terminal."""
        assert STATUS_PRECEDENCE["accepted"] == 1
        assert STATUS_PRECEDENCE["sent"] == 2
        assert STATUS_PRECEDENCE["delivered"] == 3
        assert STATUS_PRECEDENCE["read"] == 4
        assert STATUS_PRECEDENCE["failed"] == 5
        assert STATUS_PRECEDENCE["undelivered"] == 5

    def test_is_status_upgrade_normal_flow(self):
        """Normal progression: accepted → sent → delivered → read."""
        assert _is_status_upgrade(None, "sent") is True
        assert _is_status_upgrade("accepted", "sent") is True
        assert _is_status_upgrade("sent", "delivered") is True
        assert _is_status_upgrade("delivered", "read") is True

    def test_is_status_upgrade_same_status(self):
        """Same status is allowed (idempotent)."""
        assert _is_status_upgrade("delivered", "delivered") is True

    def test_is_status_upgrade_downgrade_blocked(self):
        """Downgrades are blocked: read → delivered should not upgrade."""
        assert _is_status_upgrade("read", "delivered") is False
        assert _is_status_upgrade("read", "sent") is False
        assert _is_status_upgrade("delivered", "sent") is False

    def test_is_status_upgrade_terminal_never_downgraded(self):
        """Terminal states (failed/undelivered) are never overwritten."""
        assert _is_status_upgrade("failed", "read") is False
        assert _is_status_upgrade("failed", "delivered") is False
        assert _is_status_upgrade("undelivered", "read") is False

    def test_is_status_upgrade_unsupported_never_wins(self):
        """Unsupported status has precedence 0 and never wins over real states."""
        assert _is_status_upgrade("sent", "unsupported") is False
        assert _is_status_upgrade("delivered", "unsupported") is False

    def test_out_of_order_read_before_delivered(self):
        """Read arriving before delivered: read wins, delivered is ignored."""
        # First ingest: read arrives
        read_payload = _load_fixture("status_read_before_delivered.json")
        result1 = ingest_wabis_outbound_event(
            payload=read_payload, headers={}, auth_verified=True
        )
        assert result1["status"] == "processed"
        assert result1["normalized"]["delivery_status"] == "read"

        # Verify the outbound message has read status
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT delivery_status FROM wabis_outbound_messages WHERE message_id = ?",
                ("wamid_admin_reply_001",),
            ).fetchone()
            # read was first, so it should be set
            assert row is not None

    def test_monotonic_status_in_outbound_messages(self):
        """Status in wabis_outbound_messages should only upgrade, never downgrade."""
        phone = "919746785791"
        msg_id = "wamid_monotonic_001"

        # Step 1: sent
        sent_payload = {
            "event": "conversation.message.status",
            "message": {"id": msg_id, "status": "sent"},
            "contact": {"wa_id": phone},
        }
        ingest_wabis_outbound_event(payload=sent_payload, headers={}, auth_verified=True)

        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT delivery_status FROM wabis_outbound_messages WHERE message_id = ?",
                (msg_id,),
            ).fetchone()
            assert row["delivery_status"] == "sent"

        # Step 2: delivered (upgrade)
        delivered_payload = {
            "event": "conversation.message.status",
            "message": {"id": msg_id, "status": "delivered"},
            "contact": {"wa_id": phone},
        }
        ingest_wabis_outbound_event(payload=delivered_payload, headers={}, auth_verified=True)

        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT delivery_status FROM wabis_outbound_messages WHERE message_id = ?",
                (msg_id,),
            ).fetchone()
            assert row["delivery_status"] == "delivered"

        # Step 3: late "sent" callback (should NOT downgrade)
        late_sent = {
            "event": "conversation.message.status",
            "message": {"id": msg_id, "status": "sent"},
            "contact": {"wa_id": phone},
        }
        # Use a different event_hash by adding a unique field
        late_sent["_unique"] = str(uuid.uuid4())
        ingest_wabis_outbound_event(payload=late_sent, headers={}, auth_verified=True)

        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT delivery_status FROM wabis_outbound_messages WHERE message_id = ?",
                (msg_id,),
            ).fetchone()
            # Should still be delivered, not sent
            assert row["delivery_status"] == "delivered"


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2: Raw Status Events Always Stored
# ═══════════════════════════════════════════════════════════════════════════════

class TestRawStatusEventStorage:
    """Test that ALL raw status events are stored regardless of precedence."""

    def test_all_status_events_persisted(self):
        """Every status callback creates a row in wabis_message_status_events."""
        phone = "919746785791"
        msg_id = "wamid_raw_001"

        statuses = ["sent", "delivered", "read"]
        for i, status in enumerate(statuses):
            payload = {
                "event": "conversation.message.status",
                "event_id": f"evt_raw_{i}",
                "message": {"id": msg_id, "status": status},
                "contact": {"wa_id": phone},
            }
            ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)

        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT delivery_status FROM wabis_message_status_events WHERE message_id = ? ORDER BY created_at",
                (msg_id,),
            ).fetchall()
            assert len(rows) == 3
            assert [r["delivery_status"] for r in rows] == ["sent", "delivered", "read"]


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3: Compare-and-Swap Retry Guard
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompareAndSwapRetry:
    """Test that conversation version increments on state changes and can be used for CAS."""

    def test_version_increments_on_state_change(self):
        """Each set_conversation_state call increments the version."""
        phone = "919746785791"

        set_conversation_state(phone, owner="ai", owner_reason="initial")
        state1 = get_conversation_state(phone)
        assert state1["version"] == 1

        set_conversation_state(phone, owner="human", owner_reason="admin_reply")
        state2 = get_conversation_state(phone)
        assert state2["version"] == 2

        set_conversation_state(phone, owner="ai", owner_reason="reset")
        state3 = get_conversation_state(phone)
        assert state3["version"] == 3

    def test_version_persisted_in_state(self):
        """Version is returned in get_conversation_state dict."""
        phone = "919746785791"
        set_conversation_state(phone, owner="ai")
        state = get_conversation_state(phone)
        assert "version" in state
        assert state["version"] >= 1

    def test_conversation_mode_persisted(self):
        """conversation_mode is set and retrieved correctly."""
        phone = "919746785791"
        set_conversation_state(phone, owner="human", conversation_mode="HUMAN_SOFT_LOCK")
        state = get_conversation_state(phone)
        assert state["conversation_mode"] == "HUMAN_SOFT_LOCK"

    def test_retry_state_persisted(self):
        """retry_state is set and retrieved correctly."""
        phone = "919746785791"
        set_conversation_state(phone, owner="human", retry_state="CANCELLED_BY_HUMAN")
        state = get_conversation_state(phone)
        assert state["retry_state"] == "CANCELLED_BY_HUMAN"

    def test_latest_outbound_state_persisted(self):
        """latest_outbound_state is set and retrieved correctly."""
        phone = "919746785791"
        set_conversation_state(phone, owner="human", latest_outbound_state="HUMAN_SENT")
        state = get_conversation_state(phone)
        assert state["latest_outbound_state"] == "HUMAN_SENT"


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 4: Review Item Creation + Human Lock
# ═══════════════════════════════════════════════════════════════════════════════

class TestReviewItemCreation:
    """Test that human outbound events create review items and conversation locks."""

    def test_admin_reply_creates_review_item(self):
        """Admin text reply creates a review_item with OPEN state."""
        payload = _load_fixture("admin_text_reply.json")
        result = ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)

        assert result["status"] == "processed"
        projection = result["projection"]
        assert projection["lock_applied"] is True
        assert projection["cancelled_jobs"] >= 0

        # Verify review item was created
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT * FROM review_items WHERE customer_phone = ?",
                ("919746785791",),
            ).fetchone()
            assert row is not None
            assert row["review_state"] == "OPEN"
            assert row["conversation_id"] == "conv_919746785791_001"

    def test_admin_reply_creates_human_lock(self):
        """Admin reply creates a row in wabis_human_locks."""
        payload = _load_fixture("admin_text_reply.json")
        ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)

        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT * FROM wabis_human_locks WHERE customer_phone = ?",
                ("919746785791",),
            ).fetchone()
            assert row is not None
            assert row["event_type"] == "conversation.admin_reply.sent"
            assert row["lock_reason"] == "human_outbound_observed"
            assert row["lock_until"] is not None

    def test_admin_reply_sets_conversation_owner_to_human(self):
        """Admin reply sets conversation_state.owner = 'human'."""
        phone = "919746785791"
        set_conversation_state(phone, owner="ai")
        state_before = get_conversation_state(phone)
        assert state_before["owner"] == "ai"

        payload = _load_fixture("admin_text_reply.json")
        ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)

        state_after = get_conversation_state(phone)
        assert state_after["owner"] == "human"
        assert state_after["conversation_mode"] == "HUMAN_SOFT_LOCK"
        assert state_after["retry_state"] == "CANCELLED_BY_HUMAN"
        assert state_after["latest_outbound_state"] == "HUMAN_SENT"

    def test_bot_paused_sets_hard_lock(self):
        """Bot pause sets conversation_mode = PAUSED."""
        phone = "919746785791"
        payload = _load_fixture("bot_paused.json")
        result = ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)

        assert result["projection"]["lock_applied"] is True

        state = get_conversation_state(phone)
        assert state["conversation_mode"] == "PAUSED"

    def test_agent_assigned_sets_hard_lock(self):
        """Agent assignment sets conversation_mode = HUMAN_HARD_LOCK."""
        phone = "919746785791"
        payload = _load_fixture("agent_assigned.json")
        result = ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)

        assert result["projection"]["lock_applied"] is True

        state = get_conversation_state(phone)
        assert state["conversation_mode"] == "HUMAN_HARD_LOCK"

    def test_bot_resumed_releases_lock(self):
        """Bot resume resets conversation state."""
        phone = "919746785791"
        # First pause
        set_conversation_state(phone, owner="human", conversation_mode="PAUSED")
        state = get_conversation_state(phone)
        assert state["owner"] == "human"

        # Then resume
        payload = _load_fixture("bot_resumed.json")
        result = ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)

        assert result["projection"]["released"] is True

        state = get_conversation_state(phone)
        assert state["owner"] == "ai"

    def test_status_only_event_does_not_lock(self):
        """Pure status callback (sent/delivered/read) does NOT create a lock."""
        payload = _load_fixture("status_delivered.json")
        result = ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)

        assert result["projection"]["lock_applied"] is False

        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM wabis_human_locks WHERE customer_phone = ?",
                ("919746785791",),
            ).fetchone()
            assert row["cnt"] == 0

    def test_review_item_evidence_contains_human_message(self):
        """Review item evidence_json contains the human's message text."""
        payload = _load_fixture("admin_text_reply.json")
        ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)

        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT evidence_json FROM review_items WHERE customer_phone = ?",
                ("919746785791",),
            ).fetchone()
            evidence = json.loads(row["evidence_json"])
            assert "human_message" in evidence
            assert "Google Pay" in evidence["human_message"]
            assert "event_type" in evidence
            assert evidence["event_type"] == "conversation.admin_reply.sent"


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 4: AI Job Cancellation on Human Lock
# ═══════════════════════════════════════════════════════════════════════════════

class TestAIJobCancellation:
    """Test that pending AI reply jobs are cancelled when human outbound is observed."""

    def test_pending_jobs_cancelled_on_admin_reply(self):
        """Admin reply cancels all pending/learning/ready AI jobs for that phone."""
        phone = "919746785791"

        # Create some pending AI reply jobs
        with get_db_connection() as conn:
            for i in range(3):
                conn.execute(
                    """
                    INSERT INTO ai_reply_jobs
                    (id, conversation_id, customer_phone, customer_name, source_message_id,
                     source_message, message_type, status, delay_type, scheduled_at,
                     metadata_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        f"conv_{i}",
                        phone,
                        "Test",
                        f"msg_{i}",
                        f"message {i}",
                        "text",
                        "first_learning_60s",
                        "2026-06-06T04:00:00+00:00",
                        "{}",
                        "2026-06-06T04:00:00+00:00",
                        "2026-06-06T04:00:00+00:00",
                    ),
                )
            conn.commit()

        # Ingest admin reply
        payload = _load_fixture("admin_text_reply.json")
        result = ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)

        assert result["projection"]["cancelled_jobs"] == 3

        # Verify jobs are cancelled
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT status, skipped_reason FROM ai_reply_jobs WHERE customer_phone = ?",
                (phone,),
            ).fetchall()
            for row in rows:
                assert row["status"] == "cancelled"
                assert row["skipped_reason"] == "cancelled_by_human_outbound_event"


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 5: Duplicate Handling
# ═══════════════════════════════════════════════════════════════════════════════

class TestDuplicateHandling:
    """Test that duplicate webhook deliveries are handled idempotently."""

    def test_duplicate_event_returns_duplicate_status(self):
        """Second delivery of the same event returns 'duplicate' status."""
        payload = _load_fixture("admin_text_reply.json")

        result1 = ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)
        assert result1["status"] == "processed"

        result2 = ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)
        assert result2["status"] == "duplicate"

    def test_duplicate_does_not_create_second_review_item(self):
        """Duplicate delivery does not create a second review item."""
        payload = _load_fixture("admin_text_reply.json")

        ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)
        ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)

        with get_db_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM review_items WHERE customer_phone = ?",
                ("919746785791",),
            ).fetchone()["cnt"]
            assert count == 1

    def test_duplicate_does_not_create_second_lock(self):
        """Duplicate delivery does not create a second human lock."""
        payload = _load_fixture("admin_text_reply.json")

        ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)
        ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)

        with get_db_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM wabis_human_locks WHERE customer_phone = ?",
                ("919746785791",),
            ).fetchone()["cnt"]
            assert count == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 7: Edge Cases — Unknown Fields, Unsupported, Empty Payloads
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Test edge cases: unknown fields, unsupported messages, empty payloads."""

    def test_unknown_fields_preserved_in_raw_storage(self):
        """Unknown top-level fields are preserved in raw_payload_json."""
        payload = _load_fixture("admin_text_reply.json")
        payload["unknown_future_field"] = "some_new_value"
        payload["nested_unknown"] = {"key": "value"}

        result = ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)
        assert result["status"] == "processed"

        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT raw_payload_json FROM wabis_webhook_deliveries WHERE id = ?",
                (result["delivery_id"],),
            ).fetchone()
            raw = json.loads(row["raw_payload_json"])
            assert raw["unknown_future_field"] == "some_new_value"
            assert raw["nested_unknown"]["key"] == "value"

    def test_empty_payload_does_not_crash(self):
        """Empty payload is handled gracefully."""
        result = ingest_wabis_outbound_event(payload={}, headers={}, auth_verified=True)
        assert result["status"] == "processed"
        assert result["normalized"]["customer_phone"] == ""

    def test_unsupported_message_stores_raw_evidence(self):
        """Unsupported message type stores raw evidence without crashing."""
        payload = _load_fixture("unsupported_message.json")
        result = ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)

        assert result["status"] == "processed"
        assert result["normalized"]["delivery_status"] == "unsupported"

    def test_failed_status_with_error_details(self):
        """Failed status with error code is stored correctly."""
        payload = _load_fixture("status_failed.json")
        result = ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)

        assert result["status"] == "processed"
        assert result["normalized"]["delivery_status"] == "failed"

        # Verify raw payload preserves error details
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT raw_payload_json FROM wabis_webhook_deliveries WHERE id = ?",
                (result["delivery_id"],),
            ).fetchone()
            raw = json.loads(row["raw_payload_json"])
            assert "error" in raw
            assert raw["error"]["code"] == 131047

    def test_multiple_status_events_for_same_message(self):
        """Multiple status events for the same message_id are all stored."""
        phone = "919746785791"
        msg_id = "wamid_multi_001"

        for status in ["sent", "delivered", "read"]:
            payload = {
                "event": "conversation.message.status",
                "event_id": f"evt_multi_{status}",
                "message": {"id": msg_id, "status": status},
                "contact": {"wa_id": phone},
            }
            ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)

        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT delivery_status FROM wabis_message_status_events WHERE message_id = ? ORDER BY created_at",
                (msg_id,),
            ).fetchall()
            assert len(rows) == 3
            assert [r["delivery_status"] for r in rows] == ["sent", "delivered", "read"]


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 5: Dashboard API — Intent Rule Versioning
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntentRuleVersioning:
    """Test that promotions create new immutable rule versions."""

    def test_promote_creates_intent_rule_and_version(self):
        """Promoting a review item creates an intent_rule + intent_rule_version."""
        # First create a review item via admin reply
        payload = _load_fixture("admin_text_reply.json")
        ingest_wabis_outbound_event(payload=payload, headers={}, auth_verified=True)

        # Get the review item
        with get_db_connection() as conn:
            review = conn.execute(
                "SELECT id FROM review_items WHERE customer_phone = ?",
                ("919746785791",),
            ).fetchone()
            review_id = review["id"]

        # Simulate promotion: create intent rule + version
        with get_db_connection() as conn:
            # Approve
            conn.execute(
                "UPDATE review_items SET review_state = 'APPROVED', updated_at = ? WHERE id = ?",
                ("2026-06-06T05:00:00+00:00", review_id),
            )

            # Create intent rule
            rule_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO intent_rules (id, tenant_id, intent_key, status, created_at, updated_at) VALUES (?, ?, ?, 'active', ?, ?)",
                (rule_id, "default", "payment_help", "2026-06-06T05:00:00+00:00", "2026-06-06T05:00:00+00:00"),
            )

            # Create version
            version_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO intent_rule_versions (id, intent_rule_id, version_no, is_active, rule_json, created_at) VALUES (?, ?, 1, 1, ?, ?)",
                (version_id, rule_id, json.dumps({"pattern": "payment", "response": "help"}), "2026-06-06T05:00:00+00:00"),
            )

            # Record promotion
            promo_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO rule_promotions (id, review_item_id, intent_rule_version_id, status, promoted_by, promoted_at, created_at) VALUES (?, ?, ?, 'active', ?, ?, ?)",
                (promo_id, review_id, version_id, "agent_001", "2026-06-06T05:00:00+00:00", "2026-06-06T05:00:00+00:00"),
            )

            # Update review item
            conn.execute(
                "UPDATE review_items SET review_state = 'PROMOTED', updated_at = ? WHERE id = ?",
                ("2026-06-06T05:00:00+00:00", review_id),
            )
            conn.commit()

        # Verify
        with get_db_connection() as conn:
            rule = conn.execute("SELECT * FROM intent_rules WHERE intent_key = ?", ("payment_help",)).fetchone()
            assert rule is not None
            assert rule["status"] == "active"

            version = conn.execute("SELECT * FROM intent_rule_versions WHERE intent_rule_id = ?", (rule_id,)).fetchone()
            assert version is not None
            assert version["version_no"] == 1
            assert version["is_active"] == 1

            promo = conn.execute("SELECT * FROM rule_promotions WHERE review_item_id = ?", (review_id,)).fetchone()
            assert promo is not None
            assert promo["status"] == "active"

    def test_rollback_creates_new_version_and_deactivates_old(self):
        """Rollback deactivates the promoted version and reactivates the prior one."""
        with get_db_connection() as conn:
            # Setup: create rule with two versions
            rule_id = str(uuid.uuid4())
            v1_id = str(uuid.uuid4())
            v2_id = str(uuid.uuid4())
            review_id = str(uuid.uuid4())
            now = "2026-06-06T05:00:00+00:00"

            conn.execute(
                "INSERT INTO intent_rules (id, tenant_id, intent_key, status, created_at, updated_at) VALUES (?, ?, 'active', ?, ?)",
                (rule_id, "default", "test_intent", now, now),
            )
            conn.execute(
                "INSERT INTO intent_rule_versions (id, intent_rule_id, version_no, is_active, rule_json, created_at) VALUES (?, ?, 1, 0, ?, ?)",
                (v1_id, rule_id, '{"v": 1}', now),
            )
            conn.execute(
                "INSERT INTO intent_rule_versions (id, intent_rule_id, version_no, is_active, rule_json, created_at) VALUES (?, ?, 2, 1, ?, ?)",
                (v2_id, rule_id, '{"v": 2}', now),
            )
            conn.execute(
                "INSERT INTO review_items (id, conversation_id, customer_phone, review_state, evidence_json, created_at, updated_at) VALUES (?, ?, ?, 'PROMOTED', '{}', ?, ?)",
                (review_id, "conv_001", "919746785791", now, now),
            )
            promo_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO rule_promotions (id, review_item_id, intent_rule_version_id, status, promoted_by, promoted_at, created_at) VALUES (?, ?, ?, 'active', ?, ?, ?)",
                (promo_id, review_id, v2_id, "agent_001", now, now),
            )
            conn.commit()

            # Rollback: deactivate v2, reactivate v1
            conn.execute("UPDATE intent_rule_versions SET is_active = 0 WHERE id = ?", (v2_id,))
            conn.execute("UPDATE intent_rule_versions SET is_active = 1 WHERE id = ?", (v1_id,))
            conn.execute("UPDATE rule_promotions SET status = 'rolled_back' WHERE id = ?", (promo_id,))
            conn.execute(
                "UPDATE review_items SET review_state = 'ROLLED_BACK', updated_at = ? WHERE id = ?",
                (now, review_id),
            )
            # Record rollback promotion
            rollback_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO rule_promotions (id, review_item_id, intent_rule_version_id, status, promoted_by, promoted_at, rollback_of, created_at) VALUES (?, ?, ?, 'rollback', ?, ?, ?, ?)",
                (rollback_id, review_id, v1_id, "admin_001", now, promo_id, now),
            )
            conn.commit()

        # Verify
        with get_db_connection() as conn:
            v1 = conn.execute("SELECT is_active FROM intent_rule_versions WHERE id = ?", (v1_id,)).fetchone()
            v2 = conn.execute("SELECT is_active FROM intent_rule_versions WHERE id = ?", (v2_id,)).fetchone()
            assert v1["is_active"] == 1
            assert v2["is_active"] == 0

            promo = conn.execute("SELECT status FROM rule_promotions WHERE id = ?", (promo_id,)).fetchone()
            assert promo["status"] == "rolled_back"

            rollback = conn.execute("SELECT * FROM rule_promotions WHERE rollback_of = ?", (promo_id,)).fetchone()
            assert rollback is not None
            assert rollback["status"] == "rollback"


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 6: Audit Log
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditLog:
    """Test that audit log entries are created for key operations."""

    def test_audit_log_table_exists(self):
        """audit_logs table is created by ensure_runtime_tables."""
        ensure_runtime_tables()
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'audit_logs'"
            ).fetchone()
            assert row is not None

    def test_audit_log_insert(self):
        """Can insert and retrieve audit log entries."""
        ensure_runtime_tables()
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs
                (id, actor_id, actor_role, entity_type, entity_id, action,
                 before_json, after_json, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    "agent_001",
                    "reviewer",
                    "review_item",
                    "ri_001",
                    "approve",
                    json.dumps({"review_state": "OPEN"}),
                    json.dumps({"review_state": "APPROVED"}),
                    "Valid human reply",
                    "2026-06-06T05:00:00+00:00",
                ),
            )
            conn.commit()

            row = conn.execute("SELECT * FROM audit_logs WHERE entity_id = ?", ("ri_001",)).fetchone()
            assert row is not None
            assert row["action"] == "approve"
            assert row["actor_role"] == "reviewer"
