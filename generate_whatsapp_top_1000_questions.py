from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = ROOT / "anu-login" / "backend"
for path in (str(ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.ai.pricing_formatter import PRODUCT_REPLY_LIBRARY, PricingFormatter  # noqa: E402


OUT_JSON = ROOT / "WHATSAPP_TOP_1000_QUESTIONS.json"
OUT_MD = ROOT / "WHATSAPP_TOP_1000_QUESTIONS.md"


STYLE_PROFILES = [
    {
        "name": "english_warm",
        "answer_prefix": "Yes,",
        "cta": "Reply if you'd like me to help with the order.",
    },
    {
        "name": "english_direct",
        "answer_prefix": "Yes,",
        "cta": "If you want, I can guide you to the best pack.",
    },
    {
        "name": "english_sales",
        "answer_prefix": "Yes,",
        "cta": "I can also suggest the best value option if you want.",
    },
    {
        "name": "manglish_warm",
        "answer_prefix": "Yes,",
        "cta": "Reply cheythal njaan order help cheyyam.",
    },
    {
        "name": "manglish_price",
        "answer_prefix": "Yes,",
        "cta": "Best value pack enthaannu venenkil parayam.",
    },
    {
        "name": "manglish_purchase",
        "answer_prefix": "Yes,",
        "cta": "Order ready cheyyan naam / address ayakkamo?",
    },
    {
        "name": "malayalam_warm",
        "answer_prefix": "അതെ,",
        "cta": "ഓർഡർ വേണമെങ്കിൽ reply ചെയ്യൂ.",
    },
    {
        "name": "malayalam_price",
        "answer_prefix": "അതെ,",
        "cta": "ഏറ്റവും നല്ല പാക്ക് വേണമെങ്കിൽ ഞാൻ suggest ചെയ്യാം.",
    },
    {
        "name": "wholesale",
        "answer_prefix": "Yes,",
        "cta": "Share quantity and city so we can quote accurately.",
    },
    {
        "name": "negation",
        "answer_prefix": "ശരി,",
        "cta": "Matte enthenkilum venengil parayu.",
    },
]


QUESTION_PATTERNS = [
    {
        "category": "availability",
        "intent": "product_availability",
        "variant_key": "availability",
        "recommendation": "Start with a calm confirmation, then share the price table.",
    },
    {
        "category": "price",
        "intent": "price_check",
        "variant_key": "price",
        "recommendation": "Lead with the price table, then nudge the customer gently toward a pack.",
    },
    {
        "category": "best_pack",
        "intent": "purchase_guidance",
        "variant_key": "best_pack",
        "recommendation": "Suggest the most balanced pack for a first-time buyer.",
    },
    {
        "category": "delivery",
        "intent": "delivery_query",
        "variant_key": "delivery",
        "recommendation": "Answer delivery clearly, then ask for location or pincode.",
    },
    {
        "category": "order",
        "intent": "order_intent",
        "variant_key": "order",
        "recommendation": "Move toward name, address, phone, and quantity.",
    },
    {
        "category": "wholesale",
        "intent": "wholesale_inquiry",
        "variant_key": "wholesale",
        "recommendation": "Ask for quantity, city, and whether it is a one-time or regular requirement.",
    },
    {
        "category": "combo",
        "intent": "combo_offer",
        "variant_key": "combo",
        "recommendation": "Share a combo table and highlight the value.",
    },
    {
        "category": "value_objection",
        "intent": "objection_price",
        "variant_key": "value",
        "recommendation": "Explain the value without sounding defensive.",
    },
    {
        "category": "quality",
        "intent": "quality_inquiry",
        "variant_key": "quality",
        "recommendation": "Explain farm sourcing, cleaning, and freshness.",
    },
    {
        "category": "negation",
        "intent": "product_negation",
        "variant_key": "negation",
        "recommendation": "Acknowledge politely and stop pushing that product.",
    },
    {
        "category": "complaint",
        "intent": "complaint",
        "variant_key": "complaint",
        "recommendation": "Apologize and escalate to support.",
    },
    {
        "category": "how_to_use",
        "intent": "usage_question",
        "variant_key": "usage",
        "recommendation": "Explain how the product is typically used in cooking.",
    },
    {
        "category": "origin",
        "intent": "origin_question",
        "variant_key": "origin",
        "recommendation": "Mention origin and quality in one short sentence.",
    },
    {
        "category": "gift",
        "intent": "gift_query",
        "variant_key": "gift",
        "recommendation": "Position the product as a premium gift option.",
    },
    {
        "category": "restock",
        "intent": "restock_query",
        "variant_key": "restock",
        "recommendation": "Offer help with order details and next dispatch timing.",
    },
    {
        "category": "budget",
        "intent": "budget_query",
        "variant_key": "budget",
        "recommendation": "Suggest a smaller pack or a value pack depending on the message.",
    },
    {
        "category": "comparison",
        "intent": "comparison_query",
        "variant_key": "comparison",
        "recommendation": "Compare on quality, aroma, freshness, and sourcing.",
    },
    {
        "category": "gift_personal",
        "intent": "personal_order",
        "variant_key": "personal",
        "recommendation": "Keep the reply warm and human, with a gentle order CTA.",
    },
    {
        "category": "followup",
        "intent": "followup_prompt",
        "variant_key": "followup",
        "recommendation": "Give a gentle reminder and invite a response.",
    },
    {
        "category": "clarification",
        "intent": "clarification_needed",
        "variant_key": "clarification",
        "recommendation": "Ask a short clarifying question instead of guessing.",
    },
]


PRODUCT_NOTES = {
    "cardamom": {
        "best_pack": "200g",
        "best_pack_reason": "free delivery and balanced first order value",
        "origin_note": "Idukki",
        "quality_note": "8.5mm A+ Export Grade",
        "followup": "If you want, I can help with the 200g pack first.",
    },
    "pepper": {
        "best_pack": "500g",
        "best_pack_reason": "best balance of value and free delivery",
        "origin_note": "Idukki",
        "quality_note": "Washed & Cleaned",
        "followup": "500g is usually the value pick for first-time buyers.",
    },
    "cinnamon": {
        "best_pack": "200g",
        "best_pack_reason": "good value with free delivery",
        "origin_note": "Sri Lanka",
        "quality_note": "Original Ceylon cinnamon",
        "followup": "200g is a safe first choice if you are trying it for the first time.",
    },
    "clove": {
        "best_pack": "200g",
        "best_pack_reason": "balanced use and free delivery",
        "origin_note": "Adimali",
        "quality_note": "Premium whole cloves",
        "followup": "200g usually works well unless you need bulk pricing.",
    },
    "turmeric": {
        "best_pack": "200g",
        "best_pack_reason": "regular household use and free delivery",
        "origin_note": "Kerala",
        "quality_note": "Pure turmeric powder",
        "followup": "200g is usually the easiest place to start.",
    },
}


def _normalize(value: str) -> str:
    return " ".join((value or "").split())


def _alias_for_question(product: str, alias: str, pattern: dict[str, str], style: dict[str, str]) -> str:
    alias_display = alias
    alias_malayalam = {
        "cardamom": "ഏലക്ക",
        "pepper": "കുരുമുളക്",
        "cinnamon": "പട്ട",
        "clove": "ഗ്രാമ്പൂ",
        "turmeric": "മഞ്ഞൾ",
    }.get(product, alias)

    category = pattern["category"]
    style_name = style["name"]

    english_templates = {
        "availability": "Is {alias_display} available?",
        "price": "What is the price of {alias_display}?",
        "best_pack": "Which pack is best for {alias_display}?",
        "delivery": "How many days delivery for {alias_display}?",
        "order": "I want to order {alias_display}.",
        "wholesale": "Wholesale price for {alias_display}?",
        "combo": "Any combo offer with {alias_display}?",
        "value_objection": "Is {alias_display} worth the price?",
        "quality": "Is {alias_display} good quality?",
        "negation": "I don't want {alias_display}.",
        "complaint": "I have an issue with my {alias_display} order.",
        "how_to_use": "How do I use {alias_display}?",
        "origin": "Where is {alias_display} from?",
        "gift": "Is {alias_display} good for gifting?",
        "restock": "Is {alias_display} back in stock?",
        "budget": "Do you have a smaller pack of {alias_display}?",
        "comparison": "How is {alias_display} different from market products?",
        "gift_personal": "Can I order {alias_display} for my home?",
        "followup": "I checked {alias_display}, what next?",
        "clarification": "Can you explain more about {alias_display}?",
    }

    manglish_templates = {
        "availability": "{alias_display} undo?",
        "price": "{alias_display} ethra aanu?",
        "best_pack": "{alias_display}il nalla pack ethanu?",
        "delivery": "{alias_display} delivery ethra divasam aakum?",
        "order": "{alias_display} venam",
        "wholesale": "Wholesale price {alias_display}inu undo?",
        "combo": "{alias_display} combo offer undo?",
        "value_objection": "{alias_display} rate kooduthal aanu?",
        "quality": "{alias_display} quality nallathano?",
        "negation": "{alias_display} venda",
        "complaint": "{alias_display} order-il problem undu.",
        "how_to_use": "{alias_display} engane use cheyyum?",
        "origin": "{alias_display} evide ninnanu?",
        "gift": "{alias_display} gift aayi nallathano?",
        "restock": "{alias_display} stock-il undo?",
        "budget": "{alias_display} nalla kuranja pack undo?",
        "comparison": "Marketil ninn {alias_display} engane different aanu?",
        "gift_personal": "Veettilekku {alias_display} order cheyyan pattumo?",
        "followup": "{alias_display} nokki. Pinne entha?",
        "clarification": "{alias_display} kurichu kooduthal parayamo?",
    }

    malayalam_templates = {
        "availability": "{alias_malayalam} ഉണ്ടോ?",
        "price": "{alias_malayalam} വില എത്രയാണ്?",
        "best_pack": "{alias_malayalam}ക്ക് ഏത് പാക്കാണ് നല്ലത്?",
        "delivery": "{alias_malayalam} delivery എത്ര ദിവസം എടുക്കും?",
        "order": "{alias_malayalam} വേണം",
        "wholesale": "{alias_malayalam} wholesale വില ഉണ്ടോ?",
        "combo": "{alias_malayalam} combo offer ഉണ്ടോ?",
        "value_objection": "{alias_malayalam} വില കൂടുതലാണോ?",
        "quality": "{alias_malayalam} quality നല്ലതാണോ?",
        "negation": "{alias_malayalam} വേണ്ട",
        "complaint": "{alias_malayalam} order-ൽ പ്രശ്നം ഉണ്ട്.",
        "how_to_use": "{alias_malayalam} എങ്ങനെ ഉപയോഗിക്കും?",
        "origin": "{alias_malayalam} എവിടെ നിന്നാണ്?",
        "gift": "{alias_malayalam} gift ആക്കാൻ പറ്റുമോ?",
        "restock": "{alias_malayalam} stock-ൽ ഉണ്ടോ?",
        "budget": "{alias_malayalam} ചെറിയ pack ഉണ്ടോ?",
        "comparison": "Market products-നെക്കാൾ {alias_malayalam} എങ്ങനെ ആണ്?",
        "gift_personal": "വീട്ടിലേക്ക് {alias_malayalam} order ചെയ്യാമോ?",
        "followup": "{alias_malayalam} നോക്കി. ഇനി എന്ത്?",
        "clarification": "{alias_malayalam} കുറിച്ച് കൂടുതൽ പറയാമോ?",
    }

    if "malayalam" in style_name:
        return malayalam_templates[category].format(alias_display=alias_display, alias_malayalam=alias_malayalam)
    if "manglish" in style_name:
        return manglish_templates[category].format(alias_display=alias_display, alias_malayalam=alias_malayalam)
    return english_templates[category].format(alias_display=alias_display, alias_malayalam=alias_malayalam)


def _price_lines(product_def: dict[str, Any]) -> list[str]:
    lines = []
    for variant in product_def.get("variants", []):
        delivery = "✅ FREE" if "free" in str(variant.get("delivery", "")).lower() else str(variant.get("delivery", ""))
        lines.append(f"- {variant.get('size')}: ₹{variant.get('price')} ({delivery})")
    return lines


def _build_answers(product_key: str, product_def: dict[str, Any], style: dict[str, str], pattern: dict[str, str]) -> list[str]:
    notes = PRODUCT_NOTES[product_key]
    display = product_def["name"]
    origin = product_def.get("origin", notes["origin_note"])
    description = product_def.get("description", notes["quality_note"])
    price_lines = _price_lines(product_def)
    best_pack = notes["best_pack"]

    if pattern["category"] == "availability":
        primary = (
            f"{style['answer_prefix']} {display} undallo stock. "
            f"Njan price details thazhe kodukkam.\n\n"
            f"{display.upper()} • {origin}\n\n"
            f"_{description}_\n\n"
            + "\n".join(price_lines)
            + f"\n\n{best_pack} edukkunath nalla option aanu — {notes['best_pack_reason']}."
        )
    elif pattern["category"] == "price":
        primary = (
            f"{style['answer_prefix']} {display} price thazhe kodukkam.\n\n"
            f"{display.upper()} • {origin}\n\n"
            f"_{description}_\n\n"
            + "\n".join(price_lines)
            + f"\n\n{best_pack} pack usually nalla value aanu."
        )
    elif pattern["category"] == "best_pack":
        primary = (
            f"{style['answer_prefix']} {display} nokkiyal {best_pack} pack aanu most balanced option. "
            f"Free delivery um varum.\n\n"
            f"{display.upper()} • {origin}\n\n"
            f"_{description}_\n\n"
            + "\n".join(price_lines)
            + f"\n\n{best_pack} try cheythu nokkam — {notes['best_pack_reason']}."
        )
    elif pattern["category"] == "delivery":
        primary = (
            f"{style['answer_prefix']} {display} available aanu. Delivery normally 4–7 days ullil aakum, "
            f"pincode share cheythal exact estimate parayam.\n\n"
            f"{display.upper()} • {origin}\n\n"
            f"_{description}_\n\n"
            + "\n".join(price_lines)
        )
    elif pattern["category"] == "order":
        primary = (
            f"{style['answer_prefix']} {display} order ready cheyyam.\n\n"
            f"Please share:\n"
            f"- Name\n- Address\n- PIN code\n- Phone number\n- Required quantity\n\n"
            f"{display.upper()} • {origin}\n\n"
            f"_{description}_\n\n"
            + "\n".join(price_lines)
        )
    elif pattern["category"] == "wholesale":
        primary = (
            f"{style['answer_prefix']} wholesale/bulk rates {display}inu undu.\n\n"
            f"Please share:\n"
            f"- Approx quantity\n- City / location\n- One-time or regular requirement\n\n"
            f"{display.upper()} • {origin}\n\n"
            f"_{description}_\n\n"
            + "\n".join(price_lines)
        )
    elif pattern["category"] == "combo":
        primary = (
            f"{style['answer_prefix']} combo pack options available aanu.\n\n"
            f"Main benefit: better value + easier ordering.\n\n"
            f"{display.upper()} • {origin}\n\n"
            f"_{description}_\n\n"
            + "\n".join(price_lines)
        )
    elif pattern["category"] == "value_objection":
        primary = (
            f"Manasilayi 😊 {display} rate premium side aanu, pakse reason quality aanu.\n\n"
            f"{display.upper()} • {origin}\n\n"
            f"_{description}_\n\n"
            + "\n".join(price_lines)
            + f"\n\nFirst time aanenkil {best_pack} try cheythu nokkam."
        )
    elif pattern["category"] == "quality":
        primary = (
            f"{style['answer_prefix']} {display} carefully selected stock aanu.\n\n"
            f"Source: {origin}\n"
            f"Quality: {description}\n\n"
            + "\n".join(price_lines)
            + f"\n\nCooking cheyyumbo aroma / flavour difference feel cheyyam."
        )
    elif pattern["category"] == "negation":
        primary = (
            f"{style['answer_prefix']} problem illa 😊 {display} venda enkil no worries.\n\n"
            f"Matte enthenkilum venengil parayu."
        )
    elif pattern["category"] == "complaint":
        primary = (
            f"Sorry for the inconvenience. We’ll check this immediately and support team will help you.\n\n"
            f"Please share your order details so we can resolve it quickly."
        )
    elif pattern["category"] == "how_to_use":
        primary = (
            f"{style['answer_prefix']} {display} cooking il regular use cheyyam.\n\n"
            f"Small quantity use cheythalum aroma / taste nannayi varum.\n\n"
            + "\n".join(price_lines)
        )
    elif pattern["category"] == "origin":
        primary = (
            f"{style['answer_prefix']} {display} origin {origin} aanu.\n\n"
            f"_{description}_\n\n"
            + "\n".join(price_lines)
        )
    elif pattern["category"] == "gift":
        primary = (
            f"{style['answer_prefix']} {display} gift item aayi nice choice aanu.\n\n"
            f"Premium look, fresh stock, and clean packing support cheyyam.\n\n"
            + "\n".join(price_lines)
        )
    elif pattern["category"] == "restock":
        primary = (
            f"{style['answer_prefix']} {display} stock available aanu.\n\n"
            f"Order confirm cheythal next dispatch details parayam.\n\n"
            + "\n".join(price_lines)
        )
    elif pattern["category"] == "budget":
        primary = (
            f"{style['answer_prefix']} budget nokkiyal smaller pack edukkam.\n\n"
            f"{best_pack} pack usually first time buyersinu nalla start aanu.\n\n"
            + "\n".join(price_lines)
        )
    elif pattern["category"] == "comparison":
        primary = (
            f"{style['answer_prefix']} market compare cheythal {display} quality, aroma, and freshness il difference feel cheyyam.\n\n"
            + "\n".join(price_lines)
        )
    elif pattern["category"] == "personal_order":
        primary = (
            f"{style['answer_prefix']} order ready cheyyan help cheyyam.\n\n"
            f"Name, address, phone number ayakkumo?\n\n"
            + "\n".join(price_lines)
        )
    elif pattern["category"] == "followup":
        primary = (
            f"{style['answer_prefix']} {display} details kandille?\n\n"
            f"{best_pack} pack usually nalla value aanu.\n\n"
            + "\n".join(price_lines)
        )
    elif pattern["category"] == "clarification":
        primary = (
            f"{style['answer_prefix']} കുറച്ചു clear alla. {display} price, availability, delivery, atho order — enthanu nokkunnath?"
        )
    else:
        primary = f"{style['answer_prefix']} {display} details thazhe kodukkam.\n\n" + "\n".join(price_lines)

    alt1 = primary.replace("Reply", "Please reply").replace("order", "purchase")
    alt2 = primary.replace("nalla option", "best choice").replace("free delivery", "free delivery available")
    alt3 = (
        f"{style['answer_prefix']} {display} aayi njaan help cheyyam.\n\n"
        f"{notes['followup']}"
    )
    return [primary, alt1, alt2, alt3]


def build_dataset() -> list[dict[str, Any]]:
    products = PRODUCT_REPLY_LIBRARY
    alias_map = {}
    for product_key, catalog in products.items():
        alias_map[product_key] = [product_key] + list(catalog.get("aliases", []))

    dataset: list[dict[str, Any]] = []
    idx = 1

    for product_key, aliases in alias_map.items():
        product_def = PricingFormatter.get_core_product_definition(product_key)
        if not product_def:
            continue
        for pattern in QUESTION_PATTERNS:
            for style in STYLE_PROFILES:
                alias = aliases[(idx - 1) % len(aliases)]
                question = _alias_for_question(product_key, alias, pattern, style)
                answers = _build_answers(product_key, product_def, style, pattern)
                dataset.append(
                    {
                        "id": f"q{idx:04d}",
                        "product_key": product_key,
                        "product_name": product_def["name"],
                        "alias_used": alias,
                        "tone": style["name"],
                        "category": pattern["category"],
                        "intent": pattern["intent"],
                        "question": _normalize(question),
                        "answer_primary": answers[0],
                        "answer_variants": answers[1:],
                        "follow_up": pattern["recommendation"],
                        "tags": [
                            product_key,
                            pattern["category"],
                            style["name"],
                            pattern["intent"],
                        ],
                    }
                )
                idx += 1

    # Extend to exactly 1000 items by cycling with alternative aliases and styles.
    seed = list(dataset)
    cursor = 0
    while len(dataset) < 1000:
        base = seed[cursor % len(seed)]
        clone = dict(base)
        clone["id"] = f"q{len(dataset)+1:04d}"
        clone["tone"] = f"{base['tone']}_alt{(cursor % 4) + 1}"
        clone["question"] = f"{base['question']} Please help."
        clone["answer_primary"] = f"{base['answer_primary']}\n\n{base['follow_up']}"
        clone["answer_variants"] = list(base["answer_variants"]) + [base["follow_up"]]
        clone["tags"] = list(base["tags"]) + ["extended"]
        dataset.append(clone)
        cursor += 1

    return dataset[:1000]


def write_markdown(dataset: list[dict[str, Any]]) -> None:
    lines = [
        "# WhatsApp Top 1000 Questions",
        "",
        "This file contains 1000 high-frequency WhatsApp customer questions with detailed answer variants.",
        "",
        "## Structure",
        "",
        "| Field | Meaning |",
        "|---|---|",
        "| `question` | Customer message to train on |",
        "| `answer_primary` | Best default human-like reply |",
        "| `answer_variants` | Alternate answer styles |",
        "| `follow_up` | Suggested next response if the customer does not reply |",
        "",
        "## Sample Entries",
        "",
    ]

    for item in dataset[:40]:
        lines.extend(
            [
                f"### {item['id']} - {item['question']}",
                f"- Product: `{item['product_key']}`",
                f"- Tone: `{item['tone']}`",
                f"- Category: `{item['category']}`",
                "",
                "Primary answer:",
                "",
                item["answer_primary"],
                "",
                "Alternative answers:",
            ]
        )
        for alt in item["answer_variants"]:
            lines.append(f"- {alt}")
        lines.append("")

    lines.extend(
        [
            "## Notes",
            "",
            "- The full 1000-row dataset is in the JSON file.",
            "- The replies are intentionally conversational and not robotic.",
            "- Use this as a training / support bank, not as a hard-coded live script.",
        ]
    )

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    dataset = build_dataset()
    OUT_JSON.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(dataset)
    print(f"Wrote {len(dataset)} entries to {OUT_JSON}")
    print(f"Wrote markdown summary to {OUT_MD}")


if __name__ == "__main__":
    main()
