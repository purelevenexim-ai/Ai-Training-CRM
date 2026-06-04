from __future__ import annotations

import csv
import json
import logging
import re
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timezone
from io import StringIO

from app.config import settings
from app.schemas import (
    AdminSettings,
    LeadCreate,
    LeadRecord,
    PublicSettingsResponse,
    ShopifyConnectionPayload,
    ShopifyConnectionStatus,
    TruecallerRequestRecord,
)


logger = logging.getLogger(__name__)
SHOPIFY_CONNECTION_KEY = 'shopify_connection'
TRUECALLER_REQUEST_MAX_AGE_SECONDS = 15


def _get_setting_value(setting_key: str) -> str | None:
    with get_connection() as connection:
        row = connection.execute(
            'SELECT setting_value FROM app_settings WHERE setting_key = ?',
            (setting_key,),
        ).fetchone()

    return row['setting_value'] if row is not None else None


def _save_setting_value(setting_key: str, setting_value: str) -> None:
    updated_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        connection.execute(
            '''
            INSERT INTO app_settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                updated_at = excluded.updated_at
            ''',
            (setting_key, setting_value, updated_at),
        )


def _serialize_json(value: dict[str, object] | None) -> str | None:
    if value is None:
        return None

    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _deserialize_json(value: str | None) -> dict[str, object] | None:
    if not value:
        return None

    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return None

    return payload if isinstance(payload, dict) else None


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(settings.database_path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


# Alias used by basil routes
get_db_connection = get_connection


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row[1]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def _ensure_column(connection: sqlite3.Connection, table_name: str, col_def: str) -> None:
    col_name = col_def.split()[0]
    if col_name in _table_columns(connection, table_name):
        return
    try:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_def}")
    except Exception:
        pass


def _ensure_campaign_sends_compat(connection: sqlite3.Connection) -> None:
    """Normalize legacy campaign_sends table to support phase-2 schema writes."""
    if not _table_exists(connection, 'campaign_sends'):
        return

    for col_def in [
        'id TEXT',
        'customer_id TEXT',
        'customer_email TEXT',
        "channel TEXT NOT NULL DEFAULT 'email'",
        'template_id TEXT',
        'subject_rendered TEXT',
        'body_rendered TEXT',
        'scheduled_at TEXT',
        'error_reason TEXT',
        'message_id TEXT',
    ]:
        _ensure_column(connection, 'campaign_sends', col_def)

    cols = _table_columns(connection, 'campaign_sends')

    if 'id' in cols:
        if 'send_id' in cols:
            connection.execute(
                "UPDATE campaign_sends SET id = send_id WHERE (id IS NULL OR id = '') AND send_id IS NOT NULL"
            )
        connection.execute(
            "UPDATE campaign_sends SET id = lower(hex(randomblob(16))) WHERE id IS NULL OR id = ''"
        )

    if 'customer_email' in cols and 'email' in cols:
        connection.execute(
            "UPDATE campaign_sends SET customer_email = email WHERE (customer_email IS NULL OR customer_email = '') AND email IS NOT NULL"
        )

    if 'sent_at' in cols and 'created_at' in cols:
        connection.execute(
            "UPDATE campaign_sends SET sent_at = created_at WHERE sent_at IS NULL AND created_at IS NOT NULL"
        )

    if 'status' in cols:
        connection.execute(
            "UPDATE campaign_sends SET status = 'queued' WHERE status IS NULL OR status = ''"
        )

