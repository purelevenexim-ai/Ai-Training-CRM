"""
clean_training_data.py
======================
Cleans and improves CHATBOT_TRAINING_DATA.json:

1. Detects the product for each entry (cardamom / cinnamon / pepper / clove /
   turmeric / combo / general)
2. Groups by (category × product) so every variant of the same question merges
   into a single canonical entry
3. Chooses the best ideal_response within each group (highest quality score)
4. Collects ALL real customer phrasings as input_variations
5. Appends 3 template paraphrases (English + Malayalam) not already present
6. Flags entries where the response is incomplete / wrong: needs_review + reason

Output: CHATBOT_TRAINING_DATA_CLEANED.json
"""

import html as _html
import json
import re
from collections import Counter, defaultdict

INPUT_FILE  = "CHATBOT_TRAINING_DATA.json"
OUTPUT_FILE = "CHATBOT_TRAINING_DATA_CLEANED.json"


# ── Product cluster detection ──────────────────────────────────────────────────

PRODUCT_PATTERNS = [
    ("cardamom", re.compile(r"cardamom|cardamon|elakka|ഏലക്ക|elkka", re.I)),
    ("cinnamon", re.compile(r"cinnamon|patta|karuvapatta|karuvappatta|karuv|കറുവ", re.I)),
    ("pepper",   re.compile(r"\bpepper\b|kurumul|kuru mul|കുരുമുളക്", re.I)),
    ("clove",    re.compile(r"\bclove\b|grampoo|grambu|ഗ്രാമ്പൂ", re.I)),
    ("turmeric", re.compile(r"turmeric|manjal|haldi|മഞ്ഞൾ", re.I)),
    ("combo",    re.compile(r"\bcombo\b|combo offer", re.I)),
]

def detect_product(text: str) -> str:
    for name, pat in PRODUCT_PATTERNS:
        if pat.search(text):
            return name
    return "general"


# ── Input quality helpers ──────────────────────────────────────────────────────

# Wabis button-tap artifact patterns
WABIS_ARTIFACT = re.compile(
    r"🍃|\u0d35\u0d3f\u0d32 \u0d15\u0d3e\u0d23\u0d02|Spices Price|-->|\d{1,2}:\d{2}\s*[AP]M"
    r"|Hello! Can I get mo|Can I get mo"
    r"|Hel+o!?\s+Can I"
)

def is_clean_input(text: str) -> bool:
    """Return True if text looks like a genuine customer message (strict)."""
    if len(text) < 8:
        return False
    if WABIS_ARTIFACT.search(text):
        return False
    # Any residual HTML (< covers tags, comments, incomplete tags)
    if "<" in text:
        return False
    # Wabis media / reply markers
    if re.search(r"\[Image:|\[Reply:|\[Video:|\[Audio:", text, re.I):
        return False
    # URLs
    if re.search(r"https?://|bot-data\.s3", text):
        return False
    # Pure delivery address with 6-digit pincode and no question/product
    if re.search(r"\b\d{6}\b", text) and not re.search(
            r"\?|price|rate|order|venam|want|undo|aano", text, re.I):
        return False
    return True


def is_acceptable_fallback(text: str) -> bool:
    """Looser filter used when no strictly-clean inputs exist in a cluster.
    Still blocks HTML, media markers, and URLs but allows Wabis artifacts."""
    if len(text) < 8:
        return False
    if "<" in text:
        return False
    if re.search(r"\[Image:|\[Reply:|\[Video:|\[Audio:", text, re.I):
        return False
    if re.search(r"https?://|bot-data\.s3", text):
        return False
    return True


def canonical_score(text: str) -> int:
    """Score a candidate canonical input. Higher = better."""
    score = 0
    if "?" in text:
        score += 50
    if SPICE_KW.search(text):          # noqa (defined below)
        score += 30
    l = len(text)
    if 12 <= l <= 70:
        score += 20
    elif l > 120:
        score -= 40     # penalise very long complaint-style text as canonical
    if not text.isupper():
        score += 5
    if not text.islower():
        score += 5
    return score


SPICE_KW = re.compile(
    r"cardamom|cinnamon|pepper|clove|turmeric|elakka|patta|kurumul|grampoo|"
    r"ഏലക്ക|കറുവ|കുരുമുളക്|ഗ്രാമ്പൂ|price|rate|order|delivery|payment",
    re.I,
)


# ── Text normalisation ─────────────────────────────────────────────────────────

