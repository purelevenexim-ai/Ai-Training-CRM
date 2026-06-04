"""
Journey Engine V2 — Generic Multi-Channel Journey Executor

Replaces the hardcoded review_journey_engine.py with a configurable system
where each journey is a sequence of steps, each step can send Email, WhatsApp,
or both.

Public API:
    create_journey(name, trigger_event, steps) → journey dict
    enroll_customer(journey_id, customer_email, trigger_context) → execution dict
    run_due_steps() → list of SendResult   ← called by APScheduler
    get_journey(journey_id) → dict
    list_journeys() → list
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app.storage import get_connection
from app.services.audience_service import render_template, get_template
from app.services.email_service import send_email

logger = logging.getLogger(__name__)


# ── Result ─────────────────────────────────────────────────────────────────────

@dataclass
class SendResult:
    execution_id: str
    step_id: str
    channel: str
    customer_email: str
    status: str          # sent | skipped | failed | dry_run
    message_id: str = ''
    error: str = ''


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except ValueError:
        return None


# ── Journey CRUD ───────────────────────────────────────────────────────────────

def create_journey(
    name: str,
    *,
    description: str | None = None,
    trigger_event: str = 'order_delivered',
    trigger_delay_hours: int = 0,
    target_list_id: str | None = None,
    steps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a new journey with optional steps."""
    jid = _new_id()
    now = _now()
    with get_connection() as conn:
        conn.execute(
            '''
            INSERT INTO journeys
                (id, name, description, trigger_event, trigger_delay_hours,
                 target_list_id, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'draft', ?, ?)
            ''',
            (jid, name, description, trigger_event, trigger_delay_hours,
             target_list_id, now, now),
        )
        if steps:
            for i, step in enumerate(steps, start=1):
                _insert_step(conn, jid, i, step)
        row = conn.execute('SELECT * FROM journeys WHERE id = ?', (jid,)).fetchone()
    return dict(row)


