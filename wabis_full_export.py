#!/usr/bin/env python3
"""
Wabis Full Chat Export — REST API version (no browser required)
Exports all subscriber conversations from bot.wabis.in using the Bearer token.

Endpoints used:
  POST /api/v1/whatsapp/subscriber/list  — paginate all subscribers
  POST /api/v1/whatsapp/get/conversation — get messages per subscriber

Output: customer_chats_v2/<name>_<phone>.csv

Pagination formula (empirically verified):
  offset × limit <= TOTAL_SUBS  →  response returns data
  offset × limit >  TOTAL_SUBS  →  response returns []
  Therefore: max_limit at offset O = floor(TOTAL_SUBS / O)
  Using adaptive limits cuts Phase 1 from 17,500 calls → ~3,000 calls.

Resume safety:
  Phase 1 saves _phones_cache.json — re-run skips Phase 1.
  Phase 2 skips already-written CSVs.
"""

import os
import csv
import json
import time
import subprocess
import re
from datetime import datetime

# ─── Config ────────────────────────────────────────────────────────────────────
TOKEN        = "18280|Ws5wnHgkReob1OKVhDHWH3kzEIIRjItGN9wPcQFz23380f95"
PHONE_ID     = "252036884661683"
BASE_URL     = "https://bot.wabis.in"
OUT_DIR      = "/Users/bthomas/Documents/pureleven_dev/customer_chats_v2"
PHONES_CACHE = os.path.join(OUT_DIR, "_phones_cache.json")
TOTAL_SUBS   = 17500   # empirically verified cap (limit×offset must be ≤ this)
MAX_LIMIT    = 100     # maximum per-page limit to use
MSG_LIMIT    = 1000    # messages to fetch per subscriber
SLEEP_BATCH  = 0.15    # seconds between subscriber-list pages (rate-limit safe)
SLEEP_MSG    = 0.20    # seconds between conversation fetches (rate-limit safe)

os.makedirs(OUT_DIR, exist_ok=True)

