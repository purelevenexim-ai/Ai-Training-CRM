"""Flow Helpers - Support for flow abandonment detection

Provides utilities for:
- Flow option matching (fuzzy, handles variations)
- Product intent detection (recognizes product keywords)
- Flow abandonment logging
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List

logger = logging.getLogger(__name__)


def flow_match(message: str, expected_options: List[str]) -> bool:
    """
    Does message contain any of the expected flow options?
    
    Handles variations:
    - "English please" matches "english"
    - "ENGLISH" matches "english"
    - "1" matches "1"
    
    Args:
        message: Customer's message
        expected_options: What the flow expects (e.g., ["english", "malayalam", "1", "2"])
        
    Returns:
        True if message contains one of the options, False otherwise
    """
    normalized = message.lower().strip()
    
    for option in expected_options:
        option_lower = option.lower().strip()
        if option_lower in normalized:
            return True
    
    return False


def has_product_intent(message: str) -> bool:
    """
    Does message clearly request a product?
    
    Recognizes:
    - "Cardamom"
    - "Black pepper"
    - "I need cardamom"
    - "Sesame oil price"
    
    But NOT:
    - "English" (language selection)
    - "How are you?"
    
    Args:
        message: Customer's message
        
    Returns:
        True if message contains product keyword, False otherwise
    """
    PRODUCT_KEYWORDS = [
        "cardamom", "cardamom", "elaichi", "elakka",
        "black pepper", "pepper", "மிरियา", "mirch",
        "cinnamon", "cinamon", "कस्टर", "पट्ट",
        "clove", "laung", "ग्रामपू",
        "turmeric", "haldi", "மஞ்ஜள்",
        "sesame", "til", "sesame oil",
        "ginger", "adrak", "சுக்கு",
        "cumin", "jeera", "சீரகம்",
        "nutmeg", "jaiphal",
        "anise", "saunf", "விளாயிதै",
        "fenugreek", "methi",
        "chilli", "mirch",
        "oil", "coconut", "mustard"
    ]
    
    normalized = message.lower().strip()
    return any(kw in normalized for kw in PRODUCT_KEYWORDS)


def log_flow_abandoned(
    phone: str,
    flow_name: str,
    reason: str,
    expected_options: List[str] = None,
    received_message: str = None,
) -> None:
    """
    Log flow abandonment event for audit trail.
    
    Args:
        phone: Customer phone
        flow_name: Name of flow that was abandoned (e.g., "language_selection")
        reason: Why it was abandoned (e.g., "product_intent_override", "unrelated_input")
        expected_options: What flow was expecting
        received_message: What customer actually sent
    """
    from app.storage import get_db_connection
    
    # Log to application logger
    logger.info(
        f"[FLOW-ABANDONED] "
        f"phone={phone} "
        f"flow={flow_name} "
        f"reason={reason} "
        f"expected={expected_options} "
        f"received={received_message}"
    )
    
    # Also save to database for analysis
    try:
        conn = get_db_connection()
        audit_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        expected_str = ",".join(expected_options) if expected_options else None

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS flow_audit (
                id TEXT PRIMARY KEY,
                phone TEXT NOT NULL,
                flow_name TEXT NOT NULL,
                abandonment_reason TEXT NOT NULL,
                expected_options TEXT,
                received_message TEXT,
                final_route TEXT,
                timestamp TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            INSERT INTO flow_audit 
            (id, phone, flow_name, abandonment_reason, expected_options, received_message, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (audit_id, phone, flow_name, reason, expected_str, received_message, now),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to log flow abandonment to database: {e}")
