#!/usr/bin/env python3
"""
Wabis Chat History Exporter for AI Training

Fetches conversations from Wabis API and exports to multiple formats:
- JSON (nested conversations)
- CSV (flattened messages)
- SQLite (queryable database)

Handles pagination for large datasets (10,000+ conversations).
"""

import json
import csv
import sqlite3
import requests
import time
from datetime import datetime
from typing import Any, Generator
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WabisExporter:
    """Export chat data from Wabis API for AI training."""

    def __init__(
        self,
        api_token: str,
        phone_number_id: str,
        base_url: str = "https://bot.wabis.in/api/v1",
    ):
        self.api_token = api_token
        self.phone_number_id = phone_number_id
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
        }

    def _make_request(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[Any]:
        """Make authenticated request to Wabis API."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise

    def fetch_chats(
        self, limit: int = 100, offset: int = 0
    ) -> Generator[dict[str, Any], None, None]:
        """
        Paginate through all chats.
        
        Yields individual chat/conversation objects.
        """
        while True:
            try:
                params = {
                    "limit": min(limit, 100),  # API limit
                    "offset": offset,
                    "apiToken": self.api_token,
                    "phone_number_id": self.phone_number_id,
                }
                
                result = self._make_request("/whatsapp/chats", params=params)
                
                # Handle different response formats
                chats = result if isinstance(result, list) else result.get("data", [])
                
                if not chats:
                    logger.info(f"Reached end of chats at offset {offset}")
                    break
                
                for chat in chats:
                    yield chat
                
                offset += len(chats)
                logger.info(f"Fetched {offset} chats so far...")
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error fetching chats at offset {offset}: {e}")
                break

    def fetch_inbox(
        self, limit: int = 100, offset: int = 0
    ) -> Generator[dict[str, Any], None, None]:
        """
        Paginate through inbox messages (alternative endpoint).
        
        Some Wabis installations use /inbox for message history.
        """
        while True:
            try:
                params = {
                    "limit": min(limit, 100),
                    "offset": offset,
                    "apiToken": self.api_token,
                }
                
                result = self._make_request("/whatsapp/inbox", params=params)
                
                messages = result if isinstance(result, list) else result.get("data", [])
                
                if not messages:
                    logger.info(f"Reached end of messages at offset {offset}")
                    break
                
                for msg in messages:
                    yield msg
                
                offset += len(messages)
                logger.info(f"Fetched {offset} messages so far...")
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error fetching messages at offset {offset}: {e}")
                break

    def to_json(self, output_path: str = "wabis_chats.json", max_chats: int = 10000):
        """Export chats to JSON format."""
        logger.info(f"Exporting to JSON: {output_path}")
        
        chats = []
        for i, chat in enumerate(self.fetch_chats()):
            if i >= max_chats:
                logger.info(f"Reached limit of {max_chats} chats")
                break
            chats.append(chat)
        
        with open(output_path, "w") as f:
            json.dump({"total": len(chats), "chats": chats}, f, indent=2, default=str)
        
        logger.info(f"Exported {len(chats)} chats to {output_path}")
        return output_path

    def to_csv(
        self, output_path: str = "wabis_chats.csv", max_chats: int = 10000
    ):
        """Export flattened message data to CSV."""
        logger.info(f"Exporting to CSV: {output_path}")
        
        messages = []
        with open(output_path, "w", newline="") as csvfile:
            fieldnames = [
                "timestamp",
                "sender",
                "recipient",
                "message_type",
                "body",
                "status",
                "conversation_id",
                "sender_phone",
                "recipient_phone",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for i, chat in enumerate(self.fetch_chats()):
                if i >= max_chats:
                    logger.info(f"Reached limit of {max_chats} chats")
                    break
                
                # Flatten chat structure for CSV
                messages_in_chat = chat.get("messages", [])
                for msg in messages_in_chat:
                    row = {
                        "timestamp": msg.get("timestamp") or msg.get("sent_at"),
                        "sender": msg.get("sender") or msg.get("from"),
                        "recipient": msg.get("recipient") or msg.get("to"),
                        "message_type": msg.get("type") or msg.get("message_type"),
                        "body": msg.get("body") or msg.get("text") or msg.get("content"),
                        "status": msg.get("status"),
                        "conversation_id": chat.get("id") or chat.get("conversation_id"),
                        "sender_phone": msg.get("sender_phone") or chat.get("phone_number"),
                        "recipient_phone": msg.get("recipient_phone") or chat.get("bot_phone"),
                    }
                    writer.writerow(row)
                    messages.append(row)
        
        logger.info(f"Exported {len(messages)} messages to {output_path}")
        return output_path

    def to_sqlite(
        self, db_path: str = "wabis_chats.db", max_chats: int = 10000
    ):
        """Export to SQLite database for easy querying."""
        logger.info(f"Exporting to SQLite: {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                phone_number TEXT,
                customer_name TEXT,
                last_message_at TIMESTAMP,
                message_count INTEGER,
                created_at TIMESTAMP,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                sender TEXT,
                recipient TEXT,
                message_type TEXT,
                body TEXT,
                status TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_id ON messages(conversation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp)")
        
        chat_count = 0
        msg_count = 0
        
        for chat in self.fetch_chats():
            if chat_count >= max_chats:
                logger.info(f"Reached limit of {max_chats} chats")
                break
            
            chat_id = chat.get("id") or chat.get("conversation_id")
            
            # Insert conversation
            cursor.execute(
                """
                INSERT OR IGNORE INTO conversations 
                (id, phone_number, customer_name, last_message_at, message_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    chat.get("phone_number") or chat.get("sender_phone"),
                    chat.get("customer_name") or chat.get("name"),
                    chat.get("last_message_at"),
                    len(chat.get("messages", [])),
                    chat.get("created_at"),
                ),
            )
            
            # Insert messages
            for msg in chat.get("messages", []):
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO messages
                    (id, conversation_id, sender, recipient, message_type, body, status, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        msg.get("id") or f"{chat_id}_{msg_count}",
                        chat_id,
                        msg.get("sender") or msg.get("from"),
                        msg.get("recipient") or msg.get("to"),
                        msg.get("type") or msg.get("message_type"),
                        msg.get("body") or msg.get("text"),
                        msg.get("status"),
                        msg.get("timestamp") or msg.get("sent_at"),
                    ),
                )
                msg_count += 1
            
            chat_count += 1
            if chat_count % 100 == 0:
                conn.commit()
                logger.info(f"Committed {chat_count} conversations, {msg_count} messages...")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Exported {chat_count} conversations, {msg_count} messages to {db_path}")
        return db_path

    def to_jsonl(
        self, output_path: str = "wabis_chats.jsonl", max_chats: int = 10000
    ):
        """Export to JSONL format (one JSON object per line) - ideal for streaming ML training."""
        logger.info(f"Exporting to JSONL: {output_path}")
        
        count = 0
        with open(output_path, "w") as f:
            for chat in self.fetch_chats():
                if count >= max_chats:
                    logger.info(f"Reached limit of {max_chats} chats")
                    break
                
                # Format conversation for AI training
                training_item = {
                    "conversation_id": chat.get("id") or chat.get("conversation_id"),
                    "phone_number": chat.get("phone_number"),
                    "messages": [
                        {
                            "timestamp": msg.get("timestamp") or msg.get("sent_at"),
                            "sender": msg.get("sender") or msg.get("from"),
                            "type": msg.get("type") or msg.get("message_type"),
                            "content": msg.get("body") or msg.get("text"),
                            "status": msg.get("status"),
                        }
                        for msg in chat.get("messages", [])
                    ],
                    "metadata": {
                        "created_at": chat.get("created_at"),
                        "last_message_at": chat.get("last_message_at"),
                        "customer_name": chat.get("customer_name"),
                    },
                }
                
                f.write(json.dumps(training_item, default=str) + "\n")
                count += 1
        
        logger.info(f"Exported {count} conversations to {output_path}")
        return output_path


