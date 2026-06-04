#!/usr/bin/env python3
"""
scripts/01_setup_wabis_webhooks.py

Register Pureleven's 4 WhatsApp tracking endpoints as webhooks with Wabis.
Wabis will call these URLs when customers interact with templates
(click, reply, call, unsubscribe).

Usage:
  cd anu-login/backend
  source .env  # or set env vars manually
  python scripts/01_setup_wabis_webhooks.py

Required env vars:
  WABIS_API_KEY      - From Wabis dashboard → Settings → API Keys
  WABIS_BASE_URL     - e.g. https://api.wabis.io  (default)
  PUBLIC_BASE_URL    - Your public server URL, e.g. https://xyz.loca.lt
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

# ─── Config ──────────────────────────────────────────────────────────────────

WABIS_API_KEY   = os.getenv("WABIS_API_KEY", "").strip()
WABIS_BASE_URL  = os.getenv("WABIS_BASE_URL", "https://api.wabis.io").rstrip("/")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

# Wabis event → our endpoint mapping
WEBHOOK_SUBSCRIPTIONS = [
    {
        "event":   "message.button_click",
        "url":     f"{PUBLIC_BASE_URL}/api/tracking/whatsapp-click",
        "label":   "Button Click Tracker",
    },
    {
        "event":   "message.reply",
        "url":     f"{PUBLIC_BASE_URL}/api/tracking/whatsapp-reply",
        "label":   "Reply / Conversation Tracker",
    },
    {
        "event":   "call.initiated",
        "url":     f"{PUBLIC_BASE_URL}/api/tracking/whatsapp-call",
        "label":   "WhatsApp Call Tracker",
    },
    {
        "event":   "message.unsubscribe",
        "url":     f"{PUBLIC_BASE_URL}/api/tracking/whatsapp-unsubscribe",
        "label":   "Unsubscribe Handler",
    },
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _post(path: str, body: dict) -> dict:
    url  = f"{WABIS_BASE_URL}{path}"
    data = json.dumps(body, ensure_ascii=True).encode()
    req  = urllib.request.Request(
        url, data=data,
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {WABIS_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        return {"error": exc.code, "detail": body_text}


def _get(path: str) -> dict | list:
    url = f"{WABIS_BASE_URL}{path}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {WABIS_API_KEY}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        return {"error": exc.code, "detail": body_text}


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    # Preflight checks
    errors = []
    if not WABIS_API_KEY:
        errors.append("WABIS_API_KEY is not set")
    if not PUBLIC_BASE_URL:
        errors.append("PUBLIC_BASE_URL is not set (e.g. https://your-tunnel.loca.lt)")
    if errors:
        print("❌  Missing required env vars:")
        for e in errors:
            print(f"    • {e}")
        sys.exit(1)

    print(f"\n🔗  Wabis base URL : {WABIS_BASE_URL}")
    print(f"🌐  Public base URL: {PUBLIC_BASE_URL}\n")

    # ── Step 1: List existing webhooks ────────────────────────────────────────
    print("── Existing webhooks ─────────────────────────────────────────────")
    existing = _get("/v1/webhooks")
    if isinstance(existing, list):
        if existing:
            for w in existing:
                print(f"  id={w.get('id','?')}  event={w.get('event','?')}  url={w.get('url','?')}")
        else:
            print("  (none registered)")
    else:
        print(f"  Could not list webhooks: {existing}")

    # ── Step 2: Register each webhook ─────────────────────────────────────────
    print("\n── Registering webhooks ──────────────────────────────────────────")
    results = []
    for sub in WEBHOOK_SUBSCRIPTIONS:
        payload = {
            "event": sub["event"],
            "url":   sub["url"],
            "label": sub["label"],
        }
        resp = _post("/v1/webhooks", payload)
        ok   = "error" not in resp
        icon = "✅" if ok else "❌"
        print(f"  {icon}  {sub['event']:35s}  →  {sub['url']}")
        if not ok:
            print(f"       Error: {resp}")
        results.append((sub["event"], ok))

    # ── Step 3: Summary ───────────────────────────────────────────────────────
    print("\n── Summary ───────────────────────────────────────────────────────")
    passed = sum(1 for _, ok in results if ok)
    total  = len(results)
    print(f"  {passed}/{total} webhooks registered successfully")

    if passed < total:
        print("\n  ⚠️   Some webhooks failed. Possible reasons:")
        print("        • Wabis webhook API path is different — check Wabis docs")
        print("        • PUBLIC_BASE_URL is not reachable from Wabis servers")
        print("        • API key doesn't have webhook management permissions")
        print("\n  📌  Manual fallback: Log into https://dashboard.wabis.io")
        print("        → Settings → Webhooks → Add Webhook")
        _print_manual_instructions()
    else:
        print("\n  🎉  All webhooks registered! Wabis will now call your endpoints")
        print("       on every customer interaction.\n")


def _print_manual_instructions() -> None:
    print("\n── Manual webhook URLs (copy into Wabis dashboard) ──────────────")
    for sub in WEBHOOK_SUBSCRIPTIONS:
        print(f"  Event : {sub['event']}")
        print(f"  URL   : {sub['url']}")
        print()


if __name__ == "__main__":
    main()
