"""
Basil Commerce OS — Phase 1
routes/flags.py

Feature flags CRUD.
GET  /api/flags             — fetch all flags for a shop
POST /api/flags             — upsert a flag
GET  /api/flags/{flag_name} — single flag check (used by theme JS / frontend)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.storage import get_db_connection

router = APIRouter()


class FlagUpsert(BaseModel):
    shop_domain:        str   = Field(min_length=1, max_length=200)
    flag_name:          str   = Field(min_length=1, max_length=100)
    enabled:            bool  = True
    rollout_percentage: int   = Field(default=100, ge=0, le=100)


class FlagRecord(BaseModel):
    id:                 int
    shop_domain:        str
    flag_name:          str
    enabled:            bool
    rollout_percentage: int
    created_at:         str
    updated_at:         str


@router.get("/flags", summary="List all feature flags for a shop")
def list_flags(shop_domain: str) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM feature_flags WHERE shop_domain = ? ORDER BY flag_name",
            (shop_domain,),
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/flags/{flag_name}", summary="Check a single feature flag")
def get_flag(flag_name: str, shop_domain: str) -> dict[str, Any]:
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM feature_flags WHERE shop_domain = ? AND flag_name = ?",
            (shop_domain, flag_name),
        ).fetchone()
    if not row:
        return {"flag_name": flag_name, "enabled": False, "rollout_percentage": 0}
    return dict(row)


@router.post("/flags", summary="Upsert a feature flag", status_code=status.HTTP_200_OK)
def upsert_flag(payload: FlagUpsert) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO feature_flags (shop_domain, flag_name, enabled, rollout_percentage, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(shop_domain, flag_name) DO UPDATE SET
                enabled            = excluded.enabled,
                rollout_percentage = excluded.rollout_percentage,
                updated_at         = excluded.updated_at
            """,
            (
                payload.shop_domain,
                payload.flag_name,
                int(payload.enabled),
                payload.rollout_percentage,
                now,
                now,
            ),
        )
        row = conn.execute(
            "SELECT * FROM feature_flags WHERE shop_domain = ? AND flag_name = ?",
            (payload.shop_domain, payload.flag_name),
        ).fetchone()
    return dict(row)
