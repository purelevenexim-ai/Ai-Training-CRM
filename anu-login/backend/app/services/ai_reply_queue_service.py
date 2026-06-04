from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.ai.intent_registry import intent_metadata
from app.ai.product_knowledge import detect_product
from app.ai.conversation_state_manager import get_conversation_state
from app.runtime_db import ensure_runtime_tables, get_db_connection

logger = logging.getLogger(__name__)

FIRST_LEARNING_DELAY_SECONDS = 60
# Keep every AI-owned customer message in a short "learning" window before
# sending. This gives the worker time to absorb newer customer messages and
# avoids rushed, fragmented replies in active WhatsApp conversations.
ACTIVE_SESSION_DEBOUNCE_SECONDS = 60
SESSION_TTL_HOURS = 24
STALE_LEARNING_SECONDS = 120


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _now() -> str:
    return _now_dt().isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def stable_payload_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def normalize_event_id(payload: dict[str, Any], payload_hash: str) -> str:
    for key in (
        "webhook_id",
        "message_id",
        "wa_message_id",
        "wamid",
        "id",
        "event_id",
        "reply_message_id",
        "postback_id",
        "postbackid",
    ):
        value = str(payload.get(key) or "").strip()
        if value:
            return value[:220]
    return payload_hash


def mark_processed_event(
    *,
    source: str,
    event_id: str,
    conversation_id: str,
    customer_phone: str,
    event_type: str,
    payload_hash: str,
) -> bool:
    """Return False when this webhook event has already been processed."""
    ensure_runtime_tables()
    try:
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO processed_events
                (id, source, event_id, conversation_id, customer_phone, event_type, payload_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    source,
                    event_id or payload_hash,
                    conversation_id,
                    customer_phone,
                    event_type,
                    payload_hash,
                    _now(),
                ),
            )
            conn.commit()
        return True
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            logger.warning("[AI-QUEUE] duplicate webhook ignored phone=%s event=%s", customer_phone, event_id)
            return False
        raise


def log_ai_decision(
    *,
    conversation_id: str,
    customer_phone: str,
    incoming_message: str,
    final_route_owner: str,
    generated_response: str = "",
    matched_template: str = "",
    wabis_state_transition: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    product_key = detect_product(incoming_message)
    understanding = intent_metadata(incoming_message, product_detected=bool(product_key))
    ensure_runtime_tables()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO ai_decision_logs
            (id, conversation_id, customer_phone, incoming_message, normalized_message,
             detected_language, detected_product, detected_intent, matched_template,
             generated_response, final_route_owner, wabis_state_transition, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                conversation_id,
                customer_phone,
                incoming_message[:1000],
                str(understanding.get("normalized_message") or "")[:1000],
                str(understanding.get("detected_language") or ""),
                product_key or "",
                str(understanding.get("detected_intent") or ""),
                matched_template,
                generated_response[:4000],
                final_route_owner,
                wabis_state_transition,
                json.dumps(metadata or {}, ensure_ascii=False),
                _now(),
            ),
        )
        conn.commit()


