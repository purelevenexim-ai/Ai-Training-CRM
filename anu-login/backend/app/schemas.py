from __future__ import annotations

from datetime import datetime, timezone
import re

from pydantic import BaseModel, ConfigDict, Field, model_validator


LOCAL_IN_MOBILE_RE = re.compile(r'^[6-9]\d{9}$')
E164_MOBILE_RE = re.compile(r'^\+[1-9]\d{7,14}$')


def normalize_lead_phone(value: str | None) -> str | None:
    raw_phone = (value or '').strip()

    if not raw_phone:
        return None

    digits_only = ''.join(character for character in raw_phone if character.isdigit())

    if raw_phone.startswith('+'):
        normalized_phone = f'+{digits_only}'

        if not E164_MOBILE_RE.fullmatch(normalized_phone):
            raise ValueError('Enter a valid mobile number. Use a 10 digit Indian mobile number or full international format.')

        return normalized_phone

    if LOCAL_IN_MOBILE_RE.fullmatch(digits_only):
        return f'+91{digits_only}'

    if digits_only.startswith('91') and len(digits_only) == 12 and LOCAL_IN_MOBILE_RE.fullmatch(digits_only[2:]):
        return f'+{digits_only}'

    if digits_only.startswith('0') and len(digits_only) == 11 and LOCAL_IN_MOBILE_RE.fullmatch(digits_only[1:]):
        return f'+91{digits_only[1:]}'

    raise ValueError('Enter a valid mobile number. Use a 10 digit Indian mobile number or full international format.')


class LeadCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source: str = Field(min_length=1, max_length=120)
    provider: str = Field(default='manual', max_length=50)
    name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    consent: bool
    page_type: str | None = Field(default=None, max_length=60)
    page_url: str | None = Field(default=None, max_length=500)
    customer_id: str | None = Field(default=None, max_length=80)
    cart_item_count: int = Field(default=0, ge=0)
    cart_total_cents: int = Field(default=0, ge=0)
    captured_at: datetime | None = None

    @model_validator(mode='after')
    def normalize_contact_fields(self) -> 'LeadCreate':
        self.name = (self.name or '').strip() or None
        self.email = (self.email or '').strip() or None
        self.phone = normalize_lead_phone(self.phone)
        return self

    @model_validator(mode='after')
    def ensure_required_contact_fields(self) -> 'LeadCreate':
        if not self.phone:
            raise ValueError('Phone number is required.')

        return self

    @model_validator(mode='after')
    def set_capture_time(self) -> 'LeadCreate':
        if self.captured_at is None:
            self.captured_at = datetime.now(timezone.utc)
        return self


class LeadRecord(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: int
    source: str
    provider: str
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    consent: bool
    page_type: str | None = None
    page_url: str | None = None
    customer_id: str | None = None
    cart_item_count: int = 0
    cart_total_cents: int = 0
    coupon_code: str
    captured_at: datetime
    created_at: datetime


class LeadCreateResponse(BaseModel):
    status: str = 'success'
    coupon_code: str
    lead: LeadRecord


class LeadEmailCaptureRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=160)

    @model_validator(mode='after')
    def normalize_contact_fields(self) -> 'LeadEmailCaptureRequest':
        self.phone = normalize_lead_phone(self.phone)
        self.email = (self.email or '').strip().lower() or None
        return self

    @model_validator(mode='after')
    def ensure_required_contact_fields(self) -> 'LeadEmailCaptureRequest':
        if not self.phone:
            raise ValueError('Phone number is required.')

        if not self.email:
            raise ValueError('Email is required.')

        return self


class LeadListResponse(BaseModel):
    total: int
    items: list[LeadRecord]


class ShopifyConnectionPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    shop_domain: str = Field(min_length=1, max_length=255)
    access_token: str = Field(min_length=1)


class ShopifyConnectionStatus(BaseModel):
    connected: bool = False
    shop_domain: str = ''


