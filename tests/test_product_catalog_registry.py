from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "anu-login" / "backend"

for path in (str(ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.ai import pricing_formatter
from app.ai.pricing_formatter import PRODUCT_REPLY_LIBRARY, COMBO_OFFER_LIBRARY


def test_product_catalog_file_is_loaded() -> None:
    catalog_path = Path(pricing_formatter.__file__).with_name("product_catalog.json")
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))

    for product in payload["products"]:
        assert product["id"] in PRODUCT_REPLY_LIBRARY

    combo_titles = {combo["title"] for combo in COMBO_OFFER_LIBRARY}
    for combo in payload["combos"]:
        assert combo["title"] in combo_titles

    pepper = next(product for product in payload["products"] if product["id"] == "black_pepper")
    pepper_prices = {variant["size"]: variant["price"] for variant in pepper["sizes"]}
    assert pepper_prices["1kg"] == 950


if __name__ == "__main__":
    test_product_catalog_file_is_loaded()
    print("product_catalog_registry_ok")
