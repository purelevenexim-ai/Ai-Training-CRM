"""
Monitoring routes for PureLeven WhatsApp AI system.

Endpoints:
  GET  /api/monitoring/health     — System health check
  GET  /api/monitoring/dashboard  — Stats dashboard for owner
  GET  /api/monitoring/alerts     — Recent alerts
  POST /api/monitoring/test-alert — Send a test alert to owner
"""

from __future__ import annotations

import logging
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from app.ai.alert_sender import send_daily_health_report, send_owner_alert
from app.storage import get_db_connection
from app.services.product_followup_service import (
    get_product_followup_stats,
    list_product_followups,
    preview_due_product_followups,
    run_due_product_followups,
)

logger = logging.getLogger(__name__)
router = APIRouter()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAINING_ARTIFACTS_DIR = PROJECT_ROOT / "training_artifacts"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _24h_ago() -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()


@router.get("/monitoring/health")
def health_check() -> dict[str, Any]:
    """
    System health check.
    Returns component statuses and key metrics.
    """
    status: dict[str, Any] = {
        "status": "ok",
        "timestamp": _now(),
        "components": {},
    }

    try:
        with get_db_connection() as conn:
            # WhatsApp messages sent last 24h
            row = conn.execute(
                """
                SELECT
                  COUNT(*) as total,
                  SUM(CASE WHEN delivery_status = 'failed' THEN 1 ELSE 0 END) as failed
                                FROM journey_messages
                WHERE created_at > ?
                """,
                (_24h_ago(),),
            ).fetchone()
            total_24h = row["total"] if row else 0
            failed_24h = row["failed"] if row else 0
            failure_rate = round((failed_24h / total_24h) * 100, 1) if total_24h > 0 else 0

            # Active 24h sessions
            active_sessions = conn.execute(
                "SELECT COUNT(*) as cnt FROM conversation_sessions WHERE is_active = 1 AND session_expires > ?",
                (_now(),),
            ).fetchone()["cnt"]

            # Products synced
            product_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM shopify_products",
            ).fetchone()["cnt"]
            last_sync = conn.execute(
                "SELECT MAX(synced_at) as last FROM shopify_products",
            ).fetchone()["last"]

            # Pending followups
            pending_followups = conn.execute(
                "SELECT COUNT(*) as cnt FROM conversation_followups WHERE sent = 0 AND scheduled_at <= ?",
                (_now(),),
            ).fetchone()["cnt"]

            # Recent alerts
            critical_alerts = conn.execute(
                "SELECT COUNT(*) as cnt FROM monitoring_alerts WHERE severity = 'critical' AND created_at > ?",
                (_24h_ago(),),
            ).fetchone()["cnt"]

        status["components"] = {
            "database": "ok",
            "whatsapp": {
                "messages_sent_24h": total_24h,
                "messages_failed_24h": failed_24h,
                "failure_rate": f"{failure_rate}%",
                "status": "degraded" if failure_rate > 10 else "ok",
            },
            "ai_sessions": {
                "active": active_sessions,
                "pending_followups": pending_followups,
                "status": "ok",
            },
            "product_followups": {
                **get_product_followup_stats(),
                "status": "ok",
            },
            "shopify_sync": {
                "products_synced": product_count,
                "last_sync": last_sync,
                "status": "ok" if product_count > 0 else "warning",
            },
        }

        # Overall status
        if failure_rate > 20:
            status["status"] = "degraded"
        elif critical_alerts > 0:
            status["status"] = "warning"

    except Exception as exc:
        logger.error("Health check DB error: %s", exc)
        status["status"] = "error"
        status["components"]["database"] = f"error: {str(exc)[:100]}"

    return status


