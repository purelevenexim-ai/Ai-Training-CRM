"""
Audience Service

Manages contact lists (static + dynamic) and communication templates.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.storage import get_connection

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


DEFAULT_TEMPLATES: list[dict[str, Any]] = [
    {
        'name': 'Welcome - Email + WhatsApp',
        'category': 'welcome',
        'description': 'Starter welcome template for new leads and subscribers.',
        'status': 'active',
        'email_subject': 'Welcome to PureLeven, {{first_name}}',
        'email_preheader': 'Organic essentials, carefully sourced for your kitchen.',
        'email_html': '''
<div style="font-family:Arial,sans-serif;line-height:1.6;color:#1f2937;max-width:620px;margin:0 auto;">
  <h2 style="color:#166534;">Welcome to PureLeven, {{first_name}}</h2>
  <p>Thank you for joining PureLeven. We bring clean, organic pantry essentials from trusted sources to your home.</p>
  <p>Start with our most-loved organic spices and wellness staples, then tell us what you cook most often so we can recommend better picks.</p>
  <p><a href="https://pureleven.com" style="display:inline-block;background:#166534;color:#fff;padding:12px 18px;border-radius:6px;text-decoration:none;font-weight:700;">Explore PureLeven</a></p>
</div>
'''.strip(),
        'email_text': 'Welcome to PureLeven, {{first_name}}. Explore our organic pantry essentials at https://pureleven.com',
        'whatsapp_body': 'Hi {{first_name}}, welcome to PureLeven. Explore our organic pantry essentials here: https://pureleven.com',
        'variables': ['first_name'],
    },
    {
        'name': 'Post Purchase - Thank You + Usage Guide',
        'category': 'post_purchase',
        'description': 'Thank-you and usage guide starter for purchased customers.',
        'status': 'active',
        'email_subject': 'Thank you for your PureLeven order, {{first_name}}',
        'email_preheader': 'A quick guide to get the best from your order.',
        'email_html': '''
<div style="font-family:Arial,sans-serif;line-height:1.6;color:#1f2937;max-width:620px;margin:0 auto;">
  <h2 style="color:#166534;">Thank you, {{first_name}}</h2>
  <p>Your PureLeven order means a lot to us. Use your products in small, consistent portions to enjoy the freshness and aroma.</p>
  <p>We will check in soon with usage ideas, review help, and products that pair well with your purchase.</p>
  <p><a href="https://pureleven.com" style="display:inline-block;background:#166534;color:#fff;padding:12px 18px;border-radius:6px;text-decoration:none;font-weight:700;">Visit Store</a></p>
</div>
'''.strip(),
        'email_text': 'Thank you for your PureLeven order, {{first_name}}. We will send usage ideas and helpful follow-ups soon.',
        'whatsapp_body': 'Thank you for your PureLeven order, {{first_name}}. We will send usage ideas and helpful follow-ups soon.',
        'variables': ['first_name'],
    },
    {
        'name': 'Warm Lead - Bundle Offer',
        'category': 'promotional',
        'description': 'Offer starter for warm and hot customers.',
        'status': 'active',
        'email_subject': '{{first_name}}, a PureLeven bundle picked for you',
        'email_preheader': 'Based on your recent interest, this is a good next step.',
        'email_html': '''
<div style="font-family:Arial,sans-serif;line-height:1.6;color:#1f2937;max-width:620px;margin:0 auto;">
  <h2 style="color:#166534;">A bundle picked for you</h2>
  <p>Hi {{first_name}}, based on your interest, a curated PureLeven bundle may be the easiest way to restock your kitchen.</p>
  <p>Explore clean, organic essentials and choose what fits your routine.</p>
  <p><a href="https://pureleven.com/collections/all" style="display:inline-block;background:#166534;color:#fff;padding:12px 18px;border-radius:6px;text-decoration:none;font-weight:700;">Browse Bundles</a></p>
</div>
'''.strip(),
        'email_text': 'Hi {{first_name}}, explore curated PureLeven bundles here: https://pureleven.com/collections/all',
        'whatsapp_body': 'Hi {{first_name}}, we picked a PureLeven bundle idea for you. Browse here: https://pureleven.com/collections/all',
        'variables': ['first_name'],
    },
]


def ensure_default_templates() -> dict[str, int]:
    """Create practical starter templates and repair empty built-in templates."""
    created = 0
    updated = 0
    now = _now()
    with get_connection() as conn:
        for template in DEFAULT_TEMPLATES:
            existing = conn.execute(
                'SELECT * FROM communication_templates WHERE name = ? LIMIT 1',
                (template['name'],),
            ).fetchone()
            if not existing:
                conn.execute(
                    '''
                    INSERT INTO communication_templates
                        (id, name, category, description, status,
                         email_subject, email_preheader, email_html, email_text,
                         whatsapp_body, whatsapp_header_image_url,
                         variables_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        _new_id(), template['name'], template['category'], template['description'], template['status'],
                        template['email_subject'], template['email_preheader'], template['email_html'], template['email_text'],
                        template['whatsapp_body'], None, json.dumps(template['variables']), now, now,
                    ),
                )
                created += 1
                continue

            if not existing['email_html'] or not existing['email_subject']:
                conn.execute(
                    '''
                    UPDATE communication_templates
                    SET category = ?, description = ?, status = ?, email_subject = ?,
                        email_preheader = ?, email_html = ?, email_text = ?,
                        whatsapp_body = ?, variables_json = ?, updated_at = ?
                    WHERE id = ?
                    ''',
                    (
                        template['category'], template['description'], template['status'], template['email_subject'],
                        template['email_preheader'], template['email_html'], template['email_text'],
                        template['whatsapp_body'], json.dumps(template['variables']), now, existing['id'],
                    ),
                )
                updated += 1

    return {'created': created, 'updated': updated}


# ── Contact Lists ──────────────────────────────────────────────────────────────

def create_list(
    name: str,
    *,
    description: str | None = None,
    list_type: str = 'static',
    rules: dict | None = None,
) -> dict[str, Any]:
    lid = _new_id()
    now = _now()
    with get_connection() as conn:
        conn.execute(
            '''
            INSERT INTO contact_lists (id, name, description, list_type, rules_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (lid, name, description, list_type, json.dumps(rules or {}), now, now),
        )
        row = conn.execute('SELECT * FROM contact_lists WHERE id = ?', (lid,)).fetchone()
    return dict(row)


def get_list(lid: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute('SELECT * FROM contact_lists WHERE id = ?', (lid,)).fetchone()
    return dict(row) if row else None


def list_all_lists() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            'SELECT * FROM contact_lists ORDER BY updated_at DESC'
        ).fetchall()
    return [dict(r) for r in rows]


def update_list(lid: str, *, name: str | None = None, description: str | None = None) -> dict[str, Any] | None:
    existing = get_list(lid)
    if not existing:
        return None
    now = _now()
    with get_connection() as conn:
        conn.execute(
            '''
            UPDATE contact_lists SET
                name = COALESCE(?, name),
                description = COALESCE(?, description),
                updated_at = ?
            WHERE id = ?
            ''',
            (name, description, now, lid),
        )
        row = conn.execute('SELECT * FROM contact_lists WHERE id = ?', (lid,)).fetchone()
    return dict(row)


def delete_list(lid: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute('DELETE FROM contact_lists WHERE id = ?', (lid,))
        conn.execute('DELETE FROM contact_list_members WHERE list_id = ?', (lid,))
    return cur.rowcount > 0


def add_to_list(list_id: str, customer_id: str) -> bool:
    now = _now()
    with get_connection() as conn:
        try:
            conn.execute(
                'INSERT OR IGNORE INTO contact_list_members (list_id, customer_id, added_at) VALUES (?, ?, ?)',
                (list_id, customer_id, now),
            )
            _refresh_list_count(conn, list_id)
            return True
        except Exception:
            return False


def bulk_add_to_list(list_id: str, customer_ids: list[str]) -> int:
    now = _now()
    added = 0
    with get_connection() as conn:
        for cid in customer_ids:
            try:
                conn.execute(
                    'INSERT OR IGNORE INTO contact_list_members (list_id, customer_id, added_at) VALUES (?, ?, ?)',
                    (list_id, cid, now),
                )
                added += conn.execute('SELECT changes()').fetchone()[0]
            except Exception:
                pass
        _refresh_list_count(conn, list_id)
    return added


def remove_from_list(list_id: str, customer_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            'DELETE FROM contact_list_members WHERE list_id = ? AND customer_id = ?',
            (list_id, customer_id),
        )
        _refresh_list_count(conn, list_id)
    return cur.rowcount > 0


def get_list_members(
    list_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """Returns (customers, total)."""
    with get_connection() as conn:
        total = conn.execute(
            'SELECT COUNT(*) FROM contact_list_members WHERE list_id = ?',
            (list_id,),
        ).fetchone()[0]
        rows = conn.execute(
            '''
            SELECT c.* FROM customers c
            JOIN contact_list_members m ON c.id = m.customer_id
            WHERE m.list_id = ? AND c.deleted_at IS NULL
            ORDER BY m.added_at DESC
            LIMIT ? OFFSET ?
            ''',
            (list_id, limit, offset),
        ).fetchall()
    return [dict(r) for r in rows], total


def _refresh_list_count(conn, list_id: str) -> None:
    count = conn.execute(
        'SELECT COUNT(*) FROM contact_list_members WHERE list_id = ?',
        (list_id,),
    ).fetchone()[0]
    conn.execute(
        'UPDATE contact_lists SET customer_count = ?, updated_at = ? WHERE id = ?',
        (count, _now(), list_id),
    )


# ── Communication Templates ────────────────────────────────────────────────────

def create_template(
    *,
    name: str,
    category: str = 'promotional',
    description: str | None = None,
    email_subject: str | None = None,
    email_preheader: str | None = None,
    email_html: str | None = None,
    email_text: str | None = None,
    whatsapp_body: str | None = None,
    whatsapp_header_image_url: str | None = None,
    variables: list[str] | None = None,
    status: str = 'draft',
) -> dict[str, Any]:
    tid = _new_id()
    now = _now()
    with get_connection() as conn:
        conn.execute(
            '''
            INSERT INTO communication_templates
                (id, name, category, description, status,
                 email_subject, email_preheader, email_html, email_text,
                 whatsapp_body, whatsapp_header_image_url,
                 variables_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                tid, name, category, description, status,
                email_subject, email_preheader, email_html, email_text,
                whatsapp_body, whatsapp_header_image_url,
                json.dumps(variables or []),
                now, now,
            ),
        )
        row = conn.execute('SELECT * FROM communication_templates WHERE id = ?', (tid,)).fetchone()
    return dict(row)


def get_template(tid: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute('SELECT * FROM communication_templates WHERE id = ?', (tid,)).fetchone()
    return dict(row) if row else None


def list_templates(
    *,
    category: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    where_clauses = []
    params: list[Any] = []
    if category:
        where_clauses.append('category = ?')
        params.append(category)
    if status:
        where_clauses.append('status = ?')
        params.append(status)
    where = ('WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''

    with get_connection() as conn:
        total = conn.execute(f'SELECT COUNT(*) FROM communication_templates {where}', params).fetchone()[0]
        rows = conn.execute(
            f'SELECT * FROM communication_templates {where} ORDER BY updated_at DESC LIMIT ? OFFSET ?',
            params + [limit, offset],
        ).fetchall()
    return [dict(r) for r in rows], total


def update_template(tid: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    existing = get_template(tid)
    if not existing:
        return None
    now = _now()
    allowed = {
        'name', 'category', 'description', 'status',
        'email_subject', 'email_preheader', 'email_html', 'email_text',
        'whatsapp_body', 'whatsapp_header_image_url',
    }
    sets = []
    params = []
    for k, v in updates.items():
        if k in allowed:
            sets.append(f'{k} = ?')
            params.append(v)
    if 'variables' in updates:
        sets.append('variables_json = ?')
        params.append(json.dumps(updates['variables']))
    if not sets:
        return existing
    sets.append('updated_at = ?')
    params.append(now)
    params.append(tid)
    with get_connection() as conn:
        conn.execute(f'UPDATE communication_templates SET {", ".join(sets)} WHERE id = ?', params)
        row = conn.execute('SELECT * FROM communication_templates WHERE id = ?', (tid,)).fetchone()
    return dict(row)


def delete_template(tid: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute('DELETE FROM communication_templates WHERE id = ?', (tid,))
    return cur.rowcount > 0


# ── Template Rendering ─────────────────────────────────────────────────────────

def render_template(template: dict[str, Any], channel: str, variables: dict[str, Any]) -> dict[str, str]:
    """
    Render a communication template for a given channel and variables.
    Returns dict with rendered fields.
    """
    result: dict[str, str] = {}

    def _interp(text: str | None) -> str:
        if not text:
            return ''
        for k, v in variables.items():
            text = text.replace('{{' + k + '}}', str(v))
        return text

    if channel in ('email', 'both'):
        result['email_subject'] = _interp(template.get('email_subject'))
        result['email_preheader'] = _interp(template.get('email_preheader'))
        result['email_html'] = _interp(template.get('email_html'))
        result['email_text'] = _interp(template.get('email_text'))

    if channel in ('whatsapp', 'both'):
        result['whatsapp_body'] = _interp(template.get('whatsapp_body'))
        result['whatsapp_header_image_url'] = template.get('whatsapp_header_image_url') or ''

    return result
