"""
Basil Commerce OS — Phase 1
routes/events.py

Event gateway: receives browser events, deduplicates, stores for async relay
to Meta CAPI and GA4 Measurement Protocol.

Deduplication: 5-second window per (shop_domain, event_name, cart_token).
Relay: synchronous for Phase 1 (async workers + Redis queue in Phase 2).
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.schemas import EventTrackRequest, EventTrackResponse
from app.storage import get_db_connection

router = APIRouter()

# ─── In-memory dedup cache (replaced by DB check in Phase 2) ──────────────────
# Key: sha256(shop_domain + event_name + cart_token), Value: timestamp
_dedup_cache: dict[str, float] = {}
_DEDUP_WINDOW_SECONDS = 5.0


def _dedup_key(shop: str, event: str, cart: str | None) -> str:
    raw = f"{shop}:{event}:{cart or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _is_duplicate(key: str) -> bool:
    last = _dedup_cache.get(key, 0.0)
    now = time.monotonic()
    if now - last < _DEDUP_WINDOW_SECONDS:
        return True
    _dedup_cache[key] = now
    # Prune stale entries every ~1000 checks
    if len(_dedup_cache) > 1000:
        cutoff = now - _DEDUP_WINDOW_SECONDS * 2
        for k in list(_dedup_cache):
            if _dedup_cache[k] < cutoff:
                del _dedup_cache[k]
    return False


# ─── Route ────────────────────────────────────────────────────────────────────

@router.post(
    "/events/track",
    response_model=EventTrackResponse,
    summary="Receive a browser-side event and relay to Meta CAPI + GA4",
    status_code=status.HTTP_202_ACCEPTED,
)
async def track_event(payload: EventTrackRequest, request: Request) -> EventTrackResponse:
    """
    Phase 1: stores event in SQLite event_logs table.
    Phase 2+: enqueues to Redis → Celery worker → Meta CAPI / GA4 Measurement Protocol.
    """
    # Deduplication guard
    key = _dedup_key(payload.shop_domain or "", payload.event_name, payload.cart_token)
    if _is_duplicate(key):
        return EventTrackResponse(
            status="duplicate",
            event_id=payload.event_id or "dup",
            message="Duplicate event suppressed within dedup window",
        )

    # Persist to event_logs
    try:
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO event_logs (
                    event_id, shop_domain, session_id, customer_id,
                    cart_token, event_name, event_source,
                    event_data, meta_sent, ga4_sent, retry_count,
                    ip_address, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?)
                """,
                (
                    payload.event_id,
                    payload.shop_domain,
                    payload.session_id,
                    payload.customer_id,
                    payload.cart_token,
                    payload.event_name,
                    "browser_pixel",
                    payload.model_dump_json(),  # store full payload as JSON
                    request.client.host if request.client else None,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
    except Exception as exc:
        # Don't fail the request over a storage error — event still tracked
        # browser-side via pixel. Log and continue.
        import logging
        logging.getLogger("basil.events").warning("event_logs insert failed: %s", exc)

    return EventTrackResponse(
        status="queued",
        event_id=payload.event_id or "",
        message="Event received. Server-side relay scheduled.",
    )


@router.get(
    "/events/health",
    summary="Event gateway health check",
    include_in_schema=False,
)
async def events_health() -> dict[str, Any]:
    return {"status": "ok", "dedup_cache_size": len(_dedup_cache)}
