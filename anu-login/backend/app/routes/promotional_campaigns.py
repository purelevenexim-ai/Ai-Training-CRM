"""
Promotional Campaign Routes

API endpoints for promotional campaign management and dashboard.
All endpoints require admin_secret authentication.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from app.config import settings
from app.services.shopify_customer_importer import ShopifyCustomerImporter
from app.services.promotional_campaign_service import PromotionalCampaignService
from app.storage import get_db_connection

logger = logging.getLogger(__name__)
router = APIRouter()


ENGAGEMENT_LABEL_CASE = """
CASE
    WHEN COALESCE(ss.total_clicked, 0) >= 2 OR COALESCE(ss.total_opened, 0) >= 3 THEN 'hot'
    WHEN COALESCE(ss.total_clicked, 0) >= 1 OR COALESCE(ss.total_opened, 0) >= 1 THEN 'warm'
    WHEN COALESCE(ss.total_sent, 0) >= 1 THEN 'cold'
    ELSE 'inactive'
END
"""


# ── Auth dependency ────────────────────────────────────────────────────────────
def _require_admin(admin_secret: str = Query(..., alias="admin_secret")) -> None:
    if admin_secret != settings.admin_secret:
        raise HTTPException(status_code=403, detail="Invalid admin_secret")


# ── Request models ─────────────────────────────────────────────────────────────

class ShopifyImportRequest(BaseModel):
    """Request to import customers from Shopify"""
    status: str = "any"  # any, enabled, disabled


class CampaignCreateRequest(BaseModel):
    """Request to create a promotional campaign"""
    name: str
    template_type: str  # flash_sale, seasonal, bundle_offer, vip_exclusive, restock_alert
    subject: str = ""
    html_body: str = ""
    discount_pct: int = 0
    coupon_code: str = ""
    segment: str = "all"  # all, purchased, high_value, new
    scheduled_at: str | None = None
    send_interval_seconds: float = 1.0


class CampaignSendRequest(BaseModel):
    """Request to send a campaign"""
    campaign_id: str
    send_interval_seconds: float | None = None
    start_at: str | None = None


def _parse_json_safely(raw: str | None) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


# ── Customer Import Endpoints ──────────────────────────────────────────────────

@router.post("/promo/import/shopify")
async def import_shopify_customers(
    req: ShopifyImportRequest,
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Import all customers from Shopify store."""
    try:
        importer = ShopifyCustomerImporter()
        customers = importer.get_all_customers(status=req.status)

        if not customers:
            return JSONResponse(
                {
                    "ok": False,
                    "error": "No customers found in Shopify",
                },
                status_code=404,
            )

        result = importer.import_customers_to_db(customers)

        return JSONResponse(
            {
                "ok": True,
                "imported": result["imported"],
                "updated": result["updated"],
                "skipped": result["skipped"],
                "total": result["total"],
            }
        )

    except Exception as e:
        logger.error(f"Shopify import error: {e}")
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=500,
        )


@router.get("/promo/customers/stats")
async def get_customer_stats(
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Get statistics on imported customers."""
    try:
        stats = ShopifyCustomerImporter.get_import_stats()
        return JSONResponse({"ok": True, **stats})
    except Exception as e:
        logger.error(f"Customer stats error: {e}")
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=500,
        )


@router.get("/promo/customers/list")
async def list_customers(
    segment: str = Query(default="all"),
    status: str = Query(default="active"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """List promotional customers with optional filtering."""
    try:
        with get_db_connection() as conn:
            query = "SELECT * FROM promotional_customers WHERE 1=1"
            params = []

            if segment != "all":
                query += " AND segment = ?"
                params.append(segment)

            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            customers = [dict(row) for row in conn.execute(query, params).fetchall()]

        return JSONResponse(
            {
                "ok": True,
                "customers": customers,
                "count": len(customers),
                "total": len(customers),
            }
        )

    except Exception as e:
        logger.error(f"List customers error: {e}")
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=500,
        )


# ── Campaign Management Endpoints ──────────────────────────────────────────────

@router.post("/promo/campaigns/create")
async def create_campaign(
    req: CampaignCreateRequest,
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Create a new promotional campaign."""
    try:
        result = PromotionalCampaignService.create_campaign(
            name=req.name,
            template_type=req.template_type,
            subject=req.subject,
            html_body=req.html_body,
            discount_pct=req.discount_pct,
            coupon_code=req.coupon_code,
            segment=req.segment,
            scheduled_at=req.scheduled_at,
            send_interval_seconds=req.send_interval_seconds,
        )

        return JSONResponse({"ok": True, **result})

    except Exception as e:
        logger.error(f"Create campaign error: {e}")
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=500,
        )