def main():
    """Example usage."""
    import sys
    
    # Configuration
    API_TOKEN = "18280|Ws5wnHgkReob1OKVhDHWH3kzEIIRjItGN9wPcQFz23380f95"  # From your env
    PHONE_NUMBER_ID = "252036884661683"  # From your Wabis account
    MAX_CHATS = 10000
    OUTPUT_DIR = Path("wabis_export")
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    try:
        exporter = WabisExporter(API_TOKEN, PHONE_NUMBER_ID)
        
        # Export to all formats
        print("\n" + "="*60)
        print("WABIS CHAT HISTORY EXPORTER")
        print("="*60)
        
        print("\n[1/4] Exporting to JSON...")
        json_file = exporter.to_json(str(OUTPUT_DIR / "wabis_chats.json"), MAX_CHATS)
        print(f"✓ Saved: {json_file}")
        
        print("\n[2/4] Exporting to CSV...")
        csv_file = exporter.to_csv(str(OUTPUT_DIR / "wabis_chats.csv"), MAX_CHATS)
        print(f"✓ Saved: {csv_file}")
        
        print("\n[3/4] Exporting to JSONL (for streaming ML)...")
        jsonl_file = exporter.to_jsonl(str(OUTPUT_DIR / "wabis_chats.jsonl"), MAX_CHATS)
        print(f"✓ Saved: {jsonl_file}")
        
        print("\n[4/4] Exporting to SQLite (queryable)...")
        db_file = exporter.to_sqlite(str(OUTPUT_DIR / "wabis_chats.db"), MAX_CHATS)
        print(f"✓ Saved: {db_file}")
        
        print("\n" + "="*60)
        print("EXPORT COMPLETE!")
        print("="*60)
        print(f"\nOutput directory: {OUTPUT_DIR.absolute()}")
        print("\nRecommendations:")
        print("  • JSONL for LLM fine-tuning (one conversation per line)")
        print("  • SQLite for querying and analysis")
        print("  • CSV for spreadsheet import")
        print("  • JSON for direct integration")
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
