"""
Review Dashboard API — Approve / Promote / Rollback human outbound events.

Endpoints:
  GET  /api/review-items              — List review queue (filter by state)
  GET  /api/review-items/{id}         — Get evidence for a review item
  POST /api/review-items/{id}/approve — Mark as approved (Reviewer role)
  POST /api/review-items/{id}/promote — Promote to intent rule version (Publisher role)
  POST /api/promotions/{id}/rollback  — Rollback a promotion (Admin role)
  POST /api/conversations/{id}/locks  — Manually lock a conversation (Reviewer/Admin)
  DELETE /api/conversations/{id}/locks/{lock_id} — Release lock (Admin)
  POST /api/webhook-deliveries/{id}/replay — Replay a stored delivery (Admin)
  GET  /api/admin/system-health       — Monitoring metrics snapshot
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.runtime_db import ensure_runtime_tables, get_db_connection
from app.services.owner_dashboard_service import get_ai_control_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["review-dashboard"])


# ── Role-based access ─────────────────────────────────────────────────────────

REVIEWER_ROLES = {"reviewer", "publisher", "admin"}
PUBLISHER_ROLES = {"publisher", "admin"}
ADMIN_ROLES = {"admin"}


def _require_role(min_role: str, provided_role: str) -> None:
    """Simple role check. In production this would use JWT/OAuth scopes."""
    role_hierarchy = {"reviewer": 0, "publisher": 1, "admin": 2}
    if role_hierarchy.get(provided_role, -1) < role_hierarchy.get(min_role, 0):
        raise HTTPException(status_code=403, detail=f"Requires {min_role} role or higher")


def _current_role(role: str = Query(default="admin", alias="role")) -> str:
    """Placeholder for real auth. Pass ?role=admin on the query string."""
    return role


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Audit helper ──────────────────────────────────────────────────────────────

def _append_audit_log(
    *,
    actor_id: str,
    actor_role: str,
    entity_type: str,
    entity_id: str,
    action: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str = "",
    source_review_item_id: str = "",
    source_event_id: str = "",
    request_id: str = "",
    rollback_of: str = "",
) -> None:
    ensure_runtime_tables()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_logs
            (id, actor_id, actor_role, entity_type, entity_id, action,
             before_json, after_json, reason, source_review_item_id,
             source_event_id, request_id, rollback_of, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                actor_id,
                actor_role,
                entity_type,
                entity_id,
                action,
                json.dumps(before or {}, ensure_ascii=False),
                json.dumps(after or {}, ensure_ascii=False),
                reason,
                source_review_item_id,
                source_event_id,
                request_id,
                rollback_of,
                _now(),
            ),
        )
        conn.commit()


# ── Request models ────────────────────────────────────────────────────────────

class ApproveRequest(BaseModel):
    reason: str = ""


class PromoteRequest(BaseModel):
    intent_key: str = Field(..., min_length=1, max_length=120)
    rule_json: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str = "default"
    test_run_id: str = ""


class RollbackRequest(BaseModel):
    reason: str = ""


class LockRequest(BaseModel):
    lock_kind: str = "HUMAN_HARD_LOCK"
    expires_minutes: int = 60
    reason: str = "manual_lock"


# ── Review Items ──────────────────────────────────────────────────────────────

@router.get("/review-items")
async def list_review_items(
    state: str = Query(default="open", regex="^(open|approved|promoted|rolled_back|dismissed|all)$"),
    customer_phone: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    role: str = Depends(_current_role),
) -> dict[str, Any]:
    """List review items, filterable by state and customer phone."""
    _require_role("reviewer", role)
    ensure_runtime_tables()
    with get_db_connection() as conn:
        query = "SELECT * FROM review_items WHERE 1=1"
        params: list[Any] = []
        if state != "all":
            query += " AND review_state = ?"
            params.append(state)
        if customer_phone:
            query += " AND customer_phone = ?"
            params.append(customer_phone)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
    return {"items": [dict(r) for r in rows], "count": len(rows)}


@router.get("/review-items/{item_id}")
async def get_review_item(
    item_id: str,
    role: str = Depends(_current_role),
) -> dict[str, Any]:
    """Get full evidence for a review item."""
    _require_role("reviewer", role)
    ensure_runtime_tables()
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM review_items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Review item not found")
    item = dict(row)
    item["evidence"] = json.loads(item.get("evidence_json") or "{}")
    return item


@router.post("/review-items/{item_id}/approve")
async def approve_review_item(
    item_id: str,
    req: ApproveRequest,
    actor_id: str = Query(default="system"),
    role: str = Depends(_current_role),
) -> dict[str, Any]:
    """Mark a review item as approved (evidence is valid)."""
    _require_role("reviewer", role)
    ensure_runtime_tables()
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM review_items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Review item not found")
        item = dict(row)
        if item["review_state"] not in ("OPEN", "APPROVED"):
            raise HTTPException(status_code=400, detail=f"Cannot approve item in state {item['review_state']}")
        now = _now()
        conn.execute(
            "UPDATE review_items SET review_state = 'APPROVED', updated_at = ? WHERE id = ?",
            (now, item_id),
        )
        conn.commit()
    _append_audit_log(
        actor_id=actor_id, actor_role=role,
        entity_type="review_item", entity_id=item_id,
        action="approve",
        before={"review_state": item["review_state"]},
        after={"review_state": "APPROVED"},
        reason=req.reason,
    )
    return {"status": "approved", "item_id": item_id}


@router.post("/review-items/{item_id}/promote")
async def promote_review_item(
    item_id: str,
    req: PromoteRequest,
    actor_id: str = Query(default="system"),
    role: str = Depends(_current_role),
) -> dict[str, Any]:
    """Promote an approved review item to a new intent rule version."""
    _require_role("publisher", role)
    ensure_runtime_tables()
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM review_items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Review item not found")
        item = dict(row)
        if item["review_state"] != "APPROVED":
            raise HTTPException(status_code=400, detail=f"Item must be APPROVED before promotion, current state: {item['review_state']}")

        # Find or create the intent rule
        rule_row = conn.execute(
            "SELECT id FROM intent_rules WHERE tenant_id = ? AND intent_key = ?",
            (req.tenant_id, req.intent_key),
        ).fetchone()
        if rule_row:
            rule_id = rule_row["id"]
        else:
            rule_id = str(uuid.uuid4())
            now = _now()
            conn.execute(
                "INSERT INTO intent_rules (id, tenant_id, intent_key, status, created_at, updated_at) VALUES (?, ?, ?, 'active', ?, ?)",
                (rule_id, req.tenant_id, req.intent_key, now, now),
            )

        # Determine next version number
        max_row = conn.execute(
            "SELECT MAX(version_no) as max_v FROM intent_rule_versions WHERE intent_rule_id = ?",
            (rule_id,),
        ).fetchone()
        next_version = (max_row["max_v"] or 0) + 1 if max_row else 1

        # Deactivate current active version
        conn.execute(
            "UPDATE intent_rule_versions SET is_active = 0, updated_at = ? WHERE intent_rule_id = ? AND is_active = 1",
            (_now(), rule_id),
        )

        # Create new version
        version_id = str(uuid.uuid4())
        now = _now()
        conn.execute(
            """
            INSERT INTO intent_rule_versions (id, intent_rule_id, version_no, is_active, rule_json, created_at)
            VALUES (?, ?, ?, 1, ?, ?)
            """,
            (version_id, rule_id, next_version, json.dumps(req.rule_json, ensure_ascii=False), now),
        )

        # Record promotion
        promotion_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO rule_promotions (id, review_item_id, intent_rule_version_id, status, promoted_by, promoted_at, created_at)
            VALUES (?, ?, ?, 'active', ?, ?, ?)
            """,
            (promotion_id, item_id, version_id, actor_id, now, now),
        )

        # Update review item
        conn.execute(
            "UPDATE review_items SET review_state = 'PROMOTED', updated_at = ? WHERE id = ?",
            (now, item_id),
        )
        conn.commit()

    _append_audit_log(
        actor_id=actor_id, actor_role=role,
        entity_type="review_item", entity_id=item_id,
        action="promote",
        before={"review_state": "APPROVED"},
        after={"review_state": "PROMOTED", "intent_key": req.intent_key, "version": next_version},
        reason=f"Promoted to intent_rule {req.intent_key} v{next_version}",
        source_review_item_id=item_id,
    )
    return {
        "status": "promoted",
        "item_id": item_id,
        "intent_key": req.intent_key,
        "version": next_version,
        "promotion_id": promotion_id,
    }


