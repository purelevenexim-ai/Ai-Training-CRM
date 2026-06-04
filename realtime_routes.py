"""
Real-time WebSocket Endpoints - Phase 3 Complete
Streams: journey analytics (metrics) + step logs (steps)

ARCHITECTURE:
  - Single background listener task per Redis channel (not per connection)
  - Listeners start at app lifespan → broadcast to all active WebSocket clients
  - Heartbeat every 10s keeps connections alive & pushes live metrics snapshot
  - WebSocket connections join/leave the ConnectionManager pool

REDIS CHANNELS:
  pubsub:metrics  ← journey_event payloads from journeys_routes.py
  pubsub:steps    ← enrollment_update payloads from journeys_routes.py
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import json
import asyncio
import logging
from datetime import datetime
import os

logger = logging.getLogger("pureleven.realtime")

REDIS_URL = os.getenv("REDIS_URL", "redis://pureleven-redis:6379/0")

router = APIRouter(prefix="/api/crm/ws", tags=["realtime"])
whatsapp_router = APIRouter(prefix="/api/crm/whatsapp/ws", tags=["realtime"])

# ─── Connection Manager ────────────────────────────────────────────────────────

class ConnectionManager:
    """Manages pools of WebSocket connections per channel."""

    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {
            "metrics": [],
            "steps": [],
        }
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, channel: str):
        await ws.accept()
        async with self._lock:
            self.connections[channel].append(ws)
        logger.info(f"WS connected [{channel}] total={len(self.connections[channel])}")

    async def disconnect(self, ws: WebSocket, channel: str):
        async with self._lock:
            if ws in self.connections[channel]:
                self.connections[channel].remove(ws)
        logger.info(f"WS disconnected [{channel}] total={len(self.connections[channel])}")

    async def broadcast(self, message: dict, channel: str):
        """Send message to all clients on channel; auto-prune dead connections."""
        dead: list[WebSocket] = []
        for ws in list(self.connections.get(channel, [])):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws, channel)

    async def send_one(self, ws: WebSocket, message: dict):
        """Send a message to a single WebSocket connection."""
        try:
            await ws.send_json(message)
        except Exception:
            pass

    @property
    def stats(self) -> dict:
        return {ch: len(conns) for ch, conns in self.connections.items()}


manager = ConnectionManager()

# Background task handles
_tasks: dict[str, asyncio.Task] = {}

# ─── Background Listeners ─────────────────────────────────────────────────────

async def _redis_listener(channel: str):
    """
    Single async task per channel.
    Subscribes to pubsub:{channel} and broadcasts to all WS clients.
    Automatically reconnects on Redis failure.
    """
    import redis.asyncio as aioredis

    while True:
        try:
            r = aioredis.from_url(REDIS_URL, decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.subscribe(f"pubsub:{channel}")
            logger.info(f"Redis listener subscribed to pubsub:{channel}")

            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    try:
                        data = json.loads(msg["data"])
                        await manager.broadcast(data, channel)
                    except Exception as exc:
                        logger.warning(f"Broadcast error [{channel}]: {exc}")

        except asyncio.CancelledError:
            logger.info(f"Redis listener [{channel}] cancelled.")
            break
        except Exception as exc:
            logger.error(f"Redis listener [{channel}] crashed: {exc}. Retry in 5s...")
            await asyncio.sleep(5)


async def _heartbeat():
    """
    Every 10 seconds:
    - Sends a heartbeat to metrics channel (keeps connections alive)
    - Fetches a live metrics snapshot from DB and pushes it
    """
    while True:
        try:
            await asyncio.sleep(10)

            snapshot = await asyncio.to_thread(_get_metrics_snapshot)
            payload = {
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat(),
                "connections": manager.stats,
                **snapshot,
            }
            await manager.broadcast(payload, "metrics")

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning(f"Heartbeat error: {exc}")


def _get_metrics_snapshot() -> dict:
    """Synchronous DB query for current metrics — runs in thread pool."""
    try:
        import os
        from sqlalchemy import create_engine, func, text
        from sqlalchemy.orm import sessionmaker

        url = os.getenv("DATABASE_URL") or (
            "postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}".format(
                user=os.getenv("POSTGRES_USER", "pureleven"),
                pw=os.getenv("POSTGRES_PASSWORD", ""),
                host=os.getenv("POSTGRES_HOST", "pureleven-postgres"),
                port=os.getenv("POSTGRES_PORT", 5432),
                db=os.getenv("POSTGRES_DB", "pureleven"),
            )
        )
        engine = create_engine(url, pool_pre_ping=True)
        Session = sessionmaker(bind=engine)
        db = Session()

        try:
            rows = db.execute(text("""
                SELECT
                    (SELECT COUNT(*) FROM crm_journey_instances WHERE status = 'ACTIVE')  AS active_instances,
                    (SELECT COUNT(*) FROM crm_journey_instances WHERE status = 'COMPLETED') AS completed_instances,
                    (SELECT COUNT(*) FROM crm_customers)                                   AS total_customers,
                    (SELECT COUNT(*) FROM crm_journeys WHERE status = 'ACTIVE')            AS active_journeys,
                    (SELECT COALESCE(SUM(order_value), 0) FROM crm_journey_attribution)   AS total_attributed_revenue
            """)).fetchone()

            if rows:
                return {
                    "active_instances": int(rows[0] or 0),
                    "completed_instances": int(rows[1] or 0),
                    "total_customers": int(rows[2] or 0),
                    "active_journeys": int(rows[3] or 0),
                    "total_attributed_revenue": float(rows[4] or 0),
                }
        finally:
            db.close()
            engine.dispose()

    except Exception as exc:
        logger.debug(f"Metrics snapshot error: {exc}")

    return {}


# ─── Lifecycle ────────────────────────────────────────────────────────────────

def start_listeners():
    """Start background listeners + heartbeat. Call from app lifespan."""
    loop = asyncio.get_event_loop()
    _tasks["metrics"] = loop.create_task(_redis_listener("metrics"))
    _tasks["steps"] = loop.create_task(_redis_listener("steps"))
    _tasks["heartbeat"] = loop.create_task(_heartbeat())
    logger.info("Started real-time listeners: metrics, steps, heartbeat")


def stop_listeners():
    """Cancel all background tasks. Call from app lifespan shutdown."""
    for name, task in _tasks.items():
        task.cancel()
        logger.info(f"Cancelled listener task: {name}")
    _tasks.clear()


# ─── WebSocket Endpoints ──────────────────────────────────────────────────────

@router.websocket("/metrics")
@whatsapp_router.websocket("/metrics")
async def ws_metrics(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket: real-time journey metrics stream.
    Messages: heartbeat | journey_event (created/enrolled/completed/stopped/cloned)
    """
    await manager.connect(websocket, "metrics")

    # Send immediate snapshot so dashboard shows data right away
    try:
        snapshot = await asyncio.to_thread(_get_metrics_snapshot)
        await manager.send_one(websocket, {
            "type": "initial_snapshot",
            "timestamp": datetime.utcnow().isoformat(),
            **snapshot,
        })
    except Exception:
        pass

    try:
        while True:
            # Keep alive — accept any client message (ping/filter subscription)
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, "metrics")
    except Exception as exc:
        logger.warning(f"Metrics WS error: {exc}")
        await manager.disconnect(websocket, "metrics")


