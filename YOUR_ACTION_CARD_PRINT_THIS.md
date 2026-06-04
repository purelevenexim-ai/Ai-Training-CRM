# 🎯 PURE LEVEN — YOUR ACTION CARD

**Print this or bookmark it** — Quick reference for daily work

---

## 🟢 WHAT'S WORKING RIGHT NOW (June 2, 2026)

| System | Status | Endpoint | What To Do |
|--------|--------|----------|-----------|
| **Shopify Store** | ✅ Live | pureleven.com | Browse to see storefront |
| **WhatsApp Bot** | ✅ Live | Wabis dashboard | Flows working, audit capturing |
| **Conversation Audit** | ✅ NEW | track.pureleven.com/api/admin | Check conversations & reports |
| **Customer CRM** | ✅ Live | ai.pureleven.com | View customer dashboard |
| **Paid Media** | ✅ Live | Google/Meta ads accounts | Monitor campaign performance |
| **Email System** | ✅ Live | Plunk + Sendgrid | Campaigns running |
| **AI WhatsApp** | 🟡 Disabled | (testing mode) | Do NOT re-enable yet |

---

## 📊 WHAT YOU JUST DEPLOYED

```
✅ FLOW VALIDATION SYSTEM
   Problem: Users typing "cardamom" in language menu got stuck
   Solution: Fuzzy matching + product intent detection
   Status: Live, working, tested with real message
   
✅ CONVERSATION AUDIT SYSTEM  
   What: Every message logged with intent + routing decision
   Where: track.pureleven.com/api/admin/conversations
   Reports: Auto-generated daily at midnight UTC
   Status: Capturing messages in real-time
   
✅ AI RESPONSE DISABLING
   Current: AI generates response, logs it, does NOT send to WhatsApp
   Reason: Testing phase - verifying system before Phase 2
   When to re-enable: After analyzing 1 week of audit data
   How to re-enable: Uncomment 3 lines in wave02_wabis_routes.py
```

---

## 🚀 YOUR PRIORITIES (June 2-9)

### TODAY (June 2)
- [x] Deploy flow validation system
- [x] Deploy conversation audit system  
- [x] Disable AI WhatsApp sending
- [ ] Send one test message and verify it's logged
- [ ] Bookmark the audit URL

### TOMORROW (June 3)
- [ ] Check if first daily report generated
  ```
  curl https://track.pureleven.com/api/admin/daily-report
  ```
- [ ] Review report file location on VPS:
  ```
  /app/data/reports/conversation_review_2026_06_03.md
  ```
- [ ] Verify cron job ran (check Docker logs)

### THIS WEEK (June 3-9)
- [ ] Check conversations list daily
  ```
  curl https://track.pureleven.com/api/admin/conversations?hours=24
  ```
- [ ] Monitor new conversations appearing
- [ ] Look for any errors in logs
- [ ] Keep a running tally of metrics
- [ ] Collect baseline week of data

### NEXT WEEK (June 9+)
- [ ] Analyze full week of audit data
- [ ] Measure flow completion rates
- [ ] Review detected intents distribution
- [ ] Identify top customer messages
- [ ] Plan Phase 2 changes
- [ ] Decide if/when to re-enable AI

---

## 📍 QUICK LINKS TO BOOKMARK

```
LIVE SERVICES:
https://pureleven.com                          (Shopify store)
https://ai.pureleven.com                       (Customer CRM dashboard)
https://track.pureleven.com/api/admin          (Conversation audit)

LIVE API ENDPOINTS:
https://track.pureleven.com/api/admin/conversations
https://track.pureleven.com/api/admin/conversations/{phone}
https://track.pureleven.com/api/admin/conversations/{phone}/html
https://track.pureleven.com/api/admin/routing-errors
https://track.pureleven.com/api/admin/daily-report

VPS SSH:
ssh root@192.46.213.140  (password: QazPlm123!@#)

DOCKER CONTAINERS:
pureleven-ai-engine (FastAPI backend)
pureleven-postgres (Database)

DOCUMENTATION:
PROJECT_OVERVIEW_COMPLETE.md       (Full overview)
PROJECT_QUICK_VISUAL_SUMMARY.md    (Visual guide)
SYSTEM_ARCHITECTURE_COMPLETE.md    (Technical details)
DEPLOYMENT_COMPLETE_2026_06_02.md  (Latest deployment)
CONVERSATION_AUDIT_SYSTEM.md       (How audit works)
FLOW_VALIDATION_IMPLEMENTATION.md  (Flow fix details)
CRM_MASTER_README.md               (CRM system)
```

---

## 🔧 COMMON COMMANDS

### Check System Health
```bash
# SSH to VPS
ssh root@192.46.213.140

# Check container status
docker ps | grep pureleven

# View logs
docker logs pureleven-ai-engine --tail 50

# Check recent conversations
curl https://track.pureleven.com/api/admin/conversations?hours=24

# View specific conversation
curl https://track.pureleven.com/api/admin/conversations/918547574028/html
```

### Check Latest Report
```bash
curl https://track.pureleven.com/api/admin/daily-report | head -20
```

### Send Test Message
```bash
curl -X POST https://track.pureleven.com/api/ai/wave02/webhook/wabis/incoming \
  -H "Content-Type: application/json" \
  -d '{
    "phone":"919999999999",
    "text":"cardamom price",
    "type":"text"
  }'
```

