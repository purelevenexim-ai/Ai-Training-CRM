from __future__ import annotations

import json
import logging
import re
import uuid
from urllib.parse import urlencode, urlparse

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status

from app.schemas import (
    GoogleAuthRequest,
    LeadCreate,
    LeadCreateResponse,
    OtpAuthRequest,
    TruecallerAuthRequest,
    TruecallerCallbackPayload,
    TruecallerRequestStatusResponse,
    TruecallerStartRequest,
    TruecallerStartResponse,
)
from app.storage import (
    create_truecaller_request,
    fetch_truecaller_profile,
    get_admin_settings,
    get_truecaller_request,
    insert_lead,
    is_truecaller_request_expired,
    save_truecaller_profile,
    save_truecaller_request,
    sync_lead_to_shopify_customer,
)

router = APIRouter(tags=['anu-login-auth'])
logger = logging.getLogger(__name__)


def derive_truecaller_partner_name(configured_name: str, page_url: str | None) -> str:
    partner_name = configured_name.strip()

    if partner_name:
        return partner_name

    parsed_url = urlparse(page_url or '')
    hostname = (parsed_url.hostname or '').strip().lower()

    if hostname.startswith('www.'):
        hostname = hostname[4:]

    base_name = hostname.split('.')[0]
    readable_name = re.sub(r'[^a-z0-9]+', ' ', base_name).strip().title()
    return readable_name or 'PureLeven'


def resolve_policy_url(configured_url: str, page_url: str | None) -> str:
    candidate = configured_url.strip() or (page_url or '').strip()
    return candidate or 'https://pureleven.com'


def build_truecaller_launch_url(request_id: str, payload: TruecallerStartRequest) -> str:
    admin_settings = get_admin_settings()

    params = {
        'type': 'btmsheet',
        'requestNonce': request_id,
        'partnerKey': admin_settings.truecaller.client_id,
        'partnerName': derive_truecaller_partner_name(admin_settings.truecaller.partner_name, payload.page_url),
        'lang': 'en',
        'privacyUrl': resolve_policy_url(admin_settings.privacy_policy_url, payload.page_url),
        'termsUrl': resolve_policy_url(admin_settings.terms_of_service_url, payload.page_url),
        'loginPrefix': 'continue',
        'loginSuffix': 'loginsignup',
        'ctaPrefix': 'continuewith',
        'ctaColor': '#0f7a5c',
        'ctaTextColor': '#ffffff',
        'btnShape': 'round',
        'skipOption': 'manualdetails',
        'ttl': '15000',
    }

    return f"truecallersdk://truesdk/web_verify?{urlencode(params)}"


def build_truecaller_status_message(status_value: str, error_message: str | None = None) -> str | None:
    messages = {
        'created': 'Opening Truecaller. Approve the verification sheet to continue.',
        'flow_invoked': 'Truecaller opened. Approve the verification sheet to continue.',
        'profile_requested': 'Truecaller approved. Fetching your verified profile now.',
        'verified': None,
        'user_rejected': 'Truecaller verification was cancelled. You can try again or use another method.',
        'expired': 'Truecaller verification timed out. Start the verification again.',
        'error': error_message or 'Truecaller verification could not be completed.',
    }
    return messages.get(status_value, error_message or 'Truecaller verification is still in progress.')


def complete_truecaller_profile_fetch(request_id: str, access_token: str, endpoint: str) -> None:
    try:
        profile = fetch_truecaller_profile(endpoint, access_token)
        save_truecaller_profile(request_id, profile)
    except Exception as error:  # pragma: no cover - depends on external provider callback state
        logger.warning('Truecaller profile fetch failed for request %s: %s', request_id, error)
        save_truecaller_request(
            request_id,
            status='error',
            profile_endpoint=endpoint,
            error_message=str(error),
        )


