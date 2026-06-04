#!/usr/bin/env python3
"""
Wabis Subscriber Sync Script
Fetches all subscribers from Wabis API and imports them into the WhatsApp CRM SQLite.
Run on VPS: python3 /tmp/wabis_sync.py
"""
import os, re, json, uuid, sqlite3, urllib.request, urllib.parse
from datetime import datetime, timezone

# ── Config ──────────────────────────────────────────────────────────────────
WABIS_TOKEN    = "18280|Ws5wnHgkReob1OKVhDHWH3kzEIIRjItGN9wPcQFz23380f95"
PHONE_NUM_ID   = "252036884661683"
WABIS_API_BASE = "https://bot.wabis.in/api/v1/whatsapp"

# Default SQLite location; override via env ANU_LOGIN_DATABASE_PATH
DB_PATH = os.getenv(
    "ANU_LOGIN_DATABASE_PATH",
    "/root/pureleven_dev/anu-login/backend/data/anu_login.sqlite3",
)

# ── Label classification ─────────────────────────────────────────────────────
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
    """Returns (is_purchase, is_lead) based on label string."""
    if not label_names:
        return False, False
    is_purchase = bool(PURCHASE_LABEL_PATTERNS.search(label_names))
    is_lead     = bool(LEAD_LABEL_PATTERNS.search(label_names))
    return is_purchase, is_lead

# ── Wabis API fetch ──────────────────────────────────────────────────────────
def fetch_wabis_page(limit: int, page: int) -> list[dict]:
    url = (
        f"{WABIS_API_BASE}/subscriber/list"
        f"?apiToken={urllib.parse.quote(WABIS_TOKEN)}"
        f"&phone_number_id={PHONE_NUM_ID}"
        f"&limit={limit}&page={page}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "PureLeven-Sync/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    return data.get("message") or []

def fetch_all_subscribers() -> list[dict]:
    print("Fetching Wabis subscribers...")
    all_subs: dict[int, dict] = {}
    page = 1
    while True:
        rows = fetch_wabis_page(500, page)
        if not rows:
            break
        new_count = 0
        for r in rows:
            sid = r.get("subscriber_id")
            if sid and sid not in all_subs:
                all_subs[sid] = r
                new_count += 1
        print(f"  Page {page}: {len(rows)} rows, {new_count} new (total unique: {len(all_subs)})")
        if len(rows) < 500:
            break
        if new_count == 0:
            print("  No new records on this page — stopping pagination.")
            break
        page += 1
    return list(all_subs.values())

# ── SQLite helpers ────────────────────────────────────────────────────────────
def normalise_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if not digits:
        return None
    if not digits.startswith("+"):
        digits = f"+{digits}"
    return digits

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def new_id() -> str:
    return str(uuid.uuid4())

def upsert_wabis_subscriber(conn: sqlite3.Connection, sub: dict) -> str:
    chat_id = sub.get("chat_id", "")
    phone   = normalise_phone(chat_id)
    if not phone:
        return "skipped_no_phone"

    fn    = (sub.get("first_name") or "").strip()
    ln    = (sub.get("last_name") or "").strip()
    name  = f"{fn} {ln}".strip() or phone
    labels = sub.get("label_names") or ""
    is_purchase, is_lead = classify_labels(labels)

    source = "wabis_subscriber"  # contains "wabis" → auto-classified as WhatsApp lead
    phone_digits = re.sub(r"\D", "", phone)
    email = f"wa_{phone_digits}@whatsapp.local"

    tags_list = ["wabis_subscriber"]
    if is_purchase:
        tags_list.append("wabis_purchase")
    if is_lead:
        tags_list.append("wabis_lead")
    if labels:
        for lbl in labels.split(","):
            t = lbl.strip()
            if t:
                tags_list.append(t)
    tags_json = json.dumps(list(dict.fromkeys(tags_list)))  # deduplicated, ordered

    # Check existing by phone or email
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
             tags_json, source,
             purchase_status, total_orders,
             ts, ts),
        )
        return "created"
    else:
        eid = existing[0]
        # Merge tags
        existing_tags = json.loads(existing[4] or "[]")
        merged = list(dict.fromkeys(existing_tags + tags_list))
        # Update purchase_status if we now know they purchased
        new_purchase_status = existing[2]
        new_total_orders    = existing[3] or 0
        if is_purchase and existing[2] != "purchased":
            new_purchase_status = "purchased"
            new_total_orders    = max(new_total_orders, 1)
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

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    subscribers = fetch_all_subscribers()
    print(f"\nTotal unique subscribers fetched: {len(subscribers)}")

    if not subscribers:
        print("No subscribers to import.")
        return

    print(f"\nConnecting to SQLite at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    created = updated = skipped = 0
    purchase_count = lead_count = no_label_count = 0

    for sub in subscribers:
        labels = sub.get("label_names") or ""
        is_p, is_l = classify_labels(labels)
        if is_p: purchase_count += 1
        if is_l: lead_count += 1
        if not labels: no_label_count += 1

        result = upsert_wabis_subscriber(conn, sub)
        if result == "created":   created += 1
        elif result == "updated": updated += 1
        else:                     skipped += 1

    conn.commit()
    conn.close()

    print(f"\n{'='*50}")
    print(f"Wabis Subscriber Sync Complete")
    print(f"{'='*50}")
    print(f"  Total fetched   : {len(subscribers)}")
    print(f"  Created (new)   : {created}")
    print(f"  Updated (merged): {updated}")
    print(f"  Skipped         : {skipped}")
    print(f"\nLabel breakdown:")
    print(f"  With purchase label : {purchase_count}")
    print(f"  With lead label     : {lead_count}")
    print(f"  No label (broadcast): {no_label_count}")
    print(f"\nAll source='wabis_subscriber' → classified as WhatsApp Leads in CRM")
    print(f"Purchase-labeled subscribers → purchase_status='purchased' (Purchased bucket)")

if __name__ == "__main__":
    main()
