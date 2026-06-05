from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.runtime_db import ensure_runtime_tables, get_db_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


DEFAULT_JOURNEY_NAME = "Default Product Follow-up"
LEGACY_DEFAULT_JOURNEY_NAMES = {
    "Default Product Interest Follow-up",
    DEFAULT_JOURNEY_NAME,
}

DEFAULT_JOURNEY_STEPS = [
    {
        "step_order": 1,
        "delay_value": 4,
        "delay_unit": "minutes",
        "message_type": "text",
        "message_text": "Order venenkil peru, address, phone number, pincode ayacholu 😊",
    },
    {
        "step_order": 2,
        "delay_value": 4,
        "delay_unit": "hours",
        "message_type": "text_with_image",
        "message_text": "Ithu venenkil innu dispatch cheyyan try cheyyam. Fresh stock aanu 😊",
    },
    {
        "step_order": 3,
        "delay_value": 10,
        "delay_unit": "hours",
        "message_type": "combo",
        "message_text": "Combo order aanenkil, allenkil ₹600 above order aanenkil delivery free aanu.",
    },
    {
        "step_order": 4,
        "delay_value": 23,
        "delay_unit": "hours",
        "message_type": "text",
        "message_text": "Ithu close cheyyatte? Venamengil quantity paranjal order ready cheyyam 😊",
    },
]


def _minutes_from_step(step: dict[str, Any]) -> int:
    value = max(1, int(step.get("delay_value") or 1))
    unit = str(step.get("delay_unit") or "minutes").lower()
    if unit.startswith("hour"):
        return value * 60
    if unit.startswith("day"):
        return value * 1440
    return value


def _replace_journey_steps(conn: Any, journey_id: str, now: str) -> None:
    conn.execute("DELETE FROM customer_journey_steps WHERE journey_id = ?", (journey_id,))
    for step in DEFAULT_JOURNEY_STEPS:
        conn.execute(
            """
            INSERT INTO customer_journey_steps
            (id, journey_id, step_order, delay_value, delay_unit, message_type,
             message_text, active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                journey_id,
                step["step_order"],
                step["delay_value"],
                step["delay_unit"],
                step["message_type"],
                step["message_text"],
                now,
                now,
            ),
        )


def ensure_default_customer_journey() -> None:
    ensure_runtime_tables()
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT id, name FROM customer_journeys
            WHERE trigger_type = 'product_interest' AND status = 'active'
            ORDER BY updated_at DESC
            LIMIT 1
            """
        ).fetchone()
        now = _now()
        if row:
            if str(row["name"] or "") in LEGACY_DEFAULT_JOURNEY_NAMES:
                conn.execute(
                    """
                    UPDATE customer_journeys
                    SET name = ?,
                        description = ?,
                        applies_to = 'all_products',
                        selected_products_json = '[]',
                        stop_on_reply = 1,
                        stop_on_order = 1,
                        stop_on_not_interested = 1,
                        stop_on_stop = 1,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        DEFAULT_JOURNEY_NAME,
                        "Clean follow-up journey after a product reply: 4 minutes, 4 hours, 10 hours, and 23 hours.",
                        now,
                        row["id"],
                    ),
                )
                _replace_journey_steps(conn, row["id"], now)
                conn.commit()
            return
        journey_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO customer_journeys
            (id, name, description, status, applies_to, selected_products_json,
             trigger_type, stop_on_reply, stop_on_order, stop_on_not_interested,
             stop_on_stop, created_at, updated_at)
            VALUES (?, ?, ?, 'active', 'all_products', '[]', 'product_interest', 1, 1, 1, 1, ?, ?)
            """,
            (
                journey_id,
                DEFAULT_JOURNEY_NAME,
                "Clean follow-up journey after a product reply: 4 minutes, 4 hours, 10 hours, and 23 hours.",
                now,
                now,
            ),
        )
        _replace_journey_steps(conn, journey_id, now)
        conn.commit()


def _row_to_journey(row: Any, steps: list[dict[str, Any]]) -> dict[str, Any]:
    item = dict(row)
    return {
        "id": item["id"],
        "name": item["name"],
        "description": item["description"],
        "status": item["status"],
        "applies_to": item["applies_to"],
        "selected_products": json.loads(item.get("selected_products_json") or "[]"),
        "trigger_type": item["trigger_type"],
        "stop_on_reply": bool(item["stop_on_reply"]),
        "stop_on_order": bool(item["stop_on_order"]),
        "stop_on_not_interested": bool(item["stop_on_not_interested"]),
        "stop_on_stop": bool(item["stop_on_stop"]),
        "created_at": item["created_at"],
        "updated_at": item["updated_at"],
        "steps": steps,
    }


