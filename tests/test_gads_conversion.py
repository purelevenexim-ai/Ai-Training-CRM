from datetime import datetime, timezone
from types import SimpleNamespace

import gads_conversion as gads


ENV_NAMES = (
    "GOOGLE_ADS_DEVELOPER_TOKEN",
    "GADS_DEVELOPER_TOKEN",
    "GOOGLE_ADS_CLIENT_ID",
    "GADS_OAUTH_CLIENT_ID",
    "GOOGLE_ADS_CLIENT_SECRET",
    "GADS_OAUTH_CLIENT_SECRET",
    "GOOGLE_ADS_REFRESH_TOKEN",
    "GADS_OAUTH_REFRESH_TOKEN",
    "GOOGLE_ADS_CUSTOMER_ID",
    "GADS_CUSTOMER_ID",
    "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
    "GADS_LOGIN_CUSTOMER_ID",
    "GOOGLE_ADS_PURCHASE_CONVERSION_ACTION_ID",
    "GOOGLE_ADS_CONVERSION_ACTION_ID",
    "GADS_PURCHASE_CONVERSION_ACTION_ID",
    "GADS_CONVERSION_ACTION_ID",
    "GOOGLE_ADS_COD_DELIVERED_CONVERSION_ACTION_ID",
    "GADS_COD_DELIVERED_CONVERSION_ACTION_ID",
)


def _set_base_env(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "dev-token")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setenv("GOOGLE_ADS_CUSTOMER_ID", "149-516-3260")
    monkeypatch.setenv("GOOGLE_ADS_CONVERSION_ACTION_ID", "7658758254")


class FakeConversion:
    def __init__(self):
        self.user_identifiers = []


class FakeUploadService:
    def __init__(self, response=None):
        self.response = response or SimpleNamespace(
            partial_failure_error=SimpleNamespace(code=0, message=""),
            results=[SimpleNamespace()],
        )
        self.calls = []

    def upload_click_conversions(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeClient:
    def __init__(self, upload_service):
        self.upload_service = upload_service

    def get_service(self, name):
        assert name == "ConversionUploadService"
        return self.upload_service

    def get_type(self, name):
        if name == "ClickConversion":
            return FakeConversion()
        if name == "UserIdentifier":
            return SimpleNamespace(hashed_email="", hashed_phone_number="")
        raise AssertionError(name)


def test_purchase_upload_uses_real_account_action_and_google_datetime(monkeypatch):
    _set_base_env(monkeypatch)
    upload_service = FakeUploadService()
    monkeypatch.setattr(gads, "_get_google_ads_client", lambda: FakeClient(upload_service))

    result = gads.upload_purchase_conversion(
        gclid="test-gclid",
        order_id="12345",
        value=1299,
        currency="inr",
        order_date=datetime(2026, 9, 8, 9, 30, tzinfo=timezone.utc),
        email=" Buyer@Example.com ",
        phone="9876543210",
    )

    assert result["ok"] is True
    assert result["customer_id"] == "1495163260"
    assert result["conversion_action_id"] == "7658758254"
    assert result["click_id_type"] == "gclid"

    call = upload_service.calls[0]
    assert call["customer_id"] == "1495163260"
    assert call["partial_failure"] is True
    conversion = call["conversions"][0]
    assert conversion.conversion_action == (
        "customers/1495163260/conversionActions/7658758254"
    )
    assert conversion.gclid == "test-gclid"
    assert conversion.conversion_date_time == "2026-09-08 09:30:00+00:00"
    assert "T" not in conversion.conversion_date_time
    assert conversion.conversion_value == 1299.0
    assert conversion.currency_code == "INR"
    assert conversion.order_id == "12345"
    assert len(conversion.user_identifiers) == 2


def test_wbraid_is_supported_and_only_one_click_identifier_is_sent(monkeypatch):
    _set_base_env(monkeypatch)
    upload_service = FakeUploadService()
    monkeypatch.setattr(gads, "_get_google_ads_client", lambda: FakeClient(upload_service))

    result = gads.upload_purchase_conversion(
        wbraid="test-wbraid",
        order_id="12345",
        value=450,
        order_date="2026-09-08T09:30:00+05:30",
    )

    assert result["ok"] is True
    assert result["click_id_type"] == "wbraid"
    conversion = upload_service.calls[0]["conversions"][0]
    assert conversion.wbraid == "test-wbraid"
    assert not hasattr(conversion, "gclid")
    assert not hasattr(conversion, "gbraid")


def test_legacy_gads_environment_names_still_work(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GADS_DEVELOPER_TOKEN", "dev-token")
    monkeypatch.setenv("GADS_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("GADS_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GADS_OAUTH_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setenv("GADS_CUSTOMER_ID", "1491516326")
    monkeypatch.setenv("GADS_CONVERSION_ACTION_ID", "7658758254")

    assert gads._configuration_errors("purchase") == []
    assert gads._customer_id() == "1491516326"
    assert gads._conversion_action_id("purchase") == "7658758254"


def test_non_purchase_event_never_falls_back_to_purchase_action(monkeypatch):
    _set_base_env(monkeypatch)

    assert gads._conversion_action_id("cod_delivered") == ""
    errors = gads._configuration_errors("cod_delivered")
    assert "missing_conversion_action_id_for_cod_delivered" in errors

    monkeypatch.setenv(
        "GOOGLE_ADS_COD_DELIVERED_CONVERSION_ACTION_ID", "8888888888"
    )
    assert gads._conversion_action_id("cod_delivered") == "8888888888"


def test_missing_click_identifier_is_a_recordable_failure(monkeypatch):
    _set_base_env(monkeypatch)

    result = gads.upload_purchase_conversion(
        order_id="12345",
        value=450,
        order_date="2026-09-08T09:30:00+05:30",
        email="buyer@example.com",
    )

    assert result["error"] == "missing_google_click_identifier"
    assert result["order_id"] == "12345"


def test_partial_failure_is_returned_as_error_for_crm_logging(monkeypatch):
    _set_base_env(monkeypatch)
    upload_service = FakeUploadService(
        response=SimpleNamespace(
            partial_failure_error=SimpleNamespace(
                code=3, message="The imported conversion has invalid data."
            ),
            results=[],
        )
    )
    monkeypatch.setattr(gads, "_get_google_ads_client", lambda: FakeClient(upload_service))

    result = gads.upload_purchase_conversion(
        gclid="test-gclid",
        order_id="12345",
        value=450,
        order_date="2026-09-08T09:30:00+05:30",
    )

    assert result["error"] == "google_ads_partial_failure"
    assert "invalid data" in result["details"]


def test_invalid_or_missing_datetime_does_not_reach_google(monkeypatch):
    _set_base_env(monkeypatch)
    upload_service = FakeUploadService()
    monkeypatch.setattr(gads, "_get_google_ads_client", lambda: FakeClient(upload_service))

    result = gads.upload_purchase_conversion(
        gclid="test-gclid",
        order_id="12345",
        value=450,
        order_date=None,
    )

    assert result["error"] == "missing_or_invalid_conversion_datetime"
    assert upload_service.calls == []
