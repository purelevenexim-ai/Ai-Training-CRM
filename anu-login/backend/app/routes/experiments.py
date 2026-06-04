"""
Basil Commerce OS — Phase 3
routes/experiments.py

A/B experiment framework.
Endpoints:
  GET  /api/experiments?shop_domain=x       — list experiments
  POST /api/experiments                     — create experiment
  POST /api/experiments/assign              — get/create assignment for a session
  POST /api/experiments/{exp_id}/result     — record a conversion result
  GET  /api/experiments/{exp_id}/stats      — live stats (conversion rate per variant)
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.statistical_analysis_service import StatisticalAnalysisService
from app.storage import get_db_connection

_stats_svc = StatisticalAnalysisService()

router = APIRouter()


# ─── Models ───────────────────────────────────────────────────────────────────

class ExperimentCreate(BaseModel):
    shop_domain:  str = Field(min_length=1, max_length=200)
    name:         str = Field(min_length=1, max_length=200)
    description:  str = ""
    variants:     list[dict[str, Any]]  # [{name: "A", weight: 50}, {name: "B", weight: 50}]
    goal_event:   str = "purchase"      # event_name that counts as conversion


class AssignRequest(BaseModel):
    experiment_id: str
    session_id:    str
    user_id:       str = ""


class ResultRequest(BaseModel):
    experiment_id: str
    session_id:    str
    variant:       str
    event_name:    str
    value:         float = 0


# ─── Deterministic bucketing ──────────────────────────────────────────────────

def _bucket(exp_id: str, session_id: str, total_weight: int) -> int:
    """Returns 0..(total_weight-1) deterministically for a session."""
    key    = f"{exp_id}:{session_id}"
    digest = hashlib.md5(key.encode()).hexdigest()
    return int(digest[:8], 16) % total_weight


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/experiments", summary="List experiments for a shop")
def list_experiments(shop_domain: str) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM experiments WHERE shop_domain = ? ORDER BY created_at DESC",
            (shop_domain,),
        ).fetchall()
    result = []
    for row in rows:
        r = dict(row)
        r["variants"] = json.loads(r.pop("variants_json", "[]"))
        result.append(r)
    return result


@router.post("/experiments", summary="Create an experiment", status_code=status.HTTP_201_CREATED)
def create_experiment(payload: ExperimentCreate) -> dict[str, Any]:
    exp_id = str(uuid.uuid4())
    now    = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO experiments
              (id, shop_domain, name, description, variants_json, goal_event, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'running', ?, ?)
            """,
            (
                exp_id,
                payload.shop_domain,
                payload.name,
                payload.description,
                json.dumps(payload.variants),
                payload.goal_event,
                now,
                now,
            ),
        )
    return {"experiment_id": exp_id, "status": "running"}


@router.post("/experiments/assign", summary="Get or create a variant assignment")
def assign_variant(payload: AssignRequest) -> dict[str, Any]:
    with get_db_connection() as conn:
        # Check if already assigned
        existing = conn.execute(
            "SELECT * FROM experiment_assignments WHERE experiment_id = ? AND session_id = ?",
            (payload.experiment_id, payload.session_id),
        ).fetchone()
        if existing:
            return dict(existing)

        # Fetch experiment
        exp = conn.execute(
            "SELECT * FROM experiments WHERE id = ? AND status = 'running'",
            (payload.experiment_id,),
        ).fetchone()
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found or not running")

        variants     = json.loads(exp["variants_json"] or "[]")
        total_weight = sum(v.get("weight", 1) for v in variants)
        bucket       = _bucket(payload.experiment_id, payload.session_id, total_weight)

        # Pick variant by cumulative weight
        cumulative = 0
        chosen_variant = variants[0]["name"] if variants else "control"
        for v in variants:
            cumulative += v.get("weight", 1)
            if bucket < cumulative:
                chosen_variant = v["name"]
                break

        assignment_id = str(uuid.uuid4())
        now           = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO experiment_assignments
              (id, experiment_id, session_id, user_id, variant, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (assignment_id, payload.experiment_id, payload.session_id,
             payload.user_id, chosen_variant, now),
        )

    return {
        "id":            assignment_id,
        "experiment_id": payload.experiment_id,
        "session_id":    payload.session_id,
        "variant":       chosen_variant,
        "created_at":    now,
    }


@router.post("/experiments/{exp_id}/result", summary="Record a conversion")
def record_result(exp_id: str, payload: ResultRequest) -> dict[str, Any]:
    result_id = str(uuid.uuid4())
    now       = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO experiment_results
              (id, experiment_id, session_id, variant, event_name, value, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (result_id, exp_id, payload.session_id,
             payload.variant, payload.event_name, payload.value, now),
        )
    return {"result_id": result_id, "status": "recorded"}


@router.get("/experiments/{exp_id}/stats", summary="Live A/B test stats")
def experiment_stats(exp_id: str) -> dict[str, Any]:
    with get_db_connection() as conn:
        exp = conn.execute("SELECT * FROM experiments WHERE id = ?", (exp_id,)).fetchone()
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found")

        assignments = conn.execute(
            "SELECT variant, COUNT(*) as cnt FROM experiment_assignments WHERE experiment_id = ? GROUP BY variant",
            (exp_id,),
        ).fetchall()
        conversions = conn.execute(
            "SELECT variant, COUNT(*) as cnt, SUM(value) as total_value FROM experiment_results WHERE experiment_id = ? GROUP BY variant",
            (exp_id,),
        ).fetchall()

    assign_map = {r["variant"]: r["cnt"] for r in assignments}
    conv_map   = {r["variant"]: {"count": r["cnt"], "value": r["total_value"] or 0} for r in conversions}

    variants = json.loads(exp["variants_json"] or "[]")
    stats    = []
    for v in variants:
        vname     = v["name"]
        assigned  = assign_map.get(vname, 0)
        converted = conv_map.get(vname, {}).get("count", 0)
        value     = conv_map.get(vname, {}).get("value", 0)
        stats.append({
            "variant":         vname,
            "assigned":        assigned,
            "converted":       converted,
            "conversion_rate": round(converted / assigned * 100, 2) if assigned else 0,
            "total_value":     value,
        })

    # Statistical significance analysis
    significance = _stats_svc.test_variants([
        {"name": s["variant"], "assigned": s["assigned"], "converted": s["converted"]}
        for s in stats
    ])

    # Merge stats with significance data
    sig_by_name = {v["name"]: v for v in significance["variants"]}
    for s in stats:
        sig = sig_by_name.get(s["variant"], {})
        s["p_value"]             = sig.get("p_value")
        s["confidence_interval"] = sig.get("confidence_interval")
        s["z_score"]             = sig.get("z_score")
        s["effect_size"]         = sig.get("effect_size")
        s["uplift_pct"]          = sig.get("uplift_pct")
        s["is_significant"]      = sig.get("is_significant", False)

    return {
        "experiment_id":   exp_id,
        "name":            exp["name"],
        "status":          exp["status"],
        "goal_event":      exp["goal_event"],
        "variants":        stats,
        "winner":          significance["winner"],
        "is_significant":  significance["is_significant"],
        "confidence":      significance["confidence"],
        "sample_adequate": significance["sample_adequate"],
        "recommendation":  significance["recommendation"],
    }
