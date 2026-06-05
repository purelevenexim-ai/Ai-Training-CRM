from __future__ import annotations

import sqlite3

from app.config import settings


def get_db_connection() -> sqlite3.Connection:
    """Lightweight runtime DB connector without importing the full storage layer."""
    connection = sqlite3.connect(settings.database_path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    if not _table_exists(connection, table_name):
        return set()
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_definition: str) -> None:
    column_name = column_definition.split()[0]
    if column_name in _table_columns(connection, table_name):
        return
    try:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")
    except Exception:
        pass


def ensure_runtime_tables() -> None:
    """Create only the tables needed by lightweight AI runtime paths."""
    with get_db_connection() as connection:
        connection.execute(
            """
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
            """
        )
        _ensure_column(connection, "conversation_state", "customer_id TEXT")
        _ensure_column(connection, "conversation_state", "language TEXT")
        _ensure_column(connection, "conversation_state", "active_product TEXT")
        _ensure_column(connection, "conversation_state", "latest_intent TEXT")
        _ensure_column(connection, "conversation_state", "price_shared INTEGER NOT NULL DEFAULT 0")
        _ensure_column(connection, "conversation_state", "quantity_selected TEXT")
        _ensure_column(connection, "conversation_state", "address_received INTEGER NOT NULL DEFAULT 0")
        _ensure_column(connection, "conversation_state", "pincode_received TEXT")
        _ensure_column(connection, "conversation_state", "payment_claimed INTEGER NOT NULL DEFAULT 0")
        _ensure_column(connection, "conversation_state", "payment_screenshot_received INTEGER NOT NULL DEFAULT 0")
        _ensure_column(connection, "conversation_state", "defer_intent TEXT")
        _ensure_column(connection, "conversation_state", "followups_allowed INTEGER NOT NULL DEFAULT 1")
        _ensure_column(connection, "conversation_state", "journey_stage TEXT")
        _ensure_column(connection, "conversation_state", "last_ai_reply_hash TEXT")
        _ensure_column(connection, "conversation_state", "last_ai_reply_at TEXT")
        connection.execute(
            """
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
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_outgoing_replies (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                reply_text TEXT NOT NULL,
                intent TEXT NOT NULL,
                escalated INTEGER NOT NULL DEFAULT 0,
                send_status TEXT NOT NULL DEFAULT 'pending',
                message_mode TEXT NOT NULL DEFAULT 'text',
                media_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_events (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                event_id TEXT NOT NULL,
                conversation_id TEXT,
                customer_phone TEXT,
                event_type TEXT,
                payload_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(source, event_id),
                UNIQUE(source, payload_hash)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS message_processing_locks (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                incoming_message_id TEXT NOT NULL,
                conversation_id TEXT,
                owner TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'processing',
                reply_message_id TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(customer_id, incoming_message_id)
            )
            """
        )
        _ensure_column(connection, "message_processing_locks", "reason TEXT")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS customer_journey_state (
                customer_id TEXT PRIMARY KEY,
                current_stage TEXT NOT NULL DEFAULT 'new_customer',
                active_product TEXT,
                active_language TEXT NOT NULL DEFAULT 'manglish',
                last_intent TEXT,
                last_customer_message_id TEXT,
                last_ai_reply_id TEXT,
                waiting_for TEXT,
                payment_status TEXT NOT NULL DEFAULT 'not_started',
                order_status TEXT NOT NULL DEFAULT 'not_started',
                followup_stage TEXT,
                last_interaction_at TEXT NOT NULL,
                expires_at TEXT,
                context_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS message_decisions (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                incoming_message_id TEXT NOT NULL,
                incoming_message TEXT,
                normalized_text TEXT,
                detected_type TEXT,
                detected_intent TEXT,
                confidence REAL NOT NULL DEFAULT 0,
                selected_owner TEXT,
                decision_reason TEXT,
                skipped_ai INTEGER NOT NULL DEFAULT 0,
                prompt_used_id TEXT,
                reply_message_id TEXT,
                route TEXT,
                score REAL NOT NULL DEFAULT 0,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(customer_id, incoming_message_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_reply_audit (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                incoming_message_id TEXT NOT NULL,
                reply_message_id TEXT,
                intent_match_score REAL NOT NULL DEFAULT 0,
                tone_score REAL NOT NULL DEFAULT 0,
                length_score REAL NOT NULL DEFAULT 0,
                journey_score REAL NOT NULL DEFAULT 0,
                duplicate_risk_score REAL NOT NULL DEFAULT 0,
                overall_score REAL NOT NULL DEFAULT 0,
                issues_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS button_action_mappings (
                id TEXT PRIMARY KEY,
                button_text TEXT NOT NULL,
                normalized_button_text TEXT NOT NULL UNIQUE,
                action TEXT NOT NULL,
                language TEXT,
                next_stage TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        now_for_seed = "1970-01-01T00:00:00+00:00"
        default_buttons = [
            ("Buy Now", "buy now", "ASK_ORDER_DETAILS", "", "waiting_for_address"),
            ("വിലാസം നൽകുക", "വിലാസം നൽകുക", "ASK_ADDRESS_FORMAT", "malayalam", "waiting_for_address"),
            ("🇮🇳 മലയാളം", "മലയാളം", "SET_LANGUAGE_ML", "malayalam", "language_selected"),
            ("English", "english", "SET_LANGUAGE_EN", "english", "language_selected"),
            ("🍃 Spices Price", "spices price", "SHOW_CATEGORY_PRICE", "english", "product_interest"),
            ("🍃 വില കാണം", "വില കാണം", "SHOW_PRICE_ML", "malayalam", "product_interest"),
        ]
        for button_text, normalized, action, language, next_stage in default_buttons:
            connection.execute(
                """
                INSERT OR IGNORE INTO button_action_mappings
                (id, button_text, normalized_button_text, action, language, next_stage, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    f"default:{normalized}",
                    button_text,
                    normalized,
                    action,
                    language,
                    next_stage,
                    now_for_seed,
                    now_for_seed,
                ),
            )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_conversation_sessions (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'learning',
                session_started_at TEXT NOT NULL,
                last_customer_message_at TEXT,
                last_ai_response_at TEXT,
                expires_at TEXT NOT NULL,
                context_summary TEXT,
                last_language TEXT,
                last_tone TEXT,
                last_intent TEXT,
                last_product TEXT,
                last_quantity TEXT,
                customer_stage TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_reply_jobs (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                customer_name TEXT NOT NULL DEFAULT 'Customer',
                source_message_id TEXT NOT NULL,
                source_message TEXT NOT NULL,
                message_type TEXT NOT NULL DEFAULT 'text',
                status TEXT NOT NULL DEFAULT 'pending',
                delay_type TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                locked_at TEXT,
                sent_at TEXT,
                skipped_reason TEXT,
                result_json TEXT NOT NULL DEFAULT '{}',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_decision_logs (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                customer_phone TEXT,
                incoming_message TEXT,
                normalized_message TEXT,
                detected_language TEXT,
                detected_product TEXT,
                detected_intent TEXT,
                matched_template TEXT,
                generated_response TEXT,
                final_route_owner TEXT,
                wabis_state_transition TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS customer_journeys (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft',
                applies_to TEXT NOT NULL DEFAULT 'all_products',
                selected_products_json TEXT NOT NULL DEFAULT '[]',
                trigger_type TEXT NOT NULL DEFAULT 'product_interest',
                stop_on_reply INTEGER NOT NULL DEFAULT 1,
                stop_on_order INTEGER NOT NULL DEFAULT 1,
                stop_on_not_interested INTEGER NOT NULL DEFAULT 1,
                stop_on_stop INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS customer_journey_steps (
                id TEXT PRIMARY KEY,
                journey_id TEXT NOT NULL,
                step_order INTEGER NOT NULL,
                delay_value INTEGER NOT NULL,
                delay_unit TEXT NOT NULL DEFAULT 'minutes',
                message_type TEXT NOT NULL DEFAULT 'text',
                message_text TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS customer_journey_assignments (
                id TEXT PRIMARY KEY,
                journey_id TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                product_key TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                started_at TEXT NOT NULL,
                stopped_at TEXT,
                stop_reason TEXT,
                context_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS customer_journey_logs (
                id TEXT PRIMARY KEY,
                journey_id TEXT,
                step_id TEXT,
                customer_phone TEXT NOT NULL,
                product_key TEXT,
                event_type TEXT NOT NULL,
                message_text TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS monitoring_alerts (
                id TEXT PRIMARY KEY,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_monitor_journeys (
                journey_id TEXT PRIMARY KEY,
                customer_phone TEXT NOT NULL,
                conversation_id TEXT,
                channel TEXT NOT NULL DEFAULT 'whatsapp',
                journey_status TEXT NOT NULL DEFAULT 'open',
                journey_stage TEXT,
                detected_language TEXT,
                active_product TEXT,
                latest_intent TEXT,
                total_messages INTEGER NOT NULL DEFAULT 0,
                customer_messages INTEGER NOT NULL DEFAULT 0,
                ai_messages INTEGER NOT NULL DEFAULT 0,
                automation_messages INTEGER NOT NULL DEFAULT 0,
                issue_count INTEGER NOT NULL DEFAULT 0,
                success_score REAL NOT NULL DEFAULT 0,
                last_issue TEXT,
                first_event_at TEXT,
                last_event_at TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_monitor_events (
                id TEXT PRIMARY KEY,
                journey_id TEXT NOT NULL,
                event_id TEXT,
                customer_phone TEXT NOT NULL,
                conversation_id TEXT,
                occurred_at TEXT NOT NULL,
                actor_type TEXT NOT NULL,
                source TEXT NOT NULL,
                message_text TEXT,
                detected_language TEXT,
                detected_product TEXT,
                detected_intent TEXT,
                route_owner TEXT,
                guard_action TEXT,
                issue_tags_json TEXT NOT NULL DEFAULT '[]',
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_monitor_issues (
                id TEXT PRIMARY KEY,
                journey_id TEXT NOT NULL,
                event_id TEXT,
                customer_phone TEXT NOT NULL,
                conversation_id TEXT,
                occurred_at TEXT NOT NULL,
                issue_type TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'medium',
                detail TEXT NOT NULL DEFAULT '',
                suggested_fix TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_conversation_state_owner ON conversation_state(owner)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_conversation_state_expires ON conversation_state(expires_at)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_product_followups_phone ON product_journey_followups(phone, scheduled_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_product_followups_due ON product_journey_followups(sent, scheduled_at)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_ai_outgoing_phone ON ai_outgoing_replies(customer_phone, created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_ai_outgoing_conversation ON ai_outgoing_replies(conversation_id, created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_ai_outgoing_status ON ai_outgoing_replies(send_status, created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_processed_events_phone ON processed_events(customer_phone, created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_message_locks_customer ON message_processing_locks(customer_id, created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_message_locks_owner ON message_processing_locks(owner, status, created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_customer_journey_state_stage ON customer_journey_state(current_stage, updated_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_message_decisions_customer ON message_decisions(customer_id, created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_message_decisions_owner ON message_decisions(selected_owner, created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_message_decisions_intent ON message_decisions(detected_intent, created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_ai_reply_audit_customer ON ai_reply_audit(customer_id, created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_button_action_mappings_active ON button_action_mappings(is_active, normalized_button_text)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_ai_sessions_phone ON ai_conversation_sessions(customer_phone, expires_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_ai_jobs_due ON ai_reply_jobs(status, scheduled_at)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_ai_jobs_phone ON ai_reply_jobs(customer_phone, created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_ai_decisions_phone ON ai_decision_logs(customer_phone, created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_customer_journeys_status ON customer_journeys(status, trigger_type)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_customer_journey_steps ON customer_journey_steps(journey_id, step_order)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_customer_journey_assignments ON customer_journey_assignments(customer_phone, status)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_customer_journey_logs ON customer_journey_logs(customer_phone, created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_created ON monitoring_alerts(created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_ai_monitor_journeys_updated ON ai_monitor_journeys(updated_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_ai_monitor_journeys_phone ON ai_monitor_journeys(customer_phone, last_event_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_ai_monitor_events_journey ON ai_monitor_events(journey_id, occurred_at ASC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_ai_monitor_events_phone ON ai_monitor_events(customer_phone, occurred_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_ai_monitor_issues_journey ON ai_monitor_issues(journey_id, occurred_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_ai_monitor_issues_type ON ai_monitor_issues(issue_type, occurred_at DESC)")

        _ensure_column(connection, "product_journey_followups", "message_mode TEXT NOT NULL DEFAULT 'text'")
        _ensure_column(connection, "product_journey_followups", "media_json TEXT")
        _ensure_column(connection, "ai_outgoing_replies", "message_mode TEXT NOT NULL DEFAULT 'text'")
        _ensure_column(connection, "ai_outgoing_replies", "media_json TEXT")
        connection.commit()
