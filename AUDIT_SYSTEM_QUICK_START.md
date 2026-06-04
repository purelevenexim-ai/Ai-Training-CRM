# Conversation Audit System - Quick Start

## Deploy in 2 Steps

### Step 1: Run Setup
```bash
bash /Users/bthomas/Documents/pureleven_dev/setup_audit_system.sh
```

This will:
- Copy all audit files to VPS
- Create /app/data/reports/ directory
- Add cron job for daily reports
- Restart FastAPI service

### Step 2: Verify
```bash
# Check service is running
ssh root@192.46.213.140 "docker logs pureleven-ai-engine | tail -5"

# Test conversation list endpoint
curl https://track.pureleven.com/api/admin/conversations | jq
```

---

## Access Points

| Purpose | URL | Type |
|---------|-----|------|
| List conversations | `/api/admin/conversations` | JSON API |
| View one conversation | `/api/admin/conversations/{phone}` | JSON API |
| Chat replay | `/api/admin/conversations/{phone}/html` | Web page |
| Routing errors | `/api/admin/routing-errors` | JSON API |
| Daily report | `/api/admin/daily-report` | JSON API |
| Daily report (HTML) | `/api/admin/daily-report/html` | Web page |

---

## Common Tasks

### See What Happened to a Customer
```bash
# Find their phone number
curl "https://track.pureleven.com/api/admin/conversations?hours=24" | jq '.conversations[0].phone'

# View their full conversation
open "https://track.pureleven.com/api/admin/conversations/919XXXXXXXXX/html"
```

### Check Daily Stats
```bash
# Open daily report
open "https://track.pureleven.com/api/admin/daily-report/html"
```

### Find Routing Errors
```bash
# See all errors in last 24 hours
curl "https://track.pureleven.com/api/admin/routing-errors?hours=24" | jq '.critical_errors'
```

### Query Data Directly
```bash
# SSH to VPS
ssh root@192.46.213.140

# Enter SQLite
docker exec pureleven-ai-engine sqlite3 /app/data/anu_login.sqlite3

# Find all customer messages in last 24 hours
SELECT phone, message, created_at FROM conversation_audit_log 
WHERE source='customer' AND created_at > datetime('now', '-1 day')
ORDER BY created_at DESC LIMIT 20;

# Count by detected intent
SELECT detected_intent, COUNT(*) as count 
FROM conversation_audit_log 
WHERE created_at > datetime('now', '-1 day')
GROUP BY detected_intent 
ORDER BY count DESC;
```

---

## What Gets Logged

Every message:
- ✅ Who sent it (customer / AI / Wabis / Human)
- ✅ What it says
- ✅ What intent was detected
- ✅ Who owned the conversation before/after
- ✅ Which flow was active
- ✅ Where it was routed

Every routing decision:
- ✅ Which intent triggered it
- ✅ Expected route
- ✅ Actual route
- ✅ Why the decision was made

Every flow change:
- ✅ Which flow started/ended
- ✅ Why the change happened
- ✅ State before/after

---

## Daily Report Structure

**Generated at**: Midnight UTC
**Location**: `/app/data/reports/conversation_review_YYYY_MM_DD.md`

Contains:
- Total conversations
- Owner breakdown (Wabis, AI, Catalog, Human)
- Top intents detected
- Top customer messages
- Routing errors (with details)
- Flow analysis

---

## Cron Job Verification

```bash
# Check if cron is set up
ssh root@192.46.213.140 "crontab -l | grep generate_daily"

# Expected output:
# 0 0 * * * /opt/pureleven/ai-engine/generate_daily_report.py >> /var/log/pureleven_daily_report.log 2>&1

# Watch it run (manually at 23:50 UTC for testing)
ssh root@192.46.213.140
# Then at midnight:
tail -f /var/log/pureleven_daily_report.log
```

---

## Understanding the Flow

```
Customer sends message
    ↓
Logged to conversation_audit_log (inbound, customer)
    ↓
Router detects intent
    ↓
Logged to conversation_audit_log (system, routing_decision)
    ↓
AI/Wabis/Human responds
    ↓
Logged to conversation_audit_log (outbound, ai/wabis/human)
```

This gives you the complete story.

---

## Key Metrics to Watch

### Availability
```sql
-- Are conversations being logged?
SELECT COUNT(DISTINCT phone) FROM conversation_audit_log 
WHERE created_at > datetime('now', '-1 day');
```

### Intent Detection
```sql
-- What intents are customers expressing?
SELECT detected_intent, COUNT(*) FROM conversation_audit_log 
WHERE source='customer' GROUP BY detected_intent 
ORDER BY COUNT(*) DESC;
```

### Routing Accuracy
```sql
-- Are we routing to the right place?
SELECT route_decision, COUNT(*) FROM conversation_audit_log 
WHERE direction='inbound' AND source='system' 
GROUP BY route_decision ORDER BY COUNT(*) DESC;
```

### Flow Performance
```sql
-- How many times is each flow started?
SELECT active_flow, COUNT(DISTINCT phone) FROM conversation_audit_log 
WHERE active_flow IS NOT NULL 
GROUP BY active_flow 
ORDER BY COUNT(*) DESC;
```

---

## Troubleshooting

**"No conversations showing"**
→ Wait a few minutes for first data to arrive
→ Check phone numbers are being captured
→ Look at router logs: `docker logs pureleven-ai-engine | grep ROUTE`

**"Daily report not generating"**
→ Check cron job: `crontab -l`
→ Check logs: `tail -f /var/log/pureleven_daily_report.log`
→ Run manually: `docker exec pureleven-ai-engine python3 /opt/pureleven/ai-engine/generate_daily_report.py`

**"Conversation looks incomplete"**
→ Events may still be arriving (async processing)
→ Check raw data: `SELECT * FROM conversation_audit_log WHERE phone='919XXXXXXXXX' ORDER BY created_at`

---

## Files to Know

- **Main code**: `/app/app/ai/audit_logger.py`
- **Daily reports**: `/app/data/reports/`
- **Cron logs**: `/var/log/pureleven_daily_report.log`
- **Database**: `/app/data/anu_login.sqlite3`
- **Routes**: `/app/app/routes/conversation_replay_routes.py`

---

## Next Phase

Once audit data is being collected (1-2 weeks):
1. Measure what's working: flow completion rates, intent detection accuracy
2. Identify patterns: which flows are helping, which are hurting
3. Make Phase 2 routing improvements based on **real data**, not guesses

**Remember**: "Don't build advanced features until measuring real data" ✅
