"""
Basil Commerce OS — Phase 3
routes/rules.py

Business rules engine — JSON-defined conditions/actions evaluated server-side.
Endpoints:
  GET  /api/rules?shop_domain=x   — list all active rules
  POST /api/rules                 — create / upsert a rule
  POST /api/rules/evaluate        — evaluate rules against a given context
  DELETE /api/rules/{rule_id}     — soft-delete a rule
"""
from __future__ import annotations

import json
import operator
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.storage import get_db_connection

router = APIRouter()


# ─── Models ───────────────────────────────────────────────────────────────────

class RuleCondition(BaseModel):
    field:    str           # e.g. "cart_total", "item_count", "customer_tag"
    operator: str           # eq, neq, gt, gte, lt, lte, contains, not_contains
    value:    Any


class RuleAction(BaseModel):
    type:    str            # show_offer, apply_discount, redirect, show_upsell
    payload: dict[str, Any] = {}


class RuleCreate(BaseModel):
    shop_domain:  str = Field(min_length=1, max_length=200)
    rule_name:    str = Field(min_length=1, max_length=200)
    priority:     int = Field(default=0)
    conditions:   list[RuleCondition]
    actions:      list[RuleAction]
    match_all:    bool = True   # AND (True) vs OR (False)


class EvaluateRequest(BaseModel):
    shop_domain: str
    context:     dict[str, Any]  # e.g. {cart_total: 89900, item_count: 3}


# ─── Rule evaluation ──────────────────────────────────────────────────────────

_OPS = {
    "eq":           operator.eq,
    "neq":          operator.ne,
    "gt":           operator.gt,
    "gte":          operator.ge,
    "lt":           operator.lt,
    "lte":          operator.le,
    "contains":     lambda a, b: b in a if isinstance(a, (str, list)) else False,
    "not_contains": lambda a, b: b not in a if isinstance(a, (str, list)) else True,
}


def _eval_condition(ctx: dict, cond: dict) -> bool:
    field    = cond.get("field", "")
    op_name  = cond.get("operator", "eq")
    expected = cond.get("value")
    actual   = ctx.get(field)
    if actual is None:
        return False
    op_fn = _OPS.get(op_name)
    if not op_fn:
        return False
    try:
        return bool(op_fn(actual, expected))
    except (TypeError, ValueError):
        return False


def _evaluate_rule(rule: dict, ctx: dict) -> bool:
    conditions = json.loads(rule.get("conditions_json", "[]"))
    match_all  = rule.get("match_all", 1)
    if not conditions:
        return True
    results = [_eval_condition(ctx, c) for c in conditions]
    return all(results) if match_all else any(results)


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/rules", summary="List active rules for a shop")
def list_rules(shop_domain: str) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM business_rules
            WHERE shop_domain = ? AND deleted = 0
            ORDER BY priority DESC, created_at ASC
            """,
            (shop_domain,),
        ).fetchall()
    result = []
    for row in rows:
        r = dict(row)
        r["conditions"] = json.loads(r.pop("conditions_json", "[]"))
        r["actions"]    = json.loads(r.pop("actions_json", "[]"))
        result.append(r)
    return result


@router.post("/rules", summary="Create or update a rule", status_code=status.HTTP_201_CREATED)
def create_rule(payload: RuleCreate) -> dict[str, Any]:
    rule_id = str(uuid.uuid4())
    now     = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO business_rules
              (id, shop_domain, rule_name, priority, conditions_json, actions_json, match_all, deleted, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                rule_id,
                payload.shop_domain,
                payload.rule_name,
                payload.priority,
                json.dumps([c.model_dump() for c in payload.conditions]),
                json.dumps([a.model_dump() for a in payload.actions]),
                int(payload.match_all),
                now,
                now,
            ),
        )
    return {"rule_id": rule_id, "status": "created"}


@router.post("/rules/evaluate", summary="Evaluate rules against a cart/session context")
def evaluate_rules(payload: EvaluateRequest) -> dict[str, Any]:
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM business_rules
            WHERE shop_domain = ? AND deleted = 0
            ORDER BY priority DESC
            """,
            (payload.shop_domain,),
        ).fetchall()

    matched_actions: list[dict] = []
    for row in rows:
        if _evaluate_rule(dict(row), payload.context):
            actions = json.loads(row["actions_json"] or "[]")
            matched_actions.extend(actions)

    return {
        "shop_domain": payload.shop_domain,
        "matched":     len(matched_actions) > 0,
        "actions":     matched_actions,
    }


@router.delete("/rules/{rule_id}", summary="Soft-delete a rule", status_code=status.HTTP_200_OK)
def delete_rule(rule_id: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cur = conn.execute(
            "UPDATE business_rules SET deleted = 1, updated_at = ? WHERE id = ?",
            (now, rule_id),
        )
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"rule_id": rule_id, "status": "deleted"}
