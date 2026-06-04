# 🚀 CIAMP Phase 2 Deployment Guide
**Date:** May 22, 2026  
**Status:** Ready for Production  
**Estimated Deployment Time:** 15 minutes

---

## **What's Being Deployed**

Customer Intelligence & AI Marketing Platform (CIAMP) Phase 2 enhancements:
- ✅ Persistent customer identity graph (email, phone, Meta, Google IDs)
- ✅ Customer score history and evolution tracking
- ✅ AI/rule-driven journey delivery decisions
- ✅ Hourly automated customer score refresh
- ✅ Non-empty starter Email/WhatsApp templates
- ✅ Enhanced customer details modal with identity + score history
- ✅ Campaign builder dropdown fixes

---

## **Deployment Steps**

### **STEP 1: SSH to Production Server (1 min)**

```bash
ssh root@192.46.213.140
cd /root/pureleven_dev
```

---

### **STEP 2: Backup Current State (2 min)**

```bash
# Backup database (PostgreSQL)
pg_dump -h localhost -U pureleven -d pureleven > /root/backup_$(date +%Y%m%d_%H%M%S).sql

# Backup current code
git stash
```

---

### **STEP 3: Pull Latest Code (2 min)**

```bash
# Fetch and pull
git fetch origin main
git pull origin main

# Verify new backend modules are present:
ls -la anu-login/backend/app/services/customer_score_scheduler.py
ls -la anu-login/backend/app/services/customer_intelligence_service.py
```

**Expected Output:**
- Both files should be present in `/root/pureleven_dev/anu-login/backend/app/services/`

---

### **STEP 4: Verify Frontend Build (1 min)**

```bash
# Check if dist/ has fresh build
ls -lah dist/assets/

# If needed, rebuild:
npm run build
```

**Expected:** `dist/` directory exists with `.css` and `.js` assets

---

### **STEP 5: Run Database Migrations (3 min)**

```bash
# Create migration for CIAMP Phase 2 (customer identities + score history)
cat > alembic_migration_ciamp_phase2.py << 'SQL'
import os
from alembic import op
import sqlalchemy as sa

def upgrade():
    """Create customer_identities and customer_score_history tables"""
    
    # customer_identities table
    op.execute("""
        CREATE TABLE IF NOT EXISTS customer_identities (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_uid VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            identity_type VARCHAR(50) NOT NULL,
            identity_value VARCHAR(500) NOT NULL,
            source VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_customer_identities_uid ON customer_identities(customer_uid)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_customer_identities_lookup ON customer_identities(identity_type, identity_value)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_customer_identities_source ON customer_identities(source, last_seen_at DESC)")
    
    # customer_score_history table
    op.execute("""
        CREATE TABLE IF NOT EXISTS customer_score_history (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_uid VARCHAR(255) NOT NULL,
            customer_email VARCHAR(255) NOT NULL,
            lead_score INTEGER,
            engagement_label VARCHAR(50),
            purchase_status VARCHAR(50),
            reason VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_customer_score_history_uid ON customer_score_history(customer_uid, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_customer_score_history_email ON customer_score_history(customer_email, created_at DESC)")

def downgrade():
    """Downgrade: drop CIAMP Phase 2 tables"""
    op.execute("DROP TABLE IF EXISTS customer_score_history")
    op.execute("DROP TABLE IF EXISTS customer_identities")
SQL

# Run Alembic migration
cd /root/pureleven_dev
python alembic_migration_ciamp_phase2.py

# Verify tables exist
psql -h localhost -U pureleven -d pureleven -c "
  SELECT table_name FROM information_schema.tables 
  WHERE table_name IN ('customer_identities', 'customer_score_history')
  ORDER BY table_name
"
```

**Expected Output:**
```
    table_name     
─────────────────
 customer_identities
 customer_score_history
(2 rows)
```

---

### **STEP 6: Restart Docker Container (2 min)**

