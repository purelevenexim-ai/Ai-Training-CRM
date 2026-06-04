# 🚀 QUICK DEPLOYMENT GUIDE
## Phase 0 + Sprint 1 Task 1 Deployment
**Last Updated**: May 22, 2026

---

# DEPLOYMENT CHECKLIST

## Pre-Deployment ✅
- [x] Code written and tested
- [x] React build passes
- [x] All imports fixed
- [x] Database migration created
- [x] API routes registered
- [x] UI component integrated

## Deployment Steps (5 minutes)

### 1. Backend Database Migration
```bash
cd /Users/bthomas/Documents/pureleven_dev

# Check migration status
alembic current
alembic history

# Run migration
alembic upgrade head

# Verify
psql -h localhost -U postgres -d pureleven -c "
  SELECT * FROM information_schema.tables 
  WHERE table_name IN ('crm_api_keys', 'crm_customers')
"

# Check for new columns on crm_customers
psql -h localhost -U postgres -d pureleven -c "
  \d crm_customers
" | grep lead
```

### 2. Backend Service Restart
```bash
# Kill existing process (if running)
pkill -f "python.*main.py"

# Restart FastAPI
cd /Users/bthomas/Documents/pureleven_dev
python -m uvicorn main:app --reload --port 8000

# Test health check
curl http://localhost:8000/api/crm/leads/health
# Expected: {"status": "ok", "service": "leads"}
```

### 3. Frontend Build & Deploy
```bash
cd /Users/bthomas/Documents/pureleven_dev

# Build
npm run build

# Verify build output
ls -lh dist/

# Deploy (copy dist to production)
cp -r dist/* /var/www/pureleven/

# Test in browser
# Navigate to: https://app.pureleven.com
# Click: 🎯 Leads tab
# Expected: Empty lead list with filters and create button
```

---

# TESTING IMMEDIATELY AFTER DEPLOY

## 1. Test Authentication
```bash
# Create API key
curl -X POST http://localhost:8000/api/auth/keys \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Key",
    "expires_in_days": 30,
    "description": "Testing"
  }'

# Save the returned "key" value as $API_KEY

# Exchange for JWT token
curl -X POST http://localhost:8000/api/auth/token \
  -H "X-API-Key: $API_KEY"

# Save the returned "access_token" as $JWT_TOKEN
```

## 2. Test Lead Creation
```bash
curl -X POST http://localhost:8000/api/crm/leads \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "name": "Test Lead",
    "phone": "+919876543210",
    "company": "Test Corp",
    "job_title": "Manager",
    "industry": "Technology",
    "lead_source": "manual"
  }'

# Expected: 200 OK with LeadResponse
```

## 3. Test Lead Listing
```bash
curl -X GET "http://localhost:8000/api/crm/leads?limit=50&status=new" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Expected: {"total": 1, "skip": 0, "limit": 50, "items": [...]}
```

## 4. Test UI Integration
1. Open browser: https://app.pureleven.com
2. Verify navigation bar shows "🎯 Leads" button
3. Click "🎯 Leads" tab
4. Verify:
   - Lead list appears empty
   - Filters visible (Status, Source, Min Score, Sort)
   - "+ New Lead" button visible
   - Metrics show "Total Leads: 1" (if step 2 succeeded)

## 5. Test Lead Workflow
1. Click "+ New Lead"
2. Fill form:
   - Email: `demo@pureleven.com`
   - Name: `Demo Lead`
   - Phone: `+919876543210`
   - Company: `Pure Leven`
   - Job Title: `Product Manager`
   - Industry: `E-commerce`
   - Lead Source: `manual`
3. Click "Create Lead"
4. Verify: Lead appears in list with status="new"
5. Change status dropdown to "contacted" 
6. Verify: Status badge updates, contacted_at timestamp appears

---

# ROLLBACK PROCEDURE (If Issues)

```bash
# Rollback database
alembic downgrade -1

# Rollback code (restore from git)
git checkout HEAD~1

# Restart services
pkill -f "python.*main.py"
python -m uvicorn main:app --reload --port 8000

# Re-build frontend
npm run build
cp -r dist/* /var/www/pureleven/
```

---

# MONITORING POST-DEPLOYMENT

## API Monitoring
```bash
# Watch request logs
tail -f logs/api.log | grep "POST /api/crm/leads\|GET /api/crm/leads"

# Check error rate
curl http://localhost:8000/metrics | grep lead_routes

# Monitor database
watch -n 5 "psql -h localhost -U postgres -d pureleven -c 'SELECT COUNT(*) FROM crm_api_keys; SELECT COUNT(*) FROM crm_customers WHERE is_lead=true;'"
```

## Frontend Monitoring
```bash
# Check browser console (F12 > Console)
# Look for: No errors or warnings related to leads

# Monitor network (F12 > Network)
# Filter: /api/crm/leads
# Expected: 200 responses for all requests
```

