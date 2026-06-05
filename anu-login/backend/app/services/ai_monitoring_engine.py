from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from app.runtime_db import ensure_runtime_tables, get_db_connection


BANNED_PHRASES = (
    "yes, we have",
    "i’ll share the price details below",
    "i'll share the price details below",
    "customers usually use this",
    "spice-growing belt",
    "unique qualities",
    "absolutely",
    "just checking in",
    "best pack and order it today",
    "are you referring to the price, delivery, or help with your order",
    "athu kurach clear aakki parayamo",
    "i can help with products, delivery, payment, or orders",
)

PRODUCT_HINTS = (
    "black pepper",
    "blackpepper",
    "pepper",
    "kurumulak",
    "കുരുമുളക്",
    "white pepper",
    "cardamom",
    "elakka",
    "ഏലക്ക",
    "clove",
    "grambu",
    "ഗ്രാമ്പു",
    "cinnamon",
    "patta",
    "karuvapatta",
    "turmeric",
    "manjal",
    "star anise",
    "thakkolam",
)


def _safe_ensure_runtime_tables() -> None:
    try:
        ensure_runtime_tables()
    except sqlite3.OperationalError as exc:
        if "database is locked" not in str(exc).lower():
            raise

PAYMENT_HINTS = (
    "paid",
    "payment",
    "gpay",
    "google pay",
    "upi",
    "transaction",
    "utr",
    "screenshot",
    "receipt",
    "proof",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json_loads(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        parsed = json.loads(raw)
    except Exception:
        return default
    return parsed


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.fromtimestamp(0, timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return datetime.fromtimestamp(0, timezone.utc)


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _content_hash(text: str) -> str:
    normalized = " ".join((text or "").lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _table_exists(connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _safe_json_dict(raw: str | None) -> dict[str, Any]:
    parsed = _safe_json_loads(raw, {})
    return parsed if isinstance(parsed, dict) else {}


def _conversation_id(phone: str, metadata: dict[str, Any]) -> str:
    return str(metadata.get("conversation_id") or phone or "unknown")


def _actor_type(source: str, direction: str) -> str:
    source = (source or "").lower()
    if source in {"customer", "user"}:
        return "customer"
    if source in {"ai", "assistant", "model"}:
        return "ai"
    if source in {"wabis", "bot", "campaign"}:
        return "automation"
    if source in {"human", "admin"}:
        return "admin"
    if direction == "outbound":
        return "automation"
    return "system"


def _extract_understanding(row: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    understanding = metadata.get("message_understanding") if isinstance(metadata.get("message_understanding"), dict) else {}
    return {
        "language": understanding.get("detected_language") or metadata.get("detected_language") or "",
        "product": metadata.get("resolved_product_key") or understanding.get("product") or metadata.get("active_product") or "",
        "intent": row.get("detected_intent") or understanding.get("detected_intent") or metadata.get("intent") or "",
        "route_owner": row.get("owner_after") or row.get("route_decision") or metadata.get("route") or "",
        "guard_action": metadata.get("guard_action") or "",
    }


def _issue(
    *,
    event: dict[str, Any],
    issue_type: str,
    detail: str,
    suggested_fix: str,
    severity: str = "medium",
) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "journey_id": event["journey_id"],
        "event_id": event["id"],
        "customer_phone": event["customer_phone"],
        "conversation_id": event["conversation_id"],
        "occurred_at": event["occurred_at"],
        "issue_type": issue_type,
        "severity": severity,
        "detail": detail,
        "suggested_fix": suggested_fix,
        "metadata": {},
    }


def _load_audit_events(hours: int) -> list[dict[str, Any]]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec="seconds")
    events: list[dict[str, Any]] = []

    def append_event(
        *,
        event_id: str,
        phone: str,
        conversation_id: str,
        occurred_at: str,
        actor_type: str,
        source: str,
        message_text: str,
        detected_language: str = "",
        detected_product: str = "",
        detected_intent: str = "",
        route_owner: str = "",
        guard_action: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        conv_id = conversation_id or phone or "unknown"
        events.append(
            {
                "id": event_id or str(uuid.uuid4()),
                "journey_id": f"whatsapp:{conv_id}",
                "event_id": event_id or "",
                "customer_phone": phone or "",
                "conversation_id": conv_id,
                "occurred_at": occurred_at or "",
                "actor_type": actor_type,
                "source": source,
                "message_text": message_text or "",
                "detected_language": detected_language or "",
                "detected_product": detected_product or "",
                "detected_intent": detected_intent or "",
                "route_owner": route_owner or "",
                "guard_action": guard_action or "",
                "metadata": metadata or {},
                "issue_tags": [],
            }
        )

    with get_db_connection() as connection:
        if _table_exists(connection, "conversation_audit_log"):
            rows = connection.execute(
                """
                SELECT id, created_at, phone, direction, source, message,
                       owner_before, owner_after, active_flow, detected_intent,
                       route_decision, reason, metadata_json
                FROM conversation_audit_log
                WHERE created_at >= ?
                ORDER BY created_at ASC
                """,
                (cutoff,),
            ).fetchall()
            for row in rows:
                item = dict(row)
                metadata = _safe_json_dict(item.get("metadata_json"))
                conv_id = _conversation_id(item.get("phone") or "", metadata)
                understanding = _extract_understanding(item, metadata)
                append_event(
                    event_id=item["id"],
                    phone=item.get("phone") or "",
                    conversation_id=conv_id,
                    occurred_at=item.get("created_at") or "",
                    actor_type=_actor_type(item.get("source") or "", item.get("direction") or ""),
                    source=item.get("source") or "system",
                    message_text=item.get("message") or "",
                    detected_language=understanding["language"],
                    detected_product=understanding["product"],
                    detected_intent=understanding["intent"],
                    route_owner=understanding["route_owner"],
                    guard_action=understanding["guard_action"],
                    metadata={
                        "owner_before": item.get("owner_before"),
                        "owner_after": item.get("owner_after"),
                        "active_flow": item.get("active_flow"),
                        "route_decision": item.get("route_decision"),
                        "reason": item.get("reason"),
                        **metadata,
                    },
                )

        if _table_exists(connection, "ai_incoming_messages"):
            for row in connection.execute(
                """
                SELECT id, conversation_id, customer_phone, message_type, body, created_at
                FROM ai_incoming_messages
                WHERE created_at >= ?
                ORDER BY created_at ASC
                """,
                (cutoff,),
            ).fetchall():
                append_event(
                    event_id=row["id"],
                    phone=row["customer_phone"],
                    conversation_id=row["conversation_id"],
                    occurred_at=row["created_at"],
                    actor_type="customer",
                    source="ai_incoming_messages",
                    message_text=row["body"] or row["message_type"] or "",
                    metadata={"message_type": row["message_type"]},
                )

        if _table_exists(connection, "ai_outgoing_replies"):
            for row in connection.execute(
                """
                SELECT id, conversation_id, customer_phone, reply_text, intent, send_status, created_at
                FROM ai_outgoing_replies
                WHERE created_at >= ?
                ORDER BY created_at ASC
                """,
                (cutoff,),
            ).fetchall():
                append_event(
                    event_id=row["id"],
                    phone=row["customer_phone"],
                    conversation_id=row["conversation_id"],
                    occurred_at=row["created_at"],
                    actor_type="ai",
                    source="ai_outgoing_replies",
                    message_text=row["reply_text"],
                    detected_intent=row["intent"],
                    route_owner="ai",
                    guard_action=row["send_status"],
                )

        if _table_exists(connection, "message_decisions"):
            for row in connection.execute(
                """
                SELECT id, customer_id, incoming_message_id, incoming_message, normalized_text,
                       detected_type, detected_intent, confidence, selected_owner,
                       decision_reason, skipped_ai, route, score, metadata_json, created_at
                FROM message_decisions
                WHERE created_at >= ?
                ORDER BY created_at ASC
                """,
                (cutoff,),
            ).fetchall():
                metadata = _safe_json_dict(row["metadata_json"])
                append_event(
                    event_id=row["id"],
                    phone=row["customer_id"],
                    conversation_id=str(metadata.get("conversation_id") or row["customer_id"] or ""),
                    occurred_at=row["created_at"],
                    actor_type="system",
                    source="message_decisions",
                    message_text=row["incoming_message"] or row["normalized_text"] or "",
                    detected_intent=row["detected_intent"],
                    route_owner=row["selected_owner"],
                    guard_action="ai_skipped" if row["skipped_ai"] else "ai_allowed",
                    metadata={
                        **metadata,
                        "confidence": row["confidence"],
                        "decision_reason": row["decision_reason"],
                        "detected_type": row["detected_type"],
                        "route": row["route"],
                        "score": row["score"],
                    },
                )

        if _table_exists(connection, "routing_log"):
            for row in connection.execute(
                """
                SELECT id, phone, message, owner_before, route_taken, context, timestamp
                FROM routing_log
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
                """,
                (cutoff,),
            ).fetchall():
                context = _safe_json_dict(row["context"])
                append_event(
                    event_id=row["id"],
                    phone=row["phone"],
                    conversation_id=row["phone"],
                    occurred_at=row["timestamp"],
                    actor_type="system",
                    source="routing_log",
                    message_text=row["message"] or "",
                    detected_language=str(context.get("language") or ""),
                    detected_product=str(context.get("product") or ""),
                    detected_intent=str(context.get("intent") or ""),
                    route_owner=row["route_taken"],
                    metadata={"owner_before": row["owner_before"], **context},
                )

        if not events and _table_exists(connection, "conversation_state"):
            for row in connection.execute(
                """
                SELECT phone, owner, owner_reason, flow_id, flow_step, active_product,
                       latest_intent, language, journey_stage, last_activity, updated_at
                FROM conversation_state
                ORDER BY COALESCE(last_activity, updated_at, created_at) DESC
                LIMIT 200
                """
            ).fetchall():
                append_event(
                    event_id=f"state:{row['phone']}",
                    phone=row["phone"],
                    conversation_id=row["phone"],
                    occurred_at=row["last_activity"] or row["updated_at"] or "",
                    actor_type="system",
                    source="conversation_state",
                    message_text=row["owner_reason"] or row["flow_step"] or row["journey_stage"] or row["owner"],
                    detected_language=row["language"] or "",
                    detected_product=row["active_product"] or "",
                    detected_intent=row["latest_intent"] or "",
                    route_owner=row["owner"] or "",
                    metadata={
                        "flow_id": row["flow_id"],
                        "flow_step": row["flow_step"],
                        "journey_stage": row["journey_stage"],
                    },
                )

    deduped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for event in events:
        key = (
            event["customer_phone"],
            event["occurred_at"],
            event["actor_type"],
            _content_hash(event["message_text"])[:16],
        )
        deduped.setdefault(key, event)
    return sorted(deduped.values(), key=lambda event: _parse_dt(event["occurred_at"]))


def _detect_issues(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    by_journey: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_journey[event["journey_id"]].append(event)

    for journey_events in by_journey.values():
        journey_events.sort(key=lambda event: _parse_dt(event["occurred_at"]))
        last_ai_hash = ""
        payment_seen = False
        screenshot_seen = False
        latest_customer_product_interest = False
        latest_customer_language = ""

        for index, event in enumerate(journey_events):
            text = event["message_text"] or ""
            lower_text = text.lower()
            actor = event["actor_type"]
            event_issues: list[str] = []

            if actor == "customer":
                payment_seen = payment_seen or any(hint in lower_text for hint in PAYMENT_HINTS)
                screenshot_seen = screenshot_seen or "[[media:image]]" in lower_text or "screenshot" in lower_text
                latest_customer_product_interest = any(hint in lower_text for hint in PRODUCT_HINTS)
                latest_customer_language = event["detected_language"] or latest_customer_language

            if actor == "ai":
                reply_hash = _content_hash(text)
                if reply_hash and reply_hash == last_ai_hash:
                    event_issues.append("repeated_ai_message")
                    issues.append(
                        _issue(
                            event=event,
                            issue_type="Repeated AI message",
                            detail="AI sent the same or near-identical reply again.",
                            suggested_fix="Suppress duplicate replies using the last reply hash.",
                        )
                    )
                last_ai_hash = reply_hash

                if _word_count(text) > 55:
                    event_issues.append("too_long")
                    issues.append(
                        _issue(
                            event=event,
                            issue_type="Too long",
                            detail=f"AI reply is {_word_count(text)} words.",
                            suggested_fix="Keep WhatsApp replies under 55 words unless details were explicitly requested.",
                        )
                    )

                if any(phrase in lower_text for phrase in BANNED_PHRASES):
                    event_issues.append("robotic_wording")
                    issues.append(
                        _issue(
                            event=event,
                            issue_type="Robotic or banned wording",
                            detail=text[:240],
                            suggested_fix="Rewrite with short human WhatsApp tone.",
                        )
                    )

                if payment_seen and screenshot_seen and any(hint in lower_text for hint in ("screenshot", "proof", "receipt")):
                    event_issues.append("asked_screenshot_again")
                    issues.append(
                        _issue(
                            event=event,
                            issue_type="Asked for screenshot after proof",
                            detail="Payment/image context was already present before this AI reply.",
                            suggested_fix="Acknowledge receipt and move to verification instead of asking again.",
                            severity="high",
                        )
                    )

                if latest_customer_product_interest and "₹" not in text and "price" not in lower_text and "stock" not in lower_text:
                    event_issues.append("product_interest_no_details")
                    issues.append(
                        _issue(
                            event=event,
                            issue_type="Product interest without details",
                            detail="Customer showed product interest but AI did not show pricing/details.",
                            suggested_fix="Send the short product reply for the latest product mention.",
                        )
                    )

                if latest_customer_language in {"malayalam", "manglish"} and event["detected_language"] == "english" and re.search(r"\b(please|details|available|order)\b", lower_text):
                    event_issues.append("wrong_language")
                    issues.append(
                        _issue(
                            event=event,
                            issue_type="Wrong language",
                            detail=f"Customer language looked like {latest_customer_language}, but reply was English.",
                            suggested_fix="Match the customer's latest language/tone.",
                        )
                    )

            if index > 0:
                previous = journey_events[index - 1]
                delta = (_parse_dt(event["occurred_at"]) - _parse_dt(previous["occurred_at"])).total_seconds()
                if delta <= 60 and {previous["actor_type"], actor} == {"ai", "automation"}:
                    event_issues.append("ai_automation_overlap")
                    issues.append(
                        _issue(
                            event=event,
                            issue_type="Automation and AI too close",
                            detail=f"{previous['actor_type']} and {actor} events occurred within {int(delta)} seconds.",
                            suggested_fix="Keep one route owner for each inbound message and suppress overlap.",
                        )
                    )

            event["issue_tags"] = sorted(set(event.get("issue_tags", []) + event_issues))

        last_ai_index = max((i for i, item in enumerate(journey_events) if item["actor_type"] == "ai"), default=None)
        if last_ai_index is not None and not any(item["actor_type"] == "customer" for item in journey_events[last_ai_index + 1 :]):
            event = journey_events[last_ai_index]
            issues.append(
                _issue(
                    event=event,
                    issue_type="Customer did not reply after AI",
                    detail=(event["message_text"] or "")[:240],
                    suggested_fix="Use one clear next action and avoid unnecessary follow-up unless the journey allows it.",
                )
            )
    return issues


def _journey_summary(events: list[dict[str, Any]], issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues_by_journey: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for issue in issues:
        issues_by_journey[issue["journey_id"]].append(issue)

    by_journey: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_journey[event["journey_id"]].append(event)

    summaries: list[dict[str, Any]] = []
    for journey_id, journey_events in by_journey.items():
        journey_events.sort(key=lambda event: _parse_dt(event["occurred_at"]))
        counts = Counter(event["actor_type"] for event in journey_events)
        customer_phone = journey_events[0]["customer_phone"]
        conversation_id = journey_events[0]["conversation_id"]
        detected_language = next((event["detected_language"] for event in reversed(journey_events) if event["detected_language"]), "")
        active_product = next((event["detected_product"] for event in reversed(journey_events) if event["detected_product"]), "")
        latest_intent = next((event["detected_intent"] for event in reversed(journey_events) if event["detected_intent"]), "")
        journey_issues = issues_by_journey.get(journey_id, [])
        score = max(0, min(100, 100 - (len(journey_issues) * 14)))
        last_issue = journey_issues[-1]["issue_type"] if journey_issues else ""
        last_actor = journey_events[-1]["actor_type"]
        status = "open"
        if journey_issues:
            status = "needs_review"
        if last_actor == "customer":
            status = "waiting_ai"
        if last_actor == "ai" and not any(event["actor_type"] == "customer" for event in journey_events[journey_events.index(journey_events[-1]) + 1 :]):
            status = "waiting_customer"
        summaries.append(
            {
                "journey_id": journey_id,
                "customer_phone": customer_phone,
                "conversation_id": conversation_id,
                "channel": "whatsapp",
                "journey_status": status,
                "journey_stage": latest_intent or "unknown",
                "detected_language": detected_language,
                "active_product": active_product,
                "latest_intent": latest_intent,
                "total_messages": len(journey_events),
                "customer_messages": counts["customer"],
                "ai_messages": counts["ai"],
                "automation_messages": counts["automation"],
                "issue_count": len(journey_issues),
                "success_score": score,
                "last_issue": last_issue,
                "first_event_at": journey_events[0]["occurred_at"],
                "last_event_at": journey_events[-1]["occurred_at"],
                "metadata": {
                    "sources": sorted({event["source"] for event in journey_events}),
                    "issue_types": dict(Counter(issue["issue_type"] for issue in journey_issues)),
                },
            }
        )
    return sorted(summaries, key=lambda item: item["last_event_at"], reverse=True)


def _upsert_materialized(events: list[dict[str, Any]], issues: list[dict[str, Any]], summaries: list[dict[str, Any]]) -> None:
    now = _now()
    with get_db_connection() as connection:
        for event in events:
            connection.execute(
                """
                INSERT INTO ai_monitor_events (
                    id, journey_id, event_id, customer_phone, conversation_id, occurred_at,
                    actor_type, source, message_text, detected_language, detected_product,
                    detected_intent, route_owner, guard_action, issue_tags_json, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    issue_tags_json = excluded.issue_tags_json,
                    metadata_json = excluded.metadata_json
                """,
                (
                    event["id"],
                    event["journey_id"],
                    event["event_id"],
                    event["customer_phone"],
                    event["conversation_id"],
                    event["occurred_at"],
                    event["actor_type"],
                    event["source"],
                    event["message_text"],
                    event["detected_language"],
                    event["detected_product"],
                    event["detected_intent"],
                    event["route_owner"],
                    event["guard_action"],
                    json.dumps(event.get("issue_tags") or [], ensure_ascii=False),
                    json.dumps(event.get("metadata") or {}, ensure_ascii=False),
                ),
            )
        connection.execute("DELETE FROM ai_monitor_issues WHERE occurred_at >= ?", (events[0]["occurred_at"] if events else now,))
        for issue in issues:
            connection.execute(
                """
                INSERT INTO ai_monitor_issues (
                    id, journey_id, event_id, customer_phone, conversation_id, occurred_at,
                    issue_type, severity, detail, suggested_fix, status, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
                """,
                (
                    issue["id"],
                    issue["journey_id"],
                    issue["event_id"],
                    issue["customer_phone"],
                    issue["conversation_id"],
                    issue["occurred_at"],
                    issue["issue_type"],
                    issue["severity"],
                    issue["detail"],
                    issue["suggested_fix"],
                    json.dumps(issue.get("metadata") or {}, ensure_ascii=False),
                ),
            )
        for summary in summaries:
            connection.execute(
                """
                INSERT INTO ai_monitor_journeys (
                    journey_id, customer_phone, conversation_id, channel, journey_status,
                    journey_stage, detected_language, active_product, latest_intent,
                    total_messages, customer_messages, ai_messages, automation_messages,
                    issue_count, success_score, last_issue, first_event_at, last_event_at,
                    metadata_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(journey_id) DO UPDATE SET
                    customer_phone = excluded.customer_phone,
                    conversation_id = excluded.conversation_id,
                    journey_status = excluded.journey_status,
                    journey_stage = excluded.journey_stage,
                    detected_language = excluded.detected_language,
                    active_product = excluded.active_product,
                    latest_intent = excluded.latest_intent,
                    total_messages = excluded.total_messages,
                    customer_messages = excluded.customer_messages,
                    ai_messages = excluded.ai_messages,
                    automation_messages = excluded.automation_messages,
                    issue_count = excluded.issue_count,
                    success_score = excluded.success_score,
                    last_issue = excluded.last_issue,
                    first_event_at = excluded.first_event_at,
                    last_event_at = excluded.last_event_at,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                (
                    summary["journey_id"],
                    summary["customer_phone"],
                    summary["conversation_id"],
                    summary["channel"],
                    summary["journey_status"],
                    summary["journey_stage"],
                    summary["detected_language"],
                    summary["active_product"],
                    summary["latest_intent"],
                    summary["total_messages"],
                    summary["customer_messages"],
                    summary["ai_messages"],
                    summary["automation_messages"],
                    summary["issue_count"],
                    summary["success_score"],
                    summary["last_issue"],
                    summary["first_event_at"],
                    summary["last_event_at"],
                    json.dumps(summary.get("metadata") or {}, ensure_ascii=False),
                    now,
                ),
            )
        connection.commit()


def get_ai_monitor_payload(hours: int = 4, limit: int = 80) -> dict[str, Any]:
    _safe_ensure_runtime_tables()
    events = _load_audit_events(hours=hours)
    issues = _detect_issues(events)
    summaries = _journey_summary(events, issues)
    try:
        _upsert_materialized(events, issues, summaries)
    except sqlite3.OperationalError as exc:
        if "database is locked" not in str(exc).lower():
            raise

    total_journeys = len(summaries)
    total_ai = sum(item["ai_messages"] for item in summaries)
    journeys_with_issues = sum(1 for item in summaries if item["issue_count"])
    avg_score = round(sum(item["success_score"] for item in summaries) / total_journeys, 1) if total_journeys else 0
    issue_counter = Counter(issue["issue_type"] for issue in issues)
    language_counter = Counter(item["detected_language"] or "unknown" for item in summaries)
    ai_success_rate = 0.0
    if total_ai:
        ai_success_rate = max(0.0, min(100.0, ((total_ai - len(issues)) / total_ai) * 100))

    issues_sorted = sorted(issues, key=lambda item: item["occurred_at"], reverse=True)
    events_by_journey: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        events_by_journey[event["journey_id"]].append(event)

    return {
        "window_hours": hours,
        "generated_at": _now(),
        "metrics": {
            "journeys": total_journeys,
            "messages": len(events),
            "ai_messages": total_ai,
            "issues": len(issues),
            "journeys_with_issues": journeys_with_issues,
            "avg_success_score": avg_score,
            "ai_success_rate": round(ai_success_rate, 1),
        },
        "issue_breakdown": [{"issue_type": key, "count": value} for key, value in issue_counter.most_common()],
        "language_breakdown": [{"language": key, "count": value} for key, value in language_counter.most_common()],
        "journeys": summaries[:limit],
        "issues": issues_sorted[:limit],
        "recent_events": sorted(events, key=lambda item: item["occurred_at"], reverse=True)[:limit],
        "journey_events": {
            summary["journey_id"]: sorted(
                events_by_journey.get(summary["journey_id"], []),
                key=lambda item: item["occurred_at"],
            )[-20:]
            for summary in summaries[: min(limit, 30)]
        },
    }
