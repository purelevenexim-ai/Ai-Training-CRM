"""
Customers API Routes

CRUD for unified customer profiles, CSV import, and Shopify sync trigger.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, EmailStr

from app.config import settings
from app.services import customer_unification_service as cus
from app.services import customer_intelligence_service as cis

logger = logging.getLogger(__name__)
router = APIRouter(tags=['customers'])


# ── Auth ───────────────────────────────────────────────────────────────────────

def _require_admin(admin_secret: str = Query(..., alias='admin_secret')) -> None:
    if admin_secret != settings.admin_secret:
        raise HTTPException(status_code=403, detail='Invalid admin_secret')


# ── Models ─────────────────────────────────────────────────────────────────────

class CustomerCreateRequest(BaseModel):
    email: str
    name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    tags: list[str] = []
    source: str = 'manual'
    email_opted_in: bool = False
    whatsapp_opted_in: bool = False
    notes: str | None = None
    meta_lead_id: str | None = None
    google_gclid: str | None = None
    google_campaign: str | None = None
    meta_campaign: str | None = None
    preferred_channel: str | None = 'auto'
    pause_campaigns: bool = False


class CustomerUpdateRequest(BaseModel):
    name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    tags: list[str] | None = None
    email_opted_in: bool | None = None
    whatsapp_opted_in: bool | None = None
    notes: str | None = None
    customer_status: str | None = None
    meta_lead_id: str | None = None
    google_gclid: str | None = None
    google_campaign: str | None = None
    meta_campaign: str | None = None
    preferred_channel: str | None = None
    pause_campaigns: bool | None = None


class CustomerPauseRequest(BaseModel):
    paused: bool = True


class CustomerAiReplyRequest(BaseModel):
    inbound_message: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get('/customers')
def list_customers(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None),
    status: str | None = Query(None),
    email_opted_in: bool | None = Query(None),
    order_by: str = Query('created_at'),
    order_dir: str = Query('DESC'),
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    rows, total = cus.list_customers(
        limit=limit,
        offset=offset,
        search=search,
        status=status,
        email_opted_in=email_opted_in,
        order_by=order_by,
        order_dir=order_dir,
    )
    return {
        'customers': rows,
        'total': total,
        'limit': limit,
        'offset': offset,
    }


@router.post('/customers')
def create_customer(
    body: CustomerCreateRequest,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    return cus.upsert_customer(
        email=body.email,
        name=body.name,
        first_name=body.first_name,
        last_name=body.last_name,
        phone=body.phone,
        tags=body.tags,
        source=body.source,
        email_opted_in=body.email_opted_in,
        whatsapp_opted_in=body.whatsapp_opted_in,
        notes=body.notes,
        meta_lead_id=body.meta_lead_id,
        google_gclid=body.google_gclid,
        google_campaign=body.google_campaign,
        meta_campaign=body.meta_campaign,
        preferred_channel=body.preferred_channel,
        pause_campaigns=body.pause_campaigns,
    )


@router.get('/customers/{email}')
def get_customer(
    email: str,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    customer = cus.get_customer(email)
    if not customer:
        raise HTTPException(status_code=404, detail='Customer not found')
    return customer


@router.put('/customers/{email}')
def update_customer(
    email: str,
    body: CustomerUpdateRequest,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    existing = cus.get_customer(email)
    if not existing:
        raise HTTPException(status_code=404, detail='Customer not found')
    return cus.upsert_customer(
        email=email,
        name=body.name,
        first_name=body.first_name,
        last_name=body.last_name,
        phone=body.phone,
        tags=body.tags,
        email_opted_in=body.email_opted_in,
        whatsapp_opted_in=body.whatsapp_opted_in,
        notes=body.notes,
        meta_lead_id=body.meta_lead_id,
        google_gclid=body.google_gclid,
        google_campaign=body.google_campaign,
        meta_campaign=body.meta_campaign,
        preferred_channel=body.preferred_channel,
        pause_campaigns=body.pause_campaigns,
    )


@router.get('/customers/{email}/intelligence')
def get_customer_intelligence(
    email: str,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    data = cis.get_customer_intelligence(email)
    if not data:
        raise HTTPException(status_code=404, detail='Customer not found')
    return data


@router.get('/customers/{email}/identities')
def get_customer_identities(
    email: str,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    customer = cus.get_customer(email)
    if not customer:
        raise HTTPException(status_code=404, detail='Customer not found')
    identities = cus.list_customer_identities(email)
    return {'customer_uid': customer.get('customer_uid'), 'items': identities, 'count': len(identities)}


@router.post('/customers/{email}/pause-campaigns')
def pause_customer_campaigns(
    email: str,
    body: CustomerPauseRequest,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    updated = cus.set_pause_campaigns(email, body.paused)
    if not updated:
        raise HTTPException(status_code=404, detail='Customer not found')
    return {'email': email, 'paused': body.paused}


@router.post('/customers/{email}/ai-reply-draft')
def ai_reply_draft(
    email: str,
    body: CustomerAiReplyRequest,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    result = cis.draft_ai_email_reply(email, body.inbound_message)
    if result.get('error'):
        raise HTTPException(status_code=404, detail=result['error'])
    return result


@router.delete('/customers/{email}')
def delete_customer(
    email: str,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    deleted = cus.soft_delete_customer(email)
    if not deleted:
        raise HTTPException(status_code=404, detail='Customer not found')
    return {'deleted': True, 'email': email}


# ── CSV Import ─────────────────────────────────────────────────────────────────

@router.post('/customers/import/csv')
async def import_csv(
    file: UploadFile = File(...),
    default_tags: str = Query('', description='Comma-separated tags to apply to all imported rows'),
    email_opted_in: bool = Query(True),
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    """
    Upload a CSV file to import customers.
    Required column: email
    Optional columns: name, first_name, last_name, phone, tags
    """
    content_type = file.content_type or ''
    if 'csv' not in content_type and not (file.filename or '').endswith('.csv'):
        raise HTTPException(status_code=400, detail='Only CSV files are accepted')

    raw = await file.read()
    try:
        csv_text = raw.decode('utf-8-sig')  # handles BOM
    except UnicodeDecodeError:
        csv_text = raw.decode('latin-1')

    tags = [t.strip() for t in default_tags.split(',') if t.strip()]
    result = cus.import_csv(
        csv_text,
        filename=file.filename or 'upload.csv',
        default_tags=tags,
        email_opted_in=email_opted_in,
    )
    return result


@router.post('/customers/import/xml')
async def import_xml(
    file: UploadFile = File(...),
    default_tags: str = Query('', description='Comma-separated tags to apply to all imported rows'),
    email_opted_in: bool = Query(True),
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    content_type = file.content_type or ''
    if 'xml' not in content_type and not (file.filename or '').endswith('.xml'):
        raise HTTPException(status_code=400, detail='Only XML files are accepted')

    raw = await file.read()
    try:
        xml_text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        xml_text = raw.decode('latin-1')

    tags = [t.strip() for t in default_tags.split(',') if t.strip()]
    return cus.import_xml(
        xml_text,
        filename=file.filename or 'upload.xml',
        default_tags=tags,
        email_opted_in=email_opted_in,
    )


@router.post('/customers/recompute-scores')
def recompute_scores(
    limit: int = Query(500, ge=1, le=5000),
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    return cis.recompute_all_customer_scores(limit=limit)


# ── Shopify Sync ───────────────────────────────────────────────────────────────

@router.post('/customers/sync/shopify')
def sync_from_shopify(
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    """Trigger a manual Shopify customer sync."""
    try:
        from app.services.shopify_customer_importer import ShopifyCustomerImporter
        importer = ShopifyCustomerImporter()
        result = importer.run_import()
        return {'status': 'ok', 'result': result}
    except Exception as exc:
        logger.error('shopify sync failed: %s', exc)
        raise HTTPException(status_code=500, detail=str(exc))
