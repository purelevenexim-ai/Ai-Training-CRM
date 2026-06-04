"""Message Normalizer - Simplify input before routing

Converts variations of customer input to canonical intents.
Examples: hi, Hi, HI, hiii, hello, ഹായ്, hai → all become intent: "greeting"
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def normalize(message: str) -> str:
    """
    Normalize message text for intent detection.
    - Trim whitespace
    - Lowercase
    - Remove extra spaces
    """
    if not message:
        return ""
    
    normalized = message.strip().lower()
    # Remove extra spaces
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def detect_intent(normalized_message: str) -> str:
    """
    Detect intent from normalized message.
    Returns: greeting | order_status | product_search | complaint | faq | unknown
    """
    
    if not normalized_message:
        return "unknown"
    
    # Greetings (hi, hello, hiii, ഹായ്, etc.)
    greeting_patterns = [
        r'^\s*(hi|hey|hello|hii|hiii|hiiii|hola|namaste|ഹായ്|hai|assalam|vanakkam)\s*$',
        r'^\s*(good\s+(morning|afternoon|evening|night))\s*$',
        r'^\s*(what\'s\s+up|sup|yo)\s*$',
    ]
    for pattern in greeting_patterns:
        if re.search(pattern, normalized_message):
            return "greeting"
    
    # Order status tracking
    order_patterns = [
        r'(track|where|status|order|delivery|shipped|arrived)',
        r'(my\s+order|order\s+status|shipment|when)',
        r'(പ്രേഷണ|ഓർഡർ|കിട്ടിയോ|എങ്ങാനെ)',  # Malayalam
    ]
    for pattern in order_patterns:
        if re.search(pattern, normalized_message):
            return "order_status"
    
    # Product search
    product_patterns = [
        r'(price|cost|how\s+much|how\s+much|rupees|₹)',
        r'(black\s+pepper|cardamom|cinnamon|clove|oil)',
        r'(do\s+you\s+have|available|stock|buy)',
        r'(കുരുമുളക്|ഏലക്ക|കറുവാപ്പട്ട|കിലോ)',  # Malayalam spices
    ]
    for pattern in product_patterns:
        if re.search(pattern, normalized_message):
            return "product_search"
    
    # Complaints
    complaint_patterns = [
        r'(complaint|damaged|broken|issue|problem|wrong)',
        r'(poor\s+quality|expired|fake|not\s+good)',
        r'(refund|return|replace|money\s+back)',
        r'(പരാതി|തകരാറ്|വിഷമം|പ്രശ്നം)',  # Malayalam
    ]
    for pattern in complaint_patterns:
        if re.search(pattern, normalized_message):
            return "complaint"
    
    # FAQ - Payment, Shipping, Return
    faq_patterns = [
        r'(payment|cod|credit|debit|card)',
        r'(shipping|courier|india\s+post|delivery\s+time)',
        r'(return\s+policy|how\s+to\s+return|warranty)',
        r'(free\s+shipping|delivery\s+charges)',
    ]
    for pattern in faq_patterns:
        if re.search(pattern, normalized_message):
            return "faq"
    
    return "unknown"
