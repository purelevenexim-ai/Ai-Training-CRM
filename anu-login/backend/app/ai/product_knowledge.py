from __future__ import annotations

import json
import logging
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from app.services.product_media_service import (
    normalize_product_image_entries,
    primary_product_image_url,
)

logger = logging.getLogger(__name__)

_CATALOG_CACHE: dict[str, Any] | None = None


def _catalog_path() -> Path:
    return Path(__file__).with_name("product_catalog.json")


def _normalize_lookup_text(value: str) -> str:
    return re.sub(r"[^a-z0-9\u0d00-\u0d7f]+", " ", (value or "").lower()).strip()


def _tokenize_lookup_text(value: str) -> list[str]:
    return [token for token in _normalize_lookup_text(value).split() if token]


def _slugify_product_id(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", (value or "").lower()).strip("_")
    return text or "product"


def _normalize_sizes(value: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return items
    for row in value:
        if not isinstance(row, dict):
            continue
        size = str(row.get("size") or row.get("label") or "").strip()
        if not size:
            continue
        try:
            price = int(float(row.get("price") or 0))
        except (TypeError, ValueError):
            price = 0
        items.append(
            {
                "size": size,
                "price": price,
            }
        )
    return items


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = [segment.strip() for segment in value.replace("\n", ",").split(",")]
    else:
        items = []
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in items:
        text = str(item or "").strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned


def _normalize_product(raw: dict[str, Any]) -> dict[str, Any]:
    product_id = _slugify_product_id(str(raw.get("id") or raw.get("product_key") or raw.get("name") or raw.get("display_name") or ""))
    name = str(raw.get("name") or raw.get("display_name") or product_id.replace("_", " ").title()).strip()
    story = str(raw.get("story") or raw.get("description") or "").strip()
    quality = str(raw.get("quality") or "").strip()
    use_cases = _normalize_string_list(raw.get("use_cases"))
    sizes = _normalize_sizes(raw.get("sizes") or raw.get("variants"))
    aliases = _normalize_string_list(raw.get("aliases"))
    if name and name.lower() not in {alias.lower() for alias in aliases}:
        aliases.insert(0, name)
    media_links = normalize_product_image_entries(raw.get("media_links") or raw.get("images") or [])
    return {
        "id": product_id,
        "name": name,
        "aliases": aliases,
        "origin": str(raw.get("origin") or "").strip(),
        "story": story,
        "quality": quality,
        "use_cases": use_cases,
        "sizes": sizes,
        "recommended_pack": str(raw.get("recommended_pack") or "").strip(),
        "media_links": media_links,
        "primary_image_url": primary_product_image_url(media_links),
    }


def load_catalog() -> dict[str, Any]:
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE

    payload = json.loads(_catalog_path().read_text(encoding="utf-8"))
    products = [_normalize_product(item) for item in payload.get("products", []) if isinstance(item, dict)]
    combos = [item for item in payload.get("combos", []) if isinstance(item, dict)]
    _CATALOG_CACHE = {
        "products": products,
        "combos": combos,
        "product_index": {product["id"]: product for product in products},
    }
    return _CATALOG_CACHE


def reload_catalog() -> dict[str, Any]:
    global _CATALOG_CACHE
    _CATALOG_CACHE = None
    return load_catalog()


def list_products() -> list[dict[str, Any]]:
    return list(load_catalog()["products"])


def get_product(product_id: str | None) -> dict[str, Any] | None:
    if not product_id:
        return None
    return load_catalog()["product_index"].get(_slugify_product_id(product_id))


def get_combo_offers() -> list[dict[str, Any]]:
    return list(load_catalog()["combos"])


def build_alias_map() -> dict[str, str]:
    alias_map: dict[str, str] = {}
    for product in list_products():
        for alias in product.get("aliases", []):
            normalized_alias = _normalize_lookup_text(alias)
            if normalized_alias:
                alias_map[normalized_alias] = product["id"]
    return alias_map


def _alias_candidates() -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    for alias, product_id in build_alias_map().items():
        if alias:
            candidates.append((alias, product_id))
    return sorted(
        candidates,
        key=lambda item: (len(_tokenize_lookup_text(item[0])), len(item[0])),
        reverse=True,
    )


def _contains_alias(normalized_message: str, alias: str) -> bool:
    pattern = rf"(?<!\S){re.escape(alias)}(?!\S)"
    return bool(re.search(pattern, normalized_message))


def detect_product(message: str, threshold: float = 0.84) -> str | None:
    normalized_message = _normalize_lookup_text(message)
    if not normalized_message:
        return None

    for alias, product_id in _alias_candidates():
        if _contains_alias(normalized_message, alias):
            return product_id

    msg_tokens = _tokenize_lookup_text(message)
    if not msg_tokens:
        return None

    best_product: str | None = None
    best_score = threshold
    for product in list_products():
        for alias in product.get("aliases", []):
            alias_norm = _normalize_lookup_text(alias)
            if not alias_norm:
                continue
            alias_tokens = _tokenize_lookup_text(alias)
            score = SequenceMatcher(None, normalized_message, alias_norm).ratio()
            if len(alias_tokens) == 1:
                for token in msg_tokens:
                    score = max(score, SequenceMatcher(None, token, alias_tokens[0]).ratio())
            else:
                joined = " ".join(alias_tokens)
                window_size = len(alias_tokens)
                for start in range(0, max(1, len(msg_tokens) - window_size + 1)):
                    window = " ".join(msg_tokens[start:start + window_size])
                    score = max(score, SequenceMatcher(None, window, joined).ratio())
            if score > best_score:
                best_score = score
                best_product = product["id"]

    return best_product


def detect_products(message: str, threshold: float = 0.84) -> list[str]:
    normalized_message = _normalize_lookup_text(message)
    if not normalized_message:
        return []

    found: list[str] = []
    consumed_spans: list[tuple[int, int]] = []
    for alias, product_id in _alias_candidates():
        for match in re.finditer(rf"(?<!\S){re.escape(alias)}(?!\S)", normalized_message):
            span = match.span()
            if any(not (span[1] <= existing[0] or span[0] >= existing[1]) for existing in consumed_spans):
                continue
            consumed_spans.append(span)
            if product_id not in found:
                found.append(product_id)
            break

    if found:
        return found

    fuzzy_match = detect_product(message, threshold=threshold)
    return [fuzzy_match] if fuzzy_match else []


def get_primary_image_url(product_id: str | None) -> str:
    product = get_product(product_id)
    if not product:
        return ""
    return str(product.get("primary_image_url") or "")


def get_image_entries(product_id: str | None) -> list[dict[str, Any]]:
    product = get_product(product_id)
    if not product:
        return []
    return normalize_product_image_entries(product.get("media_links", []))


def product_for_dashboard(product: dict[str, Any]) -> dict[str, Any]:
    sizes = list(product.get("sizes", []))
    return {
        "product_key": product["id"],
        "display_name": product.get("name", ""),
        "name": product.get("name", ""),
        "id": product.get("id", ""),
        "aliases": list(product.get("aliases", [])),
        "origin": product.get("origin", ""),
        "story": product.get("story", ""),
        "quality": product.get("quality", ""),
        "use_cases": list(product.get("use_cases", [])),
        "description": product.get("story", ""),
        "recommended_pack": product.get("recommended_pack", ""),
        "variants": sizes,
        "sizes": sizes,
        "images": normalize_product_image_entries(product.get("media_links", [])),
        "media_links": normalize_product_image_entries(product.get("media_links", [])),
    }


def dashboard_payload() -> dict[str, Any]:
    catalog = load_catalog()
    return {
        "products": [product_for_dashboard(product) for product in catalog["products"]],
        "combos": list(catalog["combos"]),
    }
