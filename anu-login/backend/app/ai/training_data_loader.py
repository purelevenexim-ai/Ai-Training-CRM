"""
Training Data Loader - Load and use trained responses for better AI replies

Loads CHATBOT_TRAINING_DATA_CLEANED.json and matches customer input to trained responses
"""

import json
import logging
import re
from typing import Any, Optional
from pathlib import Path
from difflib import SequenceMatcher

from app.ai.pricing_formatter import PricingFormatter

logger = logging.getLogger(__name__)

# Training data cache (loaded on first use)
_TRAINING_DATA: Optional[list[dict[str, Any]]] = None

PRODUCT_CATEGORY_PRIORITY = {
    "availability": 4,
    "price": 4,
    "details": 3,
    "quality": 3,
    "origin": 2,
    "processing": 2,
    "usage": 2,
    "benefits": 2,
    "best_pack": 2,
    "budget": 2,
    "combo": 2,
    "comparison": 1,
    "price_objection": 1,
    "delivery_charge": 1,
    "delivery_time": 1,
    "free_delivery": 1,
    "order_request": 2,
    "order_confirm": 2,
    "wholesale": 1,
    "gift": 1,
    "stock_check": 1,
    "complaint": -4,
    "return_refund": -4,
    "followup": 0,
    "negation": -2,
    "human_handoff": -1,
    "business_info": -1,
    "payment": 1,
    "fallback": -1,
    "price_check": 4,
    "product_inquiry": 3,
    "order_placement": 2,
    "payment_query": 2,
    "delivery_query": 1,
    "wholesale_inquiry": 1,
    "complaint": -4,
    "other": -2,
    "general": -1,
}

PRODUCT_VARIATIONS = PricingFormatter.get_product_alias_map()


def _normalize_lookup_text(value: str) -> str:
    """Normalize text for typo-tolerant product lookup."""
    return re.sub(r"[^a-z0-9\u0d00-\u0d7f]+", " ", (value or "").lower()).strip()


def _tokenize_lookup_text(value: str) -> list[str]:
    return [token for token in _normalize_lookup_text(value).split() if token]


def _alias_match_score(message: str, alias: str) -> float:
    """Return a similarity score for alias matching against a customer message."""
    msg_norm = _normalize_lookup_text(message)
    alias_norm = _normalize_lookup_text(alias)
    if not msg_norm or not alias_norm:
        return 0.0

    if alias_norm in msg_norm:
        return 1.0

    msg_tokens = _tokenize_lookup_text(message)
    alias_tokens = _tokenize_lookup_text(alias)

    if not msg_tokens or not alias_tokens:
        return 0.0

    best_score = SequenceMatcher(None, msg_norm, alias_norm).ratio()

    if len(alias_tokens) == 1:
        for token in msg_tokens:
            best_score = max(best_score, SequenceMatcher(None, token, alias_tokens[0]).ratio())
    else:
        alias_joined = " ".join(alias_tokens)
        window_size = len(alias_tokens)
        for start in range(0, max(1, len(msg_tokens) - window_size + 1)):
            window = " ".join(msg_tokens[start:start + window_size])
            best_score = max(best_score, SequenceMatcher(None, window, alias_joined).ratio())

    return best_score


def _find_product_mentions(message: str, threshold: float = 0.84) -> list[tuple[int, str]]:
    """Return fuzzy product mentions as (approximate_index, canonical_product)."""
    msg_norm = _normalize_lookup_text(message)
    msg_tokens = _tokenize_lookup_text(message)
    found: list[tuple[int, str]] = []

    for variation, canonical in PRODUCT_VARIATIONS.items():
        variation_norm = _normalize_lookup_text(variation)
        if not variation_norm:
            continue

        index = msg_norm.find(variation_norm)
        if index != -1:
            found.append((index, canonical))
            continue

        score = _alias_match_score(message, variation)
        if score < threshold:
            continue

        alias_tokens = _tokenize_lookup_text(variation)
        if not alias_tokens:
            continue

        if len(alias_tokens) == 1:
            for token_index, token in enumerate(msg_tokens):
                if SequenceMatcher(None, token, alias_tokens[0]).ratio() >= threshold:
                    found.append((token_index, canonical))
                    break
        else:
            window_size = len(alias_tokens)
            alias_joined = " ".join(alias_tokens)
            best_index = None
            best_window_score = threshold
            for start in range(0, max(1, len(msg_tokens) - window_size + 1)):
                window_tokens = msg_tokens[start:start + window_size]
                window = " ".join(window_tokens)
                window_score = SequenceMatcher(None, window, alias_joined).ratio()
                if window_score >= best_window_score:
                    best_window_score = window_score
                    best_index = start
            if best_index is not None:
                found.append((best_index, canonical))

    return found