def list_customer_journeys() -> dict[str, Any]:
    ensure_default_customer_journey()
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM customer_journeys ORDER BY status = 'active' DESC, updated_at DESC"
        ).fetchall()
        journeys: list[dict[str, Any]] = []
        for row in rows:
            step_rows = conn.execute(
                "SELECT * FROM customer_journey_steps WHERE journey_id = ? ORDER BY step_order ASC",
                (row["id"],),
            ).fetchall()
            steps = [dict(step) for step in step_rows]
            journeys.append(_row_to_journey(row, steps))
        return {"items": journeys, "count": len(journeys)}


def get_active_journey_plan(product_key: str | None, trigger_type: str = "product_interest") -> list[dict[str, Any]]:
    ensure_default_customer_journey()
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM customer_journeys
            WHERE status = 'active' AND trigger_type = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (trigger_type,),
        ).fetchone()
        if not row:
            return []
        selected_products = json.loads(row["selected_products_json"] or "[]")
        if row["applies_to"] == "selected_products" and product_key not in selected_products:
            return []
        step_rows = conn.execute(
            """
            SELECT *
            FROM customer_journey_steps
            WHERE journey_id = ? AND active = 1
            ORDER BY step_order ASC
            """,
            (row["id"],),
        ).fetchall()

    plan: list[dict[str, Any]] = []
    for step in step_rows:
        step_dict = dict(step)
        plan.append(
            {
                "after_minutes": _minutes_from_step(step_dict),
                "stage": step_dict.get("message_type") or "text",
                "message_type": step_dict.get("message_type") or "text",
                "message_text": step_dict.get("message_text") or "",
                "journey_id": row["id"],
                "journey_step_id": step_dict["id"],
            }
        )
    return plan


