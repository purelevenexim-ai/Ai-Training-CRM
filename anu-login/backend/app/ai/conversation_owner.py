"""Conversation Owner Manager - Track who controls each conversation

States: wabis | ai | human
Only the owner can send messages. Others stay silent.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.storage import get_db_connection

logger = logging.getLogger(__name__)


def _ensure_owner_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_owner (
            phone TEXT PRIMARY KEY,
            owner TEXT NOT NULL DEFAULT 'ai',
            updated_at TEXT NOT NULL
        )
        """
    )


def set_owner(phone: str, owner: str) -> None:
    """
    Claim ownership of conversation.
    States: 'wabis' | 'ai' | 'human'
    """
    if owner not in ("wabis", "ai", "human"):
        logger.warning(f"Invalid owner state: {owner}")
        return
    
    try:
        conn = get_db_connection()
        _ensure_owner_table(conn)
        updated_at = datetime.now(timezone.utc).isoformat()
        
        conn.execute(
            """
            INSERT INTO conversation_owner (phone, owner, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(phone) DO UPDATE SET
                owner = excluded.owner,
                updated_at = excluded.updated_at
            """,
            (phone, owner, updated_at),
        )
        conn.commit()
        logger.info(f"[OWNER] {phone} → {owner}")
    except Exception as e:
        logger.error(f"Failed to set owner: {e}")


def get_owner(phone: str) -> str:
    """Get current owner of conversation. Defaults to 'ai'"""
    try:
        conn = get_db_connection()
        _ensure_owner_table(conn)
        row = conn.execute(
            "SELECT owner FROM conversation_owner WHERE phone = ?",
            (phone,)
        ).fetchone()
        
        if row:
            return row[0]
        return "ai"  # Default
    except Exception as e:
        logger.error(f"Failed to get owner: {e}")
        return "ai"


def is_owned_by(phone: str, owner: str) -> bool:
    """Check if conversation is owned by specific owner"""
    current_owner = get_owner(phone)
    return current_owner == owner


def release_owner(phone: str) -> None:
    """Release ownership (reset to default 'ai')"""
    set_owner(phone, "ai")
