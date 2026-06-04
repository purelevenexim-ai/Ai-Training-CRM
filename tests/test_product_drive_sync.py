from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "anu-login" / "backend"

for path in (str(ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.services import owner_dashboard_service
from app.services.product_media_service import GOOGLE_DRIVE_FOLDER_MIME


def _catalog_fixture() -> dict:
    return {
        "products": [
            {
                "id": "black_pepper",
                "name": "Black Pepper",
                "aliases": ["black pepper", "pepper", "kurumulak"],
                "origin": "Idukki",
                "story": "Washed & Cleaned",
                "quality": "Bold aroma",
                "use_cases": ["cooking"],
                "recommended_pack": "500g",
                "media_links": [],
                "sizes": [
                    {"size": "250g", "price": 300},
                ],
            },
            {
                "id": "clove",
                "name": "Clove",
                "aliases": ["clove", "grambu"],
                "origin": "Adimali",
                "story": "Premium whole cloves",
                "quality": "Strong aroma",
                "use_cases": ["tea"],
                "recommended_pack": "200g",
                "media_links": [],
                "sizes": [
                    {"size": "100g", "price": 180},
                ],
            },
        ],
        "combos": [],
    }


def test_drive_sync_imports_product_images_and_skips_duplicates(monkeypatch, tmp_path: Path) -> None:
    catalog_path = tmp_path / "product_catalog.json"
    catalog_path.write_text(json.dumps(_catalog_fixture(), ensure_ascii=False, indent=2), encoding="utf-8")

    def fake_drive_listing(folder_ref: str):
        if "drive/folders/root" in str(folder_ref):
            return [
                {
                    "id": "folder-pepper",
                    "name": "Black Pepper",
                    "mime_type": GOOGLE_DRIVE_FOLDER_MIME,
                    "is_folder": True,
                    "download_url": "",
                    "folder_url": "https://drive.google.com/drive/folders/folder-pepper",
                },
                {
                    "id": "folder-clove",
                    "name": "Clove",
                    "mime_type": GOOGLE_DRIVE_FOLDER_MIME,
                    "is_folder": True,
                    "download_url": "",
                    "folder_url": "https://drive.google.com/drive/folders/folder-clove",
                },
            ]
        if folder_ref == "folder-pepper":
            return [
                {
                    "id": "pepper-image-1",
                    "name": "pepper-1.jpg",
                    "mime_type": "image/jpeg",
                    "is_folder": False,
                    "download_url": "https://drive.google.com/uc?export=download&id=pepper-image-1",
                    "folder_url": "",
                }
            ]
        if folder_ref == "folder-clove":
            return [
                {
                    "id": "clove-image-1",
                    "name": "clove-1.jpg",
                    "mime_type": "image/jpeg",
                    "is_folder": False,
                    "download_url": "https://drive.google.com/uc?export=download&id=clove-image-1",
                    "folder_url": "",
                }
            ]
        return []

    def fake_save_product_image_from_url(*, product_key: str, image_url: str, caption: str, source: str, is_primary: bool, sort_order: int):
        return {
            "id": f"{product_key}-{Path(image_url).name}",
            "url": f"/api/product-media/{product_key}/{Path(image_url).name}.jpg",
            "filename": f"{Path(image_url).name}.jpg",
            "caption": caption,
            "source": source,
            "source_url": image_url,
            "is_primary": is_primary,
            "sort_order": sort_order,
            "mime_type": "image/jpeg",
            "size_bytes": 123,
            "uploaded_at": "",
            "updated_at": "",
        }

    monkeypatch.setattr(owner_dashboard_service, "product_catalog_path", lambda: catalog_path)
    monkeypatch.setattr(owner_dashboard_service, "reload_product_catalog_from_file", lambda: None)
    monkeypatch.setattr(owner_dashboard_service, "list_public_google_drive_folder_entries", fake_drive_listing)
    monkeypatch.setattr(owner_dashboard_service, "save_product_image_from_url", fake_save_product_image_from_url)

    def dynamic_catalog_payload():
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        products = []
        for item in catalog["products"]:
            products.append(
                {
                    "product_key": item["id"],
                    "display_name": item["name"],
                    "aliases": item["aliases"],
                    "images": item.get("media_links", []),
                }
            )
        return {
            "products": products,
            "combos": [],
            "media_sync": {},
        }

    monkeypatch.setattr(
        owner_dashboard_service,
        "get_product_catalog_payload",
        dynamic_catalog_payload,
    )

    result = owner_dashboard_service.import_product_images_from_drive_folder(
        "https://drive.google.com/drive/folders/root?usp=sharing"
    )

    assert result["imported_count"] == 2
    assert {item["product_key"] for item in result["products_updated"]} == {"black_pepper", "clove"}

    catalog_after = json.loads(catalog_path.read_text(encoding="utf-8"))
    pepper = next(item for item in catalog_after["products"] if item["id"] == "black_pepper")
    clove = next(item for item in catalog_after["products"] if item["id"] == "clove")
    assert len(pepper["media_links"]) == 1
    assert len(clove["media_links"]) == 1
    assert pepper["media_links"][0]["source"] == "google_drive"

    second_result = owner_dashboard_service.import_product_images_from_drive_folder(
        "https://drive.google.com/drive/folders/root?usp=sharing"
    )
    assert second_result["imported_count"] == 0
    assert any(item["reason"] == "duplicate" for item in second_result["skipped_files"])