@router.get("/monitoring/dashboard")
def get_dashboard() -> dict[str, Any]:
    """Stats dashboard — used by owner to monitor AI system performance."""
    try:
        with get_db_connection() as conn:
            # Customer counts
            total_customers = conn.execute(
                "SELECT COUNT(*) as cnt FROM journey_customers",
            ).fetchone()["cnt"]
            active_whatsapp = conn.execute(
                "SELECT COUNT(*) as cnt FROM journey_customers WHERE do_not_message = 0",
            ).fetchone()["cnt"]
            unsubscribed = conn.execute(
                "SELECT COUNT(*) as cnt FROM journey_customers WHERE whatsapp_subscription_status = 'unsubscribed'",
            ).fetchone()["cnt"]

            # 24h session performance
            sessions_row = conn.execute(
                """
                SELECT
                  COUNT(*) as total,
                  SUM(CASE WHEN converted = 1 THEN 1 ELSE 0 END) as converted,
                  AVG(messages_sent) as avg_messages
                FROM conversation_sessions
                WHERE created_at > ?
                """,
                (_24h_ago(),),
            ).fetchone()

            # Followup click rate
            clicks_row = conn.execute(
                """
                SELECT
                  COUNT(*) as sent,
                  SUM(CASE WHEN clicked = 1 THEN 1 ELSE 0 END) as clicked
                FROM conversation_followups
                WHERE sent = 1 AND sent_at > ?
                """,
                (_24h_ago(),),
            ).fetchone()

            # Email metrics (last 24h)
            email_row = conn.execute(
                """
                SELECT
                  COUNT(*) as total,
                  SUM(CASE WHEN email_status = 'sent' THEN 1 ELSE 0 END) as sent,
                  SUM(CASE WHEN email_status IS NOT NULL AND email_status != 'sent' THEN 1 ELSE 0 END) as failed
                FROM journey_messages
                WHERE created_at > ?
                """,
                (_24h_ago(),),
            ).fetchone()

            # Email unsubscribes (last 24h)
            email_unsubs = conn.execute(
                "SELECT COUNT(*) as cnt FROM journey_customers WHERE do_not_email = 1",
            ).fetchone()["cnt"]

            # Intent breakdown (last 24h customer replies)
            # Not tracked yet — placeholder
            recent_alerts = conn.execute(
                "SELECT * FROM monitoring_alerts ORDER BY created_at DESC LIMIT 10",
            ).fetchall()

    except Exception as exc:
        logger.error("Dashboard query error: %s", exc)
        return {"error": str(exc)}

    sessions_total = sessions_row["total"] if sessions_row else 0
    sessions_converted = sessions_row["converted"] if sessions_row else 0
    clicks_sent = clicks_row["sent"] if clicks_row else 0
    clicks_clicked = clicks_row["clicked"] if clicks_row else 0
    email_total = email_row["total"] if email_row else 0
    email_sent = email_row["sent"] if email_row else 0
    email_failed = email_row["failed"] if email_row else 0

    return {
        "customers": {
            "total": total_customers,
            "active_whatsapp": active_whatsapp,
            "unsubscribed": unsubscribed,
        },
        "ai_sessions_24h": {
            "total_opened": sessions_total,
            "converted": sessions_converted,
            "conversion_rate": f"{round((sessions_converted / sessions_total) * 100, 1)}%"
            if sessions_total > 0 else "0%",
            "avg_messages_per_session": round(sessions_row["avg_messages"] or 0, 1) if sessions_row else 0,
        },
        "followup_performance_24h": {
            "sent": clicks_sent,
            "clicked": clicks_clicked,
            "click_rate": f"{round((clicks_clicked / clicks_sent) * 100, 1)}%"
            if clicks_sent > 0 else "0%",
        },
        "product_followups": get_product_followup_stats(),
        "email_performance_24h": {
            "total_journey_messages": email_total,
            "emails_sent": email_sent,
            "emails_failed": email_failed,
            "success_rate": f"{round((email_sent / email_total) * 100, 1)}%"
            if email_total > 0 else "0%",
            "total_unsubscribed": email_unsubs,
        },
        "recent_alerts": [dict(a) for a in recent_alerts],
    }


