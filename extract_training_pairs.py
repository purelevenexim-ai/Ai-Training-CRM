"""
extract_training_pairs.py
=========================
Extracts WhatsApp chat Q&A pairs from customer_chats/ and customer_chats_v2/
and outputs clean JSON training data for the PureLeven chatbot.

Usage:
    python extract_training_pairs.py
Output:
    CHATBOT_TRAINING_DATA.json
"""

import csv
import json
import os
import re
import ast
from pathlib import Path

BASE_DIRS = ["customer_chats", "customer_chats_v2"]
OUTPUT_FILE = "CHATBOT_TRAINING_DATA.json"

# ── Patterns ──────────────────────────────────────────────────────────────────

# Keywords that signal a spice/product conversation worth keeping
SPICE_KW = re.compile(
    r"(cinnamon|patta|karuvapatta|karuvappatta|karuv|കറുവ|cardamom|cardamon|elakka|ഏലക്ക|"
    r"grampoo|ഗ്രാമ്പൂ|clove|pepper|kurumul|കുരുമുളക്|turmeric|manjal|manjal|"
    r"combo|spice|kilo|price|rate|cost|order|delivery|ship|cod|wholesale|bulk|"
    r"payment|gpay|stock|available|undo|indo|theer|theern|kg|grams?|gm)",
    re.I,
)

# Skip pure greetings with no spice intent
GREETING_ONLY = re.compile(
    r"^\s*(hi|hello|hallo|namaskaram|namaskar|good (morning|evening|afternoon)|"
    r"ok|okay|k|thanks?|thank you|👍|🙏|yes|no|sure|hmm|seen)\s*$",
    re.I,
)

# Bot auto-welcome messages that should NOT be used as ideal_response
CANNED_WELCOME = re.compile(
    r"(👋Hello! Welcome to PureLeven|Choose Your Language|🌍|Welcome to Pure Leven ✨|Namaskaaram|Namaskaram.*PureLeven)",
    re.I,
)

# Category rules (checked in order, first match wins)
CATEGORY_RULES = [
    ("wholesale_inquiry",  re.compile(r"wholesale|bulk|reseller|dealer|stockist|business rate|business price", re.I)),
    ("complaint",          re.compile(r"not received|not delivered|wrong|damage|refund|missing|delay|complaint|problem|issue|cheat|fake", re.I)),
    ("delivery_query",     re.compile(r"delivery|ship|courier|parcel|track|when.*arrive|how.*long|days?|dispatch|post", re.I)),
    ("payment_query",      re.compile(r"payment|paid|gpay|google pay|cod|cash on delivery|transfer|upi|account|advance|screenshot", re.I)),
    ("order_placement",    re.compile(r"want|order|send|dispatch|book|confirm|address|pin ?code|quantity|pack|need \d+|venam|tharamo|ayakumo", re.I)),
    ("price_check",        re.compile(r"price|rate|cost|how much|ethra|vila|₹|\d+\s?gm?|\d+\s?kg|combo|offer", re.I)),
    ("product_inquiry",    re.compile(r"available|stock|undo|indo|theer|info|details|grade|quality|original|ceylon|export|8\.5|mm|pure|natural|organic", re.I)),
]


def categorise(text: str) -> str:
    for cat, rx in CATEGORY_RULES:
        if rx.search(text):
            return cat
    return "other"


def detect_language(text: str) -> str:
    # Malayalam Unicode block: 0D00–0D7F
    mal_chars = sum(1 for c in text if "\u0D00" <= c <= "\u0D7F")
    if mal_chars >= 3:
        return "malayalam"
    # Mixed (contains both English words and Malayalam)
    if mal_chars >= 1:
        return "mixed"
    return "english"


