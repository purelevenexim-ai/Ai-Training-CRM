"""
app/services/monitoring_service.py

Monitoring & Alert Service.

Collects system health metrics, evaluates thresholds, and writes alerts to
monitoring_alerts table. Optionally sends webhook notifications.

Usage:
    from app.services.monitoring_service import MonitoringService
    svc = MonitoringService()
    health = svc.collect_metrics()
    svc.evaluate_thresholds(health)
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.storage import get_connection

logger = logging.getLogger(__name__)

# ── Alert thresholds ──────────────────────────────────────────────────────────
THRESHOLDS = {
    "whatsapp_error_rate":    0.20,   # >20% failure rate → alert
    "email_error_rate":       0.20,
    "queue_depth_max":        500,    # >500 pending jobs → alert
    "delivery_failure_rate":  0.30,   # >30% undelivered orders → alert
    "journey_error_rate":     0.15,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _since(hours: int = 24) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


class MonitoringService:

    def collect_metrics(self, hours: int = 24) -> dict[str, Any]:
        """
        Collect all system health metrics for the last N hours.
        Returns a structured health dict.
        """
        since = _since(hours)
        metrics: dict[str, Any] = {
            "period_hours":  hours,
            "collected_at":  _now(),
            "components":    {},
            "overall_status": "healthy",
        }

        with get_connection() as conn:
            metrics["components"]["whatsapp"]  = self._whatsapp_health(conn, since)
            metrics["components"]["email"]     = self._email_health(conn, since)
            metrics["components"]["journeys"]  = self._journey_health(conn, since)
            metrics["components"]["queue"]     = self._queue_health(conn, since)
            metrics["components"]["database"]  = self._database_health(conn)
            metrics["components"]["campaigns"] = self._campaign_health(conn, since)

        # Derive overall status
        statuses = [c.get("status", "unknown") for c in metrics["components"].values()]
        if "critical" in statuses:
            metrics["overall_status"] = "critical"
        elif "warning" in statuses:
            metrics["overall_status"] = "warning"
        else:
            metrics["overall_status"] = "healthy"

        return metrics

    def _whatsapp_health(self, conn: Any, since: str) -> dict[str, Any]:
        try:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN delivery_status IN ('failed','error') THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN delivery_status = 'delivered' THEN 1 ELSE 0 END) as delivered,
                    SUM(CASE WHEN delivery_status = 'read' THEN 1 ELSE 0 END) as read_count
                FROM journey_messages
                WHERE sent_at >= ?
                """,
                (since,),
            ).fetchone()
            total   = row["total"] or 0
            failed  = row["failed"] or 0
            err_rate = failed / total if total else 0.0
            status  = "critical" if err_rate > THRESHOLDS["whatsapp_error_rate"] else "healthy"
            return {
                "status":         status,
                "total_sent":     total,
                "failed":         failed,
                "delivered":      row["delivered"] or 0,
                "read":           row["read_count"] or 0,
                "error_rate":     round(err_rate, 4),
            }
        except Exception as exc:
            return {"status": "unknown", "error": str(exc)}

    def _email_health(self, conn: Any, since: str) -> dict[str, Any]:
        try:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) as delivered,
                    SUM(CASE WHEN status = 'opened' THEN 1 ELSE 0 END) as opened
                FROM promo_send_logs
                WHERE logged_at >= ?
                """,
                (since,),
            ).fetchone()
            total    = row["total"] or 0
            failed   = row["failed"] or 0
            err_rate = failed / total if total else 0.0
            status   = "critical" if err_rate > THRESHOLDS["email_error_rate"] else "healthy"
            return {
                "status":       status,
                "total_sent":   total,
                "failed":       failed,
                "delivered":    row["delivered"] or 0,
                "opened":       row["opened"] or 0,
                "error_rate":   round(err_rate, 4),
            }
        except Exception as exc:
            return {"status": "unknown", "error": str(exc)}

    def _journey_health(self, conn: Any, since: str) -> dict[str, Any]:
        try:
            row = conn.execute(
                """
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN delivery_status='failed' THEN 1 ELSE 0 END) as failed
                FROM journey_messages WHERE sent_at >= ?
                """,
                (since,),
            ).fetchone()
            total    = row["total"] or 0
            failed   = row["failed"] or 0
            err_rate = failed / total if total else 0.0

            # Active journeys
            active = conn.execute(
                "SELECT COUNT(*) FROM journey_customers WHERE delivery_status NOT IN ('failed','cancelled')"
            ).fetchone()[0]

            status = "warning" if err_rate > THRESHOLDS["journey_error_rate"] else "healthy"
            return {
                "status":       status,
                "active_customers": active,
                "messages_sent": total,
                "failed":       failed,
                "error_rate":   round(err_rate, 4),
            }
        except Exception as exc:
            return {"status": "unknown", "error": str(exc)}

    def _queue_health(self, conn: Any, since: str) -> dict[str, Any]:
        try:
            # Count pending promotional_campaigns
            pending = conn.execute(
                """
                SELECT COUNT(*) as cnt FROM promotional_campaigns
                WHERE status IN ('scheduled','pending','processing')
                """,
            ).fetchone()[0]

            status = "warning" if pending > THRESHOLDS["queue_depth_max"] else "healthy"
            return {
                "status":          status,
                "pending_campaigns": pending,
                "threshold":       THRESHOLDS["queue_depth_max"],
            }
        except Exception as exc:
            return {"status": "unknown", "error": str(exc)}

    def _database_health(self, conn: Any) -> dict[str, Any]:
        try:
            # WAL mode status
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            # Table count
            tc = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
            # DB size
            pages   = conn.execute("PRAGMA page_count").fetchone()[0]
            pgsize  = conn.execute("PRAGMA page_size").fetchone()[0]
            size_mb = round(pages * pgsize / 1024 / 1024, 2)

            return {
                "status":       "healthy",
                "journal_mode": mode,
                "table_count":  tc,
                "size_mb":      size_mb,
            }
        except Exception as exc:
            return {"status": "unknown", "error": str(exc)}

    def _campaign_health(self, conn: Any, since: str) -> dict[str, Any]:
        try:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status='sent' THEN 1 ELSE 0 END) as sent,
                    SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status IN ('scheduled','pending') THEN 1 ELSE 0 END) as pending
                FROM promotional_campaigns
                WHERE created_at >= ?
                """,
                (since,),
            ).fetchone()
            total  = row["total"] or 0
            return {
                "status":  "healthy",
                "total":   total,
                "sent":    row["sent"] or 0,
                "failed":  row["failed"] or 0,
                "pending": row["pending"] or 0,
            }
        except Exception as exc:
            return {"status": "unknown", "error": str(exc)}

    def evaluate_thresholds(self, metrics: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Check metrics against thresholds, create alerts for violations.
        Returns list of new alerts created.
        """
        new_alerts: list[dict[str, Any]] = []
        components = metrics.get("components", {})

        for component_name, component in components.items():
            if component.get("status") not in ("warning", "critical"):
                continue

            error_rate = component.get("error_rate", 0)
            msg = f"{component_name} health is {component['status']}"
            if error_rate:
                msg += f" (error rate: {error_rate:.1%})"

            # Check if alert already raised in last hour to avoid spam
            with get_connection() as conn:
                recent = conn.execute(
                    """
                    SELECT 1 FROM monitoring_alerts
                    WHERE alert_type = ?
                      AND resolved_at IS NULL
                      AND created_at >= ?
                    """,
                    (component_name, _since(hours=1)),
                ).fetchone()

                if recent:
                    continue

                alert_id = str(uuid.uuid4())
                severity = "critical" if component["status"] == "critical" else "warning"
                conn.execute(
                    """
                    INSERT INTO monitoring_alerts
                      (id, alert_type, severity, message, details_json,
                       resolved_at, created_at)
                    VALUES (?, ?, ?, ?, ?, NULL, ?)
                    """,
                    (
                        alert_id, component_name, severity, msg,
                        json.dumps(component), _now(),
                    ),
                )
                new_alerts.append({
                    "id": alert_id, "type": component_name,
                    "severity": severity, "message": msg,
                })

                # Send webhook if configured
                self._send_webhook(component_name, severity, msg, component)

        return new_alerts

    def _send_webhook(
        self,
        component: str,
        severity: str,
        message: str,
        details: dict[str, Any],
    ) -> None:
        """Send Slack-compatible webhook notification if MONITORING_WEBHOOK_URL is set."""
        webhook_url = os.getenv("MONITORING_WEBHOOK_URL", "")
        if not webhook_url:
            return

        color = "#ff0000" if severity == "critical" else "#ffa500"
        payload = json.dumps({
            "text": f"*PureLeven Alert [{severity.upper()}]*",
            "attachments": [{
                "color":  color,
                "text":   message,
                "footer": f"Component: {component} | Time: {_now()}",
            }],
        }).encode()

        try:
            req = urllib.request.Request(
                webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as exc:
            logger.warning("Webhook send failed: %s", exc)

    def get_recent_alerts(self, limit: int = 50, include_resolved: bool = False) -> list[dict[str, Any]]:
        """Fetch recent monitoring alerts."""
        with get_connection() as conn:
            where = "" if include_resolved else "WHERE resolved_at IS NULL"
            rows = conn.execute(
                f"SELECT * FROM monitoring_alerts {where} ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        with get_connection() as conn:
            conn.execute(
                "UPDATE monitoring_alerts SET resolved_at=? WHERE id=?",
                (_now(), alert_id),
            )
        return True
