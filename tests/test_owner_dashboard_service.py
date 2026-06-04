from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "anu-login" / "backend"

for path in (str(ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.services import owner_dashboard_service as svc


def test_owner_dashboard_service() -> None:
    summary = svc.get_owner_dashboard_summary()
    assert "metrics" in summary
    assert "ai_status" in summary
    assert "recent_conversations" in summary

    infrastructure = svc.get_domain_certificate_status()
    assert infrastructure["domain"] == "ai.pureleven.com"
    assert "status" in infrastructure

    catalog = svc.get_product_catalog_payload()
    assert len(catalog["products"]) >= 5
    assert any(item["product_key"] == "black_pepper" for item in catalog["products"])


def test_intent_knowledge_entry_save_and_load() -> None:
    original_read_path = svc.knowledge_base_path
    original_write_path = svc.knowledge_base_write_path
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "WHATSAPP_INTENT_KNOWLEDGE_BASE.json"
            temp_path.write_text("[]\n", encoding="utf-8")
            svc.knowledge_base_path = lambda: temp_path
            svc.knowledge_base_write_path = lambda: temp_path

            saved = svc.save_knowledge_base_entry(
                {
                    "product": "ceylon_cinnamon",
                    "product_name": "Ceylon Cinnamon",
                    "intent": "availability",
                    "trigger_examples": [
                        "Patta undo?",
                        "cinnamon undo",
                        "karuvapatta undo",
                    ],
                    "answer_primary": "Undu 😊 Fresh stock aanu.",
                    "answer_variants": [
                        "Available aanu 😊",
                        "Fresh stock undallo 😊",
                    ],
                    "language": "manglish",
                    "tone": "manglish_warm",
                    "follow_up": "If they ask price, move to pack sizes next.",
                    "tags": ["cinnamon", "availability", "manglish"],
                }
            )

            entries = svc.load_knowledge_base_entries(limit=50)
            assert saved["intent"] == "availability"
            assert saved["customer_input"] == "Patta undo?"
            assert saved["trigger_examples"] == ["Patta undo?", "cinnamon undo", "karuvapatta undo"]
            assert any(entry["intent"] == "availability" and entry["product"] == "ceylon_cinnamon" for entry in entries)

            payload = json.loads(temp_path.read_text(encoding="utf-8"))
            assert len(payload) == 1
            assert payload[0]["trigger_examples"] == ["Patta undo?", "cinnamon undo", "karuvapatta undo"]
            assert payload[0]["answer_primary"] == "Undu 😊 Fresh stock aanu."
    finally:
        svc.knowledge_base_path = original_read_path
        svc.knowledge_base_write_path = original_write_path


def test_legacy_question_rows_are_grouped_into_intent_patterns() -> None:
    original_read_path = svc.knowledge_base_path
    original_write_path = svc.knowledge_base_write_path
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "WHATSAPP_TOP_1000_QUESTIONS.json"
            temp_path.write_text(
                json.dumps(
                    [
                        {
                            "id": "q0001",
                            "product_key": "black_pepper",
                            "product_name": "Black Pepper",
                            "tone": "manglish_warm",
                            "category": "availability",
                            "intent": "availability",
                            "question": "kurumulak undo?",
                            "answer_primary": "Undu 😊",
                            "answer_variants": ["Available aanu 😊"],
                            "input_variations": ["black pepper undo"],
                            "tags": ["black_pepper", "availability"],
                        },
                        {
                            "id": "q0002",
                            "product_key": "black_pepper",
                            "product_name": "Black Pepper",
                            "tone": "manglish_price",
                            "category": "availability",
                            "intent": "availability",
                            "question": "pepper undo?",
                            "answer_primary": "Undu 😊",
                            "answer_variants": ["Fresh stock aanu 😊"],
                            "input_variations": ["kurumulak undo?", "pepper available?"],
                            "tags": ["black_pepper", "availability", "manglish"],
                        },
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            intent_path = Path(temp_dir) / "WHATSAPP_INTENT_KNOWLEDGE_BASE.json"
            svc.knowledge_base_path = lambda: temp_path
            svc.knowledge_base_write_path = lambda: intent_path

            entries = svc.load_knowledge_base_entries(limit=50)
            assert len(entries) == 1
            assert entries[0]["product"] == "black_pepper"
            assert entries[0]["intent"] == "availability"
            assert entries[0]["example_count"] >= 4
            assert entries[0]["source_entry_count"] == 2
            assert "kurumulak undo?" in entries[0]["trigger_examples"]
            assert "pepper undo?" in entries[0]["trigger_examples"]
    finally:
        svc.knowledge_base_path = original_read_path
        svc.knowledge_base_write_path = original_write_path


if __name__ == "__main__":
    test_owner_dashboard_service()
    test_intent_knowledge_entry_save_and_load()
    test_legacy_question_rows_are_grouped_into_intent_patterns()
    print("owner_dashboard_service_ok")
