"""
app/routes/compliance.py

GDPR / Privacy compliance endpoints.

Endpoints:
  GET  /api/compliance/audit-log              — paginated admin action log
  GET  /api/compliance/export/{email}         — export all data for a customer
  DELETE /api/compliance/data/{email}         — right-to-erasure: delete all customer data
  POST /api/compliance/audit-log              — write an audit log entry (internal use)

All DELETE operations require X-Admin-Secret header for authorisation.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel

from app.config import settings
from app.storage import get_connection

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Email validation ──────────────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(email: str) -> str:
    """Validate and normalise an email address."""
    email = email.lower().strip()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Invalid email address")
    return email


def _require_admin(x_admin_secret: str = Header(default="")) -> None:
    """Dependency: validates admin secret header."""
    if not settings.admin_secret or x_admin_secret != settings.admin_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin secret required for this operation",
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Audit log model ───────────────────────────────────────────────────────────

class AuditLogEntry(BaseModel):
    admin_email:   str = "system"
    action:        str
    resource_type: str
    resource_id:   str = ""
    changes_json:  dict[str, Any] = {}
    ip_address:    str = ""


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/compliance/audit-log", summary="Paginated admin audit log")
def get_audit_log(
    action:        str  = "",
    resource_type: str  = "",
    admin_email:   str  = "",
    limit:         int  = Query(default=50, ge=1, le=200),
    offset:        int  = Query(default=0, ge=0),
    _admin: None = Depends(_require_admin),
) -> dict[str, Any]:
    conditions: list[str] = []
    params:     list[Any] = []

    if action:
        conditions.append("action = ?")
        params.append(action)
    if resource_type:
        conditions.append("resource_type = ?")
        params.append(resource_type)
    if admin_email:
        conditions.append("admin_email = ?")
        params.append(admin_email)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    with get_connection() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM audit_log {where}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"SELECT * FROM audit_log {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()

    return {
        "total":   total,
        "limit":   limit,
        "offset":  offset,
        "entries": [dict(r) for r in rows],
    }


@router.post(
    "/compliance/audit-log",
    summary="Write an audit log entry",
    status_code=status.HTTP_201_CREATED,
)
def write_audit_log(
    payload: AuditLogEntry,
    _admin: None = Depends(_require_admin),
) -> dict[str, Any]:
    entry_id = str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_log
              (id, admin_email, action, resource_type, resource_id,
               changes_json, ip_address, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry_id,
                payload.admin_email[:200],
                payload.action[:100],
                payload.resource_type[:100],
                payload.resource_id[:200],
                json.dumps(payload.changes_json),
                payload.ip_address[:100],
                _now(),
            ),
        )
    return {"id": entry_id, "status": "logged"}


@router.get("/compliance/export/{email}", summary="GDPR data export for a customer")
def export_customer_data(
    email: str,
    _admin: None = Depends(_require_admin),
) -> dict[str, Any]:
    """
    Return all data held for a customer across all tables.
    Caller should stream this as a JSON file download.
    """
    email = _validate_email(email)

    export: dict[str, Any] = {
        "export_version": "1.0",
        "exported_at":    _now(),
        "email":          email,
        "data":           {},
    }

    with get_connection() as conn:
        # promotional_customers
        row = conn.execute(
            "SELECT * FROM promotional_customers WHERE email = ?", (email,)
        ).fetchone()
        export["data"]["promotional_customer"] = dict(row) if row else None

        # journey_customers (all matching)
        rows = conn.execute(
            "SELECT * FROM journey_customers WHERE email = ?", (email,)
        ).fetchall()
        export["data"]["journey_customers"] = [dict(r) for r in rows]

        # journey_messages
        jc_ids = [r["id"] for r in (conn.execute(
            "SELECT id FROM journey_customers WHERE email = ?", (email,)
        ).fetchall())]
        if jc_ids:
            placeholders = ",".join("?" * len(jc_ids))
            msgs = conn.execute(
                f"SELECT * FROM journey_messages WHERE customer_id IN ({placeholders})",
                jc_ids,
            ).fetchall()
            export["data"]["journey_messages"] = [dict(r) for r in msgs]
        else:
            export["data"]["journey_messages"] = []

        # event_logs
        events = conn.execute(
            """
            SELECT * FROM event_logs
            WHERE json_extract(event_data,'$.email') = ?
            ORDER BY created_at DESC LIMIT 1000
            """,
            (email,),
        ).fetchall()
        export["data"]["events"] = [dict(r) for r in events]

        # campaign_sends
        sends = conn.execute(
            "SELECT * FROM campaign_sends WHERE email = ? ORDER BY sent_at DESC LIMIT 200",
            (email,),
        ).fetchall()
        export["data"]["campaign_sends"] = [dict(r) for r in sends]

        # promo_send_logs
        logs = conn.execute(
            "SELECT * FROM promo_send_logs WHERE email = ? ORDER BY logged_at DESC LIMIT 200",
            (email,),
        ).fetchall()
        export["data"]["promo_send_logs"] = [dict(r) for r in logs]

        # suppression records
        supps = conn.execute(
            """
            SELECT * FROM email_suppressions WHERE email = ?
            """,
            (email,),
        ).fetchall()
        export["data"]["email_suppressions"] = [dict(r) for r in supps]

        # customer_segments
        seg = conn.execute(
            "SELECT * FROM customer_segments WHERE email = ?", (email,)
        ).fetchone()
        export["data"]["customer_segment"] = dict(seg) if seg else None

        # campaign_attribution
        attr = conn.execute(
            "SELECT * FROM campaign_attribution WHERE customer_email = ? ORDER BY created_at DESC LIMIT 100",
            (email,),
        ).fetchall()
        export["data"]["campaign_attribution"] = [dict(r) for r in attr]

    # Write audit log entry
    _log_action(
        "data_export", "customer", email,
        {"email": email, "tables_exported": list(export["data"].keys())},
    )

    return export


@router.delete(
    "/compliance/data/{email}",
    summary="GDPR right-to-erasure: delete all customer data",
)
def delete_customer_data(
    email: str,
    _admin: None = Depends(_require_admin),
) -> dict[str, Any]:
    """
    Permanently delete all personally identifiable information for a customer.
    This operation is irreversible.
    """
    email = _validate_email(email)
    deleted: dict[str, int] = {}

    with get_connection() as conn:
        # Get journey customer IDs first
        jc_ids = [
            r["id"] for r in conn.execute(
                "SELECT id FROM journey_customers WHERE email = ?", (email,)
            ).fetchall()
        ]

        # Delete from all tables
        tables_by_email = [
            "promotional_customers",
            "campaign_sends",
            "promo_send_logs",
            "customer_segments",
            "campaign_attribution",
        ]
        for tbl in tables_by_email:
            try:
                cur = conn.execute(f"DELETE FROM {tbl} WHERE email = ?", (email,))
                deleted[tbl] = cur.rowcount
            except Exception:
                deleted[tbl] = 0

        # email_suppressions
        try:
            cur = conn.execute("DELETE FROM email_suppressions WHERE email = ?", (email,))
            deleted["email_suppressions"] = cur.rowcount
        except Exception:
            deleted["email_suppressions"] = 0

        # event_logs (anonymise rather than delete — preserve aggregate stats)
        try:
            cur = conn.execute(
                """
                UPDATE event_logs
                SET event_data = json_set(event_data, '$.email', 'deleted@deleted.invalid')
                WHERE json_extract(event_data,'$.email') = ?
                """,
                (email,),
            )
            deleted["event_logs_anonymised"] = cur.rowcount
        except Exception:
            deleted["event_logs_anonymised"] = 0

        # journey_messages (anonymise message content)
        if jc_ids:
            placeholders = ",".join("?" * len(jc_ids))
            try:
                cur = conn.execute(
                    f"UPDATE journey_messages SET variables_json='{{}}' WHERE customer_id IN ({placeholders})",
                    jc_ids,
                )
                deleted["journey_messages_anonymised"] = cur.rowcount
            except Exception:
                deleted["journey_messages_anonymised"] = 0

            # Delete journey_customers
            try:
                cur = conn.execute(
                    f"DELETE FROM journey_customers WHERE id IN ({placeholders})",
                    jc_ids,
                )
                deleted["journey_customers"] = cur.rowcount
            except Exception:
                deleted["journey_customers"] = 0

    _log_action("data_erasure", "customer", email, {"email": email, "deleted": deleted})
    logger.info("GDPR erasure completed for %s: %s", email, deleted)

    return {
        "status":  "completed",
        "email":   email,
        "deleted": deleted,
        "note":    "Event logs have been anonymised (email replaced). Journey messages content cleared.",
    }


# ── Segments compliance export ────────────────────────────────────────────────

@router.get("/compliance/segment-members/{segment_id}", summary="Export members of a saved segment")
def export_segment_members(
    segment_id: str,
    limit: int = Query(default=500, ge=1, le=5000),
    _admin: None = Depends(_require_admin),
) -> dict[str, Any]:
    """Export email list for a named segment (for targeted campaigns)."""
    with get_connection() as conn:
        seg = conn.execute(
            "SELECT * FROM saved_segments WHERE id = ?", (segment_id,)
        ).fetchone()
        if not seg:
            raise HTTPException(status_code=404, detail="Segment not found")

        filters = json.loads(seg["filters_json"] or "{}")
        conditions: list[str] = []
        params: list[Any] = []

        if filters.get("rfm_segment"):
            conditions.append("cs.rfm_segment = ?")
            params.append(filters["rfm_segment"])
        if filters.get("engagement_label"):
            conditions.append("cs.engagement_label = ?")
            params.append(filters["engagement_label"])

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        members = conn.execute(
            f"""
            SELECT cs.email, cs.rfm_segment, cs.engagement_label,
                   cs.clv_estimate_inr, pc.whatsapp_opted_in, pc.email_opted_in
            FROM customer_segments cs
            LEFT JOIN promotional_customers pc ON pc.email = cs.email
            {where}
            ORDER BY cs.clv_estimate_inr DESC
            LIMIT ?
            """,
            params + [limit],
        ).fetchall()

    return {
        "segment_id":   segment_id,
        "segment_name": seg["name"],
        "member_count": len(members),
        "members":      [dict(r) for r in members],
    }


# ── Internal helper ───────────────────────────────────────────────────────────

def _log_action(
    action: str,
    resource_type: str,
    resource_id: str,
    changes: dict[str, Any],
) -> None:
    """Write to audit_log silently."""
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_log
                  (id, admin_email, action, resource_type, resource_id,
                   changes_json, ip_address, created_at)
                VALUES (?, 'system', ?, ?, ?, ?, '', ?)
                """,
                (str(uuid.uuid4()), action, resource_type, resource_id,
                 json.dumps(changes), _now()),
            )
    except Exception as exc:
        logger.warning("Audit log write failed: %s", exc)
