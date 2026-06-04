#!/usr/bin/env python3
"""
Wabis Chat Exporter - Using Real Browser-Discovered Endpoints
Exports all ~725 conversations as per-customer CSV files.

Real endpoints discovered via browser inspection:
  - GET  /all/livechat/conversation/list   (paginated, 50/page, POST with form data)
  - POST /whatsapp/livechat/conversation/single  (messages for one conversation)

Auth: Browser session cookies (XSRF-TOKEN + PHPSESSID)
"""

import requests
import csv
import os
import re
import json
import time
from datetime import datetime

# ─── CONFIG ──────────────────────────────────────────────────────────────────
BASE_URL    = "https://bot.wabis.in"
XSRF_TOKEN  = "FUc5cWYVEvXFRKtHPXM1CmjYTH1N3RTlg96zQgzO"
PHPSESSID   = "gvd75cnu5spujqfkh0th38rpca"
OMNI_BOT_ID = "43011"
TEAM_MEMBERS = '{"71206":"Admin","168004":"Sunitha"}'
OUTPUT_DIR  = "customer_chats"
PAGE_SIZE   = 50
DELAY       = 0.4   # seconds between requests (be polite)

# ─── SESSION SETUP ───────────────────────────────────────────────────────────
session = requests.Session()
session.cookies.set("XSRF-TOKEN", XSRF_TOKEN, domain="bot.wabis.in")
session.cookies.set("PHPSESSID",  PHPSESSID,  domain="bot.wabis.in")
session.headers.update({
    "X-XSRF-TOKEN":     XSRF_TOKEN,
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent":       "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer":          f"{BASE_URL}/all/livechat",
})

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ─── HTML PARSING HELPERS ────────────────────────────────────────────────────

def extract_attr(html: str, attr: str) -> str:
    m = re.search(rf'{attr}="([^"]*)"', html)
    return m.group(1) if m else ""


def parse_conversations_from_html(html: str) -> list[dict]:
    """Extract conversation metadata from the HTML list fragment."""
    convs = []
    # Each conversation is in an <li> with class open_conversation
    li_blocks = re.findall(r'<li[^>]+class="[^"]*open_conversation[^"]*"[^>]+>(.*?)</li>', html, re.DOTALL)
    
    # Fallback: parse directly from <li> attributes
    for m in re.finditer(r'<li[^>]*open_conversation[^>]*>', html):
        li_tag = m.group(0)
        conv = {
            "thread_id":    extract_attr(li_tag, "thread_id"),
            "from_user":    extract_attr(li_tag, "from_user"),
            "from_user_id": extract_attr(li_tag, "from_user_id"),
            "omni_bot_id":  extract_attr(li_tag, "omni_bot_id"),
            "omni_bot_name":extract_attr(li_tag, "omni_bot_name"),
            "data_id":      extract_attr(li_tag, "data_id"),
            "social_media": extract_attr(li_tag, "social_media"),
        }
        if conv["thread_id"]:
            convs.append(conv)
    return convs


def parse_messages_from_html(html: str) -> list[dict]:
    """Extract messages from the conversation/single HTML response."""
    messages = []
    
    # Each message is in a div with class "chat-item chat-left" or "chat-item chat-right"
    # chat-left = customer message, chat-right = bot/agent message
    chat_items = re.findall(
        r'<div[^>]+class="[^"]*chat-item[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>',
        html, re.DOTALL
    )
    
    # Simpler approach: parse message blocks
    # The response HTML has chat-item divs with message attributes
    for m in re.finditer(r'<div[^>]+class="([^"]*chat-item[^"]*)"[^>]*>', html):
        direction = "customer" if "chat-left" in m.group(1) else "bot/agent"
        pos = m.end()
        
        # Find the chat-details div for message attributes
        details_match = re.search(r'<div[^>]+class="[^"]*chat-details[^"]*"[^>]*>', html[pos:pos+200])
        msg_type = "text"
        msg_id = ""
        if details_match:
            details_tag = details_match.group(0)
            msg_type = extract_attr(details_tag, "message_type")
            msg_id   = extract_attr(details_tag, "message_id")
        
        # Extract text content from chat-text div
        text_match = re.search(r'<div[^>]+class="[^"]*chat-text[^"]*"[^>]*>(.*?)</div>', html[pos:pos+2000], re.DOTALL)
        text_content = ""
        if text_match:
            raw = text_match.group(1)
            # Strip HTML tags
            text_content = re.sub(r'<[^>]+>', ' ', raw).strip()
            text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        # Extract timestamp
        time_match = re.search(r'class="[^"]*put-time[^"]*"[^>]*>([^<]+)<', html[pos:pos+500])
        timestamp = time_match.group(1).strip() if time_match else ""
        
        if msg_id or text_content:
            messages.append({
                "message_id": msg_id,
                "sender":     direction,
                "type":       msg_type or "text",
                "text":       text_content,
                "timestamp":  timestamp,
            })
    
    return messages


