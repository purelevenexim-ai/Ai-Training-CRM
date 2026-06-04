from __future__ import annotations

from hmac import compare_digest

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.config import settings
from app.schemas import (
    AdminDashboardResponse,
    AdminSettings,
    PublicSettingsResponse,
    ShopifyConnectionPayload,
    ShopifyConnectionStatus,
)
from app.storage import (
    export_leads_csv,
    get_admin_settings,
    get_dashboard_summary,
    get_public_settings,
    get_shopify_connection_status,
    save_admin_settings,
    save_shopify_connection,
)


router = APIRouter(tags=['anu-login-settings'])


def is_loopback_client(host: str | None) -> bool:
    return host in {'127.0.0.1', '::1', 'localhost', '::ffff:127.0.0.1'}


def require_admin_access(request: Request) -> None:
    if settings.admin_secret:
        provided_secret = request.headers.get('x-anu-admin-secret', '')

        if not compare_digest(provided_secret, settings.admin_secret):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid Anu admin credentials.')

        return

    client_host = request.client.host if request.client else None

    if not is_loopback_client(client_host):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Anu admin endpoints require local app access or a configured admin secret.',
        )


@router.get('/settings/public', response_model=PublicSettingsResponse)
def public_settings() -> PublicSettingsResponse:
    return get_public_settings()


@router.get('/admin/settings', response_model=AdminSettings, dependencies=[Depends(require_admin_access)])
def admin_settings() -> AdminSettings:
    return get_admin_settings()


@router.put('/admin/settings', response_model=AdminSettings, dependencies=[Depends(require_admin_access)])
def update_admin_settings(payload: AdminSettings) -> AdminSettings:
    return save_admin_settings(payload)


@router.get('/admin/shopify-connection', response_model=ShopifyConnectionStatus, dependencies=[Depends(require_admin_access)])
def admin_shopify_connection() -> ShopifyConnectionStatus:
    return get_shopify_connection_status()


@router.put('/admin/shopify-connection', response_model=ShopifyConnectionStatus, dependencies=[Depends(require_admin_access)])
def update_shopify_connection(payload: ShopifyConnectionPayload) -> ShopifyConnectionStatus:
    return save_shopify_connection(payload)


@router.get('/admin/dashboard', response_model=AdminDashboardResponse, dependencies=[Depends(require_admin_access)])
def admin_dashboard() -> AdminDashboardResponse:
    return AdminDashboardResponse.model_validate(get_dashboard_summary())


@router.get('/admin/leads/export', dependencies=[Depends(require_admin_access)])
def export_leads(search: str | None = Query(default=None, max_length=80)) -> Response:
    csv_payload = export_leads_csv(search=search)
    return Response(
        content=csv_payload,
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="anu-login-leads.csv"'},
    )