def _training_data_paths() -> list[Path]:
    """
    Return candidate locations for the cleaned training artifact.

    The file may exist:
    - beside the repo root when running locally
    - under /opt/pureleven/ai-engine on the server
    - under /opt/pureleven/ai-engine/app in older deployments
    """
    resolved = Path(__file__).resolve()
    candidates = []

    # Walk up the directory tree so both local and server layouts are covered.
    for parent in resolved.parents:
        candidates.append(parent / "WHATSAPP_INTENT_KNOWLEDGE_BASE.json")
        candidates.append(parent / "CHATBOT_TRAINING_DATA_CLEANED.json")
        candidates.append(parent / "app" / "CHATBOT_TRAINING_DATA_CLEANED.json")

    candidates.extend(
        [
            Path("/opt/pureleven/ai-engine/WHATSAPP_INTENT_KNOWLEDGE_BASE.json"),
            Path("/opt/pureleven/ai-engine/CHATBOT_TRAINING_DATA_CLEANED.json"),
            Path("/opt/pureleven/ai-engine/app/CHATBOT_TRAINING_DATA_CLEANED.json"),
            Path("/WHATSAPP_INTENT_KNOWLEDGE_BASE.json"),
            Path.cwd() / "WHATSAPP_INTENT_KNOWLEDGE_BASE.json",
            Path("/CHATBOT_TRAINING_DATA_CLEANED.json"),
            Path.cwd() / "CHATBOT_TRAINING_DATA_CLEANED.json",
            Path.cwd() / "app" / "CHATBOT_TRAINING_DATA_CLEANED.json",
        ]
    )

    seen: set[str] = set()
    unique_candidates: list[Path] = []
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(candidate)

    return unique_candidates


def load_training_data() -> list[dict[str, Any]]:
    """Load training data from JSON file"""
    global _TRAINING_DATA
    
    if _TRAINING_DATA is not None:
        return _TRAINING_DATA
    
    try:
        # Try each possible path
        for path in _training_data_paths():
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    raw_payload = json.load(f)
                _TRAINING_DATA = [
                    _normalize_training_entry(entry)
                    for entry in raw_payload
                    if isinstance(entry, dict)
                ]
                logger.info(f"Loaded {len(_TRAINING_DATA)} training entries from {path}")
                return _TRAINING_DATA
        
        logger.warning(f"Training data file not found in any of: {_training_data_paths()}")
        return []
    except Exception as e:
        logger.error(f"Error loading training data: {e}")
        return []