def build_provider_lead(
    provider: str,
    source: str,
    consent: bool,
    page_type: str | None,
    page_url: str | None,
    customer_id: str | None,
    cart_item_count: int,
    cart_total_cents: int,
    name: str | None,
    email: str | None,
    phone: str | None,
) -> LeadCreate:
    return LeadCreate(
        source=source,
        provider=provider,
        consent=consent,
        page_type=page_type,
        page_url=page_url,
        customer_id=customer_id,
        cart_item_count=cart_item_count,
        cart_total_cents=cart_total_cents,
        name=name,
        email=email,
        phone=phone,
    )


@router.post('/auth/google', response_model=LeadCreateResponse, status_code=status.HTTP_201_CREATED)
def auth_google(payload: GoogleAuthRequest) -> LeadCreateResponse:
    admin_settings = get_admin_settings()
    client_id = admin_settings.google.client_id or payload.client_id

    if not client_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Google login is not configured.')

    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token

        identity = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            client_id,
        )
    except Exception as error:  # pragma: no cover - verification depends on provider input
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid Google credential.') from error

    lead = sync_lead_to_shopify_customer(insert_lead(
        build_provider_lead(
            provider='google',
            source='anu_login_google',
            consent=payload.consent,
            page_type=payload.page_type,
            page_url=payload.page_url,
            customer_id=payload.customer_id,
            cart_item_count=payload.cart_item_count,
            cart_total_cents=payload.cart_total_cents,
            name=payload.name or identity.get('name'),
            email=payload.email or identity.get('email'),
            phone=payload.phone,
        )
    ))
    return LeadCreateResponse(coupon_code=lead.coupon_code, lead=lead)


def get_firebase_auth_client(service_account_json: str):
    try:
        import firebase_admin
        from firebase_admin import auth as firebase_auth
        from firebase_admin import credentials

        service_account = json.loads(service_account_json)
        app_name = f"anu-login-{service_account.get('project_id', 'default')}"

        try:
            firebase_app = firebase_admin.get_app(app_name)
        except ValueError:
            firebase_app = firebase_admin.initialize_app(credentials.Certificate(service_account), name=app_name)

        return firebase_auth, firebase_app
    except Exception as error:  # pragma: no cover - provider bootstrap depends on runtime secrets
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Firebase OTP is not configured correctly.') from error


@router.post('/auth/otp', response_model=LeadCreateResponse, status_code=status.HTTP_201_CREATED)
def auth_otp(payload: OtpAuthRequest) -> LeadCreateResponse:
    admin_settings = get_admin_settings()

    if not admin_settings.otp.enabled or not admin_settings.otp.service_account_json:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='OTP login is not configured.')

    firebase_auth, firebase_app = get_firebase_auth_client(admin_settings.otp.service_account_json)

    try:
        decoded_token = firebase_auth.verify_id_token(payload.firebase_token, app=firebase_app)
    except Exception as error:  # pragma: no cover - verification depends on provider input
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid OTP token.') from error

    lead = sync_lead_to_shopify_customer(insert_lead(
        build_provider_lead(
            provider='otp',
            source='anu_login_otp',
            consent=payload.consent,
            page_type=payload.page_type,
            page_url=payload.page_url,
            customer_id=payload.customer_id,
            cart_item_count=payload.cart_item_count,
            cart_total_cents=payload.cart_total_cents,
            name=payload.name,
            email=payload.email,
            phone=payload.phone or decoded_token.get('phone_number'),
        )
    ))
    return LeadCreateResponse(coupon_code=lead.coupon_code, lead=lead)


