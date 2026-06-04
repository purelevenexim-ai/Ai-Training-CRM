# Conversation Audit System - Complete Guide

**Status**: ✅ Ready for deployment
**Purpose**: Capture every message, routing decision, and state change for debugging and compliance
**Access**: Web UI + API endpoints + Daily reports

---

## The Problem This Solves

Before audit system:
```
Customer: "Cardamom"
Router: Sends to Wabis
AI Team: "Why did they go to Wabis?"
Answer: ❓ No logs, no explanation
```

After audit system:
```
Customer: "Cardamom"
Router: Sends to Catalog (product intent detected)
AI Team: Clicks conversation → sees full history → understands why
```

---

## Database Schema

### conversation_audit_log
Every single event in a conversation gets logged here.

```sql
CREATE TABLE conversation_audit_log (
    id TEXT PRIMARY KEY,           -- UUID
    created_at TEXT NOT NULL,      -- ISO timestamp
    
    phone TEXT NOT NULL,           -- Customer phone
    
    direction TEXT NOT NULL,       -- "inbound" or "outbound"
    source TEXT NOT NULL,          -- "customer" | "ai" | "wabis" | "human" | "campaign" | "system"
    message TEXT,                  -- Actual message content
    
    owner_before TEXT,             -- Who owned before this event
    owner_after TEXT,              -- Who owns after this event
    
    active_flow TEXT,              -- Which flow is running
    detected_intent TEXT,          -- What intent was recognized
    route_decision TEXT,           -- Where message was routed
    reason TEXT,                   -- Why the decision was made
    
    metadata_json TEXT             -- Extra context (JSON)
);

-- Indexes for fast querying
CREATE INDEX idx_audit_phone ON conversation_audit_log(phone, created_at DESC);
CREATE INDEX idx_audit_source ON conversation_audit_log(source, created_at DESC);
CREATE INDEX idx_audit_intent ON conversation_audit_log(detected_intent, created_at DESC);
CREATE INDEX idx_audit_route ON conversation_audit_log(route_decision, created_at DESC);
```

---

## Key Components

### 1. audit_logger.py
Helper functions to log events.

**Main Functions**:
- `log_customer_message()` - Log incoming message from customer
- `log_routing_decision()` - Log where message was routed and why
- `log_ai_response()` - Log AI-generated response
- `log_wabis_response()` - Log Wabis bot response
- `log_flow_transition()` - Log flow state changes
- `get_conversation_history()` - Retrieve all events for a phone

**Example Usage**:
```python
from app.ai.audit_logger import log_customer_message, log_routing_decision

# When customer sends message
log_customer_message(
    phone="919876543210",
    message="Cardamom",
    owner="wabis",
    active_flow="language_selection",
    detected_intent="product_search"
)

# When router makes decision
log_routing_decision(
    phone="919876543210",
    owner_before="wabis",
    owner_after="catalog",
    route_decision="catalog",
    reason="product_intent_override"
)
```

### 2. daily_report_generator.py
Auto-generates markdown reports every night.

**Reports include**:
- Total conversations by owner (Wabis, AI, Catalog, Human)
- Detected intents breakdown
- Top customer messages
- Flow start counts
- Routing errors with details

**Generated at**: Midnight UTC
**Location**: `/app/data/reports/conversation_review_YYYY_MM_DD.md`

**Manual generation**:
```bash
python3 /opt/pureleven/ai-engine/generate_daily_report.py
```

### 3. routing_error_detector.py
Automatically flags routing mistakes.

**Detects**:
- Expected Catalog → Actual Wabis (ERROR)
- Expected Human → Actual AI (ERROR)
- Expected Order System → Actual Campaign (WARNING)

**Usage**:
```python
from app.ai.routing_error_detector import detect_routing_errors, get_routing_error_summary

errors = detect_routing_errors(hours=24)
summary = get_routing_error_summary(hours=24)
```

### 4. conversation_replay_routes.py
Web endpoints for viewing conversations and reports.

---

## Web Interface