---

# CONFIGURATION AFTER DEPLOY

## 1. Create Admin API Key
```bash
curl -X POST http://localhost:8000/api/auth/keys \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Admin CLI",
    "expires_in_days": 365,
    "description": "Admin access for scripts and automation"
  }'

# Save key securely!
# Store in: ~/.env or secure vault
```

## 2. Create Integration API Keys
```bash
# For Google Forms integration
curl -X POST http://localhost:8000/api/auth/keys \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Google Forms → Leads",
    "expires_in_days": 90,
    "description": "Auto-import leads from Google Forms",
    "scope": "write:leads"
  }'

# For Meta Ads integration
curl -X POST http://localhost:8000/api/auth/keys \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Meta Lead Ads",
    "expires_in_days": 90,
    "description": "Auto-enroll Meta leads in journeys",
    "scope": "write:leads"
  }'
```

## 3. Configure Lead Source Tracking
Update these in backend config:
- `contact_form` - Shopify contact form
- `google_forms` - Google Forms integration
- `meta_ads` - Meta Lead Ads
- `csv_import` - Bulk CSV uploads
- `email` - Email signups
- `manual` - Admin entry

---

# PERFORMANCE TUNING

## Database Indexes
All indexes created automatically via migration:
- `idx_is_lead` - Filter leads only
- `idx_lead_status` - Filter by status
- `idx_lead_source` - Filter by source
- `idx_lead_score` - Sort by score

## Query Optimization
If listing leads feels slow:
```sql
-- Check index usage
EXPLAIN ANALYZE 
SELECT * FROM crm_customers 
WHERE is_lead = true AND lead_status = 'new' 
LIMIT 50;

-- Should show "Index Scan" not "Sequential Scan"
```

## API Response Caching
For high-traffic scenarios, consider:
```python
# Add to lead_routes.py if needed
from functools import lru_cache

@lru_cache(maxsize=100)
def get_lead_analytics(start_date, end_date):
    # Cached for 5 minutes
    return calculate_analytics(...)
```

---

# TROUBLESHOOTING

## Issue: Migration fails
```bash
# Check current schema
alembic current

# Check migration history
alembic history --verbose

# If stuck, reset to previous version
alembic downgrade -1

# Then try again
alembic upgrade head
```

## Issue: 401 Unauthorized when calling API
```bash
# Verify token not expired
curl -X POST http://localhost:8000/api/auth/verify \
  -H "Authorization: Bearer $JWT_TOKEN"

# If expired, get new token
curl -X POST http://localhost:8000/api/auth/token \
  -H "X-API-Key: $API_KEY"
```

## Issue: LeadManagerPanel not showing in UI
```bash
# 1. Check browser console (F12)
# 2. Verify import: grep "import LeadManagerPanel" src/components/CRMDashboard_V2.jsx
# 3. Verify navigation button added
# 4. Rebuild: npm run build
# 5. Clear browser cache: Ctrl+Shift+Delete
```

## Issue: Database tables don't exist after migration
```bash
# Check Alembic version table
psql -h localhost -U postgres -d pureleven -c "SELECT * FROM alembic_version;"

# If empty, manually insert
psql -h localhost -U postgres -d pureleven -c "INSERT INTO alembic_version (version_num) VALUES ('003_add_lead_management');"

# Then verify
alembic current
```

---

# SUCCESS CRITERIA

After deployment, verify:
- [x] `/api/crm/leads` returns 200 with empty array
- [x] Can create lead with POST
- [x] Can list leads with filters
- [x] Can update lead status
- [x] Can convert lead to customer
- [x] UI shows "🎯 Leads" tab
- [x] Lead list appears when tab clicked
- [x] Create form works
- [x] Filters work
- [x] Pagination works
- [x] No 500 errors in logs

**If all ✓, deployment is successful!**

---

# WHAT'S NEXT

Once deployment verified, begin:
1. **Sprint 1 Task 2**: Offline Conversion Matching (25h)
   - Phone hashing for CAPI
   - Address matching
   - Feedback loop

2. **Sprint 1 Task 3**: Propensity Scoring (30h)
   - RFM model
   - ML feature engineering
   - Daily recalculation

3. **Sprint 1 Task 4**: Cart Recovery (25h)
   - N8N workflow
   - Recovery emails
   - Attribution

---

# SUPPORT

**Questions about deployment?**
- Check: `IMPLEMENTATION_PHASE0_SPRINT1_2026-05-22.md`
- Check: `API_DOCUMENTATION.md`
- Check: Error logs in `/var/log/pureleven/`

**Still stuck?**
- Enable debug logs: Set `DEBUG=true` in `.env`
- Check database directly: `psql -U postgres -d pureleven`
- Review browser network tab for API response errors
