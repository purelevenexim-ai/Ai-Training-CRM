from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.ai.conversation_state_manager import get_conversation_state, set_conversation_state
from app.ai.pricing_formatter import PricingFormatter
from app.ai.whatsapp_delivery_service import send_whatsapp_reply_with_fallback
from app.config import settings
from app.runtime_db import ensure_runtime_tables, get_db_connection
from app.services.owner_dashboard_service import get_ai_control_settings

logger = logging.getLogger(__name__)


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _now() -> str:
    return _now_dt().isoformat()


FOLLOWUP_STAGE_COPY: dict[str, dict[str, str]] = {
    "gentle_reminder": {
        "english": "Just checking in. If you'd like, I can help you choose the best pack and order it today.",
        "manglish": "Just check cheyyan aanu. Venengil best option suggest cheythu order help cheyyam.",
        "malayalam": "ഒന്ന് follow up ചെയ്യുന്നതാണ്. വേണമെങ്കിൽ ഏറ്റവും നല്ല option suggest ചെയ്ത് order help ചെയ്യാം.",
    },
    "combo_offer": {
        "english": "If you want better value, here are the combo packs customers usually like.",
        "manglish": "Value nokkiyal combo packs aanu best. Njan thazhe options share cheyyam.",
        "malayalam": "നല്ല വില നോക്കുകയാണെങ്കിൽ combo packs ആണ് best. താഴെ options share ചെയ്യാം.",
    },
    "image_only": {
        "english": "",
        "manglish": "",
        "malayalam": "",
    },
    "soft_nudge": {
        "english": "If you're still interested, reply with your name, full address, pincode, and quantity.",
        "manglish": "Still interested aanenkil name, full address, pincode, quantity ayacholu. Next step help cheyyam.",
        "malayalam": "ഇനിയും താൽപ്പര്യമുണ്ടെങ്കിൽ പേര്, പൂർണ്ണ വിലാസം, pincode, quantity അയയ്ക്കൂ. അടുത്ത step help ചെയ്യും.",
    },
    "final_followup": {
        "english": "I’ll keep this open for now. If you want to continue later, just reply with the product name.",
        "manglish": "Ippo ithu open aayi vechittundu. Pinne venengil product name ayachal mathi.",
        "malayalam": "ഇപ്പോൾ ഇത് തുറന്ന നിലയിലാണ്. പിന്നീട് വേണമെങ്കിൽ product name അയച്ചാൽ മതി.",
    },
    "order_capture_reminder": {
        "english": "If you'd like to confirm the order, please share your name, full address, pincode, phone number, and quantity.",
        "manglish": "Order confirm cheyyan venengil name, full address, pincode, phone number, quantity ayacholu. Njan total confirm cheythu help cheyyam.",
        "malayalam": "Order confirm ചെയ്യാൻ വേണമെങ്കിൽ പേര്, പൂർണ്ണ വിലാസം, pincode, ഫോൺ നമ്പർ, quantity അയയ്ക്കൂ. ഞാൻ total confirm ചെയ്ത് help ചെയ്യും.",
    },
    "payment_reminder": {
        "english": "Payment pending aanu. If payment is done, please share the screenshot or transaction reference so we can confirm it.",
        "manglish": "Payment pending aanu. Payment kazhinjengil screenshot allenkil transaction reference ayacholu, confirm cheyyam.",
        "malayalam": "Payment pending ആണ്. Payment കഴിഞ്ഞാൽ screenshot അല്ലെങ്കിൽ transaction reference അയച്ചോളൂ, confirm ചെയ്യാം.",
    },
    "order_confirmation": {
        "english": "Order details received 😊 We’ll confirm the total and dispatch update shortly.",
        "manglish": "Order details kitti 😊 Total confirm cheythu dispatch update share cheyyam.",
        "malayalam": "Order details കിട്ടി 😊 Total confirm ചെയ്ത് dispatch update share ചെയ്യാം.",
    },
}


