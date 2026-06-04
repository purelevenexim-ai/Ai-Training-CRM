#!/usr/bin/env python3
"""
Wabis Full Chat Export — Threaded Production Version
=====================================================
Phase 1: 4 threads collect all ~17,500 subscriber phones using adaptive limits
Phase 2: 4 worker threads fetch conversations (pipeline — starts while Phase 1 runs)

API pagination rule (empirically verified):
    offset × limit ≤ TOTAL_SUBS  →  API returns results
    offset × limit >  TOTAL_SUBS  →  API returns []
    ∴ max_limit(offset) = floor(TOTAL_SUBS / offset)

Rate limiting:
    4 Phase-1 threads × 0.25s sleep = ~16 req/s peak (safe)
    4 Phase-2 workers × 0.30s sleep = ~13 req/s peak (safe)

Output: customer_chats_v2/<Name>_<phone>.csv
        customer_chats_v2/_phones_cache.json   (Phase 1 cache — delete to re-run)
        customer_chats_v2/EXPORT_SUMMARY.csv
"""

import os
import csv
import json
import time
import subprocess
import re
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed, wait
from datetime import datetime

# ─── Config ─────────────────────────────────────────────────────────────────────
TOKEN          = "18280|Ws5wnHgkReob1OKVhDHWH3kzEIIRjItGN9wPcQFz23380f95"
PHONE_ID       = "252036884661683"
BASE_URL       = "https://bot.wabis.in"
OUT_DIR        = "/Users/bthomas/Documents/pureleven_dev/customer_chats_v2"
PHONES_CACHE   = os.path.join(OUT_DIR, "_phones_cache.json")

TOTAL_SUBS     = 17500   # empirically verified: offset×limit must be ≤ this
MAX_LIMIT      = 100     # max per-page for subscriber list
MSG_LIMIT      = 1000    # messages per conversation fetch

P1_THREADS     = 4       # Phase 1 parallel subscriber-list threads
P2_WORKERS     = 4       # Phase 2 parallel conversation-fetch workers

SLEEP_P1       = 0.25    # per-thread sleep between subscriber-list calls
SLEEP_P2       = 0.30    # per-worker sleep between conversation calls
CURL_TIMEOUT   = 30      # curl timeout per request

os.makedirs(OUT_DIR, exist_ok=True)

# ─── Shared state ────────────────────────────────────────────────────────────────
_write_lock    = threading.Lock()   # for CSV writes + summary list
_print_lock    = threading.Lock()   # for console output
_counter_lock  = threading.Lock()   # for all counters
_summary_rows  = []

# Thread-safe counters (plain ints behind a lock)
_counters = {'p1': 0, 'p2_exported': 0, 'p2_empty': 0, 'p2_existing': 0}

def _inc(key: str, n: int = 1) -> int:
    """Increment counter and return new value."""
    with _counter_lock:
        _counters[key] += n
        return _counters[key]

def _get(key: str) -> int:
    with _counter_lock:
        return _counters[key]

def tprint(*args, **kwargs):
    with _print_lock:
        print(*args, **kwargs)


# ─── HTTP via curl (Cloudflare bypass) ──────────────────────────────────────────
def post_json(endpoint: str, payload: dict, retries: int = 2) -> dict:
    body = json.dumps(payload)
    cmd = [
        "curl", "-s", "-X", "POST",
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", "Content-Type: application/json",
        "-d", body,
        f"{BASE_URL}{endpoint}"
    ]
    for attempt in range(retries + 1):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=CURL_TIMEOUT)
            if result.stdout.strip():
                return json.loads(result.stdout)
        except json.JSONDecodeError:
            pass
        except Exception:
            pass
        if attempt < retries:
            time.sleep(1.0)  # wait before retry
    return {}


# ─── Message content parser ──────────────────────────────────────────────────────
def parse_message_content(mc_str: str, sender: str) -> str:
    if not mc_str:
        return ""
    try:
        mc = json.loads(mc_str)
    except Exception:
        return mc_str[:200]

    if not isinstance(mc, dict):
        return str(mc)[:200]

    # User messages: full Meta WhatsApp webhook payload
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
                    return f"[Reply: {inter.get('button_reply', {}).get('title', '')}]"
                elif itype == "list_reply":
                    return f"[List: {inter.get('list_reply', {}).get('title', '')}]"
                else:
                    return f"[Interactive: {itype}]"
            elif mtype in ("document", "image", "video", "audio", "sticker"):
                media = msg.get(mtype, {})
                fname = media.get("filename", media.get("url", "")[:60])
                return f"[{mtype.capitalize()}: {fname}]"
            elif mtype == "location":
                loc = msg.get("location", {})
                return f"[Location: lat={loc.get('latitude')}, lon={loc.get('longitude')}]"
            elif mtype == "reaction":
                return f"[Reaction: {msg.get('reaction', {}).get('emoji', '')}]"
            elif mtype == "order":
                return "[Order]"
            else:
                return f"[{mtype}]"
        except Exception:
            pass
        raw = json.dumps(mc)
        m = re.search(r'"body"\s*:\s*"([^"]{2,200})"', raw)
        if m:
            return m.group(1)
        return str(mc)[:200]

    # Bot/agent messages: template JSON
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