def clean_text(raw: str) -> str:
    if not raw:
        return ""
    text = _html.unescape(raw)
    # Remove HTML comments first
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Remove Wabis arrow artifacts at end
    text = re.sub(r"\s*-->\s*$", "", text)
    # Remove trailing timestamps  "5/4/26 11:52 AM - Admin"
    text = re.sub(r"\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}\s*[AP]M.*$", "", text, flags=re.I)
    text = re.sub(r"\d{1,2}:\d{2}\s*(AM|PM)\s*-\s*(Bot|Admin)\s*$", "", text, flags=re.I)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Strip trailing stray HTML-start char
    text = re.sub(r"\s*<$", "", text).strip()
    return text


# ── Response quality score ─────────────────────────────────────────────────────

def response_score(response: str) -> int:
    if not response:
        return 0
    score = min(len(response), 800)
    if re.search(r"<[^>]+>|&[a-z]{2,6};", response):
        score -= 600
    if re.search(r"Choose Your Language|Welcome to PureLeven|Namaskaaram.*PureLeven",
                 response, re.I):
        score -= 600
    if re.search(r"\d{1,2}:\d{2}\s*(AM|PM)\s*-\s*(Bot|Admin)", response, re.I):
        score -= 300
    if "₹" in response:
        score += 150
    if re.search(r"free delivery|free dilivery", response, re.I):
        score += 50
    return score


# ── Needs-review detection ─────────────────────────────────────────────────────

def flag_review(category: str, customer_input: str, ideal_response: str) -> tuple[bool, str]:
    resp = ideal_response or ""
    inp  = customer_input or ""
    reasons: list[str] = []

    if len(resp) < 30:
        reasons.append("response_too_short")
    if re.search(r"<[^>]+>|&[a-z]{2,6};", resp):
        reasons.append("html_in_response")
    if re.search(r"<[^>]+>|&[a-z]{2,6};", inp):
        reasons.append("html_in_input")
    if re.search(r"Choose Your Language|Welcome to PureLeven", resp, re.I):
        reasons.append("canned_welcome_as_response")
    if re.search(r"\d{1,2}:\d{2}\s*(AM|PM)\s*-\s*(Bot|Admin)", resp, re.I):
        reasons.append("timestamp_in_response")
    if category == "complaint" and not re.search(
            r"sorry|resolve|check|detail|order|investigate", resp, re.I):
        reasons.append("complaint_not_properly_addressed")

    return bool(reasons), "; ".join(reasons)


# ── Paraphrase templates ───────────────────────────────────────────────────────
# 5 options per (category, product). Script picks 3 not already present in real data.

