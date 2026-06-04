"""
Pureleven CRM — Identity Graph + Multi-Touch Attribution Migration
Revision ID: 020_identity_attribution
Create Date: 2026-05-25

Deploy:
  scp alembic_migration_identity_attribution.py root@192.46.213.140:/tmp/
  ssh root@192.46.213.140 'docker cp /tmp/alembic_migration_identity_attribution.py pureleven-ai-engine:/tmp/ && docker exec pureleven-ai-engine python /tmp/alembic_migration_identity_attribution.py'
"""

import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("identity_attribution_migration")

try:
    import psycopg2
except ImportError:
    logger.error("psycopg2 not installed. Run this inside the ai-engine container.")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv("/app/.env", override=False)
    load_dotenv(override=False)
except Exception:
    pass

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
        logger.error("✗ %s: %s", label, str(exc).strip())
        raise


run("crm_customer_identities", """
CREATE TABLE IF NOT EXISTS crm_customer_identities (
    id VARCHAR(36) PRIMARY KEY,
    canonical_customer_id VARCHAR(36) NOT NULL REFERENCES crm_customers(id) ON DELETE CASCADE,
    identity_type VARCHAR(50) NOT NULL,
    identity_value VARCHAR(500) NOT NULL,
    identity_hash VARCHAR(64) NOT NULL,
    confidence_score DOUBLE PRECISION DEFAULT 1.0,
    source VARCHAR(100),
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)
""")
run("crm_customer_identities unique", "CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_identity_type_hash ON crm_customer_identities(identity_type, identity_hash)")
run("crm_customer_identities customer_type", "CREATE INDEX IF NOT EXISTS idx_customer_identity_customer_type ON crm_customer_identities(canonical_customer_id, identity_type)")
run("crm_customer_identities hash", "CREATE INDEX IF NOT EXISTS idx_customer_identity_hash ON crm_customer_identities(identity_hash)")

run("crm_identity_merge_history", """
CREATE TABLE IF NOT EXISTS crm_identity_merge_history (
    id VARCHAR(36) PRIMARY KEY,
    from_customer_id VARCHAR(36) REFERENCES crm_customers(id) ON DELETE SET NULL,
    to_customer_id VARCHAR(36) REFERENCES crm_customers(id) ON DELETE SET NULL,
    merge_method VARCHAR(50) NOT NULL,
    confidence_score DOUBLE PRECISION DEFAULT 1.0,
    matched_fields JSONB,
    reason VARCHAR(255),
    status VARCHAR(20) DEFAULT 'applied',
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    reversed_at TIMESTAMP
)
""")
run("crm_identity_merge_history to_status", "CREATE INDEX IF NOT EXISTS idx_identity_merge_to_status ON crm_identity_merge_history(to_customer_id, status)")
run("crm_identity_merge_history from", "CREATE INDEX IF NOT EXISTS idx_identity_merge_from ON crm_identity_merge_history(from_customer_id)")

run("crm_unresolved_order_refs", """
CREATE TABLE IF NOT EXISTS crm_unresolved_order_refs (
    id VARCHAR(36) PRIMARY KEY,
    raw_order_ref VARCHAR(100) NOT NULL,
    source VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    payload JSONB,
    resolution_status VARCHAR(30) DEFAULT 'unresolved',
    resolved_shopify_order_id VARCHAR(50),
    error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)
""")
run("crm_unresolved_order_refs ref", "CREATE INDEX IF NOT EXISTS idx_unresolved_order_ref ON crm_unresolved_order_refs(raw_order_ref)")
run("crm_unresolved_order_refs source_status", "CREATE INDEX IF NOT EXISTS idx_unresolved_order_source_status ON crm_unresolved_order_refs(source, resolution_status)")
run("crm_unresolved_order_refs contact", "CREATE INDEX IF NOT EXISTS idx_unresolved_order_contact ON crm_unresolved_order_refs(email, phone)")

run("crm_attribution_model_config", """
CREATE TABLE IF NOT EXISTS crm_attribution_model_config (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(80) UNIQUE NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    config JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)
""")
run("crm_attribution_model_config active", "CREATE INDEX IF NOT EXISTS idx_attribution_model_active ON crm_attribution_model_config(is_active)")

