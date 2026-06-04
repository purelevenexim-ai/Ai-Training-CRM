"""
Promotional Campaign Service

Manages promotional email campaigns for purchased customers.
Tracks opens, clicks, queue progress, and send outcomes.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import settings
from app.services.email_service import send_email as send_raw_email, classify_smtp_error
from app.storage import get_db_connection

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_or_none(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


class PromotionalCampaignService:
    """Manages promotional campaign lifecycle and delivery."""

    CAMPAIGN_TEMPLATES = {
        "flash_sale": {
            "name": "Flash Sale - 24hrs",
            "discount": 20,
            "subject_template": "Flash sale: {discount}% off for 24 hours",
            "color": "#FF6B35",
        },
        "seasonal": {
            "name": "Seasonal Collection",
            "discount": 15,
            "subject_template": "Seasonal collection is live",
            "color": "#2E7D32",
        },
        "bundle_offer": {
            "name": "Bundle and Save",
            "discount": 25,
            "subject_template": "Bundle {items} items and save {discount}%",
            "color": "#1565C0",
        },
        "vip_exclusive": {
            "name": "VIP Exclusive",
            "discount": 30,
            "subject_template": "Exclusive VIP offer: {discount}% off",
            "color": "#C41E3A",
        },
        "restock_alert": {
            "name": "Restocking Alert",
            "discount": 10,
            "subject_template": "Your favorites are back in stock",
            "color": "#F57C00",
        },
    }

    @staticmethod
    def _resolve_subject(template_type: str, subject: str, discount_pct: int) -> str:
        if subject.strip():
            return subject.strip()
        template = PromotionalCampaignService.CAMPAIGN_TEMPLATES.get(template_type, {})
        subject_template = template.get("subject_template", "Special offer from PureLeven")
        return subject_template.format(discount=discount_pct or template.get("discount", 10), items=3)

    @staticmethod
    def _build_default_html(template_type: str, campaign_name: str, subject: str, discount_pct: int, coupon_code: str) -> str:
        template = PromotionalCampaignService.CAMPAIGN_TEMPLATES.get(template_type, {})
        accent = template.get("color", "#2E7D32")
        discount_text = f"{discount_pct}% OFF" if discount_pct else "special offer"
        coupon_html = ""
        if coupon_code:
            coupon_html = (
                "<p style='font-size:16px;margin:18px 0 0;'>"
                "Use code <strong style='letter-spacing:1px'>"
                f"{coupon_code}"
                "</strong> at checkout.</p>"
            )
        return (
            "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:24px;'>"
            f"<h1 style='margin:0 0 8px;color:{accent};font-size:28px;'>{campaign_name}</h1>"
            f"<p style='margin:0 0 16px;color:#374151;font-size:16px;'>{subject}</p>"
            f"<div style='background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:18px;'>"
            f"<p style='margin:0;font-size:22px;font-weight:700;color:{accent};'>{discount_text}</p>"
            "<p style='margin:12px 0 0;color:#4b5563;font-size:15px;'>"
            "Curated organic essentials from PureLeven for your kitchen and wellness routine."
            "</p>"
            f"{coupon_html}"
            "</div>"
            "<p style='margin:18px 0 0;color:#4b5563;font-size:14px;'>"
            "Shop now and enjoy premium, authentic ingredients with trusted quality."
            "</p>"
            "</div>"
        )

    @staticmethod
    def create_campaign(
        name: str,
        template_type: str,
        subject: str,
        html_body: str,
        discount_pct: int = 0,
        coupon_code: str = "",
        segment: str = "all",
        scheduled_at: str | None = None,
        send_interval_seconds: float | None = None,
    ) -> dict[str, Any]:
        """Create a campaign in draft or scheduled state."""
        if not name.strip():
            raise ValueError("Campaign name is required")

        campaign_id = f"promo_{secrets.token_hex(8)}"
        created_at = _now_iso()
        effective_interval = max(0.2, float(send_interval_seconds or settings.promo_send_interval_seconds))

        resolved_subject = PromotionalCampaignService._resolve_subject(template_type, subject, discount_pct)
        resolved_html = html_body.strip() if html_body and html_body.strip() else PromotionalCampaignService._build_default_html(
            template_type=template_type,
            campaign_name=name.strip(),
            subject=resolved_subject,
            discount_pct=discount_pct,
            coupon_code=coupon_code,
        )

        scheduled_dt = _parse_iso_or_none(scheduled_at)
        status = "scheduled" if scheduled_dt else "draft"

        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO promotional_campaigns
                (campaign_id, name, template_type, subject, html_body,
                 discount_pct, coupon_code, segment, status, queue_status,
                 send_interval_seconds, scheduled_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    campaign_id,
                    name.strip(),
                    template_type,
                    resolved_subject,
                    resolved_html,
                    discount_pct,
                    coupon_code,
                    segment,
                    status,
                    status,
                    effective_interval,
                    scheduled_dt.isoformat() if scheduled_dt else None,
                    created_at,
                    created_at,
                ),
            )
            conn.commit()

        return {
            "campaign_id": campaign_id,
            "name": name.strip(),
            "status": status,
            "queue_status": status,
            "send_interval_seconds": effective_interval,
            "created_at": created_at,
        }

    @staticmethod
    def get_campaign_recipients(campaign_id: str) -> list[dict[str, Any]]:
        """Get recipients by configured segment."""
        with get_db_connection() as conn:
            campaign = conn.execute(
                "SELECT segment FROM promotional_campaigns WHERE campaign_id = ?",
                (campaign_id,),
            ).fetchone()

            if not campaign:
                return []

            segment = campaign["segment"]
            if segment == "all":
                query = "SELECT email, first_name, last_name FROM promotional_customers WHERE status = 'active'"
                params: tuple[Any, ...] = ()
            elif segment == "purchased":
                query = "SELECT email, first_name, last_name FROM promotional_customers WHERE segment = 'purchased' AND status = 'active'"
                params = ()
            elif segment == "high_value":
                query = "SELECT email, first_name, last_name FROM promotional_customers WHERE tags LIKE '%high_value%' AND status = 'active'"
                params = ()
            elif segment == "new":
                query = "SELECT email, first_name, last_name FROM promotional_customers WHERE segment = 'new' AND status = 'active'"
                params = ()
            else:
                query = "SELECT email, first_name, last_name FROM promotional_customers WHERE status = 'active'"
                params = ()

            recipients = [dict(row) for row in conn.execute(query, params).fetchall()]

        return recipients

    @staticmethod
    def enqueue_campaign(
        campaign_id: str,
        send_interval_seconds: float | None = None,
        start_at: str | None = None,
    ) -> dict[str, Any]:
        """Queue all recipients with optional per-email interval and start time."""
        now = datetime.now(timezone.utc)
        requested_start = _parse_iso_or_none(start_at) or now

        with get_db_connection() as conn:
            campaign = conn.execute(
                "SELECT * FROM promotional_campaigns WHERE campaign_id = ?",
                (campaign_id,),
            ).fetchone()
            if not campaign:
                return {"error": "Campaign not found"}

            campaign = dict(campaign)
            recipients = PromotionalCampaignService.get_campaign_recipients(campaign_id)
            effective_interval = max(
                0.2,
                float(
                    send_interval_seconds
                    or campaign.get("send_interval_seconds")
                    or settings.promo_send_interval_seconds
                ),
            )

            conn.execute(
                "DELETE FROM campaign_send_queue WHERE campaign_id = ? AND status IN ('queued', 'sending')",
                (campaign_id,),
            )

            for index, recipient in enumerate(recipients):
                email = (recipient.get("email") or "").strip()
                if not email:
                    continue
                due = requested_start + timedelta(seconds=index * effective_interval)
                queue_id = f"q_{secrets.token_hex(8)}"
                now_iso = _now_iso()
                conn.execute(
                    """
                    INSERT OR REPLACE INTO campaign_send_queue
                    (queue_id, campaign_id, email, first_name, last_name, status,
                     scheduled_for, attempt_count, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 'queued', ?, 0, ?, ?)
                    """,
                    (
                        queue_id,
                        campaign_id,
                        email,
                        recipient.get("first_name"),
                        recipient.get("last_name"),
                        due.isoformat(),
                        now_iso,
                        now_iso,
                    ),
                )

            queued_count = conn.execute(
                "SELECT COUNT(*) AS cnt FROM campaign_send_queue WHERE campaign_id = ? AND status IN ('queued', 'sending')",
                (campaign_id,),
            ).fetchone()["cnt"]

            queue_status = "scheduled" if requested_start > now else "queued"
            status = "scheduled" if requested_start > now else "queued"
            conn.execute(
                """
                UPDATE promotional_campaigns
                SET status = ?, queue_status = ?, queued_count = ?, send_interval_seconds = ?,
                    scheduled_at = ?, started_at = CASE WHEN ? = 'queued' THEN ? ELSE started_at END,
                    updated_at = ?
                WHERE campaign_id = ?
                """,
                (
                    status,
                    queue_status,
                    queued_count,
                    effective_interval,
                    requested_start.isoformat(),
                    queue_status,
                    _now_iso(),
                    _now_iso(),
                    campaign_id,
                ),
            )
            conn.commit()

        return {
            "campaign_id": campaign_id,
            "status": status,
            "queue_status": queue_status,
            "queued": queued_count,
            "send_interval_seconds": effective_interval,
            "scheduled_at": requested_start.isoformat(),
        }

    @staticmethod
    def enqueue_due_campaigns() -> dict[str, Any]:
        """Move due scheduled campaigns into queued dispatch mode."""
        now = datetime.now(timezone.utc).isoformat()
        queued_campaigns: list[str] = []

        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT campaign_id, scheduled_at, send_interval_seconds
                FROM promotional_campaigns
                WHERE status = 'scheduled' AND scheduled_at IS NOT NULL AND scheduled_at <= ?
                ORDER BY scheduled_at ASC
                """,
                (now,),
            ).fetchall()

        for row in rows:
            result = PromotionalCampaignService.enqueue_campaign(
                campaign_id=row["campaign_id"],
                send_interval_seconds=row["send_interval_seconds"],
                start_at=row["scheduled_at"],
            )
            if "error" not in result:
                queued_campaigns.append(row["campaign_id"])

        return {"queued_campaigns": queued_campaigns, "count": len(queued_campaigns)}

    @staticmethod
    def _append_tracking_html(campaign_id: str, send_id: str, email: str, html_body: str) -> str:
        base_url = settings.public_base_url.rstrip("/")
        unsubscribe_link = f"https://pureleven.com/unsubscribe-promo?email={email}&campaign={campaign_id}"
        return (
            html_body
            + f"<img src='{base_url}/api/promo/track/open?send_id={send_id}&campaign_id={campaign_id}&email={email}' "
            "width='1' height='1' alt='' style='display:none;'/>"
            + "<p style='font-size:12px;color:#999;text-align:center;margin-top:40px;'>"
            + f"<a href='{unsubscribe_link}' style='color:#999;text-decoration:none;'>Unsubscribe from promotions</a>"
            + "</p>"
        )

    @staticmethod
    def process_queue_batch() -> dict[str, Any]:
        """Process a due queue batch. Safe to call frequently via scheduler."""
        now_iso = _now_iso()
        processed = 0
        sent = 0
        failed = 0
        skipped = 0
        touched_campaign_ids: set[str] = set()

        with get_db_connection() as conn:
            queue_rows = conn.execute(
                """
                SELECT q.queue_id, q.campaign_id, q.email, q.attempt_count,
                       c.subject, c.html_body
                FROM campaign_send_queue q
                JOIN promotional_campaigns c ON c.campaign_id = q.campaign_id
                WHERE q.status = 'queued' AND q.scheduled_for <= ?
                ORDER BY q.scheduled_for ASC
                LIMIT ?
                """,
                (now_iso, settings.promo_queue_batch_size),
            ).fetchall()

            for row in queue_rows:
                campaign_id = row["campaign_id"]
                queue_id = row["queue_id"]
                email = row["email"]
                touched_campaign_ids.add(campaign_id)

                # ── Suppression check ──────────────────────────────────────────
                suppressed = conn.execute(
                    "SELECT 1 FROM email_suppression WHERE email = ? LIMIT 1",
                    (email.lower(),),
                ).fetchone()
                if suppressed:
                    conn.execute(
                        "UPDATE campaign_send_queue SET status = 'suppressed', updated_at = ? WHERE queue_id = ?",
                        (_now_iso(), queue_id),
                    )
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO promo_send_logs
                        (log_id, campaign_id, queue_id, email, status, error_raw, error_type, attempt, logged_at)
                        VALUES (?,?,?,?,'suppressed','suppression_list','suppressed',1,?)
                        """,
                        (secrets.token_hex(10), campaign_id, queue_id, email, _now_iso()),
                    )
                    conn.commit()
                    skipped += 1
                    continue

                processed += 1
                conn.execute(
                    """
                    UPDATE campaign_send_queue
                    SET status = 'sending', attempt_count = attempt_count + 1, updated_at = ?
                    WHERE queue_id = ?
                    """,
                    (_now_iso(), queue_id),
                )
                conn.commit()

                send_id = f"promo_send_{secrets.token_hex(8)}"
                html_body = PromotionalCampaignService._append_tracking_html(
                    campaign_id=campaign_id,
                    send_id=send_id,
                    email=email,
                    html_body=row["html_body"] or "",
                )

                result = send_raw_email(
                    to_email=email,
                    subject=row["subject"] or "PureLeven Offer",
                    html_body=html_body,
                    text_body="Please view the HTML email version.",
                    retries=1,
                    campaign_id=campaign_id,
                )

                if result.success:
                    sent += 1
                    conn.execute(
                        """
                        INSERT INTO campaign_sends
                        (send_id, campaign_id, email, queue_id, status, sent_at, created_at)
                        VALUES (?, ?, ?, ?, 'sent', ?, ?)
                        """,
                        (send_id, campaign_id, email, queue_id, _now_iso(), _now_iso()),
                    )
                    conn.execute(
                        """
                        UPDATE campaign_send_queue
                        SET status = 'sent', sent_at = ?, last_error = NULL, updated_at = ?
                        WHERE queue_id = ?
                        """,
                        (_now_iso(), _now_iso(), queue_id),
                    )
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO promo_send_logs
                        (log_id, campaign_id, queue_id, send_id, email, status, attempt, logged_at)
                        VALUES (?,?,?,?,?,'sent',?,?)
                        """,
                        (secrets.token_hex(10), campaign_id, queue_id, send_id, email, result.attempt, _now_iso()),
                    )
                    conn.commit()
                    continue

                failed += 1
                err = result.error or "send_failed"
                error_type = classify_smtp_error(err)
                attempts = int(row["attempt_count"] or 0) + 1

                # Auto-suppress hard bounces
                if error_type == "hard":
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO email_suppression
                        (id, email, reason, bounce_type, source, campaign_id, raw_error, created_at)
                        VALUES (?,?,?,?,?,?,?,?)
                        """,
                        (secrets.token_hex(10), email.lower(), "bounce", "hard", "auto", campaign_id, err, _now_iso()),
                    )

                if error_type != "hard" and attempts < settings.promo_retry_attempts:
                    retry_due = datetime.now(timezone.utc) + timedelta(
                        seconds=settings.promo_retry_backoff_seconds * attempts
                    )
                    conn.execute(
                        """
                        UPDATE campaign_send_queue
                        SET status = 'queued', scheduled_for = ?, last_error = ?, updated_at = ?
                        WHERE queue_id = ?
                        """,
                        (retry_due.isoformat(), err, _now_iso(), queue_id),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE campaign_send_queue
                        SET status = 'failed', last_error = ?, updated_at = ?
                        WHERE queue_id = ?
                        """,
                        (err, _now_iso(), queue_id),
                    )
                    conn.execute(
                        """
                        INSERT INTO campaign_sends
                        (send_id, campaign_id, email, queue_id, status, sent_at, created_at, last_error)
                        VALUES (?, ?, ?, ?, 'failed', ?, ?, ?)
                        """,
                        (send_id, campaign_id, email, queue_id, _now_iso(), _now_iso(), err),
                    )

                conn.execute(
                    """
                    INSERT OR IGNORE INTO promo_send_logs
                    (log_id, campaign_id, queue_id, send_id, email, status, error_raw, error_type, attempt, logged_at)
                    VALUES (?,?,?,?,?,'failed',?,?,?,?)
                    """,
                    (secrets.token_hex(10), campaign_id, queue_id, send_id, email, err, error_type, attempts, _now_iso()),
                )
                conn.commit()

        if touched_campaign_ids:
            PromotionalCampaignService.refresh_campaign_rollups(sorted(touched_campaign_ids))

        return {
            "processed": processed,
            "sent": sent,
            "failed": failed,
            "skipped_suppressed": skipped,
            "campaigns_touched": len(touched_campaign_ids),
        }

    @staticmethod
    def refresh_campaign_rollups(campaign_ids: list[str]) -> None:
        """Sync campaign status counters from queue state."""
        if not campaign_ids:
            return

        with get_db_connection() as conn:
            for campaign_id in campaign_ids:
                stats = conn.execute(
                    """
                    SELECT
                      SUM(CASE WHEN status = 'queued' THEN 1 ELSE 0 END) AS queued,
                      SUM(CASE WHEN status = 'sending' THEN 1 ELSE 0 END) AS sending,
                      SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) AS sent,
                      SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed
                    FROM campaign_send_queue
                    WHERE campaign_id = ?
                    """,
                    (campaign_id,),
                ).fetchone()
                queued = int(stats["queued"] or 0)
                sending = int(stats["sending"] or 0)
                sent = int(stats["sent"] or 0)
                failed = int(stats["failed"] or 0)

                if queued + sending > 0:
                    status = "sending"
                    queue_status = "sending"
                    completed_at = None
                elif sent + failed > 0:
                    status = "sent"
                    queue_status = "completed"
                    completed_at = _now_iso()
                else:
                    status = "draft"
                    queue_status = "draft"
                    completed_at = None

                conn.execute(
                    """
                    UPDATE promotional_campaigns
                    SET status = ?, queue_status = ?, queued_count = ?,
                        sent_count = ?, failed_count = ?, completed_at = ?, updated_at = ?
                    WHERE campaign_id = ?
                    """,
                    (
                        status,
                        queue_status,
                        queued + sending,
                        sent,
                        failed,
                        completed_at,
                        _now_iso(),
                        campaign_id,
                    ),
                )
            conn.commit()

    @staticmethod
    def send_campaign(campaign_id: str) -> dict[str, Any]:
        """Compatibility wrapper: queue campaign immediately."""
        result = PromotionalCampaignService.enqueue_campaign(campaign_id=campaign_id)
        if "error" in result:
            return result
        result["mode"] = "queued"
        return result

    @staticmethod
    def get_campaign_progress(campaign_id: str) -> dict[str, Any]:
        """Return queue progress for live campaign viewer polling."""
        with get_db_connection() as conn:
            campaign = conn.execute(
                """
                SELECT campaign_id, name, status, queue_status, send_interval_seconds,
                       queued_count, sent_count, failed_count, scheduled_at, started_at, completed_at
                FROM promotional_campaigns
                WHERE campaign_id = ?
                """,
                (campaign_id,),
            ).fetchone()

            if not campaign:
                return {}

            queue_stats = conn.execute(
                """
                SELECT
                  SUM(CASE WHEN status = 'queued' THEN 1 ELSE 0 END) AS queued,
                  SUM(CASE WHEN status = 'sending' THEN 1 ELSE 0 END) AS sending,
                  SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) AS sent,
                  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
                  MAX(scheduled_for) AS max_due
                FROM campaign_send_queue
                WHERE campaign_id = ?
                """,
                (campaign_id,),
            ).fetchone()

        queued = int(queue_stats["queued"] or 0)
        sending = int(queue_stats["sending"] or 0)
        sent = int(queue_stats["sent"] or 0)
        failed = int(queue_stats["failed"] or 0)
        total = queued + sending + sent + failed
        remaining = queued + sending
        interval = float(campaign["send_interval_seconds"] or settings.promo_send_interval_seconds)

        return {
            "campaign_id": campaign["campaign_id"],
            "name": campaign["name"],
            "status": campaign["status"],
            "queue_status": campaign["queue_status"],
            "total": total,
            "queued": queued,
            "sending": sending,
            "sent": sent,
            "failed": failed,
            "remaining": remaining,
            "eta_seconds": round(remaining * interval, 1),
            "scheduled_at": campaign["scheduled_at"],
            "started_at": campaign["started_at"],
            "completed_at": campaign["completed_at"],
        }

    @staticmethod
    def get_campaign_stats(campaign_id: str) -> dict[str, Any]:
        """Get performance + queue stats for a campaign."""
        with get_db_connection() as conn:
            campaign = conn.execute(
                """
                SELECT
                    campaign_id, name, template_type, status, queue_status,
                    sent_count, failed_count, queued_count,
                    (SELECT COUNT(*) FROM campaign_sends WHERE campaign_id = ?) as total_sent,
                    (SELECT COUNT(*) FROM campaign_sends WHERE campaign_id = ? AND opened_at IS NOT NULL) as total_opened,
                    (SELECT COUNT(*) FROM campaign_sends WHERE campaign_id = ? AND clicked_at IS NOT NULL) as total_clicked,
                    created_at, sent_at, started_at, completed_at
                FROM promotional_campaigns
                WHERE campaign_id = ?
                """,
                (campaign_id, campaign_id, campaign_id, campaign_id),
            ).fetchone()

            if not campaign:
                return {}

            campaign = dict(campaign)
            total = campaign.get("total_sent", 0)

            return {
                "campaign_id": campaign_id,
                "name": campaign.get("name"),
                "status": campaign.get("status"),
                "queue_status": campaign.get("queue_status"),
                "queued_count": campaign.get("queued_count", 0),
                "total_sent": campaign.get("total_sent", 0),
                "total_opened": campaign.get("total_opened", 0),
                "total_clicked": campaign.get("total_clicked", 0),
                "open_rate_pct": round((campaign.get("total_opened", 0) / max(1, total)) * 100, 1),
                "click_rate_pct": round((campaign.get("total_clicked", 0) / max(1, total)) * 100, 1),
                "created_at": campaign.get("created_at"),
                "sent_at": campaign.get("sent_at"),
                "started_at": campaign.get("started_at"),
                "completed_at": campaign.get("completed_at"),
            }

    @staticmethod
    def track_open(send_id: str, campaign_id: str, email: str) -> bool:
        """Track email open."""
        try:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    UPDATE campaign_sends
                    SET opened_at = ?
                    WHERE send_id = ? AND campaign_id = ? AND email = ?
                    """,
                    (_now_iso(), send_id, campaign_id, email),
                )
                conn.commit()
            return True
        except Exception as exc:
            logger.error("Failed to track open: %s", exc)
            return False

    @staticmethod
    def track_click(send_id: str, campaign_id: str, email: str, link: str) -> bool:
        """Track email click."""
        try:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    UPDATE campaign_sends
                    SET clicked_at = ?
                    WHERE send_id = ? AND campaign_id = ? AND email = ?
                    """,
                    (_now_iso(), send_id, campaign_id, email),
                )
                conn.commit()
            return True
        except Exception as exc:
            logger.error("Failed to track click for %s (%s): %s", email, link, exc)
            return False

    @staticmethod
    def list_campaigns(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        """List campaigns with queue and engagement rollups."""
        with get_db_connection() as conn:
            campaigns = conn.execute(
                """
                SELECT c.campaign_id, c.name, c.template_type, c.subject,
                       c.status, c.queue_status, c.segment,
                       c.queued_count, c.sent_count, c.failed_count,
                       c.send_interval_seconds, c.created_at, c.sent_at, c.scheduled_at,
                       (SELECT COUNT(*) FROM campaign_sends s WHERE s.campaign_id = c.campaign_id AND s.opened_at IS NOT NULL) AS open_count,
                       (SELECT COUNT(*) FROM campaign_sends s WHERE s.campaign_id = c.campaign_id AND s.clicked_at IS NOT NULL) AS click_count
                FROM promotional_campaigns c
                ORDER BY c.created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()

        return [dict(row) for row in campaigns]

    @staticmethod
    def segment_preview_count(segment: str) -> int:
        """Return the number of active promotional customers matching a segment."""
        with get_db_connection() as conn:
            if segment in ("purchased", "high_value", "new"):
                row = conn.execute(
                    "SELECT COUNT(*) FROM promotional_customers WHERE status = 'active' AND segment = ?",
                    (segment,),
                ).fetchone()
            else:  # 'all'
                row = conn.execute(
                    "SELECT COUNT(*) FROM promotional_customers WHERE status = 'active'"
                ).fetchone()
        return int(row[0]) if row else 0
