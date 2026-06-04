"""
CRM Database Models for Pureleven
Stores customer data from Shopify, GA4, Google Ads, Meta, and Email
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Date, Text, JSON, Boolean, ForeignKey, Table, UniqueConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4

Base = declarative_base()


class Customer(Base):
    """Unified customer record across all platforms"""
    __tablename__ = "crm_customers"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    shopify_customer_id = Column(String(50), unique=True, nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    phone = Column(String(20), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    
    # Shopify fields
    shopify_created_at = Column(DateTime, nullable=True)
    shopify_updated_at = Column(DateTime, nullable=True)
    tags = Column(JSON, nullable=True)  # Shopify customer tags
    
    # Aggregated metrics
    total_spent = Column(Float, default=0.0)
    orders_count = Column(Integer, default=0)
    last_order_date = Column(DateTime, nullable=True)
    
    # Contact preferences
    email_subscribed = Column(Boolean, default=False)
    sms_subscribed = Column(Boolean, default=False)

    # Attribution / identity linkage (Phase 1 v2)
    gclid = Column(String(255), nullable=True)
    gbraid = Column(String(255), nullable=True)
    wbraid = Column(String(255), nullable=True)
    fbclid = Column(String(255), nullable=True)
    fbp = Column(String(255), nullable=True)
    fbc = Column(String(255), nullable=True)
    session_id = Column(String(255), nullable=True, index=True)
    identity_id = Column(String(36), nullable=True, index=True)
    
    # Lead management fields (Sprint 1)
    is_lead = Column(Boolean, default=False, index=True)
    lead_source = Column(String(50), nullable=True)  # contact_form, google_forms, meta_ads, manual, etc.
    lead_status = Column(String(50), nullable=True)  # new, contacted, qualified, customer, lost
    lead_score = Column(Float, nullable=True)  # 0.0-1.0 propensity score
    lead_created_at = Column(DateTime, nullable=True)
    contacted_at = Column(DateTime, nullable=True)
    qualified_at = Column(DateTime, nullable=True)
    
    # Propensity & enrichment (Sprint 1)
    propensity_score = Column(Float, default=0.5)  # 0.0-1.0, default 0.5
    propensity_updated_at = Column(DateTime, nullable=True)
    company = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    industry = Column(String(255), nullable=True)
    
    # Metadata
    meta_data = Column(JSON, nullable=True)  # Custom fields, interests, etc.
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    orders = relationship("Order", back_populates="customer")
    events = relationship("Event", back_populates="customer")
    
    __table_args__ = (
        Index('idx_email_phone', 'email', 'phone'),
        Index('idx_shopify_id', 'shopify_customer_id'),
    )


class Order(Base):
    """Customer order from Shopify"""
    __tablename__ = "crm_orders"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    shopify_order_id = Column(String(50), unique=True, nullable=True, index=True)
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), index=True)
    
    email = Column(String(255), nullable=True)
    order_date = Column(DateTime, nullable=True)
    total_amount = Column(Float)
    currency = Column(String(3), default="INR")
    status = Column(String(50), nullable=True)  # pending, completed, cancelled, etc.
    
    # Order details
    items = Column(JSON)  # Array of {item_id, name, price, quantity, category}
    shipping_address = Column(JSON, nullable=True)
    
    # Attribution
    utm_source = Column(String(100), nullable=True)
    utm_medium = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)
    campaign_id = Column(String(100), nullable=True)

    # COD + offline attribution (Phase 1 v2)
    gclid = Column(String(255), nullable=True)
    gbraid = Column(String(255), nullable=True)
    wbraid = Column(String(255), nullable=True)
    fbclid = Column(String(255), nullable=True)
    fbp = Column(String(255), nullable=True)
    fbc = Column(String(255), nullable=True)
    utm_content = Column(String(255), nullable=True)
    utm_term = Column(String(255), nullable=True)
    payment_method = Column(String(50), nullable=True)   # cod / upi / card / prepaid
    delivered_at = Column(DateTime, nullable=True)
    rto = Column(Boolean, default=False)
    offline_conversion_sent = Column(Boolean, default=False)

    # Phase 2: Email lifecycle tracking flags
    review_email_sent       = Column(Boolean, default=False)  # Day-7 review request
    repeat_email_sent       = Column(Boolean, default=False)  # Day-21 repeat purchase nudge
    replenishment_email_sent= Column(Boolean, default=False)  # Day-35 replenishment reminder
    winback_email_sent      = Column(Boolean, default=False)  # Day-60+ win-back campaign

    # Phase 1: Fraud & dedup
    fraud_score = Column(Integer, default=0)                  # 0-100, higher = more risky
    capi_suppressed = Column(Boolean, default=False)          # True if CAPI send was blocked
    capi_status = Column(String(20), default="pending", nullable=True)
    capi_attempts = Column(Integer, default=0)
    capi_last_error = Column(Text, nullable=True)
    capi_sent_at = Column(DateTime, nullable=True)
    conversion_risk_reason = Column(String(255), nullable=True)

    # Destination-specific delivery observability
    meta_event_id = Column(String(100), nullable=True)
    meta_status = Column(String(20), nullable=True)
    meta_sent_at = Column(DateTime, nullable=True)
    meta_response = Column(Text, nullable=True)
    meta_error = Column(Text, nullable=True)

    google_status = Column(String(20), nullable=True)
    google_sent_at = Column(DateTime, nullable=True)
    google_response = Column(Text, nullable=True)
    google_error = Column(Text, nullable=True)

    ga4_status = Column(String(20), nullable=True)
    ga4_sent_at = Column(DateTime, nullable=True)
    ga4_response = Column(Text, nullable=True)
    ga4_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    customer = relationship("Customer", back_populates="orders")
    
    __table_args__ = (
        Index('idx_customer_id_date', 'customer_id', 'order_date'),
    )


class Event(Base):
    """Customer interaction event from any source"""
    __tablename__ = "crm_events"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), index=True, nullable=True)
    email = Column(String(255), nullable=True, index=True)
    
    event_type = Column(String(100), index=True)  # page_view, add_to_cart, purchase, email_open, etc.
    source = Column(String(50), index=True)  # shopify, ga4, google_ads, meta, email
    
    event_data = Column(JSON)  # Event-specific data

    # Session linkage + N8N dedup (Phase 1 v2)
    session_id = Column(String(255), nullable=True, index=True)
    n8n_notified = Column(Boolean, default=False)
    
    timestamp = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    customer = relationship("Customer", back_populates="events")
    
    __table_args__ = (
        Index('idx_customer_timestamp', 'customer_id', 'timestamp'),
        Index('idx_source_type', 'source', 'event_type'),
    )


class Segment(Base):
    """Customer segment/audience definition"""
    __tablename__ = "crm_segments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), unique=True)
    description = Column(String(1000), nullable=True)
    
    # Segmentation rules (e.g., "min_spend > 5000", "last_order < 30 days", etc.)
    rule_set = Column(JSON)
    
    # Computed metrics
    customer_count = Column(Integer, default=0)
    
    # Configuration
    is_active = Column(Boolean, default=True)
    auto_update = Column(Boolean, default=True)  # Auto-recalculate membership
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Attribution(Base):
    """Campaign attribution for orders"""
    __tablename__ = "crm_attributions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    order_id = Column(String(36), ForeignKey("crm_orders.id"), index=True)
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), index=True)
    
    # Attribution source
    source_type = Column(String(50))  # google_ads, meta, email, organic, direct
    campaign_id = Column(String(100), nullable=True)
    campaign_name = Column(String(255), nullable=True)
    ad_id = Column(String(100), nullable=True)
    
    # Click/touchpoint info
    gclid = Column(String(255), nullable=True)  # Google click ID
    fbp = Column(String(255), nullable=True)   # Facebook pixel ID
    
    # Attribution value
    attributed_amount = Column(Float)
    attributed_percentage = Column(Float)  # 0-100, portion of order attributed to this source
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_order_campaign', 'order_id', 'campaign_id'),
    )


class ConversionFeed(Base):
    """Incoming conversion data from GA4, Google Ads, Meta for unification"""
    __tablename__ = "crm_conversion_feeds"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Source & ID
    source = Column(String(50), index=True)  # ga4, google_ads, meta, shopify
    external_id = Column(String(255), index=True)  # Conversion ID from source
    
    # Customer identifier
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(20), nullable=True)
    shopify_customer_id = Column(String(50), nullable=True)
    
    # Conversion details
    conversion_type = Column(String(100))  # purchase, add_to_cart, view_item, etc.
    conversion_value = Column(Float)
    currency = Column(String(3), default="INR")
    
    # Campaign info
    campaign_id = Column(String(100), nullable=True)
    campaign_name = Column(String(255), nullable=True)
    gclid = Column(String(255), nullable=True)
    fbp = Column(String(255), nullable=True)
    
    # Status & metadata
    is_matched = Column(Boolean, default=False)  # Whether matched to a customer
    matched_customer_id = Column(String(36), ForeignKey("crm_customers.id"), nullable=True)
    meta_data = Column(JSON, nullable=True)
    
    timestamp = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_conversion_source_time', 'source', 'created_at'),
    )


class TrackingEvent(Base):
    """Per-destination tracking delivery log for order events."""
    __tablename__ = "tracking_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    order_id = Column(String(50), nullable=False, index=True)
    destination = Column(String(20), nullable=False, index=True)  # meta | google | ga4
    event_name = Column(String(100), nullable=False)
    event_id = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, index=True)  # sent | failed | skipped
    response_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    attempt = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('idx_tracking_events_order_destination', 'order_id', 'destination'),
        Index('idx_tracking_events_status_created', 'status', 'created_at'),
    )


class CustomerIdentity(Base):
    """Deterministic identity keys attached to a canonical CRM customer."""
    __tablename__ = "crm_customer_identities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    canonical_customer_id = Column(String(36), ForeignKey("crm_customers.id"), nullable=False, index=True)
    identity_type = Column(String(50), nullable=False)  # email | phone | shopify_customer_id | gclid | fbp | fbc | ga_client_id | session_id
    identity_value = Column(String(500), nullable=False)
    identity_hash = Column(String(64), nullable=False, index=True)
    confidence_score = Column(Float, default=1.0)
    source = Column(String(100), nullable=True)
    first_seen_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_seen_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('identity_type', 'identity_hash', name='uq_customer_identity_type_hash'),
        Index('idx_customer_identity_customer_type', 'canonical_customer_id', 'identity_type'),
    )


class IdentityMergeHistory(Base):
    """Audit log for customer identity merges and manual review decisions."""
    __tablename__ = "crm_identity_merge_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    from_customer_id = Column(String(36), ForeignKey("crm_customers.id"), nullable=True, index=True)
    to_customer_id = Column(String(36), ForeignKey("crm_customers.id"), nullable=True, index=True)
    merge_method = Column(String(50), nullable=False)  # deterministic | manual | suggested_probabilistic
    confidence_score = Column(Float, default=1.0)
    matched_fields = Column(JSON, nullable=True)
    reason = Column(String(255), nullable=True)
    status = Column(String(20), default="applied", index=True)  # suggested | applied | rejected | reversed
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    reversed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_identity_merge_to_status', 'to_customer_id', 'status'),
    )


class UnresolvedOrderRef(Base):
    """Manual/bridge order references that could not be resolved to canonical Shopify IDs."""
    __tablename__ = "crm_unresolved_order_refs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    raw_order_ref = Column(String(100), nullable=False, index=True)
    source = Column(String(100), nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    payload = Column(JSON, nullable=True)
    resolution_status = Column(String(30), default="unresolved", index=True)  # unresolved | resolved | ignored
    resolved_shopify_order_id = Column(String(50), nullable=True, index=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_unresolved_order_source_status', 'source', 'resolution_status'),
    )


class AttributionModelConfig(Base):
    """Configurable attribution models for repeatable revenue allocation."""
    __tablename__ = "crm_attribution_model_config"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(80), unique=True, nullable=False, index=True)
    model_type = Column(String(50), nullable=False)  # first_touch | last_touch | linear | position_based | time_decay
    config = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OrderTouchpointAttribution(Base):
    """Derived multi-touch attribution allocation for one order/touchpoint/model."""
    __tablename__ = "crm_order_touchpoint_attribution"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    order_id = Column(String(36), ForeignKey("crm_orders.id"), nullable=False, index=True)
    shopify_order_id = Column(String(50), nullable=True, index=True)
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), nullable=True, index=True)
    touchpoint_event_id = Column(String(36), ForeignKey("crm_events.id"), nullable=True, index=True)
    source = Column(String(50), nullable=False, index=True)
    campaign_id = Column(String(100), nullable=True)
    campaign_name = Column(String(255), nullable=True)
    gclid = Column(String(255), nullable=True)
    fbclid = Column(String(255), nullable=True)
    fbp = Column(String(255), nullable=True)
    fbc = Column(String(255), nullable=True)
    touch_type = Column(String(30), nullable=False)  # first | last | assist | conversion | linear_share
    attribution_model = Column(String(80), nullable=False, index=True)
    model_version = Column(String(20), default="v1")
    lookback_days = Column(Integer, default=30)
    attributed_value = Column(Float, default=0.0)
    attributed_percentage = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        UniqueConstraint('order_id', 'touchpoint_event_id', 'attribution_model', name='uq_order_touchpoint_model'),
        Index('idx_attr_order_model', 'order_id', 'attribution_model'),
        Index('idx_attr_customer_source', 'customer_id', 'source'),
    )


class AudienceMaterializationRun(Base):
    """Run history for CRM/retargeting audience generation jobs."""
    __tablename__ = "crm_audience_materialization_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    audience_key = Column(String(100), nullable=False, index=True)
    audience_type = Column(String(50), nullable=False)  # anonymous | known | customer
    status = Column(String(30), nullable=False, default="started", index=True)
    record_count = Column(Integer, default=0)
    destination = Column(String(50), nullable=True)
    details = Column(JSON, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    finished_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_audience_run_key_started', 'audience_key', 'started_at'),
    )


# ─── PHASE 9 TABLES (created now so migrations run once) ─────────────────────

class AIReview(Base):
    """
    Daily AI-powered ad review records.
    Each row = one scheduled review run (Meta or Google).
    Tracks the AI recommendation, approval status, and execution result.
    """
    __tablename__ = "crm_ai_reviews"

    id                  = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    review_date         = Column(DateTime, nullable=True, index=True)
    review_type         = Column(String(50), nullable=True)   # 'meta' | 'google' | 'combined'
    metrics_json        = Column(JSON, nullable=True)          # Raw platform metrics snapshot
    ai_analysis_json    = Column(JSON, nullable=True)          # Claude API response
    email_sent          = Column(Boolean, default=False)
    approval_status     = Column(String(20), default="pending")  # pending | approved | rejected
    approval_id         = Column(String(100), nullable=True)
    approval_timestamp  = Column(DateTime, nullable=True)
    execution_status    = Column(String(20), nullable=True)    # executed | skipped | failed
    executed_timestamp  = Column(DateTime, nullable=True)
    adjustments_executed= Column(Integer, default=0)
    created_at          = Column(DateTime, default=datetime.utcnow)


class MessageLog(Base):
    """
    Outbound message log for email (SendGrid/Plunk) and WhatsApp (Wabis).
    Used for lifecycle deduplication — prevents duplicate sends.
    Tracks quality (high-priority vs follow-up) for hybrid SendGrid+Plunk routing.
    """
    __tablename__ = "crm_messages"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id     = Column(String(36), ForeignKey("crm_customers.id"), nullable=True, index=True)
    customer_email  = Column(String(255), nullable=True, index=True)
    customer_phone  = Column(String(20), nullable=True)
    channel         = Column(String(50), nullable=True)   # 'email' | 'whatsapp'
    template_id     = Column(String(100), nullable=True)  # e.g. 'review_request_d7'
    status          = Column(String(20), nullable=True)   # sent | delivered | failed | opened
    response_code   = Column(Integer, nullable=True)
    provider        = Column(String(50), nullable=True)   # 'sendgrid' | 'plunk' | 'wabis'
    msg_metadata    = Column(JSON, nullable=True)         # {"quality": true, ...}
    sent_at         = Column(DateTime, nullable=True, index=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        # Prevent duplicate sends for the same customer+template
        UniqueConstraint('customer_email', 'template_id', name='uq_message_customer_template'),
        Index('idx_message_channel_date', 'channel', 'sent_at'),
    )


class AutomationLog(Base):
    """
    N8N automation run log. One row per daily automation batch.
    Tracks which sequences ran, how many messages were sent, and any failures.
    """
    __tablename__ = "crm_automation_log"

    id            = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_date      = Column(DateTime, nullable=True, index=True)
    workflow_name = Column(String(100), nullable=True)    # e.g. 'lifecycle_email_daily'
    sequences_run = Column(Integer, default=0)
    total_sent    = Column(Integer, default=0)
    failures      = Column(Integer, default=0)
    status        = Column(String(20), nullable=True)      # success | partial | failed
    details_json  = Column(JSON, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)


# ─── JOURNEY ORCHESTRATION TABLES ────────────────────────────────────────────

class Journey(Base):
    """
    Journey template definition.
    Each journey = one customer lifecycle scenario (e.g. cart_recovery, welcome).
    Steps are stored as JSON (array of {type, delay_days, action_data}).
    """
    __tablename__ = "crm_journeys"

    id                  = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name                = Column(String(255), unique=True, nullable=False)  # 'cart_recovery'
    description         = Column(String(1000), nullable=True)
    segment_id          = Column(String(36), ForeignKey("crm_segments.id"), nullable=True)
    status              = Column(String(50), default="DRAFT")  # DRAFT | ACTIVE | PAUSED
    entry_trigger       = Column(String(100), nullable=True)   # 'cart_abandon' | 'order_complete' | 'customer_create'
    exit_criteria       = Column(JSON, nullable=True)          # e.g. {"event": "purchase"}
    max_frequency_per_day = Column(Integer, default=2)
    n8n_workflow_id     = Column(String(50), nullable=True)    # N8N workflow webhook ID
    template_json       = Column(JSON, nullable=True)          # Step definitions array
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    instances = relationship("JourneyInstance", back_populates="journey")


class JourneyInstance(Base):
    """
    Active journey enrollment per customer.
    One row per (customer, journey) pair while active.
    Tracks progress through steps and overall result.
    """
    __tablename__ = "crm_journey_instances"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    journey_id      = Column(String(36), ForeignKey("crm_journeys.id"), nullable=False, index=True)
    customer_id     = Column(String(36), ForeignKey("crm_customers.id"), nullable=False, index=True)
    email           = Column(String(255), nullable=True, index=True)
    status          = Column(String(50), default="ACTIVE", index=True)  # ACTIVE | PAUSED | COMPLETED | EXITED
    current_step    = Column(Integer, default=0)
    started_at      = Column(DateTime, default=datetime.utcnow)
    completed_at    = Column(DateTime, nullable=True)
    exit_reason     = Column(String(255), nullable=True)
    result_data     = Column(JSON, nullable=True)   # e.g. {"converted": true, "revenue": 450}
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    journey     = relationship("Journey", back_populates="instances")
    customer    = relationship("Customer")
    steps       = relationship("JourneyStep", back_populates="instance")

    __table_args__ = (
        Index('idx_ji_customer_status', 'customer_id', 'status'),
        Index('idx_ji_journey_status', 'journey_id', 'status'),
        UniqueConstraint('journey_id', 'customer_id', name='uq_journey_customer_active'),
    )


class JourneyStep(Base):
    """
    Individual step execution record within a journey instance.
    One row per step per customer (email send, WhatsApp send, delay, condition, etc.).
    """
    __tablename__ = "crm_journey_steps"

    id                   = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    journey_instance_id  = Column(String(36), ForeignKey("crm_journey_instances.id"), nullable=False, index=True)
    step_index           = Column(Integer, nullable=True)
    step_type            = Column(String(50), nullable=True)   # email | whatsapp | meta_audience | google_audience | delay | condition
    step_name            = Column(String(255), nullable=True)
    action_data          = Column(JSON, nullable=True)         # Template ID, delay days, condition rule
    scheduled_at         = Column(DateTime, nullable=True)
    executed_at          = Column(DateTime, nullable=True)
    status               = Column(String(50), default="PENDING")  # PENDING | EXECUTED | SKIPPED | FAILED
    result               = Column(JSON, nullable=True)            # Provider response: {message_id, status}
    created_at           = Column(DateTime, default=datetime.utcnow)

    instance = relationship("JourneyInstance", back_populates="steps")

    __table_args__ = (
        Index('idx_js_instance', 'journey_instance_id'),
        Index('idx_js_scheduled', 'scheduled_at', 'status'),
    )


# ─── PHASE 4: ATTRIBUTION & A/B TESTING TABLES ───────────────────────────────

class JourneyAttribution(Base):
    """
    Revenue attribution: links a customer order to the journey that drove it.
    Supports first_touch, last_touch, multi_touch attribution models.
    """
    __tablename__ = "crm_journey_attribution"

    id                   = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    journey_id           = Column(String(36), ForeignKey("crm_journeys.id"), nullable=True, index=True)
    journey_instance_id  = Column(String(36), ForeignKey("crm_journey_instances.id"), nullable=True, index=True)
    customer_id          = Column(String(36), ForeignKey("crm_customers.id"), nullable=True, index=True)
    order_id             = Column(String(100), nullable=True, index=True)  # Shopify order ID
    order_value          = Column(Float, default=0.0)
    attributed_revenue   = Column(Float, default=0.0)    # may differ from order_value in multi-touch
    currency             = Column(String(10), default='INR')
    attribution_model    = Column(String(50), default='first_touch')  # first_touch | last_touch | multi_touch
    conversion_date      = Column(DateTime, nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_attr_journey', 'journey_id'),
        Index('idx_attr_order', 'order_id'),
        Index('idx_attr_customer', 'customer_id'),
    )


class JourneyVariant(Base):
    """
    A/B test variant for a journey.
    Multiple variants can exist for one journey (e.g. 50/50 split).
    """
    __tablename__ = "crm_journey_variants"

    id                   = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    journey_id           = Column(String(36), ForeignKey("crm_journeys.id"), nullable=False, index=True)
    variant_name         = Column(String(255), nullable=False)       # 'Control', 'Variant A', 'Variant B'
    traffic_split_pct    = Column(Integer, default=50)               # 0-100 percentage
    template_json        = Column(JSON, nullable=True)               # Override template from base journey
    config_changes       = Column(JSON, nullable=True)               # Specific node changes
    status               = Column(String(50), default='DRAFT')       # DRAFT | ACTIVE | WINNER | PAUSED
    enrollments          = Column(Integer, default=0)
    conversions          = Column(Integer, default=0)
    revenue              = Column(Float, default=0.0)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_variant_journey', 'journey_id'),
    )


class BulkEnrollmentJob(Base):
    """
    Async bulk CSV enrollment job.
    Tracks progress for large customer imports into journeys.
    """
    __tablename__ = "crm_bulk_enrollment_jobs"

    id               = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    journey_id       = Column(String(36), ForeignKey("crm_journeys.id"), nullable=False, index=True)
    status           = Column(String(50), default='PENDING')  # PENDING | RUNNING | COMPLETED | FAILED
    total_rows       = Column(Integer, default=0)
    success_count    = Column(Integer, default=0)
    error_count      = Column(Integer, default=0)
    error_rows       = Column(JSON, nullable=True)   # [{row, email, reason}]
    created_at       = Column(DateTime, default=datetime.utcnow)
    completed_at     = Column(DateTime, nullable=True)
    created_by       = Column(String(255), nullable=True)


# ─── AUTHENTICATION & AUTHORIZATION ──────────────────────────────────────────

class APIKey(Base):
    """
    API authentication key for secure programmatic access.
    Each API key is associated with a name and optional expiration.
    """
    __tablename__ = "crm_api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False)  # e.g. "Mobile App", "N8N Integration"
    key_hash = Column(String(255), unique=True, nullable=False)  # SHA256 hash of actual key
    key_preview = Column(String(8), nullable=True)  # First 8 chars for display: "sk_live_a1b2c3d4..."
    
    # Permissions (future: support roles)
    scope = Column(String(255), default="read:write")  # read | write | admin
    
    # Lifecycle
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True, index=True)  # Optional expiration
    last_used_at = Column(DateTime, nullable=True)
    
    # Metadata
    description = Column(String(500), nullable=True)
    ip_whitelist = Column(JSON, nullable=True)  # List of allowed IPs (optional)
    
    created_by = Column(String(255), nullable=True)  # User who created this key
    
    __table_args__ = (
        Index('idx_apikey_active', 'is_active'),
        Index('idx_apikey_expires', 'expires_at'),
    )


class OfflineConversion(Base):
    """Offline conversion events for Meta CAPI matching"""
    __tablename__ = "crm_offline_conversions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id = Column(String(36), ForeignKey('crm_customers.id'), nullable=True, index=True)
    
    # Conversion details
    conversion_type = Column(String(50), default="Purchase")  # Purchase, Lead, ViewContent, etc
    conversion_value = Column(Float, nullable=True)  # Monetary value
    currency = Column(String(3), default="INR")  # ISO 4217 code
    
    # Conversion source
    source = Column(String(50), nullable=True)  # meta_ads, google_ads, shopify, manual
    conversion_timestamp = Column(DateTime, nullable=True)  # When conversion happened
    
    # Offline conversion data (pre-match)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(2), nullable=True)  # ISO 3166-1 alpha-2
    
    # Matching results
    status = Column(String(20), default="pending")  # pending, matched, unmatched, failed, retrying
    match_algorithm = Column(String(50), nullable=True)  # email, phone, address, phone+name, etc
    match_confidence = Column(Float, default=0.0)  # 0.0-1.0 confidence score
    match_fields = Column(JSON, nullable=True)  # List of fields that matched
    
    # CAPI submission
    capi_status = Column(String(50), nullable=True)  # "sent", "received", "failed"
    capi_event_id = Column(String(100), nullable=True, unique=True)  # Event ID from CAPI
    capi_response = Column(JSON, nullable=True)  # Full CAPI response
    
    # Retry logic
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=5)
    next_retry_at = Column(DateTime, nullable=True)
    error_message = Column(String(500), nullable=True)
    
    # Metadata
    meta_data = Column(JSON, nullable=True)  # Custom data (order_id, etc)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    matched_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_offline_conversion_customer', 'customer_id'),
        Index('idx_offline_conversion_status', 'status'),
        Index('idx_offline_conversion_capi_status', 'capi_status'),
        Index('idx_offline_conversion_source', 'source'),
        Index('idx_offline_conversion_retry', 'next_retry_at'),
    )


class CartAbandonment(Base):
    """Track abandoned shopping carts"""
    __tablename__ = "crm_cart_abandonments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id = Column(String(36), ForeignKey('crm_customers.id'), nullable=True, index=True)
    
    # Cart details
    cart_token = Column(String(100), unique=True, nullable=True, index=True)  # Shopify cart token
    cart_value = Column(Float, nullable=True)  # Total cart value (INR)
    items_count = Column(Integer, default=0)  # Number of items
    currency = Column(String(3), default="INR")
    
    # Cart items
    cart_items = Column(JSON, nullable=True)  # [{sku, product_id, name, price, quantity}]
    
    # Abandonment details
    abandoned_at = Column(DateTime, nullable=True, index=True)
    abandoned_url = Column(String(500), nullable=True)  # URL when abandoned
    reason = Column(String(100), nullable=True)  # checkout, shipping, payment, etc
    
    # Recovery tracking
    recovery_status = Column(String(50), default="pending")  # pending, email_sent, recovered, expired, lost
    recovery_attempts = Column(Integer, default=0)
    
    # Recovery campaign linkage
    first_recovery_campaign_id = Column(String(36), nullable=True, index=True)
    last_recovery_campaign_id = Column(String(36), nullable=True, index=True)
    last_recovery_at = Column(DateTime, nullable=True)
    
    # Recovery outcome
    recovered_value = Column(Float, default=0.0)  # Value of items recovered/purchased
    recovered_at = Column(DateTime, nullable=True)
    time_to_recovery_hours = Column(Integer, nullable=True)  # Hours between abandon and recovery
    
    # Email tracking
    recovery_emails_sent = Column(Integer, default=0)
    recovery_emails_clicked = Column(Integer, default=0)
    recovery_email_click_rate = Column(Float, default=0.0)
    
    # Metadata
    source = Column(String(50), default="shopify")  # shopify, woocommerce, custom
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_cart_abandoned_customer', 'customer_id'),
        Index('idx_cart_abandoned_status', 'recovery_status'),
        Index('idx_cart_abandoned_time', 'abandoned_at'),
    )


class CartRecoveryTemplate(Base):
    """Email templates for cart recovery campaigns"""
    __tablename__ = "crm_cart_recovery_templates"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Template details
    name = Column(String(255), nullable=False)
    subject = Column(String(200), nullable=False)  # Email subject
    template_html = Column(String(10000), nullable=False)  # HTML email template
    template_text = Column(String(10000), nullable=True)  # Plain text fallback
    
    # Template logic
    trigger_hours_after_abandon = Column(Integer, default=1)  # When to send (1h, 24h, 72h)
    cta_text = Column(String(100), default="Complete Your Purchase")
    cta_url_param = Column(String(255), nullable=True)  # UTM or tracking param
    include_product_image = Column(Boolean, default=True)
    include_discount_code = Column(Boolean, default=False)
    discount_code = Column(String(50), nullable=True)
    discount_percentage = Column(Integer, nullable=True)  # e.g., 10 for 10%
    
    # Performance tracking
    is_active = Column(Boolean, default=True)
    send_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    recovery_count = Column(Integer, default=0)
    avg_recovery_value = Column(Float, default=0.0)
    
    # Metadata
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_template_active', 'is_active'),
        Index('idx_template_trigger', 'trigger_hours_after_abandon'),
    )


class CartRecoveryCampaign(Base):
    """Track cart recovery email campaigns"""
    __tablename__ = "crm_cart_recovery_campaigns"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Campaign details
    cart_abandonment_id = Column(String(36), ForeignKey('crm_cart_abandonments.id'), nullable=False, index=True)
    template_id = Column(String(36), ForeignKey('crm_cart_recovery_templates.id'), nullable=False)
    customer_email = Column(String(255), nullable=False)
    
    # Email tracking
    email_sent_at = Column(DateTime, nullable=True)
    email_delivered_at = Column(DateTime, nullable=True)
    email_opened_at = Column(DateTime, nullable=True)
    email_clicked_at = Column(DateTime, nullable=True)
    
    # Campaign status
    status = Column(String(50), default="pending")  # pending, sent, delivered, opened, clicked, converted, bounced, failed
    
    # Recovery outcome
    recovered = Column(Boolean, default=False)
    recovered_value = Column(Float, nullable=True)
    recovered_at = Column(DateTime, nullable=True)
    
    # N8N integration
    n8n_execution_id = Column(String(100), nullable=True)  # N8N workflow execution ID
    n8n_status = Column(String(50), nullable=True)  # success, failed, pending
    
    # Metadata
    utm_source = Column(String(100), default="cart_recovery")
    utm_campaign = Column(String(100), nullable=True)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_recovery_campaign_cart', 'cart_abandonment_id'),
        Index('idx_recovery_campaign_status', 'status'),
        Index('idx_recovery_campaign_email_sent', 'email_sent_at'),
        Index('idx_recovery_campaign_recovered', 'recovered'),
    )


class DelhiveryOrder(Base):
    """Track orders through Delhivery fulfillment"""
    __tablename__ = "crm_delhivery_orders"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id = Column(String(36), ForeignKey('crm_customers.id'), nullable=True, index=True)
    
    # Order details
    order_number = Column(String(100), unique=True, nullable=False, index=True)  # Shopify order #
    order_id = Column(String(100), nullable=True)  # Shopify order ID
    
    # Recipient details
    recipient_name = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=True)
    recipient_phone = Column(String(20), nullable=False)
    
    # Delivery address
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(2), default="IN")
    
    # Order items
    items_count = Column(Integer, default=0)
    items = Column(JSON, nullable=True)  # [{sku, qty, price, name}]
    
    # Order value
    subtotal = Column(Float, nullable=True)
    shipping_charge = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)
    
    # Delhivery integration
    delhivery_waybill = Column(String(50), nullable=True, index=True)  # Tracking number
    delhivery_status = Column(String(50), default="pending")  # pending, picked, in_transit, delivered, cancelled
    delhivery_sku = Column(String(50), nullable=True)  # For shipping
    delhivery_response = Column(JSON, nullable=True)  # Raw Delhivery API response
    
    # Tracking
    tracking_url = Column(String(500), nullable=True)
    last_track_at = Column(DateTime, nullable=True)
    estimated_delivery = Column(Date, nullable=True)
    actual_delivery = Column(DateTime, nullable=True)
    
    # Shipment events
    picked_at = Column(DateTime, nullable=True)
    in_transit_at = Column(DateTime, nullable=True)
    out_for_delivery_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    failed_reason = Column(String(500), nullable=True)
    
    # Callbacks & notifications
    webhook_notified_at = Column(DateTime, nullable=True)
    customer_notified_at = Column(DateTime, nullable=True)
    notification_status = Column(String(50), nullable=True)  # sent, failed, pending
    
    # Metadata
    is_cancellable = Column(Boolean, default=False)
    cancellation_reason = Column(String(500), nullable=True)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_delhivery_customer', 'customer_id'),
        Index('idx_delhivery_status', 'delhivery_status'),
        Index('idx_delhivery_waybill', 'delhivery_waybill'),
        Index('idx_delhivery_created', 'created_at'),
    )


class DelhiveryTracking(Base):
    """Track shipment status updates from Delhivery"""
    __tablename__ = "crm_delhivery_tracking"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    delhivery_order_id = Column(String(36), ForeignKey('crm_delhivery_orders.id'), nullable=False, index=True)
    
    # Event details
    event_type = Column(String(100), nullable=False)  # pickup, in_transit, delivery_attempt, delivered, cancelled
    event_timestamp = Column(DateTime, nullable=False)
    
    # Location
    location = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Status details
    status_message = Column(String(500), nullable=True)
    status_code = Column(String(50), nullable=True)
    
    # Handler info
    handler_name = Column(String(255), nullable=True)
    handler_contact = Column(String(20), nullable=True)
    
    # Metadata
    meta_data = Column(JSON, nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_tracking_order', 'delhivery_order_id'),
        Index('idx_tracking_event_type', 'event_type'),
        Index('idx_tracking_timestamp', 'event_timestamp'),
    )


class GoogleFormSubmission(Base):
    """Google Form submissions tracking"""
    __tablename__ = "crm_google_form_submissions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    form_id = Column(String(100), nullable=False, index=True)  # Google Form ID
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), nullable=True, index=True)
    
    # Raw submission
    submission_data = Column(JSON, nullable=False)  # Raw form response data
    extracted_fields = Column(JSON, nullable=True)  # Extracted {email, phone, first_name, last_name, company}
    submission_hash = Column(String(64), nullable=True, unique=True)  # Prevent duplicates if webhook fires twice
    
    # Processing
    status = Column(String(50), nullable=False, default="received")  # received, processing, duplicate, lead_created, error
    match_type = Column(String(50), nullable=True)  # exact_email, exact_phone, email_phone, no_match, etc
    error_message = Column(String(500), nullable=True)  # If processing failed
    
    # Metadata
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_form_customer', 'form_id', 'customer_id'),
        Index('idx_form_status', 'form_id', 'status'),
        Index('idx_form_created', 'form_id', 'created_at'),
    )


class GoogleFormTemplate(Base):
    """Saved Google Form field mappings"""
    __tablename__ = "crm_google_form_templates"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    form_id = Column(String(100), nullable=False, unique=True, index=True)  # Google Form ID
    form_name = Column(String(255), nullable=False)  # Form display name
    form_url = Column(String(500), nullable=True)  # Form URL for reference
    
    # Field mapping: {email: "Email Address", phone: "Phone Number", etc}
    field_mapping = Column(JSON, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_template_active', 'is_active'),
    )


class MetaAudience(Base):
    """Meta custom audiences for targeting"""
    __tablename__ = "crm_meta_audiences"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    meta_audience_id = Column(String(100), nullable=False, unique=True, index=True)  # Meta audience ID
    audience_name = Column(String(255), nullable=False)
    audience_description = Column(String(500), nullable=True)
    audience_type = Column(String(50), nullable=True)  # CUSTOM_LIST, LOOKALIKE, WEBSITE, ENGAGEMENT
    
    # Sync tracking
    customer_count = Column(Integer, default=0)  # Number of customers synced
    last_synced_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Metadata
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_audience_active', 'is_active'),
        Index('idx_audience_type', 'audience_type'),
    )


class MetaConversion(Base):
    """Meta offline conversions for attribution"""
    __tablename__ = "crm_meta_conversions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), index=True)
    
    # Conversion details
    event_name = Column(String(100), nullable=False)  # Purchase, Lead, Contact, etc
    value = Column(Float, nullable=True)  # Conversion value
    currency = Column(String(3), default="INR")
    status = Column(String(50), nullable=True)  # Conversion status
    
    # Meta sync
    synced_to_meta = Column(Boolean, default=False, index=True)
    meta_response = Column(JSON, nullable=True)  # API response details
    meta_event_id = Column(String(100), nullable=True)  # Meta event ID
    
    # Metadata
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_conversion_customer', 'customer_id'),
        Index('idx_conversion_event', 'event_name'),
        Index('idx_conversion_synced', 'synced_to_meta'),
        Index('idx_conversion_created', 'created_at'),
    )


# ============================================================================
# SPRINT 3 TASK 1: CSV IMPORT & BULK OPERATIONS
# ============================================================================

class ImportJob(Base):
    """Tracks CSV import jobs"""
    __tablename__ = "crm_import_jobs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # File info
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)  # Bytes
    row_count = Column(Integer, nullable=False)  # Total rows in CSV
    
    # Processing status
    status = Column(String(50), nullable=False)  # pending, validating, validated, processing, completed, failed, cancelled
    validation_errors = Column(JSON, nullable=True)  # List of validation errors
    
    # Results
    processed_count = Column(Integer, default=0)  # Rows processed
    success_count = Column(Integer, default=0)  # Successfully imported
    duplicate_count = Column(Integer, default=0)  # Duplicates found
    error_count = Column(Integer, default=0)  # Processing errors
    
    # Metadata
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_import_status', 'status'),
        Index('idx_import_created', 'created_at'),
    )


class ImportResult(Base):
    """Tracks individual CSV row import results"""
    __tablename__ = "crm_import_results"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Import reference
    job_id = Column(String(36), ForeignKey("crm_import_jobs.id"), nullable=False, index=True)
    row_index = Column(Integer, nullable=False)  # Row number in CSV
    
    # Result details
    status = Column(String(50), nullable=False)  # success, duplicate, validation_error, processing_error, skipped
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), nullable=True)
    error_message = Column(String(500), nullable=True)
    
    # Original data
    data = Column(JSON, nullable=True)  # Original row data
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_result_job', 'job_id'),
        Index('idx_result_status', 'status'),
    )


class BulkOperation(Base):
    """Tracks bulk operations (update, delete)"""
    __tablename__ = "crm_bulk_operations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Operation details
    operation_type = Column(String(50), nullable=False)  # create, update, delete, property_update
    customer_count = Column(Integer, nullable=False)  # Total customers affected
    operation_data = Column(JSON, nullable=False)  # Operation parameters (e.g., updates dict)
    
    # Status
    status = Column(String(50), default="pending", nullable=False)  # pending, processing, completed, failed
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    
    # Metadata
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_bulk_status', 'status'),
        Index('idx_bulk_created', 'created_at'),
    )


class BulkOperationResult(Base):
    """Tracks results for individual records in bulk operations"""
    __tablename__ = "crm_bulk_operation_results"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Operation reference
    operation_id = Column(String(36), ForeignKey("crm_bulk_operations.id"), index=True)
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), index=True)
    
    # Result
    status = Column(String(50), nullable=False)  # success, error
    error_message = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# SPRINT 3 TASK 2: SMS & EMAIL NOTIFICATIONS
# ============================================================================

class SMSMessage(Base):
    """Tracks SMS messages sent via Twilio"""
    __tablename__ = "crm_sms_messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Reference
    campaign_id = Column(String(36), ForeignKey("crm_sms_campaigns.id"), nullable=True, index=True)
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), nullable=False, index=True)
    
    # Message details
    phone_number = Column(String(20), nullable=False)
    message_text = Column(Text, nullable=False)
    
    # Delivery tracking
    status = Column(String(50), nullable=False)  # pending, sent, delivered, failed, bounced
    twilio_sid = Column(String(100), nullable=True)  # Twilio message ID
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_sms_customer', 'customer_id'),
        Index('idx_sms_campaign', 'campaign_id'),
        Index('idx_sms_status', 'status'),
    )


class SMSCampaign(Base):
    """Tracks SMS campaigns"""
    __tablename__ = "crm_sms_campaigns"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Campaign details
    campaign_name = Column(String(255), nullable=False)
    message_text = Column(Text, nullable=False)
    
    # Targeting
    audience_filter = Column(JSON, nullable=False)  # Filter params for audience selection
    
    # Status & metrics
    status = Column(String(50), nullable=False)  # draft, scheduled, sending, completed, failed, cancelled
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    
    # Metadata
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_sms_campaign_status', 'status'),
        Index('idx_sms_campaign_created', 'created_at'),
    )


class EmailTemplate(Base):
    """Email templates for campaigns"""
    __tablename__ = "crm_email_templates"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Template details
    template_name = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)  # Email subject (supports variables)
    html_content = Column(Text, nullable=False)  # HTML content (supports variables like {{first_name}})
    
    # Template metadata
    variables = Column(JSON, nullable=True)  # List of available variables
    is_active = Column(Boolean, default=True, index=True)
    
    # Creation
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_template_active', 'is_active'),
    )


class EmailMessage(Base):
    """Tracks email messages sent via Plunk"""
    __tablename__ = "crm_email_messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Reference
    campaign_id = Column(String(36), ForeignKey("crm_email_campaigns.id"), nullable=True, index=True)
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), nullable=False, index=True)
    
    # Message details
    email_address = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    
    # Delivery tracking
    status = Column(String(50), nullable=False)  # pending, sent, delivered, failed, bounced, unsubscribed
    plunk_message_id = Column(String(100), nullable=True)  # Plunk message ID
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_email_customer', 'customer_id'),
        Index('idx_email_campaign', 'campaign_id'),
        Index('idx_email_status', 'status'),
    )


class EmailCampaign(Base):
    """Tracks email campaigns"""
    __tablename__ = "crm_email_campaigns"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Campaign details
    campaign_name = Column(String(255), nullable=False)
    template_id = Column(String(36), ForeignKey("crm_email_templates.id"), nullable=False)
    
    # Targeting
    audience_filter = Column(JSON, nullable=False)  # Filter params for audience selection
    
    # Status & metrics
    status = Column(String(50), nullable=False)  # draft, scheduled, sending, completed, failed, cancelled
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    
    # Metadata
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_email_campaign_status', 'status'),
        Index('idx_email_campaign_created', 'created_at'),
    )


# ============================================================================
# SPRINT 3 TASK 3: CUSTOMER ENRICHMENT
# ============================================================================

class CustomerEnrichment(Base):
    """Tracks customer data enrichment jobs"""
    __tablename__ = "crm_customer_enrichment"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Reference
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), index=True)
    
    # Enrichment details
    enrichment_type = Column(String(50), nullable=False)  # linkedin, company, signals
    status = Column(String(50), nullable=False)  # pending, enriching, completed, partial, failed
    enriched_fields = Column(JSON, nullable=True)  # List of fields enriched
    meta_data = Column(JSON, nullable=True)  # Enrichment result data
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_enrichment_customer', 'customer_id'),
        Index('idx_enrichment_type', 'enrichment_type'),
        Index('idx_enrichment_status', 'status'),
    )


class CompanyData(Base):
    """Enriched company data for customers"""
    __tablename__ = "crm_company_data"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Reference
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), index=True, unique=True)
    
    # Company details
    company_name = Column(String(255), nullable=False)
    industry = Column(String(100), nullable=True)
    employees = Column(Integer, nullable=True)
    revenue = Column(String(50), nullable=True)  # e.g., "1M-10M"
    founded_year = Column(Integer, nullable=True)
    website = Column(String(255), nullable=True)
    location = Column(String(100), nullable=True)
    
    # Metadata
    data_source = Column(String(50), nullable=False)  # linkedin, clearbit, hunter, internal
    enriched_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_company_customer', 'customer_id'),
        Index('idx_company_industry', 'industry'),
    )


class IntentSignal(Base):
    """Detected buyer intent signals for customers"""
    __tablename__ = "crm_intent_signals"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Reference
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), index=True)
    
    # Signal details
    signal_type = Column(String(50), nullable=False)  # website_visit, pricing_page, demo_request, etc
    score = Column(Float, nullable=False)  # 0.0 to 1.0 confidence
    source = Column(String(100), nullable=False)  # cart_activity, propensity_model, company_data, etc
    meta_data = Column(JSON, nullable=True)  # Additional signal context
    
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_signal_customer', 'customer_id'),
        Index('idx_signal_type', 'signal_type'),
        Index('idx_signal_score', 'score'),
    )


# ─── WAVE 0.1: AI CRM CORE TABLES ────────────────────────────────────────────

class CustomerAIProfile(Base):
    """Customer AI scoring and status (Wave 0.1 + Wave 0.2)"""
    __tablename__ = "customer_ai_profile"
    
    profile_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), nullable=False, unique=True, index=True)
    overall_score = Column(Integer, default=0)  # 0-100
    engagement_score = Column(Integer, default=0)  # 0-100
    purchase_intent_score = Column(Integer, default=0)  # 0-100
    customer_value_score = Column(Integer, default=0)  # 0-100
    response_quality_score = Column(Float, default=3.5)  # 1-5 stars (Wave 0.2)
    churn_risk_score = Column(Integer, default=0)  # 0-100 (Wave 0.2)
    lead_status = Column(String(20), default='Cold')  # Cold, Warm, Hot, Ready
    last_activity = Column(DateTime, nullable=True)
    next_action = Column(String(100), nullable=True)  # "Call Now", "Send Offer", "Follow Up"
    last_score_update = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_customer_ai_profile_score', 'overall_score'),
        Index('idx_customer_ai_profile_status', 'lead_status'),
    )


class CustomerEvent(Base):
    """Customer interaction events for AI (Wave 0.1)"""
    __tablename__ = "customer_events"
    
    event_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), nullable=False, index=True)
    conversation_id = Column(String(36), nullable=True, index=True)
    event_type = Column(String(50), nullable=False)  # PRICE_INQUIRY, COD_INQUIRY, ORDER_CREATED, etc.
    context_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_customer_events_customer_created', 'customer_id', 'created_at'),
    )


class AIConversation(Base):
    """AI chat sessions (Wave 0.1)"""
    __tablename__ = "ai_conversations"
    
    conversation_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), nullable=False, index=True)
    message_count = Column(Integer, default=1)
    intents_in_path = Column(JSON, nullable=True)  # Array of detected intents
    outcome = Column(String(50), nullable=True)  # converted, lost, pending, escalated
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_ai_conversations_customer', 'customer_id'),
    )


class ProductCatalog(Base):
    """Product catalog for AI (Wave 0.1)"""
    __tablename__ = "product_catalog"
    
    product_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False, unique=True, index=True)
    price_inr = Column(Float, nullable=False)  # Current price in INR
    stock = Column(Integer, default=0)  # Current stock level
    category = Column(String(100), nullable=True)  # Pepper, Cardamom, Clove, etc.
    status = Column(String(20), default='active')  # active, inactive, discontinued
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_product_catalog_category', 'category'),
    )


class KnowledgeBase(Base):
    """FAQ and help articles for AI (Wave 0.1)"""
    __tablename__ = "knowledge_base"
    
    kb_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(50), nullable=True)  # FAQ, Shipping, Payment, Policy, etc.
    status = Column(String(20), default='active')  # active, inactive, archived
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_knowledge_base_category', 'category'),
        Index('idx_knowledge_base_status', 'status'),
    )


class AILog(Base):
    """AI audit trail (Wave 0.1)"""
    __tablename__ = "ai_logs"
    
    log_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), nullable=True, index=True)
    conversation_id = Column(String(36), nullable=True)
    intent_detected = Column(String(50), nullable=True)
    language_detected = Column(String(20), nullable=True)  # english, malayalam, manglish, mixed
    response_text = Column(Text, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_ai_logs_customer', 'customer_id', 'created_at'),
    )


# ─── WAVE 0.2: REVIEW & LEARNING TABLES ──────────────────────────────────────

class AIReviewQueue(Base):
    """Low-confidence questions flagged for human review (Wave 0.2)"""
    __tablename__ = "ai_review_queue"
    
    queue_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id = Column(String(36), ForeignKey("ai_conversations.id"), nullable=True, index=True)
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), nullable=True, index=True)
    customer_message = Column(Text, nullable=False)
    detected_intent = Column(String(50), nullable=True)
    intent_confidence = Column(Float, nullable=True)  # 0-1
    detected_language = Column(String(20), nullable=True)
    ai_response = Column(Text, nullable=True)
    review_status = Column(String(20), default='pending')  # pending, approved, reclassified, escalated
    human_intent_correction = Column(String(50), nullable=True)  # If reclassified by human
    human_notes = Column(Text, nullable=True)
    should_add_to_kb = Column(Boolean, default=False)
    kb_category = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    
    __table_args__ = (
        Index('idx_review_queue_status_created', 'review_status', 'created_at'),
    )


class ManualTrainingExample(Base):
    """Your approved message/intent pairs for learning (Wave 0.2)"""
    __tablename__ = "manual_training_examples"
    
    example_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    review_queue_id = Column(String(36), ForeignKey("ai_review_queue.id"), nullable=True)
    message_text = Column(Text, nullable=False)
    detected_language = Column(String(20), nullable=True)
    correct_intent = Column(String(50), nullable=False)
    intent_confidence = Column(Float, nullable=True)
    keywords_identified = Column(JSON, nullable=True)  # Keywords that led to intent
    approved_by = Column(String(100), nullable=False)
    learning_phase = Column(Integer, default=1)  # Track which learning batch
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_training_examples_intent', 'correct_intent'),
    )


class KBPerformance(Base):
    """Track which KB entries are actually helpful (Wave 0.2)"""
    __tablename__ = "kb_performance"
    
    perf_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    kb_id = Column(String(36), ForeignKey("knowledge_base.id"), nullable=False, unique=True, index=True)
    times_suggested = Column(Integer, default=0)  # How many times suggested in responses
    times_clicked_helpful = Column(Integer, default=0)  # Customer said "helpful"
    times_marked_unhelpful = Column(Integer, default=0)  # Customer said "not helpful"
    average_rating = Column(Float, default=0.0)  # 1-5 stars
    last_updated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class ResponseQualityFeedback(Base):
    """User feedback on AI responses (Wave 0.2)"""
    __tablename__ = "response_quality_feedback"
    
    feedback_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    ai_log_id = Column(String(36), ForeignKey("ai_logs.id"), nullable=True)
    customer_id = Column(String(36), ForeignKey("crm_customers.id"), nullable=True)
    response_text = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5 stars
    feedback_text = Column(Text, nullable=True)  # Why did you rate it?
    is_helpful = Column(Boolean, nullable=True)  # Thumbs up/down
    suggested_improvement = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_response_quality_rating', 'rating', 'created_at'),
    )


class FeatureToggle(Base):
    """Feature flags for enabling/disabling Wave features (Wave 0.2)"""
    __tablename__ = "feature_toggles"
    
    toggle_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    feature_key = Column(String(50), nullable=False, unique=True, index=True)
    feature_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, index=True)
    category = Column(String(50), nullable=True)  # Wave 0.2, Wave 1, Wave 2, etc
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
