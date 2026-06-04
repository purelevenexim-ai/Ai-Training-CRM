#!/usr/bin/env python3
"""
Continuous production validator for server-side tracking.

Usage:
  python scripts/production_tracking_validation.py \
    --base-url https://track.pureleven.com \
    --admin-secret basil

Recommended cron (every 15 minutes):
  */15 * * * * /usr/bin/python3 /opt/pureleven/ai-engine/app/scripts/production_tracking_validation.py \
      --base-url https://track.pureleven.com --admin-secret basil
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://track.pureleven.com")
    parser.add_argument("--admin-secret", required=True)
    parser.add_argument("--health-hours", type=int, default=24)
    parser.add_argument("--alert-hours", type=int, default=6)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    qs_health = urllib.parse.urlencode({"admin_secret": args.admin_secret, "hours": args.health_hours})
    qs_alerts = urllib.parse.urlencode({"admin_secret": args.admin_secret, "hours": args.alert_hours})

    health_url = f"{base}/api/crm/admin/tracking/health?{qs_health}"
    alerts_url = f"{base}/api/crm/admin/tracking/alerts?{qs_alerts}"

    try:
        health = get_json(health_url)
        alerts = get_json(alerts_url)
    except urllib.error.HTTPError as exc:
        print(f"VALIDATION_HTTP_ERROR status={exc.code} url={exc.geturl()}")
        return 2
    except Exception as exc:
        print(f"VALIDATION_RUNTIME_ERROR error={exc}")
        return 3

    summary = (health or {}).get("summary", {})
    severity = (alerts or {}).get("severity", "ok")
    total = int(summary.get("total", 0) or 0)
    failed = int(summary.get("failed", 0) or 0)

    print("TRACKING_VALIDATION")
    print(json.dumps({
        "health_window_hours": args.health_hours,
        "alert_window_hours": args.alert_hours,
        "total_events": total,
        "failed_events": failed,
        "alert_severity": severity,
        "alerts": (alerts or {}).get("alerts", []),
    }, ensure_ascii=True))

    if severity == "critical":
        return 10
    if total == 0:
        return 11
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
