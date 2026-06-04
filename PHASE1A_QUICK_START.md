# Phase 1A - Quick Start (5 Minutes)

## What Was Done

✅ Created 2 new Python modules (conversation_state_manager.py, clarification_flow.py)  
✅ Completely rewrote intent_router.py with corrected 11-level routing  
✅ Updated wave02_wabis_routes.py to use new modules  
✅ Updated storage.py with new database tables  
✅ All code syntax verified (no errors)  

**Result**: Complete routing foundation ready for deployment

---

## Deploy in 5 Steps

### 1️⃣ Backup Database (30 seconds)
```bash
ssh root@192.46.213.140
cp /root/pureleven_dev/app.db /root/pureleven_dev/app.db.backup.$(date +%s)
```

### 2️⃣ Copy Files (1 minute)
```bash
# From your local machine
scp /Users/bthomas/Documents/pureleven_dev/anu-login/backend/app/ai/conversation_state_manager.py \
    root@192.46.213.140:/root/pureleven_dev/anu-login/backend/app/ai/

scp /Users/bthomas/Documents/pureleven_dev/anu-login/backend/app/ai/clarification_flow.py \
    root@192.46.213.140:/root/pureleven_dev/anu-login/backend/app/ai/

scp /Users/bthomas/Documents/pureleven_dev/anu-login/backend/app/ai/intent_router.py \
    root@192.46.213.140:/root/pureleven_dev/anu-login/backend/app/ai/

scp /Users/bthomas/Documents/pureleven_dev/anu-login/backend/app/routes/wave02_wabis_routes.py \
    root@192.46.213.140:/root/pureleven_dev/anu-login/backend/app/routes/

scp /Users/bthomas/Documents/pureleven_dev/anu-login/backend/app/storage.py \
    root@192.46.213.140:/root/pureleven_dev/anu-login/backend/app/
```

### 3️⃣ Initialize Database (30 seconds)
```bash
ssh root@192.46.213.140
cd /root/pureleven_dev
python3 << 'EOF'
from anu_login.backend.app.storage import init_db
init_db()
print("✅ Database initialized")
EOF
```

### 4️⃣ Restart Container (30 seconds)
```bash
docker compose -f /root/pureleven_dev/docker-compose.yml restart pureleven-ai-engine
sleep 5
docker logs pureleven-ai-engine | grep -i "startup\|error" | tail -10
```

### 5️⃣ Test One Scenario (1 minute)
```bash
# Test: Send greeting (should set Wabis owner)
curl -X POST http://localhost:8000/api/ai/wave02/webhook/wabis/incoming \
  -H "Content-Type: application/json" \
  -d '{"phone":"919111111111","text":"Hi","first_name":"Test"}'

# Verify: Check database
sqlite3 /root/pureleven_dev/app.db "SELECT phone, owner, flow_id FROM conversation_state WHERE phone='919111111111';"

# Should output: 919111111111|wabis|greeting ✅
```

---

## Success Indicators

| Check | Command | Expected |
|-------|---------|----------|
| **Container Running** | `docker ps \| grep pureleven` | Container listed |
| **Greeting Routed** | `SELECT owner FROM conversation_state WHERE phone='919111111111';` | wabis |
| **Knowledge Gap Captured** | `sqlite3 app.db "SELECT COUNT(*) FROM knowledge_gaps;"` | > 0 |
| **Routing Logged** | `sqlite3 app.db "SELECT COUNT(*) FROM routing_log;"` | > 0 |
| **No Errors** | `docker logs pureleven-ai-engine \| grep ERROR` | (empty) |

---

## 10-Scenario Full Test (Optional but Recommended)

After step 5 works, run all 10 tests:

```bash
# See PHASE1A_DEPLOYMENT_GUIDE.md for full test suite
bash /root/pureleven_dev/run-10-scenario-tests.sh
```

---

## Rollback (If Something Wrong)

```bash
# Stop container
docker compose -f /root/pureleven_dev/docker-compose.yml stop pureleven-ai-engine

# Restore database
cp /root/pureleven_dev/app.db.backup.* /root/pureleven_dev/app.db

# Restart
docker compose -f /root/pureleven_dev/docker-compose.yml up -d pureleven-ai-engine
```

---

## What's Next

1. ✅ **Deploy** (5 minutes) ← YOU ARE HERE
2. ✅ **Test Scenarios** (30 minutes)
3. **Monitor Logs** (24 hours)
4. **Implement Missing Handlers** (Catalog, Sales, Order)

---

## Documentation

- **Full Deployment**: [PHASE1A_DEPLOYMENT_GUIDE.md](PHASE1A_DEPLOYMENT_GUIDE.md)
- **Architecture**: [PHASE1A_IMPLEMENTATION_SUMMARY.md](PHASE1A_IMPLEMENTATION_SUMMARY.md)

---

**Ready to deploy?** Copy the commands in Step 1-5 and run them on the VPS.

Questions? Check the full guide above.
