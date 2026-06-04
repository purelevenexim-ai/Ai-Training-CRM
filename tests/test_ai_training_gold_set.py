from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "anu-login" / "backend"

for path in (str(ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.ai.wabis_reply_generator import WabisReplyGenerator


def load_gold_cases() -> list[dict[str, object]]:
    with open(Path(__file__).with_name("ai_training_gold_cases.json"), "r", encoding="utf-8") as handle:
        return json.load(handle)


def assert_gold_case(case: dict[str, object]) -> None:
    message = str(case["message"])
    result = WabisReplyGenerator.generate_reply(
        incoming_message=message,
        customer_phone="919999999994",
        customer_name="Anu",
    )

    assert result["intent"] == case["expected_intent"], case["name"]

    reply_lower = result["reply_text"].lower()

    for fragment in case.get("must_contain", []):
        assert str(fragment).lower() in reply_lower, f"{case['name']} missing {fragment!r}"

    for fragment in case.get("must_not_contain", []):
        assert str(fragment).lower() not in reply_lower, f"{case['name']} contained {fragment!r}"


def test_ai_training_gold_cases() -> None:
    for case in load_gold_cases():
        assert_gold_case(case)


if __name__ == "__main__":
    for case in load_gold_cases():
        assert_gold_case(case)
    print("ai_training_gold_cases_ok")