def _insert_step(conn, journey_id: str, step_number: int, step: dict[str, Any]) -> None:
    sid = _new_id()
    now = _now()
    conn.execute(
        '''
        INSERT INTO journey_steps
            (id, journey_id, step_number, name, delay_days, delay_hours,
             channel, template_id, conditions_json, max_retries, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            sid, journey_id, step_number,
            step.get('name', f'Step {step_number}'),
            int(step.get('delay_days', 0)),
            int(step.get('delay_hours', 0)),
            step.get('channel', 'email'),
            step.get('template_id'),
            json.dumps(step.get('conditions', {})),
            int(step.get('max_retries', 1)),
            now,
        ),
    )


def get_journey(jid: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute('SELECT * FROM journeys WHERE id = ?', (jid,)).fetchone()
        if not row:
            return None
        steps = conn.execute(
            'SELECT * FROM journey_steps WHERE journey_id = ? ORDER BY step_number',
            (jid,),
        ).fetchall()
    result = dict(row)
    result['steps'] = [dict(s) for s in steps]
    return result


def list_journeys(*, status: str | None = None) -> list[dict[str, Any]]:
    where = 'WHERE status = ?' if status else ''
    params = [status] if status else []
    with get_connection() as conn:
        rows = conn.execute(
            f'SELECT * FROM journeys {where} ORDER BY updated_at DESC',
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def update_journey(jid: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {'name', 'description', 'trigger_event', 'trigger_delay_hours',
               'target_list_id', 'status'}
    sets = []
    params = []
    for k, v in updates.items():
        if k in allowed:
            sets.append(f'{k} = ?')
            params.append(v)
    if not sets:
        return get_journey(jid)
    sets.append('updated_at = ?')
    params.append(_now())
    params.append(jid)
    with get_connection() as conn:
        conn.execute(f'UPDATE journeys SET {", ".join(sets)} WHERE id = ?', params)
    return get_journey(jid)


def add_step(journey_id: str, step: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as conn:
        max_step = conn.execute(
            'SELECT COALESCE(MAX(step_number), 0) FROM journey_steps WHERE journey_id = ?',
            (journey_id,),
        ).fetchone()[0]
        _insert_step(conn, journey_id, max_step + 1, step)
        new_step = conn.execute(
            'SELECT * FROM journey_steps WHERE journey_id = ? ORDER BY step_number DESC LIMIT 1',
            (journey_id,),
        ).fetchone()
    return dict(new_step)


def delete_step(step_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute('DELETE FROM journey_steps WHERE id = ?', (step_id,))
    return cur.rowcount > 0


def replace_steps(journey_id: str, steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replace all steps for a journey."""
    with get_connection() as conn:
        conn.execute('DELETE FROM journey_steps WHERE journey_id = ?', (journey_id,))
        for i, step in enumerate(steps, start=1):
            _insert_step(conn, journey_id, i, step)
        rows = conn.execute(
            'SELECT * FROM journey_steps WHERE journey_id = ? ORDER BY step_number',
            (journey_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Enrollment ─────────────────────────────────────────────────────────────────

def enroll_customer(
    journey_id: str,
    customer_email: str,
    *,
    customer_id: str | None = None,
    trigger_context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Enroll a customer in a journey.
    Returns the execution record (or None if already enrolled and active).
    """
    journey = get_journey(journey_id)
    if not journey or journey['status'] != 'active':
        return None

    now = _now()

    with get_connection() as conn:
        # Prevent duplicate active enrollments
        existing = conn.execute(
            '''
            SELECT id FROM journey_executions
            WHERE journey_id = ? AND customer_email = ? AND status = 'active'
            ''',
            (journey_id, customer_email),
        ).fetchone()
        if existing:
            logger.debug('customer already enrolled: %s in %s', customer_email, journey_id)
            return None

        eid = _new_id()
        conn.execute(
            '''
            INSERT INTO journey_executions
                (id, journey_id, customer_id, customer_email, triggered_at,
                 trigger_context, current_step, status, started_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, 'active', ?, ?)
            ''',
            (
                eid, journey_id,
                customer_id or customer_email,
                customer_email,
                now,
                json.dumps(trigger_context or {}),
                now, now,
            ),
        )
        conn.execute(
            'UPDATE journeys SET enrolled_count = enrolled_count + 1, updated_at = ? WHERE id = ?',
            (now, journey_id),
        )

        # Schedule the first step immediately (or with trigger delay)
        steps = journey['steps']
        if steps:
            _schedule_step_send(conn, eid, steps[0], customer_email, trigger_dt=datetime.now(timezone.utc))

        row = conn.execute('SELECT * FROM journey_executions WHERE id = ?', (eid,)).fetchone()

    return dict(row)


def _schedule_step_send(
    conn,
    execution_id: str,
    step: dict[str, Any],
    customer_email: str,
    trigger_dt: datetime,
) -> None:
    delay = timedelta(
        days=int(step.get('delay_days', 0)),
        hours=int(step.get('delay_hours', 0)),
    )
    base_scheduled_at = trigger_dt + delay

    try:
        from app.services.customer_intelligence_service import decide_journey_delivery
        decision = decide_journey_delivery(conn, customer_email, step, base_scheduled_at)
        channels = decision.get('channels', [])
        scheduled_dt = decision.get('scheduled_at') or base_scheduled_at
    except Exception as exc:
        logger.warning('AI journey delivery decision failed for %s: %s', customer_email, exc)
        channels = ['email', 'whatsapp'] if step.get('channel') == 'both' else [step.get('channel', 'email')]
        scheduled_dt = base_scheduled_at

    if not channels:
        logger.info('journey step not scheduled for %s step=%s: no channels', customer_email, step.get('id'))
        return

    scheduled_at = scheduled_dt.isoformat() if hasattr(scheduled_dt, 'isoformat') else str(scheduled_dt)

    conn.execute(
        'UPDATE journey_executions SET current_step = ? WHERE id = ?',
        (int(step.get('step_number', 0)), execution_id),
    )

    for ch in channels:
        sid = _new_id()
        conn.execute(
            '''
            INSERT INTO journey_step_sends
                (id, execution_id, step_id, channel, template_id,
                 scheduled_at, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'queued', ?)
            ''',
            (sid, execution_id, step['id'], ch, step.get('template_id'), scheduled_at, _now()),
        )


# ── Execution runner (called by scheduler) ────────────────────────────────────

def run_due_steps(*, dry_run: bool = False) -> list[SendResult]:
    """
    Fetch all queued step_sends that are due, execute them.
    Called every 5 minutes by APScheduler.
    """
    now_dt = datetime.now(timezone.utc)
    results: list[SendResult] = []

    with get_connection() as conn:
        due = conn.execute(
            '''
            SELECT ss.*, je.customer_email, je.trigger_context,
                   je.journey_id, js.conditions_json, js.journey_id as j_id
            FROM journey_step_sends ss
            JOIN journey_executions je ON ss.execution_id = je.id
            JOIN journey_steps js ON ss.step_id = js.id
            WHERE ss.status = 'queued' AND ss.scheduled_at <= ?
            ORDER BY ss.scheduled_at ASC
            LIMIT 100
            ''',
            (now_dt.isoformat(),),
        ).fetchall()

    for send in due:
        result = _execute_step_send(dict(send), dry_run=dry_run)
        results.append(result)

        # Schedule next step if current step succeeded
        if result.status in ('sent', 'dry_run', 'skipped'):
            _maybe_schedule_next(send['execution_id'], send['step_id'])

    return results


def _execute_step_send(send: dict[str, Any], *, dry_run: bool = False) -> SendResult:
    execution_id = send['execution_id']
    step_id = send['step_id']
    channel = send['channel']
    customer_email = send['customer_email']
    template_id = send.get('template_id')

    # Check suppression conditions
    conditions = json.loads(send.get('conditions_json') or '{}')
    if _should_suppress(customer_email, conditions):
        _update_send_status(send['id'], 'skipped', reason='suppressed by condition')
        return SendResult(execution_id, step_id, channel, customer_email, 'skipped')

    if not template_id:
        _update_send_status(send['id'], 'skipped', reason='no_template')
        return SendResult(execution_id, step_id, channel, customer_email, 'skipped')

    # Load template
    template = get_template(template_id)
    if not template:
        _update_send_status(send['id'], 'failed', reason='template_not_found')
        return SendResult(execution_id, step_id, channel, customer_email, 'failed',
                          error='template_not_found')

    # Build variables from customer record + trigger context
    variables = _build_variables(customer_email, send.get('trigger_context', '{}'))
    rendered = render_template(template, channel, variables)

    if dry_run:
        _update_send_status(send['id'], 'dry_run')
        return SendResult(execution_id, step_id, channel, customer_email, 'dry_run')

    # Dispatch
    try:
        msg_id = ''
        if channel == 'email':
            result = send_email(
                to_email=customer_email,
                subject=rendered.get('email_subject', '(no subject)'),
                html_body=rendered.get('email_html', ''),
                text_body=rendered.get('email_text', ''),
            )
            msg_id = str(result.get('message_id', ''))
        elif channel == 'whatsapp':
            # Use existing wabis_client
            from app import wabis_client
            from app.config import settings
            wa_result = wabis_client.send_template_message(
                phone=_get_phone_for_email(customer_email),
                template_name=template.get('name', ''),
                body_params=_extract_wa_params(rendered.get('whatsapp_body', ''), variables),
                shop_domain=settings.default_shop_domain or "rwxtic-gz.myshopify.com",
            )
            msg_id = str(wa_result.get('messages', [{}])[0].get('id', ''))

        _update_send_status(send['id'], 'sent', message_id=msg_id)
        return SendResult(execution_id, step_id, channel, customer_email, 'sent', message_id=msg_id)

    except Exception as exc:
        logger.error('journey_step_send failed: exec=%s step=%s: %s', execution_id, step_id, exc)
        _update_send_status(send['id'], 'failed', reason=str(exc))
        return SendResult(execution_id, step_id, channel, customer_email, 'failed', error=str(exc))


def _maybe_schedule_next(execution_id: str, completed_step_id: str) -> None:
    with get_connection() as conn:
        exec_row = conn.execute(
            'SELECT * FROM journey_executions WHERE id = ?',
            (execution_id,),
        ).fetchone()
        if not exec_row or exec_row['status'] != 'active':
            return

        # Find the next step
        current_step = conn.execute(
            'SELECT * FROM journey_steps WHERE id = ?',
            (completed_step_id,),
        ).fetchone()
        if not current_step:
            return

        next_step = conn.execute(
            '''
            SELECT * FROM journey_steps
            WHERE journey_id = ? AND step_number > ?
            ORDER BY step_number ASC LIMIT 1
            ''',
            (current_step['journey_id'], current_step['step_number']),
        ).fetchone()

        if next_step:
            # Get the sent_at of the just-completed send as reference point
            completed_send = conn.execute(
                '''
                SELECT sent_at, scheduled_at FROM journey_step_sends
                WHERE execution_id = ? AND step_id = ? AND status IN ('sent', 'dry_run', 'skipped')
                ORDER BY created_at DESC LIMIT 1
                ''',
                (execution_id, completed_step_id),
            ).fetchone()
            ref_time_str = (
                (completed_send['sent_at'] or completed_send['scheduled_at'])
                if completed_send else _now()
            )
            ref_time = _parse_dt(ref_time_str) or datetime.now(timezone.utc)
            _schedule_step_send(conn, execution_id, dict(next_step), exec_row['customer_email'], ref_time)
        else:
            # No more steps → mark execution complete
            conn.execute(
                '''
                UPDATE journey_executions SET status = 'completed', completed_at = ?, updated_at = ?
                WHERE id = ?
                ''',
                (_now(), _now(), execution_id),
            )
            conn.execute(
                'UPDATE journeys SET completed_count = completed_count + 1 WHERE id = ?',
                (exec_row['journey_id'],),
            )


def _update_send_status(
    send_id: str,
    status: str,
    *,
    reason: str | None = None,
    message_id: str | None = None,
) -> None:
    now = _now()
    with get_connection() as conn:
        conn.execute(
            '''
            UPDATE journey_step_sends
            SET status = ?, error_reason = COALESCE(?, error_reason),
                message_id = COALESCE(?, message_id),
                sent_at = CASE WHEN ? IN ('sent','dry_run') THEN ? ELSE sent_at END
            WHERE id = ?
            ''',
            (status, reason, message_id, status, now, send_id),
        )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _should_suppress(customer_email: str, conditions: dict[str, Any]) -> bool:
    """Basic suppression: check email suppression list."""
    if not conditions:
        return False
    with get_connection() as conn:
        sup = conn.execute(
            'SELECT id FROM email_suppression WHERE email = ?',
            (customer_email.lower(),),
        ).fetchone()
    if sup:
        return True
    return False


def _build_variables(customer_email: str, trigger_context_json: str) -> dict[str, Any]:
    variables: dict[str, Any] = {'email': customer_email}
    try:
        ctx = json.loads(trigger_context_json or '{}')
        variables.update(ctx)
    except Exception:
        pass

    with get_connection() as conn:
        c = conn.execute(
            'SELECT first_name, name, total_orders, total_spent FROM customers WHERE email = ?',
            (customer_email,),
        ).fetchone()
    if c:
        variables['first_name'] = c['first_name'] or (c['name'] or '').split()[0] or 'there'
        variables['name'] = c['name'] or ''
        variables['total_orders'] = c['total_orders']
        variables['total_spent'] = c['total_spent']

    return variables


def _get_phone_for_email(customer_email: str) -> str:
    with get_connection() as conn:
        row = conn.execute(
            'SELECT phone FROM customers WHERE email = ?',
            (customer_email,),
        ).fetchone()
    return row['phone'] if row and row['phone'] else ''


def _extract_wa_params(body: str, variables: dict[str, Any]) -> list[str]:
    """Extract ordered parameter values from a rendered WhatsApp body."""
    # After rendering, there should be no {{vars}} left.
    # Return variables values that were used as positional params.
    return [str(v) for v in variables.values() if v]


# ── Journey analytics ──────────────────────────────────────────────────────────

def get_journey_stats(journey_id: str) -> dict[str, Any]:
    with get_connection() as conn:
        journey = conn.execute('SELECT * FROM journeys WHERE id = ?', (journey_id,)).fetchone()
        if not journey:
            return {}
        stats = conn.execute(
            '''
            SELECT
                COUNT(DISTINCT je.id) as total_enrolled,
                SUM(CASE WHEN je.status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN je.status = 'active' THEN 1 ELSE 0 END) as active,
                COUNT(DISTINCT ss.id) as total_sends,
                SUM(CASE WHEN ss.status = 'sent' THEN 1 ELSE 0 END) as sent,
                SUM(CASE WHEN ss.status = 'opened' THEN 1 ELSE 0 END) as opened,
                SUM(CASE WHEN ss.status = 'clicked' THEN 1 ELSE 0 END) as clicked,
                SUM(CASE WHEN ss.status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM journey_executions je
            LEFT JOIN journey_step_sends ss ON ss.execution_id = je.id
            WHERE je.journey_id = ?
            ''',
            (journey_id,),
        ).fetchone()
    return {
        'journey_id': journey_id,
        'name': journey['name'],
        'status': journey['status'],
        'enrolled_count': journey['enrolled_count'],
        'completed_count': journey['completed_count'],
        **({k: stats[k] for k in stats.keys()} if stats else {}),
    }


def get_journey_graph_summary() -> list[dict[str, Any]]:
    """Return per-journey node counts for dashboard graph-style overview."""
    with get_connection() as conn:
        journeys = conn.execute(
            "SELECT id, name, status FROM journeys ORDER BY created_at DESC"
        ).fetchall()

        output: list[dict[str, Any]] = []
        for journey in journeys:
            total_customers = conn.execute(
                "SELECT COUNT(*) FROM journey_executions WHERE journey_id = ?",
                (journey['id'],),
            ).fetchone()[0]

            step_counts = conn.execute(
                '''
                SELECT js.step_number, COUNT(*) AS customers
                FROM journey_executions je
                JOIN journey_steps js ON js.journey_id = je.journey_id
                WHERE je.journey_id = ? AND je.current_step = js.step_number
                GROUP BY js.step_number
                ORDER BY js.step_number
                ''',
                (journey['id'],),
            ).fetchall()

            purchased = conn.execute(
                '''
                SELECT COUNT(*)
                FROM journey_executions je
                JOIN customers c ON c.email = je.customer_email
                WHERE je.journey_id = ? AND c.deleted_at IS NULL AND COALESCE(c.total_orders, 0) > 0
                ''',
                (journey['id'],),
            ).fetchone()[0]

            output.append({
                'journey_id': journey['id'],
                'journey_name': journey['name'],
                'status': journey['status'],
                'total_customers': total_customers,
                'purchased_customers': purchased,
                'steps': [{'step_number': r['step_number'], 'customers': r['customers']} for r in step_counts],
            })

    return output