def _scenario_from_intent(intent: str | None) -> str:
    normalized = str(intent or "").strip().lower()
    scenario_map = {
        "purchase_intent": "order_request",
        "availability": "availability",
        "stock_check": "availability",
        "price": "price",
        "details": "details",
        "quality": "quality",
        "origin": "origin",
        "processing": "processing",
        "usage": "usage",
        "benefits": "benefits",
        "best_pack": "best_pack",
        "budget": "budget",
        "combo": "combo",
        "comparison": "comparison",
        "price_objection": "price_objection",
        "delivery_charge": "delivery_charge",
        "delivery_time": "delivery_time",
        "free_delivery": "free_delivery",
        "order_request": "order_request",
        "order_confirm": "order_confirm",
        "followup": "details",
        "fallback": "fallback",
    }
    return scenario_map.get(normalized, "availability")


def _followup_message_mode(stage: str) -> str:
    if stage in {"text_with_image", "order_capture"}:
        return "text_with_image"
    if stage == "image_only":
        return "image_only"
    if stage == "combo":
        return "text"
    if stage == "latent_handoff":
        return "text_with_image"
    if stage in {"gentle_reminder", "soft_nudge", "order_capture_reminder"}:
        return "text_with_image"
    return "text"


def _followup_media_urls(product_key: str | None) -> list[str]:
    if not product_key:
        return []
    return PricingFormatter.get_product_image_urls(product_key)[:3]


def _render_followup_payload(item: dict[str, Any]) -> dict[str, Any]:
    style = item.get("reply_style") or "english"
    stage = item.get("followup_stage") or "gentle_reminder"
    scenario = item.get("scenario") or "availability"
    product_key = item.get("product_key")
    customer_reference = item.get("customer_reference")
    media_urls = _followup_media_urls(product_key)
    media_mode = _followup_message_mode(stage)
    context = json.loads(item.get("context_json") or "{}") if item.get("context_json") else {}
    custom_message = str(context.get("message_text") or "").strip()
    custom_message_type = str(context.get("message_type") or stage or "text").strip()

    if custom_message_type == "image_only":
        return {
            "reply_text": "",
            "media_urls": media_urls,
            "media_caption": "",
            "media_mode": "image_only",
            "scenario": scenario,
        }

    if custom_message_type == "combo":
        reply_text = PricingFormatter.format_combo_response(style=style)
        if custom_message:
            reply_text = f"{custom_message}\n\n{reply_text}".strip()
        return {
            "reply_text": reply_text,
            "media_urls": [],
            "media_caption": "",
            "media_mode": "text",
            "scenario": scenario,
        }

    if custom_message:
        return {
            "reply_text": custom_message,
            "media_urls": media_urls[:1],
            "media_caption": customer_reference or "",
            "media_mode": "text_with_image" if custom_message_type == "text_with_image" else "text",
            "scenario": scenario,
        }

    if stage == "latent_handoff":
        latent_scenario = str(context.get("scenario") or scenario or "availability")
        latent_reference = customer_reference or context.get("customer_reference")
        latent_payload = (
            PricingFormatter.build_product_journey_reply_payload(
                product_key,
                style=style,
                scenario=latent_scenario,
                customer_reference=latent_reference,
            )
            if product_key
            else None
        )
        if latent_payload:
            return {
                "reply_text": latent_payload.get("reply_text", ""),
                "media_urls": latent_payload.get("image_urls", []),
                "media_caption": str(latent_reference or ""),
                "media_mode": "image" if latent_payload.get("image_urls") else "text",
                "scenario": latent_scenario,
            }
        return {
            "reply_text": str(context.get("source_message") or "").strip(),
            "media_urls": [],
            "media_caption": "",
            "media_mode": "text",
            "scenario": latent_scenario,
        }

    if stage == "image_only":
        return {
            "reply_text": "",
            "media_urls": media_urls,
            "media_caption": "",
            "media_mode": "image_only",
            "scenario": scenario,
        }

    if stage == "combo_offer":
        reply_text = PricingFormatter.format_combo_response(style=style)
        if scenario in {"order_intent", "order_request", "order_confirm"}:
            reply_text = (
                f"{reply_text}\n\n"
                + PricingFormatter.build_order_capture_reply(style=style)
            )
        return {
            "reply_text": reply_text,
            "media_urls": [],
            "media_caption": "",
            "media_mode": "text",
            "scenario": scenario,
        }

    if stage == "order_capture_reminder":
        reply_text = PricingFormatter.build_order_capture_reply(style=style)
        return {
            "reply_text": reply_text,
            "media_urls": media_urls[:1],
            "media_caption": customer_reference or "",
            "media_mode": media_mode,
            "scenario": scenario,
        }

    if stage in {"payment_reminder", "order_confirmation"}:
        reply_text = FOLLOWUP_STAGE_COPY[stage].get(style) or FOLLOWUP_STAGE_COPY[stage]["english"]
        return {
            "reply_text": reply_text,
            "media_urls": [],
            "media_caption": "",
            "media_mode": "text",
            "scenario": scenario,
        }

    if stage == "final_followup":
        reply_text = FOLLOWUP_STAGE_COPY[stage].get(style) or FOLLOWUP_STAGE_COPY[stage]["english"]
        return {
            "reply_text": reply_text,
            "media_urls": [],
            "media_caption": "",
            "media_mode": "text",
            "scenario": scenario,
        }

    base_copy = FOLLOWUP_STAGE_COPY.get(stage, FOLLOWUP_STAGE_COPY["gentle_reminder"]).get(style)
    if base_copy is None:
        base_copy = FOLLOWUP_STAGE_COPY.get(stage, FOLLOWUP_STAGE_COPY["gentle_reminder"])["english"]

    if product_key:
        product_name = str(customer_reference or product_key).replace("_", " ").strip()
        if style == "manglish":
            followup_intro = f"{product_name} inu interest undenkil reply cheyyu."
        elif style == "malayalam":
            followup_intro = f"{product_name} ന്റെ കാര്യമെങ്കിൽ reply ചെയ്യൂ."
        else:
            followup_intro = f"If {product_name} is still on your mind, reply and I’ll help."
        reply_text = f"{base_copy}\n\n{followup_intro}".strip()
    else:
        reply_text = base_copy

    return {
        "reply_text": reply_text,
        "media_urls": media_urls[:1],
        "media_caption": customer_reference or "",
        "media_mode": media_mode,
        "scenario": scenario,
    }