@router.post("/promo/campaigns/send")
async def send_campaign(
    req: CampaignSendRequest,
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Queue a campaign for sending with optional custom interval/start time."""
    try:
        result = PromotionalCampaignService.enqueue_campaign(
            campaign_id=req.campaign_id,
            send_interval_seconds=req.send_interval_seconds,
            start_at=req.start_at,
        )

        if "error" in result:
            return JSONResponse(
                {"ok": False, **result},
                status_code=404,
            )

        return JSONResponse({"ok": True, "mode": "queued", **result})

    except Exception as e:
        logger.error(f"Send campaign error: {e}")
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=500,
        )


@router.get("/promo/campaigns/{campaign_id}/progress")
async def get_campaign_progress(
    campaign_id: str,
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Get live queue progress for a campaign."""
    try:
        progress = PromotionalCampaignService.get_campaign_progress(campaign_id)
        if not progress:
            return JSONResponse({"ok": False, "error": "Campaign not found"}, status_code=404)
        return JSONResponse({"ok": True, **progress})
    except Exception as e:
        logger.error(f"Progress fetch error: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/promo/campaigns/list")
async def list_campaigns(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """List all promotional campaigns."""
    try:
        campaigns = PromotionalCampaignService.list_campaigns(limit=limit, offset=offset)
        return JSONResponse(
            {
                "ok": True,
                "campaigns": campaigns,
                "count": len(campaigns),
            }
        )

    except Exception as e:
        logger.error(f"List campaigns error: {e}")
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=500,
        )


@router.get("/promo/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Get campaign details and performance stats."""
    try:
        stats = PromotionalCampaignService.get_campaign_stats(campaign_id)

        if not stats:
            return JSONResponse(
                {"ok": False, "error": "Campaign not found"},
                status_code=404,
            )

        return JSONResponse({"ok": True, **stats})

    except Exception as e:
        logger.error(f"Get campaign error: {e}")
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=500,
        )


# ── Analytics Endpoints ────────────────────────────────────────────────────────

@router.get("/promo/campaigns/{campaign_id}/analytics")
async def get_campaign_analytics(
    campaign_id: str,
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Get detailed analytics for a campaign."""
    try:
        with get_db_connection() as conn:
            # Campaign details
            campaign = conn.execute(
                "SELECT * FROM promotional_campaigns WHERE campaign_id = ?",
                (campaign_id,),
            ).fetchone()

            if not campaign:
                return JSONResponse(
                    {"ok": False, "error": "Campaign not found"},
                    status_code=404,
                )

            campaign = dict(campaign)

            # Send performance
            sends = conn.execute(
                """
                SELECT
                    COUNT(*) as total_sent,
                    SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) as total_opened,
                    SUM(CASE WHEN clicked_at IS NOT NULL THEN 1 ELSE 0 END) as total_clicked,
                    SUM(CASE WHEN converted_at IS NOT NULL THEN 1 ELSE 0 END) as total_converted
                FROM campaign_sends
                WHERE campaign_id = ?
                """,
                (campaign_id,),
            ).fetchone()

            sends = dict(sends) if sends else {}
            total = sends.get("total_sent", 1)

            # Hourly open distribution
            hourly = []
            for row in conn.execute(
                """
                SELECT
                    strftime('%H', opened_at) as hour,
                    COUNT(*) as count
                FROM campaign_sends
                WHERE campaign_id = ? AND opened_at IS NOT NULL
                GROUP BY hour
                ORDER BY hour
                """,
                (campaign_id,),
            ).fetchall():
                hourly.append({"hour": row["hour"], "opens": row["count"]})

            # Click distribution
            clicks = []
            for row in conn.execute(
                """
                SELECT
                    strftime('%H', clicked_at) as hour,
                    COUNT(*) as count
                FROM campaign_sends
                WHERE campaign_id = ? AND clicked_at IS NOT NULL
                GROUP BY hour
                ORDER BY hour
                """,
                (campaign_id,),
            ).fetchall():
                clicks.append({"hour": row["hour"], "clicks": row["count"]})

        return JSONResponse(
            {
                "ok": True,
                "campaign_id": campaign_id,
                "name": campaign.get("name"),
                "status": campaign.get("status"),
                "total_sent": sends.get("total_sent", 0),
                "total_opened": sends.get("total_opened", 0),
                "total_clicked": sends.get("total_clicked", 0),
                "total_converted": sends.get("total_converted", 0),
                "open_rate_pct": round((sends.get("total_opened", 0) / max(1, total)) * 100, 1),
                "click_rate_pct": round((sends.get("total_clicked", 0) / max(1, total)) * 100, 1),
                "conversion_rate_pct": round((sends.get("total_converted", 0) / max(1, total)) * 100, 1),
                "hourly_opens": hourly,
                "hourly_clicks": clicks,
            }
        )

    except Exception as e:
        logger.error(f"Campaign analytics error: {e}")
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=500,
        )


@router.get("/promo/dashboard/journey/customers")
async def journey_customers_dashboard(
    search: str = Query(default=""),
    label: str = Query(default="all"),
    segment: str = Query(default="all"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Journey + purchase list with engagement labels and segment filters."""
    try:
        where = ["pc.status = 'active'"]
        params: list[Any] = []

        if segment != "all":
            where.append("pc.segment = ?")
            params.append(segment)

        if search.strip():
            needle = f"%{search.strip().lower()}%"
            where.append("(LOWER(pc.email) LIKE ? OR LOWER(COALESCE(pc.first_name, '') || ' ' || COALESCE(pc.last_name, '')) LIKE ?)")
            params.extend([needle, needle])

        where_clause = " AND ".join(where)

        base_sql = f"""
            WITH send_stats AS (
                SELECT
                    email,
                    COUNT(*) AS total_sent,
                    SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) AS total_opened,
                    SUM(CASE WHEN clicked_at IS NOT NULL THEN 1 ELSE 0 END) AS total_clicked,
                    MAX(opened_at) AS last_opened_at,
                    MAX(clicked_at) AS last_clicked_at
                FROM campaign_sends
                GROUP BY email
            ),
            purchase_stats AS (
                SELECT
                    LOWER(COALESCE(email_address, email)) AS email_key,
                    COUNT(DISTINCT shopify_order_id) AS purchase_count,
                    CAST(SUM(COALESCE(order_value_paise, 0)) AS REAL) / 100.0 AS total_spent,
                    MAX(COALESCE(last_purchase_at, created_at)) AS last_purchase_at,
                    MAX(shopify_order_id) AS latest_order_id
                FROM journey_customers
                WHERE COALESCE(email_address, email) IS NOT NULL
                GROUP BY LOWER(COALESCE(email_address, email))
            ),
            base AS (
                SELECT
                    pc.id,
                    pc.customer_id,
                    pc.email,
                    pc.first_name,
                    pc.last_name,
                    pc.phone,
                    pc.tags,
                    pc.segment,
                    pc.status,
                    COALESCE(ss.total_sent, 0) AS total_sent,
                    COALESCE(ss.total_opened, 0) AS total_opened,
                    COALESCE(ss.total_clicked, 0) AS total_clicked,
                    ss.last_opened_at,
                    ss.last_clicked_at,
                    COALESCE(ps.purchase_count, 0) AS purchase_count,
                    ROUND(COALESCE(ps.total_spent, 0), 2) AS total_spent,
                    ps.last_purchase_at,
                    ps.latest_order_id,
                    {ENGAGEMENT_LABEL_CASE} AS engagement_label,
                    pc.created_at
                FROM promotional_customers pc
                LEFT JOIN send_stats ss ON ss.email = pc.email
                LEFT JOIN purchase_stats ps ON ps.email_key = LOWER(pc.email)
                WHERE {where_clause}
            )
            SELECT *
            FROM base
        """

        outer_where = []
        outer_params: list[Any] = []
        if label != "all":
            outer_where.append("engagement_label = ?")
            outer_params.append(label)

        final_sql = base_sql
        if outer_where:
            final_sql += " WHERE " + " AND ".join(outer_where)

        final_sql += " ORDER BY total_clicked DESC, total_opened DESC, created_at DESC LIMIT ? OFFSET ?"

        count_sql = f"SELECT COUNT(*) AS cnt FROM ({base_sql}{(' WHERE ' + ' AND '.join(outer_where)) if outer_where else ''})"

        with get_db_connection() as conn:
            customers = [
                {
                    **dict(row),
                    "full_name": " ".join([p for p in [row["first_name"], row["last_name"]] if p]).strip() or None,
                }
                for row in conn.execute(final_sql, [*params, *outer_params, limit, offset]).fetchall()
            ]
            total = conn.execute(count_sql, [*params, *outer_params]).fetchone()["cnt"]

        return JSONResponse({
            "ok": True,
            "customers": customers,
            "count": len(customers),
            "total": total,
        })

    except Exception as e:
        logger.error(f"Journey customers dashboard error: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/promo/dashboard/engagement/summary")
async def engagement_summary_dashboard(
    segment: str = Query(default="all"),
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Aggregate engagement labels for dashboard cards."""
    try:
        where = ["pc.status = 'active'"]
        params: list[Any] = []
        if segment != "all":
            where.append("pc.segment = ?")
            params.append(segment)

        with get_db_connection() as conn:
            rows = conn.execute(
                f"""
                WITH send_stats AS (
                    SELECT
                        email,
                        COUNT(*) AS total_sent,
                        SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) AS total_opened,
                        SUM(CASE WHEN clicked_at IS NOT NULL THEN 1 ELSE 0 END) AS total_clicked
                    FROM campaign_sends
                    GROUP BY email
                )
                SELECT
                    {ENGAGEMENT_LABEL_CASE} AS engagement_label,
                    COUNT(*) AS cnt
                FROM promotional_customers pc
                LEFT JOIN send_stats ss ON ss.email = pc.email
                WHERE {' AND '.join(where)}
                GROUP BY engagement_label
                """,
                params,
            ).fetchall()

            totals = {"hot": 0, "warm": 0, "cold": 0, "inactive": 0}
            for row in rows:
                totals[row["engagement_label"]] = row["cnt"]

            total_customers = sum(totals.values())

        return JSONResponse({
            "ok": True,
            "total_customers": total_customers,
            **totals,
        })
    except Exception as e:
        logger.error(f"Engagement summary error: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/promo/dashboard/journey/{email}")
async def journey_customer_detail(
    email: str,
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Customer drill-down: profile + purchase visibility + journey timeline."""
    try:
        normalized_email = email.strip().lower()
        with get_db_connection() as conn:
            customer = conn.execute(
                """
                SELECT id, customer_id, email, first_name, last_name, phone, tags, segment, status, created_at, updated_at
                FROM promotional_customers
                WHERE LOWER(email) = ?
                LIMIT 1
                """,
                (normalized_email,),
            ).fetchone()

            if not customer:
                return JSONResponse({"ok": False, "error": "Customer not found"}, status_code=404)

            customer_dict = dict(customer)

            purchase = conn.execute(
                """
                SELECT
                    COUNT(DISTINCT shopify_order_id) AS purchase_count,
                    CAST(SUM(COALESCE(order_value_paise, 0)) AS REAL) / 100.0 AS total_spent,
                    MAX(COALESCE(last_purchase_at, created_at)) AS last_purchase_at,
                    MAX(shopify_order_id) AS latest_order_id,
                    GROUP_CONCAT(DISTINCT shopify_order_id) AS order_ids
                FROM journey_customers
                WHERE LOWER(COALESCE(email_address, email)) = ?
                """,
                (normalized_email,),
            ).fetchone()

            promo_events = [
                {
                    "source": "promo",
                    "event_at": row["sent_at"],
                    "event_type": "promo_email",
                    "campaign_id": row["campaign_id"],
                    "campaign_name": row["campaign_name"],
                    "status": row["status"],
                    "opened_at": row["opened_at"],
                    "clicked_at": row["clicked_at"],
                    "journey_stage": None,
                    "channel": "email",
                }
                for row in conn.execute(
                    """
                    SELECT
                        cs.sent_at,
                        cs.campaign_id,
                        cs.status,
                        cs.opened_at,
                        cs.clicked_at,
                        pc.name AS campaign_name
                    FROM campaign_sends cs
                    LEFT JOIN promotional_campaigns pc ON pc.campaign_id = cs.campaign_id
                    WHERE LOWER(cs.email) = ?
                    ORDER BY cs.sent_at DESC
                    LIMIT 200
                    """,
                    (normalized_email,),
                ).fetchall()
            ]

            journey_events = [
                {
                    "source": "journey",
                    "event_at": row["sent_at"],
                    "event_type": "journey_message",
                    "campaign_id": None,
                    "campaign_name": row["template_name"],
                    "status": row["status"],
                    "opened_at": row["opened_at"],
                    "clicked_at": row["clicked_at"],
                    "journey_stage": row["journey_stage"],
                    "channel": row["channel"] or "whatsapp",
                    "variables": _parse_json_safely(row["variables_json"]),
                }
                for row in conn.execute(
                    """
                    SELECT
                        jm.sent_at,
                        jm.template_name,
                        jm.journey_stage,
                        COALESCE(jm.email_status, jm.delivery_status) AS status,
                        jm.opened_at,
                        jm.clicked_at,
                        jm.channel,
                        jm.variables_json
                    FROM journey_messages jm
                    JOIN journey_customers jc ON jc.id = jm.customer_id
                    WHERE LOWER(COALESCE(jc.email_address, jc.email)) = ?
                    ORDER BY jm.sent_at DESC
                    LIMIT 200
                    """,
                    (normalized_email,),
                ).fetchall()
            ]

        timeline = sorted(
            [*promo_events, *journey_events],
            key=lambda item: item.get("event_at") or "",
            reverse=True,
        )

        return JSONResponse(
            {
                "ok": True,
                "customer": {
                    **customer_dict,
                    "full_name": " ".join(
                        [x for x in [customer_dict.get("first_name"), customer_dict.get("last_name")] if x]
                    ).strip() or None,
                },
                "purchase": {
                    "purchase_count": int((purchase["purchase_count"] or 0) if purchase else 0),
                    "total_spent": round(float((purchase["total_spent"] or 0) if purchase else 0), 2),
                    "last_purchase_at": purchase["last_purchase_at"] if purchase else None,
                    "latest_order_id": purchase["latest_order_id"] if purchase else None,
                    "order_ids": (purchase["order_ids"] or "").split(",") if purchase and purchase["order_ids"] else [],
                },
                "timeline": timeline,
                "timeline_count": len(timeline),
            }
        )

    except Exception as e:
        logger.error(f"Journey detail error: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# ── Tracking Endpoints (pixel tracking) ────────────────────────────────────────

@router.get("/promo/track/open")
async def track_open(
    send_id: str = Query(...),
    campaign_id: str = Query(...),
    email: str = Query(...),
) -> FileResponse:
    """Track email open via pixel."""
    try:
        PromotionalCampaignService.track_open(send_id, campaign_id, email)
    except Exception as e:
        logger.error(f"Track open error: {e}")

    # Return 1x1 transparent GIF
    return FileResponse(
        "/dev/null",  # This will cause a 200 response with empty body
        media_type="image/gif",
    )


@router.get("/promo/track/click")
async def track_click(
    send_id: str = Query(...),
    campaign_id: str = Query(...),
    email: str = Query(...),
    link: str = Query(...),
) -> JSONResponse:
    """Track email click."""
    try:
        PromotionalCampaignService.track_click(send_id, campaign_id, email, link)
    except Exception as e:
        logger.error(f"Track click error: {e}")

    return JSONResponse({"ok": True})


# ── Dashboard Summary ──────────────────────────────────────────────────────────

@router.get("/promo/dashboard/summary")
async def dashboard_summary(
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Get promotional campaign dashboard summary."""
    try:
        with get_db_connection() as conn:
            # Total customers
            total_customers = conn.execute(
                "SELECT COUNT(*) as cnt FROM promotional_customers WHERE status = 'active'"
            ).fetchone()["cnt"]

            # Total campaigns
            total_campaigns = conn.execute(
                "SELECT COUNT(*) as cnt FROM promotional_campaigns"
            ).fetchone()["cnt"]

            # Sent emails
            total_sent = conn.execute(
                "SELECT COUNT(*) as cnt FROM campaign_sends WHERE status = 'sent'"
            ).fetchone()["cnt"]

            # Overall open rate
            opens = conn.execute(
                "SELECT COUNT(*) as cnt FROM campaign_sends WHERE opened_at IS NOT NULL"
            ).fetchone()["cnt"]

            # Overall click rate
            clicks = conn.execute(
                "SELECT COUNT(*) as cnt FROM campaign_sends WHERE clicked_at IS NOT NULL"
            ).fetchone()["cnt"]

            # Recent campaigns
            recent = []
            for row in conn.execute(
                """
                SELECT campaign_id, name, status, sent_count, created_at
                FROM promotional_campaigns
                ORDER BY created_at DESC
                LIMIT 5
                """
            ).fetchall():
                recent.append(dict(row))

        return JSONResponse(
            {
                "ok": True,
                "total_customers": total_customers,
                "total_campaigns": total_campaigns,
                "total_sent": total_sent,
                "total_opened": opens,
                "total_clicked": clicks,
                "open_rate_pct": round((opens / max(1, total_sent)) * 100, 1),
                "click_rate_pct": round((clicks / max(1, total_sent)) * 100, 1),
                "recent_campaigns": recent,
            }
        )

    except Exception as e:
        logger.error(f"Dashboard summary error: {e}")
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=500,
        )


# ── Logs / Bounces / Issues Endpoints ─────────────────────────────────────────

@router.get("/promo/logs")
async def get_promo_logs(
    campaign_id: str = Query(""),
    status: str = Query(""),
    email_search: str = Query(""),
    date_from: str = Query(""),
    date_to: str = Query(""),
    limit: int = Query(50),
    offset: int = Query(0),
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Paginated send-log with campaign/status/date/email filters."""
    try:
        wheres: list[str] = []
        params: list[Any] = []

        if campaign_id:
            wheres.append("l.campaign_id = ?")
            params.append(campaign_id)
        if status:
            wheres.append("l.status = ?")
            params.append(status)
        if email_search:
            wheres.append("l.email LIKE ?")
            params.append(f"%{email_search}%")
        if date_from:
            wheres.append("l.logged_at >= ?")
            params.append(date_from)
        if date_to:
            wheres.append("l.logged_at <= ?")
            params.append(date_to)

        where_clause = ("WHERE " + " AND ".join(wheres)) if wheres else ""

        with get_db_connection() as conn:
            total_row = conn.execute(
                f"SELECT COUNT(*) FROM promo_send_logs l {where_clause}", params
            ).fetchone()
            total = int(total_row[0]) if total_row else 0

            rows = conn.execute(
                f"""
                SELECT l.log_id, l.campaign_id, c.name AS campaign_name,
                       l.queue_id, l.send_id, l.email, l.status,
                       l.error_raw, l.error_type, l.attempt, l.logged_at
                FROM promo_send_logs l
                LEFT JOIN promotional_campaigns c ON c.campaign_id = l.campaign_id
                {where_clause}
                ORDER BY l.logged_at DESC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset],
            ).fetchall()

        return JSONResponse({
            "ok": True,
            "total": total,
            "logs": [dict(r) for r in rows],
        })

    except Exception as exc:
        logger.error("promo_logs error: %s", exc)
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@router.get("/promo/logs/bounces")
async def get_bounce_summary(
    campaign_id: str = Query(""),
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Bounce/error summary grouped by error_type."""
    try:
        params: list[Any] = []
        where = ""
        if campaign_id:
            where = "WHERE l.campaign_id = ?"
            params.append(campaign_id)

        with get_db_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT l.error_type, COUNT(*) AS count
                FROM promo_send_logs l
                {where}
                WHERE l.status = 'failed'
                GROUP BY l.error_type
                ORDER BY count DESC
                """.replace(
                    "WHERE l.status = 'failed'",
                    ("AND l.status = 'failed'" if where else "WHERE l.status = 'failed'"),
                ),
                params,
            ).fetchall()

            # Suppression count
            supp_params: list[Any] = []
            supp_where = ""
            if campaign_id:
                supp_where = "WHERE campaign_id = ?"
                supp_params.append(campaign_id)
            supp_row = conn.execute(
                f"SELECT COUNT(*) FROM email_suppression {supp_where}", supp_params
            ).fetchone()

            # Total failed
            total_failed = conn.execute(
                f"SELECT COUNT(*) FROM promo_send_logs l {where} {'AND' if where else 'WHERE'} l.status = 'failed'",
                params,
            ).fetchone()

        return JSONResponse({
            "ok": True,
            "total_suppressed": int(supp_row[0]) if supp_row else 0,
            "total_failed": int(total_failed[0]) if total_failed else 0,
            "by_type": [dict(r) for r in rows],
        })

    except Exception as exc:
        logger.error("bounce_summary error: %s", exc)
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


class SuppressionAddRequest(BaseModel):
    email: str
    reason: str = "unsubscribed"  # unsubscribed | bounce | complaint | manual
    campaign_id: str = ""
    note: str = ""


@router.post("/promo/suppression/add")
async def add_suppression(
    req: SuppressionAddRequest,
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Add an email to the suppression list (prevents future sends)."""
    import secrets as _s
    email = req.email.strip().lower()
    if not email or "@" not in email:
        return JSONResponse({"ok": False, "error": "Invalid email"}, status_code=400)
    try:
        from datetime import datetime, timezone
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO email_suppression
                (id, email, reason, source, campaign_id, raw_error, created_at)
                VALUES (COALESCE((SELECT id FROM email_suppression WHERE email=?), ?),
                        ?, ?, 'manual', ?, ?, ?)
                """,
                (email, _s.token_hex(10), email, req.reason,
                 req.campaign_id or None, req.note or None,
                 datetime.now(timezone.utc).isoformat()),
            )
        return JSONResponse({"ok": True, "email": email, "reason": req.reason})
    except Exception as exc:
        logger.error("suppression_add error: %s", exc)
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@router.delete("/promo/suppression/remove")
async def remove_suppression(
    email: str = Query(...),
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Remove an email from the suppression list."""
    email = email.strip().lower()
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM email_suppression WHERE email = ?", (email,))
        return JSONResponse({"ok": True, "email": email})
    except Exception as exc:
        logger.error("suppression_remove error: %s", exc)
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@router.get("/promo/suppression/list")
async def list_suppressions(
    limit: int = Query(100),
    offset: int = Query(0),
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Paginated suppression list."""
    try:
        with get_db_connection() as conn:
            total_row = conn.execute("SELECT COUNT(*) FROM email_suppression").fetchone()
            rows = conn.execute(
                "SELECT * FROM email_suppression ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return JSONResponse({
            "ok": True,
            "total": int(total_row[0]) if total_row else 0,
            "suppressions": [dict(r) for r in rows],
        })
    except Exception as exc:
        logger.error("suppression_list error: %s", exc)
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@router.post("/promo/logs/retry-transient")
async def retry_transient_failures(
    campaign_id: str = Query(""),
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Re-queue transient-failed queue rows for retry (skips hard/soft bounces)."""
    import secrets as _s
    try:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        params: list[Any] = [now, now]
        where_extra = ""
        if campaign_id:
            where_extra = " AND campaign_id = ?"
            params.append(campaign_id)

        with get_db_connection() as conn:
            # Only retry rows whose last_error classifies as transient
            # We re-queue rows in 'failed' status that don't have a hard/soft bounce log entry
            result = conn.execute(
                f"""
                UPDATE campaign_send_queue
                SET status = 'queued', scheduled_for = ?, attempt_count = 0, last_error = NULL, updated_at = ?
                WHERE status = 'failed'
                  AND queue_id NOT IN (
                      SELECT DISTINCT queue_id FROM promo_send_logs
                      WHERE status = 'failed' AND error_type IN ('hard', 'soft')
                  )
                  {where_extra}
                """,
                params,
            )
            requeued = result.rowcount
        return JSONResponse({"ok": True, "requeued": requeued})
    except Exception as exc:
        logger.error("retry_transient error: %s", exc)
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


# ── Segment Preview ────────────────────────────────────────────────────────────

@router.get("/promo/segments/preview")
async def segment_preview(
    segment: str = Query("all"),
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Return count of active customers matching the given segment."""
    try:
        count = PromotionalCampaignService.segment_preview_count(segment)
        return JSONResponse({"ok": True, "segment": segment, "count": count})
    except Exception as exc:
        logger.error("segment_preview error: %s", exc)
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


# ── CSV Export for Journey Segment ────────────────────────────────────────────

@router.get("/promo/dashboard/journey/customers/export")
async def export_journey_customers_csv(
    label: str = Query(""),
    segment: str = Query(""),
    search: str = Query(""),
    _: None = Depends(_require_admin),
) -> Any:
    """Download filtered journey customer list as CSV."""
    import csv
    import io
    from fastapi.responses import StreamingResponse

    try:
        wheres: list[str] = []
        params: list[Any] = []

        if search:
            wheres.append(
                "(LOWER(COALESCE(pc.email,'')) LIKE ? OR LOWER(COALESCE(pc.first_name,'')) LIKE ?)"
            )
            params += [f"%{search.lower()}%", f"%{search.lower()}%"]
        if segment and segment != "all":
            wheres.append("pc.segment = ?")
            params.append(segment)

        where_clause = ("WHERE " + " AND ".join(wheres)) if wheres else ""

        cte_sql = f"""
        WITH send_stats AS (
            SELECT email,
                   COUNT(*) AS total_sent,
                   SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) AS total_opened,
                   SUM(CASE WHEN clicked_at IS NOT NULL THEN 1 ELSE 0 END) AS total_clicked,
                   MAX(sent_at) AS last_sent_at
            FROM campaign_sends
            WHERE status = 'sent'
            GROUP BY email
        )
        SELECT
            COALESCE(pc.email, '') AS email,
            COALESCE(pc.first_name, '') AS first_name,
            COALESCE(pc.last_name, '') AS last_name,
            COALESCE(pc.segment, 'all') AS segment,
            COALESCE(ss.total_sent, 0) AS total_sent,
            COALESCE(ss.total_opened, 0) AS total_opened,
            COALESCE(ss.total_clicked, 0) AS total_clicked,
            COALESCE(ss.last_sent_at, '') AS last_sent_at,
            {ENGAGEMENT_LABEL_CASE} AS engagement_label
        FROM promotional_customers pc
        LEFT JOIN send_stats ss ON LOWER(ss.email) = LOWER(pc.email)
        {where_clause}
        """

        label_filter = ""
        if label and label != "all":
            label_filter = f"HAVING engagement_label = '{label}'"

        with get_db_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM ({cte_sql}) sub {label_filter} ORDER BY total_clicked DESC, total_opened DESC",
                params,
            ).fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["email", "first_name", "last_name", "segment", "total_sent", "total_opened", "total_clicked", "last_sent_at", "engagement_label"])
        for r in rows:
            writer.writerow([r["email"], r["first_name"], r["last_name"], r["segment"],
                              r["total_sent"], r["total_opened"], r["total_clicked"],
                              r["last_sent_at"], r["engagement_label"]])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=journey_customers.csv"},
        )

    except Exception as exc:
        logger.error("journey_export error: %s", exc)
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)