@router.websocket("/steps")
@whatsapp_router.websocket("/steps")
async def ws_steps(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket: real-time journey step & enrollment event stream.
    Messages: enrollment_update (status, current_step, customer_email)
    """
    await manager.connect(websocket, "steps")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, "steps")
    except Exception as exc:
        logger.warning(f"Steps WS error: {exc}")
        await manager.disconnect(websocket, "steps")


# ─── Broadcast Helpers (call from route handlers) ─────────────────────────────

async def broadcast_metrics_update(metrics: dict):
    """
    Publish a metrics update to all connected metrics WebSocket clients.
    Also writes to Redis so other workers receive it.
    """
    import redis as _redis

    msg = {
        "type": "metrics_update",
        "data": metrics,
        "timestamp": datetime.utcnow().isoformat(),
    }
    try:
        r = _redis.Redis.from_url(REDIS_URL, decode_responses=True)
        r.publish("pubsub:metrics", json.dumps(msg))
    except Exception as exc:
        logger.warning(f"Redis publish (metrics) failed: {exc}")

    await manager.broadcast(msg, "metrics")


async def broadcast_step_log(step_log: dict):
    """
    Publish a step log to all connected steps WebSocket clients.
    Also writes to Redis so other workers receive it.
    """
    import redis as _redis

    msg = {
        "type": "step_log",
        "data": step_log,
        "timestamp": datetime.utcnow().isoformat(),
    }
    try:
        r = _redis.Redis.from_url(REDIS_URL, decode_responses=True)
        r.publish("pubsub:steps", json.dumps(msg))
    except Exception as exc:
        logger.warning(f"Redis publish (steps) failed: {exc}")

    await manager.broadcast(msg, "steps")


# ─── Health Endpoint ──────────────────────────────────────────────────────────

@router.get("/health")
def ws_health():
    """WebSocket infrastructure health check."""
    try:
        import redis as _redis
        r = _redis.Redis.from_url(REDIS_URL, socket_connect_timeout=2)
        r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    return {
        "status": "healthy" if redis_ok else "degraded",
        "redis": "connected" if redis_ok else "error",
        "background_tasks": {name: not task.done() for name, task in _tasks.items()},
        "active_connections": manager.stats,
        "timestamp": datetime.utcnow().isoformat(),
    }