# ─── Phase 1: subscriber list worker (shared sequential pages) ──────────────────
def _p1_page_worker(
    page_counter: list,
    page_lock: threading.Lock,
    result_list: list,
    r_lock: threading.Lock,
    work_queue: queue.Queue,
):
    """
    Each thread grabs the next sequential page atomically from page_counter.
    Uses limit=MAX_LIMIT (100) always — total valid pages = ceil(17500/100) = 175.
    Stops when page_counter reaches MAX_PAGE (cap). Transient empty pages are
    silently skipped (no stop_event) so a single network hiccup won't abort all threads.
    """
    MAX_PAGE = (TOTAL_SUBS + MAX_LIMIT - 1) // MAX_LIMIT + 10  # 185 (safe cap)

    while True:
        with page_lock:
            page = page_counter[0]
            if page >= MAX_PAGE:
                break
            page_counter[0] += 1

        resp = post_json("/api/v1/whatsapp/subscriber/list", {
            "phone_number_id": PHONE_ID,
            "limit": MAX_LIMIT,
            "offset": page
        })
        items = resp.get("message", [])

        if not isinstance(items, list) or not items:
            # Empty page: could be end of data or transient error — skip
            time.sleep(SLEEP_P1)
            continue

        with r_lock:
            result_list.extend(items)
        for item in items:
            work_queue.put(item)   # feed Phase 2 pipeline immediately

        _inc('p1', len(items))
        time.sleep(SLEEP_P1)


# ─── Phase 2: conversation fetch worker ──────────────────────────────────────────
def safe_filename(name: str, phone: str) -> str:
    name_clean = re.sub(r'[^a-zA-Z0-9_]', '_', name)[:30].strip('_') or "Customer"
    return f"{name_clean}_{phone}.csv"


def fetch_messages(phone: str) -> list[dict]:
    resp = post_json("/api/v1/whatsapp/get/conversation", {
        "phone_number_id": PHONE_ID,
        "phone_number": phone,
        "limit": MSG_LIMIT
    })
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


def _p2_worker(work_queue: queue.Queue, poison: object, p2_start: float):
    """Consume subscriber dicts from queue, fetch conversations, write CSVs."""
    while True:
        try:
            sub = work_queue.get(timeout=5)
        except queue.Empty:
            continue

        if sub is poison:
            work_queue.put(poison)  # re-insert so other workers see it
            break

        phone  = sub.get("chat_id", "")
        first  = sub.get("first_name", "")
        last   = sub.get("last_name", "")
        sub_id = sub.get("subscriber_id", "")
        labels = sub.get("label_names", "")
        name   = f"{first} {last}".strip() or phone

        if not phone:
            work_queue.task_done()
            continue

        filename = safe_filename(name, phone)
        path = os.path.join(OUT_DIR, filename)

        # Resume: skip existing
        if os.path.exists(path):
            _inc('p2_existing')
            try:
                with open(path, newline="", encoding="utf-8") as f:
                    msg_count = sum(1 for _ in f) - 1
                with _write_lock:
                    _summary_rows.append({
                        "subscriber_id": sub_id, "customer": name, "phone": phone,
                        "messages": msg_count, "labels": labels or "", "file": filename
                    })
                _inc('p2_exported')
            except Exception:
                pass
            work_queue.task_done()
            continue

        messages = fetch_messages(phone)

        if messages:
            # Write CSV (thread-safe via per-file path — each file is unique)
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["timestamp", "sender", "type", "message", "message_id", "status"])
                writer.writeheader()
                writer.writerows(messages)

            with _write_lock:
                _summary_rows.append({
                    "subscriber_id": sub_id, "customer": name, "phone": phone,
                    "messages": len(messages), "labels": labels or "", "file": filename
                })
            _inc('p2_exported')
            tprint(f"  ✓ {name} ({phone}): {len(messages)} msgs", flush=True)
        else:
            _inc('p2_empty')

        # Periodic progress report every 500 processed
        total_done = _get('p2_exported') + _get('p2_empty') + _get('p2_existing')
        if total_done % 500 == 0 and total_done > 0:
            elapsed = time.time() - p2_start
            rate = total_done / elapsed if elapsed > 0 else 0
            remaining = _get('p1') - total_done
            eta = remaining / rate if rate > 0 else 0
            tprint(
                f"  ── P2 progress: {total_done:,} processed | "
                f"exported={_get('p2_exported'):,} empty={_get('p2_empty'):,} "
                f"rate={rate:.1f}/s ETA≈{eta/60:.0f}min",
                flush=True
            )

        work_queue.task_done()
        time.sleep(SLEEP_P2)


