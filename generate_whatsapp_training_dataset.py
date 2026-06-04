from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = ROOT / "anu-login" / "backend"
for path in (str(ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.ai.pricing_formatter import (
    PRODUCT_REPLY_LIBRARY,
    PricingFormatter,
)


OUTPUT_JSON = ROOT / "GENERATED_WHATSAPP_TRAINING_DATASET.json"
OUTPUT_MD = ROOT / "GENERATED_WHATSAPP_TRAINING_DATASET.md"

KEYWORD_FILTER = re.compile(
    r"(price|rate|ethra|undo|venda|vena|need|want|place|order|wholesale|bulk|combo|delivery|cod|cash|refund|return|replace|damaged|not received|issue|problem|question|details)",
    re.IGNORECASE,
)

MALAYALAM_RE = re.compile(r"[\u0D00-\u0D7F]")


def style_for_text(text: str) -> str:
    lower = (text or "").lower()
    if MALAYALAM_RE.search(text or ""):
        return "malayalam"
    if any(token in lower for token in ("undo", "venda", "ethra", "kurumulak", "venam", "enik", "ethra aanu")):
        return "manglish"
    return "english"


def product_reply(product_key: str, style: str) -> str:
    return PricingFormatter.build_core_product_reply(product_key, style=style) or ""


def combo_reply(style: str) -> str:
    return PricingFormatter.build_combo_reply(style=style)


def wholesale_reply(style: str) -> str:
    return PricingFormatter.build_wholesale_reply(style=style)


def no_interest_reply(style: str) -> str:
    return PricingFormatter.build_no_interest_reply(style=style)


def order_capture_reply(style: str, product_label: str | None = None) -> str:
    base = PricingFormatter.build_order_capture_reply(style=style)
    if product_label:
        return f"{product_label} order oke. {base}"
    return base


def delivery_reply(product_key: str, style: str) -> str:
    definition = PRODUCT_REPLY_LIBRARY.get(product_key, {})
    display = definition.get("display_name", product_key.title())
    if style == "malayalam":
        return (
            f"{display} delivery സംബന്ധിച്ച്:\n\n"
            "• 100g / small pack -> delivery charge applies\n"
            "• 200g and above -> free delivery\n"
            "• Combo orders -> free delivery\n\n"
            "Delivery details share cheyyumbo exact amount paranju tharam."
        )
    if style == "manglish":
        return (
            f"{display} delivery kurichu:\n\n"
            "• 100g / small pack aanenkil delivery charge varum\n"
            "• 200g and above free delivery aanu\n"
            "• Combo orders kkum free delivery aanu\n\n"
            "Details paranjal exact charge paranju tharam."
        )
    return (
        f"{display} delivery details:\n\n"
        "• 100g / small pack: delivery charge applies\n"
        "• 200g and above: free delivery\n"
        "• Combo orders: free delivery\n\n"
        "Share the quantity if you want the exact total."
    )


def canonical_aliases(product_key: str) -> list[str]:
    definition = PRODUCT_REPLY_LIBRARY.get(product_key, {})
    aliases = [product_key]
    aliases.extend(definition.get("aliases", []))
    unique: list[str] = []
    seen: set[str] = set()
    for alias in aliases:
        key = alias.strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(alias.strip())
    return unique


def aliases_by_style(product_key: str, style: str) -> list[str]:
    aliases = canonical_aliases(product_key)
    if style == "malayalam":
        picked = [a for a in aliases if MALAYALAM_RE.search(a)]
        return picked or aliases
    if style == "manglish":
        picked = [a for a in aliases if not MALAYALAM_RE.search(a)]
        return picked or aliases
    picked = [a for a in aliases if not MALAYALAM_RE.search(a)]
    return picked or aliases


QUESTION_PATTERNS: dict[str, dict[str, list[str]]] = {
    "product_info": {
        "english": [
            "{alias}",
            "{alias} price",
            "{alias} rate",
            "price of {alias}",
            "what is the price of {alias}",
            "{alias} details",
            "{alias} info",
            "need {alias}",
        ],
        "manglish": [
            "{alias} undo ?",
            "{alias} ethra aanu",
            "{alias} ethra?",
            "{alias} need",
            "{alias} price undo ?",
            "{alias} details undo ?",
        ],
        "malayalam": [
            "{alias} ഉണ്ടോ ?",
            "{alias} വില എത്രയാണ് ?",
            "{alias} എത്രയാണ് വില ?",
            "{alias} വേണ്ട",
            "{alias} വിവരങ്ങൾ വേണം",
        ],
    },
    "negation": {
        "english": [
            "{alias} not needed",
            "don't need {alias}",
            "no {alias}",
            "not interested in {alias}",
        ],
        "manglish": [
            "{alias} venda",
            "{alias} enik venda",
            "{alias} venda ?",
            "{alias} ippol venda",
            "{alias} വേണ്ടാ",
            "{alias} വേണ്ട",
        ],
        "malayalam": [
            "{alias} വേണ്ട",
            "{alias} വേണ്ടാ",
            "{alias} ഇപ്പോൾ വേണ്ട",
            "{alias} വേണ്ടത്തില്ല",
        ],
    },
    "order": {
        "english": [
            "order {alias}",
            "place order for {alias}",
            "i want {alias}",
            "need to order {alias}",
        ],
        "manglish": [
            "{alias} venam",
            "{alias} order cheyyam",
            "{alias} place cheyyam",
            "{alias} ayachu tharamo",
            "{alias} വേണം",
        ],
        "malayalam": [
            "{alias} വേണം",
            "{alias} ഓർഡർ ചെയ്യണം",
            "{alias} അയച്ചു തരാമോ",
        ],
    },
    "wholesale": {
        "english": [
            "{alias} wholesale price",
            "{alias} bulk rate",
            "wholesale {alias}",
            "bulk {alias}",
            "{alias} wholesale undo",
        ],
        "manglish": [
            "{alias} wholesale undo ?",
            "{alias} bulk rate undo ?",
            "{alias} wholesale price undo ?",
            "{alias} wholesale",
        ],
        "malayalam": [
            "{alias} wholesale ഉണ്ടോ ?",
            "{alias} bulk rate ഉണ്ടോ ?",
            "{alias} wholesale price പറയാമോ ?",
        ],
    },
    "delivery": {
        "english": [
            "{alias} delivery charges",
            "{alias} cash on delivery",
            "{alias} courier charges",
            "is delivery free for {alias}",
        ],
        "manglish": [
            "{alias} courier undo ?",
            "{alias} cash on delivery undo ?",
            "{alias} delivery undo ?",
        ],
        "malayalam": [
            "{alias} delivery ഉണ്ടോ ?",
            "{alias} cash on delivery ഉണ്ടോ ?",
            "{alias} courier ചാർജ് എത്ര ?",
        ],
    },
    "combo": {
        "english": [
            "combo offer",
            "combo price",
            "{alias} combo",
            "{alias} combo price",
        ],
        "manglish": [
            "combo undo ?",
            "{alias} combo undo ?",
            "combo price undo ?",
        ],
        "malayalam": [
            "combo ഉണ്ടോ ?",
            "{alias} combo ഉണ്ടോ ?",
            "combo വില എത്രയാണ് ?",
        ],
    },
}


def infer_intent(message: str) -> str:
    msg = (message or "").lower()
    if any(token in msg for token in ("wholesale", "bulk")):
        return "wholesale"
    if any(token in msg for token in ("combo", "bundle", "special offer")):
        return "combo"
    if any(token in msg for token in ("venda", "വേണ്ട", "not needed", "don't need", "enik venda")):
        return "negation"
    if any(token in msg for token in ("delivery", "courier", "cod", "cash on delivery")):
        return "delivery"
    if any(token in msg for token in ("order", "place", "want", "need")):
        return "order"
    return "product_info"


def choose_product_key(message: str) -> str | None:
    lower = (message or "").lower()
    for canonical_key, definition in PRODUCT_REPLY_LIBRARY.items():
        for alias in canonical_aliases(canonical_key):
            if alias.lower() in lower:
                return canonical_key
    return None


def build_seed_examples() -> list[dict[str, Any]]:
    seeds: list[dict[str, Any]] = []

    cleaned_path = ROOT / "CHATBOT_TRAINING_DATA_CLEANED.json"
    if cleaned_path.exists():
        rows = json.loads(cleaned_path.read_text(encoding="utf-8"))
        for row in rows:
            text = row.get("customer_input") or ""
            if not text:
                continue
            if not KEYWORD_FILTER.search(text):
                continue
            seeds.append(
                {
                    "source": "cleaned_dataset",
                    "customer_input": text,
                    "product": row.get("product") or choose_product_key(text) or "general",
                    "intent": row.get("category") or infer_intent(text),
                    "style": style_for_text(text),
                }
            )
            for variation in row.get("input_variations", []):
                if variation and KEYWORD_FILTER.search(variation):
                    seeds.append(
                        {
                            "source": "cleaned_dataset_variation",
                            "customer_input": variation,
                            "product": row.get("product") or choose_product_key(variation) or "general",
                            "intent": row.get("category") or infer_intent(variation),
                            "style": style_for_text(variation),
                        }
                    )

    for doc_name in ("CUSTOMER_QA_DATABASE.md", "PURELEVEN_WABIS_UPLOAD.txt"):
        doc_path = ROOT / doc_name
        if not doc_path.exists():
            continue
        for line in doc_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip().lstrip("> ").strip()
            if not stripped or not KEYWORD_FILTER.search(stripped):
                continue
            if len(stripped) < 3:
                continue
            seeds.append(
                {
                    "source": doc_name,
                    "customer_input": stripped,
                    "product": choose_product_key(stripped) or "general",
                    "intent": infer_intent(stripped),
                    "style": style_for_text(stripped),
                }
            )

    chats_dir = ROOT / "customer_chats_v2"
    if chats_dir.exists():
        for csv_path in chats_dir.glob("*.csv"):
            try:
                with csv_path.open("r", encoding="utf-8", errors="ignore") as handle:
                    reader = csv.DictReader(handle)
                    for row in reader:
                        sender = (row.get("sender") or "").lower()
                        message = (row.get("message") or "").strip()
                        if sender != "user" or not message:
                            continue
                        if not KEYWORD_FILTER.search(message):
                            continue
                        seeds.append(
                            {
                                "source": f"customer_chats_v2/{csv_path.name}",
                                "customer_input": message,
                                "product": choose_product_key(message) or "general",
                                "intent": infer_intent(message),
                                "style": style_for_text(message),
                            }
                        )
            except Exception:
                continue

    return seeds


def build_synthetic_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for product_key, definition in PRODUCT_REPLY_LIBRARY.items():
        aliases = {
            "english": aliases_by_style(product_key, "english"),
            "manglish": aliases_by_style(product_key, "manglish"),
            "malayalam": aliases_by_style(product_key, "malayalam"),
        }

        for style, alias_list in aliases.items():
            if not alias_list:
                continue

            # Keep a practical number of combinations per product.
            alias_sample = alias_list[:4]
            for alias in alias_sample:
                for pattern in QUESTION_PATTERNS["product_info"][style]:
                    rows.append({
                        "source": "synthetic",
                        "intent": "product_info",
                        "product": product_key,
                        "style": style,
                        "customer_input": pattern.format(alias=alias),
                        "ideal_response": product_reply(product_key, style),
                    })
                for pattern in QUESTION_PATTERNS["negation"][style]:
                    rows.append({
                        "source": "synthetic",
                        "intent": "product_negation",
                        "product": product_key,
                        "style": style,
                        "customer_input": pattern.format(alias=alias),
                        "ideal_response": no_interest_reply(style),
                    })
                for pattern in QUESTION_PATTERNS["order"][style]:
                    rows.append({
                        "source": "synthetic",
                        "intent": "order_capture",
                        "product": product_key,
                        "style": style,
                        "customer_input": pattern.format(alias=alias),
                        "ideal_response": order_capture_reply(style, definition.get("display_name")),
                    })
                for pattern in QUESTION_PATTERNS["wholesale"][style]:
                    rows.append({
                        "source": "synthetic",
                        "intent": "wholesale_inquiry",
                        "product": product_key,
                        "style": style,
                        "customer_input": pattern.format(alias=alias),
                        "ideal_response": wholesale_reply(style),
                    })
                for pattern in QUESTION_PATTERNS["delivery"][style]:
                    rows.append({
                        "source": "synthetic",
                        "intent": "delivery_query",
                        "product": product_key,
                        "style": style,
                        "customer_input": pattern.format(alias=alias),
                        "ideal_response": delivery_reply(product_key, style),
                    })

    # Combos are product-agnostic, but we still want style coverage.
    combo_messages = {
        "english": QUESTION_PATTERNS["combo"]["english"],
        "manglish": QUESTION_PATTERNS["combo"]["manglish"],
        "malayalam": QUESTION_PATTERNS["combo"]["malayalam"],
    }
    for style, patterns in combo_messages.items():
        for pattern in patterns:
            rows.append({
                "source": "synthetic",
                "intent": "combo_offer",
                "product": "combo",
                "style": style,
                "customer_input": pattern.format(alias="combo"),
                "ideal_response": combo_reply(style),
            })

    return rows


def normalize_dataset(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["customer_input"].lower().strip(), row.get("intent", "").lower().strip())
        if key not in unique:
            unique[key] = row
    return list(unique.values())


def main() -> None:
    seeds = build_seed_examples()
    synthetic = build_synthetic_examples()
    dataset = normalize_dataset(seeds + synthetic)
    dataset.sort(key=lambda row: (row.get("product", ""), row.get("intent", ""), row.get("style", ""), row.get("customer_input", "")))

    OUTPUT_JSON.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = Counter((row.get("intent", "unknown"), row.get("product", "unknown")) for row in dataset)
    sources = Counter(row.get("source", "unknown") for row in dataset)
    styles = Counter(row.get("style", "unknown") for row in dataset)

    md_lines = [
        "# Generated WhatsApp Training Dataset",
        "",
        f"- Total rows: {len(dataset)}",
        f"- Seed rows: {len(seeds)}",
        f"- Synthetic rows: {len(synthetic)}",
        "",
        "## By Source",
    ]
    for source, count in sources.most_common():
        md_lines.append(f"- {source}: {count}")
    md_lines += ["", "## By Style"]
    for style, count in styles.most_common():
        md_lines.append(f"- {style}: {count}")
    md_lines += ["", "## Top Intent/Product Buckets"]
    for (intent, product), count in counts.most_common(30):
        md_lines.append(f"- {intent} / {product}: {count}")
    md_lines += ["", "## Sample Rows"]
    for row in dataset[:40]:
        md_lines.append(
            f"- `{row.get('intent')}` / `{row.get('product')}` / `{row.get('style')}` -> {row.get('customer_input')}"
        )

    OUTPUT_MD.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"wrote {OUTPUT_JSON}")
    print(f"wrote {OUTPUT_MD}")
    print(f"rows={len(dataset)}")


if __name__ == "__main__":
    main()