def parse_messages_simple(html: str) -> list[dict]:
    """
    Simpler message extraction: parse all chat-item divs with a regex.
    Returns list of {sender, type, text, timestamp, message_id}.
    """
    messages = []
    
    # Find all chat-item start positions
    for item_m in re.finditer(r'<div\s+class="(chat-item\s+chat-(?:left|right))[^"]*"', html):
        direction = "customer" if "chat-left" in item_m.group(1) else "bot_agent"
        start = item_m.start()
        snippet = html[start: start + 3000]
        
        # Extract message_type and message_id from nested chat-details
        msg_type = extract_attr(snippet, "message_type") or "text"
        msg_id   = extract_attr(snippet, "message_id")
        
        # Extract timestamp from small tag
        ts_m = re.search(r'class="put-time[^"]*"[^>]*>\s*([^<]+)\s*<', snippet)
        timestamp = ts_m.group(1).strip() if ts_m else ""
        
        # Extract the chat-text content (strip all tags)
        ct_m = re.search(r'class="chat-text[^"]*"[^>]*>(.*?)(?=<div class="(?:chat-item|chat-footer|row))', snippet, re.DOTALL)
        text = ""
        if ct_m:
            raw = ct_m.group(1)
            text = re.sub(r'<[^>]+>', ' ', raw)
            text = re.sub(r'\s+', ' ', text).strip()
        
        # Also grab button text (interactive messages)
        btn_texts = re.findall(r'<a[^>]*class="[^"]*btn[^"]*"[^>]*>([^<]+)<', snippet)
        if btn_texts and not text:
            text = " | ".join(t.strip() for t in btn_texts)
        
        messages.append({
            "message_id": msg_id,
            "sender":     direction,
            "type":       msg_type,
            "text":       text,
            "timestamp":  timestamp,
        })
    
    return messages


# ─── API CALLS ───────────────────────────────────────────────────────────────

def fetch_conversation_list(start: int = 0) -> str:
    """Fetch conversation list HTML fragment."""
    data = {
        "whatsapp_bot_id":  "all",
        "telegram_bot_id":  "all",
        "message_type":     "all",
        "start":            str(start),
        "order_by_id":      "last_interacted_at",
        "channel_list[]":   "all",
        "start_filter_date": "",
        "end_filter_date":  "",
        "team_member_list": TEAM_MEMBERS,
    }
    resp = session.post(f"{BASE_URL}/all/livechat/conversation/list", data=data, timeout=30)
    resp.raise_for_status()
    return resp.text


def fetch_conversation_messages(conv: dict) -> str:
    """Fetch HTML messages for a single conversation."""
    data = {
        "thread_id":        conv["thread_id"],
        "whatsapp_bot_id":  conv["omni_bot_id"],
        "telegram_bot_id":  conv["omni_bot_id"],
        "from_user_id":     conv["from_user_id"],
        "last_message_id":  "",
        "media_type":       "fb",
        "data_key":         "",
        "has_unseen":       "true",
        "team_member_list": TEAM_MEMBERS,
    }
    resp = session.post(f"{BASE_URL}/whatsapp/livechat/conversation/single", data=data, timeout=30)
    resp.raise_for_status()
    try:
        j = resp.json()
        return j.get("str", "")
    except Exception:
        return resp.text