@router.get("/monitoring/alerts")
def get_alerts(limit: int = 50, severity: str | None = None) -> dict[str, Any]:
    """Return recent alerts from monitoring_alerts table."""
    with get_db_connection() as conn:
        if severity:
            rows = conn.execute(
                "SELECT * FROM monitoring_alerts WHERE severity = ? ORDER BY created_at DESC LIMIT ?",
                (severity, min(limit, 200)),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM monitoring_alerts ORDER BY created_at DESC LIMIT ?",
                (min(limit, 200),),
            ).fetchall()
    return {"alerts": [dict(r) for r in rows], "count": len(rows)}


@router.post("/monitoring/test-alert")
def test_alert() -> dict[str, str]:
    """Send a test WhatsApp alert to the owner. Use to verify alert delivery."""
    sent = send_owner_alert(
        "This is a test alert from PureLeven WhatsApp AI system. Everything is working correctly! ✅",
        severity="info",
        alert_type="test",
    )
    return {"status": "sent" if sent else "failed"}


@router.post("/monitoring/daily-report")
def send_daily_report() -> dict[str, str]:
    """Manually trigger the daily health report (n8n or cron also calls this)."""
    try:
        with get_db_connection() as conn:
            health = health_check()
            wa = health.get("components", {}).get("whatsapp", {})
            sessions = health.get("components", {}).get("ai_sessions", {})

            new_customers = conn.execute(
                "SELECT COUNT(*) as cnt FROM journey_customers WHERE created_at > ?",
                (_24h_ago(),),
            ).fetchone()["cnt"]

            unsubs = conn.execute(
                "SELECT COUNT(*) as cnt FROM journey_customers WHERE whatsapp_subscription_status = 'unsubscribed' AND updated_at > ?",
                (_24h_ago(),),
            ).fetchone()["cnt"]

        stats = {
            "messages_sent_24h": wa.get("messages_sent_24h", 0),
            "messages_failed": wa.get("messages_failed_24h", 0),
            "failure_rate": wa.get("failure_rate", "0%"),
            "new_customers": new_customers,
            "unsubscribes_24h": unsubs,
            "active_sessions": sessions.get("active", 0),
            "session_conversions": 0,  # Will populate when Shopify order tracking added
        }

        if float(str(wa.get("failure_rate", "0%")).replace("%", "")) > 10:
            stats["warnings"] = [f"High failure rate: {wa.get('failure_rate')}"]

        send_daily_health_report(stats)
        return {"status": "sent"}

    except Exception as exc:
        logger.error("Daily report failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


@router.get("/monitoring/product-followups")
def get_product_followups(
    limit: int = 50,
    phone: str | None = None,
    send_status: str | None = None,
) -> dict[str, Any]:
    items = list_product_followups(limit=limit, phone=phone, send_status=send_status)
    return {
        "count": len(items),
        "items": items,
        "stats": get_product_followup_stats(),
    }


@router.post("/monitoring/product-followups/run")
def run_product_followups(limit: int = 25, send_live: bool = False) -> dict[str, Any]:
    processed = run_due_product_followups(limit=limit, send_live=send_live)
    return {
        "processed_count": len(processed),
        "processed": processed,
        "stats": get_product_followup_stats(),
        "send_live": send_live,
    }


@router.get("/monitoring/product-followups/preview")
def preview_product_followups(limit: int = 25) -> dict[str, Any]:
    previews = preview_due_product_followups(limit=limit)
    return {
        "count": len(previews),
        "items": previews,
        "stats": get_product_followup_stats(),
    }


@router.get("/monitoring/training-releases")
def get_training_releases() -> dict[str, Any]:
    current_path = TRAINING_ARTIFACTS_DIR / "current_release.json"
    history_path = TRAINING_ARTIFACTS_DIR / "release_history.json"

    current = {}
    history: list[dict[str, Any]] = []
    if current_path.exists():
        current = json.loads(current_path.read_text(encoding="utf-8"))
    if history_path.exists():
        history = json.loads(history_path.read_text(encoding="utf-8"))

    return {
        "current": current,
        "history": history[:10],
        "artifacts_dir": str(TRAINING_ARTIFACTS_DIR),
    }