# ─── Main ────────────────────────────────────────────────────────────────────────
def main():
    start_time = datetime.now()
    tprint(f"\nWabis Threaded Export — {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    tprint(f"Phase 1: {P1_THREADS} threads | Phase 2: {P2_WORKERS} workers")
    tprint(f"Output: {OUT_DIR}")
    tprint(f"Cache:  {PHONES_CACHE}")

    work_queue = queue.Queue()  # unbounded — P1 must finish before P2 starts
    POISON = object()
    p1_lock = threading.Lock()
    all_subs: list[dict] = []

    # ── Phase 1 ──────────────────────────────────────────────────────────────────
    tprint(f"\n{'='*60}")
    tprint(f"PHASE 1: Collecting subscriber phone numbers ({P1_THREADS} threads)")
    tprint(f"{'='*60}")

    cache_loaded = False
    if os.path.exists(PHONES_CACHE):
        try:
            with open(PHONES_CACHE, "r", encoding="utf-8") as f:
                all_subs = json.load(f)
            tprint(f"  → Cache loaded: {len(all_subs):,} subscribers")
            for sub in all_subs:
                work_queue.put(sub)
            _inc('p1', len(all_subs))
            cache_loaded = True
        except Exception as e:
            tprint(f"  [WARN] Cache load failed ({e}), re-collecting...")

    if not cache_loaded:
        p1_start = time.time()
        # Shared page counter — all threads pull sequential pages with limit=MAX_LIMIT
        # Total pages = ceil(TOTAL_SUBS / MAX_LIMIT) = ceil(17500/100) = 175
        page_counter = [0]
        page_lock2   = threading.Lock()

        total_pages = (TOTAL_SUBS + MAX_LIMIT - 1) // MAX_LIMIT
        tprint(f"  Strategy: {P1_THREADS} threads sharing {total_pages} pages (limit={MAX_LIMIT} each)")

        with ThreadPoolExecutor(max_workers=P1_THREADS) as executor:
            futures = [
                executor.submit(_p1_page_worker, page_counter, page_lock2, all_subs, p1_lock, work_queue)
                for _ in range(P1_THREADS)
            ]
            # Print progress while P1 threads run
            last_count = 0
            while not all(f.done() for f in futures):
                time.sleep(10)
                cnt = _get('p1')
                if cnt != last_count:
                    elapsed = time.time() - p1_start
                    rate = cnt / elapsed if elapsed > 0 else 0
                    eta = (TOTAL_SUBS - cnt) / rate if rate > 0 else 0
                    tprint(
                        f"  P1: {cnt:,}/{TOTAL_SUBS:,} subscribers collected "
                        f"({rate:.0f}/s, ETA≈{eta/60:.0f}min)",
                        flush=True
                    )
                    last_count = cnt
            # Re-raise any exceptions
            for f in futures:
                f.result()

        p1_elapsed = time.time() - p1_start
        tprint(f"\n  → Phase 1 done: {len(all_subs):,} subscribers in {p1_elapsed/60:.1f} min")

        # Save cache (deduplicate by chat_id)
        seen = {}
        for sub in all_subs:
            cid = sub.get("chat_id", "")
            if cid:
                seen[cid] = sub
        all_subs = list(seen.values())
        tprint(f"  → After dedup: {len(all_subs):,} unique subscribers")
        with open(PHONES_CACHE, "w", encoding="utf-8") as f:
            json.dump(all_subs, f)
        tprint(f"  → Cache saved: {PHONES_CACHE}")

    # ── Phase 2 ──────────────────────────────────────────────────────────────────
    tprint(f"\n{'='*60}")
    tprint(f"PHASE 2: Fetching conversations ({P2_WORKERS} workers)")
    tprint(f"{'='*60}")

    p2_start = time.time()
    work_queue.put(POISON)  # signal end of data

    with ThreadPoolExecutor(max_workers=P2_WORKERS) as executor:
        p2_futures = [
            executor.submit(_p2_worker, work_queue, POISON, p2_start)
            for _ in range(P2_WORKERS)
        ]
        for f in as_completed(p2_futures):
            try:
                f.result()
            except Exception as e:
                tprint(f"  [P2 WORKER ERROR] {e}")

    p2_elapsed = time.time() - p2_start

    # ── Summary ───────────────────────────────────────────────────────────────────
    summary_path = os.path.join(OUT_DIR, "EXPORT_SUMMARY.csv")
    with _write_lock:
        rows = sorted(_summary_rows, key=lambda r: -int(r.get("messages", 0) or 0))
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["subscriber_id", "customer", "phone", "messages", "labels", "file"])
        writer.writeheader()
        writer.writerows(rows)

    total_msgs = sum(int(r.get("messages", 0) or 0) for r in rows)
    elapsed = (datetime.now() - start_time).total_seconds()

    tprint(f"\n{'='*60}")
    tprint("EXPORT COMPLETE")
    tprint(f"{'='*60}")
    tprint(f"  Total subscribers:        {len(all_subs):,}")
    tprint(f"  Exported (with msgs):     {_get('p2_exported'):,}")
    tprint(f"  Skipped (empty/no msgs):  {_get('p2_empty'):,}")
    tprint(f"  Skipped (already exist):  {_get('p2_existing'):,}")
    tprint(f"  Total messages:           {total_msgs:,}")
    tprint(f"  Phase 2 time:             {p2_elapsed/60:.1f} min")
    tprint(f"  Total elapsed:            {elapsed/60:.1f} min")
    tprint(f"  Summary:                  {summary_path}")


if __name__ == "__main__":
    main()