# ─── HTTP via curl (bypasses Cloudflare) ───────────────────────────────────────
def post_json(endpoint: str, payload: dict) -> dict:
    """POST JSON via curl, return parsed response."""
    body = json.dumps(payload)
    cmd = [
        "curl", "-s", "-X", "POST",
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", "Content-Type: application/json",
        "-d", body,
        f"{BASE_URL}{endpoint}"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return json.loads(result.stdout)
    except Exception as e:
        print(f"  [ERROR] {endpoint}: {e}")
        return {}

# ─── Message content parser ────────────────────────────────────────────────────
def parse_message_content(mc_str: str, sender: str) -> str:
    """Extract human-readable text from message_content JSON."""
    if not mc_str:
        return ""
    try:
        mc = json.loads(mc_str)
    except Exception:
        return mc_str[:200]

    if not isinstance(mc, dict):
        return str(mc)[:200]

    # ── User messages: full Meta webhook payload ──
    if sender == "user":
        try:
            msg = mc["entry"][0]["changes"][0]["value"]["messages"][0]
            mtype = msg.get("type", "")
            if mtype == "text":
                return msg.get("text", {}).get("body", "")
            elif mtype == "button":
                return f"[Button: {msg.get('button', {}).get('text', '')}]"
            elif mtype == "interactive":
                inter = msg.get("interactive", {})
                itype = inter.get("type", "")
                if itype == "button_reply":
                    return f"[Reply: {inter.get('button_reply',{}).get('title','')}]"
                elif itype == "list_reply":
                    return f"[List: {inter.get('list_reply',{}).get('title','')}]"
                else:
                    return f"[Interactive: {itype}]"
            elif mtype in ("document", "image", "video", "audio", "sticker"):
                media = msg.get(mtype, {})
                filename = media.get("filename", media.get("url", "")[:60])
                return f"[{mtype.capitalize()}: {filename}]"
            elif mtype == "location":
                loc = msg.get("location", {})
                return f"[Location: lat={loc.get('latitude')}, lon={loc.get('longitude')}]"
            elif mtype == "reaction":
                return f"[Reaction: {msg.get('reaction',{}).get('emoji','')}]"
            elif mtype == "order":
                return "[Order]"
            else:
                return f"[{mtype}]"
        except Exception:
            pass
        # Fallback: look for any text anywhere
        raw = json.dumps(mc)
        m = re.search(r'"body"\s*:\s*"([^"]{2,200})"', raw)
        if m:
            return m.group(1)
        return str(mc)[:200]

    # ── Bot/agent messages: template or plain text ──
    if "text" in mc and isinstance(mc["text"], str):
        return mc["text"]
    if "body" in mc and isinstance(mc["body"], str) and mc["body"].strip():
        return mc["body"]
    if "components" in mc and isinstance(mc["components"], list):
        parts = []
        for comp in mc["components"]:
            if isinstance(comp, dict):
                t = comp.get("text", "")
                if t and isinstance(t, str) and t.strip():
                    # Replace template variables
                    t = re.sub(r'\{\{[^}]+\}\}', '[VAR]', t)
                    t = re.sub(r'#[^#]+#', '[VAR]', t)
                    parts.append(t.strip())
        if parts:
            return " | ".join(parts)
    if "name" in mc:
        return f"[Template: {mc['name']}]"
    if "caption" in mc:
        return mc["caption"]

    return str(mc)[:200]


# ─── Fetch all subscribers ─────────────────────────────────────────────────────
def _adaptive_limit(offset: int) -> int:
    """
    Return the largest safe limit for this offset.
    Rule: offset × limit <= TOTAL_SUBS  (empirically verified)
    At offset=0 the rule gives ∞; cap at MAX_LIMIT.
    """
    if offset == 0:
        return MAX_LIMIT
    return max(1, min(MAX_LIMIT, TOTAL_SUBS // offset))


def fetch_all_subscribers() -> list[dict]:
    """
    Return list of all subscriber dicts.
    Uses adaptive limit to minimize API calls (~3,000 vs 17,500 with limit=1).
    Saves to cache so Phase 1 is skipped on resume.
    """
    print(f"\n{'='*60}")
    print("STEP 1: Fetching subscriber list (adaptive limit)...")
    print(f"{'='*60}")

    # Load cache if available
    if os.path.exists(PHONES_CACHE):
        with open(PHONES_CACHE, "r", encoding="utf-8") as f:
            cached = json.load(f)
        print(f"  → Loaded {len(cached):,} subscribers from cache: {PHONES_CACHE}")
        print(f"  → Delete cache to re-run Phase 1")
        return cached

    all_subs = []
    offset = 0
    api_calls = 0
    consecutive_empty = 0
    phase1_start = time.time()

    while offset <= TOTAL_SUBS:
        limit = _adaptive_limit(offset)
        payload = {
            "phone_number_id": PHONE_ID,
            "limit": limit,
            "offset": offset
        }
        resp = post_json("/api/v1/whatsapp/subscriber/list", payload)
        api_calls += 1
        items = resp.get("message", [])

        if not isinstance(items, list) or not items:
            consecutive_empty += 1
            if consecutive_empty >= 5:
                # Try falling back to limit=1 before giving up
                if limit > 1:
                    print(f"  [WARN] Empty at offset={offset} limit={limit} — retrying with limit=1")
                    consecutive_empty = 0
                    # Force limit=1 by temporarily saturating TOTAL_SUBS
                    resp2 = post_json("/api/v1/whatsapp/subscriber/list", {
                        "phone_number_id": PHONE_ID,
                        "limit": 1,
                        "offset": offset
                    })
                    api_calls += 1
                    items2 = resp2.get("message", [])
                    if isinstance(items2, list) and items2:
                        all_subs.extend(items2)
                        offset += 1
                        time.sleep(SLEEP_BATCH)
                        continue
                print(f"  5 consecutive empty responses at offset={offset}. Phase 1 done.")
                break
            offset += 1  # nudge forward on single empty
            time.sleep(SLEEP_BATCH * 2)
            continue

        consecutive_empty = 0
        all_subs.extend(items)

        if api_calls % 100 == 0 or api_calls <= 5:
            elapsed = time.time() - phase1_start
            rate = api_calls / elapsed if elapsed > 0 else 0
            eta_subs = TOTAL_SUBS - len(all_subs)
            eta_s = (eta_subs / (len(all_subs) / elapsed)) if elapsed > 0 and all_subs else 0
            print(
                f"  [{api_calls} calls] offset={offset} total={len(all_subs):,} "
                f"limit={limit} rate={rate:.1f}calls/s ETA≈{eta_s/60:.0f}min",
                flush=True
            )

        offset += len(items)
        time.sleep(SLEEP_BATCH)

    elapsed = time.time() - phase1_start
    print(f"\n  → Phase 1 done: {len(all_subs):,} subscribers in {api_calls} API calls ({elapsed/60:.1f} min)")

    # Save cache
    with open(PHONES_CACHE, "w", encoding="utf-8") as f:
        json.dump(all_subs, f)
    print(f"  → Cache saved: {PHONES_CACHE}")

    return all_subs


# ─── Fetch messages for one subscriber ────────────────────────────────────────
def fetch_messages(phone: str) -> list[dict]:
    """Return list of parsed messages for a subscriber phone number."""
    payload = {
        "phone_number_id": PHONE_ID,
        "phone_number": phone,
        "limit": MSG_LIMIT
    }
    resp = post_json("/api/v1/whatsapp/get/conversation", payload)
    msg_data = resp.get("message", "")

    try:
        if isinstance(msg_data, str) and msg_data.startswith("{"):
            raw_msgs = json.loads(msg_data)
        else:
            return []
    except Exception:
        return []

    if not isinstance(raw_msgs, dict) or not raw_msgs:
        return []

    messages = []
    for k in sorted(raw_msgs.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        m = raw_msgs[k]
        text = parse_message_content(m.get("message_content", ""), m.get("sender", ""))
        messages.append({
            "timestamp": m.get("conversation_time", ""),
            "sender": m.get("sender", ""),
            "type": "text",
            "message": text,
            "message_id": m.get("id", ""),
            "status": m.get("message_status", "")
        })
    return messages


# ─── Write CSV ────────────────────────────────────────────────────────────────
def safe_filename(name: str, phone: str) -> str:
    name_clean = re.sub(r'[^a-zA-Z0-9_]', '_', name)[:30].strip('_') or "Customer"
    return f"{name_clean}_{phone}.csv"


def write_csv(filename: str, messages: list[dict]):
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "sender", "type", "message", "message_id", "status"])
        writer.writeheader()
        writer.writerows(messages)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    start_time = datetime.now()
    print(f"\nWabis Full Chat Export — {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Output dir: {OUT_DIR}")

    # Step 1: Get all subscribers
    subscribers = fetch_all_subscribers()
    total_subs = len(subscribers)
    print(f"\n→ {total_subs} total subscribers found")

    # Step 2: For each subscriber, fetch and export messages
    print(f"\n{'='*60}")
    print("STEP 2: Fetching conversations...")
    print(f"{'='*60}")

    summary_rows = []
    exported = 0
    skipped_empty = 0
    skipped_existing = 0
    phase2_start = time.time()

    for i, sub in enumerate(subscribers):
        phone     = sub.get("chat_id", "")
        first     = sub.get("first_name", "")
        last      = sub.get("last_name", "")
        sub_id    = sub.get("subscriber_id", "")
        labels    = sub.get("label_names", "")
        name      = f"{first} {last}".strip() or phone

        if not phone:
            continue

        filename = safe_filename(name, phone)
        path = os.path.join(OUT_DIR, filename)

        # Resume: skip already-exported files
        if os.path.exists(path):
            skipped_existing += 1
            try:
                with open(path, newline="", encoding="utf-8") as f:
                    msg_count = sum(1 for _ in f) - 1
                summary_rows.append({
                    "subscriber_id": sub_id, "customer": name, "phone": phone,
                    "messages": msg_count, "labels": labels or "", "file": filename
                })
                exported += 1
            except Exception:
                pass
            continue

        messages = fetch_messages(phone)

        progress = f"[{i+1}/{total_subs}]"
        if messages:
            write_csv(filename, messages)
            exported += 1
            summary_rows.append({
                "subscriber_id": sub_id,
                "customer": name,
                "phone": phone,
                "messages": len(messages),
                "labels": labels or "",
                "file": filename
            })
            print(f"  {progress} {name} ({phone}): {len(messages)} msgs → {filename}", flush=True)
        else:
            skipped_empty += 1

        # Progress every 500
        if (i + 1) % 500 == 0:
            elapsed = time.time() - phase2_start
            done = i + 1
            rate = done / elapsed if elapsed > 0 else 0
            remaining = total_subs - done
            eta_s = remaining / rate if rate > 0 else 0
            print(
                f"  ── [{i+1}/{total_subs}] exported={exported:,} empty={skipped_empty:,} "
                f"existing={skipped_existing:,} rate={rate:.1f}/s ETA≈{eta_s/60:.0f}min",
                flush=True
            )

        time.sleep(SLEEP_MSG)

    # Step 3: Write summary
    summary_path = os.path.join(OUT_DIR, "EXPORT_SUMMARY.csv")
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["subscriber_id", "customer", "phone", "messages", "labels", "file"])
        writer.writeheader()
        writer.writerows(sorted(summary_rows, key=lambda r: -int(r["messages"])))

    elapsed = (datetime.now() - start_time).total_seconds()
    total_msgs = sum(int(r["messages"]) for r in summary_rows)

    print(f"\n{'='*60}")
    print("EXPORT COMPLETE")
    print(f"{'='*60}")
    print(f"  Total subscribers:     {total_subs:,}")
    print(f"  Exported (with msgs):  {exported:,}")
    print(f"  Skipped (empty):       {skipped_empty:,}")
    print(f"  Skipped (existing):    {skipped_existing:,}")
    print(f"  Total messages:        {total_msgs:,}")
    print(f"  Output directory:      {OUT_DIR}")
    print(f"  Summary CSV:           {summary_path}")
    print(f"  Time elapsed:          {elapsed:.0f}s ({elapsed/60:.1f} min)")


if __name__ == "__main__":
    main()
