"""
Audiences API Routes

Contact lists and communication templates.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.config import settings
from app.services import audience_service as aud

logger = logging.getLogger(__name__)
router = APIRouter(tags=['audiences'])


# ── Auth ───────────────────────────────────────────────────────────────────────

def _require_admin(admin_secret: str = Query(..., alias='admin_secret')) -> None:
    if admin_secret != settings.admin_secret:
        raise HTTPException(status_code=403, detail='Invalid admin_secret')


# ── Models ─────────────────────────────────────────────────────────────────────

class ListCreateRequest(BaseModel):
    name: str
    description: str | None = None
    list_type: str = 'static'
    rules: dict | None = None


class ListUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class BulkAddRequest(BaseModel):
    customer_ids: list[str]


class TemplateCreateRequest(BaseModel):
    name: str
    category: str = 'promotional'
    description: str | None = None
    email_subject: str | None = None
    email_preheader: str | None = None
    email_html: str | None = None
    email_text: str | None = None
    whatsapp_body: str | None = None
    whatsapp_header_image_url: str | None = None
    variables: list[str] = []
    status: str = 'draft'


class TemplateUpdateRequest(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    status: str | None = None
    email_subject: str | None = None
    email_preheader: str | None = None
    email_html: str | None = None
    email_text: str | None = None
    whatsapp_body: str | None = None
    whatsapp_header_image_url: str | None = None
    variables: list[str] | None = None


# ── List endpoints ─────────────────────────────────────────────────────────────

@router.get('/audiences/lists')
def list_contact_lists(_: None = Depends(_require_admin)) -> dict[str, Any]:
    return {'lists': aud.list_all_lists()}


@router.post('/audiences/lists')
def create_list(
    body: ListCreateRequest,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    return aud.create_list(body.name, description=body.description,
                           list_type=body.list_type, rules=body.rules)


@router.get('/audiences/lists/{list_id}')
def get_list(
    list_id: str,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    lst = aud.get_list(list_id)
    if not lst:
        raise HTTPException(status_code=404, detail='List not found')
    return lst


@router.put('/audiences/lists/{list_id}')
def update_list(
    list_id: str,
    body: ListUpdateRequest,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    updated = aud.update_list(list_id, name=body.name, description=body.description)
    if not updated:
        raise HTTPException(status_code=404, detail='List not found')
    return updated


@router.delete('/audiences/lists/{list_id}')
def delete_list(
    list_id: str,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    deleted = aud.delete_list(list_id)
    if not deleted:
        raise HTTPException(status_code=404, detail='List not found')
    return {'deleted': True, 'list_id': list_id}


@router.get('/audiences/lists/{list_id}/members')
def get_list_members(
    list_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    members, total = aud.get_list_members(list_id, limit=limit, offset=offset)
    return {'members': members, 'total': total, 'list_id': list_id}


@router.post('/audiences/lists/{list_id}/members/{customer_id}')
def add_member(
    list_id: str,
    customer_id: str,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    added = aud.add_to_list(list_id, customer_id)
    return {'added': added, 'list_id': list_id, 'customer_id': customer_id}


@router.post('/audiences/lists/{list_id}/members/bulk')
def bulk_add_members(
    list_id: str,
    body: BulkAddRequest,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    added = aud.bulk_add_to_list(list_id, body.customer_ids)
    return {'added': added, 'list_id': list_id}


@router.delete('/audiences/lists/{list_id}/members/{customer_id}')
def remove_member(
    list_id: str,
    customer_id: str,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    removed = aud.remove_from_list(list_id, customer_id)
    if not removed:
        raise HTTPException(status_code=404, detail='Member not found')
    return {'removed': True}


# ── Template endpoints ─────────────────────────────────────────────────────────

@router.get('/audiences/templates')
def list_templates(
    category: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    rows, total = aud.list_templates(category=category, status=status, limit=limit, offset=offset)
    return {'templates': rows, 'total': total}


@router.post('/audiences/templates')
def create_template(
    body: TemplateCreateRequest,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    return aud.create_template(
        name=body.name,
        category=body.category,
        description=body.description,
        email_subject=body.email_subject,
        email_preheader=body.email_preheader,
        email_html=body.email_html,
        email_text=body.email_text,
        whatsapp_body=body.whatsapp_body,
        whatsapp_header_image_url=body.whatsapp_header_image_url,
        variables=body.variables,
        status=body.status,
    )


@router.get('/audiences/templates/{template_id}')
def get_template(
    template_id: str,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    tmpl = aud.get_template(template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail='Template not found')
    return tmpl


@router.put('/audiences/templates/{template_id}')
def update_template(
    template_id: str,
    body: TemplateUpdateRequest,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    updates = body.model_dump(exclude_none=True)
    updated = aud.update_template(template_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail='Template not found')
    return updated


@router.delete('/audiences/templates/{template_id}')
def delete_template(
    template_id: str,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    deleted = aud.delete_template(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail='Template not found')
    return {'deleted': True, 'template_id': template_id}
