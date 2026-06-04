from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.runtime_db import ensure_runtime_tables, get_db_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def claim_message_owner(
    *,
    customer_id: str,
    incoming_message_id: str,
    owner: str,
    conversation_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Claim one reply owner for a single inbound provider event.

    Returns {"claimed": False, ...} when another path already owns/replied to the
    same message. This is deliberately small and deterministic so every send path
    can use it without depending on the LLM stack.
    """
    ensure_runtime_tables()
    customer_id = str(customer_id or "").strip()
    incoming_message_id = str(incoming_message_id or "").strip()
    owner = str(owner or "").strip() or "ai"
    if not customer_id or not incoming_message_id:
        return {"claimed": True, "reason": "missing_lock_key"}

    now = _now()
    try:
        with get_db_connection() as connection:
            lock_id = str(uuid.uuid4())
            connection.execute(
                """
                INSERT INTO message_processing_locks
                (id, customer_id, incoming_message_id, conversation_id, owner, status,
                 metadata_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'processing', ?, ?, ?)
                """,
                (
                    lock_id,
                    customer_id,
                    incoming_message_id,
                    conversation_id,
                    owner,
                    json.dumps(metadata or {}, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            connection.commit()
        return {"claimed": True, "lock_id": lock_id, "owner": owner}
    except Exception as exc:
        if "UNIQUE" not in str(exc).upper():
            raise
        with get_db_connection() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM message_processing_locks
                WHERE customer_id = ? AND incoming_message_id = ?
                LIMIT 1
                """,
                (customer_id, incoming_message_id),
            ).fetchone()
        existing = dict(row) if row else {}
        return {
            "claimed": False,
            "reason": "already_claimed",
            "owner": existing.get("owner") or "",
            "status": existing.get("status") or "",
            "lock_id": existing.get("id") or "",
        }


def finish_message_owner(
    *,
    lock_id: str,
    status: str,
    reply_message_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    if not lock_id:
        return
    ensure_runtime_tables()
    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE message_processing_locks
            SET status = ?,
                reply_message_id = COALESCE(NULLIF(?, ''), reply_message_id),
                metadata_json = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                reply_message_id or "",
                json.dumps(metadata or {}, ensure_ascii=False),
                _now(),
                lock_id,
            ),
        )
        connection.commit()
