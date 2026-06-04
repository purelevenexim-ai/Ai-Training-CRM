"""
celery_app.py

Celery application for Pureleven background jobs.

Broker:  Redis (pureleven-redis:6379/0)
Backend: Redis (pureleven-redis:6379/1)

Tasks:
  app.tasks.profile_rebuild  — sync customer metrics from crm_orders nightly
"""
from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.getenv("REDIS_URL", "redis://pureleven-redis:6379")

app = Celery("pureleven")

app.conf.broker_url = f"{REDIS_URL}/0"
app.conf.result_backend = f"{REDIS_URL}/1"
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.timezone = "UTC"
app.conf.enable_utc = True

# Auto-discover tasks in app.tasks.*
app.conf.include = [
    "app.tasks.profile_rebuild",
]

# ── Beat schedule (periodic tasks) ────────────────────────────────────────────

app.conf.beat_schedule = {
    # Rebuild all customer metrics nightly at 03:00 UTC
    "rebuild-all-profiles-nightly": {
        "task": "app.tasks.profile_rebuild.rebuild_all_profiles",
        "schedule": crontab(hour=3, minute=0),
    },
}
