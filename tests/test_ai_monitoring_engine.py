from __future__ import annotations

import os
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "anu-login" / "backend"

for path in (str(ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

tmp = tempfile.NamedTemporaryFile(prefix="pureleven_monitor_", suffix=".sqlite3", delete=False)
tmp.close()
os.environ["ANU_LOGIN_DATABASE_PATH"] = tmp.name

from app.runtime_db import ensure_runtime_tables, get_db_connection
from app.services.ai_monitoring_engine import get_ai_monitor_payload
from app.storage import init_database


def _insert_audit(
    *,
    phone: str,
    created_at: str,
    source: str,
    direction: str,
    message: str,
    metadata_json: str = "{}",
) -> None:
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO conversation_audit_log (
                id, created_at, phone, direction, source, message,
                owner_before, owner_after, active_flow, detected_intent,
                route_decision, reason, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, NULL, ?)
            """,
            (
                str(uuid.uuid4()),
                created_at,
                phone,
                direction,
                source,
                message,
                metadata_json,
            ),
        )
        connection.commit()


def test_ai_monitor_flags_reply_quality_issues() -> None:
    init_database()
    ensure_runtime_tables()
    now = datetime.now(timezone.utc)
    phone = "919999999901"

    _insert_audit(
        phone=phone,
        created_at=(now - timedelta(minutes=8)).isoformat(),
        source="customer",
        direction="inbound",
        message="black pepper undo?",
    )
    _insert_audit(
        phone=phone,
        created_at=(now - timedelta(minutes=7)).isoformat(),
        source="ai",
        direction="outbound",
        message=(
            "Absolutely, Yes, we have black pepper in stock. Washed and cleaned Idukki black pepper "
            "from our spice-growing belt. Customers usually use this for everyday cooking, pepper tea, "
            "masala blends, and unique qualities. This is a very long catalog style response that keeps "
            "explaining the product instead of answering the customer briefly. It also repeats source, "
            "quality, benefits, usage, and order guidance in one block when the customer only asked if "
            "black pepper is available."
        ),
    )

    payload = get_ai_monitor_payload(hours=1, limit=20)
    issue_types = {item["issue_type"] for item in payload["issues"]}

    assert payload["metrics"]["journeys"] >= 1
    assert "Too long" in issue_types
    assert "Robotic or banned wording" in issue_types


def test_ai_monitor_detects_payment_proof_repeat_and_materializes_journey() -> None:
    init_database()
    ensure_runtime_tables()
    now = datetime.now(timezone.utc)
    phone = "919999999902"

    _insert_audit(
        phone=phone,
        created_at=(now - timedelta(minutes=5)).isoformat(),
        source="customer",
        direction="inbound",
        message="Paid using Google Pay",
    )
    _insert_audit(
        phone=phone,
        created_at=(now - timedelta(minutes=4)).isoformat(),
        source="customer",
        direction="inbound",
        message="[[media:image]]",
    )
    _insert_audit(
        phone=phone,
        created_at=(now - timedelta(minutes=3)).isoformat(),
        source="ai",
        direction="outbound",
        message="Please share payment screenshot or proof so we can confirm.",
    )

    payload = get_ai_monitor_payload(hours=1, limit=20)
    issue_types = {item["issue_type"] for item in payload["issues"]}

    assert "Asked for screenshot after proof" in issue_types
    assert any(item["customer_phone"] == phone for item in payload["journeys"])

    with get_db_connection() as connection:
        row = connection.execute(
            "SELECT issue_count FROM ai_monitor_journeys WHERE customer_phone = ?",
            (phone,),
        ).fetchone()
        assert row is not None
        assert row["issue_count"] >= 1


if __name__ == "__main__":
    test_ai_monitor_flags_reply_quality_issues()
    test_ai_monitor_detects_payment_proof_repeat_and_materializes_journey()