@router.post("/promotions/{promotion_id}/rollback")
async def rollback_promotion(
    promotion_id: str,
    req: RollbackRequest,
    actor_id: str = Query(default="system"),
    role: str = Depends(_current_role),
) -> dict[str, Any]:
    """Rollback a promotion — deactivate the promoted version and reactivate the prior one."""
    _require_role("admin", role)
    ensure_runtime_tables()
    with get_db_connection() as conn:
        promo = conn.execute("SELECT * FROM rule_promotions WHERE id = ?", (promotion_id,)).fetchone()
        if not promo:
            raise HTTPException(status_code=404, detail="Promotion not found")
        promo = dict(promo)
        if promo["status"] != "active":
            raise HTTPException(status_code=400, detail=f"Promotion is {promo['status']}, not active")

        version = conn.execute("SELECT * FROM intent_rule_versions WHERE id = ?", (promo["intent_rule_version_id"],)).fetchone()
        if not version:
            raise HTTPException(status_code=404, detail="Intent rule version not found")
        version = dict(version)

        now = _now()

        # Deactivate the rolled-back version
        conn.execute(
            "UPDATE intent_rule_versions SET is_active = 0 WHERE id = ?",
            (version["id"],),
        )

        # Reactivate the previous version
        prev = conn.execute(
            """
            SELECT id FROM intent_rule_versions
            WHERE intent_rule_id = ? AND version_no < ?
            ORDER BY version_no DESC LIMIT 1
            """,
            (version["intent_rule_id"], version["version_no"]),
        ).fetchone()
        if prev:
            conn.execute(
                "UPDATE intent_rule_versions SET is_active = 1 WHERE id = ?",
                (prev["id"],),
            )

        # Mark promotion as rolled back
        conn.execute(
            "UPDATE rule_promotions SET status = 'rolled_back' WHERE id = ?",
            (promotion_id,),
        )

        # Update review item
        conn.execute(
            "UPDATE review_items SET review_state = 'ROLLED_BACK', updated_at = ? WHERE id = ?",
            (now, promo["review_item_id"]),
        )

        # Record rollback promotion
        rollback_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO rule_promotions (id, review_item_id, intent_rule_version_id, status, promoted_by, promoted_at, rollback_of, created_at)
            VALUES (?, ?, ?, 'rollback', ?, ?, ?, ?)
            """,
            (rollback_id, promo["review_item_id"], prev["id"] if prev else "", actor_id, now, promotion_id, now),
        )
        conn.commit()

    _append_audit_log(
        actor_id=actor_id, actor_role=role,
        entity_type="promotion", entity_id=promotion_id,
        action="rollback",
        before={"status": "active", "version_no": version["version_no"]},
        after={"status": "rolled_back", "reactivated_version": prev["version_no"] if prev else None},
        reason=req.reason,
        rollback_of=promotion_id,
    )
    return {"status": "rolled_back", "promotion_id": promotion_id, "rollback_id": rollback_id}


# ── Conversation Locks ────────────────────────────────────────────────────────

@router.post("/conversations/{phone}/locks")
async def create_conversation_lock(
    phone: str,
    req: LockRequest,
    actor_id: str = Query(default="system"),
    role: str = Depends(_current_role),
) -> dict[str, Any]:
    """Manually lock a conversation (prevents AI from responding)."""
    _require_role("reviewer", role)
    ensure_runtime_tables()
    now = _now()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=req.expires_minutes)).isoformat()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO wabis_human_locks
            (id, customer_phone, conversation_id, event_type, lock_reason, lock_until, raw_delivery_id, created_at)
            VALUES (?, ?, ?, 'manual_lock', ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), phone, phone, req.reason, expires_at, "manual", now),
        )
        conn.commit()
    # Also update conversation_state
    try:
        from app.ai.conversation_state_manager import set_conversation_state
        set_conversation_state(
            phone,
            owner="human",
            owner_reason="manual_lock",
            flow_id="human_review",
            flow_step="manual_lock",
            context={"lock_kind": req.lock_kind, "expires_at": expires_at, "reason": req.reason},
            conversation_mode=req.lock_kind,
            retry_state="CANCELLED_BY_HUMAN",
        )
    except Exception as exc:
        logger.warning("Failed to update conversation_state for manual lock: %s", exc)

    _append_audit_log(
        actor_id=actor_id, actor_role=role,
        entity_type="conversation_lock", entity_id=phone,
        action="create_lock",
        after={"lock_kind": req.lock_kind, "expires_at": expires_at, "reason": req.reason},
    )
    return {"status": "locked", "phone": phone, "expires_at": expires_at}


@router.delete("/conversations/{phone}/locks/{lock_id}")
async def release_conversation_lock(
    phone: str,
    lock_id: str,
    actor_id: str = Query(default="system"),
    role: str = Depends(_current_role),
) -> dict[str, Any]:
    """Release a conversation lock (allows AI to resume)."""
    _require_role("admin", role)
    ensure_runtime_tables()
    now = _now()
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE wabis_human_locks SET lock_until = ? WHERE id = ? AND customer_phone = ?",
            (now, lock_id, phone),
        )
        conn.commit()
    try:
        from app.ai.conversation_state_manager import reset_conversation_state
        reset_conversation_state(phone)
    except Exception as exc:
        logger.warning("Failed to reset conversation_state for lock release: %s", exc)

    _append_audit_log(
        actor_id=actor_id, actor_role=role,
        entity_type="conversation_lock", entity_id=lock_id,
        action="release_lock",
        after={"released_at": now},
    )
    return {"status": "released", "phone": phone}


# ── Webhook Replay ────────────────────────────────────────────────────────────

@router.post("/webhook-deliveries/{delivery_id}/replay")
async def replay_webhook_delivery(
    delivery_id: str,
    actor_id: str = Query(default="system"),
    role: str = Depends(_current_role),
) -> dict[str, Any]:
    """Replay a stored webhook delivery through the normalizer."""
    _require_role("admin", role)
    ensure_runtime_tables()
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT raw_payload_json FROM wabis_webhook_deliveries WHERE id = ?",
            (delivery_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Webhook delivery not found")
    raw_payload = json.loads(row["raw_payload_json"] or "{}")

    from app.services.wabis_outbound_event_service import ingest_wabis_outbound_event
    result = ingest_wabis_outbound_event(
        payload=raw_payload,
        headers={"X-Replay": "true"},
        auth_verified=True,
    )

    _append_audit_log(
        actor_id=actor_id, actor_role=role,
        entity_type="webhook_delivery", entity_id=delivery_id,
        action="replay",
        after={"result_status": result.get("status")},
    )
    return {"status": "replayed", "delivery_id": delivery_id, "result": result}


# ── System Health ─────────────────────────────────────────────────────────────

@router.get("/admin/system-health")
async def system_health(
    role: str = Depends(_current_role),
) -> dict[str, Any]:
    """Return monitoring metrics snapshot for the admin outbound event pipeline."""
    _require_role("reviewer", role)
    ensure_runtime_tables()
    now = _now()
    with get_db_connection() as conn:
        # Webhook delivery stats (last 5 minutes)
        five_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        total_deliveries = conn.execute(
            "SELECT COUNT(*) as cnt FROM wabis_webhook_deliveries WHERE created_at >= ?",
            (five_min_ago,),
        ).fetchone()["cnt"]
        failed_deliveries = conn.execute(
            "SELECT COUNT(*) as cnt FROM wabis_webhook_deliveries WHERE created_at >= ? AND processing_status = 'error'",
            (five_min_ago,),
        ).fetchone()["cnt"]

        # Review queue stats
        open_reviews = conn.execute(
            "SELECT COUNT(*) as cnt FROM review_items WHERE review_state = 'OPEN'"
        ).fetchone()["cnt"]
        oldest_open = conn.execute(
            "SELECT MIN(created_at) as oldest FROM review_items WHERE review_state = 'OPEN'"
        ).fetchone()["oldest"]

        # Human lock stats
        active_locks = conn.execute(
            "SELECT COUNT(*) as cnt FROM wabis_human_locks WHERE lock_until > ?",
            (now,),
        ).fetchone()["cnt"]
        stale_locks = conn.execute(
            "SELECT COUNT(*) as cnt FROM wabis_human_locks WHERE lock_until > ? AND created_at < ?",
            (now, (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()),
        ).fetchone()["cnt"]

        # AI retry stats
        pending_jobs = conn.execute(
            "SELECT COUNT(*) as cnt FROM ai_reply_jobs WHERE status IN ('pending', 'learning')"
        ).fetchone()["cnt"]
        cancelled_by_human = conn.execute(
            "SELECT COUNT(*) as cnt FROM ai_reply_jobs WHERE skipped_reason = 'cancelled_by_human_outbound_event' AND updated_at >= ?",
            (five_min_ago,),
        ).fetchone()["cnt"]

        # Status correlation
        total_status_events = conn.execute("SELECT COUNT(*) as cnt FROM wabis_message_status_events").fetchone()["cnt"]
        total_outbound = conn.execute("SELECT COUNT(*) as cnt FROM wabis_outbound_messages").fetchone()["cnt"]

        # Intent rule stats
        total_rules = conn.execute("SELECT COUNT(*) as cnt FROM intent_rules").fetchone()["cnt"]
        total_versions = conn.execute("SELECT COUNT(*) as cnt FROM intent_rule_versions").fetchone["cnt"]
        active_promotions = conn.execute(
            "SELECT COUNT(*) as cnt FROM rule_promotions WHERE status = 'active'"
        ).fetchone()["cnt"]

    return {
        "timestamp": now,
        "webhook_deliveries": {
            "last_5min_total": total_deliveries,
            "last_5min_errors": failed_deliveries,
            "error_rate": round(failed_deliveries / max(total_deliveries, 1) * 100, 2),
        },
        "review_queue": {
            "open": open_reviews,
            "oldest_open": oldest_open,
        },
        "human_locks": {
            "active": active_locks,
            "stale": stale_locks,
        },
        "ai_retries": {
            "pending_jobs": pending_jobs,
            "cancelled_by_human_last_5min": cancelled_by_human,
        },
        "outbound_messages": {
            "total": total_outbound,
            "total_status_events": total_status_events,
        },
        "intent_rules": {
            "total_rules": total_rules,
            "total_versions": total_versions,
            "active_promotions": active_promotions,
        },
    }
