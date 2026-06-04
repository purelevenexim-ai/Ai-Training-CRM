"""
Phase 3 — Communication Analytics Routes

Unified analytics over communication_events table.
All endpoints require ?admin_secret=.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.services.event_tracking_service import (
    get_customer_events,
    get_overview_stats,
    get_source_stats,
    log_event,
)
from app.services.timeline_service import get_customer_timeline, get_customer_summary

router = APIRouter(tags=["comm_analytics"])


def _auth(admin_secret: str):
    if admin_secret != settings.admin_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/comm/stats/overview")
def overview_stats(
    admin_secret: str = Query(""),
    days: int = Query(30, ge=1, le=365),
) -> dict[str, Any]:
    _auth(admin_secret)
    return get_overview_stats(days=days)


@router.get("/comm/stats/{source_type}/{source_id}")
def source_stats(
    source_type: str,
    source_id: str,
    admin_secret: str = Query(""),
) -> dict[str, Any]:
    _auth(admin_secret)
    return get_source_stats(source_type, source_id)


@router.get("/comm/events")
def customer_events(
    email: str,
    admin_secret: str = Query(""),
    channel: str | None = Query(None),
    event_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    _auth(admin_secret)
    items, total = get_customer_events(
        email=email, limit=limit, offset=offset,
        channel=channel, event_type=event_type,
    )
    return {"items": items, "total": total}


@router.get("/comm/timeline")
def customer_timeline(
    email: str,
    admin_secret: str = Query(""),
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    _auth(admin_secret)
    events = get_customer_timeline(email, limit=limit)
    summary = get_customer_summary(email)
    return {"email": email, "events": events, "summary": summary}


@router.post("/comm/events/track")
def track_event(
    admin_secret: str = Query(""),
    customer_email: str = Query(...),
    event_type: str = Query(...),
    channel: str = Query("email"),
    source_type: str = Query("manual"),
    source_id: str | None = Query(None),
    template_id: str | None = Query(None),
    template_name: str | None = Query(None),
) -> dict[str, Any]:
    _auth(admin_secret)
    eid = log_event(
        customer_email=customer_email,
        event_type=event_type,
        channel=channel,
        source_type=source_type,
        source_id=source_id,
        template_id=template_id,
        template_name=template_name,
    )
    return {"event_id": eid}
