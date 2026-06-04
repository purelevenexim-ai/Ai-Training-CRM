from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas import LeadCreate, LeadCreateResponse, LeadEmailCaptureRequest, LeadListResponse
from app.routes.settings import require_admin_access
from app.storage import insert_lead, list_leads, sync_lead_to_shopify_customer, update_lead_email


router = APIRouter(tags=['anu-login'])


@router.post('/leads', response_model=LeadCreateResponse, status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate) -> LeadCreateResponse:
    lead = sync_lead_to_shopify_customer(insert_lead(payload))
    return LeadCreateResponse(coupon_code=lead.coupon_code, lead=lead)


@router.put('/leads/{lead_id}/email', response_model=LeadCreateResponse)
def update_lead_email_capture(lead_id: int, payload: LeadEmailCaptureRequest) -> LeadCreateResponse:
    try:
        lead = sync_lead_to_shopify_customer(update_lead_email(lead_id, payload.phone, payload.email))
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return LeadCreateResponse(coupon_code=lead.coupon_code, lead=lead)


@router.get('/leads', response_model=LeadListResponse, dependencies=[Depends(require_admin_access)])
def get_leads(
    limit: int = Query(default=50, ge=1, le=200),
    search: str | None = Query(default=None, max_length=80),
) -> LeadListResponse:
    total, items = list_leads(limit=limit, search=search)
    return LeadListResponse(total=total, items=items)