def _normalize_training_entry(entry: dict[str, Any]) -> dict[str, Any]:
    trigger_examples = entry.get("trigger_examples") or entry.get("examples") or []
    if isinstance(trigger_examples, str):
        trigger_examples = [segment.strip() for segment in trigger_examples.splitlines()]
    if not isinstance(trigger_examples, list):
        trigger_examples = []

    customer_input = str(
        entry.get("customer_input")
        or entry.get("question")
        or (trigger_examples[0] if trigger_examples else "")
    ).strip()

    input_variations = entry.get("input_variations") or []
    if isinstance(input_variations, str):
        input_variations = [segment.strip() for segment in input_variations.replace("\n", ",").split(",")]
    if not isinstance(input_variations, list):
        input_variations = []

    for example in trigger_examples[1:]:
        if isinstance(example, str) and example.strip():
            input_variations.append(example.strip())

    seen_variations: set[str] = set()
    normalized_variations: list[str] = []
    for item in input_variations:
        text = str(item or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen_variations or key == customer_input.lower():
            continue
        seen_variations.add(key)
        normalized_variations.append(text)

    return {
        **entry,
        "product": str(entry.get("product") or entry.get("product_key") or "general").strip(),
        "category": str(entry.get("category") or entry.get("intent") or "general").strip(),
        "intent": str(entry.get("intent") or entry.get("category") or "general").strip(),
        "customer_input": customer_input,
        "input_variations": normalized_variations,
        "ideal_response": str(entry.get("ideal_response") or entry.get("answer_primary") or entry.get("answer") or "").strip(),
        "trigger_examples": [customer_input, *normalized_variations] if customer_input else normalized_variations,
        "answer_primary": str(entry.get("answer_primary") or entry.get("ideal_response") or entry.get("answer") or "").strip(),
    }


def reset_training_data_cache() -> None:
    """Clear the in-memory training data cache so dashboard edits take effect."""
    global _TRAINING_DATA
    _TRAINING_DATA = None


def similarity_score(s1: str, s2: str) -> float:
    """Calculate similarity between two strings (0-1)"""
    if not s1 or not s2:
        return 0.0
    s1_lower = s1.lower().strip()
    s2_lower = s2.lower().strip()
    return SequenceMatcher(None, s1_lower, s2_lower).ratio()


def find_best_match(customer_message: str, threshold: float = 0.6) -> Optional[dict[str, Any]]:
    """
    Find the best matching training entry for customer message.
    
    Args:
        customer_message: Customer's input text
        threshold: Minimum similarity score (0-1)
        
    Returns:
        Best matching training entry or None
    """
    training_data = load_training_data()
    if not training_data:
        return None
    
    best_match = None
    best_score = threshold
    
    # Check direct customer inputs
    for entry in training_data:
        score = similarity_score(customer_message, entry.get("customer_input", ""))
        if score > best_score:
            best_score = score
            best_match = entry
        
        # Also check variations
        for variation in entry.get("input_variations", []):
            score = similarity_score(customer_message, variation)
            if score > best_score:
                best_score = score
                best_match = entry
    
    if best_match:
        logger.info(
            f"Found training match: category={best_match.get('category')}, "
            f"product={best_match.get('product')}, score={best_score:.2f}"
        )
    
    return best_match


def find_product_response(
    product_name: str,
    customer_message: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Find training data for a specific product.
    
    Args:
        product_name: Name of product (e.g., "black pepper", "cardamom")
        
    Returns:
        Training entry with product info or None
    """
    training_data = load_training_data()
    product_lower = product_name.lower().strip()

    def score_entry(entry: dict[str, Any]) -> float:
        score = 0.0
        entry_product = entry.get("product", "")
        if entry_product:
            score += similarity_score(product_name, entry_product)
        if customer_message:
            score += similarity_score(customer_message, entry.get("customer_input", "")) * 0.4
        score += PRODUCT_CATEGORY_PRIORITY.get(entry.get("category", ""), 0) * 0.07
        if entry.get("needs_review"):
            score -= 0.15
        response_text = entry.get("ideal_response", "")
        if response_text and "₹" in response_text:
            score += 0.05
        if entry.get("category") in {"price_check", "product_inquiry"}:
            score += 0.05
        return score

    exact_matches = [
        entry for entry in training_data
        if entry.get("product", "").lower() == product_lower
    ]
    if exact_matches:
        return max(exact_matches, key=score_entry)

    # Fallback to a ranked fuzzy match. Prefer useful product/price entries
    # over complaints or generic support replies.
    best_match = None
    best_score = 0.55

    for entry in training_data:
        entry_product = entry.get("product", "")
        if not entry_product:
            continue

        score = score_entry(entry)
        if score > best_score:
            best_score = score
            best_match = entry

    return best_match


def get_product_catalog() -> dict[str, list[dict[str, Any]]]:
    """
    Get organized product catalog from training data.
    
    Returns:
        Dict mapping product name to list of relevant training entries
    """
    training_data = load_training_data()
    catalog = {}
    
    for entry in training_data:
        product = entry.get("product", "general")
        if product not in catalog:
            catalog[product] = []
        catalog[product].append(entry)
    
    return catalog


def is_greeting(message: str) -> bool:
    """Check if message is a standalone greeting, not a mixed product query."""
    greetings = ("hi", "hello", "hey", "namaste", "greetings", "sup", "hola", "bonjour", "hai", "ഹായ്")
    msg_lower = (message or "").lower().strip()
    if not msg_lower:
        return False

    if not (msg_lower in greetings or any(msg_lower.startswith(f"{g} ") or msg_lower.startswith(f"{g}!") or msg_lower.startswith(f"{g},") for g in greetings)):
        return False

    # If the message also mentions a product, let product routing win.
    if extract_product_mention(msg_lower):
        return False

    # Keep greeting handling focused on short openings.
    return len(msg_lower.split()) <= 4


def extract_product_mention(message: str) -> Optional[str]:
    """
    Extract product name from customer message.
    Maps variations to canonical product names.
    
    Args:
        message: Customer message
        
    Returns:
        Product name or None
    """
    matches = _find_product_mentions(message)
    if matches:
        return matches[0][1]

    msg_lower = (message or "").lower().strip()

    # Fallback: check for any product match in the training data labels.
    training_data = load_training_data()
    if not training_data:
        return None

    products = set(entry.get("product") for entry in training_data if entry.get("product"))
    for product in products:
        product_lower = product.lower().strip()
        if product_lower and product_lower in msg_lower:
            return product

    return None


def extract_product_mentions(message: str) -> list[str]:
    """Extract every product mention in first-seen order."""
    found = _find_product_mentions(message)

    ordered: list[str] = []
    for _, canonical in sorted(found, key=lambda item: item[0]):
        if canonical not in ordered:
            ordered.append(canonical)

    return ordered


def get_greeting_response(
customer_name: str = "Customer") -> str:
    """Generate a warm greeting response"""
    greeting_responses = [
        f"Hey {customer_name}! 👋 Welcome to PureLeven. How can I help you today?",
        f"Hi {customer_name}! 🌿 Thanks for reaching out! What can I help you with?",
        f"Hello {customer_name}! Welcome! 😊 Looking for some fresh spices?",
    ]
    import random
    return random.choice(greeting_responses)
