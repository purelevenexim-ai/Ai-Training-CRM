"""
Wabis Webhook Streaming Exporter

Alternative approach: Capture messages via Wabis webhooks
instead of bulk API export.

Setup:
1. In Wabis Dashboard → Webhook Workflow
2. Create webhook pointing to your endpoint
3. This script runs a FastAPI server to capture messages
4. Automatically saves to database/JSON as messages arrive
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from datetime import datetime
from typing import Any, Optional
import json
import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Wabis Webhook Receiver")

# Database setup
DB_PATH = Path("wabis_streaming.db")


def init_db():
    """Initialize SQLite database for streaming ingestion."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS webhook_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            webhook_id TEXT UNIQUE,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            sender TEXT,
            recipient TEXT,
            message_type TEXT,
            body TEXT,
            conversation_id TEXT,
            metadata TEXT,
            raw_payload TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations_streamed (
            id TEXT PRIMARY KEY,
            phone_number TEXT,
            last_message_at DATETIME,
            message_count INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv ON webhook_messages(conversation_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON webhook_messages(timestamp)")
    
    conn.commit()
    conn.close()


class WabisMessage(BaseModel):
    """Expected webhook payload from Wabis."""
    
    webhook_id: str
    from_phone: str
    to_phone: str
    message_type: str
    body: Optional[str] = None
    timestamp: Optional[datetime] = None
    conversation_id: Optional[str] = None
    template_id: Optional[str] = None
    variables: Optional[dict[str, Any]] = None
    
    class Config:
        extra = "allow"  # Allow additional fields


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_db()
    logger.info("Database initialized")


@app.post("/webhook/wabis")
async def receive_wabis_message(
    request: Request, 
    background_tasks: BackgroundTasks
):
    """
    Webhook endpoint for Wabis.
    
    Payload format (expected):
    {
        "webhook_id": "msg_12345",
        "from_phone": "+91XXXXXXXXXX",
        "to_phone": "+91YYYYYYYYYY",
        "message_type": "text",
        "body": "Customer message here",
        "timestamp": "2024-05-25T10:30:00Z",
        "conversation_id": "conv_xyz"
    }
    """
    try:
        payload = await request.json()
        
        # Background task to save to database
        background_tasks.add_task(save_message_to_db, payload)
        
        logger.info(f"Received message from {payload.get('from_phone')}")
        
        return {
            "status": "received",
            "webhook_id": payload.get("webhook_id"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))


def save_message_to_db(payload: dict[str, Any]):
    """Save received message to SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Insert message
        cursor.execute("""
            INSERT OR IGNORE INTO webhook_messages 
            (webhook_id, sender, recipient, message_type, body, conversation_id, raw_payload)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.get("webhook_id"),
            payload.get("from_phone"),
            payload.get("to_phone"),
            payload.get("message_type"),
            payload.get("body"),
            payload.get("conversation_id"),
            json.dumps(payload)
        ))
        
        # Update conversation metadata
        cursor.execute("""
            INSERT INTO conversations_streamed (id, phone_number, last_message_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET 
                last_message_at = datetime('now'),
                message_count = message_count + 1
        """, (
            payload.get("conversation_id") or payload.get("from_phone"),
            payload.get("from_phone")
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Saved message: {payload.get('webhook_id')}")
        
    except Exception as e:
        logger.error(f"Error saving to database: {e}")


@app.get("/stats")
async def get_stats():
    """Get streaming ingestion statistics."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get counts
        cursor.execute("SELECT COUNT(*) FROM webhook_messages")
        msg_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM conversations_streamed")
        conv_count = cursor.fetchone()[0]
        
        # Get latest messages
        cursor.execute("""
            SELECT timestamp FROM webhook_messages 
            ORDER BY timestamp DESC LIMIT 1
        """)
        latest = cursor.fetchone()
        
        conn.close()
        
        return {
            "total_messages": msg_count,
            "total_conversations": conv_count,
            "last_message_at": latest[0] if latest else None,
            "database_path": str(DB_PATH.absolute())
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/export/jsonl")
async def export_jsonl(limit: int = 10000):
    """Export collected messages as JSONL for AI training."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT conversation_id, sender, message_type, body, timestamp
            FROM webhook_messages
            ORDER BY timestamp ASC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Generate JSONL content
        jsonl_lines = []
        for row in rows:
            item = {
                "conversation_id": row[0],
                "sender": row[1],
                "message_type": row[2],
                "body": row[3],
                "timestamp": row[4]
            }
            jsonl_lines.append(json.dumps(item))
        
        return {
            "format": "jsonl",
            "count": len(jsonl_lines),
            "data": "\n".join(jsonl_lines)
        }
        
    except Exception as e:
        logger.error(f"Error exporting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    
    print("""
    ============================================================
    WABIS WEBHOOK STREAMING EXPORTER
    ============================================================
    
    Starting webhook receiver...
    
    Instructions:
    1. In Wabis Dashboard → Webhook Workflow
    2. Create new workflow with URL:
       https://your-domain.com/webhook/wabis
    
    3. Send test message through Wabis
    
    4. Check stats:
       curl http://localhost:8000/stats
    
    5. Export data:
       curl http://localhost:8000/export/jsonl > training_data.jsonl
    
    ============================================================
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
