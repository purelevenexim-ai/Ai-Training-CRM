"""
Phase 2 — Campaign Routes

CRUD + execution endpoints for broadcast campaigns.
All endpoints require ?admin_secret=.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import settings
from app.services.campaign_service import (
    create_campaign, get_campaign, list_campaigns,
    update_campaign, delete_campaign,
    preview_campaign, send_campaign_now, get_campaign_stats, process_due_campaigns,
)

router = APIRouter(tags=["campaigns"])


def _auth(admin_secret: str):
    if admin_secret != settings.admin_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")


class CampaignCreate(BaseModel):
    name: str
    description: str = ""
    type: str = "email"
    audience_type: str = "all"
    list_id: str | None = None
    segment_filter: dict = {}
    template_id: str | None = None
    schedule_type: str = "send_now"
    scheduled_at: str | None = None
    recurring_pattern: str | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    type: str | None = None
    audience_type: str | None = None
    list_id: str | None = None
    segment_filter: dict | None = None
    template_id: str | None = None
    schedule_type: str | None = None
    scheduled_at: str | None = None
    recurring_pattern: str | None = None


@router.get("/campaigns")
def list_campaigns_endpoint(
    admin_secret: str = Query(""),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    _auth(admin_secret)
    items, total = list_campaigns(status=status, limit=limit, offset=offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/campaigns", status_code=201)
def create_campaign_endpoint(
    body: CampaignCreate,
    admin_secret: str = Query(""),
) -> dict[str, Any]:
    _auth(admin_secret)
    return create_campaign(
        name=body.name,
        description=body.description,
        type=body.type,
        audience_type=body.audience_type,
        list_id=body.list_id,
        segment_filter=body.segment_filter,
        template_id=body.template_id,
        schedule_type=body.schedule_type,
        scheduled_at=body.scheduled_at,
        recurring_pattern=body.recurring_pattern,
    )


@router.get("/campaigns/{campaign_id}")
def get_campaign_endpoint(
    campaign_id: str,
    admin_secret: str = Query(""),
) -> dict[str, Any]:
    _auth(admin_secret)
    c = get_campaign(campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return c


@router.put("/campaigns/{campaign_id}")
def update_campaign_endpoint(
    campaign_id: str,
    body: CampaignUpdate,
    admin_secret: str = Query(""),
) -> dict[str, Any]:
    _auth(admin_secret)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    result = update_campaign(campaign_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return result


@router.delete("/campaigns/{campaign_id}")
def delete_campaign_endpoint(
    campaign_id: str,
    admin_secret: str = Query(""),
) -> dict[str, Any]:
    _auth(admin_secret)
    if not delete_campaign(campaign_id):
        raise HTTPException(status_code=400, detail="Cannot delete — campaign not in draft status")
    return {"deleted": True}


@router.post("/campaigns/{campaign_id}/preview")
def preview_campaign_endpoint(
    campaign_id: str,
    admin_secret: str = Query(""),
    sample_size: int = Query(5, ge=1, le=20),
) -> list[dict]:
    _auth(admin_secret)
    return preview_campaign(campaign_id, sample_size=sample_size)


@router.post("/campaigns/{campaign_id}/send")
def send_campaign_endpoint(
    campaign_id: str,
    admin_secret: str = Query(""),
    dry_run: bool = Query(False),
) -> dict[str, Any]:
    _auth(admin_secret)
    return send_campaign_now(campaign_id, dry_run=dry_run)


@router.post("/campaigns/process-due")
def process_due_campaigns_endpoint(
    admin_secret: str = Query(""),
    limit: int = Query(25, ge=1, le=500),
) -> dict[str, Any]:
    _auth(admin_secret)
    return process_due_campaigns(limit=limit)


@router.get("/campaigns/{campaign_id}/stats")
def campaign_stats_endpoint(
    campaign_id: str,
    admin_secret: str = Query(""),
) -> dict[str, Any]:
    _auth(admin_secret)
    stats = get_campaign_stats(campaign_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return stats
