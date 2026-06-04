"""
WebSocket routes for real-time CRM metrics and journey step streaming.
Endpoints:
    GET /api/crm/ws/metrics           — live aggregated metrics broadcast
    GET /api/crm/whatsapp/ws/metrics  — proxy-safe alias for public track host
    GET /api/crm/ws/steps             — live journey step execution logs
    GET /api/crm/whatsapp/ws/steps    — proxy-safe alias for public track host
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Set

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# ─── Connection Managers ──────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.active.discard(ws)

    async def broadcast(self, data: dict) -> None:
        dead: Set[WebSocket] = set()
        payload = json.dumps(data)
        for ws in list(self.active):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active.discard(ws)


metrics_manager = ConnectionManager()
steps_manager = ConnectionManager()


# ─── Auth helper ─────────────────────────────────────────────────────────────

def _is_valid_token(token: str | None) -> bool:
    if not token or not settings.admin_secret:
        return False
    return token == settings.admin_secret


# ─── Metrics WebSocket ───────────────────────────────────────────────────────

@router.websocket('/crm/ws/metrics')
@router.websocket('/crm/whatsapp/ws/metrics')
async def ws_metrics(
    websocket: WebSocket,
    token: str | None = Query(default=None),
):
    if not _is_valid_token(token):
        await websocket.close(code=4401, reason='Unauthorized')
        return

    await metrics_manager.connect(websocket)
    logger.info('Metrics WS connected. Total connections: %d', len(metrics_manager.active))

    try:
        # Send initial ping so the client knows the connection is alive
        await websocket.send_text(json.dumps({'type': 'connected', 'ts': _now()}))

        # Keep connection alive; broadcast is driven externally via broadcast_metrics()
        while True:
            # Wait for a client ping or idle; echo pings back
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                await websocket.send_text(json.dumps({'type': 'pong', 'ts': _now()}))
            except asyncio.TimeoutError:
                # Send a heartbeat every 30 s so nginx/browser don't drop the conn
                await websocket.send_text(json.dumps({'type': 'heartbeat', 'ts': _now()}))
    except WebSocketDisconnect:
        pass
    finally:
        metrics_manager.disconnect(websocket)
        logger.info('Metrics WS disconnected. Remaining: %d', len(metrics_manager.active))


# ─── Steps WebSocket ─────────────────────────────────────────────────────────

@router.websocket('/crm/ws/steps')
@router.websocket('/crm/whatsapp/ws/steps')
async def ws_steps(
    websocket: WebSocket,
    token: str | None = Query(default=None),
):
    if not _is_valid_token(token):
        await websocket.close(code=4401, reason='Unauthorized')
        return

    await steps_manager.connect(websocket)
    logger.info('Steps WS connected. Total connections: %d', len(steps_manager.active))

    try:
        await websocket.send_text(json.dumps({'type': 'connected', 'ts': _now()}))

        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                await websocket.send_text(json.dumps({'type': 'pong', 'ts': _now()}))
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({'type': 'heartbeat', 'ts': _now()}))
    except WebSocketDisconnect:
        pass
    finally:
        steps_manager.disconnect(websocket)
        logger.info('Steps WS disconnected. Remaining: %d', len(steps_manager.active))


# ─── Broadcast helpers (called from other services) ──────────────────────────

async def broadcast_metrics(data: dict) -> None:
    """Push a metrics update to all connected metrics clients."""
    await metrics_manager.broadcast({'type': 'metrics', 'data': data, 'ts': _now()})


async def broadcast_step_log(data: dict) -> None:
    """Push a journey step log entry to all connected step clients."""
    await steps_manager.broadcast({'type': 'step_log', 'data': data, 'ts': _now()})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