def _active_session_row(conn, phone: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT *
        FROM ai_conversation_sessions
        WHERE customer_phone = ? AND status = 'active' AND expires_at > ?
        ORDER BY expires_at DESC
        LIMIT 1
        """,
        (phone, _now()),
    ).fetchone()
    return dict(row) if row else None


def _latest_learning_session_row(conn, phone: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT *
        FROM ai_conversation_sessions
        WHERE customer_phone = ? AND status = 'learning'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (phone,),
    ).fetchone()
    return dict(row) if row else None


def enqueue_ai_reply_job(
    *,
    conversation_id: str,
    customer_phone: str,
    customer_name: str,
    source_message_id: str,
    incoming_message: str,
    message_type: str = "text",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist a delayed AI reply job. Newer customer messages supersede older pending jobs."""
    now_dt = _now_dt()
    now = now_dt.isoformat()
    ensure_runtime_tables()
    with get_db_connection() as conn:
        active_session = _active_session_row(conn, customer_phone)
        delay_seconds = ACTIVE_SESSION_DEBOUNCE_SECONDS if active_session else FIRST_LEARNING_DELAY_SECONDS
        delay_type = "active_session_learning_60s" if active_session else "first_learning_60s"

        conn.execute(
            """
            UPDATE ai_reply_jobs
            SET status = 'cancelled',
                skipped_reason = 'newer_customer_message',
                updated_at = ?
            WHERE customer_phone = ?
              AND status IN ('pending', 'learning', 'ready')
            """,
            (now, customer_phone),
        )

        product_key = detect_product(incoming_message)
        understanding = intent_metadata(incoming_message, product_detected=bool(product_key))
        expires_at = (now_dt + timedelta(hours=SESSION_TTL_HOURS)).isoformat()
        if active_session:
            session_id = active_session["id"]
            conn.execute(
                """
                UPDATE ai_conversation_sessions
                SET conversation_id = ?,
                    last_customer_message_at = ?,
                    expires_at = ?,
                    last_language = ?,
                    last_intent = ?,
                    last_product = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    conversation_id,
                    now,
                    expires_at,
                    understanding.get("detected_language"),
                    understanding.get("detected_intent"),
                    product_key,
                    now,
                    session_id,
                ),
            )
        else:
            learning = _latest_learning_session_row(conn, customer_phone)
            session_id = learning["id"] if learning else str(uuid.uuid4())
            if learning:
                conn.execute(
                    """
                    UPDATE ai_conversation_sessions
                    SET conversation_id = ?,
                        last_customer_message_at = ?,
                        expires_at = ?,
                        last_language = ?,
                        last_intent = ?,
                        last_product = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        conversation_id,
                        now,
                        expires_at,
                        understanding.get("detected_language"),
                        understanding.get("detected_intent"),
                        product_key,
                        now,
                        session_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO ai_conversation_sessions
                    (id, conversation_id, customer_phone, status, session_started_at,
                     last_customer_message_at, expires_at, last_language, last_intent,
                     last_product, customer_stage, created_at, updated_at)
                    VALUES (?, ?, ?, 'learning', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        conversation_id,
                        customer_phone,
                        now,
                        now,
                        expires_at,
                        understanding.get("detected_language"),
                        understanding.get("detected_intent"),
                        product_key,
                        "learning_context",
                        now,
                        now,
                    ),
                )

        job_id = str(uuid.uuid4())
        scheduled_at = (now_dt + timedelta(seconds=delay_seconds)).isoformat()
        conn.execute(
            """
            INSERT INTO ai_reply_jobs
            (id, conversation_id, customer_phone, customer_name, source_message_id,
             source_message, message_type, status, delay_type, scheduled_at,
             metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                conversation_id,
                customer_phone,
                customer_name or "Customer",
                source_message_id,
                incoming_message,
                message_type,
                delay_type,
                scheduled_at,
                json.dumps(metadata or {}, ensure_ascii=False),
                now,
                now,
            ),
        )
        conn.commit()

    log_ai_decision(
        conversation_id=conversation_id,
        customer_phone=customer_phone,
        incoming_message=incoming_message,
        final_route_owner="ai_queue",
        matched_template=delay_type,
        metadata={"job_id": job_id, "scheduled_at": scheduled_at, "delay_seconds": delay_seconds},
    )
    return {
        "status": "queued",
        "job_id": job_id,
        "delay_type": delay_type,
        "scheduled_at": scheduled_at,
        "session_id": session_id,
    }


def _newer_customer_message_exists(conn, job: dict[str, Any]) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM ai_incoming_messages
        WHERE customer_phone = ?
          AND id != ?
          AND created_at > ?
        LIMIT 1
        """,
        (
            job["customer_phone"],
            job["source_message_id"],
            job["created_at"],
        ),
    ).fetchone()
    return row is not None


def _build_context_summary(conn, job: dict[str, Any]) -> str:
    incoming_rows = conn.execute(
        """
        SELECT body, created_at
        FROM ai_incoming_messages
        WHERE customer_phone = ?
        ORDER BY created_at DESC
        LIMIT 8
        """,
        (job["customer_phone"],),
    ).fetchall()
    outgoing_rows = conn.execute(
        """
        SELECT reply_text, intent, send_status, created_at
        FROM ai_outgoing_replies
        WHERE customer_phone = ?
        ORDER BY created_at DESC
        LIMIT 5
        """,
        (job["customer_phone"],),
    ).fetchall()
    state_row = conn.execute(
        """
        SELECT owner, flow_id, flow_step, owner_reason, context_json
        FROM conversation_state
        WHERE phone = ?
        LIMIT 1
        """,
        (job["customer_phone"],),
    ).fetchone()
    product_key = detect_product(job["source_message"])
    understanding = intent_metadata(job["source_message"], product_detected=bool(product_key))
    summary = {
        "latest_message": job["source_message"],
        "detected_product": product_key,
        "detected_language": understanding.get("detected_language"),
        "detected_intent": understanding.get("detected_intent"),
        "recent_customer_messages": [dict(row) for row in incoming_rows],
        "recent_ai_replies": [dict(row) for row in outgoing_rows],
        "state": dict(state_row) if state_row else None,
    }
    return json.dumps(summary, ensure_ascii=False, default=str)[:6000]


def _reconcile_stale_jobs(conn) -> list[dict[str, Any]]:
    """Recover jobs left in learning/failed states after send/write races."""
    now = _now()
    stale_cutoff = (_now_dt() - timedelta(seconds=STALE_LEARNING_SECONDS)).isoformat()
    recovered: list[dict[str, Any]] = []
    rows = conn.execute(
        """
        SELECT *
        FROM ai_reply_jobs
        WHERE (
            status = 'learning' AND updated_at <= ?
        ) OR (
            status = 'failed'
            AND (
                skipped_reason LIKE '%database is locked%'
                OR result_json LIKE '%database is locked%'
            )
        )
        ORDER BY updated_at ASC
        LIMIT 20
        """,
        (stale_cutoff,),
    ).fetchall()
    for row in rows:
        job = dict(row)
        sent_row = conn.execute(
            """
            SELECT id, created_at
            FROM ai_outgoing_replies
            WHERE customer_phone = ?
              AND created_at >= ?
              AND send_status IN ('sent', 'logged')
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (job["customer_phone"], job["created_at"]),
        ).fetchone()
        if sent_row:
            conn.execute(
                """
                UPDATE ai_reply_jobs
                SET status = 'sent',
                    sent_at = ?,
                    skipped_reason = 'reconciled_existing_outgoing_reply',
                    result_json = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    sent_row["created_at"],
                    json.dumps({"reconciled_reply_id": sent_row["id"]}, ensure_ascii=False),
                    now,
                    job["id"],
                ),
            )
            recovered.append({"job_id": job["id"], "status": "sent", "reason": "reconciled_existing_outgoing_reply"})
            continue
        if job["status"] == "learning":
            conn.execute(
                """
                UPDATE ai_reply_jobs
                SET status = 'pending',
                    scheduled_at = ?,
                    skipped_reason = 'recovered_stale_learning_job',
                    updated_at = ?
                WHERE id = ?
                """,
                (now, now, job["id"]),
            )
            recovered.append({"job_id": job["id"], "status": "pending", "reason": "recovered_stale_learning_job"})
    return recovered


