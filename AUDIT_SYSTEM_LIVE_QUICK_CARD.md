# 🚀 LIVE - Audit System Quick Reference

**Last Updated**: June 2, 2026, 7:31 PM UTC  
**Status**: 🟢 **LIVE AND WORKING**

## 🌐 Access URLs

| Feature | URL |
|---------|-----|
| **View conversation (HTML)** | `https://track.pureleven.com/api/admin/conversations/{phone}/html` |
| **List conversations** | `https://track.pureleven.com/api/admin/conversations?hours=24` |
| **Routing errors** | `https://track.pureleven.com/api/admin/routing-errors` |
| **Daily report** | `https://track.pureleven.com/api/admin/daily-report/html` |

Example: `https://track.pureleven.com/api/admin/conversations/918547574028/html`

---

## ✅ Live Proof

### Working Example
Phone: `918547574028`
- 4 messages captured
- Timestamps: 2026-06-01 19:30-19:31 UTC
- Messages: "Hello" → "Black pepper" → "Product" → "Cardamom"
- Routing: wabis → catalog → clarification → catalog
- **Status**: ✅ Logging working perfectly

---

## 🧪 Quick Test

```bash
# Send test message
curl -X POST https://track.pureleven.com/api/ai/wave02/webhook/wabis/incoming \
  -H "Content-Type: application/json" \
  -d '{"phone":"919999999999","text":"Hello Cardamom please"}'

# Wait 2 seconds, then check
curl -s 'https://track.pureleven.com/api/admin/conversations/919999999999/html'
```

Should show WhatsApp-style chat with message logged.

---

## 📊 What's Captured

Every customer message gets logged with:
- ✅ Timestamp (UTC ISO format)
- ✅ Phone number
- ✅ Message text
- ✅ Detected intent (product, greeting, order_tracking, etc.)
- ✅ Routing decision (wabis, ai, catalog, human, etc.)
- ✅ Active flow (if any)
- ✅ Owner before/after (state machine)

---

## 📈 Tomorrow (June 3)

Check automated daily report at midnight UTC:
```
/app/data/reports/conversation_review_2026_06_03.md
```

Will include:
- Total conversations
- Owner breakdown (wabis %, ai %, catalog %)
- Top 10 messages
- Routing errors (if any)
- Intent distribution

Accessible via: `https://track.pureleven.com/api/admin/daily-report`

---

## 🔧 Important Paths

| What | Path |
|------|------|
| VPS Host | 192.46.213.140 |
| Code | /opt/pureleven/ai-engine/app/ |
| Database | /app/data/anu_login.sqlite3 |
| Reports | /app/data/reports/ |
| Cron script | /opt/pureleven/ai-engine/generate_daily_report.py |

---

## ⚙️ System Files

| File | Size | Purpose |
|------|------|---------|
| audit_logger.py | 7.3K | Core logging |
| daily_report_generator.py | 7.8K | Report generation |
| routing_error_detector.py | 4.9K | Error detection |
| conversation_replay_routes.py | 16K | Web interface |
| flow_helpers.py | 3.8K | Fuzzy matching |
| intent_router.py | 12K | Routing logic |

---

## 🔍 Check Status

```bash
# Service health
curl -s https://track.pureleven.com/api/health | jq .

# Recent conversations
curl -s 'https://track.pureleven.com/api/admin/conversations?hours=24' | jq .

# Any routing errors?
curl -s 'https://track.pureleven.com/api/admin/routing-errors' | jq .

# Check logs (SSH)
ssh root@192.46.213.140 "docker logs pureleven-ai-engine --tail 20"
```

---

## ⏰ Cron Schedule

```
0 0 * * * /opt/pureleven/ai-engine/generate_daily_report.py
```

Runs daily at **midnight UTC**. Check results at:
- `/app/data/reports/conversation_review_YYYY_MM_DD.md`
- `https://track.pureleven.com/api/admin/daily-report`

---

## 🎯 One Week Plan

### Day 1 (Today) ✅
- [x] Deploy system
- [x] Test endpoints
- [ ] Send 1-2 test messages

### Days 2-6
- [ ] Monitor conversations being captured
- [ ] Review WhatsApp-style replays
- [ ] Check daily reports

### Day 7 (June 9)
- [ ] Analyze week of data
- [ ] Review daily reports
- [ ] Plan Phase 2 improvements

---

## 📋 Phase 2 Data-Driven Decisions

Based on audit data, answer:

1. **Language selection flow**: Is it helping?
   - Metric: % of users completing it
   - Target: >70%
   
2. **Intent detection accuracy**: Are we detecting correctly?
   - Metric: % of intended routes matching detected intent
   - Target: >85%

3. **Top customer needs**: What are they asking?
   - Metric: Top 10 messages/intents
   - Action: Build features for top 3

4. **Routing errors**: Any mismatches?
   - Metric: Count of routing errors per day
   - Target: 0

---

## 💡 Usage Examples

### Find all conversations in last 24 hours
```bash
curl -s 'https://track.pureleven.com/api/admin/conversations?hours=24&limit=100'
```

### View specific customer conversation
```bash
curl -s 'https://track.pureleven.com/api/admin/conversations/919876543210/html'
```

### Check for routing problems
```bash
curl -s 'https://track.pureleven.com/api/admin/routing-errors?hours=24'
```

### Get daily summary
```bash
curl -s 'https://track.pureleven.com/api/admin/daily-report'
```

---

## 🚨 Troubleshooting

| Issue | Fix |
|-------|-----|
| Endpoint 404 | `docker restart pureleven-ai-engine` |
| No conversations | Send test message (wait 2 sec) |
| Report not generating | Check cron: `crontab -l` |
| Service down | Check logs: `docker logs pureleven-ai-engine` |

---

## 📚 Full Documentation

- **Full Deployment Summary**: DEPLOYMENT_COMPLETE_2026_06_02.md
- **Conversation Audit System**: CONVERSATION_AUDIT_SYSTEM.md  
- **Quick Start Operations**: AUDIT_SYSTEM_QUICK_START.md
- **Flow Validation Details**: FLOW_VALIDATION_IMPLEMENTATION.md

---

## ✨ Summary

✅ Flow validation (Cardamom bug fixed)  
✅ Message logging (every message captured)  
✅ Routing tracking (decision recorded)  
✅ Conversation replay (WhatsApp-style UI)  
✅ Daily reports (automated at midnight UTC)  
✅ Error detection (routing mismatches flagged)  

**Status**: 🟢 **PRODUCTION READY**

**Next**: Monitor for 1 week, then analyze data for Phase 2 improvements.