@router.post('/auth/truecaller', response_model=LeadCreateResponse, status_code=status.HTTP_201_CREATED)
def auth_truecaller(payload: TruecallerAuthRequest) -> LeadCreateResponse:
    admin_settings = get_admin_settings()

    if not admin_settings.truecaller.enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Truecaller login is not configured.')

    verified_name = None
    verified_email = None
    verified_phone = None

    if admin_settings.truecaller.verification_mode != 'passthrough':
        if not payload.request_nonce:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Truecaller verification session is missing.')

        request_record = get_truecaller_request(payload.request_nonce)

        if request_record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Truecaller verification session was not found.')

        if is_truecaller_request_expired(request_record) and request_record.status not in {'verified', 'user_rejected', 'error'}:
            request_record = save_truecaller_request(
                payload.request_nonce,
                status='expired',
                error_message='Truecaller verification timed out.',
            )

        if request_record.status != 'verified':
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=build_truecaller_status_message(request_record.status, request_record.error_message)
                or 'Truecaller verification is still in progress.',
            )

        verified_name = request_record.name
        verified_email = request_record.email
        verified_phone = request_record.phone

    resolved_name = verified_name or payload.name
    resolved_email = verified_email or payload.email
    resolved_phone = verified_phone or payload.phone

    if not resolved_phone and not resolved_email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Truecaller verification did not return a phone number or email address.',
        )

    lead = sync_lead_to_shopify_customer(insert_lead(
        build_provider_lead(
            provider='truecaller',
            source='anu_login_truecaller',
            consent=payload.consent,
            page_type=payload.page_type,
            page_url=payload.page_url,
            customer_id=payload.customer_id,
            cart_item_count=payload.cart_item_count,
            cart_total_cents=payload.cart_total_cents,
            name=resolved_name,
            email=resolved_email,
            phone=resolved_phone,
        )
    ))
    return LeadCreateResponse(coupon_code=lead.coupon_code, lead=lead)


@router.post('/truecaller/start', response_model=TruecallerStartResponse, status_code=status.HTTP_201_CREATED)
def start_truecaller_verification(payload: TruecallerStartRequest, request: Request) -> TruecallerStartResponse:
    admin_settings = get_admin_settings()

    if not admin_settings.truecaller.enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Truecaller login is not enabled.')

    if admin_settings.truecaller.verification_mode == 'passthrough':
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Truecaller is currently configured for manual passthrough mode.')

    if not admin_settings.truecaller.client_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Truecaller app key is missing from Anu settings.')

    request_id = uuid.uuid4().hex
    create_truecaller_request(request_id)
    launch_url = build_truecaller_launch_url(request_id, payload)

    return TruecallerStartResponse(
        request_id=request_id,
        launch_url=launch_url,
        status_url=str(request.url_for('truecaller_request_status', request_id=request_id)),
    )


@router.post('/truecaller/callback', status_code=status.HTTP_204_NO_CONTENT)
def truecaller_callback(payload: TruecallerCallbackPayload, background_tasks: BackgroundTasks) -> Response:
    raw_payload = payload.model_dump(by_alias=True, exclude_none=True)

    if payload.status == 'flow_invoked':
        save_truecaller_request(payload.request_id, status='flow_invoked', raw_callback=raw_payload, error_message='')
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if payload.status == 'user_rejected':
        save_truecaller_request(payload.request_id, status='user_rejected', raw_callback=raw_payload, error_message='Truecaller verification was cancelled by the user.')
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if payload.access_token and payload.endpoint:
        save_truecaller_request(
            payload.request_id,
            status='profile_requested',
            profile_endpoint=payload.endpoint,
            raw_callback=raw_payload,
            error_message='',
        )
        background_tasks.add_task(complete_truecaller_profile_fetch, payload.request_id, payload.access_token, payload.endpoint)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    save_truecaller_request(
        payload.request_id,
        status='error',
        raw_callback=raw_payload,
        error_message='Truecaller callback payload was incomplete.',
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get('/truecaller/requests/{request_id}', response_model=TruecallerRequestStatusResponse)
def truecaller_request_status(request_id: str) -> TruecallerRequestStatusResponse:
    request_record = get_truecaller_request(request_id)

    if request_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Truecaller verification session was not found.')

    if is_truecaller_request_expired(request_record) and request_record.status not in {'verified', 'user_rejected', 'error'}:
        request_record = save_truecaller_request(
            request_id,
            status='expired',
            error_message='Truecaller verification timed out.',
        )

    return TruecallerRequestStatusResponse(
        request_id=request_record.request_id,
        status=request_record.status,
        verified=request_record.status == 'verified',
        name=request_record.name,
        email=request_record.email,
        phone=request_record.phone,
        phone_country_code=request_record.phone_country_code,
        message=build_truecaller_status_message(request_record.status, request_record.error_message),
        updated_at=request_record.updated_at,
    )