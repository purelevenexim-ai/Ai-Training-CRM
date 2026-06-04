from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "training_artifacts"


def test_training_release_manager_release_and_list() -> None:
    release = subprocess.run(
        ["python3", str(ROOT / "training_release_manager.py"), "release"],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(release.stdout)
    release_id = payload["release_id"]
    release_dir = ARTIFACTS / "releases" / release_id

    assert release_dir.exists()
    assert (release_dir / "release_manifest.json").exists()
    assert (ARTIFACTS / "current" / "wabis_training_upload.json").exists()
    assert (ARTIFACTS / "current_release.json").exists()
    assert (ARTIFACTS / "release_history.json").exists()
    current_train = (ARTIFACTS / "current" / "whatsapp_train.jsonl").read_text(encoding="utf-8")
    assert "1kg: ₹950" in current_train
    assert "1kg: ₹980" not in current_train

    listed = subprocess.run(
        ["python3", str(ROOT / "training_release_manager.py"), "list"],
        capture_output=True,
        text=True,
        check=True,
    )
    listed_payload = json.loads(listed.stdout)
    assert listed_payload["current"]["release_id"] == release_id
    assert listed_payload["history"][0]["release_id"] == release_id


if __name__ == "__main__":
    test_training_release_manager_release_and_list()
    print("training_release_manager_ok")