def queue_product_followups(
    phone: str,
    product_key: str | None,
    scenario: str,
    reply_style: str,
    follow_up_plan: list[dict[str, Any]],
    customer_reference: str | None = None,
) -> int:
    """Replace any pending followups for the phone with a fresh plan."""
    if not phone or not follow_up_plan:
        return 0

    now = _now()
    ensure_runtime_tables()
    log_customer_journey_event = None
    record_customer_journey_assignment = None
    try:
        from app.services.customer_journey_service import (
            get_active_journey_plan,
            log_customer_journey_event,
            record_customer_journey_assignment,
        )

        configured_plan = get_active_journey_plan(product_key, trigger_type="product_interest")
        if configured_plan:
            follow_up_plan = configured_plan
    except Exception as exc:
        logger.warning("Customer journey plan fallback to static plan for %s: %s", phone, exc)

    active_journey_id = str((follow_up_plan[0] or {}).get("journey_id") or "") if follow_up_plan else ""
    assignment_id = ""
    if active_journey_id and record_customer_journey_assignment:
        assignment_id = record_customer_journey_assignment(
            journey_id=active_journey_id,
            customer_phone=phone,
            product_key=product_key,
            context={
                "scenario": scenario,
                "reply_style": reply_style,
                "customer_reference": customer_reference,
            },
        )

    journey_step_logs: list[dict[str, Any]] = []
    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE product_journey_followups
            SET send_status = 'replaced', updated_at = ?
            WHERE phone = ? AND sent = 0 AND send_status = 'queued'
            """,
            (now, phone),
        )

        count = 0
        for slot in follow_up_plan:
            scheduled_at = (_now_dt() + timedelta(minutes=int(slot.get("after_minutes", 0)))).isoformat()
            stage = str(slot.get("stage", "gentle_reminder"))
            message_mode = _followup_message_mode(stage)
            context = {
                "product_key": product_key,
                "scenario": scenario,
                "reply_style": reply_style,
                "customer_reference": customer_reference,
                "message_text": slot.get("message_text") or "",
                "message_type": slot.get("message_type") or stage,
                "journey_id": slot.get("journey_id") or "",
                "journey_step_id": slot.get("journey_step_id") or "",
                "assignment_id": assignment_id,
            }
            conn.execute(
                """
                INSERT INTO product_journey_followups
                (id, phone, conversation_phone, product_key, scenario, reply_style,
                 customer_reference, followup_stage, scheduled_at, message_mode, media_json, context_json,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    phone,
                    phone,
                    product_key,
                    scenario,
                    reply_style,
                    customer_reference,
                    stage,
                    scheduled_at,
                    message_mode,
                    json.dumps({"message_mode": message_mode}, ensure_ascii=False),
                    json.dumps(context, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            if slot.get("journey_id"):
                journey_step_logs.append(
                    {
                        "journey_id": str(slot.get("journey_id") or ""),
                        "step_id": str(slot.get("journey_step_id") or ""),
                        "product_key": product_key,
                        "event_type": "step_queued",
                        "message_text": str(slot.get("message_text") or stage),
                        "metadata": {
                            "scheduled_at": scheduled_at,
                            "message_type": slot.get("message_type") or stage,
                            "assignment_id": assignment_id,
                        },
                    }
                )
            count += 1
        conn.commit()
    if log_customer_journey_event:
        for item in journey_step_logs:
            log_customer_journey_event(
                customer_phone=phone,
                **item,
            )
    return count


def queue_latent_handoff_followup(
    *,
    phone: str,
    product_key: str | None,
    detected_intent: str,
    reply_style: str,
    customer_reference: str | None = None,
    source_message: str = "",
    after_minutes: int = 5,
) -> int:
    """Queue a delayed AI handoff after Wabis gets first chance to complete its flow."""
    if not phone or not product_key:
        return 0

    now = _now()
    scenario = _scenario_from_intent(detected_intent)
    ensure_runtime_tables()
    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE product_journey_followups
            SET send_status = 'replaced', updated_at = ?
            WHERE phone = ? AND sent = 0 AND send_status = 'queued' AND followup_stage = 'latent_handoff'
            """,
            (now, phone),
        )
        scheduled_at = (_now_dt() + timedelta(minutes=max(1, int(after_minutes)))).isoformat()
        context = {
            "product_key": product_key,
            "scenario": scenario,
            "reply_style": reply_style,
            "customer_reference": customer_reference,
            "source_message": source_message,
            "latent_intent": detected_intent,
            "priority_minutes": max(1, int(after_minutes)),
        }
        conn.execute(
            """
            INSERT INTO product_journey_followups
            (id, phone, conversation_phone, product_key, scenario, reply_style,
             customer_reference, followup_stage, scheduled_at, message_mode, media_json, context_json,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                phone,
                phone,
                product_key,
                scenario,
                reply_style,
                customer_reference,
                "latent_handoff",
                scheduled_at,
                _followup_message_mode("latent_handoff"),
                json.dumps({"message_mode": "text_with_image"}, ensure_ascii=False),
                json.dumps(context, ensure_ascii=False),
                now,
                now,
            ),
        )
        conn.commit()
    return 1


def cancel_product_followups(phone: str, reason: str = "cancelled", stages: set[str] | None = None) -> int:
    """Cancel any unsent followups for a phone when the journey should stop."""
    if not phone:
        return 0

    now = _now()
    ensure_runtime_tables()
    query = """
        UPDATE product_journey_followups
        SET sent = 1, sent_at = ?, send_status = 'cancelled', send_error = ?, updated_at = ?
        WHERE phone = ? AND sent = 0 AND send_status = 'queued'
    """
    params: list[Any] = [now, reason, now, phone]
    if stages:
        placeholders = ",".join("?" for _ in stages)
        query += f" AND followup_stage IN ({placeholders})"
        params.extend(sorted(stages))

    with get_db_connection() as conn:
        cursor = conn.execute(query, tuple(params))
        conn.commit()
        return int(cursor.rowcount or 0)


def _customer_has_purchased(conn, phone: str) -> bool:
    if not phone:
        return False

    if _table_exists(conn, "customers"):
        row = conn.execute(
            """
            SELECT 1
            FROM customers
            WHERE phone = ?
              AND (
                LOWER(COALESCE(purchase_status, '')) = 'purchased'
                OR COALESCE(total_orders, 0) > 0
              )
            LIMIT 1
            """,
            (phone,),
        ).fetchone()
        if row:
            return True

    if _table_exists(conn, "journey_customers"):
        row = conn.execute(
            """
            SELECT 1
            FROM journey_customers
            WHERE phone = ? AND COALESCE(purchase_count, 0) > 0
            LIMIT 1
            """,
            (phone,),
        ).fetchone()
        if row:
            return True

    return False


def _table_exists(connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _defer_followup_if_wabis_recent(
    item: dict[str, Any],
    state: dict[str, Any],
    control: dict[str, Any],
) -> str | None:
    if str(item.get("followup_stage") or "") != "latent_handoff":
        return None

    last_activity_raw = state.get("last_activity") or state.get("updated_at")
    if not last_activity_raw:
        return None

    try:
        last_activity = datetime.fromisoformat(str(last_activity_raw))
    except ValueError:
        return None

    priority_minutes = max(1, int(control.get("wabis_priority_minutes", 5)))
    next_due = last_activity + timedelta(minutes=priority_minutes)
    if next_due > _now_dt():
        return next_due.isoformat()
    return None


def _activate_product_journey_from_latent(item: dict[str, Any], scenario: str) -> None:
    product_key = item.get("product_key")
    reply_style = item.get("reply_style") or "english"
    customer_reference = item.get("customer_reference")
    if not item.get("phone") or not product_key:
        return

    from app.ai.wabis_reply_generator import WabisReplyGenerator

    plan = WabisReplyGenerator._build_follow_up_plan(scenario)
    set_conversation_state(
        phone=item["phone"],
        owner="ai",
        owner_reason=f"product_{scenario}",
        flow_id="product_journey",
        flow_step="awaiting_customer_reply" if scenario != "order_intent" else "awaiting_order_details",
        expected_responses="yes,no,price,delivery,order,wholesale",
        context={
            "product_key": product_key,
            "scenario": scenario,
            "reply_style": reply_style,
            "customer_reference": customer_reference,
            "follow_up_plan": plan,
        },
    )
    if plan:
        queue_product_followups(
            phone=item["phone"],
            product_key=product_key,
            scenario=scenario,
            reply_style=reply_style,
            follow_up_plan=plan,
            customer_reference=customer_reference,
        )


def _write_customer_journey_log_for_followup(
    conn,
    item: dict[str, Any],
    *,
    event_type: str,
    message_text: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    context = json.loads(item.get("context_json") or "{}") if item.get("context_json") else {}
    journey_id = str(context.get("journey_id") or "").strip()
    if not journey_id:
        return
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
            str(context.get("journey_step_id") or "") or None,
            item["phone"],
            item.get("product_key"),
            event_type,
            message_text[:4000],
            json.dumps(metadata or {}, ensure_ascii=False),
            _now(),
        ),
    )


def preview_due_product_followups(limit: int = 25) -> list[dict[str, Any]]:
    """Return due followups and rendered reply text without sending or updating state."""
    now = _now()
    ensure_runtime_tables()
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM product_journey_followups
            WHERE sent = 0 AND send_status = 'queued' AND scheduled_at <= ?
            ORDER BY scheduled_at ASC
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()

    previews: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        payload = _render_followup_payload(item)
        previews.append(
            {
                "id": item["id"],
                "phone": item["phone"],
                "stage": item["followup_stage"],
                "scheduled_at": item["scheduled_at"],
                "reply_text": payload["reply_text"],
                "media_mode": payload["media_mode"],
                "image_urls": payload["media_urls"],
            }
        )
    return previews


def run_due_product_followups(limit: int = 100, send_live: bool | None = None) -> list[dict[str, Any]]:
    """Process queued product followups that are due."""
    now = _now()
    processed: list[dict[str, Any]] = []
    activations: list[tuple[dict[str, Any], str]] = []
    control = get_ai_control_settings()
    if not control.get("ai_running", True):
        return processed

    live_mode = (
        bool(control.get("followup_send_enabled", settings.ai_followup_send_enabled))
        if send_live is None
        else send_live
    )

    ensure_runtime_tables()
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM product_journey_followups
            WHERE sent = 0 AND send_status = 'queued' AND scheduled_at <= ?
            ORDER BY scheduled_at ASC
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()

        for row in rows:
            item = dict(row)
            state = get_conversation_state(item["phone"])

            if _customer_has_purchased(conn, item["phone"]):
                conn.execute(
                    """
                    UPDATE product_journey_followups
                    SET sent = 1, sent_at = ?, send_status = 'suppressed', send_error = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (now, "purchase_detected", now, item["id"]),
                )
                _write_customer_journey_log_for_followup(
                    conn,
                    item,
                    event_type="step_suppressed",
                    message_text=item.get("reply_text") or item.get("followup_stage") or "",
                    metadata={
                        "followup_id": item["id"],
                        "stage": item["followup_stage"],
                        "reason": "purchase_detected",
                        "send_live": live_mode,
                    },
                )
                processed.append(
                    {
                        "id": item["id"],
                        "phone": item["phone"],
                        "stage": item["followup_stage"],
                        "send_status": "suppressed",
                        "send_live": live_mode,
                    }
                )
                continue

            if state and state.get("owner") in {"human", "campaign", "system"}:
                reason = f"owner={state.get('owner')}"
                conn.execute(
                    """
                    UPDATE product_journey_followups
                    SET sent = 1, sent_at = ?, send_status = 'suppressed', send_error = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (now, reason, now, item["id"]),
                )
                _write_customer_journey_log_for_followup(
                    conn,
                    item,
                    event_type="step_suppressed",
                    message_text=item.get("reply_text") or item.get("followup_stage") or "",
                    metadata={
                        "followup_id": item["id"],
                        "stage": item["followup_stage"],
                        "reason": reason,
                        "send_live": live_mode,
                    },
                )
                processed.append(
                    {
                        "id": item["id"],
                        "phone": item["phone"],
                        "stage": item["followup_stage"],
                        "send_status": "suppressed",
                        "send_live": live_mode,
                    }
                )
                continue

            if state and state.get("owner") == "wabis" and item.get("followup_stage") != "latent_handoff":
                conn.execute(
                    """
                    UPDATE product_journey_followups
                    SET sent = 1, sent_at = ?, send_status = 'suppressed', send_error = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (now, "wabis_flow_active", now, item["id"]),
                )
                _write_customer_journey_log_for_followup(
                    conn,
                    item,
                    event_type="step_suppressed",
                    message_text=item.get("reply_text") or item.get("followup_stage") or "",
                    metadata={
                        "followup_id": item["id"],
                        "stage": item["followup_stage"],
                        "reason": "wabis_flow_active",
                        "send_live": live_mode,
                    },
                )
                processed.append(
                    {
                        "id": item["id"],
                        "phone": item["phone"],
                        "stage": item["followup_stage"],
                        "send_status": "suppressed",
                        "send_live": live_mode,
                    }
                )
                continue

            if item.get("followup_stage") == "latent_handoff":
                latent_context = (state or {}).get("context") or {}
                latent_handoff = latent_context.get("latent_handoff") if isinstance(latent_context, dict) else None
                if not state or state.get("owner") != "wabis" or not isinstance(latent_handoff, dict):
                    conn.execute(
                        """
                        UPDATE product_journey_followups
                        SET sent = 1, sent_at = ?, send_status = 'suppressed', send_error = ?, updated_at = ?
                        WHERE id = ?
                    """,
                    (now, "latent_handoff_no_longer_needed", now, item["id"]),
                )
                    _write_customer_journey_log_for_followup(
                        conn,
                        item,
                        event_type="step_suppressed",
                        message_text=item.get("reply_text") or item.get("followup_stage") or "",
                        metadata={
                            "followup_id": item["id"],
                            "stage": item["followup_stage"],
                            "reason": "latent_handoff_no_longer_needed",
                            "send_live": live_mode,
                        },
                    )
                    processed.append(
                        {
                            "id": item["id"],
                            "phone": item["phone"],
                            "stage": item["followup_stage"],
                            "send_status": "suppressed",
                            "send_live": live_mode,
                        }
                    )
                    continue

                deferred_until = _defer_followup_if_wabis_recent(item, state, control)
                if deferred_until:
                    conn.execute(
                        """
                        UPDATE product_journey_followups
                        SET scheduled_at = ?, updated_at = ?, send_error = ?
                        WHERE id = ?
                        """,
                        (deferred_until, now, "waiting_for_wabis_completion", item["id"]),
                    )
                    _write_customer_journey_log_for_followup(
                        conn,
                        item,
                        event_type="step_deferred",
                        message_text=item.get("reply_text") or item.get("followup_stage") or "",
                        metadata={
                            "followup_id": item["id"],
                            "stage": item["followup_stage"],
                            "reason": "waiting_for_wabis_completion",
                            "deferred_until": deferred_until,
                            "send_live": live_mode,
                        },
                    )
                    processed.append(
                        {
                            "id": item["id"],
                            "phone": item["phone"],
                            "stage": item["followup_stage"],
                            "send_status": "deferred",
                            "send_live": live_mode,
                        }
                    )
                    continue

            if item.get("followup_stage") != "latent_handoff":
                if not state or state.get("flow_id") != "product_journey" or state.get("owner") != "ai":
                    conn.execute(
                        """
                        UPDATE product_journey_followups
                        SET sent = 1, sent_at = ?, send_status = 'suppressed', send_error = ?, updated_at = ?
                        WHERE id = ?
                    """,
                    (now, "product_journey_inactive", now, item["id"]),
                )
                    _write_customer_journey_log_for_followup(
                        conn,
                        item,
                        event_type="step_suppressed",
                        message_text=item.get("reply_text") or item.get("followup_stage") or "",
                        metadata={
                            "followup_id": item["id"],
                            "stage": item["followup_stage"],
                            "reason": "product_journey_inactive",
                            "send_live": live_mode,
                        },
                    )
                    processed.append(
                        {
                            "id": item["id"],
                            "phone": item["phone"],
                            "stage": item["followup_stage"],
                            "send_status": "suppressed",
                            "send_live": live_mode,
                        }
                    )
                    continue

            if state and state.get("flow_id") == "product_journey" and item.get("product_key"):
                active_product = ((state.get("context") or {}).get("product_key") or "").strip()
                if active_product and active_product != str(item.get("product_key") or "").strip():
                    conn.execute(
                        """
                        UPDATE product_journey_followups
                        SET sent = 1, sent_at = ?, send_status = 'suppressed', send_error = ?, updated_at = ?
                        WHERE id = ?
                    """,
                    (now, "stale_product_context", now, item["id"]),
                )
                    _write_customer_journey_log_for_followup(
                        conn,
                        item,
                        event_type="step_suppressed",
                        message_text=item.get("reply_text") or item.get("followup_stage") or "",
                        metadata={
                            "followup_id": item["id"],
                            "stage": item["followup_stage"],
                            "reason": "stale_product_context",
                            "send_live": live_mode,
                        },
                    )
                    processed.append(
                        {
                            "id": item["id"],
                            "phone": item["phone"],
                            "stage": item["followup_stage"],
                            "send_status": "suppressed",
                            "send_live": live_mode,
                        }
                    )
                    continue

            payload = _render_followup_payload(item)
            reply_text = payload["reply_text"]
            send_status = "logged"
            send_error = None
            scenario = str(payload.get("scenario") or item.get("scenario") or "availability")

            if live_mode:
                result = send_whatsapp_reply_with_fallback(
                    phone_number=item["phone"],
                    message_text=reply_text,
                    conversation_id=f"product_followup:{item['id']}",
                    media_urls=payload.get("media_urls", []),
                    media_caption=payload.get("media_caption", ""),
                    media_only=payload.get("media_mode") == "image_only",
                    reply_result={
                        "intent": f"product_followup_{item['followup_stage']}",
                        "message_understanding": {
                            "product": item.get("product_key"),
                        },
                        "image_urls": payload.get("media_urls", []),
                        "media_mode": payload.get("media_mode", "text"),
                    },
                    customer_name="Customer",
                )
                if result.get("success"):
                    send_status = "sent"
                else:
                    send_status = "failed"
                    send_error = result.get("error")

            conn.execute(
                """
                UPDATE product_journey_followups
                SET sent = 1, sent_at = ?, reply_text = ?, send_status = ?, send_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (now, reply_text, send_status, send_error, now, item["id"]),
            )
            _write_customer_journey_log_for_followup(
                conn,
                item,
                event_type=f"step_{send_status}",
                message_text=reply_text,
                metadata={
                    "followup_id": item["id"],
                    "stage": item["followup_stage"],
                    "media_mode": payload.get("media_mode", "text"),
                    "send_error": send_error,
                    "send_live": live_mode,
                },
            )

            if item.get("followup_stage") == "latent_handoff" and send_status in {"sent", "logged"}:
                activations.append((item, scenario))

            conn.execute(
                """
                INSERT INTO ai_outgoing_replies
                (id, conversation_id, customer_phone, reply_text, intent,
                 escalated, send_status, message_mode, media_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    f"product_followup:{item['id']}",
                    item["phone"],
                    reply_text,
                    f"product_followup_{item['followup_stage']}",
                    0,
                    send_status,
                    payload.get("media_mode", "text"),
                    json.dumps({"image_urls": payload.get("media_urls", [])}, ensure_ascii=False),
                    now,
                ),
            )
            processed.append(
                {
                    "id": item["id"],
                    "phone": item["phone"],
                    "stage": item["followup_stage"],
                    "send_status": send_status,
                    "send_live": live_mode,
                }
            )

        conn.commit()

    for item, scenario in activations:
        try:
            _activate_product_journey_from_latent(item, scenario)
        except Exception as exc:
            logger.warning(
                "Failed to activate product journey from latent handoff for %s: %s",
                item.get("phone"),
                exc,
            )

    return processed


def get_product_followup_stats() -> dict[str, Any]:
    control = get_ai_control_settings()
    ensure_runtime_tables()
    with get_db_connection() as conn:
        queued = conn.execute(
            "SELECT COUNT(*) AS cnt FROM product_journey_followups WHERE sent = 0 AND send_status = 'queued'"
        ).fetchone()["cnt"]
        due = conn.execute(
            "SELECT COUNT(*) AS cnt FROM product_journey_followups WHERE sent = 0 AND send_status = 'queued' AND scheduled_at <= ?",
            (_now(),),
        ).fetchone()["cnt"]
        sent = conn.execute(
            "SELECT COUNT(*) AS cnt FROM product_journey_followups WHERE send_status = 'sent'"
        ).fetchone()["cnt"]
        logged = conn.execute(
            "SELECT COUNT(*) AS cnt FROM product_journey_followups WHERE send_status = 'logged'"
        ).fetchone()["cnt"]
        failed = conn.execute(
            "SELECT COUNT(*) AS cnt FROM product_journey_followups WHERE send_status = 'failed'"
        ).fetchone()["cnt"]
        replaced = conn.execute(
            "SELECT COUNT(*) AS cnt FROM product_journey_followups WHERE send_status = 'replaced'"
        ).fetchone()["cnt"]
        suppressed = conn.execute(
            "SELECT COUNT(*) AS cnt FROM product_journey_followups WHERE send_status = 'suppressed'"
        ).fetchone()["cnt"]
        cancelled = conn.execute(
            "SELECT COUNT(*) AS cnt FROM product_journey_followups WHERE send_status = 'cancelled'"
        ).fetchone()["cnt"]
    return {
        "queued": queued,
        "due": due,
        "sent": sent,
        "logged": logged,
        "failed": failed,
        "replaced": replaced,
        "suppressed": suppressed,
        "cancelled": cancelled,
        "send_enabled": bool(control.get("followup_send_enabled", settings.ai_followup_send_enabled)),
        "ai_running": bool(control.get("ai_running", True)),
    }


def list_product_followups(
    limit: int = 50,
    phone: str | None = None,
    send_status: str | None = None,
) -> list[dict[str, Any]]:
    ensure_runtime_tables()
    query = """
        SELECT *
        FROM product_journey_followups
        WHERE 1 = 1
    """
    params: list[Any] = []

    if phone:
        query += " AND phone = ?"
        params.append(phone)
    if send_status:
        query += " AND send_status = ?"
        params.append(send_status)

    query += " ORDER BY scheduled_at DESC LIMIT ?"
    params.append(min(limit, 200))

    with get_db_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def _render_followup_reply(item: dict[str, Any]) -> str:
    return _render_followup_payload(item)["reply_text"]