### List Recent Conversations
```
GET /api/admin/conversations
```

**Parameters**:
- `hours`: Last N hours (default 24)
- `limit`: Max conversations (default 50)

**Response**:
```json
{
  "total": 127,
  "hours_lookback": 24,
  "conversations": [
    {
      "phone": "919876543210",
      "first_message": "2026-06-02T10:30:00+00:00",
      "last_message": "2026-06-02T12:45:00+00:00",
      "message_count": 8,
      "view_url": "/api/admin/conversations/919876543210"
    }
  ]
}
```

### View Conversation Replay (JSON)
```
GET /api/admin/conversations/{phone}
```

**Response**: Chronological list of all events
```json
{
  "phone": "919876543210",
  "total_events": 8,
  "current_owner": "catalog",
  "current_flow": null,
  "events": [
    {
      "timestamp": "2026-06-02T10:30:00+00:00",
      "type": "customer",
      "direction": "inbound",
      "message": "Hi",
      "detected_intent": "greeting",
      "route_decision": "wabis",
      "owner_after": "wabis"
    },
    {
      "timestamp": "2026-06-02T10:30:05+00:00",
      "type": "wabis",
      "direction": "outbound",
      "message": "Choose Language: English / Malayalam",
      "owner_after": "wabis"
    },
    {
      "timestamp": "2026-06-02T10:30:45+00:00",
      "type": "customer",
      "direction": "inbound",
      "message": "Cardamom",
      "detected_intent": "product_search",
      "route_decision": "catalog"
    }
  ]
}
```

### View Conversation (WhatsApp-style Chat)
```
GET /api/admin/conversations/{phone}/html
```

Opens in browser showing conversation like WhatsApp:
- Left side: Customer & Wabis messages
- Right side: AI responses
- Gray messages: System events (routing, flow changes)
- Timestamps and metadata visible

### View Routing Errors
```
GET /api/admin/routing-errors
```

**Parameters**:
- `hours`: How far back to look (default 24)

**Response**:
```json
{
  "total_errors": 12,
  "by_type": {
    "catalog→wabis": 8,
    "ai→wabis": 3,
    "human→ai": 1
  },
  "by_severity": {
    "error": 5,
    "warning": 7,
    "info": 0
  },
  "critical_errors": [
    {
      "phone": "919876543210",
      "timestamp": "2026-06-02T11:30:00+00:00",
      "message": "Cardamom",
      "detected_intent": "product_search",
      "expected_route": "catalog",
      "actual_route": "wabis",
      "severity": "error"
    }
  ]
}
```

### View Daily Report (HTML)
```
GET /api/admin/daily-report/html
```

Formatted HTML with:
- Summary statistics
- Conversations by owner (table)
- Top intents
- Top customer messages
- Routing errors
- Flow analysis

### Download Daily Report (JSON)
```
GET /api/admin/daily-report
```

Returns raw markdown content for programmatic access.

---

## Files Deployed

**New Files**:
- `app/ai/audit_logger.py` (200 lines)
- `app/ai/daily_report_generator.py` (280 lines)
- `app/ai/routing_error_detector.py` (150 lines)
- `app/routes/conversation_replay_routes.py` (430 lines)
- `backend/generate_daily_report.py` (cron script)

**Modified Files**:
- `app/storage.py` (added conversation_audit_log table)
- `app/ai/intent_router.py` (integrated audit logging)

---

## Deployment

### Prerequisites
- VPS: 192.46.213.140
- Container: pureleven-ai-engine
- Storage: /app/data/reports/

### Deploy Steps

```bash
# 1. Run setup script (all files copied, cron job added)
bash /Users/bthomas/Documents/pureleven_dev/setup_audit_system.sh

# 2. Verify deployment
ssh root@192.46.213.140 "ls -la /app/data/reports/"

# 3. Check cron job
ssh root@192.46.213.140 "crontab -l | grep generate_daily"

# 4. Monitor logs
ssh root@192.46.213.140 "tail -f /var/log/pureleven_daily_report.log"
```

