"""Customer Intelligence Service

Unifies CRM, journey, email, WhatsApp, and AI-decision data into a single
customer intelligence view and score.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from app.ai.openrouter_client import ai_client
from app.storage import get_connection

# Label patterns for score override rules
_PURCHASE_LABEL_RE = re.compile(
    r'\b(purchase[ds]?|purchse|purchsae|puchase|prepaid_customer|'
    r'cinnamon_purchase|blackpepper_purchase|tamarind_purchase|website_purchase|'
    r'bought|ordered)\b',
    re.IGNORECASE,
)
_INTERESTED_LABEL_RE = re.compile(
    r'\b(interested|price_checked|price\s*checked)\b',
    re.IGNORECASE,
)
_MALAYALAM_RE = re.compile(r'[\u0D00-\u0D7F]')


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _safe_pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 1)


def _label_for_score(score: int) -> str:
    if score <= 30:
        return 'cold'
    if score <= 70:
        return 'warm'
    return 'hot'


def compute_customer_score(email: str) -> dict[str, Any]:
    with get_connection() as conn:
        customer = conn.execute(
            'SELECT id, total_orders, total_spent, pause_campaigns, tags, purchase_status '
            'FROM customers WHERE email = ? AND deleted_at IS NULL',
            (email,),
        ).fetchone()
        if not customer:
            return {}

        row = conn.execute(
            """
            SELECT
                SUM(CASE WHEN event_type IN ('EMAIL_SENT') THEN 1 ELSE 0 END) AS email_sent,
                SUM(CASE WHEN event_type IN ('EMAIL_OPENED') THEN 1 ELSE 0 END) AS email_opened,
                SUM(CASE WHEN event_type IN ('EMAIL_CLICKED') THEN 1 ELSE 0 END) AS email_clicked,
                SUM(CASE WHEN event_type IN ('WA_SENT') THEN 1 ELSE 0 END) AS wa_sent,
                SUM(CASE WHEN event_type IN ('WA_REPLIED') THEN 1 ELSE 0 END) AS wa_replied,
                SUM(CASE WHEN event_type IN ('PRODUCT_VIEWED', 'WEBSITE_VISIT') THEN 1 ELSE 0 END) AS website_visits,
                SUM(CASE WHEN event_type IN ('ADD_TO_CART') THEN 1 ELSE 0 END) AS add_to_cart,
                SUM(CASE WHEN event_type IN ('EMAIL_UNSUBSCRIBED', 'UNSUBSCRIBED') THEN 1 ELSE 0 END) AS unsubscribed,
                MAX(created_at) AS last_engagement_at
            FROM communication_events
            WHERE customer_email = ?
            """,
            (email,),
        ).fetchone()

    total_orders = int(customer['total_orders'] or 0)
    crm_purchase_status = str(customer['purchase_status'] or '').lower()

    # Parse tags for label-based scoring
    try:
        tags_list = json.loads(customer['tags'] or '[]') if isinstance(customer['tags'], str) else (customer['tags'] or [])
    except Exception:
        tags_list = []
    tag_str = ' '.join(str(t) for t in tags_list).lower()

    # Hard-cap: useless label → score 10, but only for non-buyers
    is_confirmed_buyer_early = total_orders > 0 or crm_purchase_status == 'purchased'
    if 'useless' in tag_str.split() and not is_confirmed_buyer_early:
        return {
            'lead_score': 10,
            'engagement_label': 'cold',
            'purchase_status': crm_purchase_status or 'not_purchased',
            'email_sent': 0, 'email_opened': 0, 'email_clicked': 0,
            'wa_sent': 0, 'wa_replied': 0, 'website_visits': 0,
            'add_to_cart': 0, 'unsubscribed': 0,
            'open_rate': 0.0, 'click_rate': 0.0,
            'last_engagement_at': None,
        }

    email_sent = int(row['email_sent'] or 0)
    email_opened = int(row['email_opened'] or 0)
    email_clicked = int(row['email_clicked'] or 0)
    wa_sent = int(row['wa_sent'] or 0)
    wa_replied = int(row['wa_replied'] or 0)
    website_visits = int(row['website_visits'] or 0)
    add_to_cart = int(row['add_to_cart'] or 0)
    unsubscribed = int(row['unsubscribed'] or 0)

    # Label-based base score (overrides pure behavioral for cold leads with intent signals)
    has_purchase_label = bool(_PURCHASE_LABEL_RE.search(tag_str))
    has_interested_label = bool(_INTERESTED_LABEL_RE.search(tag_str))
    is_confirmed_buyer = total_orders > 0 or crm_purchase_status == 'purchased'

    if has_purchase_label and is_confirmed_buyer:
        base_score = 95 if total_orders >= 2 else 90
    elif has_purchase_label:
        base_score = 80
    elif wa_replied > 0 and not has_interested_label:
        base_score = 75
    elif has_interested_label:
        base_score = 50
    else:
        base_score = 0

    # Behavioral score (additive signals)
    behavior_score = 0
    behavior_score += email_opened * 5
    behavior_score += email_clicked * 10
    behavior_score += wa_replied * 12
    behavior_score += website_visits * 15
    behavior_score += add_to_cart * 25
    if total_orders > 0:
        behavior_score += 50
    if unsubscribed > 0:
        behavior_score -= 50
    if email_sent >= 3 and email_opened == 0:
        behavior_score -= 20

    # Base score is the floor; behavioral can raise it further
    score = max(base_score, behavior_score) if base_score > 0 else behavior_score
    score = max(0, min(100, score))

    label = _label_for_score(score)
    purchase_status = 'purchased' if is_confirmed_buyer else 'not_purchased'

    return {
        'lead_score': score,
        'engagement_label': label,
        'purchase_status': purchase_status,
        'email_sent': email_sent,
        'email_opened': email_opened,
        'email_clicked': email_clicked,
        'wa_sent': wa_sent,
        'wa_replied': wa_replied,
        'website_visits': website_visits,
        'add_to_cart': add_to_cart,
        'unsubscribed': unsubscribed,
        'open_rate': _safe_pct(email_opened, email_sent),
        'click_rate': _safe_pct(email_clicked, email_sent),
        'last_engagement_at': row['last_engagement_at'],
    }


def recommend_next_action(email: str, score_bundle: dict[str, Any]) -> tuple[str, str]:
    if not score_bundle:
        return 'insufficient_data', 'No customer activity found yet'

    if score_bundle['purchase_status'] == 'purchased':
        return 'start_post_purchase_journey', 'Customer purchased; trigger cross-sell and review flow'

    if score_bundle['open_rate'] <= 5 and score_bundle['wa_replied'] > 0:
        return 'switch_to_whatsapp_primary', 'Email engagement low, WhatsApp engagement stronger'

    if score_bundle['click_rate'] >= 20:
        return 'send_offer_in_48h', 'High click intent detected; send targeted offer soon'

    if score_bundle['lead_score'] <= 30:
        return 'nurture_with_education', 'Low score segment needs nurture content before hard offer'

    return 'continue_current_journey', 'Maintain current cadence with personalization updates'


def refresh_customer_intelligence(email: str) -> dict[str, Any]:
    score_bundle = compute_customer_score(email)
    if not score_bundle:
        return {}

    next_action, reason = recommend_next_action(email, score_bundle)
    now = _now()

    with get_connection() as conn:
        conn.execute(
            '''
            UPDATE customers
            SET lead_score = ?,
                engagement_label = ?,
                purchase_status = ?,
                next_ai_action = ?,
                ai_last_reason = ?,
                last_engagement_at = ?,
                updated_at = ?
            WHERE email = ? AND deleted_at IS NULL
            ''',
            (
                score_bundle['lead_score'],
                score_bundle['engagement_label'],
                score_bundle['purchase_status'],
                next_action,
                reason,
                score_bundle.get('last_engagement_at'),
                now,
                email,
            ),
        )

        customer = conn.execute(
            'SELECT * FROM customers WHERE email = ? AND deleted_at IS NULL',
            (email,),
        ).fetchone()

        if customer:
            conn.execute(
                '''
                INSERT INTO customer_score_history
                    (id, customer_uid, customer_id, customer_email, lead_score,
                     engagement_label, purchase_status, reason, metrics_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    _new_id(), customer['customer_uid'], customer['id'], customer['email'],
                    score_bundle['lead_score'], score_bundle['engagement_label'],
                    score_bundle['purchase_status'], reason,
                    json.dumps(score_bundle, ensure_ascii=True, sort_keys=True), now,
                ),
            )

    result = dict(customer)
    result['metrics'] = score_bundle
    return result


def get_customer_intelligence(email: str) -> dict[str, Any] | None:
    base = refresh_customer_intelligence(email)
    if not base:
        return None

    with get_connection() as conn:
        journeys = conn.execute(
            '''
            SELECT
                je.id,
                je.journey_id,
                j.name AS journey_name,
                je.current_step,
                je.status,
                je.started_at,
                je.triggered_at
            FROM journey_executions je
            JOIN journeys j ON j.id = je.journey_id
            WHERE je.customer_email = ?
            ORDER BY je.created_at DESC
            ''',
            (email,),
        ).fetchall()

        send_counts = conn.execute(
            '''
            SELECT
                SUM(CASE WHEN ss.status IN ('sent','opened','clicked','failed') THEN 1 ELSE 0 END) AS sent_count,
                SUM(CASE WHEN ss.status IN ('queued') THEN 1 ELSE 0 END) AS planned_count
            FROM journey_step_sends ss
            JOIN journey_executions je ON je.id = ss.execution_id
            WHERE je.customer_email = ?
            ''',
            (email,),
        ).fetchone()

        comm_counts = conn.execute(
            '''
            SELECT
                SUM(CASE WHEN event_type = 'EMAIL_SENT' THEN 1 ELSE 0 END) AS email_sent,
                SUM(CASE WHEN event_type = 'WA_SENT' THEN 1 ELSE 0 END) AS wa_sent
            FROM communication_events
            WHERE customer_email = ?
            ''',
            (email,),
        ).fetchone()

        ai_decisions = conn.execute(
            '''
            SELECT id, decision_type, source, ai_output_json, created_at
            FROM ai_decisions
            WHERE customer_id = ? OR customer_id = ?
            ORDER BY created_at DESC
            LIMIT 20
            ''',
            (base['id'], email),
        ).fetchall()

        identities = conn.execute(
            '''
            SELECT identity_type, identity_value, source, first_seen_at, last_seen_at
            FROM customer_identities
            WHERE customer_uid = ?
            ORDER BY identity_type, last_seen_at DESC
            ''',
            (base['customer_uid'],),
        ).fetchall()

        score_history = conn.execute(
            '''
            SELECT lead_score, engagement_label, purchase_status, reason, created_at
            FROM customer_score_history
            WHERE customer_uid = ?
            ORDER BY created_at DESC
            LIMIT 20
            ''',
            (base['customer_uid'],),
        ).fetchall()

    active = [dict(r) for r in journeys if (r['status'] or '').lower() == 'active']
    all_journeys = [dict(r) for r in journeys]

    return {
        'customer': base,
        'journeys': {
            'active': active,
            'all': all_journeys,
        },
        'communication': {
            'emails_sent': int(comm_counts['email_sent'] or 0),
            'whatsapp_sent': int(comm_counts['wa_sent'] or 0),
            'planned_messages': int(send_counts['planned_count'] or 0),
            'journey_messages_sent': int(send_counts['sent_count'] or 0),
        },
        'ai': {
            'next_action': base.get('next_ai_action'),
            'reason': base.get('ai_last_reason'),
            'decisions': [
                {
                    'id': row['id'],
                    'decision_type': row['decision_type'],
                    'source': row['source'],
                    'created_at': row['created_at'],
                    'output': json.loads(row['ai_output_json'] or '{}'),
                }
                for row in ai_decisions
            ],
        },
        'identity_map': [dict(r) for r in identities],
        'score_history': [dict(r) for r in score_history],
    }


def tag_customer_language(email: str) -> None:
    """Detect language from WhatsApp replies and add MAL_Customer / Eng_customer tag."""
    with get_connection() as conn:
        customer = conn.execute(
            'SELECT id, tags, whatsapp_number, phone FROM customers WHERE email = ? AND deleted_at IS NULL',
            (email,),
        ).fetchone()
        if not customer:
            return

        wa_number = customer['whatsapp_number'] or customer['phone'] or ''

        texts = conn.execute(
            '''
            SELECT cm.customer_text
            FROM journey_customers jc
            JOIN conversation_sessions cs ON cs.customer_id = jc.id
            JOIN conversation_messages cm ON cm.session_id = cs.id
            WHERE (jc.email = ? OR jc.phone = ?)
              AND cm.actor = 'customer'
              AND cm.customer_text IS NOT NULL
              AND cm.customer_text != ''
            LIMIT 100
            ''',
            (email, wa_number),
        ).fetchall()

        if not texts:
            return

        has_malayalam = any(_MALAYALAM_RE.search(r['customer_text'] or '') for r in texts)
        has_non_malayalam = any(not _MALAYALAM_RE.search(r['customer_text'] or '') for r in texts)

        try:
            tags = json.loads(customer['tags'] or '[]') if isinstance(customer['tags'], str) else list(customer['tags'] or [])
        except Exception:
            tags = []

        tags_lower = {str(t).lower() for t in tags}
        new_tags = list(tags)

        if has_malayalam and 'mal_customer' not in tags_lower:
            new_tags.append('MAL_Customer')
        if has_non_malayalam and 'eng_customer' not in tags_lower:
            new_tags.append('Eng_customer')

        if len(new_tags) != len(tags):
            conn.execute(
                'UPDATE customers SET tags = ?, updated_at = ? WHERE id = ?',
                (json.dumps(new_tags, ensure_ascii=False), _now(), customer['id']),
            )


def recompute_all_customer_scores(limit: int = 5000) -> dict[str, int]:
    with get_connection() as conn:
        rows = conn.execute(
            '''
            SELECT email FROM customers
            WHERE deleted_at IS NULL
            ORDER BY COALESCE(lead_score, 0) ASC, created_at ASC
            LIMIT ?
            ''',
            (limit,),
        ).fetchall()

    updated = 0
    for row in rows:
        if refresh_customer_intelligence(row['email']):
            updated += 1
        tag_customer_language(row['email'])
    return {'checked': len(rows), 'updated': updated}


def decide_journey_delivery(conn, customer_email: str, step: dict[str, Any], scheduled_at: datetime) -> dict[str, Any]:
    """Rule/AI decision for journey channel and adaptive timing, using current transaction."""
    customer = conn.execute(
        '''
        SELECT id, customer_uid, email, phone, preferred_channel, email_opted_in,
               whatsapp_opted_in, pause_campaigns, lead_score, engagement_label,
               purchase_status
        FROM customers
        WHERE email = ? AND deleted_at IS NULL
        ''',
        (customer_email,),
    ).fetchone()

    requested_channel = (step.get('channel') or 'email').lower()
    conditions = json.loads(step.get('conditions_json') or '{}') if isinstance(step.get('conditions_json'), str) else step.get('conditions_json') or {}
    ai_enabled = requested_channel in ('auto', 'ai') or bool(conditions.get('ai_decide'))

    if not customer:
        return {
            'channels': ['email'] if requested_channel not in ('both', 'whatsapp') else [requested_channel],
            'scheduled_at': scheduled_at,
            'source': 'fallback',
            'reason': 'Customer record unavailable; using configured channel',
        }

    if customer['pause_campaigns']:
        decision = {
            'channels': [],
            'scheduled_at': scheduled_at,
            'source': 'rule',
            'reason': 'Customer campaigns are paused',
            'customer_uid': customer['customer_uid'],
        }
        _log_journey_decision(conn, customer, step, decision)
        return decision

    if requested_channel == 'both':
        channels = ['email', 'whatsapp']
    elif requested_channel in ('auto', 'ai'):
        channels = ['email']
    else:
        channels = [requested_channel]

    reason = 'Configured journey channel and delay used'
    if ai_enabled:
        preferred = (customer['preferred_channel'] or 'auto').lower()
        score = int(customer['lead_score'] or 0)
        label = (customer['engagement_label'] or 'cold').lower()

        if preferred == 'email':
            channels = ['email']
            reason = 'Customer preference is email'
        elif preferred == 'whatsapp':
            channels = ['whatsapp']
            reason = 'Customer preference is WhatsApp'
        elif label == 'cold' and customer['whatsapp_opted_in']:
            channels = ['whatsapp']
            scheduled_at = scheduled_at.replace() + _adaptive_delay_hours(72)
            reason = 'Cold lead: use WhatsApp with slower nurture cadence'
        elif score >= 71 and customer['email_opted_in']:
            channels = ['email']
            reason = 'Hot lead: continue email quickly with stronger offer'
        elif customer['whatsapp_opted_in'] and not customer['email_opted_in']:
            channels = ['whatsapp']
            reason = 'Email unavailable; WhatsApp opted in'
        else:
            channels = ['email'] if customer['email_opted_in'] else ['whatsapp']
            reason = 'Auto channel selected from opt-in and score signals'

    # Remove channels the customer cannot receive.
    filtered = []
    for channel in channels:
        if channel == 'email' and customer['email_opted_in']:
            filtered.append(channel)
        elif channel == 'whatsapp' and customer['whatsapp_opted_in'] and customer['phone']:
            filtered.append(channel)
    channels = filtered

    decision = {
        'channels': channels,
        'scheduled_at': scheduled_at,
        'source': 'rule_ai',
        'reason': reason,
        'customer_uid': customer['customer_uid'],
        'lead_score': int(customer['lead_score'] or 0),
        'engagement_label': customer['engagement_label'],
        'purchase_status': customer['purchase_status'],
    }
    _log_journey_decision(conn, customer, step, decision)
    return decision


def _adaptive_delay_hours(hours: int):
    from datetime import timedelta
    return timedelta(hours=hours)


def _log_journey_decision(conn, customer, step: dict[str, Any], decision: dict[str, Any]) -> None:
    output = {
        'step_id': step.get('id'),
        'step_name': step.get('name'),
        'channels': decision.get('channels', []),
        'scheduled_at': decision.get('scheduled_at').isoformat() if hasattr(decision.get('scheduled_at'), 'isoformat') else decision.get('scheduled_at'),
        'reason': decision.get('reason'),
        'lead_score': decision.get('lead_score'),
        'engagement_label': decision.get('engagement_label'),
        'purchase_status': decision.get('purchase_status'),
    }
    conn.execute(
        '''
        INSERT INTO ai_decisions
            (id, decision_type, customer_id, ai_output_json, source, created_at)
        VALUES (?, 'journey_delivery', ?, ?, ?, ?)
        ''',
        (
            f"ai-jour-{uuid.uuid4().hex[:8]}",
            customer['id'],
            json.dumps(output, ensure_ascii=True, sort_keys=True),
            decision.get('source', 'rule_ai'),
            _now(),
        ),
    )


def list_ai_decisions(limit: int = 100, customer_email: str | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if customer_email:
            customer = conn.execute(
                'SELECT id FROM customers WHERE email = ? AND deleted_at IS NULL',
                (customer_email,),
            ).fetchone()
            if customer:
                rows = conn.execute(
                    '''
                    SELECT id, decision_type, customer_id, source, ai_output_json, created_at, used
                    FROM ai_decisions
                    WHERE customer_id = ? OR customer_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    ''',
                    (customer['id'], customer_email, limit),
                ).fetchall()
            else:
                rows = []
        else:
            rows = conn.execute(
                '''
                SELECT id, decision_type, customer_id, source, ai_output_json, created_at, used
                FROM ai_decisions
                ORDER BY created_at DESC
                LIMIT ?
                ''',
                (limit,),
            ).fetchall()

    result: list[dict[str, Any]] = []
    for row in rows:
        d = dict(row)
        try:
            d['ai_output'] = json.loads(d.pop('ai_output_json') or '{}')
        except Exception:
            d['ai_output'] = {}
        result.append(d)
    return result


def draft_ai_email_reply(customer_email: str, inbound_message: str) -> dict[str, Any]:
    with get_connection() as conn:
        customer = conn.execute(
            'SELECT customer_uid, name, engagement_label, purchase_status, preferred_channel FROM customers WHERE email = ? AND deleted_at IS NULL',
            (customer_email,),
        ).fetchone()

    if not customer:
        return {'error': 'Customer not found'}

    prompt = f"""You are an email support + sales assistant for PureLeven organic brand.