def _mark_job(conn, job_id: str, status: str, *, reason: str = "", result: dict[str, Any] | None = None) -> None:
    now = _now()
    conn.execute(
        """
        UPDATE ai_reply_jobs
        SET status = ?,
            sent_at = CASE WHEN ? IN ('sent', 'skipped', 'failed') THEN ? ELSE sent_at END,
            skipped_reason = ?,
            result_json = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            status,
            status,
            now,
            reason,
            json.dumps(result or {}, ensure_ascii=False),
            now,
            job_id,
        ),
    )


def _finish_job(
    job: dict[str, Any],
    status: str,
    *,
    reason: str = "",
    result: dict[str, Any] | None = None,
) -> None:
    now = _now()
    with get_db_connection() as conn:
        _mark_job(conn, job["id"], status, reason=reason, result=result)
        if status == "sent":
            expires_at = (_now_dt() + timedelta(hours=SESSION_TTL_HOURS)).isoformat()
            conn.execute(
                """
                UPDATE ai_conversation_sessions
                SET status = 'active',
                    last_ai_response_at = ?,
                    expires_at = ?,
                    updated_at = ?
                WHERE customer_phone = ?
                  AND status IN ('learning', 'active')
                """,
                (now, expires_at, now, job["customer_phone"]),
            )
        conn.commit()


def _claim_due_jobs(limit: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    now = _now()
    claimed: list[dict[str, Any]] = []
    with get_db_connection() as conn:
        recovered = _reconcile_stale_jobs(conn)
        rows = conn.execute(
            """
            SELECT *
            FROM ai_reply_jobs
            WHERE status = 'pending' AND scheduled_at <= ?
            ORDER BY scheduled_at ASC
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()
        for row in rows:
            job = dict(row)
            cursor = conn.execute(
                """
                UPDATE ai_reply_jobs
                SET status = 'learning',
                    locked_at = ?,
                    updated_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (now, now, job["id"]),
            )
            if cursor.rowcount:
                claimed.append(job | {"locked_at": now})
        conn.commit()
    return claimed, recovered


def run_due_ai_reply_jobs(limit: int = 20) -> list[dict[str, Any]]:
    """Process due AI reply jobs. Safe to run frequently from a scheduler."""
    ensure_runtime_tables()
    claimed_jobs, recovered = _claim_due_jobs(limit)
    processed: list[dict[str, Any]] = list(recovered)

    for job in claimed_jobs:
        try:
            with get_db_connection() as conn:
                context_summary = _build_context_summary(conn, job)
                conn.execute(
                    """
                    UPDATE ai_conversation_sessions
                    SET context_summary = ?,
                        updated_at = ?
                    WHERE customer_phone = ?
                      AND status IN ('learning', 'active')
                    """,
                    (context_summary, _now(), job["customer_phone"]),
                )
                conn.commit()

            with get_db_connection() as conn:
                job = dict(
                    conn.execute(
                        "SELECT * FROM ai_reply_jobs WHERE id = ? LIMIT 1",
                        (job["id"],),
                    ).fetchone()
                    or job
                )
                if job.get("status") != "learning":
                    processed.append({"job_id": job["id"], "status": "skipped", "reason": f"status={job.get('status')}"})
                    continue
                newer_message_exists = _newer_customer_message_exists(conn, job)

            if newer_message_exists:
                _finish_job(job, "cancelled", reason="newer_customer_message")
                processed.append({"job_id": job["id"], "status": "cancelled", "reason": "newer_customer_message"})
                continue

            state = get_conversation_state(job["customer_phone"])
            if state and state.get("owner") == "wabis":
                _finish_job(job, "skipped", reason="wabis_owns")
                processed.append({"job_id": job["id"], "status": "skipped", "reason": "wabis_owns"})
                log_ai_decision(
                    conversation_id=job["conversation_id"],
                    customer_phone=job["customer_phone"],
                    incoming_message=job["source_message"],
                    final_route_owner="wabis",
                    matched_template="wabis_state_active",
                    metadata={"job_id": job["id"], "state": state},
                )
                continue

            from app.routes.wave02_wabis_routes import _generate_and_send_reply

            result = _generate_and_send_reply(
                conversation_id=job["conversation_id"],
                customer_phone=job["customer_phone"],
                customer_name=job["customer_name"],
                incoming_message=job["source_message"],
                message_type=job["message_type"],
            )
            status = "sent" if result.get("status") in {"sent", "escalated"} else "skipped"
            if result.get("status") == "error":
                status = "failed"
            _finish_job(job, status, reason=str(result.get("reason") or ""), result=result)
            processed.append({"job_id": job["id"], "status": status, "result": result})
            log_ai_decision(
                conversation_id=job["conversation_id"],
                customer_phone=job["customer_phone"],
                incoming_message=job["source_message"],
                final_route_owner="ai",
                generated_response=str((result or {}).get("reply_text") or ""),
                matched_template=str((result or {}).get("intent") or ""),
                metadata={"job_id": job["id"], "result": result},
            )
        except Exception as exc:
            logger.error("[AI-QUEUE] job failed id=%s phone=%s error=%s", job["id"], job["customer_phone"], exc)
            _finish_job(job, "failed", reason=str(exc), result={"error": str(exc)})
            processed.append({"job_id": job["id"], "status": "failed", "error": str(exc)})

    return processed
