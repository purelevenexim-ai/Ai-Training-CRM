from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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


def test_product_catalog_sync_keeps_wabis_defined_prices() -> None:
    subprocess.run(
        ["python3", str(ROOT / "sync_product_catalog_from_wabis_upload.py")],
        capture_output=True,
        text=True,
        check=True,
    )

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    pepper = next(product for product in catalog["products"] if product["id"] == "black_pepper")
    pepper_prices = {variant["size"]: variant["price"] for variant in pepper["sizes"]}
    combos = {combo["includes"]: combo["price"] for combo in catalog["combos"]}

    assert pepper_prices["1kg"] == 950
    assert set(pepper_prices) == {"250g", "500g", "1kg"}
    assert combos["Cardamom 100g + Black Pepper 200g"] == 640


if __name__ == "__main__":
    test_product_catalog_sync_keeps_wabis_defined_prices()
    print("product_catalog_sync_ok")