# ─── MAIN EXPORT ─────────────────────────────────────────────────────────────

def safe_filename(name: str, phone: str) -> str:
    """Create a safe filename from customer name and phone."""
    clean = re.sub(r'[^\w\s\-]', '', name).strip()
    clean = re.sub(r'\s+', '_', clean)[:40]
    return f"{clean}_{phone}.csv"


def write_customer_csv(filepath: str, conv: dict, messages: list[dict]) -> None:
    """Write messages for one customer to a CSV file."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        f.write(f"# Customer: {conv['from_user']}\n")
        f.write(f"# Phone: {conv['thread_id']}\n")
        f.write(f"# Bot: {conv['omni_bot_name']}\n")
        f.write(f"# Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        
        writer = csv.DictWriter(f, fieldnames=["timestamp", "sender", "type", "message", "message_id"])
        writer.writeheader()
        for msg in messages:
            writer.writerow({
                "timestamp":  msg.get("timestamp", ""),
                "sender":     msg.get("sender", ""),
                "type":       msg.get("type", "text"),
                "message":    msg.get("text", ""),
                "message_id": msg.get("message_id", ""),
            })


def main():
    print("=" * 60)
    print("  Wabis Chat Exporter — Per-Customer CSV")
    print(f"  Output: {OUTPUT_DIR}/")
    print("=" * 60)
    
    # ── Step 1: Collect all conversations ──
    print("\n[1/2] Fetching conversation list...")
    all_convs = []
    start = 0
    while True:
        try:
            html = fetch_conversation_list(start)
            convs = parse_conversations_from_html(html)
            if not convs:
                break
            all_convs.extend(convs)
            print(f"  Page {start//PAGE_SIZE + 1}: {len(convs)} conversations (total: {len(all_convs)})")
            if len(convs) < PAGE_SIZE:
                break
            start += PAGE_SIZE
            time.sleep(DELAY)
        except Exception as e:
            print(f"  ERROR at start={start}: {e}")
            break
    
    print(f"\n  Found {len(all_convs)} total conversations")
    
    if not all_convs:
        print("\nERROR: No conversations found. Check cookies/session.")
        print(f"  XSRF_TOKEN: {XSRF_TOKEN[:20]}...")
        print(f"  PHPSESSID:  {PHPSESSID}")
        return
    
    # ── Step 2: Fetch messages and write CSVs ──
    print(f"\n[2/2] Fetching messages and writing CSVs...")
    
    success_count = 0
    error_count   = 0
    summary_rows  = []
    
    for i, conv in enumerate(all_convs, 1):
        name  = conv["from_user"]  or "Unknown"
        phone = conv["thread_id"]  or "NoPhone"
        
        print(f"  [{i:03d}/{len(all_convs)}] {name} ({phone})...", end=" ")
        
        try:
            html = fetch_conversation_messages(conv)
            messages = parse_messages_simple(html)
            
            filename  = safe_filename(name, phone)
            filepath  = os.path.join(OUTPUT_DIR, filename)
            write_customer_csv(filepath, conv, messages)
            
            print(f"{len(messages)} msgs → {filename}")
            success_count += 1
            summary_rows.append({
                "customer":     name,
                "phone":        phone,
                "messages":     len(messages),
                "file":         filename,
                "subscriber_id":conv["from_user_id"],
            })
        except Exception as e:
            print(f"ERROR: {e}")
            error_count += 1
        
        time.sleep(DELAY)
    
    # ── Write summary ──
    summary_path = os.path.join(OUTPUT_DIR, "EXPORT_SUMMARY.csv")
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["customer", "phone", "messages", "file", "subscriber_id"])
        writer.writeheader()
        writer.writerows(summary_rows)
    
    print("\n" + "=" * 60)
    print(f"  Export complete!")
    print(f"  ✓ Success: {success_count} files")
    print(f"  ✗ Errors:  {error_count}")
    print(f"  Summary:   {summary_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
