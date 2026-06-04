"""
Clarification Flow Handler
Captures knowledge gaps instead of guessing with AI.

When customer query is unclear, ask for clarification.
Build knowledge base from customer responses instead of hallucinating.
"""

import logging
import json
import uuid
from typing import Any
from datetime import datetime, timezone

from app.storage import get_db_connection
from app.ai.wabis_api_client import WabisAPIClient

logger = logging.getLogger(__name__)


def log_knowledge_gap(phone: str, original_query: str, conversation_id: str = "") -> str:
    """
    Log that we don't understand this query.
    Returns gap_id for tracking.
    """
    try:
        gap_id = str(uuid.uuid4())
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO knowledge_gaps 
            (id, phone, original_query, conversation_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                gap_id,
                phone,
                original_query,
                conversation_id,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        logger.warning(f"[GAP-LOGGED] {phone}: {original_query[:50]}")
        return gap_id
    except Exception as e:
        logger.error(f"Failed to log knowledge gap: {e}")
        return ""


def send_clarification_menu(phone: str, conversation_id: str, original_query: str) -> None:
    """
    Send clarification menu to customer.
    Don't guess - ask what they mean.
    """
    
    clarification_text = f"""I wasn't sure what you meant by "{original_query}".

Could you tell me more? Are you looking for:

1️⃣ A specific product
2️⃣ How to use something
3️⃣ Recipe or cooking advice
4️⃣ Health or medical info

Just reply with the number!"""
    
    try:
        WabisAPIClient.send_text_message(
            phone_number=phone,
            message_text=clarification_text,
            conversation_id=conversation_id,
        )
        logger.info(f"[CLARIFICATION] Sent menu to {phone}")
    except Exception as e:
        logger.error(f"Failed to send clarification menu: {e}")


def process_clarification_response(
    phone: str,
    clarification_choice: str,  # "1", "2", "3", or "4"
    gap_id: str,
) -> str:
    """
    Customer responded to clarification menu.
    Update knowledge gap with clarification.
    Returns detected intent.
    """
    
    clarification_map = {
        "1": "product_search",
        "2": "usage_question",
        "3": "recipe_question",
        "4": "health_question",
    }
    
    intent = clarification_map.get(clarification_choice, "unknown")
    
    try:
        conn = get_db_connection()
        
        # Store the clarification choice
        current_clarifications = conn.execute(
            "SELECT clarifications FROM knowledge_gaps WHERE id = ?",
            (gap_id,)
        ).fetchone()
        
        clarifications = []
        if current_clarifications and current_clarifications[0]:
            clarifications = json.loads(current_clarifications[0])
        
        clarifications.append({
            "choice": clarification_choice,
            "intent": intent,
            "at": datetime.now(timezone.utc).isoformat()
        })
        
        conn.execute(
            """
            UPDATE knowledge_gaps
            SET clarifications = ?, detected_intent = ?
            WHERE id = ?
            """,
            (json.dumps(clarifications), intent, gap_id),
        )
        conn.commit()
        logger.info(f"[GAP-CLARIFIED] {phone} chose {clarification_choice} → {intent}")
        return intent
    except Exception as e:
        logger.error(f"Failed to process clarification: {e}")
        return "unknown"


def mark_gap_resolved(
    gap_id: str,
    resolved_by: str,  # "human" | "training_update" | "ai_fallback"
    final_answer: str = "",
) -> None:
    """Mark knowledge gap as resolved"""
    try:
        conn = get_db_connection()
        conn.execute(
            """
            UPDATE knowledge_gaps
            SET resolved_by = ?, final_answer = ?, resolved_at = ?
            WHERE id = ?
            """,
            (
                resolved_by,
                final_answer,
                datetime.now(timezone.utc).isoformat(),
                gap_id,
            ),
        )
        conn.commit()
        logger.info(f"[GAP-RESOLVED] {gap_id} by {resolved_by}")
    except Exception as e:
        logger.error(f"Failed to mark gap resolved: {e}")


def log_missing_product(product_query: str, clarification: str = "") -> None:
    """
    Customer asked for product we don't have.
    Track for monthly product research.
    """
    try:
        conn = get_db_connection()
        
        # Check if already tracked
        existing = conn.execute(
            "SELECT search_count FROM missing_products WHERE product_name = ?",
            (product_query,)
        ).fetchone()
        
        if existing:
            # Increment counter
            search_count = existing[0] + 1
            clarifications = conn.execute(
                "SELECT clarifications FROM missing_products WHERE product_name = ?",
                (product_query,)
            ).fetchone()[0]
            
            if clarifications:
                clar_list = json.loads(clarifications)
            else:
                clar_list = []
            
            if clarification:
                clar_list.append(clarification)
            
            conn.execute(
                """
                UPDATE missing_products
                SET search_count = ?, clarifications = ?, last_searched = ?
                WHERE product_name = ?
                """,
                (search_count, json.dumps(clar_list), datetime.now(timezone.utc).isoformat(), product_query),
            )
        else:
            # New unknown product
            clar_list = [clarification] if clarification else []
            conn.execute(
                """
                INSERT INTO missing_products
                (product_name, search_count, last_searched, clarifications, created_at)
                VALUES (?, 1, ?, ?, ?)
                """,
                (
                    product_query,
                    datetime.now(timezone.utc).isoformat(),
                    json.dumps(clar_list),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        
        conn.commit()
        logger.warning(f"[MISSING-PRODUCT] {product_query}")
    except Exception as e:
        logger.error(f"Failed to log missing product: {e}")


def get_unresolved_gaps(limit: int = 20) -> list[dict[str, Any]]:
    """Get unresolved knowledge gaps for human review"""
    try:
        conn = get_db_connection()
        rows = conn.execute(
            """
            SELECT id, phone, original_query, clarifications, detected_intent, created_at
            FROM knowledge_gaps
            WHERE resolved_by IS NULL
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        
        result = []
        for row in rows:
            result.append({
                "id": row[0],
                "phone": row[1],
                "query": row[2],
                "clarifications": json.loads(row[3]) if row[3] else [],
                "intent": row[4],
                "created": row[5],
            })
        return result
    except Exception as e:
        logger.error(f"Failed to get gaps: {e}")
        return []


def get_missing_products_report(limit: int = 20) -> list[dict[str, Any]]:
    """Get top missing products for research"""
    try:
        conn = get_db_connection()
        rows = conn.execute(
            """
            SELECT product_name, search_count, last_searched, clarifications, added_to_catalog
            FROM missing_products
            WHERE added_to_catalog = 0
            ORDER BY search_count DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        
        result = []
        for row in rows:
            result.append({
                "product": row[0],
                "searches": row[1],
                "last_searched": row[2],
                "clarifications": json.loads(row[3]) if row[3] else [],
                "action": "Add to catalog" if row[1] >= 5 else "Monitor",
            })
        return result
    except Exception as e:
        logger.error(f"Failed to get missing products: {e}")
        return []
