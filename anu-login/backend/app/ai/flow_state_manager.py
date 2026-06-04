"""Flow State Manager - Track Wabis flows per customer

When a Wabis flow is active:
- Owner is set to 'wabis' (AI cannot interrupt)
- Returns flow ID and current step
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.storage import get_db_connection
from app.ai.conversation_owner import set_owner, release_owner

logger = logging.getLogger(__name__)


def _table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def start_flow(phone: str, flow_id: str, initial_step: str = "started") -> None:
    """
    Start a Wabis flow for customer.
    Automatically sets owner to 'wabis' (AI cannot interrupt).
    """
    try:
        conn = get_db_connection()
        now = datetime.now(timezone.utc).isoformat()
        
        conn.execute(
            """
            INSERT INTO conversation_flow (phone, flow_id, current_step, started_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(phone) DO UPDATE SET
                flow_id = excluded.flow_id,
                current_step = excluded.current_step,
                started_at = excluded.started_at,
                updated_at = excluded.updated_at
            """,
            (phone, flow_id, initial_step, now, now),
        )
        conn.commit()
        
        # Claim ownership for Wabis
        set_owner(phone, "wabis")
        logger.info(f"[FLOW] Started {flow_id} for {phone}, owner=wabis")
    except Exception as e:
        logger.error(f"Failed to start flow: {e}")


def get_active_flow(phone: str) -> Optional[dict[str, Any]]:
    """Get active flow for customer (if any)"""
    try:
        conn = get_db_connection()
        row = conn.execute(
            """
            SELECT flow_id, current_step, started_at
            FROM conversation_flow
            WHERE phone = ?
            """,
            (phone,)
        ).fetchone()
        
        if row:
            return {
                "flow_id": row[0],
                "current_step": row[1],
                "started_at": row[2],
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get active flow: {e}")
        return None


def mark_flow_step(phone: str, step: str) -> None:
    """Update current step in active flow"""
    try:
        conn = get_db_connection()
        now = datetime.now(timezone.utc).isoformat()
        
        conn.execute(
            """
            UPDATE conversation_flow
            SET current_step = ?, updated_at = ?
            WHERE phone = ?
            """,
            (step, now, phone),
        )
        conn.commit()
        logger.info(f"[FLOW] {phone} → step: {step}")
    except Exception as e:
        logger.error(f"Failed to mark flow step: {e}")


def end_flow(phone: str) -> None:
    """
    End flow for customer.
    Releases Wabis ownership, allows AI to respond again.
    """
    try:
        conn = get_db_connection()

        if _table_exists(conn, "conversation_flow"):
            conn.execute(
                "DELETE FROM conversation_flow WHERE phone = ?",
                (phone,)
            )
            conn.commit()
        else:
            logger.info("[FLOW] conversation_flow table missing; skipping legacy flow delete for %s", phone)

        logger.info(f"[FLOW] Ended for {phone}, owner=ai")
    except Exception as e:
        logger.error(f"Failed to end flow: {e}")
    finally:
        # Release legacy ownership even when the legacy flow table is absent.
        release_owner(phone)


def is_waiting_response(phone: str) -> bool:
    """Check if flow is waiting for customer response"""
    flow = get_active_flow(phone)
    if not flow:
        return False
    
    # If flow is waiting for specific step (not ended), return True
    return flow.get("current_step") not in (None, "ended", "completed")
