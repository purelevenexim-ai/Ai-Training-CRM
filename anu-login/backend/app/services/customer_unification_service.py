"""
Customer Unification Service

Maintains a single customer record per person across:
  - Shopify orders
  - CSV imports
  - WhatsApp interactions
  - Manual entry

Identity resolution: email (primary key) → phone (secondary)
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
import xml.etree.ElementTree as ET
import uuid
from datetime import datetime, timezone
from typing import Any

from app.storage import get_connection

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalise_email(email: str) -> str:
    return email.strip().lower()


def _normalise_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 10:
        return f'+91{digits}'
    if len(digits) == 12 and digits.startswith('91'):
        return f'+{digits}'
    if len(digits) == 13 and digits.startswith('091'):
        return f'+{digits[1:]}'
    return f'+{digits}' if not digits.startswith('+') else phone.strip()


def _new_id() -> str:
    return str(uuid.uuid4())


def _new_customer_uid() -> str:
    return f"CUS-{uuid.uuid4().hex[:12].upper()}"


def _record_identity(
    conn,
    *,
    customer_uid: str,
    customer_id: str,
    identity_type: str,
    identity_value: str | None,
    source: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    if not identity_value:
        return
    value = str(identity_value).strip()
    if not value:
        return
    now = _now()
    conn.execute(
        '''
        INSERT INTO customer_identities
            (id, customer_uid, customer_id, identity_type, identity_value, source,
             metadata_json, first_seen_at, last_seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(customer_uid, identity_type, identity_value) DO UPDATE SET
            customer_id = excluded.customer_id,
            source = excluded.source,
            metadata_json = excluded.metadata_json,
            last_seen_at = excluded.last_seen_at
        ''',
        (
            _new_id(), customer_uid, customer_id, identity_type, value, source,
            json.dumps(metadata or {}, ensure_ascii=True, sort_keys=True), now, now,
        ),
    )


def _sync_customer_identities(conn, customer: dict[str, Any], source: str) -> None:
    customer_uid = customer.get('customer_uid')
    customer_id = customer.get('id')
    if not customer_uid or not customer_id:
        return

    identity_specs = [
        ('email', customer.get('email'), 'crm'),
        ('phone', customer.get('phone'), 'crm'),
        ('whatsapp_number', customer.get('whatsapp_number') or customer.get('phone'), 'whatsapp'),
        ('shopify_customer_id', customer.get('shopify_customer_id'), 'shopify'),
        ('meta_lead_id', customer.get('meta_lead_id'), 'meta'),
        ('meta_campaign', customer.get('meta_campaign'), 'meta'),
        ('google_gclid', customer.get('google_gclid'), 'google'),
        ('google_campaign', customer.get('google_campaign'), 'google'),
    ]
    for identity_type, identity_value, default_source in identity_specs:
        _record_identity(
            conn,
            customer_uid=customer_uid,
            customer_id=customer_id,
            identity_type=identity_type,
            identity_value=identity_value,
            source=source if source in ('shopify', 'shopify_webhook', 'shopify_backfill', 'meta', 'google') else default_source,
        )


# ── Core operations ────────────────────────────────────────────────────────────

def upsert_customer(
    *,
    email: str,
    name: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    phone: str | None = None,
    shopify_customer_id: str | None = None,
    tags: list[str] | None = None,
    source: str = 'manual',
    email_opted_in: bool | None = None,
    whatsapp_opted_in: bool | None = None,
    notes: str | None = None,
    meta_lead_id: str | None = None,
    google_gclid: str | None = None,
    google_campaign: str | None = None,
    meta_campaign: str | None = None,
    preferred_channel: str | None = None,
    pause_campaigns: bool | None = None,
) -> dict[str, Any]:
    """Insert or update a customer. Returns the final customer record."""
    email = _normalise_email(email)
    phone = _normalise_phone(phone)
    now = _now()

    with get_connection() as conn:
        existing = conn.execute(
            'SELECT * FROM customers WHERE email = ? AND deleted_at IS NULL',
            (email,),
        ).fetchone()

        if existing is None:
            cid = _new_id()
            customer_uid = _new_customer_uid()
            derived_name = name or (
                f'{first_name or ""} {last_name or ""}'.strip() or None
            )
            conn.execute(
                '''
                INSERT INTO customers
                    (id, customer_uid, email, phone, whatsapp_number, name, first_name, last_name,
                     shopify_customer_id, tags, source, customer_status,
                     meta_lead_id, google_gclid, google_campaign, meta_campaign,
                     preferred_channel, pause_campaigns,
                     email_opted_in, whatsapp_opted_in, notes,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    cid, customer_uid, email, phone, phone,
                    derived_name, first_name, last_name,
                    shopify_customer_id,
                    json.dumps(tags or []),
                    source,
                    meta_lead_id,
                    google_gclid,
                    google_campaign,
                    meta_campaign,
                    (preferred_channel or 'auto'),
                    1 if pause_campaigns else 0,
                    1 if email_opted_in else 0,
                    1 if whatsapp_opted_in else 0,
                    notes, now, now,
                ),
            )
            logger.info('customer.created email=%s source=%s', email, source)
        else:
            cid = existing['id']
            # Merge: update fields that have new values, keep existing for nulls
            merged_phone = phone or existing['phone']
            merged_name = name or existing['name']
            merged_fn = first_name or existing['first_name']
            merged_ln = last_name or existing['last_name']
            merged_shopify = shopify_customer_id or existing['shopify_customer_id']
            merged_notes = notes or existing['notes']
            merged_meta_lead_id = meta_lead_id or existing['meta_lead_id']
            merged_google_gclid = google_gclid or existing['google_gclid']
            merged_google_campaign = google_campaign or existing['google_campaign']
            merged_meta_campaign = meta_campaign or existing['meta_campaign']
            merged_preferred_channel = preferred_channel or existing['preferred_channel'] or 'auto'
            merged_pause = (1 if pause_campaigns else 0) if pause_campaigns is not None else existing['pause_campaigns']

            # Merge tags (union of both)
            existing_tags = json.loads(existing['tags'] or '[]')
            merged_tags_set = set(existing_tags) | set(tags or [])
            merged_tags = json.dumps(sorted(merged_tags_set))

            opt_in_email = (
                1 if email_opted_in
                else (0 if email_opted_in is False else existing['email_opted_in'])
            )
            opt_in_wa = (
                1 if whatsapp_opted_in
                else (0 if whatsapp_opted_in is False else existing['whatsapp_opted_in'])
            )

            conn.execute(
                '''
                UPDATE customers SET
                    phone = ?, name = ?, first_name = ?, last_name = ?,
                    shopify_customer_id = ?, tags = ?,
                    meta_lead_id = ?, google_gclid = ?, google_campaign = ?, meta_campaign = ?,
                    preferred_channel = ?, pause_campaigns = ?,
                    whatsapp_number = COALESCE(?, whatsapp_number),
                    email_opted_in = ?, whatsapp_opted_in = ?,
                    notes = ?, updated_at = ?
                WHERE id = ?
                ''',
                (
                    merged_phone, merged_name, merged_fn, merged_ln,
                    merged_shopify, merged_tags,
                    merged_meta_lead_id, merged_google_gclid, merged_google_campaign, merged_meta_campaign,
                    merged_preferred_channel, merged_pause,
                    merged_phone,
                    opt_in_email, opt_in_wa,
                    merged_notes, now, cid,
                ),
            )
            logger.debug('customer.updated email=%s', email)

        row = conn.execute('SELECT * FROM customers WHERE id = ?', (cid,)).fetchone()
        _sync_customer_identities(conn, dict(row), source)

    return dict(row)


def list_customer_identities(email: str) -> list[dict[str, Any]]:
    email = _normalise_email(email)
    with get_connection() as conn:
        customer = conn.execute(
            'SELECT customer_uid FROM customers WHERE email = ? AND deleted_at IS NULL',
            (email,),
        ).fetchone()
        if not customer:
            return []
        rows = conn.execute(
            '''
            SELECT id, customer_uid, identity_type, identity_value, source,
                   metadata_json, first_seen_at, last_seen_at
            FROM customer_identities
            WHERE customer_uid = ?
            ORDER BY identity_type, last_seen_at DESC
            ''',
            (customer['customer_uid'],),
        ).fetchall()

    result = []
    for row in rows:
        item = dict(row)
        try:
            item['metadata'] = json.loads(item.pop('metadata_json') or '{}')
        except Exception:
            item['metadata'] = {}
        result.append(item)
    return result


def sync_order_stats(customer_email: str, *, total_orders: int, total_spent: float,
                     last_order_date: str | None, first_order_date: str | None = None) -> None:
    """Update order aggregates after a Shopify sync."""
    now = _now()
    with get_connection() as conn:
        conn.execute(
            '''
            UPDATE customers SET
                total_orders = ?, total_spent = ?,
                last_order_date = ?,
                first_order_date = COALESCE(first_order_date, ?),
                customer_status = CASE
                    WHEN ? >= 5 AND ? >= 5000 THEN 'vip'
                    WHEN ? >= 1 THEN 'active'
                    ELSE customer_status
                END,
                purchase_status = CASE WHEN ? >= 1 THEN 'purchased' ELSE 'not_purchased' END,
                updated_at = ?
            WHERE email = ? AND deleted_at IS NULL
            ''',
            (
                total_orders, total_spent, last_order_date, first_order_date,
                total_orders, total_spent, total_orders,
                total_orders,
                now, customer_email,
            ),
        )


def get_customer(email: str) -> dict[str, Any] | None:
    email = _normalise_email(email)
    with get_connection() as conn:
        row = conn.execute(
            'SELECT * FROM customers WHERE email = ? AND deleted_at IS NULL',
            (email,),
        ).fetchone()
    return dict(row) if row else None


def get_customer_by_id(cid: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            'SELECT * FROM customers WHERE id = ? AND deleted_at IS NULL',
            (cid,),
        ).fetchone()
    return dict(row) if row else None


def list_customers(
    *,
    limit: int = 50,
    offset: int = 0,
    search: str | None = None,
    status: str | None = None,
    email_opted_in: bool | None = None,
    order_by: str = 'created_at',
    order_dir: str = 'DESC',
) -> tuple[list[dict[str, Any]], int]:
    """Returns (rows, total_count)."""
    safe_cols = {'created_at', 'updated_at', 'email', 'total_spent', 'total_orders', 'last_order_date'}
    order_col = order_by if order_by in safe_cols else 'created_at'
    order_d = 'ASC' if order_dir.upper() == 'ASC' else 'DESC'

    where_clauses = ['deleted_at IS NULL']
    params: list[Any] = []

    if search:
        where_clauses.append('(email LIKE ? OR name LIKE ? OR phone LIKE ?)')
        like = f'%{search}%'
        params.extend([like, like, like])
    if status:
        where_clauses.append('customer_status = ?')
        params.append(status)
    if email_opted_in is not None:
        where_clauses.append('email_opted_in = ?')
        params.append(1 if email_opted_in else 0)

    where = ' AND '.join(where_clauses)

    with get_connection() as conn:
        total = conn.execute(f'SELECT COUNT(*) FROM customers WHERE {where}', params).fetchone()[0]
        rows = conn.execute(
            f'SELECT * FROM customers WHERE {where} ORDER BY {order_col} {order_d} LIMIT ? OFFSET ?',
            params + [limit, offset],
        ).fetchall()

    return [dict(r) for r in rows], total


def soft_delete_customer(email: str) -> bool:
    email = _normalise_email(email)
    now = _now()
    with get_connection() as conn:
        cur = conn.execute(
            'UPDATE customers SET deleted_at = ?, updated_at = ? WHERE email = ? AND deleted_at IS NULL',
            (now, now, email),
        )
    return cur.rowcount > 0


def set_pause_campaigns(email: str, paused: bool) -> bool:
    email = _normalise_email(email)
    now = _now()
    with get_connection() as conn:
        cur = conn.execute(
            'UPDATE customers SET pause_campaigns = ?, updated_at = ? WHERE email = ? AND deleted_at IS NULL',
            (1 if paused else 0, now, email),
        )
    return cur.rowcount > 0


# ── CSV Import ─────────────────────────────────────────────────────────────────

def import_csv(
    csv_content: str,
    *,
    filename: str = 'upload.csv',
    default_tags: list[str] | None = None,
    email_opted_in: bool = True,
) -> dict[str, Any]:
    """
    Parse CSV text and upsert customers.

    Expected columns (case-insensitive, flexible names):
      email (required), name / first_name / last_name, phone, tags
    Returns an import summary dict.
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    fieldnames = [f.lower().strip() for f in (reader.fieldnames or [])]

    # Normalise header aliases
    col_map: dict[str, str] = {}
    for raw in (reader.fieldnames or []):
        low = raw.lower().strip()
        if 'email' in low:
            col_map['email'] = raw
        elif 'first' in low and 'name' in low:
            col_map['first_name'] = raw
        elif 'last' in low and 'name' in low:
            col_map['last_name'] = raw
        elif 'name' in low and 'first' not in low and 'last' not in low:
            col_map['name'] = raw
        elif 'phone' in low or 'mobile' in low or 'whatsapp' in low:
            col_map['phone'] = raw
        elif 'tag' in low:
            col_map['tags'] = raw

    if 'email' not in col_map:
        return {
            'status': 'error',
            'message': 'CSV must contain an email column',
            'total_rows': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': [],
        }

    created = updated = skipped = error_count = 0
    errors: list[dict[str, Any]] = []
    row_num = 0

    for row in reader:
        row_num += 1
        email_raw = row.get(col_map['email'], '').strip()
        if not email_raw or '@' not in email_raw:
            skipped += 1
            continue

        try:
            email = _normalise_email(email_raw)
            first_name = row.get(col_map.get('first_name', ''), '').strip() or None
            last_name = row.get(col_map.get('last_name', ''), '').strip() or None
            name = row.get(col_map.get('name', ''), '').strip() or None
            phone = row.get(col_map.get('phone', ''), '').strip() or None
            tag_str = row.get(col_map.get('tags', ''), '').strip()
            row_tags = [t.strip() for t in tag_str.split(',') if t.strip()]
            merged_tags = list(set((default_tags or []) + row_tags))

            existing_before = get_customer(email)
            upsert_customer(
                email=email,
                name=name,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                tags=merged_tags,
                source='csv_import',
                email_opted_in=email_opted_in,
            )
            if existing_before is None:
                created += 1
            else:
                updated += 1
        except Exception as exc:
            error_count += 1
            errors.append({'row': row_num, 'email': email_raw, 'error': str(exc)})
            logger.warning('csv_import row=%d error: %s', row_num, exc)

    # Log the import
    now = _now()
    import_id = _new_id()
    with get_connection() as conn:
        conn.execute(
            '''
            INSERT INTO csv_import_log
                (id, filename, total_rows, created_count, updated_count,
                 skipped_count, error_count, errors_json, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'complete', ?)
            ''',
            (
                import_id, filename, row_num,
                created, updated, skipped, error_count,
                json.dumps(errors[:50]),  # cap error list
                now,
            ),
        )

    return {
        'status': 'complete',
        'import_id': import_id,
        'total_rows': row_num,
        'created': created,
        'updated': updated,
        'skipped': skipped,
        'errors': errors[:20],
    }


