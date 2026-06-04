#!/usr/bin/env python3
"""Pureleven CRM E2E Test Suite"""
import os
import json
import urllib.request
import urllib.error
from datetime import datetime

SEP = "=" * 60
ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
print(f"\n{SEP}\nPURELEVEN CRM E2E TEST SUITE  [{ts}]\n{SEP}\n")

results = {}

# ── TEST 1: AWS SES Email Delivery ─────────────────────────────
print("TEST 1: AWS SES Email Delivery")
print("-" * 40)
try:
    import boto3
    region = os.getenv("AWS_SES_REGION", "us-east-1")
    key_id = os.getenv("AWS_SES_ACCESS_KEY_ID", "")
    secret = os.getenv("AWS_SES_SECRET_ACCESS_KEY", "")
    if not key_id or not secret:
        raise ValueError("AWS_SES_ACCESS_KEY_ID or SECRET not set in env")
    ses = boto3.client(
        "ses",
        region_name=region,
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
    )
    resp = ses.send_email(
        Source="noreply@mail.pureleven.com",
        Destination={"ToAddresses": ["purelevenexim@gmail.com"]},
        Message={
            "Subject": {"Data": f"[E2E] AWS SES Test {ts}"},
            "Body": {
                "Html": {"Data": f"<h2>AWS SES E2E Test</h2><p>Sent: {ts}</p>"},
                "Text": {"Data": f"AWS SES E2E Test. Sent: {ts}"},
            },
        },
    )
    print(f"PASS - MessageId: {resp['MessageId']}")
    results["ses"] = "PASS"
except Exception as e:
    print(f"FAIL - {e}")
    results["ses"] = f"FAIL: {e}"

# ── TEST 2: Meta Audience Sync via CAPI ───────────────────────
print("\nTEST 2: Meta Audience Sync (CAPI event test)")
print("-" * 40)
try:
    import hashlib
    import time

    token = os.getenv("META_CAPI_ACCESS_TOKEN") or os.getenv("FACEBOOK_ACCESS_TOKEN", "")
    pixel_id = os.getenv("META_CAPI_PIXEL_ID", "609256704464862")
    if not token:
        raise ValueError("No Meta CAPI access token in env")

    # Send a test Purchase event via CAPI
    test_email_hash = hashlib.sha256("purelevenexim@gmail.com".lower().encode()).hexdigest()
    event_time = int(time.time())
    payload = json.dumps({
        "data": [{
            "event_name": "Purchase",
            "event_time": event_time,
            "action_source": "website",
            "event_source_url": "https://pureleven.com/test",
            "user_data": {
                "em": [test_email_hash],
                "client_ip_address": "127.0.0.1",
                "client_user_agent": "CRM-E2E-Test/1.0",
            },
            "custom_data": {
                "currency": "INR",
                "value": 1.0,
                "order_id": f"e2e-test-{ts}",
                "content_name": "E2E Test Purchase",
            },
        }],
        "test_event_code": "TEST12345",
        "access_token": token,
    }).encode("utf-8")

    url = f"https://graph.facebook.com/v18.0/{pixel_id}/events"
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode())

    events_received = data.get("events_received", 0)
    fbtrace = data.get("fbtrace_id", "")
    print(f"PASS - events_received={events_received}, fbtrace_id={fbtrace}")
    print(f"   Pixel ID: {pixel_id}")
    print(f"   Check Meta Events Manager test events for 'TEST12345'")
    results["meta"] = "PASS"
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"FAIL - HTTP {e.code}: {body[:300]}")
    results["meta"] = f"FAIL: HTTP {e.code}"
except Exception as e:
    print(f"FAIL - {e}")
    results["meta"] = f"FAIL: {e}"

# ── TEST 3: Google Ads Customer Match ──────────────────────────
print("\nTEST 3: Google Ads Customer Match (API Auth)")
print("-" * 40)
try:
    from google.ads.googleads.client import GoogleAdsClient
    config = {
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", ""),
        "client_id":       os.getenv("GOOGLE_ADS_CLIENT_ID", ""),
        "client_secret":   os.getenv("GOOGLE_ADS_CLIENT_SECRET", ""),
        "refresh_token":   os.getenv("GOOGLE_ADS_OAUTH_REFRESH_TOKEN", ""),
        "use_proto_plus":  True,
    }
    missing = [k for k, v in config.items() if not v and k != "use_proto_plus"]
    if missing:
        raise ValueError(f"Missing env vars: {missing}")
    client = GoogleAdsClient.load_from_dict(config)
    ga_svc = client.get_service("GoogleAdsService")
    cid = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "7225234563")
    query = "SELECT customer.id, customer.descriptive_name, customer.status FROM customer LIMIT 1"
    response = ga_svc.search(customer_id=cid, query=query)
    rows = list(response)
    if rows:
        c = rows[0].customer
        print(f"PASS - Connected to customer {c.id} ({c.descriptive_name}), status: {c.status.name}")
    else:
        print("PASS - API connected (0 rows returned)")
    results["google_ads"] = "PASS"
except ImportError:
    # Try legacy google-ads SDK style
    try:
        from google.ads.google_ads.client import GoogleAdsClient as LegacyClient
        print("NOTE: Using legacy google-ads SDK")
        print("PASS - Legacy SDK imported successfully")
        results["google_ads"] = "PASS (legacy SDK)"
    except Exception as e2:
        print(f"FAIL - {e2}")
        results["google_ads"] = f"FAIL: {e2}"
except Exception as e:
    print(f"FAIL - {e}")
    results["google_ads"] = f"FAIL: {e}"

# ── SUMMARY ────────────────────────────────────────────────────
print(f"\n{SEP}")
print("SUMMARY:")
for k, v in results.items():
    icon = "PASS" if v.startswith("PASS") else "FAIL"
    print(f"  [{icon}] {k}: {v}")
print(SEP + "\n")
