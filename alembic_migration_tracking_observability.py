"""
Pureleven CRM — Tracking observability migration

Adds:
- Attribution enrichment columns on crm_orders/crm_customers (gbraid, wbraid, fbp, fbc, utm_content, utm_term)
- Paid-order risk marker (conversion_risk_reason)
- Destination-specific delivery status fields for Meta/Google/GA4
- tracking_events table for per-destination delivery logs

Run:
  docker cp alembic_migration_tracking_observability.py pureleven-ai-engine:/tmp/
  docker exec pureleven-ai-engine python /tmp/alembic_migration_tracking_observability.py
"""

import os
import logging

import psycopg2
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("tracking_observability_migration")

load_dotenv("/app/.env", override=False)
load_dotenv(override=False)

DB_DSN = (
    f"postgresql://{os.getenv('POSTGRES_USER', 'pureleven')}:"
    f"{os.getenv('POSTGRES_PASSWORD', '')}@"
    f"{os.getenv('POSTGRES_HOST', 'pureleven-postgres')}:"
    f"{os.getenv('POSTGRES_PORT', '5432')}/"
    f"{os.getenv('POSTGRES_DB', 'pureleven')}"
)


conn = psycopg2.connect(DB_DSN)
conn.autocommit = True
cur = conn.cursor()


def run(label: str, sql: str) -> None:
    try:
        cur.execute(sql)
        logger.info("✓ %s", label)
    except psycopg2.Error as exc:
        err = str(exc).strip()
        if "already exists" in err:
            logger.info("- %s (already exists)", label)
        else:
            logger.error("✗ %s: %s", label, err)


# crm_customers attribution columns
run("crm_customers.gbraid", "ALTER TABLE crm_customers ADD COLUMN IF NOT EXISTS gbraid VARCHAR(255)")
run("crm_customers.wbraid", "ALTER TABLE crm_customers ADD COLUMN IF NOT EXISTS wbraid VARCHAR(255)")
run("crm_customers.fbp", "ALTER TABLE crm_customers ADD COLUMN IF NOT EXISTS fbp VARCHAR(255)")
run("crm_customers.fbc", "ALTER TABLE crm_customers ADD COLUMN IF NOT EXISTS fbc VARCHAR(255)")

# crm_orders attribution + observability columns
run("crm_orders.gbraid", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS gbraid VARCHAR(255)")
run("crm_orders.wbraid", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS wbraid VARCHAR(255)")
run("crm_orders.fbp", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS fbp VARCHAR(255)")
run("crm_orders.fbc", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS fbc VARCHAR(255)")
run("crm_orders.utm_content", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS utm_content VARCHAR(255)")
run("crm_orders.utm_term", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS utm_term VARCHAR(255)")
run("crm_orders.conversion_risk_reason", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS conversion_risk_reason VARCHAR(255)")

run("crm_orders.meta_event_id", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS meta_event_id VARCHAR(100)")
run("crm_orders.meta_status", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS meta_status VARCHAR(20)")
run("crm_orders.meta_sent_at", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS meta_sent_at TIMESTAMP")
run("crm_orders.meta_response", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS meta_response TEXT")
run("crm_orders.meta_error", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS meta_error TEXT")

run("crm_orders.google_status", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS google_status VARCHAR(20)")
run("crm_orders.google_sent_at", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS google_sent_at TIMESTAMP")
run("crm_orders.google_response", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS google_response TEXT")
run("crm_orders.google_error", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS google_error TEXT")

run("crm_orders.ga4_status", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS ga4_status VARCHAR(20)")
run("crm_orders.ga4_sent_at", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS ga4_sent_at TIMESTAMP")
run("crm_orders.ga4_response", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS ga4_response TEXT")
run("crm_orders.ga4_error", "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS ga4_error TEXT")

# Indexes
run("idx_order_gbraid", "CREATE INDEX IF NOT EXISTS idx_order_gbraid ON crm_orders(gbraid)")
run("idx_order_wbraid", "CREATE INDEX IF NOT EXISTS idx_order_wbraid ON crm_orders(wbraid)")
run("idx_customer_gbraid", "CREATE INDEX IF NOT EXISTS idx_customer_gbraid ON crm_customers(gbraid)")
run("idx_customer_wbraid", "CREATE INDEX IF NOT EXISTS idx_customer_wbraid ON crm_customers(wbraid)")

# tracking_events table
run(
    "tracking_events table",
    """
    CREATE TABLE IF NOT EXISTS tracking_events (
        id VARCHAR(36) PRIMARY KEY,
        order_id VARCHAR(50) NOT NULL,
        destination VARCHAR(20) NOT NULL,
        event_name VARCHAR(100) NOT NULL,
        event_id VARCHAR(100),
        status VARCHAR(20) NOT NULL,
        response_code INTEGER,
        response_body TEXT,
        error TEXT,
        attempt INTEGER,
        created_at TIMESTAMP DEFAULT NOW()
    )
    """,
)
run("idx_tracking_events_order_destination", "CREATE INDEX IF NOT EXISTS idx_tracking_events_order_destination ON tracking_events(order_id, destination)")
run("idx_tracking_events_status_created", "CREATE INDEX IF NOT EXISTS idx_tracking_events_status_created ON tracking_events(status, created_at)")

cur.close()
conn.close()
logger.info("Tracking observability migration complete")
