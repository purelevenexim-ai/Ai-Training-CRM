#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from pathlib import Path

CURRENT_DIR_NAME = "current"


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "WHATSAPP_TOP_1000_QUESTIONS.json"
OUT_DIR = ROOT / "training_artifacts"

TRAIN_PER_CATEGORY = 35
VALIDATION_PER_CATEGORY = 10
GOLD_PER_CATEGORY = 5


def _run_step(args: list[str]) -> dict[str, object]:
    result = subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return {
        "command": args,
        "stdout": result.stdout.strip(),
    }


def load_source() -> list[dict[str, object]]:
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def build_training_record(row: dict[str, object]) -> dict[str, object]:
    return {
        "id": row["id"],
        "input": row["question"],
        "output": row["answer_primary"],
        "intent": row["intent"],
        "category": row["category"],
        "product_key": row["product_key"],
        "tone": row["tone"],
        "tags": row.get("tags", []),
        "answer_variants": row.get("answer_variants", []),
        "follow_up": row.get("follow_up", ""),
    }


def build_wabis_record(row: dict[str, object]) -> dict[str, object]:
    tone = str(row.get("tone", ""))
    language = "ml" if tone.startswith("malayalam") else "en-ml" if "manglish" in tone else "en"
    return {
        "question": row["question"],
        "answer": row["answer_primary"],
        "category": row["category"],
        "product": row["product_key"],
        "language": language,
        "intent": row["intent"],
        "id": row["id"],
    }


def split_rows(rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["category"])].append(row)

    train: list[dict[str, object]] = []
    validation: list[dict[str, object]] = []
    gold: list[dict[str, object]] = []

    for category in sorted(grouped):
        items = sorted(grouped[category], key=lambda row: str(row["id"]))
        gold.extend(items[:GOLD_PER_CATEGORY])
        validation.extend(items[GOLD_PER_CATEGORY:GOLD_PER_CATEGORY + VALIDATION_PER_CATEGORY])
        train.extend(items[GOLD_PER_CATEGORY + VALIDATION_PER_CATEGORY:GOLD_PER_CATEGORY + VALIDATION_PER_CATEGORY + TRAIN_PER_CATEGORY])

    return {"train": train, "validation": validation, "gold": gold}


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_summary(path: Path, splits: dict[str, list[dict[str, object]]]) -> None:
    lines = [
        "# WhatsApp Training Artifact Summary",
        "",
        f"Source file: `{SOURCE}`",
        "",
        "| Split | Rows |",
        "|---|---:|",
    ]
    for split_name in ("train", "validation", "gold"):
        lines.append(f"| {split_name} | {len(splits[split_name])} |")

    lines.extend(["", "## Categories per split", ""])
    for split_name in ("train", "validation", "gold"):
        counts: dict[str, int] = defaultdict(int)
        for row in splits[split_name]:
            counts[str(row["category"])] += 1
        lines.append(f"### {split_name}")
        lines.append("")
        lines.append("| Category | Rows |")
        lines.append("|---|---:|")
        for category in sorted(counts):
            lines.append(f"| {category} | {counts[category]} |")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    refresh_steps = {
        "catalog_sync": _run_step(["python3", str(ROOT / "sync_product_catalog_from_wabis_upload.py")]),
        "question_bank": _run_step(["python3", str(ROOT / "generate_whatsapp_top_1000_questions.py")]),
    }
    rows = load_source()
    splits = split_rows(rows)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    train_records = [build_training_record(row) for row in splits["train"]]
    validation_records = [build_training_record(row) for row in splits["validation"]]
    gold_records = [build_training_record(row) for row in splits["gold"]]
    wabis_records = [build_wabis_record(row) for row in rows]

    write_jsonl(OUT_DIR / "whatsapp_train.jsonl", train_records)
    write_jsonl(OUT_DIR / "whatsapp_validation.jsonl", validation_records)
    write_jsonl(OUT_DIR / "whatsapp_gold_test.jsonl", gold_records)
    (OUT_DIR / "wabis_training_upload.json").write_text(
        json.dumps(wabis_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT_DIR / "workflow_manifest.json").write_text(
        json.dumps(
            {
                "source_file": str(SOURCE),
                "train_rows": len(train_records),
                "validation_rows": len(validation_records),
                "gold_rows": len(gold_records),
                "wabis_rows": len(wabis_records),
                "catalog_products": len({str(row["product_key"]) for row in rows}),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    write_summary(OUT_DIR / "workflow_summary.md", splits)

    print(
        json.dumps(
            {
                "status": "ok",
                "refresh_steps": refresh_steps,
                "output_dir": str(OUT_DIR),
                "train_rows": len(train_records),
                "validation_rows": len(validation_records),
                "gold_rows": len(gold_records),
                "wabis_rows": len(wabis_records),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