def extract_text(raw: str) -> str:
    """
    Normalise a raw message cell which may be:
    - plain text
    - a Python-dict-like string {'text': {'body': '...'}}
    - an HTML-polluted Wabis livechat export
    """
    raw = raw.strip()
    if not raw:
        return ""

    # v1 export sometimes prepends "FirstName LastName " before the actual message
    # e.g.  "Kishore Kumar What is the wholesale price?"
    # Strip leading "Firstname Lastname " if it looks like a name prefix.
    raw = re.sub(r"^[A-Z][a-z]+ [A-Z][a-z]+ ", "", raw)

    # Try to parse as Python dict literal (v2 format)
    if raw.startswith("{") and "'body'" in raw:
        try:
            obj = ast.literal_eval(raw)
            body = (
                obj.get("text", {}).get("body")
                or obj.get("interactive", {}).get("body", {}).get("text")
                or ""
            )
            if body:
                return body.strip()
        except Exception:
            pass
        # Fallback: grab body value with regex
        m = re.search(r"'body'\s*:\s*'([^']+)'", raw)
        if m:
            return m.group(1).strip()

    # Strip HTML tags and Wabis footer (e.g. " --> <i class=..." or " <span ...")
    text = re.sub(r"\s*-->\s*<.*", "", raw, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&[a-z]+;", " ", text)          # HTML entities
    text = re.sub(r"\s*-\s*Bot\s*$", "", text, flags=re.I)  # trailing "- Bot" timestamp
    text = re.sub(r"\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}\s*[AP]M.*$", "", text, flags=re.I)
    # strip "▶ Ad ... View details" ad prefix from v1 exports
    text = re.sub(r"▶.*?View details\s*", "", text, flags=re.DOTALL)
    return text.strip()


def clean_response(text: str) -> str:
    """Light cleanup for agent/bot replies used as ideal_response."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def is_skip_worthy(text: str) -> bool:
    """True if the customer message should be ignored."""
    if not text or len(text) < 6:
        return True
    if GREETING_ONLY.match(text):
        return True
    # Skip if clearly an address block with no question
    if re.match(r"^[\w\s,./-]+\d{6}[\w\s]*$", text) and "?" not in text:
        return True
    # Skip HTML artifact leftovers like "-->" or "🍃 Spices Price -->"
    if re.fullmatch(r"[\s\-–—>◀▶🍃⬅➡]+", text):
        return True
    # Skip if it ends with --> (Wabis button-tap artifact)
    # e.g. "🍃 Spices Price -->" or "Payment -->"
    if text.rstrip().endswith("-->") or text.rstrip().endswith("-- >"):
        stripped = re.sub(r"-->.*$", "", text).strip()
        # Only keep if there is genuine spice content before the arrow
        if not SPICE_KW.search(stripped) or len(stripped) < 10:
            return True
    # Skip pure address blocks (name + address with pin and no spice keyword)
    if SPICE_KW.search(text) is None and re.search(r"\d{6}", text):
        return True
    # Skip rows that are just a name label plus an artifact
    if re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+\s+(-->|<|🍃|\?|👍)", text):
        return True
    return False


# ── Conversation reader ────────────────────────────────────────────────────────

def rows_from_csv(path: str):
    """
    Yield (sender, text) tuples from a chat CSV.
    Both v1 and v2 schemas are supported.
    """
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 4:
                    continue
                # v1: [blank, sender, type, message, id, ...]
                # v2: [timestamp, sender, type, message, id, state]
                sender = row[1].strip().lower()
                raw_text = row[3]
                text = extract_text(raw_text)
                if text:
                    yield sender, text
    except Exception:
        return


def pair_messages(rows):
    """
    Slide through a conversation and yield (customer_text, agent_text) pairs.
    A customer turn may span several consecutive customer rows.
    The first non-customer row after those is the agent reply.
    """
    customer_buffer = []
    for sender, text in rows:
        is_customer = sender in {"customer", "user"}
        is_agent = sender in {"bot", "bot_agent", "admin", "agent", "system"}
        if is_customer:
            customer_buffer.append(text)
        elif is_agent and customer_buffer:
            combined_customer = " ".join(customer_buffer).strip()
            customer_buffer = []
            if combined_customer and text:
                yield combined_customer, text
            elif combined_customer:
                yield combined_customer, ""
        else:
            # Non-customer, non-agent row (system note etc.) — flush buffer
            if customer_buffer:
                combined_customer = " ".join(customer_buffer).strip()
                customer_buffer = []
                if combined_customer:
                    yield combined_customer, ""

    # Flush any trailing customer message with no reply
    if customer_buffer:
        yield " ".join(customer_buffer).strip(), ""


# ── Ideal-response generator ───────────────────────────────────────────────────

# Current price list (update when prices change)
PRICE_CARD = """
Ceylon Cinnamon (Original): 100g ₹320 + ₹40 delivery | 200g ₹560 free delivery | 500g ₹1400 free delivery
Cardamom 8.5mm A+ Export: 100g ₹460 + ₹40 | 200g ₹840 free | 500g ₹1799 free | 1kg ₹3350 free
Black Pepper (Idukki, washed): 250g ₹300 + ₹40 | 500g ₹540 free
Clove (Adimali): 100g ₹180 + ₹40 | 200g ₹340 free | 500g ₹649 free
Turmeric Powder: 100g ₹160 + ₹40 | 200g ₹300 free
Combo – 100g Cardamom + 100g Cinnamon: ₹699 free delivery
Combo – 100g Cardamom + 100g Clove: ₹560 free delivery
Combo – 100g Cardamom + 200g Pepper: ₹640 free delivery
""".strip()

STOCK_OUT_REPLY_EN = (
    "Cinnamon (Patta) is currently out of stock. "
    "We'll notify you as soon as the next batch arrives. "
    "Would you like to pre-book?"
)
STOCK_OUT_REPLY_ML = (
    "ഇപ്പോൾ കറുവപ്പട്ട (Patta) stock തീർന്നിരിക്കുന്നു. "
    "Stock വന്നാൽ ഉടൻ അറിയിക്കാം. Pre-book ചെയ്യണോ?"
)
PAYMENT_REPLY = (
    "Please send payment via Google Pay to 8075519579 (PureLeven Exim). "
    "After payment, share a screenshot here so we can dispatch your order."
)
DELIVERY_REPLY = (
    "We dispatch within 1-2 business days via India Post / courier. "
    "Delivery usually takes 3-7 days depending on your location. "
    "We'll share a tracking number once dispatched."
)
WHOLESALE_REPLY = (
    "For wholesale / bulk orders, please share your requirements (product, quantity, location). "
    "We offer special rates for businesses and regular bulk buyers."
)


def ideal_response(customer_input: str, agent_reply: str, category: str) -> str:
    """
    Return the best possible response:
    - If agent replied well (>10 chars, not a broken payload), clean and use it.
    - Otherwise, generate a standard response based on category and keywords.
    """
    agent_clean = clean_response(agent_reply) if agent_reply else ""

    # Agent reply is acceptable if it has real content AND is not a canned welcome
    if (len(agent_clean) > 20
            and not agent_clean.startswith("{")
            and "bot-data.s3" not in agent_clean
            and not CANNED_WELCOME.search(agent_clean)):
        return agent_clean

    # Generate a good fallback
    inp = customer_input.lower()

    if category == "payment_query":
        return PAYMENT_REPLY

    if category == "delivery_query":
        return DELIVERY_REPLY

    if category == "wholesale_inquiry":
        return WHOLESALE_REPLY

    if category == "complaint":
        return (
            "We're sorry to hear that. Could you please share your order details "
            "(order date, address, and what was ordered)? We'll investigate and resolve this promptly."
        )

    stock_match = re.search(r"(indo|undo|available|stock|theer|ഉണ്ടോ|ഉണ്ട്)", inp)
    if stock_match:
        if "patta" in inp or "cinnamon" in inp or "karuv" in inp or "കറുവ" in inp:
            lang = detect_language(customer_input)
            return STOCK_OUT_REPLY_ML if lang in ("malayalam", "mixed") else STOCK_OUT_REPLY_EN
        return (
            "Yes, we currently have all products in stock: Ceylon Cinnamon, "
            "Cardamom (8.5mm A+), Black Pepper, Clove, and Turmeric. "
            "Which product are you looking for?"
        )

    if category == "price_check":
        return (
            f"Here are our current prices:\n{PRICE_CARD}\n\n"
            "Free delivery on 200g packs and all combos. "
            "What would you like to order?"
        )

    if category == "product_inquiry":
        if "cardamom" in inp or "elakka" in inp or "ഏലക്ക" in inp:
            return (
                "Our Cardamom is Export Grade 8.5mm A+ from Idukki, Kerala — "
                "70-80% fruit content, sun-dried, no chemicals. "
                "100g ₹460 + ₹40 delivery | 200g ₹840 free delivery | 500g ₹1799 free delivery. "
                "Would you like to place an order?"
            )
        if "cinnamon" in inp or "patta" in inp or "karuv" in inp or "കറുവ" in inp:
            return (
                "We sell Original Ceylon Cinnamon (C5 grade) — true cinnamon, not cassia. "
                "Sourced directly from Sri Lanka, hand-packed fresh. "
                "100g ₹320 + ₹40 | 200g ₹560 free delivery | 500g ₹1400 free delivery. "
                "Combo: 100g Cardamom + 100g Cinnamon = ₹699 free delivery."
            )
        return (
            "We offer fresh Kerala spices sourced directly from farms: "
            "Ceylon Cinnamon, Cardamom (8.5mm A+), Black Pepper, Clove, and Turmeric. "
            "All products are 100% natural with no additives. "
            "Which product are you interested in?"
        )

    if category == "order_placement":
        return (
            "Sure! Please share your: full name, delivery address, PIN code, and phone number. "
            "Also confirm which products and quantities you'd like. "
            "We'll confirm the total and share payment details."
        )

    return (
        "Thank you for reaching out to PureLeven! "
        "We sell fresh Kerala spices: Ceylon Cinnamon, Cardamom, Black Pepper, Clove, and Turmeric. "
        "How can we help you today?"
    )


# ── Main extraction loop ───────────────────────────────────────────────────────

def main():
    results = []
    seen = set()  # deduplicate by (customer_input, category) pairs

    for base in BASE_DIRS:
        if not os.path.isdir(base):
            print(f"[SKIP] directory not found: {base}")
            continue

        csv_files = list(Path(base).rglob("*.csv"))
        print(f"[INFO] {base}: {len(csv_files)} CSV files")

        for path in csv_files:
            rows = list(rows_from_csv(str(path)))
            for customer_input, agent_reply in pair_messages(rows):

                # Skip pure greetings or empty messages
                if is_skip_worthy(customer_input):
                    continue

                # Only keep spice-related turns
                if not SPICE_KW.search(customer_input) and not SPICE_KW.search(agent_reply):
                    continue

                category = categorise(customer_input)
                language = detect_language(customer_input)
                ideal = ideal_response(customer_input, agent_reply, category)

                # Deduplicate
                key = (category, customer_input[:80])
                if key in seen:
                    continue
                seen.add(key)

                results.append({
                    "category": category,
                    "customer_input": customer_input,
                    "ideal_response": ideal,
                    "language": language,
                })

    # Sort by category for readability
    results.sort(key=lambda x: (x["category"], x["language"]))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[DONE] {len(results)} training pairs written to {OUTPUT_FILE}")

    # Print category breakdown
    from collections import Counter
    cats = Counter(r["category"] for r in results)
    langs = Counter(r["language"] for r in results)
    print("\nCategory breakdown:")
    for cat, count in cats.most_common():
        print(f"  {cat:<25} {count}")
    print("\nLanguage breakdown:")
    for lang, count in langs.most_common():
        print(f"  {lang:<15} {count}")


if __name__ == "__main__":
    main()
