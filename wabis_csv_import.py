#!/usr/bin/env python3
"""
Wabis CSV Import Script
Reads Wabis subscriber export CSV(s) and imports into the WhatsApp CRM SQLite.

Usage:
    python3 wabis_csv_import.py <file1.csv> [file2.csv ...]

CSV columns expected (Wabis export format):
    #, Phone Number, Subscriber ID, Email, Name, Last Name, Label Name,
    Subscribe Status, Subscribed at, Updated at, Address Details, Name :
"""
import csv
import json
import os
import re
import sys
import uuid
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.getenv(
    "ANU_LOGIN_DATABASE_PATH",
    "/root/pureleven_dev/anu-login/backend/data/anu_login.sqlite3",
)

PURCHASE_LABEL_PATTERNS = re.compile(
    r"(?i)\b(purchase[ds]?|purchse|purchsae|puchase|prepaid_customer|"
    r"cinnamon_purchase|blackpepper_purchase|tamarind_purchase|website_purchase)\b"
)
LEAD_LABEL_PATTERNS = re.compile(
    r"(?i)\b(lead[s]?|interested|spices_english_lead|black_pepper_lead|"
    r"black pepper lead|black pepper interested|followup|wholesale_requested|"
    r"price_checked|address_checked|level\s*4|mill|1flour_mill|dealership|distribution)\b"
)


def classify_labels(label_names: str | None) -> tuple[bool, bool]:
    """Returns (is_purchase, is_lead)."""
    if not label_names:
        return False, False
    return (
        bool(PURCHASE_LABEL_PATTERNS.search(label_names)),
        bool(LEAD_LABEL_PATTERNS.search(label_names)),
    )


def normalise_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if not digits:
        return None
    return f"+{digits}"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_id() -> str:
    return str(uuid.uuid4())


def upsert_csv_row(conn: sqlite3.Connection, row: dict) -> str:
    phone = normalise_phone(row.get("Phone Number") or row.get("phone_number") or row.get("phone"))
    if not phone:
        return "skipped_no_phone"

    fn = (row.get("Name") or "").strip()
    ln = (row.get("Last Name") or "").strip()
    name = f"{fn} {ln}".strip() or phone
    email_raw = (row.get("Email") or "").strip()
    labels = (row.get("Label Name") or row.get("label_name") or "").strip()

    is_purchase, is_lead = classify_labels(labels)

    phone_digits = re.sub(r"\D", "", phone)
    email = email_raw if (email_raw and "@" in email_raw) else f"wa_{phone_digits}@whatsapp.local"

    tags_list = ["wabis_subscriber", "csv_import"]
    if is_purchase:
        tags_list.append("wabis_purchase")
    if is_lead:
        tags_list.append("wabis_lead")
    for lbl in labels.split(","):
        t = lbl.strip()
        if t:
            tags_list.append(t)
    tags_json = json.dumps(list(dict.fromkeys(tags_list)))

    existing = conn.execute(
        """SELECT id, email, purchase_status, total_orders, tags
           FROM customers
           WHERE deleted_at IS NULL AND (email = ? OR phone = ? OR whatsapp_number = ?)
           LIMIT 1""",
        (email, phone, phone),
    ).fetchone()

    ts = now_iso()

    if existing is None:
        cid = new_id()
        cuid = "CUS-" + uuid.uuid4().hex[:12].upper()
        purchase_status = "purchased" if is_purchase else "not_purchased"
        total_orders = 1 if is_purchase else 0
        conn.execute(
            """INSERT INTO customers
               (id, customer_uid, email, phone, whatsapp_number, name, first_name, last_name,
                tags, source, customer_status, purchase_status, total_orders,
                whatsapp_opted_in, preferred_channel, engagement_label,
                created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,'new',?,?,1,'whatsapp','cold',?,?)""",
            (cid, cuid, email, phone, phone, name, fn, ln,
             tags_json, "wabis_subscriber",
             purchase_status, total_orders, ts, ts),
        )
        return "created"
    else:
        eid = existing[0]
        try:
            existing_tags = json.loads(existing[4] or "[]")
        except Exception:
            existing_tags = []
        merged = list(dict.fromkeys(existing_tags + tags_list))
        new_purchase_status = existing[2]
        new_total_orders = existing[3] or 0
        if is_purchase and existing[2] != "purchased":
            new_purchase_status = "purchased"
            new_total_orders = max(new_total_orders, 1)
        conn.execute(
            """UPDATE customers
               SET whatsapp_number = COALESCE(NULLIF(whatsapp_number,''), ?),
                   phone = COALESCE(NULLIF(phone,''), ?),
                   name = COALESCE(NULLIF(name,''), ?),
                   tags = ?,
                   purchase_status = ?,
                   total_orders = ?,
                   whatsapp_opted_in = 1,
                   preferred_channel = COALESCE(NULLIF(preferred_channel,'auto'), preferred_channel, 'whatsapp'),
                   updated_at = ?
               WHERE id = ?""",
            (phone, phone, name, json.dumps(merged),
             new_purchase_status, new_total_orders, ts, eid),
        )
        return "updated"


def import_csv_file(conn: sqlite3.Connection, filepath: str) -> dict:
    print(f"\nReading: {filepath}")
    created = updated = skipped = total_rows = 0
    purchase_count = lead_count = 0

    with open(filepath, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            labels = row.get("Label Name") or ""
            is_p, is_l = classify_labels(labels)
            if is_p:
                purchase_count += 1
            if is_l:
                lead_count += 1

            result = upsert_csv_row(conn, row)
            if result == "created":
                created += 1
            elif result == "updated":
                updated += 1
            else:
                skipped += 1

            if total_rows % 1000 == 0:
                conn.commit()
                print(f"  ... {total_rows} rows processed (c={created} u={updated} s={skipped})")

    conn.commit()
    print(f"  Done: {total_rows} total | created={created} updated={updated} skipped={skipped}")
    print(f"  Label breakdown: purchase={purchase_count} lead={lead_count}")
    return {"total": total_rows, "created": created, "updated": updated, "skipped": skipped}


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 wabis_csv_import.py <file1.csv> [file2.csv ...]")
        sys.exit(1)

    files = sys.argv[1:]

    print(f"Connecting to SQLite at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    totals = {"total": 0, "created": 0, "updated": 0, "skipped": 0}
    for f in files:
        if not os.path.exists(f):
            print(f"WARNING: File not found: {f} — skipping")
            continue
        result = import_csv_file(conn, f)
        for k in totals:
            totals[k] += result[k]

    conn.close()

    print(f"\n{'='*50}")
    print("Wabis CSV Import Complete")
    print(f"{'='*50}")
    print(f"  Files processed : {len(files)}")
    print(f"  Total rows      : {totals['total']}")
    print(f"  Created (new)   : {totals['created']}")
    print(f"  Updated (merged): {totals['updated']}")
    print(f"  Skipped         : {totals['skipped']}")
    print(f"\nAll records → source='wabis_subscriber' (WhatsApp Leads bucket)")
    print(f"Purchase-labeled → purchase_status='purchased' (Purchased bucket)")


if __name__ == "__main__":
    main()