### View Database Directly
```bash
# SSH to VPS
ssh root@192.46.213.140

# Into container
docker exec -it pureleven-ai-engine bash

# Connect to SQLite
sqlite3 /app/data/anu_login.sqlite3

# View audit logs
SELECT phone, message, detected_intent, route_decision 
FROM conversation_audit_log 
ORDER BY created_at DESC 
LIMIT 10;

# Exit
.quit
```

---

## ⚠️ DO NOT DO THIS

```
❌ Do NOT re-enable AI WhatsApp sending yet
   → We're in testing/data collection phase
   → Wait until analyzing 1 week of data
   
❌ Do NOT change routing logic without testing
   → Test locally first
   → Test with 1 message on VPS
   → Monitor logs before full deployment
   
❌ Do NOT modify database schema without migration
   → Use alembic migrations
   → Test migration on staging first
   → Document all schema changes
   
❌ Do NOT ignore error messages
   → Check Docker logs if something breaks
   → Usually in the last 20 lines of logs
   → Ask for help if unsure

❌ Do NOT deploy without testing
   → Always test on VPS with one message first
   → Check logs for 30 seconds after deploy
   → Verify in audit logs that it was captured
```

---

## ✅ VERIFICATION CHECKLIST

### For Any Change You Make:

```
Before Deployment:
[ ] Code is tested locally
[ ] No syntax errors
[ ] All imports are correct
[ ] Changes are small and focused

After Deployment:
[ ] Service restarted successfully
[ ] Docker container still running (docker ps)
[ ] Health check passes (curl /api/health)
[ ] Send 1 test message
[ ] Check logs for errors
[ ] Verify in audit logs message was captured
[ ] No "Failed to get state" errors
[ ] Timestamp is correct (UTC ISO)
```

---

## 📈 METRICS TO TRACK (Daily)

### Morning Routine (When you check first)
```
1. Check daily report
   curl https://track.pureleven.com/api/admin/daily-report
   
2. Count conversations
   curl https://track.pureleven.com/api/admin/conversations?hours=24
   
3. Check for errors
   curl https://track.pureleven.com/api/admin/routing-errors
   
4. Note:
   - # of conversations that day
   - # of messages total
   - # of routing errors (should be 0-2)
   - Any new intents detected
```

### Weekly Summary (Every Sunday)
```
1. Total conversations
2. Average messages per conversation
3. Top 5 detected intents
4. Top 5 customer messages
5. Flow completion rates
6. Any patterns or problems noticed
```

---

## 🎓 KEY CONCEPTS

### What is the Audit System Doing?

```
Every WhatsApp message that comes in:

1. Stored in database
2. Analyzed for intent (what customer wants)
3. Routed to right handler (Wabis bot, AI, catalog, human, etc.)
4. Routing decision recorded with reason
5. Owner changes tracked (who "owns" conversation)
6. All logged for review

This creates a searchable, analyzable record of:
- What customers are asking about
- How well the bot understands them
- Where the system works/fails
- What features to build next
```

### Why Disable AI Right Now?

```
You can't measure the impact of AI if you:
1. Don't know what conversations look like WITHOUT AI
2. Haven't established baseline metrics
3. Don't understand your customer intents

By disabling AI, we:
1. See pure bot+flow behavior
2. Understand what gaps exist
3. Can measure before/after AI impact
4. Know exactly what problems to solve

When we re-enable AI:
- All messages are still logged
- We can compare before/after
- We'll KNOW if AI actually helps
```

---

## 🔑 PASSWORD & CREDENTIALS

```
VPS SSH:
Host: 192.46.213.140
User: root
Pass: QazPlm123!@#
Port: 22

Shopify Admin:
(In .env.production)

Meta Ad Account (to remember):
Facebook Pure Leven Exim
ID: 237007475595482

Google Ads:
(In Google Cloud console)

Wabis Account:
(In Wabis.in dashboard)
```

---

## 📞 IF SOMETHING BREAKS

```
Step 1: Check Docker status
  docker ps | grep pureleven
  
Step 2: View recent logs
  docker logs pureleven-ai-engine --tail 100
  
Step 3: Look for error patterns
  - "Failed to get state" → Database schema issue
  - "Connection refused" → PostgreSQL down
  - "500 Internal Server Error" → Code error
  - "Module not found" → Missing dependency
  
Step 4: Check which system is affected
  - Shopify store not working? → Check nginx
  - WhatsApp messages not arriving? → Check Wabis webhook
  - Audit logs empty? → Check API endpoint
  - Conversions not tracking? → Check event routes
  
Step 5: When in doubt
  - Restart container: docker restart pureleven-ai-engine
  - Check logs again after restart
  - Send test message again
  - Verify in audit logs
```

---

## 🎉 REMEMBER

You're building a **real product for real customers** in a **real market**. 

The fact that you:
- ✅ Deployed two major systems in one day
- ✅ Fixed a critical bug (Cardamom routing)
- ✅ Set up full audit trail for decision-making
- ✅ Followed data-driven methodology

...means you're doing it **RIGHT**.

Stay focused on:
1. **Measuring** before building
2. **Testing** before deploying
3. **Monitoring** after changes
4. **Documenting** everything you learn

The next week of data will show you exactly what to build next.

---

**Status**: 🟢 All Systems Go  
**Next Milestone**: June 9 (1 week data collected)  
**Your Mission**: Monitor, collect data, learn, decide  

Good luck! 🚀