```bash
# Stop the API container
docker compose down crm-api

# Wait 5 seconds
sleep 5

# Start with new code
docker compose up -d crm-api

# Check logs
docker compose logs -f crm-api | head -50
```

**Expected Output:**
```
crm-api    | INFO:     Uvicorn running on http://0.0.0.0:8000
crm-api    | INFO:     Application startup complete
```

---

### **STEP 7: Health Checks (2 min)**

```bash
# Check API health
curl -s https://ai.pureleven.com/api/health | jq .

# Verify new endpoints exist
curl -s https://ai.pureleven.com/api/customers \
  -H "Authorization: Bearer $(echo $INTERNAL_API_KEY)" | jq '.status'

# Check score scheduler is running
curl -s https://ai.pureleven.com/api/ai/performance-dashboard \
  -H "Authorization: Bearer $(echo $INTERNAL_API_KEY)" | jq '.scheduler_status'

# Verify templates seeded
curl -s https://ai.pureleven.com/api/audiences/templates \
  -H "Authorization: Bearer $(echo $INTERNAL_API_KEY)" | jq '.templates | length'
```

**Expected Results:**
- ✅ Health returns `{"status": "ok"}`
- ✅ Customers endpoint returns valid response
- ✅ Templates endpoint returns count ≥ 3

---

## **Rollback Plan (If Needed)**

```bash
# Stop current container
docker compose down crm-api

# Restore code
git checkout HEAD~1  # or specific commit

# Rebuild and restart
docker compose up -d crm-api

# Restore database backup if needed
psql -h localhost -U pureleven -d pureleven < /root/backup_TIMESTAMP.sql

# Restart
docker compose restart crm-api
```

---

## **Post-Deployment Verification**

### **1. Test Customer Identity Recording**

```bash
# Create test customer
curl -X POST https://ai.pureleven.com/api/customers \
  -H "Authorization: Bearer $(echo $INTERNAL_API_KEY)" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ciamp-test@pureleven.com",
    "phone": "9999999999",
    "meta_lead_id": "META-LEAD-TEST",
    "google_gclid": "GCLID-TEST-123",
    "preferred_channel": "auto"
  }'

# Fetch customer identities
curl -s https://ai.pureleven.com/api/customers/ciamp-test@pureleven.com/identities \
  -H "Authorization: Bearer $(echo $INTERNAL_API_KEY)" | jq '.items'
```

**Expected:** Identity map shows email, phone, Meta, Google IDs

### **2. Test AI Journey Scheduling**

```bash
# Verify AI decisions are being logged
curl -s https://ai.pureleven.com/api/ai/decisions?limit=10 \
  -H "Authorization: Bearer $(echo $INTERNAL_API_KEY)" | jq '.decisions | length'
```

**Expected:** ≥ 1 recent AI journey decision logged

### **3. Test Customer Score Scheduler**

```bash
# Trigger manual score recompute
curl -X POST https://ai.pureleven.com/api/customers/recompute-scores \
  -H "Authorization: Bearer $(echo $INTERNAL_API_KEY)" | jq '.'
```

**Expected Output:**
```json
{
  "checked": <number>,
  "updated": <number>
}
```

---

## **Monitoring Checklist**

After deployment, monitor for 1 hour:

- [ ] API logs show no errors
- [ ] Database queries completing normally
- [ ] Score refresh scheduler running (logs show hourly runs)
- [ ] No spike in CPU/memory usage
- [ ] Frontend loads and customer modal displays identity map + score history
- [ ] Campaign builder dropdowns populate correctly

---

## **Support Contacts**

- **API Issues:** Check logs: `docker compose logs crm-api`
- **Database Issues:** Run: `psql -U pureleven -d pureleven -c "SELECT COUNT(*) FROM customer_identities"`
- **Frontend Issues:** Clear browser cache (Cmd+Shift+Delete) and reload

---

**✅ Deployment Complete!**

Your CIAMP Phase 2 system is now live with:
- Full customer identity graph
- Persistent score history
- AI-driven journey scheduling
- Automated score refresh hourly
- Rich customer intelligence UI