PARA_TEMPLATES: dict[tuple, list[str]] = {
    ("price_check", "cardamom"): [
        "Cardamom 100g price?",
        "Elakka rate ethra aanu?",
        "ഏലക്ക 500g ethra roopa?",
        "How much for 1kg cardamom?",
        "Elakka 200g cost?"
    ],
    ("price_check", "cinnamon"): [
        "Patta 100g rate?",
        "Karuvapatta price list?",
        "Ceylon cinnamon ethra?",
        "How much for 200g cinnamon?",
        "Cinnamon 500g price?"
    ],
    ("price_check", "pepper"): [
        "Black pepper 500g price?",
        "Kurumulaku kilo rate?",
        "How much for 250g pepper?",
        "Pepper rate list please?",
        "ഇടുക്കി കുരുമുളക് വില?"
    ],
    ("price_check", "clove"): [
        "Grampoo 100g price?",
        "Clove rate ethra?",
        "How much for 200g clove?",
        "Adimali clove rate?",
        "ഗ്രാമ്പൂ വില?"
    ],
    ("price_check", "turmeric"): [
        "Turmeric powder price?",
        "Manjal podi rate?",
        "How much for 200g turmeric?",
        "Lakadong turmeric price?",
        "Haldi price?"
    ],
    ("price_check", "combo"): [
        "What combo offers do you have?",
        "Combo price list please?",
        "Best spice combo pack?",
        "Elakka + patta combo price?",
        "ഓഫർ ഉണ്ടോ?"
    ],
    ("price_check", "general"): [
        "Full price list for all spices?",
        "All products rate list?",
        "Can you send your price list?",
        "All spice rates please?",
        "Rate list tharamo?"
    ],
    ("product_inquiry", "cardamom"): [
        "Is your cardamom export A+ grade?",
        "What size is your cardamom pods?",
        "Is the cardamom chemical-free?",
        "Elakka farm direct aano?",
        "Cardamom 8.5mm aano?"
    ],
    ("product_inquiry", "cinnamon"): [
        "Is it real Ceylon cinnamon or cassia?",
        "C5 grade patta aano?",
        "Original Sri Lanka cinnamon aano?",
        "Is your cinnamon organic?",
        "True cinnamon aano?"
    ],
    ("product_inquiry", "pepper"): [
        "Is it Idukki origin pepper?",
        "Washed and cleaned pepper aano?",
        "Is it organic black pepper?",
        "Black pepper quality details?",
        "Kurumulaku farm direct aano?"
    ],
    ("product_inquiry", "clove"): [
        "Is it Adimali origin clove?",
        "High oil content clove aano?",
        "Fresh grampoo aano?",
        "Clove quality details?",
        "Which estate is your clove from?"
    ],
    ("product_inquiry", "turmeric"): [
        "Is it Lakadong turmeric?",
        "Pure turmeric powder aano?",
        "Organic turmeric aano?",
        "Curcumin content details?",
        "Is it adulteration-free?"
    ],
    ("product_inquiry", "general"): [
        "What spices do you sell?",
        "Tell me about PureLeven products?",
        "Are your spices farm direct?",
        "What products are available?",
        "PureLeven products list?"
    ],
    ("order_placement", "cardamom"): [
        "I want to order 100g cardamom",
        "Elakka venam, order cheyyam",
        "Send me 200g cardamom",
        "Cardamom 500g order cheyam",
        "1 kg elakka venam"
    ],
    ("order_placement", "cinnamon"): [
        "I want 100g cinnamon",
        "Patta venam order cheyyam",
        "Ceylon cinnamon 200g order",
        "Send me cinnamon please",
        "Karuvapatta 500g order cheyam"
    ],
    ("order_placement", "pepper"): [
        "250g black pepper order cheyam",
        "Kurumulaku venam",
        "I want to buy pepper",
        "Send me 500g black pepper",
        "Pepper 1kg order"
    ],
    ("order_placement", "clove"): [
        "I want 100g clove",
        "Grampoo venam",
        "Send me 200g clove",
        "Clove order cheyam",
        "Adimali clove 100g venam"
    ],
    ("order_placement", "general"): [
        "I want to place an order",
        "How do I order from you?",
        "Order cheyyam, how to proceed?",
        "Can I buy spices from PureLeven?",
        "I want to buy spices"
    ],
    ("delivery_query", "general"): [
        "When will my order arrive?",
        "How many days for delivery?",
        "Dispatch cheyto? Tracking number?",
        "Delivery ethra divasam?",
        "Order status check cheyyam"
    ],
    ("payment_query", "general"): [
        "Can I pay via GPay?",
        "Is COD available?",
        "GPay number tharamo?",
        "What payment methods are accepted?",
        "Can I pay cash on delivery?"
    ],
    ("wholesale_inquiry", "cardamom"): [
        "Wholesale price for cardamom?",
        "Elakka bulk rate?",
        "Business rate for cardamom?",
        "5kg+ cardamom price?",
        "Cardamom dealer rate?"
    ],
    ("wholesale_inquiry", "cinnamon"): [
        "Cinnamon bulk rate?",
        "Patta wholesale price?",
        "Business rate for cinnamon?",
        "Karuvapatta dealer price?",
        "Ceylon cinnamon bulk order?"
    ],
    ("wholesale_inquiry", "general"): [
        "Wholesale price list?",
        "Bulk order rates?",
        "I am a reseller, what is your rate?",
        "Business pricing available?",
        "Dealer rate tharamo?"
    ],
    ("complaint", "general"): [
        "I haven't received my order yet",
        "Order vanno? Already paid",
        "My parcel is very delayed",
        "I paid but nothing arrived",
        "Please check my delivery status"
    ],
    ("other", "general"): [
        "Can I get more information?",
        "I need help with my purchase",
        "PureLeven customer support?",
        "I have a question",
        "Please help me"
    ],
}