def init_database() -> None:
    with get_connection() as connection:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                provider TEXT NOT NULL,
                name TEXT,
                email TEXT,
                phone TEXT,
                consent INTEGER NOT NULL,
                page_type TEXT,
                page_url TEXT,
                customer_id TEXT,
                cart_item_count INTEGER NOT NULL DEFAULT 0,
                cart_total_cents INTEGER NOT NULL DEFAULT 0,
                coupon_code TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone)')
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            '''
        )
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS truecaller_requests (
                request_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                profile_endpoint TEXT,
                name TEXT,
                email TEXT,
                phone TEXT,
                phone_country_code TEXT,
                error_message TEXT,
                raw_callback TEXT,
                raw_profile TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            '''
        )
        connection.execute(
            'CREATE INDEX IF NOT EXISTS idx_truecaller_requests_updated_at ON truecaller_requests(updated_at DESC)'
        )
        # ── Basil Commerce OS Phase 1 tables ─────────────────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS event_logs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id     TEXT UNIQUE,
                shop_domain  TEXT,
                session_id   TEXT,
                customer_id  TEXT,
                cart_token   TEXT,
                event_name   TEXT NOT NULL,
                event_source TEXT NOT NULL DEFAULT 'browser_pixel',
                event_data   TEXT,
                meta_sent    INTEGER NOT NULL DEFAULT 0,
                ga4_sent     INTEGER NOT NULL DEFAULT 0,
                retry_count  INTEGER NOT NULL DEFAULT 0,
                last_error   TEXT,
                ip_address   TEXT,
                created_at   TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_event_logs_created_at ON event_logs(created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_event_logs_event_name ON event_logs(event_name)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_event_logs_cart_token ON event_logs(cart_token)')
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS feature_flags (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_domain         TEXT NOT NULL,
                flag_name           TEXT NOT NULL,
                enabled             INTEGER NOT NULL DEFAULT 0,
                rollout_percentage  INTEGER NOT NULL DEFAULT 100,
                created_at          TEXT NOT NULL,
                updated_at          TEXT NOT NULL,
                UNIQUE(shop_domain, flag_name)
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_feature_flags_shop ON feature_flags(shop_domain)')

        # ── Phase 2: checkout_sessions ────────────────────────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS checkout_sessions (
                id                  TEXT PRIMARY KEY,
                shop_domain         TEXT NOT NULL,
                cart_token          TEXT,
                external_session_id TEXT,
                customer_id         TEXT,
                pincode             TEXT,
                cod_enabled         INTEGER NOT NULL DEFAULT 0,
                eta_label           TEXT,
                shipping_paise      INTEGER NOT NULL DEFAULT 0,
                address_json        TEXT,
                status              TEXT NOT NULL DEFAULT 'initiated',
                shopify_order_id    TEXT,
                created_at          TEXT NOT NULL,
                updated_at          TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_checkout_sessions_shop ON checkout_sessions(shop_domain, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_checkout_sessions_cart ON checkout_sessions(cart_token)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_checkout_sessions_status ON checkout_sessions(status)')

        # ── Phase 3: business_rules ───────────────────────────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS business_rules (
                id               TEXT PRIMARY KEY,
                shop_domain      TEXT NOT NULL,
                rule_name        TEXT NOT NULL,
                priority         INTEGER NOT NULL DEFAULT 0,
                conditions_json  TEXT NOT NULL DEFAULT '[]',
                actions_json     TEXT NOT NULL DEFAULT '[]',
                match_all        INTEGER NOT NULL DEFAULT 1,
                deleted          INTEGER NOT NULL DEFAULT 0,
                created_at       TEXT NOT NULL,
                updated_at       TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_business_rules_shop ON business_rules(shop_domain, deleted, priority DESC)')

        # ── Phase 3: experiments + assignments + results ──────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS experiments (
                id             TEXT PRIMARY KEY,
                shop_domain    TEXT NOT NULL,
                name           TEXT NOT NULL,
                description    TEXT,
                variants_json  TEXT NOT NULL DEFAULT '[]',
                goal_event     TEXT NOT NULL DEFAULT 'purchase',
                status         TEXT NOT NULL DEFAULT 'running',
                created_at     TEXT NOT NULL,
                updated_at     TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_experiments_shop ON experiments(shop_domain, status)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS experiment_assignments (
                id              TEXT PRIMARY KEY,
                experiment_id   TEXT NOT NULL,
                session_id      TEXT NOT NULL,
                user_id         TEXT,
                variant         TEXT NOT NULL,
                created_at      TEXT NOT NULL,
                UNIQUE(experiment_id, session_id)
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_exp_assign_exp ON experiment_assignments(experiment_id, variant)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS experiment_results (
                id              TEXT PRIMARY KEY,
                experiment_id   TEXT NOT NULL,
                session_id      TEXT NOT NULL,
                variant         TEXT NOT NULL,
                event_name      TEXT NOT NULL,
                value           REAL NOT NULL DEFAULT 0,
                created_at      TEXT NOT NULL,
                UNIQUE(experiment_id, session_id, event_name)
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_exp_results_exp ON experiment_results(experiment_id, variant)')

        # ── Phase 4: customer_profiles + identity_graph ───────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS customer_profiles (
                id                    TEXT PRIMARY KEY,
                shop_domain           TEXT NOT NULL,
                shopify_customer_id   TEXT,
                email_hash            TEXT,
                email_masked          TEXT,
                name                  TEXT,
                phone                 TEXT,
                source                TEXT NOT NULL DEFAULT 'web',
                traits_json           TEXT NOT NULL DEFAULT '{}',
                created_at            TEXT NOT NULL,
                updated_at            TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_profiles_shop ON customer_profiles(shop_domain, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_profiles_email_hash ON customer_profiles(email_hash)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_profiles_shopify_id ON customer_profiles(shopify_customer_id)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS customer_identity_graph (
                id              TEXT PRIMARY KEY,
                profile_id      TEXT NOT NULL,
                shop_domain     TEXT NOT NULL,
                identity_type   TEXT NOT NULL,
                identity_value  TEXT NOT NULL,
                created_at      TEXT NOT NULL,
                UNIQUE(shop_domain, identity_type, identity_value)
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_identity_graph_profile ON customer_identity_graph(profile_id)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_identity_graph_lookup ON customer_identity_graph(shop_domain, identity_type, identity_value)')

        # ── Phase 5: WhatsApp Journey tables ─────────────────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS journey_customers (
                id                          TEXT PRIMARY KEY,
                shop_domain                 TEXT NOT NULL,
                phone                       TEXT NOT NULL,
                name                        TEXT,
                email                       TEXT,
                shopify_customer_id         TEXT,
                shopify_order_id            TEXT,
                -- Delivery
                waybill_id                  TEXT,
                delivery_status             TEXT NOT NULL DEFAULT 'pending',
                delivered_at                TEXT,
                estimated_delivery_at       TEXT,
                order_value_paise           INTEGER NOT NULL DEFAULT 0,
                -- Journey stage
                journey_stage               TEXT NOT NULL DEFAULT 'order_confirmed',
                journey_started_at          TEXT NOT NULL,
                -- Per-day sent flags
                day1_sent                   INTEGER NOT NULL DEFAULT 0,
                day1_sent_at                TEXT,
                day2_sent                   INTEGER NOT NULL DEFAULT 0,
                day2_sent_at                TEXT,
                day2_engagement_status      TEXT,
                day5_sent                   INTEGER NOT NULL DEFAULT 0,
                day5_sent_at                TEXT,
                day5_engagement_status      TEXT,
                day15_sent                  INTEGER NOT NULL DEFAULT 0,
                day15_sent_at               TEXT,
                day15_engagement_status     TEXT,
                review_coupon_code          TEXT,
                review_coupon_expires_at    TEXT,
                day30_sent                  INTEGER NOT NULL DEFAULT 0,
                day30_sent_at               TEXT,
                day30_engagement_status     TEXT,
                day30_product_recommended   TEXT,
                day60_sent                  INTEGER NOT NULL DEFAULT 0,
                day60_sent_at               TEXT,
                day60_engagement_status     TEXT,
                day75_sent                  INTEGER NOT NULL DEFAULT 0,
                day75_sent_at               TEXT,
                day95_sent                  INTEGER NOT NULL DEFAULT 0,
                day95_sent_at               TEXT,
                -- Engagement
                engagement_score            REAL NOT NULL DEFAULT 0.0,
                last_engagement_at          TEXT,
                is_responsive               INTEGER NOT NULL DEFAULT 0,
                do_not_message              INTEGER NOT NULL DEFAULT 0,
                whatsapp_subscription_status TEXT NOT NULL DEFAULT 'subscribed',
                -- Reviews
                google_review_status        TEXT NOT NULL DEFAULT 'not_submitted',
                -- RFM / Segment
                customer_segment            TEXT NOT NULL DEFAULT 'new',
                total_spent_paise           INTEGER NOT NULL DEFAULT 0,
                purchase_count              INTEGER NOT NULL DEFAULT 0,
                last_purchase_at            TEXT,
                -- Meta
                created_at                  TEXT NOT NULL,
                updated_at                  TEXT NOT NULL,
                UNIQUE(shop_domain, shopify_order_id)
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_journey_customers_phone ON journey_customers(shop_domain, phone)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_journey_customers_stage ON journey_customers(shop_domain, journey_stage, do_not_message)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_journey_customers_delivery ON journey_customers(waybill_id)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_journey_customers_segment ON journey_customers(shop_domain, customer_segment)')

        # Email columns — added as ALTER TABLE so existing DBs are not broken
        for _col, _ddl in [
            ("email_address",      "TEXT"),
            ("do_not_email",       "INTEGER NOT NULL DEFAULT 0"),
            ("unsubscribe_token",  "TEXT"),
        ]:
            try:
                connection.execute(f"ALTER TABLE journey_customers ADD COLUMN {_col} {_ddl}")
            except Exception:
                pass  # Column already exists — safe to ignore

        # Cross-platform tracking columns used by the root CRM identity graph bridge.
        for _col, _ddl in [
            ("gclid", "TEXT"),
            ("gbraid", "TEXT"),
            ("wbraid", "TEXT"),
            ("fbclid", "TEXT"),
            ("fbp", "TEXT"),
            ("fbc", "TEXT"),
            ("ga_client_id", "TEXT"),
            ("ga_session_id", "TEXT"),
            ("utm_source", "TEXT"),
            ("utm_medium", "TEXT"),
            ("utm_campaign", "TEXT"),
            ("utm_content", "TEXT"),
            ("utm_term", "TEXT"),
        ]:
            try:
                connection.execute(f"ALTER TABLE journey_customers ADD COLUMN {_col} {_ddl}")
            except Exception:
                pass
        connection.execute('CREATE INDEX IF NOT EXISTS idx_journey_customers_gclid ON journey_customers(gclid)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_journey_customers_fbclid ON journey_customers(fbclid)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_journey_customers_fbp ON journey_customers(fbp)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS journey_messages (
                id              TEXT PRIMARY KEY,
                customer_id     TEXT NOT NULL,
                template_name   TEXT NOT NULL,
                journey_stage   TEXT NOT NULL,
                wabis_message_id TEXT,
                delivery_status TEXT NOT NULL DEFAULT 'sent',
                variables_json  TEXT NOT NULL DEFAULT '{}',
                sent_at         TEXT NOT NULL,
                created_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_journey_messages_customer ON journey_messages(customer_id, sent_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_journey_messages_template ON journey_messages(template_name, sent_at DESC)')

        # Email send tracking columns on journey_messages
        for _col, _ddl in [
            ("email_status",  "TEXT"),
            ("email_sent_at", "TEXT"),
        ]:
            try:
                connection.execute(f"ALTER TABLE journey_messages ADD COLUMN {_col} {_ddl}")
            except Exception:
                pass  # Column already exists — safe to ignore

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS whatsapp_message_status_events (
                id                  TEXT PRIMARY KEY,
                message_id          TEXT NOT NULL,
                recipient_phone     TEXT,
                status              TEXT NOT NULL,
                template_name       TEXT,
                error_code          TEXT,
                error_title         TEXT,
                error_detail        TEXT,
                raw_payload_json    TEXT NOT NULL DEFAULT '{}',
                created_at          TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_whatsapp_status_mid ON whatsapp_message_status_events(message_id, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_whatsapp_status_phone ON whatsapp_message_status_events(recipient_phone, created_at DESC)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS journey_engagement_events (
                id              TEXT PRIMARY KEY,
                customer_id     TEXT NOT NULL,
                event_type      TEXT NOT NULL,
                template_name   TEXT,
                journey_stage   TEXT,
                points_awarded  REAL NOT NULL DEFAULT 0.0,
                metadata_json   TEXT NOT NULL DEFAULT '{}',
                created_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_journey_engagement_customer ON journey_engagement_events(customer_id, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_journey_engagement_type ON journey_engagement_events(event_type, created_at DESC)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS delivery_tracking (
                id                  TEXT PRIMARY KEY,
                waybill_id          TEXT NOT NULL,
                shop_domain         TEXT NOT NULL,
                shopify_order_id    TEXT,
                customer_phone      TEXT,
                status_code         INTEGER NOT NULL,
                status_label        TEXT NOT NULL,
                location            TEXT,
                event_timestamp     TEXT,
                raw_payload_json    TEXT,
                created_at          TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_delivery_tracking_waybill ON delivery_tracking(waybill_id, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_delivery_tracking_order ON delivery_tracking(shopify_order_id)')

        # ── Phase AI: Shopify catalog (synced from API, no hallucination) ─────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS shopify_products (
                id                  TEXT PRIMARY KEY,
                shopify_product_id  TEXT UNIQUE NOT NULL,
                title               TEXT NOT NULL,
                description         TEXT,
                price               REAL NOT NULL DEFAULT 0,
                compare_at_price    REAL,
                tags                TEXT,
                collections         TEXT,
                featured_image_url  TEXT,
                images_json         TEXT NOT NULL DEFAULT '[]',
                rating              REAL,
                review_count        INTEGER NOT NULL DEFAULT 0,
                top_review_text     TEXT,
                top_reviewer_name   TEXT,
                harvest_region      TEXT,
                harvest_date        TEXT,
                quality_notes       TEXT,
                best_for_uses       TEXT,
                flavor_pairing      TEXT,
                cooking_tip         TEXT,
                synced_at           TEXT NOT NULL,
                created_at          TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_shopify_products_synced ON shopify_products(synced_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_shopify_products_tags ON shopify_products(tags)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS shopify_inventory (
                id          TEXT PRIMARY KEY,
                product_id  TEXT NOT NULL REFERENCES shopify_products(id) ON DELETE CASCADE,
                variant_id  TEXT,
                size_label  TEXT,
                quantity    INTEGER NOT NULL DEFAULT 0,
                status      TEXT NOT NULL DEFAULT 'unknown',
                updated_at  TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_shopify_inventory_product ON shopify_inventory(product_id)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS shopify_offers (
                id                  TEXT PRIMARY KEY,
                code                TEXT UNIQUE NOT NULL,
                discount_type       TEXT NOT NULL DEFAULT 'percentage',
                discount_value      REAL NOT NULL,
                valid_from          TEXT,
                valid_until         TEXT,
                applicable_products TEXT NOT NULL DEFAULT '[]',
                max_uses            INTEGER,
                uses_so_far         INTEGER NOT NULL DEFAULT 0,
                is_active           INTEGER NOT NULL DEFAULT 1,
                synced_at           TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_shopify_offers_active ON shopify_offers(is_active, valid_until)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS shopify_content (
                id              TEXT PRIMARY KEY,
                content_type    TEXT NOT NULL,
                title           TEXT NOT NULL,
                body            TEXT NOT NULL,
                product_tags    TEXT NOT NULL DEFAULT '[]',
                published_at    TEXT,
                source_url      TEXT,
                synced_at       TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_shopify_content_type ON shopify_content(content_type, synced_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_shopify_content_tags ON shopify_content(product_tags)')

        # ── Phase AI: Story templates (human-approved, AI uses to render) ─────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS ai_story_templates (
                id              TEXT PRIMARY KEY,
                story_type      TEXT NOT NULL,
                product_category TEXT NOT NULL DEFAULT 'all',
                template_text   TEXT NOT NULL,
                required_fields TEXT NOT NULL DEFAULT '[]',
                approved        INTEGER NOT NULL DEFAULT 1,
                version         INTEGER NOT NULL DEFAULT 1,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_story_templates_type ON ai_story_templates(story_type, approved)')

        # ── Phase AI: 24-hour conversation sessions ───────────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                id                  TEXT PRIMARY KEY,
                customer_id         TEXT NOT NULL,
                customer_phone      TEXT NOT NULL,
                shop_domain         TEXT NOT NULL,
                trigger_template    TEXT NOT NULL,
                trigger_product_id  TEXT,
                session_start       TEXT NOT NULL,
                session_expires     TEXT NOT NULL,
                is_active           INTEGER NOT NULL DEFAULT 1,
                messages_sent       INTEGER NOT NULL DEFAULT 0,
                converted           INTEGER NOT NULL DEFAULT 0,
                conversion_product_id TEXT,
                conversion_amount   REAL,
                created_at          TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_conv_sessions_phone ON conversation_sessions(customer_phone, is_active)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_conv_sessions_expires ON conversation_sessions(session_expires, is_active)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id              TEXT PRIMARY KEY,
                session_id      TEXT NOT NULL REFERENCES conversation_sessions(id),
                turn_number     INTEGER NOT NULL,
                actor           TEXT NOT NULL,
                customer_text   TEXT,
                ai_decision_json TEXT,
                message_rendered TEXT,
                message_type    TEXT,
                delivery_status TEXT NOT NULL DEFAULT 'pending',
                created_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_conv_messages_session ON conversation_messages(session_id, turn_number)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS conversation_followups (
                id              TEXT PRIMARY KEY,
                session_id      TEXT NOT NULL REFERENCES conversation_sessions(id),
                message_type    TEXT NOT NULL,
                message_content TEXT NOT NULL,
                product_id      TEXT,
                scheduled_at    TEXT NOT NULL,
                sent            INTEGER NOT NULL DEFAULT 0,
                sent_at         TEXT,
                clicked         INTEGER NOT NULL DEFAULT 0,
                clicked_at      TEXT,
                created_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_followups_session ON conversation_followups(session_id)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_followups_scheduled ON conversation_followups(scheduled_at, sent)')

        # ── Phase AI: Behavioral learning (what works per segment) ────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS product_affinity_scores (
                id                      TEXT PRIMARY KEY,
                customer_id             TEXT NOT NULL,
                product_id              TEXT NOT NULL,
                affinity_score          REAL NOT NULL DEFAULT 0.0,
                last_recommended_at     TEXT,
                recommendation_count    INTEGER NOT NULL DEFAULT 0,
                click_count             INTEGER NOT NULL DEFAULT 0,
                purchase_count          INTEGER NOT NULL DEFAULT 0,
                best_message_type       TEXT,
                best_send_hour          INTEGER,
                updated_at              TEXT NOT NULL,
                UNIQUE(customer_id, product_id)
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_affinity_customer ON product_affinity_scores(customer_id, affinity_score DESC)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS segment_message_performance (
                id              TEXT PRIMARY KEY,
                segment         TEXT NOT NULL,
                message_type    TEXT NOT NULL,
                template_name   TEXT,
                send_count      INTEGER NOT NULL DEFAULT 0,
                click_count     INTEGER NOT NULL DEFAULT 0,
                conversion_count INTEGER NOT NULL DEFAULT 0,
                avg_conversion_hour REAL,
                updated_at      TEXT NOT NULL,
                UNIQUE(segment, message_type)
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_segment_perf_seg ON segment_message_performance(segment, message_type)')

        # ── Phase AI: Monitoring alerts log ───────────────────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS monitoring_alerts (
                id          TEXT PRIMARY KEY,
                alert_type  TEXT NOT NULL,
                severity    TEXT NOT NULL DEFAULT 'info',
                message     TEXT NOT NULL,
                resolved    INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_created ON monitoring_alerts(created_at DESC, resolved)')

        # ── Test Journey Logging ──────────────────────────────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS test_journey_log (
                id                          TEXT PRIMARY KEY,
                customer_id                 TEXT,
                phone                       TEXT NOT NULL,
                journey_type                TEXT NOT NULL,
                message_stage               TEXT NOT NULL,
                template_name               TEXT NOT NULL,
                body_params                 TEXT NOT NULL DEFAULT '[]',
                status                      TEXT NOT NULL DEFAULT 'pending',
                error                       TEXT,
                psychology_type             TEXT,
                psychology_confidence       REAL DEFAULT 0.0,
                conversion_probability      REAL DEFAULT 0.0,
                created_at                  TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_test_journey_phone ON test_journey_log(phone, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_test_journey_journey ON test_journey_log(journey_type, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_test_journey_stage ON test_journey_log(message_stage, created_at DESC)')


        # ── Phase Abandoned: Lead capture & campaign tracking ──────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS abandoned_leads (
                id                      TEXT PRIMARY KEY,
                shop_domain             TEXT NOT NULL,
                name                    TEXT,
                email                   TEXT NOT NULL,
                phone                   TEXT,
                interest_product        TEXT,
                interest_category       TEXT DEFAULT 'general',
                engagement_score        REAL NOT NULL DEFAULT 0.0,
                ai_context              TEXT,
                do_not_email            INTEGER NOT NULL DEFAULT 0,
                do_not_email_reason     TEXT,
                created_at              TEXT NOT NULL,
                updated_at              TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_abandoned_leads_email ON abandoned_leads(email)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_abandoned_leads_engagement ON abandoned_leads(engagement_score DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_abandoned_leads_created ON abandoned_leads(created_at DESC)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS abandoned_campaigns (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id                 TEXT NOT NULL REFERENCES abandoned_leads(id),
                campaign_num            INTEGER NOT NULL,
                subject                 TEXT NOT NULL,
                email_to                TEXT NOT NULL,
                opened_at               TEXT,
                clicked_at              TEXT,
                created_at              TEXT NOT NULL,
                updated_at              TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_abandoned_campaigns_lead ON abandoned_campaigns(lead_id, campaign_num)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_abandoned_campaigns_created ON abandoned_campaigns(created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_abandoned_campaigns_engagement ON abandoned_campaigns(opened_at, clicked_at)')

        # ── Google My Business automation ──────────────────────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS gmb_posts (
                id                      TEXT PRIMARY KEY,
                business_id             TEXT,
                post_type               TEXT NOT NULL,
                title                   TEXT NOT NULL,
                content                 TEXT NOT NULL,
                image_url               TEXT,
                customer_id             TEXT,
                offer_discount          INTEGER,
                offer_expiry            TEXT,
                product_price           REAL,
                call_to_action_url      TEXT,
                published               INTEGER NOT NULL DEFAULT 0,
                published_at            TEXT,
                created_at              TEXT NOT NULL,
                updated_at              TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_gmb_posts_business ON gmb_posts(business_id, published)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_gmb_posts_type ON gmb_posts(post_type, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_gmb_posts_created ON gmb_posts(created_at DESC)')

        # ── AI Decisions table ────────────────────────────────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS ai_decisions (
                id               TEXT PRIMARY KEY,
                decision_type    TEXT NOT NULL,
                customer_id      TEXT NOT NULL,
                ai_output_json   TEXT NOT NULL,
                source           TEXT NOT NULL DEFAULT 'ai',
                used             INTEGER NOT NULL DEFAULT 0,
                open_rate        REAL,
                ctr              REAL,
                conversion       REAL,
                created_at       TEXT NOT NULL,
                used_at          TEXT
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_ai_decisions_customer ON ai_decisions(customer_id, decision_type)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_ai_decisions_type ON ai_decisions(decision_type, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_ai_decisions_created ON ai_decisions(created_at DESC)')

        # ── AI columns on journey_customers (safe ALTER TABLE) ────────────────
        for col_def in [
            "ALTER TABLE journey_customers ADD COLUMN psychograph_ai_json TEXT",
            "ALTER TABLE journey_customers ADD COLUMN psychograph_updated_at TEXT",
            "ALTER TABLE journey_customers ADD COLUMN review_incentive_ai_decision TEXT",
        ]:
            try:
                connection.execute(col_def)
            except Exception:
                pass  # Column already exists

        # ── AI columns on journey_messages (safe ALTER TABLE) ─────────────────
        for col_def in [
            "ALTER TABLE journey_messages ADD COLUMN ai_subject_id TEXT",
            "ALTER TABLE journey_messages ADD COLUMN subject_line_variant TEXT",
            "ALTER TABLE journey_messages ADD COLUMN product_recommendation_id TEXT",
            "ALTER TABLE journey_messages ADD COLUMN tone_variant_used TEXT",
        ]:
            try:
                connection.execute(col_def)
            except Exception:
                pass  # Column already exists

        # ── AI columns on abandoned_campaigns (safe ALTER TABLE) ──────────────
        for col_def in [
            "ALTER TABLE abandoned_campaigns ADD COLUMN ai_context_used TEXT",
            "ALTER TABLE abandoned_campaigns ADD COLUMN personalization_score REAL",
        ]:
            try:
                connection.execute(col_def)
            except Exception:
                pass  # Column already exists

        # ── Promotional Campaigns (collected customers + campaigns) ───────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS promotional_customers (
                id                  TEXT PRIMARY KEY,
                customer_id         TEXT,
                email               TEXT NOT NULL UNIQUE,
                first_name          TEXT,
                last_name           TEXT,
                phone               TEXT,
                tags                TEXT DEFAULT '',
                segment             TEXT NOT NULL DEFAULT 'general',
                status              TEXT NOT NULL DEFAULT 'active',
                subscribed_to_promo INTEGER NOT NULL DEFAULT 1,
                created_at          TEXT NOT NULL,
                updated_at          TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_promo_customers_email ON promotional_customers(email)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_promo_customers_segment ON promotional_customers(segment, status)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_promo_customers_created ON promotional_customers(created_at DESC)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS promotional_campaigns (
                campaign_id         TEXT PRIMARY KEY,
                name                TEXT NOT NULL,
                template_type       TEXT NOT NULL,
                subject             TEXT NOT NULL,
                html_body           TEXT NOT NULL,
                discount_pct        INTEGER NOT NULL DEFAULT 0,
                coupon_code         TEXT,
                segment             TEXT NOT NULL DEFAULT 'all',
                status              TEXT NOT NULL DEFAULT 'draft',
                sent_count          INTEGER NOT NULL DEFAULT 0,
                failed_count        INTEGER NOT NULL DEFAULT 0,
                scheduled_at        TEXT,
                sent_at             TEXT,
                created_at          TEXT NOT NULL,
                updated_at          TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_promo_campaigns_status ON promotional_campaigns(status)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_promo_campaigns_created ON promotional_campaigns(created_at DESC)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS campaign_sends (
                send_id             TEXT PRIMARY KEY,
                campaign_id         TEXT NOT NULL,
                email               TEXT NOT NULL,
                status              TEXT NOT NULL DEFAULT 'sent',
                sent_at             TEXT NOT NULL,
                opened_at           TEXT,
                clicked_at          TEXT,
                converted_at        TEXT,
                created_at          TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_campaign_sends_campaign ON campaign_sends(campaign_id, status)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_campaign_sends_email ON campaign_sends(email)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_campaign_sends_opened ON campaign_sends(campaign_id, opened_at)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_campaign_sends_clicked ON campaign_sends(campaign_id, clicked_at)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS campaign_send_queue (
                queue_id             TEXT PRIMARY KEY,
                campaign_id          TEXT NOT NULL,
                email                TEXT NOT NULL,
                first_name           TEXT,
                last_name            TEXT,
                status               TEXT NOT NULL DEFAULT 'queued',
                scheduled_for        TEXT NOT NULL,
                attempt_count        INTEGER NOT NULL DEFAULT 0,
                last_error           TEXT,
                sent_at              TEXT,
                created_at           TEXT NOT NULL,
                updated_at           TEXT NOT NULL,
                UNIQUE(campaign_id, email)
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_campaign_send_queue_status_due ON campaign_send_queue(status, scheduled_for)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_campaign_send_queue_campaign ON campaign_send_queue(campaign_id, status)')

        for col_def in [
            "ALTER TABLE promotional_campaigns ADD COLUMN send_interval_seconds REAL NOT NULL DEFAULT 1.0",
            "ALTER TABLE promotional_campaigns ADD COLUMN queue_status TEXT NOT NULL DEFAULT 'draft'",
            "ALTER TABLE promotional_campaigns ADD COLUMN queued_count INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE promotional_campaigns ADD COLUMN started_at TEXT",
            "ALTER TABLE promotional_campaigns ADD COLUMN completed_at TEXT",
            "ALTER TABLE campaign_sends ADD COLUMN queue_id TEXT",
            "ALTER TABLE campaign_sends ADD COLUMN last_error TEXT",
        ]:
            try:
                connection.execute(col_def)
            except Exception:
                pass  # Column already exists

        # ── Review Journey: new columns on journey_customers ─────────────────
        for col_def in [
            "ALTER TABLE journey_customers ADD COLUMN customer_status TEXT NOT NULL DEFAULT 'cold'",
            "ALTER TABLE journey_customers ADD COLUMN review_requested_at TEXT",
            "ALTER TABLE journey_customers ADD COLUMN review_submitted_at TEXT",
            "ALTER TABLE journey_customers ADD COLUMN review_submitted_channel TEXT",
            "ALTER TABLE journey_customers ADD COLUMN review_rating INTEGER",
            "ALTER TABLE journey_customers ADD COLUMN review_text TEXT",
            "ALTER TABLE journey_customers ADD COLUMN repeat_purchase_triggered INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE journey_customers ADD COLUMN repeat_purchase_date TEXT",
            "ALTER TABLE journey_customers ADD COLUMN purchased_product_name TEXT",
            "ALTER TABLE journey_customers ADD COLUMN purchased_product_handle TEXT",
            "ALTER TABLE journey_customers ADD COLUMN crosssell_day18_sent INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE journey_customers ADD COLUMN crosssell_day18_sent_at TEXT",
            "ALTER TABLE journey_customers ADD COLUMN replenishment_day45_sent INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE journey_customers ADD COLUMN replenishment_day45_sent_at TEXT",
            "ALTER TABLE journey_customers ADD COLUMN vip_day75_sent INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE journey_customers ADD COLUMN vip_day75_sent_at TEXT",
        ]:
            try:
                connection.execute(col_def)
            except Exception:
                pass  # Column already exists

        # ── Review Journey: new tracking columns on journey_messages ──────────
        for col_def in [
            "ALTER TABLE journey_messages ADD COLUMN opened_at TEXT",
            "ALTER TABLE journey_messages ADD COLUMN clicked_at TEXT",
            "ALTER TABLE journey_messages ADD COLUMN channel TEXT NOT NULL DEFAULT 'whatsapp'",
        ]:
            try:
                connection.execute(col_def)
            except Exception:
                pass  # Column already exists

        # ── Review Journey events table ───────────────────────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS review_journey_events (
                id              TEXT PRIMARY KEY,
                customer_id     TEXT NOT NULL,
                shop_domain     TEXT NOT NULL DEFAULT 'rwxtic-gz.myshopify.com',
                event_type      TEXT NOT NULL,
                journey_stage   TEXT,
                channel         TEXT,
                template_name   TEXT,
                metadata_json   TEXT NOT NULL DEFAULT '{}',
                created_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_rj_events_customer ON review_journey_events(customer_id, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_rj_events_type ON review_journey_events(event_type, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_rj_events_shop ON review_journey_events(shop_domain, created_at DESC)')

        # ── Email Suppression list ─────────────────────────────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS email_suppression (
                id              TEXT PRIMARY KEY,
                email           TEXT NOT NULL UNIQUE,
                reason          TEXT NOT NULL DEFAULT 'unsubscribed',
                bounce_type     TEXT,
                source          TEXT NOT NULL DEFAULT 'manual',
                campaign_id     TEXT,
                raw_error       TEXT,
                created_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_suppression_email ON email_suppression(email)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_suppression_reason ON email_suppression(reason, created_at DESC)')

        # ── Promotional send logs (granular per-send event log) ────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS promo_send_logs (
                log_id          TEXT PRIMARY KEY,
                campaign_id     TEXT NOT NULL,
                queue_id        TEXT,
                send_id         TEXT,
                email           TEXT NOT NULL,
                status          TEXT NOT NULL,
                error_raw       TEXT,
                error_type      TEXT,
                attempt         INTEGER NOT NULL DEFAULT 1,
                logged_at       TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_promo_send_logs_campaign ON promo_send_logs(campaign_id, logged_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_promo_send_logs_status ON promo_send_logs(status, logged_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_promo_send_logs_email ON promo_send_logs(email, logged_at DESC)')

        # ── Enable WAL mode for better concurrency ────────────────────────────
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA cache_size=-32000")  # 32 MB page cache

        # ── Review Journey: extra columns on journey_customers ────────────────
        for _col, _ddl in [
            ("customer_status",          "TEXT NOT NULL DEFAULT 'cold'"),
            ("purchased_product_name",   "TEXT"),
            ("purchased_product_handle", "TEXT"),
            ("review_requested_at",      "TEXT"),
            ("review_submitted_at",      "TEXT"),
            ("review_submitted_channel", "TEXT"),
            ("review_rating",            "INTEGER"),
            ("review_text",              "TEXT"),
            ("repeat_purchase_triggered","INTEGER NOT NULL DEFAULT 0"),
            ("repeat_purchase_date",     "TEXT"),
        ]:
            try:
                connection.execute(f"ALTER TABLE journey_customers ADD COLUMN {_col} {_ddl}")
            except Exception:
                pass  # Column already exists — safe to ignore

        # ── ROI Attribution results ────────────────────────────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS campaign_attribution (
                id              TEXT PRIMARY KEY,
                campaign_id     TEXT NOT NULL,
                campaign_type   TEXT NOT NULL DEFAULT 'promotional',
                order_id        TEXT,
                customer_email  TEXT,
                order_revenue   REAL NOT NULL DEFAULT 0,
                attribution_model TEXT NOT NULL DEFAULT 'last_touch',
                attributed_revenue REAL NOT NULL DEFAULT 0,
                touch_type      TEXT NOT NULL DEFAULT 'send',
                days_to_convert INTEGER,
                created_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_attribution_campaign ON campaign_attribution(campaign_id, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_attribution_email ON campaign_attribution(customer_email)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_attribution_order ON campaign_attribution(order_id)')

        # ── Saved audience segments ────────────────────────────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS saved_segments (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                description     TEXT,
                filters_json    TEXT NOT NULL DEFAULT '{}',
                customer_count  INTEGER NOT NULL DEFAULT 0,
                last_computed   TEXT,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_saved_segments_updated ON saved_segments(updated_at DESC)')

        # ── Audit log for all admin actions ───────────────────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS audit_log (
                id              TEXT PRIMARY KEY,
                admin_email     TEXT NOT NULL DEFAULT 'system',
                action          TEXT NOT NULL,
                resource_type   TEXT NOT NULL,
                resource_id     TEXT,
                changes_json    TEXT NOT NULL DEFAULT '{}',
                ip_address      TEXT,
                created_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_audit_log_resource ON audit_log(resource_type, resource_id)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at DESC)')

        # ── Customer RFM + engagement scores (segmentation cache) ─────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS customer_segments (
                id                  TEXT PRIMARY KEY,
                email               TEXT NOT NULL UNIQUE,
                shop_domain         TEXT NOT NULL DEFAULT 'rwxtic-gz.myshopify.com',
                rfm_segment         TEXT NOT NULL DEFAULT 'new',
                recency_days        INTEGER,
                frequency           INTEGER NOT NULL DEFAULT 0,
                monetary_inr        REAL NOT NULL DEFAULT 0,
                engagement_label    TEXT NOT NULL DEFAULT 'inactive',
                churn_risk_score    REAL NOT NULL DEFAULT 0,
                clv_estimate_inr    REAL NOT NULL DEFAULT 0,
                computed_at         TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_cust_segments_email ON customer_segments(email)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_cust_segments_rfm ON customer_segments(rfm_segment, computed_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_cust_segments_shop ON customer_segments(shop_domain, rfm_segment)')

        # ── Unified Customers (single profile across Shopify, Email, WhatsApp) ─
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS customers (
                id                      TEXT PRIMARY KEY,
                email                   TEXT NOT NULL UNIQUE,
                phone                   TEXT,
                name                    TEXT,
                first_name              TEXT,
                last_name               TEXT,
                shopify_customer_id     TEXT,
                tags                    TEXT NOT NULL DEFAULT '[]',
                source                  TEXT NOT NULL DEFAULT 'manual',
                customer_status         TEXT NOT NULL DEFAULT 'new',
                total_orders            INTEGER NOT NULL DEFAULT 0,
                total_spent             REAL NOT NULL DEFAULT 0,
                last_order_date         TEXT,
                first_order_date        TEXT,
                email_opted_in          INTEGER NOT NULL DEFAULT 0,
                whatsapp_opted_in       INTEGER NOT NULL DEFAULT 0,
                email_unsubscribed_at   TEXT,
                whatsapp_unsubscribed_at TEXT,
                notes                   TEXT,
                created_at              TEXT NOT NULL,
                updated_at              TEXT NOT NULL,
                deleted_at              TEXT
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_customers_shopify ON customers(shopify_customer_id)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(customer_status, deleted_at)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_customers_last_order ON customers(last_order_date DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_customers_created ON customers(created_at DESC)')

        # Identity + customer intelligence columns for unified CRM/Email/WhatsApp orchestration.
        for col_def in [
            'customer_uid TEXT',
            'meta_lead_id TEXT',
            'google_gclid TEXT',
            'google_campaign TEXT',
            'meta_campaign TEXT',
            'whatsapp_number TEXT',
            "preferred_channel TEXT NOT NULL DEFAULT 'auto'",
            'lead_score INTEGER NOT NULL DEFAULT 0',
            "engagement_label TEXT NOT NULL DEFAULT 'cold'",
            "purchase_status TEXT NOT NULL DEFAULT 'not_purchased'",
            'pause_campaigns INTEGER NOT NULL DEFAULT 0',
            'next_ai_action TEXT',
            'ai_last_reason TEXT',
            'last_engagement_at TEXT',
            'fbc TEXT',
        ]:
            try:
                connection.execute(f'ALTER TABLE customers ADD COLUMN {col_def}')
            except Exception:
                pass

        # Backfill identity and core intelligence fields for historical rows.
        connection.execute(
            """
            UPDATE customers
            SET customer_uid = 'CUS-' || upper(substr(hex(randomblob(8)), 1, 12))
            WHERE customer_uid IS NULL OR customer_uid = ''
            """
        )
        connection.execute(
            """
            UPDATE customers
            SET whatsapp_number = phone
            WHERE (whatsapp_number IS NULL OR whatsapp_number = '') AND phone IS NOT NULL AND phone != ''
            """
        )
        connection.execute(
            """
            UPDATE customers
            SET purchase_status = CASE WHEN COALESCE(total_orders, 0) > 0 THEN 'purchased' ELSE 'not_purchased' END
            WHERE purchase_status IS NULL OR purchase_status = ''
            """
        )

        connection.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_uid ON customers(customer_uid)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_customers_pause_campaigns ON customers(pause_campaigns, deleted_at)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_customers_engagement_label ON customers(engagement_label, lead_score DESC)')

        # ── Customer Identity Map (Meta/Google/Shopify/WhatsApp/Email) ───────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS customer_identities (
                id              TEXT PRIMARY KEY,
                customer_uid    TEXT NOT NULL,
                customer_id     TEXT,
                identity_type   TEXT NOT NULL,
                identity_value  TEXT NOT NULL,
                source          TEXT NOT NULL DEFAULT 'system',
                metadata_json   TEXT NOT NULL DEFAULT '{}',
                first_seen_at   TEXT NOT NULL,
                last_seen_at    TEXT NOT NULL,
                UNIQUE(customer_uid, identity_type, identity_value)
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_customer_identities_uid ON customer_identities(customer_uid)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_customer_identities_lookup ON customer_identities(identity_type, identity_value)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_customer_identities_source ON customer_identities(source, last_seen_at DESC)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS customer_score_history (
                id              TEXT PRIMARY KEY,
                customer_uid    TEXT NOT NULL,
                customer_id     TEXT,
                customer_email  TEXT NOT NULL,
                lead_score      INTEGER NOT NULL DEFAULT 0,
                engagement_label TEXT NOT NULL DEFAULT 'cold',
                purchase_status TEXT NOT NULL DEFAULT 'not_purchased',
                reason          TEXT,
                metrics_json    TEXT NOT NULL DEFAULT '{}',
                created_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_customer_score_history_uid ON customer_score_history(customer_uid, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_customer_score_history_email ON customer_score_history(customer_email, created_at DESC)')

        # Backfill identity map from columns already present on historical customers.
        for identity_type, column_name, source in [
            ('email', 'email', 'crm'),
            ('phone', 'phone', 'crm'),
            ('whatsapp_number', 'whatsapp_number', 'whatsapp'),
            ('shopify_customer_id', 'shopify_customer_id', 'shopify'),
            ('meta_lead_id', 'meta_lead_id', 'meta'),
            ('google_gclid', 'google_gclid', 'google'),
        ]:
            connection.execute(
                f'''
                INSERT OR IGNORE INTO customer_identities
                    (id, customer_uid, customer_id, identity_type, identity_value, source,
                     metadata_json, first_seen_at, last_seen_at)
                SELECT lower(hex(randomblob(16))), customer_uid, id, ?, {column_name}, ?, '{{}}', created_at, updated_at
                FROM customers
                WHERE customer_uid IS NOT NULL AND {column_name} IS NOT NULL AND {column_name} != ''
                ''',
                (identity_type, source),
            )

        # ── Contact Lists (static + dynamic audiences) ────────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS contact_lists (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                description     TEXT,
                list_type       TEXT NOT NULL DEFAULT 'static',
                rules_json      TEXT NOT NULL DEFAULT '{}',
                customer_count  INTEGER NOT NULL DEFAULT 0,
                last_computed   TEXT,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_contact_lists_name ON contact_lists(name)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_contact_lists_updated ON contact_lists(updated_at DESC)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS contact_list_members (
                list_id         TEXT NOT NULL,
                customer_id     TEXT NOT NULL,
                added_at        TEXT NOT NULL,
                PRIMARY KEY (list_id, customer_id)
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_list_members_list ON contact_list_members(list_id)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_list_members_customer ON contact_list_members(customer_id)')

        # ── Unified Communication Templates (Email + WhatsApp) ────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS communication_templates (
                id                      TEXT PRIMARY KEY,
                name                    TEXT NOT NULL,
                category                TEXT NOT NULL DEFAULT 'promotional',
                description             TEXT,
                status                  TEXT NOT NULL DEFAULT 'draft',
                email_subject           TEXT,
                email_preheader         TEXT,
                email_html              TEXT,
                email_text              TEXT,
                whatsapp_body           TEXT,
                whatsapp_header_image_url TEXT,
                variables_json          TEXT NOT NULL DEFAULT '[]',
                created_at              TEXT NOT NULL,
                updated_at              TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_comm_templates_category ON communication_templates(category, status)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_comm_templates_status ON communication_templates(status)')

        # ── Journeys (automated trigger-based sequences) ──────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS journeys (
                id                  TEXT PRIMARY KEY,
                name                TEXT NOT NULL,
                description         TEXT,
                trigger_event       TEXT NOT NULL DEFAULT 'order_delivered',
                trigger_delay_hours INTEGER NOT NULL DEFAULT 0,
                target_list_id      TEXT,
                status              TEXT NOT NULL DEFAULT 'draft',
                enrolled_count      INTEGER NOT NULL DEFAULT 0,
                completed_count     INTEGER NOT NULL DEFAULT 0,
                created_at          TEXT NOT NULL,
                updated_at          TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_journeys_status ON journeys(status)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_journeys_trigger ON journeys(trigger_event, status)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS journey_steps (
                id              TEXT PRIMARY KEY,
                journey_id      TEXT NOT NULL,
                step_number     INTEGER NOT NULL,
                name            TEXT,
                delay_days      INTEGER NOT NULL DEFAULT 0,
                delay_hours     INTEGER NOT NULL DEFAULT 0,
                channel         TEXT NOT NULL DEFAULT 'email',
                template_id     TEXT,
                conditions_json TEXT NOT NULL DEFAULT '{}',
                max_retries     INTEGER NOT NULL DEFAULT 1,
                created_at      TEXT NOT NULL,
                UNIQUE(journey_id, step_number)
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_journey_steps_journey ON journey_steps(journey_id, step_number)')

        # ── Journey Executions (per-customer run tracking) ────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS journey_executions (
                id              TEXT PRIMARY KEY,
                journey_id      TEXT NOT NULL,
                customer_id     TEXT NOT NULL,
                customer_email  TEXT NOT NULL,
                triggered_at    TEXT NOT NULL,
                trigger_context TEXT NOT NULL DEFAULT '{}',
                current_step    INTEGER NOT NULL DEFAULT 0,
                status          TEXT NOT NULL DEFAULT 'active',
                started_at      TEXT NOT NULL,
                completed_at    TEXT,
                created_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_j_exec_journey ON journey_executions(journey_id, status)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_j_exec_customer ON journey_executions(customer_email, status)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_j_exec_triggered ON journey_executions(triggered_at DESC)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS journey_step_sends (
                id              TEXT PRIMARY KEY,
                execution_id    TEXT NOT NULL,
                step_id         TEXT NOT NULL,
                channel         TEXT NOT NULL DEFAULT 'email',
                template_id     TEXT,
                subject_rendered TEXT,
                body_rendered   TEXT,
                scheduled_at    TEXT NOT NULL,
                sent_at         TEXT,
                status          TEXT NOT NULL DEFAULT 'queued',
                error_reason    TEXT,
                message_id      TEXT,
                opened_at       TEXT,
                clicked_at      TEXT,
                created_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_j_step_sends_exec ON journey_step_sends(execution_id)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_j_step_sends_scheduled ON journey_step_sends(scheduled_at, status)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_j_step_sends_status ON journey_step_sends(status, scheduled_at)')

        # ── CSV Import log ────────────────────────────────────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS csv_import_log (
                id              TEXT PRIMARY KEY,
                filename        TEXT NOT NULL,
                imported_by     TEXT,
                total_rows      INTEGER NOT NULL DEFAULT 0,
                created_count   INTEGER NOT NULL DEFAULT 0,
                updated_count   INTEGER NOT NULL DEFAULT 0,
                skipped_count   INTEGER NOT NULL DEFAULT 0,
                error_count     INTEGER NOT NULL DEFAULT 0,
                errors_json     TEXT NOT NULL DEFAULT '[]',
                status          TEXT NOT NULL DEFAULT 'complete',
                created_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_csv_import_log ON csv_import_log(created_at DESC)')

        # ── Shopify Orders sync (for unified customer enrichment) ─────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS shopify_orders (
                id                  TEXT PRIMARY KEY,
                shopify_order_id    TEXT UNIQUE NOT NULL,
                customer_email      TEXT,
                shopify_customer_id TEXT,
                order_name          TEXT,
                total_price         REAL NOT NULL DEFAULT 0,
                financial_status    TEXT,
                fulfillment_status  TEXT,
                line_items_json     TEXT NOT NULL DEFAULT '[]',
                tags                TEXT,
                note                TEXT,
                created_at_shopify  TEXT,
                updated_at_shopify  TEXT,
                synced_at           TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_shopify_orders_email ON shopify_orders(customer_email)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_shopify_orders_customer ON shopify_orders(shopify_customer_id)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_shopify_orders_synced ON shopify_orders(synced_at DESC)')

        # ── WhatsApp Sales OS: retargeting + order lifecycle reliability ────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS retargeting_sync_runs (
                id              TEXT PRIMARY KEY,
                audience_key    TEXT NOT NULL,
                audience_name   TEXT NOT NULL,
                platform        TEXT NOT NULL,
                filter_json     TEXT NOT NULL DEFAULT '{}',
                matched_count   INTEGER NOT NULL DEFAULT 0,
                status          TEXT NOT NULL DEFAULT 'pending',
                result_json     TEXT NOT NULL DEFAULT '{}',
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_retargeting_sync_runs_platform ON retargeting_sync_runs(platform, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_retargeting_sync_runs_audience ON retargeting_sync_runs(audience_key, platform, created_at DESC)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS order_lifecycle_audit (
                id                  TEXT PRIMARY KEY,
                order_id            TEXT,
                customer_id         TEXT,
                phone               TEXT,
                event_type          TEXT NOT NULL,
                lifecycle_status    TEXT NOT NULL,
                template_name       TEXT,
                message_id          TEXT,
                error_detail        TEXT,
                payload_json        TEXT NOT NULL DEFAULT '{}',
                created_at          TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_order_lifecycle_audit_order ON order_lifecycle_audit(order_id, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_order_lifecycle_audit_status ON order_lifecycle_audit(lifecycle_status, created_at DESC)')

        # ── Phase 2: Campaigns (one-off broadcast campaigns) ─────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS campaigns (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                description     TEXT,
                type            TEXT NOT NULL DEFAULT 'email',
                audience_type   TEXT NOT NULL DEFAULT 'all',
                list_id         TEXT,
                segment_filter_json TEXT NOT NULL DEFAULT '{}',
                template_id     TEXT,
                schedule_type   TEXT NOT NULL DEFAULT 'send_now',
                scheduled_at    TEXT,
                recurring_pattern TEXT,
                status          TEXT NOT NULL DEFAULT 'draft',
                total_recipients INTEGER NOT NULL DEFAULT 0,
                sent_count      INTEGER NOT NULL DEFAULT 0,
                opened_count    INTEGER NOT NULL DEFAULT 0,
                clicked_count   INTEGER NOT NULL DEFAULT 0,
                error_count     INTEGER NOT NULL DEFAULT 0,
                started_at      TEXT,
                completed_at    TEXT,
                created_by      TEXT,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_campaigns_created ON campaigns(created_at DESC)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS campaign_sends (
                id              TEXT PRIMARY KEY,
                campaign_id     TEXT NOT NULL,
                customer_id     TEXT,
                customer_email  TEXT NOT NULL,
                channel         TEXT NOT NULL DEFAULT 'email',
                template_id     TEXT,
                subject_rendered TEXT,
                body_rendered   TEXT,
                status          TEXT NOT NULL DEFAULT 'queued',
                scheduled_at    TEXT,
                sent_at         TEXT,
                error_reason    TEXT,
                message_id      TEXT,
                opened_at       TEXT,
                clicked_at      TEXT,
                created_at      TEXT NOT NULL,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
            )
            '''
        )
        _ensure_campaign_sends_compat(connection)
        connection.execute('CREATE INDEX IF NOT EXISTS idx_campaign_sends_v2_campaign ON campaign_sends(campaign_id)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_campaign_sends_v2_customer_email ON campaign_sends(customer_email)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_campaign_sends_v2_status ON campaign_sends(status)')

        # ── Phase 3: Communication Events (unified event stream) ─────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS communication_events (
                id              TEXT PRIMARY KEY,
                customer_id     TEXT,
                customer_email  TEXT NOT NULL,
                source_type     TEXT NOT NULL DEFAULT 'journey',
                source_id       TEXT,
                event_type      TEXT NOT NULL,
                channel         TEXT NOT NULL DEFAULT 'email',
                template_id     TEXT,
                template_name   TEXT,
                subject         TEXT,
                message_preview TEXT,
                metadata_json   TEXT NOT NULL DEFAULT '{}',
                created_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_comm_events_email ON communication_events(customer_email)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_comm_events_type ON communication_events(event_type)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_comm_events_source ON communication_events(source_type, source_id)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_comm_events_created ON communication_events(created_at DESC)')

        # ── Phase 5: Shopify Sync Log ─────────────────────────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS shopify_sync_log (
                id              TEXT PRIMARY KEY,
                sync_type       TEXT NOT NULL,
                event_type      TEXT,
                shopify_id      TEXT,
                customer_email  TEXT,
                status          TEXT NOT NULL DEFAULT 'ok',
                error_reason    TEXT,
                payload_json    TEXT NOT NULL DEFAULT '{}',
                created_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_shopify_sync_log_created ON shopify_sync_log(created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_shopify_sync_log_type ON shopify_sync_log(sync_type, status)')

        # ── Wave 0.2: Wabis AI Integration ───────────────────────────────────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS ai_incoming_messages (
                id              TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                customer_phone  TEXT NOT NULL,
                message_type    TEXT NOT NULL DEFAULT 'text',
                body            TEXT NOT NULL,
                created_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_ai_incoming_phone ON ai_incoming_messages(customer_phone, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_ai_incoming_conversation ON ai_incoming_messages(conversation_id, created_at DESC)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS ai_outgoing_replies (
                id              TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                customer_phone  TEXT NOT NULL,
                reply_text      TEXT NOT NULL,
                intent          TEXT NOT NULL,
                escalated       INTEGER NOT NULL DEFAULT 0,
                send_status     TEXT NOT NULL DEFAULT 'pending',
                message_mode    TEXT NOT NULL DEFAULT 'text',
                media_json      TEXT,
                created_at      TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_ai_outgoing_phone ON ai_outgoing_replies(customer_phone, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_ai_outgoing_conversation ON ai_outgoing_replies(conversation_id, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_ai_outgoing_status ON ai_outgoing_replies(send_status, created_at DESC)')

        # ── Stage 1: Unified Conversation State (Single Source of Truth) ──────
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS conversation_state (
                phone TEXT PRIMARY KEY,
                
                owner TEXT NOT NULL DEFAULT 'ai',
                owner_reason TEXT,
                
                flow_id TEXT,
                flow_step TEXT,
                expected_responses TEXT,
                
                started_at TEXT,
                expires_at TEXT,
                last_activity TEXT,
                
                context_json TEXT,
                customer_id TEXT,
                language TEXT,
                active_product TEXT,
                latest_intent TEXT,
                price_shared INTEGER NOT NULL DEFAULT 0,
                quantity_selected TEXT,
                address_received INTEGER NOT NULL DEFAULT 0,
                pincode_received TEXT,
                payment_claimed INTEGER NOT NULL DEFAULT 0,
                payment_screenshot_received INTEGER NOT NULL DEFAULT 0,
                defer_intent TEXT,
                followups_allowed INTEGER NOT NULL DEFAULT 1,
                journey_stage TEXT,
                last_ai_reply_hash TEXT,
                last_ai_reply_at TEXT,
                
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_conversation_state_owner ON conversation_state(owner)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_conversation_state_expires ON conversation_state(expires_at)')
        for _col, _ddl in [
            ("customer_id", "TEXT"),
            ("language", "TEXT"),
            ("active_product", "TEXT"),
            ("latest_intent", "TEXT"),
            ("price_shared", "INTEGER NOT NULL DEFAULT 0"),
            ("quantity_selected", "TEXT"),
            ("address_received", "INTEGER NOT NULL DEFAULT 0"),
            ("pincode_received", "TEXT"),
            ("payment_claimed", "INTEGER NOT NULL DEFAULT 0"),
            ("payment_screenshot_received", "INTEGER NOT NULL DEFAULT 0"),
            ("defer_intent", "TEXT"),
            ("followups_allowed", "INTEGER NOT NULL DEFAULT 1"),
            ("journey_stage", "TEXT"),
            ("last_ai_reply_hash", "TEXT"),
            ("last_ai_reply_at", "TEXT"),
        ]:
            try:
                connection.execute(f"ALTER TABLE conversation_state ADD COLUMN {_col} {_ddl}")
            except Exception:
                pass

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS product_journey_followups (
                id TEXT PRIMARY KEY,
                phone TEXT NOT NULL,
                conversation_phone TEXT NOT NULL,
                product_key TEXT,
                scenario TEXT NOT NULL,
                reply_style TEXT NOT NULL DEFAULT 'english',
                customer_reference TEXT,
                followup_stage TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                sent INTEGER NOT NULL DEFAULT 0,
                sent_at TEXT,
                reply_text TEXT,
                send_status TEXT NOT NULL DEFAULT 'queued',
                send_error TEXT,
                message_mode TEXT NOT NULL DEFAULT 'text',
                media_json TEXT,
                context_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_product_followups_phone ON product_journey_followups(phone, scheduled_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_product_followups_due ON product_journey_followups(sent, scheduled_at)')

        _ensure_column(connection, 'ai_outgoing_replies', "message_mode TEXT NOT NULL DEFAULT 'text'")
        _ensure_column(connection, 'ai_outgoing_replies', 'media_json TEXT')
        _ensure_column(connection, 'product_journey_followups', "message_mode TEXT NOT NULL DEFAULT 'text'")
        _ensure_column(connection, 'product_journey_followups', 'media_json TEXT')

        # Knowledge gaps - tracks questions we couldn't answer
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS knowledge_gaps (
                id TEXT PRIMARY KEY,
                phone TEXT NOT NULL,
                original_query TEXT NOT NULL,
                conversation_id TEXT,
                clarifications TEXT,
                detected_intent TEXT,
                resolved_by TEXT,
                final_answer TEXT,
                created_at TEXT NOT NULL,
                resolved_at TEXT
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_kg_phone ON knowledge_gaps(phone, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_kg_unresolved ON knowledge_gaps(resolved_by, created_at DESC)')

        # Missing products - tracks products customers ask for but we don't have
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS missing_products (
                product_name TEXT PRIMARY KEY,
                search_count INTEGER NOT NULL DEFAULT 1,
                last_searched TEXT NOT NULL,
                clarifications TEXT,
                added_to_catalog INTEGER NOT NULL DEFAULT 0,
                added_at TEXT,
                created_at TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_mp_count ON missing_products(search_count DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_mp_added ON missing_products(added_to_catalog, created_at DESC)')

        # Routing audit log
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS routing_log (
                id TEXT PRIMARY KEY,
                phone TEXT NOT NULL,
                message TEXT,
                owner_before TEXT,
                route_taken TEXT NOT NULL,
                context TEXT,
                timestamp TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_routing_log_phone ON routing_log(phone, timestamp DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_routing_log_route ON routing_log(route_taken, timestamp DESC)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS escalation_queue (
                id              TEXT PRIMARY KEY,
                customer_phone  TEXT NOT NULL,
                reason          TEXT NOT NULL,
                resolved        INTEGER NOT NULL DEFAULT 0,
                created_at      TEXT NOT NULL,
                resolved_at     TEXT
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_escalation_phone ON escalation_queue(customer_phone, resolved)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_escalation_created ON escalation_queue(created_at DESC, resolved)')

        # Flow abandonment audit - tracks when customers abandon flows
        # Conversation audit log - comprehensive conversation history
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS conversation_audit_log (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                
                phone TEXT NOT NULL,
                
                direction TEXT NOT NULL,
                -- inbound / outbound
                
                source TEXT NOT NULL,
                -- customer / wabis / ai / system / human / campaign
                
                message TEXT,
                
                owner_before TEXT,
                owner_after TEXT,
                
                active_flow TEXT,
                
                detected_intent TEXT,
                
                route_decision TEXT,
                
                reason TEXT,
                
                metadata_json TEXT
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_audit_phone ON conversation_audit_log(phone, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_audit_source ON conversation_audit_log(source, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_audit_intent ON conversation_audit_log(detected_intent, created_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_audit_route ON conversation_audit_log(route_decision, created_at DESC)')

        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS flow_audit (
                id TEXT PRIMARY KEY,
                phone TEXT NOT NULL,
                flow_name TEXT NOT NULL,
                abandonment_reason TEXT NOT NULL,
                expected_options TEXT,
                received_message TEXT,
                final_route TEXT,
                timestamp TEXT NOT NULL
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_flow_audit_phone ON flow_audit(phone, timestamp DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_flow_audit_flow ON flow_audit(flow_name, timestamp DESC)')


def row_to_truecaller_request(row: sqlite3.Row) -> TruecallerRequestRecord:
    return TruecallerRequestRecord.model_validate(
        {
            'request_id': row['request_id'],
            'status': row['status'],
            'profile_endpoint': row['profile_endpoint'],
            'name': row['name'],
            'email': row['email'],
            'phone': row['phone'],
            'phone_country_code': row['phone_country_code'],
            'error_message': row['error_message'],
            'raw_callback': _deserialize_json(row['raw_callback']),
            'raw_profile': _deserialize_json(row['raw_profile']),
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
        }
    )


def save_truecaller_request(
    request_id: str,
    *,
    status: str,
    profile_endpoint: str | None = None,
    name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    phone_country_code: str | None = None,
    error_message: str | None = None,
    raw_callback: dict[str, object] | None = None,
    raw_profile: dict[str, object] | None = None,
) -> TruecallerRequestRecord:
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        connection.execute(
            '''
            INSERT INTO truecaller_requests (
                request_id,
                status,
                profile_endpoint,
                name,
                email,
                phone,
                phone_country_code,
                error_message,
                raw_callback,
                raw_profile,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(request_id) DO UPDATE SET
                status = excluded.status,
                profile_endpoint = COALESCE(excluded.profile_endpoint, truecaller_requests.profile_endpoint),
                name = COALESCE(excluded.name, truecaller_requests.name),
                email = COALESCE(excluded.email, truecaller_requests.email),
                phone = COALESCE(excluded.phone, truecaller_requests.phone),
                phone_country_code = COALESCE(excluded.phone_country_code, truecaller_requests.phone_country_code),
                error_message = COALESCE(excluded.error_message, truecaller_requests.error_message),
                raw_callback = COALESCE(excluded.raw_callback, truecaller_requests.raw_callback),
                raw_profile = COALESCE(excluded.raw_profile, truecaller_requests.raw_profile),
                updated_at = excluded.updated_at
            ''',
            (
                request_id,
                status,
                profile_endpoint,
                name,
                email,
                phone,
                phone_country_code,
                error_message,
                _serialize_json(raw_callback),
                _serialize_json(raw_profile),
                now,
                now,
            ),
        )
        row = connection.execute(
            'SELECT * FROM truecaller_requests WHERE request_id = ?',
            (request_id,),
        ).fetchone()

    if row is None:
        raise RuntimeError('Truecaller request save failed unexpectedly.')

    return row_to_truecaller_request(row)


def create_truecaller_request(request_id: str) -> TruecallerRequestRecord:
    return save_truecaller_request(request_id, status='created')


def get_truecaller_request(request_id: str) -> TruecallerRequestRecord | None:
    with get_connection() as connection:
        row = connection.execute(
            'SELECT * FROM truecaller_requests WHERE request_id = ?',
            (request_id,),
        ).fetchone()

    if row is None:
        return None

    return row_to_truecaller_request(row)


def is_truecaller_request_expired(record: TruecallerRequestRecord) -> bool:
    age_seconds = (datetime.now(timezone.utc) - record.created_at).total_seconds()
    return age_seconds >= TRUECALLER_REQUEST_MAX_AGE_SECONDS


def fetch_truecaller_profile(profile_endpoint: str, access_token: str) -> dict[str, object]:
    request = urllib.request.Request(
        url=profile_endpoint,
        headers={
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}',
            'Cache-Control': 'no-cache',
        },
        method='GET',
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as error:
        response_body = error.read().decode('utf-8', errors='ignore')
        raise RuntimeError(f'Truecaller profile request failed with status {error.code}: {response_body or error.reason}') from error
    except urllib.error.URLError as error:
        raise RuntimeError(f'Truecaller profile request failed: {error.reason}') from error

    if not isinstance(payload, dict):
        raise RuntimeError('Truecaller profile response was not a JSON object.')

    return payload


def _normalize_truecaller_phone(value: str | None) -> str | None:
    phone = (value or '').strip()

    if not phone:
        return None

    if phone.startswith('+'):
        return phone

    digits_only = ''.join(character for character in phone if character.isdigit())

    if digits_only and digits_only == phone:
        return f'+{digits_only}'

    return phone


def extract_truecaller_identity(profile: dict[str, object]) -> tuple[str | None, str | None, str | None, str | None]:
    name_value: str | None = None
    email_value: str | None = None
    phone_value: str | None = None
    country_code_value: str | None = None

    name_payload = profile.get('name')

    if isinstance(name_payload, dict):
        first_name = str(name_payload.get('first') or '').strip()
        last_name = str(name_payload.get('last') or '').strip()
        full_name = ' '.join(part for part in [first_name, last_name] if part).strip()
        name_value = full_name or None

    online_identities = profile.get('onlineIdentities')

    if isinstance(online_identities, dict):
        email_candidate = str(online_identities.get('email') or '').strip()
        email_value = email_candidate or None

    phone_numbers = profile.get('phoneNumbers')

    if isinstance(phone_numbers, list):
        for phone_candidate in phone_numbers:
            normalized_phone = _normalize_truecaller_phone(str(phone_candidate or '').strip())

            if normalized_phone:
                phone_value = normalized_phone
                break

    addresses = profile.get('addresses')

    if isinstance(addresses, list):
        for address in addresses:
            if isinstance(address, dict):
                country_code = str(address.get('countryCode') or '').strip()

                if country_code:
                    country_code_value = country_code
                    break

    return name_value, email_value, phone_value, country_code_value


def save_truecaller_profile(request_id: str, profile: dict[str, object]) -> TruecallerRequestRecord:
    name_value, email_value, phone_value, country_code_value = extract_truecaller_identity(profile)
    return save_truecaller_request(
        request_id,
        status='verified',
        name=name_value,
        email=email_value,
        phone=phone_value,
        phone_country_code=country_code_value,
        error_message='',
        raw_profile=profile,
    )


def default_admin_settings() -> AdminSettings:
    return AdminSettings(coupon_code=settings.default_coupon_code)


def get_admin_settings() -> AdminSettings:
    setting_value = _get_setting_value('admin_settings')

    if setting_value is None:
        defaults = default_admin_settings()
        save_admin_settings(defaults)
        return defaults

    return AdminSettings.model_validate_json(setting_value)


def save_admin_settings(payload: AdminSettings) -> AdminSettings:
    normalized_payload = payload.model_copy(update={'coupon_code': payload.coupon_code or settings.default_coupon_code})
    _save_setting_value('admin_settings', normalized_payload.model_dump_json())

    return normalized_payload


def get_shopify_connection() -> ShopifyConnectionPayload | None:
    setting_value = _get_setting_value(SHOPIFY_CONNECTION_KEY)

    if setting_value is None:
        return None

    return ShopifyConnectionPayload.model_validate_json(setting_value)


def get_shopify_connection_status() -> ShopifyConnectionStatus:
    connection = get_shopify_connection()

    if not connection:
        return ShopifyConnectionStatus(connected=False, shop_domain='')

    return ShopifyConnectionStatus(connected=True, shop_domain=connection.shop_domain)


def save_shopify_connection(payload: ShopifyConnectionPayload) -> ShopifyConnectionStatus:
    _save_setting_value(SHOPIFY_CONNECTION_KEY, payload.model_dump_json())
    return ShopifyConnectionStatus(connected=True, shop_domain=payload.shop_domain)


def get_public_settings() -> PublicSettingsResponse:
    admin_settings = get_admin_settings()
    google_is_configured = bool(admin_settings.google.client_id)
    otp_is_configured = bool(
        admin_settings.otp.firebase_api_key
        and admin_settings.otp.firebase_project_id
        and admin_settings.otp.firebase_app_id
        and admin_settings.otp.service_account_json
    )
    truecaller_is_configured = bool(
        admin_settings.truecaller.verification_mode == 'passthrough'
        or admin_settings.truecaller.client_id
    )

    return PublicSettingsResponse(
        coupon_code=admin_settings.coupon_code,
        privacy_policy_url=admin_settings.privacy_policy_url,
        terms_of_service_url=admin_settings.terms_of_service_url,
        basil_checkout=admin_settings.basil_checkout,
        providers={
            'google': {
                'enabled': admin_settings.google.enabled,
                'preview_only': admin_settings.google.enabled and not google_is_configured,
                'client_id': admin_settings.google.client_id,
                'one_tap_enabled': admin_settings.google.one_tap_enabled,
            },
            'otp': {
                'enabled': admin_settings.otp.enabled,
                'preview_only': admin_settings.otp.enabled and not otp_is_configured,
                'firebase_api_key': admin_settings.otp.firebase_api_key,
                'firebase_auth_domain': admin_settings.otp.firebase_auth_domain,
                'firebase_project_id': admin_settings.otp.firebase_project_id,
                'firebase_app_id': admin_settings.otp.firebase_app_id,
                'firebase_messaging_sender_id': admin_settings.otp.firebase_messaging_sender_id,
            },
            'truecaller': {
                'enabled': admin_settings.truecaller.enabled,
                'preview_only': admin_settings.truecaller.enabled and not truecaller_is_configured,
                'button_text': admin_settings.truecaller.button_text,
                'sdk_script_url': admin_settings.truecaller.sdk_script_url,
                'start_url': admin_settings.truecaller.start_url,
                'verification_mode': admin_settings.truecaller.verification_mode,
            },
            'email_enabled': admin_settings.features.email_enabled,
        },
    )


def row_to_lead(row: sqlite3.Row) -> LeadRecord:
    return LeadRecord.model_validate({key: row[key] for key in row.keys()})


def update_lead_customer_id(lead_id: int, customer_id: str) -> LeadRecord:
    with get_connection() as connection:
        connection.execute(
            'UPDATE leads SET customer_id = ? WHERE id = ?',
            (customer_id, lead_id),
        )
        row = connection.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()

    if row is None:
        raise RuntimeError('Lead update failed unexpectedly.')

    return row_to_lead(row)


def update_lead_email(lead_id: int, phone: str, email: str) -> LeadRecord:
    with get_connection() as connection:
        row = connection.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()

        if row is None:
            raise RuntimeError('Lead record could not be found.')

        if (row['phone'] or '').strip() != phone:
            raise RuntimeError('Lead verification failed for this email update.')

        connection.execute(
            'UPDATE leads SET email = ? WHERE id = ?',
            (email, lead_id),
        )
        updated_row = connection.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()

    if updated_row is None:
        raise RuntimeError('Lead email update failed unexpectedly.')

    return row_to_lead(updated_row)


def insert_lead(payload: LeadCreate, coupon_code: str | None = None) -> LeadRecord:
    created_at = datetime.now(timezone.utc).isoformat()
    resolved_coupon_code = coupon_code or get_admin_settings().coupon_code or settings.default_coupon_code

    with get_connection() as connection:
        cursor = connection.execute(
            '''
            INSERT INTO leads (
                source,
                provider,
                name,
                email,
                phone,
                consent,
                page_type,
                page_url,
                customer_id,
                cart_item_count,
                cart_total_cents,
                coupon_code,
                captured_at,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                payload.source,
                payload.provider,
                payload.name,
                payload.email,
                payload.phone,
                1 if payload.consent else 0,
                payload.page_type,
                payload.page_url,
                payload.customer_id,
                payload.cart_item_count,
                payload.cart_total_cents,
                resolved_coupon_code,
                payload.captured_at.isoformat(),
                created_at,
            ),
        )
        row = connection.execute('SELECT * FROM leads WHERE id = ?', (cursor.lastrowid,)).fetchone()

    if row is None:
        raise RuntimeError('Lead insert failed unexpectedly.')

    return row_to_lead(row)


def _sanitize_tag_fragment(value: str) -> str:
    normalized = re.sub(r'[^a-z0-9]+', '-', (value or '').strip().lower()).strip('-')
    return normalized or 'unknown'


def _build_shopify_tags(lead: LeadRecord) -> list[str]:
    tags = ['anu-login', 'anu-login-lead']

    if lead.provider:
        tags.append(f'anu-provider-{_sanitize_tag_fragment(lead.provider)}')

    if lead.coupon_code:
        tags.append(f'anu-coupon-{_sanitize_tag_fragment(lead.coupon_code)}')

    return tags


def _split_name(full_name: str | None) -> tuple[str, str]:
    value = (full_name or '').strip()

    if not value:
        return '', ''

    parts = value.split()

    if len(parts) == 1:
        return parts[0], ''

    return parts[0], ' '.join(parts[1:])


def _quote_search_value(value: str) -> str:
    escaped = value.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


def _coerce_customer_gid(customer_id: str | None) -> str | None:
    value = (customer_id or '').strip()

    if not value:
        return None

    if value.startswith('gid://shopify/Customer/'):
        return value

    if value.isdigit():
        return f'gid://shopify/Customer/{value}'

    return None


def _shopify_graphql_request(connection: ShopifyConnectionPayload, query: str, variables: dict[str, object]) -> dict[str, object]:
    request_body = json.dumps({'query': query, 'variables': variables}).encode('utf-8')
    request = urllib.request.Request(
        url=f'https://{connection.shop_domain}/admin/api/{settings.shopify_admin_api_version}/graphql.json',
        data=request_body,
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': connection.access_token,
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as error:
        response_body = error.read().decode('utf-8', errors='ignore')
        raise RuntimeError(f'Shopify API request failed with status {error.code}: {response_body or error.reason}') from error
    except urllib.error.URLError as error:
        raise RuntimeError(f'Shopify API request failed: {error.reason}') from error

    if payload.get('errors'):
        raise RuntimeError(f"Shopify GraphQL error: {payload['errors']}")

    return payload.get('data') or {}


def _raise_shopify_user_errors(operation: str, user_errors: list[dict[str, object]] | None) -> None:
    if not user_errors:
        return

    messages = '; '.join(str(error.get('message') or 'Unknown Shopify error') for error in user_errors)
    raise RuntimeError(f'{operation} failed: {messages}')


def _find_shopify_customer(lead: LeadRecord, connection: ShopifyConnectionPayload) -> str | None:
    known_customer_id = _coerce_customer_gid(lead.customer_id)

    if known_customer_id:
        return known_customer_id

    search_parts: list[str] = []

    if lead.email:
        search_parts.append(f'email:{_quote_search_value(lead.email)}')

    if lead.phone:
        search_parts.append(f'phone:{_quote_search_value(lead.phone)}')

    if not search_parts:
        return None

    data = _shopify_graphql_request(
        connection,
        '''
        query FindCustomer($query: String!) {
          customers(first: 1, query: $query) {
            nodes {
              id
            }
          }
        }
        ''',
        {'query': ' OR '.join(search_parts)},
    )

    customers = ((data.get('customers') or {}).get('nodes') or [])

    if not customers:
        return None

    return customers[0].get('id')


def _create_or_update_shopify_customer(lead: LeadRecord, connection: ShopifyConnectionPayload) -> str | None:
    existing_customer_id = _find_shopify_customer(lead, connection)
    first_name, last_name = _split_name(lead.name)

    customer_input: dict[str, object] = {}

    if existing_customer_id:
        customer_input['id'] = existing_customer_id

    if first_name:
        customer_input['firstName'] = first_name

    if last_name:
        customer_input['lastName'] = last_name

    if lead.email:
        customer_input['email'] = lead.email

    if lead.phone:
        customer_input['phone'] = lead.phone

    if not existing_customer_id:
        customer_input['tags'] = _build_shopify_tags(lead)

        data = _shopify_graphql_request(
            connection,
            '''
            mutation CreateCustomer($input: CustomerInput!) {
              customerCreate(input: $input) {
                customer {
                  id
                }
                userErrors {
                  message
                }
              }
            }
            ''',
            {'input': customer_input},
        )
        payload = data.get('customerCreate') or {}
        _raise_shopify_user_errors('customerCreate', payload.get('userErrors'))
        customer = payload.get('customer') or {}
        return customer.get('id')

    if len(customer_input) > 1:
        data = _shopify_graphql_request(
            connection,
            '''
            mutation UpdateCustomer($input: CustomerInput!) {
              customerUpdate(input: $input) {
                customer {
                  id
                }
                userErrors {
                  message
                }
              }
            }
            ''',
            {'input': customer_input},
        )
        payload = data.get('customerUpdate') or {}
        _raise_shopify_user_errors('customerUpdate', payload.get('userErrors'))

    tags_data = _shopify_graphql_request(
        connection,
        '''
        mutation AddCustomerTags($id: ID!, $tags: [String!]!) {
          tagsAdd(id: $id, tags: $tags) {
            node {
              id
            }
            userErrors {
              message
            }
          }
        }
        ''',
        {'id': existing_customer_id, 'tags': _build_shopify_tags(lead)},
    )
    tags_payload = tags_data.get('tagsAdd') or {}
    _raise_shopify_user_errors('tagsAdd', tags_payload.get('userErrors'))
    return existing_customer_id


def sync_lead_to_shopify_customer(lead: LeadRecord) -> LeadRecord:
    admin_settings = get_admin_settings()

    if not admin_settings.features.auto_shopify_sync:
        return lead

    connection = get_shopify_connection()

    if connection is None:
        logger.warning('Skipping Shopify sync for lead %s because no shop connection is registered.', lead.id)
        return lead

    if not lead.email and not lead.phone and not lead.customer_id:
        logger.warning('Skipping Shopify sync for lead %s because no customer identity is available.', lead.id)
        return lead

    try:
        customer_id = _create_or_update_shopify_customer(lead, connection)
    except Exception as error:  # pragma: no cover - depends on external Shopify API state
        logger.warning('Shopify sync failed for lead %s: %s', lead.id, error)
        return lead

    if not customer_id or customer_id == lead.customer_id:
        return lead

    return update_lead_customer_id(lead.id, customer_id)


def list_leads(limit: int = 50, search: str | None = None) -> tuple[int, list[LeadRecord]]:
    search_term = (search or '').strip()
    conditions: list[str] = []
    parameters: list[object] = []

    if search_term:
        conditions.append('(COALESCE(name, "") LIKE ? OR COALESCE(email, "") LIKE ? OR COALESCE(phone, "") LIKE ?)')
        wildcard = f'%{search_term}%'
        parameters.extend([wildcard, wildcard, wildcard])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ''

    with get_connection() as connection:
        total = connection.execute(f'SELECT COUNT(*) AS total FROM leads {where_clause}', parameters).fetchone()['total']
        rows = connection.execute(
            f'''
            SELECT *
            FROM leads
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
            ''',
            [*parameters, limit],
        ).fetchall()

    return total, [row_to_lead(row) for row in rows]


def get_dashboard_summary() -> dict[str, object]:
    today = datetime.now(timezone.utc).date().isoformat()

    with get_connection() as connection:
        total_row = connection.execute('SELECT COUNT(*) AS total FROM leads').fetchone()
        today_row = connection.execute(
            'SELECT COUNT(*) AS total FROM leads WHERE substr(created_at, 1, 10) = ?',
            (today,),
        ).fetchone()
        provider_rows = connection.execute(
            'SELECT provider, COUNT(*) AS total FROM leads GROUP BY provider ORDER BY total DESC'
        ).fetchall()

    return {
        'total_leads': int(total_row['total']) if total_row else 0,
        'today_leads': int(today_row['total']) if today_row else 0,
        'provider_breakdown': {row['provider']: int(row['total']) for row in provider_rows},
    }


def export_leads_csv(search: str | None = None) -> str:
    _, leads = list_leads(limit=5000, search=search)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            'id',
            'source',
            'provider',
            'name',
            'email',
            'phone',
            'consent',
            'page_type',
            'page_url',
            'customer_id',
            'cart_item_count',
            'cart_total_cents',
            'coupon_code',
            'captured_at',
            'created_at',
        ]
    )

    for lead in leads:
        writer.writerow(
            [
                lead.id,
                lead.source,
                lead.provider,
                lead.name or '',
                lead.email or '',
                lead.phone or '',
                'true' if lead.consent else 'false',
                lead.page_type or '',
                lead.page_url or '',
                lead.customer_id or '',
                lead.cart_item_count,
                lead.cart_total_cents,
                lead.coupon_code,
                lead.captured_at.isoformat(),
                lead.created_at.isoformat(),
            ]
        )

    return output.getvalue()