Customer context:
- Customer UID: {customer['customer_uid']}
- Name: {customer['name'] or 'Customer'}
- Engagement label: {customer['engagement_label']}
- Purchase status: {customer['purchase_status']}
- Preferred channel: {customer['preferred_channel']}

Customer inbound email:
{inbound_message}

Generate concise JSON only:
{{
  "subject": "reply subject",
  "body": "plain-text body",
  "intent": "support|pricing|product|order|other",
  "confidence": 0.0,
  "suggested_next_action": "one short action"
}}"""

    raw = ai_client._call(prompt=prompt, max_tokens=240, temperature=0.3)
    if raw:
        try:
            parsed = json.loads(raw)
            return {
                'customer_email': customer_email,
                'customer_uid': customer['customer_uid'],
                'draft': parsed,
                'source': 'ai',
            }
        except Exception:
            pass

    # Safe fallback if AI unavailable or malformed.
    return {
        'customer_email': customer_email,
        'customer_uid': customer['customer_uid'],
        'draft': {
            'subject': 'Thanks for contacting PureLeven',
            'body': (
                "Thanks for writing to us. We have received your message and our team is reviewing it. "
                "We will follow up shortly with the exact details and the best recommendation for you."
            ),
            'intent': 'other',
            'confidence': 0.35,
            'suggested_next_action': 'human_review_before_send',
        },
        'source': 'fallback',
    }