run("crm_order_touchpoint_attribution", """
CREATE TABLE IF NOT EXISTS crm_order_touchpoint_attribution (
    id VARCHAR(36) PRIMARY KEY,
    order_id VARCHAR(36) NOT NULL REFERENCES crm_orders(id) ON DELETE CASCADE,
    shopify_order_id VARCHAR(50),
    customer_id VARCHAR(36) REFERENCES crm_customers(id) ON DELETE SET NULL,
    touchpoint_event_id VARCHAR(36) REFERENCES crm_events(id) ON DELETE SET NULL,
    source VARCHAR(50) NOT NULL,
    campaign_id VARCHAR(100),
    campaign_name VARCHAR(255),
    gclid VARCHAR(255),
    fbclid VARCHAR(255),
    fbp VARCHAR(255),
    fbc VARCHAR(255),
    touch_type VARCHAR(30) NOT NULL,
    attribution_model VARCHAR(80) NOT NULL,
    model_version VARCHAR(20) DEFAULT 'v1',
    lookback_days INTEGER DEFAULT 30,
    attributed_value DOUBLE PRECISION DEFAULT 0.0,
    attributed_percentage DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW()
)
""")
run("crm_order_touchpoint_attribution unique", "CREATE UNIQUE INDEX IF NOT EXISTS uq_order_touchpoint_model ON crm_order_touchpoint_attribution(order_id, touchpoint_event_id, attribution_model)")
run("crm_order_touchpoint_attribution order_model", "CREATE INDEX IF NOT EXISTS idx_attr_order_model ON crm_order_touchpoint_attribution(order_id, attribution_model)")
run("crm_order_touchpoint_attribution customer_source", "CREATE INDEX IF NOT EXISTS idx_attr_customer_source ON crm_order_touchpoint_attribution(customer_id, source)")
run("crm_order_touchpoint_attribution shopify", "CREATE INDEX IF NOT EXISTS idx_attr_shopify_order_id ON crm_order_touchpoint_attribution(shopify_order_id)")

run("crm_audience_materialization_runs", """
CREATE TABLE IF NOT EXISTS crm_audience_materialization_runs (
    id VARCHAR(36) PRIMARY KEY,
    audience_key VARCHAR(100) NOT NULL,
    audience_type VARCHAR(50) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'started',
    record_count INTEGER DEFAULT 0,
    destination VARCHAR(50),
    details JSONB,
    started_at TIMESTAMP DEFAULT NOW(),
    finished_at TIMESTAMP
)
""")
run("crm_audience_materialization_runs key_started", "CREATE INDEX IF NOT EXISTS idx_audience_run_key_started ON crm_audience_materialization_runs(audience_key, started_at)")
run("crm_audience_materialization_runs status", "CREATE INDEX IF NOT EXISTS idx_audience_run_status ON crm_audience_materialization_runs(status)")

seed_rows = [
    ("position_based_40_20_40", "position_based", '{"first_pct":40,"last_pct":40,"middle_pct":20,"lookback_days":30}'),
    ("first_touch", "first_touch", '{"lookback_days":30}'),
    ("last_touch", "last_touch", '{"lookback_days":30}'),
    ("linear", "linear", '{"lookback_days":30}'),
]
for name, model_type, config_json in seed_rows:
    run(f"seed model {name}", f"""
    INSERT INTO crm_attribution_model_config (id, name, model_type, config, is_active, created_at, updated_at)
    VALUES (md5(random()::text || clock_timestamp()::text), '{name}', '{model_type}', '{config_json}'::jsonb, TRUE, NOW(), NOW())
    ON CONFLICT (name) DO NOTHING
    """)

cur.execute("""
SELECT table_name
FROM information_schema.tables
WHERE table_schema='public'
  AND table_name IN (
    'crm_customer_identities',
    'crm_identity_merge_history',
    'crm_unresolved_order_refs',
    'crm_attribution_model_config',
    'crm_order_touchpoint_attribution',
    'crm_audience_materialization_runs'
  )
ORDER BY table_name
""")
logger.info("Identity/attribution tables present: %s", [row[0] for row in cur.fetchall()])

cur.close()
conn.close()
logger.info("Identity + attribution migration complete")
