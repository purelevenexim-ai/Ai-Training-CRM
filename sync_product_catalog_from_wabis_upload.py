#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "PURELEVEN_WABIS_UPLOAD.txt"


def _catalog_path() -> Path:
    candidates = (
        ROOT / "anu-login" / "backend" / "app" / "ai" / "product_catalog.json",
        ROOT / "app" / "ai" / "product_catalog.json",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


CATALOG = _catalog_path()

QUESTION_TO_PRODUCT = {
    "cardamom": "cardamom",
    "black pepper": "black_pepper",
    "cinnamon": "ceylon_cinnamon",
    "clove": "clove",
    "turmeric powder": "turmeric",
}


def _normalize_size(value: str) -> str:
    return value.strip().lower().replace(" ", "")


def load_catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def load_source_text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def parse_product_pricing(text: str) -> dict[str, list[dict[str, int | str]]]:
    product_sections: dict[str, list[dict[str, int | str]]] = {}
    question_pattern = re.compile(r"Q:\s+What is the price of ([^?]+)\?", re.IGNORECASE)
    qa_pattern = re.compile(r"Q:\s+What is the price of ([^?]+)\?\nA:\s+(.+?)(?=\nQ:|\Z)", re.IGNORECASE | re.DOTALL)
    variant_pattern = re.compile(
        r"(\d+\s?(?:g|kg))\s*=\s*Rs\.?\s*(\d+)\s*(?:plus\s*Rs\.?\s*(\d+)\s*delivery|with\s*free delivery)",
        re.IGNORECASE,
    )

    for match in qa_pattern.finditer(text):
        raw_question = match.group(1).strip().lower()
        answer = match.group(2).strip()
        canonical = QUESTION_TO_PRODUCT.get(raw_question)
        if not canonical:
            continue

        variants: list[dict[str, str | int]] = []
        for size, price, delivery_charge in variant_pattern.findall(answer):
            variants.append(
                {
                    "size": _normalize_size(size),
                    "price": int(price),
                }
            )
        if variants:
            normalized_variants = []
            for variant in variants:
                normalized_variants.append(
                    {
                        "size": _normalize_size(str(variant["size"])),
                        "price": int(variant["price"]),
                    }
                )
            product_sections[canonical] = normalized_variants

    # keep question_pattern referenced for easier future extension / lint quiet
    _ = question_pattern
    return product_sections


def parse_combo_pricing(text: str) -> dict[str, int]:
    combos: dict[str, int] = {}
    combo_match = re.search(r"Q:\s+Do you have any combo offers\?\nA:\s+(.+?)(?=\nQ:|\Z)", text, re.IGNORECASE | re.DOTALL)
    if not combo_match:
        return combos

    answer = combo_match.group(1).strip()
    combo_pattern = re.compile(
        r"Cardamom\s+100g\s+plus\s+(Cinnamon|Clove|Pepper)\s+(100g|200g)\s*=\s*Rs\.?\s*(\d+)",
        re.IGNORECASE,
    )
    combo_display_name = {
        "cinnamon": "Cinnamon",
        "clove": "Clove",
        "pepper": "Black Pepper",
    }
    for item_name, size, price in combo_pattern.findall(answer):
        includes = f"Cardamom 100g + {combo_display_name[item_name.lower()]} {size}"
        combos[includes] = int(price)
    return combos


def sync_catalog() -> dict[str, object]:
    catalog = load_catalog()
    source_text = load_source_text()
    product_pricing = parse_product_pricing(source_text)
    combo_pricing = parse_combo_pricing(source_text)

    updated_products: list[str] = []
    for product in catalog.get("products", []):
        key = str(product.get("id") or product.get("product_key") or "")
        if key in product_pricing:
            product["sizes"] = product_pricing[key]
            updated_products.append(key)

    updated_combos: list[str] = []
    for combo in catalog.get("combos", []):
        includes = str(combo.get("includes", ""))
        if includes in combo_pricing:
            combo["price"] = combo_pricing[includes]
            updated_combos.append(includes)

    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "updated_products": updated_products,
        "updated_combos": updated_combos,
        "catalog_path": str(CATALOG),
        "source_path": str(SOURCE),
    }


def main() -> int:
    result = sync_catalog()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
