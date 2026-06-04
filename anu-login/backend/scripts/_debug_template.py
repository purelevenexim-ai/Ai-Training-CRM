#!/usr/bin/env python3
"""Debug a specific template by submitting it and printing the full error."""
import json
import os
import urllib.error
import urllib.request

token = os.environ["META_ACCESS_TOKEN"].strip()
waba_id = os.environ["WHATSAPP_BUSINESS_ACCOUNT_ID"].strip()
TRACK_URL = "https://www.delhivery.com/track/package"
REVIEW_URL = "https://g.page/r/pureleven/review"
STORE_URL = "https://pureleven.com"

tests = [
    # Test 1: delivery_begun_v1 - fixed (no emoji in QUICK_REPLY, simple example)
    {
        "name": "delivery_begun_v1",
        "category": "UTILITY",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Your Pureleven spices are on the way! \U0001f69a\n\n"
                    "Hi {{1}},\nWaybill: {{2}}\nETA: {{3}}\n\nTrack live below"
                ),
                "example": {"body_text": [["Priya", "AWB123456", "May 22"]]},
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Track Live",
                        "url": f"{TRACK_URL}/{{{{1}}}}",
                        "example": ["AWB123456"],
                    },
                    {"type": "QUICK_REPLY", "text": "Got it!"},
                ],
            },
        ],
    },
    # Test 2: delivered_review_request_v1 - fixed (no trailing var, no emoji in button)
    {
        "name": "delivered_review_request_v1_test",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Your Pureleven spices have arrived! \U0001f60a\n\n"
                    "Hi {{1}}, how's the aroma and quality?\n"
                    "Your 1-minute review helps other customers "
                    "discover authentic Kerala spices. "
                    "Review here: {{2}}"
                ),
                "example": {
                    "body_text": [["Priya", f"{REVIEW_URL}?utm_source=whatsapp"]],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Write Review",
                        "url": f"{REVIEW_URL}?utm_source=whatsapp",
                    },
                    {"type": "QUICK_REPLY", "text": "Love it!"},
                    {"type": "QUICK_REPLY", "text": "Ask Question"},
                ],
            },
        ],
    },
]

for tmpl in tests:
    name = tmpl["name"]
    url = f"https://graph.facebook.com/v20.0/{waba_id}/message_templates"
    data = json.dumps(tmpl, ensure_ascii=True).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
            result = json.loads(resp.read())
            print(f"SUCCESS [{name}]: {result}")
    except urllib.error.HTTPError as exc:
        print(f"FAILED  [{name}]: {exc.read().decode()}")
    print()
