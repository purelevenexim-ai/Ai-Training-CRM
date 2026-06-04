#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "training_artifacts"


def load_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def validate_rows(rows: list[dict[str, object]], split_name: str) -> list[str]:
    problems: list[str] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(rows, start=1):
        for key in ("id", "input", "output", "intent", "category", "product_key", "tone"):
            if not str(row.get(key, "")).strip():
                problems.append(f"{split_name}: row {index} missing {key}")
        row_id = str(row.get("id", ""))
        if row_id in seen_ids:
            problems.append(f"{split_name}: duplicate id {row_id}")
        seen_ids.add(row_id)
    return problems


def detect_conflicts(rows: list[dict[str, object]]) -> list[str]:
    by_input: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for row in rows:
        normalized = " ".join(str(row["input"]).lower().split())
        by_input[normalized].add((str(row["intent"]), str(row["product_key"])))

    conflicts: list[str] = []
    for message, mappings in by_input.items():
        if len(mappings) > 1:
            conflicts.append(f"conflicting mappings for input: {message}")
    return conflicts


def main() -> int:
    train_rows = load_jsonl(ARTIFACTS / "whatsapp_train.jsonl")
    validation_rows = load_jsonl(ARTIFACTS / "whatsapp_validation.jsonl")
    gold_rows = load_jsonl(ARTIFACTS / "whatsapp_gold_test.jsonl")
    all_rows = train_rows + validation_rows + gold_rows

    problems: list[str] = []
    problems.extend(validate_rows(train_rows, "train"))
    problems.extend(validate_rows(validation_rows, "validation"))
    problems.extend(validate_rows(gold_rows, "gold"))
    problems.extend(detect_conflicts(all_rows))

    summary = {
        "train_rows": len(train_rows),
        "validation_rows": len(validation_rows),
        "gold_rows": len(gold_rows),
        "categories": Counter(str(row["category"]) for row in all_rows),
        "tones": Counter(str(row["tone"]) for row in all_rows),
        "problems": problems,
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2, default=lambda value: dict(value)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
