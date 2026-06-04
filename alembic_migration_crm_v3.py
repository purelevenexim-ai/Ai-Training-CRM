"""
Pureleven CRM — Database Migration v3
Phase 1-4 schema changes + Phase 9 tables.

Changes:
  crm_orders      → +review_email_sent, +repeat_email_sent, +replenishment_email_sent,
                     +winback_email_sent, +fraud_score, +capi_suppressed
  crm_events      → +n8n_notified (idempotent), +session_id (idempotent)
  NEW crm_ai_reviews      (Phase 9 AI ad review log)
  NEW crm_messages        (Email + WhatsApp outbound dedup log)
  NEW crm_automation_log  (N8N daily run audit trail)

Deploy:
  # Upload to server
  scp alembic_migration_crm_v3.py root@192.46.213.140:/tmp/

  # Run inside container
  sshpass -p 'QazPlm123!@#' ssh -o StrictHostKeyChecking=no root@192.46.213.140 \\
    'docker cp /tmp/alembic_migration_crm_v3.py pureleven-ai-engine:/tmp/ && \\
     docker exec pureleven-ai-engine python /tmp/alembic_migration_crm_v3.py'
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("migration_v3")

# ── Connection setup ──────────────────────────────────────────────────────────
try:
    import psycopg2
except ImportError:
    logger.error("psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

from dotenv import load_dotenv
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

logger.info("Connected: %s", os.getenv("POSTGRES_DB", "pureleven"))


def run(label: str, sql: str):
    try:
        cur.execute(sql)
        logger.info("✓  %s", label)
    except psycopg2.Error as e:
        err_msg = str(e).strip()
        if "already exists" in err_msg:
            logger.info("─  %s (already exists — skipped)", label)
        else:
            logger.error("✗  %s: %s", label, err_msg)


# ══════════════════════════════════════════════════════════════════════════════
# 1. crm_orders — Phase 1 fraud/dedup + Phase 2 email lifecycle flags
# ══════════════════════════════════════════════════════════════════════════════
run("crm_orders: fraud_score",
    "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS fraud_score INTEGER DEFAULT 0")
run("crm_orders: capi_suppressed",
    "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS capi_suppressed BOOLEAN DEFAULT FALSE")
run("crm_orders: review_email_sent",
    "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS review_email_sent BOOLEAN DEFAULT FALSE")
run("crm_orders: repeat_email_sent",
    "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS repeat_email_sent BOOLEAN DEFAULT FALSE")
run("crm_orders: replenishment_email_sent",
    "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS replenishment_email_sent BOOLEAN DEFAULT FALSE")
run("crm_orders: winback_email_sent",
    "ALTER TABLE crm_orders ADD COLUMN IF NOT EXISTS winback_email_sent BOOLEAN DEFAULT FALSE")

# ══════════════════════════════════════════════════════════════════════════════
# 2. crm_events — ensure session_id + n8n_notified (may exist from v2)
# ══════════════════════════════════════════════════════════════════════════════
run("crm_events: session_id column",
    "ALTER TABLE crm_events ADD COLUMN IF NOT EXISTS session_id VARCHAR(255)")
run("crm_events: n8n_notified column",
    "ALTER TABLE crm_events ADD COLUMN IF NOT EXISTS n8n_notified BOOLEAN DEFAULT FALSE")
run("crm_events: idx_session_id",
    "CREATE INDEX IF NOT EXISTS idx_events_session_id ON crm_events(session_id)")

# ══════════════════════════════════════════════════════════════════════════════
# 3. crm_ai_reviews — Phase 9 AI-powered ad review log
# ══════════════════════════════════════════════════════════════════════════════
run("crm_ai_reviews: create table", """
    CREATE TABLE IF NOT EXISTS crm_ai_reviews (
        id                   VARCHAR(36) PRIMARY KEY,
        review_date          TIMESTAMP,
        review_type          VARCHAR(50),
        metrics_json         JSONB,
        ai_analysis_json     JSONB,
        email_sent           BOOLEAN DEFAULT FALSE,
        approval_status      VARCHAR(20) DEFAULT 'pending',
        approval_id          VARCHAR(100),
        approval_timestamp   TIMESTAMP,
        execution_status     VARCHAR(20),
        executed_timestamp   TIMESTAMP,
        adjustments_executed INTEGER DEFAULT 0,
        created_at           TIMESTAMP DEFAULT NOW()
    )
""")
run("crm_ai_reviews: idx_review_date",
    "CREATE INDEX IF NOT EXISTS idx_ai_reviews_date ON crm_ai_reviews(review_date)")

# ══════════════════════════════════════════════════════════════════════════════
# 4. crm_messages — Email / WhatsApp outbound dedup log
# ══════════════════════════════════════════════════════════════════════════════
run("crm_messages: create table", """
    CREATE TABLE IF NOT EXISTS crm_messages (
        id              VARCHAR(36) PRIMARY KEY,
        customer_id     VARCHAR(36) REFERENCES crm_customers(id) ON DELETE SET NULL,
        customer_email  VARCHAR(255),
        customer_phone  VARCHAR(20),
        channel         VARCHAR(50),
        template_id     VARCHAR(100),
        status          VARCHAR(20),
        response_code   INTEGER,
        sent_at         TIMESTAMP,
        created_at      TIMESTAMP DEFAULT NOW()
    )
""")
run("crm_messages: unique constraint email+template",
    "ALTER TABLE crm_messages ADD CONSTRAINT uq_message_customer_template UNIQUE (customer_email, template_id)")
run("crm_messages: idx_channel_date",
    "CREATE INDEX IF NOT EXISTS idx_messages_channel_date ON crm_messages(channel, sent_at)")
run("crm_messages: idx_email",
    "CREATE INDEX IF NOT EXISTS idx_messages_email ON crm_messages(customer_email)")

# ══════════════════════════════════════════════════════════════════════════════
# 5. crm_automation_log — N8N daily workflow audit trail
# ══════════════════════════════════════════════════════════════════════════════
run("crm_automation_log: create table", """
    CREATE TABLE IF NOT EXISTS crm_automation_log (
        id            VARCHAR(36) PRIMARY KEY,
        run_date      TIMESTAMP,
        workflow_name VARCHAR(100),
        sequences_run INTEGER DEFAULT 0,
        total_sent    INTEGER DEFAULT 0,
        failures      INTEGER DEFAULT 0,
        status        VARCHAR(20),
        details_json  JSONB,
        created_at    TIMESTAMP DEFAULT NOW()
    )
""")
run("crm_automation_log: idx_run_date",
    "CREATE INDEX IF NOT EXISTS idx_automation_log_date ON crm_automation_log(run_date)")

# ══════════════════════════════════════════════════════════════════════════════
# 6. Verification summary
# ══════════════════════════════════════════════════════════════════════════════
cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name IN (
          'crm_ai_reviews', 'crm_messages', 'crm_automation_log',
          'crm_orders', 'crm_customers', 'crm_events'
      )
    ORDER BY 1
""")
tables = [r[0] for r in cur.fetchall()]
logger.info("Tables present: %s", tables)

cur.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'crm_orders'
      AND column_name IN (
          'review_email_sent', 'repeat_email_sent',
          'replenishment_email_sent', 'winback_email_sent',
          'fraud_score', 'capi_suppressed'
      )
    ORDER BY 1
""")
cols = [r[0] for r in cur.fetchall()]
logger.info("crm_orders v3 columns present: %s", cols)

cur.close()
conn.close()
logger.info("Migration v3 complete ✓")
