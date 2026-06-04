"""
Alembic migration: Add Journey Orchestration Tables
Creates: crm_journeys, crm_journey_instances, crm_journey_steps
Adds:    journey_instance_id column to crm_messages (crm_message_logs linkage)

Run:
  alembic upgrade head
  -- OR direct SQL (below) if running outside alembic context:
  docker exec pureleven-postgres psql -U pureleven -d pureleven -f /tmp/journeys_migration.sql
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    # ── 1. crm_journeys ─────────────────────────────────────────────────────
    op.create_table(
        "crm_journeys",
        sa.Column("id",                   sa.String(36), primary_key=True, nullable=False),
        sa.Column("name",                 sa.String(255), nullable=False),
        sa.Column("description",          sa.String(1000), nullable=True),
        sa.Column("segment_id",           sa.String(36), nullable=True),
        sa.Column("status",               sa.String(50), nullable=False, server_default="DRAFT"),
        sa.Column("entry_trigger",        sa.String(100), nullable=True),
        sa.Column("exit_criteria",        postgresql.JSON(), nullable=True),
        sa.Column("max_frequency_per_day",sa.Integer(), nullable=False, server_default="2"),
        sa.Column("n8n_workflow_id",      sa.String(50), nullable=True),
        sa.Column("template_json",        postgresql.JSON(), nullable=True),
        sa.Column("created_at",           sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",           sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.ForeignKeyConstraint(["segment_id"], ["crm_segments.id"], ondelete="SET NULL"),
    )

    # ── 2. crm_journey_instances ─────────────────────────────────────────────
    op.create_table(
        "crm_journey_instances",
        sa.Column("id",           sa.String(36), primary_key=True, nullable=False),
        sa.Column("journey_id",   sa.String(36), nullable=False),
        sa.Column("customer_id",  sa.String(36), nullable=False),
        sa.Column("email",        sa.String(255), nullable=True),
        sa.Column("status",       sa.String(50), nullable=False, server_default="ACTIVE"),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at",   sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("exit_reason",  sa.String(255), nullable=True),
        sa.Column("result_data",  postgresql.JSON(), nullable=True),
        sa.Column("created_at",   sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",   sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["journey_id"],  ["crm_journeys.id"],  ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["crm_customers.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("journey_id", "customer_id", name="uq_journey_customer_active"),
    )
    op.create_index("idx_ji_customer_status", "crm_journey_instances", ["customer_id", "status"])
    op.create_index("idx_ji_journey_status",  "crm_journey_instances", ["journey_id",  "status"])
    op.create_index("idx_ji_email",           "crm_journey_instances", ["email"])

    # ── 3. crm_journey_steps ─────────────────────────────────────────────────
    op.create_table(
        "crm_journey_steps",
        sa.Column("id",                  sa.String(36), primary_key=True, nullable=False),
        sa.Column("journey_instance_id", sa.String(36), nullable=False),
        sa.Column("step_index",          sa.Integer(), nullable=True),
        sa.Column("step_type",           sa.String(50), nullable=True),
        sa.Column("step_name",           sa.String(255), nullable=True),
        sa.Column("action_data",         postgresql.JSON(), nullable=True),
        sa.Column("scheduled_at",        sa.DateTime(), nullable=True),
        sa.Column("executed_at",         sa.DateTime(), nullable=True),
        sa.Column("status",              sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("result",              postgresql.JSON(), nullable=True),
        sa.Column("created_at",          sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["journey_instance_id"], ["crm_journey_instances.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_js_instance",  "crm_journey_steps", ["journey_instance_id"])
    op.create_index("idx_js_scheduled", "crm_journey_steps", ["scheduled_at", "status"])

    # ── 4. Backlink: add journey_instance_id to crm_messages ─────────────────
    op.add_column(
        "crm_messages",
        sa.Column("journey_instance_id", sa.String(36), nullable=True),
    )
    op.create_foreign_key(
        "fk_messages_journey_instance",
        "crm_messages", "crm_journey_instances",
        ["journey_instance_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("fk_messages_journey_instance", "crm_messages", type_="foreignkey")
    op.drop_column("crm_messages", "journey_instance_id")
    op.drop_index("idx_js_scheduled", table_name="crm_journey_steps")
    op.drop_index("idx_js_instance",  table_name="crm_journey_steps")
    op.drop_table("crm_journey_steps")
    op.drop_index("idx_ji_email",           table_name="crm_journey_instances")
    op.drop_index("idx_ji_journey_status",  table_name="crm_journey_instances")
    op.drop_index("idx_ji_customer_status", table_name="crm_journey_instances")
    op.drop_table("crm_journey_instances")
    op.drop_table("crm_journeys")


# ─── DIRECT SQL (use when running outside Alembic) ────────────────────────────
DIRECT_SQL = """
-- Run this file directly if Alembic is not configured:
--   docker exec pureleven-postgres psql -U pureleven -d pureleven < /tmp/journeys_migration.sql

CREATE TABLE IF NOT EXISTS crm_journeys (
    id                    VARCHAR(36)   PRIMARY KEY,
    name                  VARCHAR(255)  NOT NULL UNIQUE,
    description           VARCHAR(1000),
    segment_id            VARCHAR(36)   REFERENCES crm_segments(id) ON DELETE SET NULL,
    status                VARCHAR(50)   NOT NULL DEFAULT 'DRAFT',
    entry_trigger         VARCHAR(100),
    exit_criteria         JSONB,
    max_frequency_per_day INTEGER       NOT NULL DEFAULT 2,
    n8n_workflow_id       VARCHAR(50),
    template_json         JSONB,
    created_at            TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMP     NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm_journey_instances (
    id           VARCHAR(36)  PRIMARY KEY,
    journey_id   VARCHAR(36)  NOT NULL REFERENCES crm_journeys(id)  ON DELETE CASCADE,
    customer_id  VARCHAR(36)  NOT NULL REFERENCES crm_customers(id) ON DELETE CASCADE,
    email        VARCHAR(255),
    status       VARCHAR(50)  NOT NULL DEFAULT 'ACTIVE',
    current_step INTEGER      NOT NULL DEFAULT 0,
    started_at   TIMESTAMP    NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    exit_reason  VARCHAR(255),
    result_data  JSONB,
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_journey_customer_active UNIQUE (journey_id, customer_id)
);

CREATE INDEX IF NOT EXISTS idx_ji_customer_status ON crm_journey_instances (customer_id, status);
CREATE INDEX IF NOT EXISTS idx_ji_journey_status  ON crm_journey_instances (journey_id,  status);
CREATE INDEX IF NOT EXISTS idx_ji_email           ON crm_journey_instances (email);

CREATE TABLE IF NOT EXISTS crm_journey_steps (
    id                   VARCHAR(36)  PRIMARY KEY,
    journey_instance_id  VARCHAR(36)  NOT NULL REFERENCES crm_journey_instances(id) ON DELETE CASCADE,
    step_index           INTEGER,
    step_type            VARCHAR(50),
    step_name            VARCHAR(255),
    action_data          JSONB,
    scheduled_at         TIMESTAMP,
    executed_at          TIMESTAMP,
    status               VARCHAR(50)  NOT NULL DEFAULT 'PENDING',
    result               JSONB,
    created_at           TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_js_instance  ON crm_journey_steps (journey_instance_id);
CREATE INDEX IF NOT EXISTS idx_js_scheduled ON crm_journey_steps (scheduled_at, status);

ALTER TABLE crm_messages
    ADD COLUMN IF NOT EXISTS journey_instance_id VARCHAR(36)
        REFERENCES crm_journey_instances(id) ON DELETE SET NULL;
"""