class GoogleAdminSettings(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    enabled: bool = False
    client_id: str = ''
    one_tap_enabled: bool = True


class OtpAdminSettings(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    enabled: bool = False
    firebase_api_key: str = ''
    firebase_auth_domain: str = ''
    firebase_project_id: str = ''
    firebase_app_id: str = ''
    firebase_messaging_sender_id: str = ''
    service_account_json: str = ''


class TruecallerAdminSettings(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    enabled: bool = False
    client_id: str = ''
    client_secret: str = ''
    partner_name: str = 'PureLeven'
    button_text: str = 'Continue with Truecaller'
    sdk_script_url: str = ''
    start_url: str = ''
    verification_mode: str = 'mobile_web'


class AdminFeatureSettings(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email_enabled: bool = True
    widget_enabled: bool = True
    auto_shopify_sync: bool = False
    export_enabled: bool = True


class BasilCheckoutSettings(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    enabled: bool = True
    program_label: str = 'Basil Checkout'
    free_delivery_threshold: int = Field(default=649, ge=0)
    gift_threshold: int = Field(default=1449, ge=0)
    delivery_value: int = Field(default=80, ge=0)
    gift_value: int = Field(default=200, ge=0)
    delivery_label: str = 'Free delivery'
    gift_label: str = 'Free gift'
    complete_label: str = 'Rewards unlocked'
    rewards_heading: str = 'Your rewards'
    rewards_copy: str = 'Track delivery and gift checkpoints as your cart grows.'
    upsell_heading: str = 'Add a best-seller'
    upsell_copy: str = 'Small add-ons that move you closer to the next reward.'
    delivery_unlocked_toast: str = 'Free delivery unlocked'
    gift_unlocked_toast: str = 'Gift unlocked'
    add_to_cart_toast: str = 'Cart updated'


class AdminSettings(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    coupon_code: str = 'PL10OFF'
    privacy_policy_url: str = ''
    terms_of_service_url: str = ''
    support_email: str = ''
    google: GoogleAdminSettings = Field(default_factory=GoogleAdminSettings)
    otp: OtpAdminSettings = Field(default_factory=OtpAdminSettings)
    truecaller: TruecallerAdminSettings = Field(default_factory=TruecallerAdminSettings)
    features: AdminFeatureSettings = Field(default_factory=AdminFeatureSettings)
    basil_checkout: BasilCheckoutSettings = Field(default_factory=BasilCheckoutSettings)


class GooglePublicSettings(BaseModel):
    enabled: bool = False
    preview_only: bool = False
    client_id: str = ''
    one_tap_enabled: bool = False


class OtpPublicSettings(BaseModel):
    enabled: bool = False
    preview_only: bool = False
    firebase_api_key: str = ''
    firebase_auth_domain: str = ''
    firebase_project_id: str = ''
    firebase_app_id: str = ''
    firebase_messaging_sender_id: str = ''


class TruecallerPublicSettings(BaseModel):
    enabled: bool = False
    preview_only: bool = False
    button_text: str = 'Continue with Truecaller'
    sdk_script_url: str = ''
    start_url: str = ''
    verification_mode: str = 'mobile_web'


class ProviderPublicSettings(BaseModel):
    google: GooglePublicSettings = Field(default_factory=GooglePublicSettings)
    otp: OtpPublicSettings = Field(default_factory=OtpPublicSettings)
    truecaller: TruecallerPublicSettings = Field(default_factory=TruecallerPublicSettings)
    email_enabled: bool = True


class PublicSettingsResponse(BaseModel):
    coupon_code: str = 'PL10OFF'
    privacy_policy_url: str = ''
    terms_of_service_url: str = ''
    providers: ProviderPublicSettings = Field(default_factory=ProviderPublicSettings)
    basil_checkout: BasilCheckoutSettings = Field(default_factory=BasilCheckoutSettings)


class AdminDashboardResponse(BaseModel):
    total_leads: int = 0
    today_leads: int = 0
    provider_breakdown: dict[str, int] = Field(default_factory=dict)


class ProviderAuthBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    consent: bool
    page_type: str | None = Field(default=None, max_length=60)
    page_url: str | None = Field(default=None, max_length=500)
    customer_id: str | None = Field(default=None, max_length=80)
    cart_item_count: int = Field(default=0, ge=0)
    cart_total_cents: int = Field(default=0, ge=0)
    name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=40)


class GoogleAuthRequest(ProviderAuthBase):
    credential: str = Field(min_length=1)
    client_id: str = ''


class OtpAuthRequest(ProviderAuthBase):
    firebase_token: str = Field(min_length=1)


class TruecallerAuthRequest(ProviderAuthBase):
    verification_token: str | None = None
    request_nonce: str | None = None

    @model_validator(mode='after')
    def ensure_contact_details(self) -> 'TruecallerAuthRequest':
        if not self.request_nonce and not self.phone and not self.email:
            raise ValueError('Truecaller verification requires a phone number or email payload.')
        return self


class TruecallerStartRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    page_type: str | None = Field(default=None, max_length=60)
    page_url: str | None = Field(default=None, max_length=500)


class TruecallerStartResponse(BaseModel):
    request_id: str
    launch_url: str
    status_url: str
    expires_in_seconds: int = 15


class TruecallerCallbackPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='allow', populate_by_name=True)

    request_id: str = Field(alias='requestId', min_length=8, max_length=64)
    access_token: str | None = Field(default=None, alias='accessToken')
    endpoint: str | None = None
    status: str | None = None


class TruecallerRequestRecord(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    request_id: str
    status: str = 'created'
    profile_endpoint: str | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    phone_country_code: str | None = None
    error_message: str | None = None
    raw_callback: dict[str, object] | None = None
    raw_profile: dict[str, object] | None = None
    created_at: datetime
    updated_at: datetime


class TruecallerRequestStatusResponse(BaseModel):
    request_id: str
    status: str = 'created'
    verified: bool = False
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    phone_country_code: str | None = None
    message: str | None = None
    updated_at: datetime


# ─── Basil Commerce OS — Phase 1 schemas ──────────────────────────────────────

class EventTrackRequest(BaseModel):
    """Payload sent by basil-cart.js to the event gateway."""
    model_config = ConfigDict(str_strip_whitespace=True)

    event_name:  str       = Field(min_length=1, max_length=100)
    event_id:    str | None = Field(default=None, max_length=80)
    shop_domain: str | None = Field(default=None, max_length=200)
    customer_id: str | None = Field(default=None, max_length=80)
    session_id:  str | None = Field(default=None, max_length=80)
    cart_token:  str | None = Field(default=None, max_length=80)
    page_url:    str | None = Field(default=None, max_length=500)
    timestamp:   str | None = None
    user_agent:  str | None = Field(default=None, max_length=300)
    # Flexible event data (items, value, currency, etc.)
    currency:    str | None = Field(default='INR', max_length=10)
    value:       float | None = None
    num_items:   int | None = None


class EventTrackResponse(BaseModel):
    status:   str  # "queued" | "duplicate"
    event_id: str
    message:  str = ''
