from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "training_artifacts"


def test_training_workflow() -> None:
    prep = subprocess.run(
        ["python3", str(ROOT / "prepare_whatsapp_training_artifacts.py")],
        capture_output=True,
        text=True,
        check=True,
    )
    prep_result = json.loads(prep.stdout.strip())
    assert prep_result["status"] == "ok"
    assert "catalog_sync" in prep_result["refresh_steps"]
    assert "question_bank" in prep_result["refresh_steps"]
    assert prep_result["train_rows"] == 700
    assert prep_result["validation_rows"] == 200
    assert prep_result["gold_rows"] == 100

    for filename in (
        "whatsapp_train.jsonl",
        "whatsapp_validation.jsonl",
        "whatsapp_gold_test.jsonl",
        "wabis_training_upload.json",
        "workflow_manifest.json",
        "workflow_summary.md",
    ):
        assert (ARTIFACTS / filename).exists(), filename

    evaluation = subprocess.run(
        ["python3", str(ROOT / "evaluate_whatsapp_training_workflow.py")],
        capture_output=True,
        text=True,
        check=True,
    )
    summary = json.loads(evaluation.stdout)
    assert summary["train_rows"] == 700
    assert summary["validation_rows"] == 200
    assert summary["gold_rows"] == 100
    assert summary["problems"] == []

    pepper_lines = [
        line
        for line in (ARTIFACTS / "whatsapp_train.jsonl").read_text(encoding="utf-8").splitlines()
        if "Black Pepper" in line or "\"product_key\": \"pepper\"" in line
    ]
    assert any("₹950" in line or '"price": 950' in line or "1kg: ₹950" in line for line in pepper_lines)
    assert not any("1kg: ₹980" in line for line in pepper_lines)


if __name__ == "__main__":
    test_training_workflow()
    print("training_workflow_ok")