def import_xml(
    xml_content: str,
    *,
    filename: str = 'upload.xml',
    default_tags: list[str] | None = None,
    email_opted_in: bool = True,
) -> dict[str, Any]:
    """
    Parse XML text and upsert customers.

    Expected shape:
    <customers>
      <customer>
        <name>..</name>
        <email>..</email>
        <phone>..</phone>
      </customer>
    </customers>
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        return {
            'status': 'error',
            'message': f'Invalid XML: {exc}',
            'total_rows': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': [],
        }

    rows = root.findall('.//customer')
    created = updated = skipped = error_count = 0
    errors: list[dict[str, Any]] = []

    for idx, customer in enumerate(rows, start=1):
        email_raw = (customer.findtext('email') or '').strip()
        if not email_raw or '@' not in email_raw:
            skipped += 1
            continue

        try:
            name = (customer.findtext('name') or '').strip() or None
            first_name = (customer.findtext('first_name') or '').strip() or None
            last_name = (customer.findtext('last_name') or '').strip() or None
            phone = (customer.findtext('phone') or customer.findtext('mobile') or '').strip() or None
            tags_raw = (customer.findtext('tags') or '').strip()
            row_tags = [t.strip() for t in tags_raw.split(',') if t.strip()]
            merged_tags = list(set((default_tags or []) + row_tags))

            existing_before = get_customer(email_raw)
            upsert_customer(
                email=email_raw,
                name=name,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                tags=merged_tags,
                source='xml_import',
                email_opted_in=email_opted_in,
            )
            if existing_before is None:
                created += 1
            else:
                updated += 1
        except Exception as exc:
            error_count += 1
            errors.append({'row': idx, 'email': email_raw, 'error': str(exc)})

    now = _now()
    import_id = _new_id()
    with get_connection() as conn:
        conn.execute(
            '''
            INSERT INTO csv_import_log
                (id, filename, total_rows, created_count, updated_count,
                 skipped_count, error_count, errors_json, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'complete', ?)
            ''',
            (
                import_id, filename, len(rows),
                created, updated, skipped, error_count,
                json.dumps(errors[:50]),
                now,
            ),
        )

    return {
        'status': 'complete',
        'import_id': import_id,
        'total_rows': len(rows),
        'created': created,
        'updated': updated,
        'skipped': skipped,
        'errors': errors[:20],
    }


# ── Shopify sync helpers ───────────────────────────────────────────────────────

def sync_shopify_customer(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Upsert a customer from a Shopify customers/create or customers/update webhook payload.
    """
    email = (payload.get('email') or '').strip()
    if not email or '@' not in email:
        return {'skipped': True, 'reason': 'no_email'}

    shopify_id = str(payload.get('id', ''))
    first = payload.get('first_name') or ''
    last = payload.get('last_name') or ''
    phone = payload.get('phone') or ''

    tags_raw = payload.get('tags', '')
    tags = [t.strip() for t in tags_raw.split(',') if t.strip()] if isinstance(tags_raw, str) else (tags_raw or [])

    orders_count = int(payload.get('orders_count', 0))
    total_spent_str = payload.get('total_spent', '0') or '0'
    total_spent = float(total_spent_str)

    last_order = payload.get('last_order_updated_at') or None

    customer = upsert_customer(
        email=email,
        first_name=first or None,
        last_name=last or None,
        phone=phone or None,
        shopify_customer_id=shopify_id,
        tags=tags,
        source='shopify',
        email_opted_in=True,
    )

    sync_order_stats(
        email,
        total_orders=orders_count,
        total_spent=total_spent,
        last_order_date=last_order,
    )

    return customer
