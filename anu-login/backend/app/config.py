from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def parse_origins(raw_value: str) -> list[str]:
    origins = [origin.strip() for origin in raw_value.split(',') if origin.strip()]
    return origins or ['*']


def parse_bool(raw_value: str, default: bool) -> bool:
    value = (raw_value or '').strip().lower()
    if not value:
        return default
    return value in {'1', 'true', 'yes', 'on'}


@dataclass(frozen=True)
class Settings:
    app_name: str
    database_path: Path
    admin_ui_path: Path
    default_coupon_code: str
    allowed_origins: list[str]
    admin_secret: str
    shopify_admin_api_version: str
    # WhatsApp / Delhivery / Wabis
    delhivery_api_token: str
    delhivery_webhook_secret: str
    default_shop_domain: str
    wabis_api_key: str
    wabis_phone_number_id: str
    wabis_base_url: str
    wabis_webhook_secret: str
    meta_webhook_verify_token: str
    # Shopify webhooks
    shopify_webhook_secret: str
    # Meta WhatsApp direct API
    meta_waba_id: str
    meta_phone_number_id: str
    meta_access_token: str
    meta_owner_phone: str   # Owner alert target (e.g. 918848265849)
    # AI APIs
    gemini_api_key: str
    openrouter_api_key: str
    openrouter_base_url: str
    # Shopify Admin API
    shopify_admin_api_token: str
    shopify_access_token: str
    # Public base URL
    public_base_url: str
    # Google Workspace SMTP
    google_workspace_email: str
    google_workspace_app_password: str
    google_workspace_sender_name: str
    google_smtp_host: str
    google_smtp_port: int
    promo_scheduler_enabled: bool
    ai_followup_send_enabled: bool
    promo_queue_poll_seconds: int
    promo_send_interval_seconds: float
    promo_retry_attempts: int
    promo_retry_backoff_seconds: int
    promo_queue_batch_size: int
    # Google Business Profile (GMB)
    gmb_access_token: str
    gmb_location_name: str


def load_settings() -> Settings:
    default_database = Path(__file__).resolve().parents[1] / 'data' / 'anu_login.sqlite3'
    raw_database_path = os.getenv('ANU_LOGIN_DATABASE_PATH', '').strip()
    database_path = Path(raw_database_path) if raw_database_path else default_database
    database_path.parent.mkdir(parents=True, exist_ok=True)
    admin_ui_path = Path(__file__).resolve().parents[2] / 'app' / 'anu-login-admin' / 'build' / 'client'

    raw_origins = os.getenv('ANU_LOGIN_ALLOWED_ORIGINS', '*').strip()

    return Settings(
        app_name='Anu Login API',
        database_path=database_path,
        admin_ui_path=admin_ui_path,
        default_coupon_code=os.getenv('ANU_LOGIN_DEFAULT_COUPON', 'PL10OFF').strip() or 'PL10OFF',
        allowed_origins=parse_origins(raw_origins),
        admin_secret=os.getenv('ANU_LOGIN_ADMIN_SECRET', '').strip(),
        shopify_admin_api_version=os.getenv('ANU_LOGIN_SHOPIFY_API_VERSION', '2026-07').strip() or '2026-07',
        # WhatsApp / Delhivery / Wabis
        delhivery_api_token=os.getenv('DELHIVERY_API_TOKEN', '').strip(),
        delhivery_webhook_secret=os.getenv('DELHIVERY_WEBHOOK_SECRET', '').strip(),
        default_shop_domain=os.getenv('SHOPIFY_SHOP_DOMAIN', '').strip(),
        wabis_api_key=(os.getenv('WABIS_API_KEY') or os.getenv('WABIS_API_TOKEN') or '').strip(),
        wabis_phone_number_id=(os.getenv('WABIS_PHONE_NUMBER_ID') or '252036884661683').strip(),
        wabis_base_url=os.getenv('WABIS_BASE_URL', 'https://api.wabis.io').strip(),
        wabis_webhook_secret=os.getenv('WABIS_WEBHOOK_SECRET', os.getenv('ANU_LOGIN_WABIS_WEBHOOK_SECRET', '')).strip(),
        meta_webhook_verify_token=os.getenv('META_WEBHOOK_VERIFY_TOKEN', '').strip(),
        # Shopify webhooks
        shopify_webhook_secret=os.getenv('SHOPIFY_WEBHOOK_SECRET', '').strip(),
        # Meta WhatsApp direct API
        meta_waba_id=(os.getenv('META_WABA_ID') or os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID') or '').strip(),
        meta_phone_number_id=(os.getenv('META_PHONE_NUMBER_ID') or os.getenv('META_WA_PHONE_ID') or '').strip(),
        meta_access_token=(os.getenv('META_WA_TOKEN') or os.getenv('META_ACCESS_TOKEN') or '').strip(),
        meta_owner_phone=os.getenv('META_OWNER_PHONE', '918848265849').strip(),
        # AI APIs
        gemini_api_key=os.getenv('GEMINI_API_KEY', '').strip(),
        openrouter_api_key=os.getenv('OPENROUTER_API_KEY', '').strip(),
        openrouter_base_url=os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1').strip(),
        # Shopify Admin API
        shopify_admin_api_token=os.getenv('SHOPIFY_ADMIN_API_TOKEN', '').strip(),
        shopify_access_token=os.getenv('SHOPIFY_ACCESS_TOKEN', os.getenv('SHOPIFY_ADMIN_API_TOKEN', '')).strip(),
        # Public base URL
        public_base_url=os.getenv('PUBLIC_BASE_URL', 'https://api.pureleven.com').strip(),
        # Google Workspace SMTP
        google_workspace_email=os.getenv('GOOGLE_WORKSPACE_EMAIL', '').strip(),
        google_workspace_app_password=os.getenv('GOOGLE_WORKSPACE_APP_PASSWORD', '').strip(),
        google_workspace_sender_name=os.getenv('GOOGLE_WORKSPACE_SENDER_NAME', 'PureLeven').strip(),
        google_smtp_host=os.getenv('GOOGLE_SMTP_HOST', 'smtp.gmail.com').strip(),
        google_smtp_port=int(os.getenv('GOOGLE_SMTP_PORT', '587') or '587'),
        promo_scheduler_enabled=parse_bool(os.getenv('ANU_LOGIN_PROMO_SCHEDULER_ENABLED', 'true'), True),
        ai_followup_send_enabled=parse_bool(os.getenv('ANU_LOGIN_AI_FOLLOWUP_SEND_ENABLED', 'false'), False),
        promo_queue_poll_seconds=int(os.getenv('ANU_LOGIN_PROMO_QUEUE_POLL_SECONDS', '3') or '3'),
        promo_send_interval_seconds=float(os.getenv('ANU_LOGIN_PROMO_SEND_INTERVAL_SECONDS', '1.0') or '1.0'),
        promo_retry_attempts=int(os.getenv('ANU_LOGIN_PROMO_RETRY_ATTEMPTS', '3') or '3'),
        promo_retry_backoff_seconds=int(os.getenv('ANU_LOGIN_PROMO_RETRY_BACKOFF_SECONDS', '30') or '30'),
        promo_queue_batch_size=int(os.getenv('ANU_LOGIN_PROMO_QUEUE_BATCH_SIZE', '25') or '25'),
        # Google Business Profile
        gmb_access_token=os.getenv('GMB_ACCESS_TOKEN', '').strip(),
        gmb_location_name=os.getenv('GMB_LOCATION_NAME', '').strip(),
    )


settings = load_settings()