def get_template_paras(category: str, product: str, existing: list[str]) -> list[str]:
    """Return up to 3 template paraphrases not already present in existing."""
    key = (category, product)
    # fallback chain: (cat, general) → (other, general)
    templates = (
        PARA_TEMPLATES.get(key)
        or PARA_TEMPLATES.get((category, "general"))
        or PARA_TEMPLATES.get(("other", "general"))
        or ["Can I get more info?", "Please help", "I need assistance"]
    )
    existing_lower = {e.lower().strip() for e in existing}
    result: list[str] = []
    for t in templates:
        if t.lower().strip() not in existing_lower and len(result) < 3:
            result.append(t)
    return result


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    with open(INPUT_FILE, encoding="utf-8") as f:
        raw_data = json.load(f)
    print(f"Loaded {len(raw_data)} raw entries")

    # Normalise + enrich each entry
    enriched: list[dict] = []
    for entry in raw_data:
        inp  = clean_text(entry.get("customer_input", ""))
        resp = clean_text(entry.get("ideal_response", ""))
        cat  = entry.get("category", "other")
        # Don't split "other" by product — keep it as one general bucket
        prod = "general" if cat == "other" else detect_product(inp + " " + resp)
        enriched.append({
            "category":       cat,
            "product":        prod,
            "customer_input": inp,
            "ideal_response": resp,
            "language":       entry.get("language", "english"),
        })

    # Group by (category, product)
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for e in enriched:
        groups[(e["category"], e["product"])].append(e)

    print(f"Collapsed into {len(groups)} unique intent × product clusters")

    results: list[dict] = []

    for (cat, prod), entries in sorted(groups.items()):
        # Best response = highest quality score
        entries_sorted = sorted(
            entries,
            key=lambda e: response_score(e["ideal_response"]),
            reverse=True,
        )
        ideal_response = entries_sorted[0]["ideal_response"]

        # Collect unique, genuinely clean customer inputs (no Wabis artifacts)
        seen_inputs: set[str] = set()
        clean_inputs: list[str] = []
        all_inputs: list[str] = []   # fallback pool including less-clean inputs
        for e in entries_sorted:
            inp = re.sub(r"<[^>]+>", "", e["customer_input"]).strip()
            if len(inp) < 6:
                continue
            k = inp.lower()
            if k in seen_inputs:
                continue
            seen_inputs.add(k)
            all_inputs.append(inp)
            if is_clean_input(inp):
                clean_inputs.append(inp)

        if not all_inputs:
            continue

        # Canonical = highest canonical_score among clean inputs
        # Fall back to any input if no clean ones available
        if clean_inputs:
            candidate_pool = clean_inputs
        else:
            candidate_pool = [t for t in all_inputs if is_acceptable_fallback(t)]

        if candidate_pool:
            canonical = max(candidate_pool, key=canonical_score)
        else:
            # All inputs are too dirty — use first template paraphrase as canonical
            template_pool = get_template_paras(cat, prod, [])
            canonical = template_pool[0] if template_pool else f"What is the {prod} price?"

        # input_variations = other real inputs (clean preferred) + template paraphrases
        # Cap real variations at 30 to keep the list manageable
        other_real = [v for v in clean_inputs if v.lower() != canonical.lower()][:30]
        if len(other_real) < 5:
            # pad from all_inputs when clean pool is thin
            extras = [v for v in all_inputs
                      if v.lower() != canonical.lower()
                      and v not in other_real][:5 - len(other_real)]
            other_real += extras
        template_paras = get_template_paras(cat, prod, [canonical] + other_real)
        input_variations = other_real + template_paras

        # Language of canonical input
        mal = sum(1 for c in canonical if "\u0D00" <= c <= "\u0D7F")
        language = "malayalam" if mal >= 3 else ("mixed" if mal >= 1 else "english")

        # Review flags
        review, review_reason = flag_review(cat, canonical, ideal_response)

        record: dict = {
            "category":         cat,
            "product":          prod,
            "customer_input":   canonical,
            "input_variations": input_variations,
            "ideal_response":   ideal_response,
            "language":         language,
        }
        if review:
            record["needs_review"]  = True
            record["review_reason"] = review_reason

        results.append(record)

    # Write output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Print summary
    nr    = sum(1 for r in results if r.get("needs_review"))
    cats  = Counter(r["category"] for r in results)
    prods = Counter(r["product"]   for r in results)
    avg_v = sum(len(r["input_variations"]) for r in results) / max(len(results), 1)

    print(f"\nOutput             : {len(results)} deduplicated intent entries")
    print(f"Flagged needs_review: {nr}")
    print(f"Avg variations/entry: {avg_v:.1f}")
    print("\nBy category:")
    for c, n in cats.most_common():
        print(f"  {c:<25} {n}")
    print("\nBy product:")
    for p, n in prods.most_common():
        print(f"  {p:<15} {n}")
    print(f"\nSaved → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
