import importlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("GA4_MEASUREMENT_ID", "G-TEST123")
os.environ.setdefault("GA4_API_SECRET", "test-secret")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

crm_routes = importlib.import_module("crm_routes")


def paid_shopify_order(**overrides):
    order = {
        "id": 12345,
        "email": "buyer@example.com",
        "financial_status": "paid",
        "total_price": "1299.00",
        "currency": "INR",
        "created_at": "2026-05-24T10:30:00Z",
        "billing_address": {"phone": "+91 9876543210"},
        "shipping_address": {"city": "Kochi", "zip": "682001"},
        "customer": {"phone": "+91 9876543210"},
        "line_items": [
            {
                "id": 1,
                "product_id": 9001,
                "variant_id": 8001,
                "title": "Kerala Cardamom",
                "price": "1299.00",
                "quantity": 1,
            }
        ],
        "_gclid": "test-gclid",
        "_fbclid": "test-fbclid",
    }
    order.update(overrides)
    return order


def test_clean_paid_order_is_approved_for_conversion_fanout():
    order = paid_shopify_order()

    assert crm_routes.calculate_fraud_score(order) == 0
    assert crm_routes.should_send_to_capi(order) == (True, "approved")


def test_missing_identity_and_shipping_data_is_sent_with_risk_flag():
    order = paid_shopify_order(
        email=None,
        billing_address={},
        customer={},
        shipping_address={},
        _gclid=None,
        _fbclid=None,
    )

    assert crm_routes.calculate_fraud_score(order) == 65
    assert crm_routes.should_send_to_capi(order) == (
        True,
        "approved_with_risk_fraud_score_65",
    )


def test_click_attribution_prevents_missing_optional_fields_from_suppressing_order():
    order = paid_shopify_order(
        email=None,
        billing_address={},
        customer={},
        shipping_address={},
    )

    assert crm_routes.calculate_fraud_score(order) == 30
    assert crm_routes.should_send_to_capi(order) == (True, "approved")


def test_internal_email_is_never_sent_to_conversion_destinations():
    order = paid_shopify_order(email="test@pureleven.com")

    assert crm_routes.should_send_to_capi(order) == (False, "internal_email")


def test_meta_capi_fanout_normalizes_purchase_payload(monkeypatch):
    captured = {}

    class FakeMetaCapi:
        @staticmethod
        def send_purchase(**kwargs):
            captured.update(kwargs)
            return {"events_received": 1}

    monkeypatch.setattr(crm_routes, "_meta_capi", lambda: FakeMetaCapi)
    monkeypatch.setattr(crm_routes, "_update_capi_status", lambda order_id, result: None)

    crm_routes.fire_meta_capi(
        paid_shopify_order(),
        client_ip="203.0.113.10",
        user_agent="pytest-agent",
    )

    assert captured["order_id"] == "12345"
    assert captured["value"] == 1299.0
    assert captured["currency"] == "INR"
    assert captured["email"] == "buyer@example.com"
    assert captured["phone"] == "+91 9876543210"
    assert captured["client_ip"] == "203.0.113.10"
    assert captured["client_user_agent"] == "pytest-agent"
    assert captured["fbclid"] == "test-fbclid"
    assert captured["items"] == [
        {
            "id": "8001",
            "quantity": 1,
            "item_price": 1299.0,
            "title": "Kerala Cardamom",
        }
    ]


def test_google_ads_fanout_passes_click_and_enhanced_conversion_fields(monkeypatch):
    captured = {}

    class FakeGoogleAds:
        @staticmethod
        def upload_purchase_conversion(**kwargs):
            captured.update(kwargs)
            return {"ok": True}

    monkeypatch.setattr(crm_routes, "_gads", lambda: FakeGoogleAds)

    crm_routes.fire_google_conversion(paid_shopify_order())

    assert captured["gclid"] == "test-gclid"
    assert captured["order_id"] == "12345"
    assert captured["value"] == 1299.0
    assert captured["currency"] == "INR"
    assert captured["email"] == "buyer@example.com"
    assert captured["phone"] == "+91 9876543210"
    assert captured["order_date"] == datetime(2026, 5, 24, 10, 30, tzinfo=timezone.utc)


def test_ga4_purchase_payload_uses_ga_client_id_when_available(monkeypatch):
    requests = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    def fake_urlopen(request, timeout):
        requests.append(request)
        return FakeResponse()

    monkeypatch.setenv("GA4_MEASUREMENT_ID", "G-TEST123")
    monkeypatch.setenv("GA4_API_SECRET", "test-secret")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    order = paid_shopify_order(ga_client_id="1234567890.1710000000")

    crm_routes.fire_ga4_purchase(order)

    assert len(requests) == 1
    payload = json.loads(requests[0].data.decode())
    assert payload["client_id"] == "1234567890.1710000000"
    assert payload["events"][0]["name"] == "purchase"
    assert payload["events"][0]["params"]["transaction_id"] == "12345"
    assert payload["events"][0]["params"]["value"] == 1299.0