### Manual Report Generation
```bash
ssh root@192.46.213.140
docker exec pureleven-ai-engine python3 /opt/pureleven/ai-engine/generate_daily_report.py
```

---

## Usage Examples

### Morning Review
1. Open browser: `https://track.pureleven.com/api/admin/daily-report/html`
2. Review summary: Total conversations, routing errors, top messages
3. Check routing errors: `https://track.pureleven.com/api/admin/routing-errors`
4. If errors found, click phone number to view full conversation

### Debugging a Conversation
1. Get phone number from error report
2. Open: `https://track.pureleven.com/api/admin/conversations/919876543210/html`
3. See entire conversation flow:
   - Customer messages on left
   - AI responses on right
   - Routing decisions in gray
   - Metadata shows intent, flow, owner changes

### Checking Flow Abandonment
```sql
SELECT COUNT(*) as total,
       SUM(CASE WHEN source='customer' THEN 1 ELSE 0 END) as customer_messages,
       SUM(CASE WHEN route_decision='catalog' THEN 1 ELSE 0 END) as routed_to_catalog
FROM conversation_audit_log
WHERE created_at > datetime('now', '-7 days')
  AND active_flow='language_selection';
```

### Finding Top Customer Questions
```sql
SELECT message, COUNT(*) as count
FROM conversation_audit_log
WHERE source='customer' AND created_at > datetime('now', '-7 days')
GROUP BY message
ORDER BY count DESC
LIMIT 20;
```

---

## Cron Job Setup

**Added to VPS crontab**:
```
0 0 * * * /opt/pureleven/ai-engine/generate_daily_report.py >> /var/log/pureleven_daily_report.log 2>&1
```

- Runs every day at midnight UTC
- Generates report for previous day
- Saves to: `/app/data/reports/conversation_review_YYYY_MM_DD.md`
- Logs to: `/var/log/pureleven_daily_report.log`

---

## Storage Requirements

**Per conversation** (average):
- 5-10 events
- ~200 bytes per event
- Total: ~2KB per conversation

**Daily** (estimated):
- 100-200 conversations
- ~200-400 KB per day
- ~150 MB per year

---

## Security & Privacy

**What's logged**:
- Message content (needed for debugging)
- Phone numbers (needed for tracking)
- Routing decisions (needed for analysis)
- Metadata (context for decisions)

**Access control**:
- Currently: All endpoints at `/api/admin/` are internal-only
- Recommended: Add authentication before exposing to public
- Reports: Stored in `/app/data/reports/` (local access only)

---

## Next Steps

### Phase 2 (Based on Audit Data)
Before making any routing changes, measure:
1. ✅ Language flow completion rate
2. ✅ Product intent detection success
3. ✅ Routing error frequency
4. ✅ Customer satisfaction indicators

Then decide:
- Should we keep language selection?
- Should we auto-detect language?
- What flows are really helping?
- Which customers are bouncing?

### Phase 3 (Advanced)
- Customer satisfaction scoring
- Conversation health alerts
- Predictive routing optimization
- A/B testing different flows

---

## Troubleshooting

### Reports not generating
```bash
# Check cron logs
tail -f /var/log/pureleven_daily_report.log

# Run manually to see errors
docker exec pureleven-ai-engine python3 /opt/pureleven/ai-engine/generate_daily_report.py
```

### Conversation page showing blank
```bash
# Check if phone has events in audit table
docker exec pureleven-ai-engine sqlite3 /app/data/anu_login.sqlite3 \
  "SELECT COUNT(*) FROM conversation_audit_log WHERE phone='919876543210';"
```

### Slow report generation
```bash
# Check database size
docker exec pureleven-ai-engine sqlite3 /app/data/anu_login.sqlite3 \
  "SELECT COUNT(*) as total FROM conversation_audit_log;"

# If too large, archive old records
```

---

## Support

**Questions?** Check the main router and audit_logger source code.
**Issues?** Check VPS logs: `docker logs pureleven-ai-engine`
**Data?** Query /app/data/anu_login.sqlite3 directly via SSH
