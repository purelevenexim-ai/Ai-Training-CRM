#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
ARTIFACTS_DIR = ROOT / "training_artifacts"
RELEASES_DIR = ARTIFACTS_DIR / "releases"
CURRENT_DIR = ARTIFACTS_DIR / "current"
HISTORY_PATH = ARTIFACTS_DIR / "release_history.json"
CURRENT_RELEASE_PATH = ARTIFACTS_DIR / "current_release.json"

ARTIFACT_FILES = (
    "whatsapp_train.jsonl",
    "whatsapp_validation.jsonl",
    "whatsapp_gold_test.jsonl",
    "wabis_training_upload.json",
    "workflow_manifest.json",
    "workflow_summary.md",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _release_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _run_json_command(args: list[str]) -> dict[str, Any]:
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=True)
    return json.loads(result.stdout.strip())


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _copy_release_files(source_dir: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    for name in ARTIFACT_FILES:
        shutil.copy2(source_dir / name, dest_dir / name)


def _promote_release_dir(release_dir: Path, release_meta: dict[str, Any]) -> None:
    if CURRENT_DIR.exists():
        shutil.rmtree(CURRENT_DIR)
    CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    _copy_release_files(release_dir, CURRENT_DIR)
    _write_json(CURRENT_RELEASE_PATH, release_meta)


def build_release(upload_wabis: bool = False) -> dict[str, Any]:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)

    prepare_result = _run_json_command(["python3", str(ROOT / "prepare_whatsapp_training_artifacts.py")])
    evaluate_result = _run_json_command(["python3", str(ROOT / "evaluate_whatsapp_training_workflow.py")])
    if evaluate_result.get("problems"):
        raise RuntimeError(f"Training evaluation failed: {evaluate_result['problems']}")

    release_id = _release_id()
    release_dir = RELEASES_DIR / release_id
    _copy_release_files(ARTIFACTS_DIR, release_dir)

    manifest = {
        "release_id": release_id,
        "created_at": _now(),
        "prepare_result": prepare_result,
        "evaluate_result": evaluate_result,
        "upload_wabis_requested": upload_wabis,
        "upload_wabis_status": "not_requested",
        "release_dir": str(release_dir),
    }

    if upload_wabis:
        env = os.environ.copy()
        env["WABIS_TRAINING_FILE"] = str(release_dir / "wabis_training_upload.json")
        upload = subprocess.run(
            [
                "python3",
                str(ROOT / "wabis_ai_train.py"),
                "--training-file",
                str(release_dir / "wabis_training_upload.json"),
                "--skip-discovery",
                "--fail-on-upload-error",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
        )
        manifest["upload_wabis_status"] = "success" if upload.returncode == 0 else "failed"
        manifest["upload_wabis_stdout"] = upload.stdout.strip()
        manifest["upload_wabis_stderr"] = upload.stderr.strip()
        if upload.returncode != 0:
            _write_json(release_dir / "release_manifest.json", manifest)
            raise RuntimeError(upload.stderr.strip() or upload.stdout.strip() or "Wabis upload failed")

    _write_json(release_dir / "release_manifest.json", manifest)
    _promote_release_dir(release_dir, manifest)

    history = _load_json(HISTORY_PATH, [])
    history = [manifest] + [item for item in history if item.get("release_id") != release_id]
    _write_json(HISTORY_PATH, history)
    return manifest


def promote_release(release_id: str) -> dict[str, Any]:
    release_dir = RELEASES_DIR / release_id
    manifest_path = release_dir / "release_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Release not found: {release_id}")
    manifest = _load_json(manifest_path, {})
    _promote_release_dir(release_dir, manifest)
    return manifest


def list_releases() -> dict[str, Any]:
    return {
        "current": _load_json(CURRENT_RELEASE_PATH, {}),
        "history": _load_json(HISTORY_PATH, []),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage versioned WhatsApp training releases.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    release_parser = subparsers.add_parser("release", help="Build, validate, archive, and promote a release.")
    release_parser.add_argument("--upload-wabis", action="store_true", help="Upload the promoted release to Wabis.")

    promote_parser = subparsers.add_parser("promote", help="Promote an existing archived release.")
    promote_parser.add_argument("--release-id", required=True)

    subparsers.add_parser("list", help="List current and historical releases.")

    args = parser.parse_args(argv)

    try:
        if args.command == "release":
            payload = build_release(upload_wabis=args.upload_wabis)
        elif args.command == "promote":
            payload = promote_release(args.release_id)
        else:
            payload = list_releases()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