def record_customer_journey_assignment(
    *,
    journey_id: str,
    customer_phone: str,
    product_key: str | None = None,
    context: dict[str, Any] | None = None,
) -> str:
    ensure_runtime_tables()
    assignment_id = str(uuid.uuid4())
    now = _now()
    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE customer_journey_assignments
            SET status = 'replaced',
                stopped_at = ?,
                stop_reason = 'new_assignment_replaced'
            WHERE customer_phone = ?
              AND journey_id = ?
              AND status = 'active'
            """,
            (now, customer_phone, journey_id),
        )
        conn.execute(
            """
            INSERT INTO customer_journey_assignments
            (id, journey_id, customer_phone, product_key, status, started_at, context_json)
            VALUES (?, ?, ?, ?, 'active', ?, ?)
            """,
            (
                assignment_id,
                journey_id,
                customer_phone,
                product_key,
                now,
                json.dumps(context or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
    return assignment_id


def log_customer_journey_event(
    *,
    customer_phone: str,
    event_type: str,
    journey_id: str | None = None,
    step_id: str | None = None,
    product_key: str | None = None,
    message_text: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    ensure_runtime_tables()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO customer_journey_logs
            (id, journey_id, step_id, customer_phone, product_key, event_type,
             message_text, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                journey_id,
                step_id,
                customer_phone,
                product_key,
                event_type,
                message_text[:4000],
                json.dumps(metadata or {}, ensure_ascii=False),
                _now(),
            ),
        )
        conn.commit()


def stop_customer_journeys_for_customer(
    *,
    customer_phone: str,
    reason: str,
    stop_flag: str = "stop_on_reply",
) -> int:
    """Stop active journey assignments and pending followups when a stop rule matches."""
    if not customer_phone:
        return 0
    allowed_flags = {"stop_on_reply", "stop_on_order", "stop_on_not_interested", "stop_on_stop"}
    flag = stop_flag if stop_flag in allowed_flags else "stop_on_reply"
    now = _now()
    ensure_runtime_tables()
    with get_db_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT cja.id, cja.journey_id, cja.product_key
            FROM customer_journey_assignments cja
            JOIN customer_journeys cj ON cj.id = cja.journey_id
            WHERE cja.customer_phone = ?
              AND cja.status = 'active'
              AND cj.{flag} = 1
            """,
            (customer_phone,),
        ).fetchall()
        if not rows:
            return 0
        assignment_ids = [row["id"] for row in rows]
        placeholders = ",".join("?" for _ in assignment_ids)
        conn.execute(
            f"""
            UPDATE customer_journey_assignments
            SET status = 'stopped',
                stopped_at = ?,
                stop_reason = ?
            WHERE id IN ({placeholders})
            """,
            (now, reason, *assignment_ids),
        )
        conn.execute(
            """
            UPDATE product_journey_followups
            SET sent = 1,
                sent_at = ?,
                send_status = 'cancelled',
                send_error = ?,
                updated_at = ?
            WHERE phone = ?
              AND sent = 0
              AND send_status = 'queued'
            """,
            (now, reason, now, customer_phone),
        )
        for row in rows:
            conn.execute(
                """
                INSERT INTO customer_journey_logs
                (id, journey_id, step_id, customer_phone, product_key, event_type,
                 message_text, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    row["journey_id"],
                    None,
                    customer_phone,
                    row["product_key"],
                    "journey_stopped",
                    reason,
                    json.dumps({"stop_flag": flag, "assignment_id": row["id"]}, ensure_ascii=False),
                    now,
                ),
            )
        conn.commit()
    return len(rows)


def save_customer_journey(payload: dict[str, Any], journey_id: str | None = None) -> dict[str, Any]:
    ensure_runtime_tables()
    now = _now()
    item_id = journey_id or str(payload.get("id") or uuid.uuid4())
    selected_products = payload.get("selected_products") or payload.get("selected_products_json") or []
    if isinstance(selected_products, str):
        try:
            selected_products = json.loads(selected_products)
        except json.JSONDecodeError:
            selected_products = [value.strip() for value in selected_products.split(",") if value.strip()]
    steps = payload.get("steps") or []
    with get_db_connection() as conn:
        exists = conn.execute("SELECT 1 FROM customer_journeys WHERE id = ?", (item_id,)).fetchone()
        values = (
            str(payload.get("name") or "Customer Journey").strip(),
            str(payload.get("description") or "").strip(),
            str(payload.get("status") or "draft").strip(),
            str(payload.get("applies_to") or "all_products").strip(),
            json.dumps(selected_products, ensure_ascii=False),
            str(payload.get("trigger_type") or "product_interest").strip(),
            1 if payload.get("stop_on_reply", True) else 0,
            1 if payload.get("stop_on_order", True) else 0,
            1 if payload.get("stop_on_not_interested", True) else 0,
            1 if payload.get("stop_on_stop", True) else 0,
            now,
            item_id,
        )
        if exists:
            conn.execute(
                """
                UPDATE customer_journeys
                SET name = ?, description = ?, status = ?, applies_to = ?,
                    selected_products_json = ?, trigger_type = ?, stop_on_reply = ?,
                    stop_on_order = ?, stop_on_not_interested = ?, stop_on_stop = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                values,
            )
            conn.execute("DELETE FROM customer_journey_steps WHERE journey_id = ?", (item_id,))
        else:
            conn.execute(
                """
                INSERT INTO customer_journeys
                (id, name, description, status, applies_to, selected_products_json,
                 trigger_type, stop_on_reply, stop_on_order, stop_on_not_interested,
                 stop_on_stop, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    values[0],
                    values[1],
                    values[2],
                    values[3],
                    values[4],
                    values[5],
                    values[6],
                    values[7],
                    values[8],
                    values[9],
                    now,
                    now,
                ),
            )
        for index, step in enumerate(steps, start=1):
            conn.execute(
                """
                INSERT INTO customer_journey_steps
                (id, journey_id, step_order, delay_value, delay_unit, message_type,
                 message_text, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(step.get("id") or uuid.uuid4()),
                    item_id,
                    int(step.get("step_order") or index),
                    int(step.get("delay_value") or 1),
                    str(step.get("delay_unit") or "minutes"),
                    str(step.get("message_type") or "text"),
                    str(step.get("message_text") or ""),
                    1 if step.get("active", True) else 0,
                    now,
                    now,
                ),
            )
        conn.commit()
    return next(item for item in list_customer_journeys()["items"] if item["id"] == item_id)


def delete_customer_journey(journey_id: str) -> dict[str, Any]:
    ensure_runtime_tables()
    with get_db_connection() as conn:
        conn.execute("DELETE FROM customer_journey_steps WHERE journey_id = ?", (journey_id,))
        cursor = conn.execute("DELETE FROM customer_journeys WHERE id = ?", (journey_id,))
        conn.commit()
    return {"ok": bool(cursor.rowcount), "deleted": journey_id}
