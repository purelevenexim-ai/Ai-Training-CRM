# ⚡ CIAMP Phase 2 Production Deploy — Quick Reference
**Deploy Date:** May 22, 2026  
**Type:** Backend API + Frontend UI Update  
**Estimated Time:** 15 min

---

## **TL;DR — Copy & Paste Deployment**

```bash
# On server: 192.46.213.140
ssh root@192.46.213.140
cd /root/pureleven_dev

# Backup
pg_dump -h localhost -U pureleven -d pureleven > backup_$(date +%Y%m%d).sql
git stash

# Deploy
git fetch origin main && git pull origin main
npm run build || true

# Migrate (run the CIAMP Phase 2 migration script)
python3 -c "
import psycopg2
conn = psycopg2.connect(host='localhost', user='pureleven', password=os.getenv('POSTGRES_PASSWORD'), database='pureleven')
cur = conn.cursor()
cur.execute('''
CREATE TABLE IF NOT EXISTS customer_identities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_uid VARCHAR(255), identity_type VARCHAR(50), identity_value VARCHAR(500),
  source VARCHAR(50), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS customer_score_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_uid VARCHAR(255), customer_email VARCHAR(255), lead_score INTEGER,
  engagement_label VARCHAR(50), reason VARCHAR(255), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ci_uid ON customer_identities(customer_uid);
CREATE INDEX IF NOT EXISTS idx_csh_uid ON customer_score_history(customer_uid, created_at DESC);
''')
conn.commit()
cur.close()
conn.close()
"

# Restart
docker compose down crm-api && sleep 5 && docker compose up -d crm-api && sleep 10

# Verify
curl -s https://ai.pureleven.com/api/health | jq .status
```

---

## **What Changed**

| Component | Change | Impact |
|-----------|--------|--------|
| `customer_identities` | NEW TABLE | Stores email, phone, Meta, Google IDs |
| `customer_score_history` | NEW TABLE | Audit trail of score changes |
| `customer_score_scheduler.py` | NEW SERVICE | Hourly automatic score refresh |
| `journey_engine_v2.py` | UPDATED | AI decides channels + timing |
| `audience_service.py` | UPDATED | Seeds non-empty templates |
| `ContactsPanel.jsx` | UPDATED | Shows identity map + score history |
| `CampaignBuilderPanel.jsx` | FIXED | Dropdown data fetch bug fixed |

---

## **New API Endpoints**

```
GET  /api/customers/{email}/identities       → Returns identity map
GET  /api/customers/{email}/intelligence     → Includes score_history + identity_map
POST /api/customers/recompute-scores         → Manual score refresh
```

---

## **Backend Files Modified**

```
anu-login/backend/app/
  ├── storage.py                             (schemas: customer_identities, customer_score_history)
  ├── services/
  │   ├── customer_score_scheduler.py       (NEW)
  │   ├── customer_intelligence_service.py  (AI decisions + score history)
  │   ├── customer_unification_service.py   (identity recording)
  │   ├── audience_service.py               (default templates)
  │   ├── journey_engine_v2.py              (AI channel selection)
  │   └── shopify_sync_service.py           (backfill fix)
  ├── routes/customers.py                   (new endpoints)
  └── main.py                               (scheduler startup)
```

---

## **Frontend Files Modified**

```
src/components/
  ├── ContactsPanel.jsx                     (identity + score history display)
  └── CampaignBuilderPanel.jsx              (dropdown fix)
```

---

## **Database Schema Changes**

### New Tables

**`customer_identities`**
```sql
id (UUID)
customer_uid (VARCHAR)
identity_type (VARCHAR) — 'email', 'phone', 'meta_lead_id', 'google_gclid', etc.
identity_value (VARCHAR)
source (VARCHAR) — 'api', 'shopify', 'meta', 'google', etc.
created_at (TIMESTAMP)
last_seen_at (TIMESTAMP)
```

**`customer_score_history`**
```sql
id (UUID)
customer_uid (VARCHAR)
customer_email (VARCHAR)
lead_score (INTEGER)
engagement_label (VARCHAR)
purchase_status (VARCHAR)
reason (VARCHAR) — e.g., "website_visit", "open_email", "purchase"
created_at (TIMESTAMP)
```

---

## **Health Checks**

After restart, verify:

```bash
# 1. API is up
curl https://ai.pureleven.com/api/health

# 2. Tables exist
psql -U pureleven -d pureleven -c "
  SELECT COUNT(*) as tables_found FROM information_schema.tables 
  WHERE table_name IN ('customer_identities', 'customer_score_history')
"

# 3. Scheduler is running
docker compose logs crm-api | grep "customer_score_scheduler"

# 4. Templates are seeded
curl -s https://ai.pureleven.com/api/audiences/templates | jq '.templates | length'

# 5. Sample customer identity
curl -s https://ai.pureleven.com/api/customers/sample@example.com/identities 2>/dev/null | jq .
```

---

## **Rollback (If Needed)**

```bash
git reset --hard HEAD~1
docker compose down crm-api && sleep 5 && docker compose up -d crm-api
# Optional: restore DB from backup
psql -U pureleven -d pureleven < backup_YYYYMMDD.sql
```

---

## **Key Features Deployed**

✅ **Customer Identity Graph** — Email, phone, Meta, Google unified view  
✅ **Score History** — Track customer score evolution over time  
✅ **AI Journey Scheduling** — Decisions logged, channels selected per customer  
✅ **Auto Score Refresh** — Hourly background job  
✅ **Starter Templates** — Welcome, post-purchase, promo emails seeded  
✅ **Enhanced CRM UI** — Identity map + score history in customer modal  
✅ **Campaign Builder** — Fixed dropdown data binding  

---

**Questions?** Check: `/DEPLOYMENT_GUIDE_CIAMP_PHASE2_2026-05-22.md`
