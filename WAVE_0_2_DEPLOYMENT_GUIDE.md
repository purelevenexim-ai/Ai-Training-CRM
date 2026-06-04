# 🚀 Wave 0.2 Complete Deployment Guide

## Project Status: READY FOR LIVE DEPLOYMENT

All Wave 0.2 features are **code complete** and ready for production deployment.

---

## 📋 What's Included

### Backend Services (Ready ✅)
- **Advanced Scoring Engine**: Churn risk + response quality scoring
- **KB Organization Service**: Performance tracking + auto-archiving
- **Feature Toggle Service**: Runtime feature control (no code redeploy needed)

### API Endpoints (Ready ✅)
- 21 new endpoints under `/api/ai/wave02/`
- Feature toggle management endpoints
- Advanced scoring endpoints
- KB organization endpoints
- Dashboard summary endpoint

### Database Migration (Ready ✅)
- Migration 008: Adds feature_toggles table + new scoring columns
- 5 default features pre-configured
- Reversible with `alembic downgrade 007`

### Admin Dashboard (Ready ✅)
- Beautiful React component for feature control
- Real-time KPI cards (reviews, learning, KB, features)
- One-click toggle buttons with instant feedback
- Category-based organization

---

## 🔧 Deployment Steps

### Prerequisites
- Live server with PostgreSQL database
- FastAPI + Python 3.9+ running
- Alembic for migrations
- PostgreSQL client tools

### Step 1: Backup Production Database (⚠️ CRITICAL)
```bash
# SSH into live server
ssh user@live-server

# Backup database
pg_dump -U db_user -d pureleven_crm > /backups/pureleven_crm_backup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -lh /backups/*.sql | tail -1
```

### Step 2: Upload Files to Live Server
```bash
# From your local machine (within pureleven_dev folder)

# Copy backend services
scp app/ai_service/advanced_scoring_engine.py user@live-server:/app/ai_service/
scp app/ai_service/kb_organization_service.py user@live-server:/app/ai_service/
scp app/ai_service/feature_toggle_service.py user@live-server:/app/ai_service/

# Copy API routes
scp app/routes/wave02_routes.py user@live-server:/app/routes/

# Copy database migration
scp alembic/versions/008_wave_0_2_complete.py user@live-server:/alembic/versions/

# Copy frontend dashboard
scp src/components/AdminDashboard.jsx user@live-server:/src/components/

# Copy updated main.py
scp main.py user@live-server:/app/

# Copy alembic config (if not exists)
scp alembic.ini user@live-server:/
scp alembic/env.py user@live-server:/alembic/
```

### Step 3: Verify Files Uploaded
```bash
# SSH into server
ssh user@live-server

# Check files
ls -la app/ai_service/ | grep -E "advanced_scoring|kb_organization|feature_toggle"
ls -la app/routes/wave02_routes.py
ls -la alembic/versions/008_*
```

### Step 4: Run Database Migration
```bash
# SSH into server
ssh user@live-server

# Navigate to app directory
cd /app

# Activate virtual environment
source .venv/bin/activate

# Run migration
export DATABASE_URL="postgresql://db_user:db_password@localhost:5432/pureleven_crm"
alembic upgrade 008

# Verify migration success (should show: "Succeeded!")
```

### Step 5: Verify Database Changes
```bash
# In PostgreSQL
psql -U db_user -d pureleven_crm

-- Check new columns
\d customer_ai_profile

-- Check feature_toggles table
\d feature_toggles

-- List all toggles
SELECT feature_key, feature_name, enabled FROM feature_toggles;
```

### Step 6: Restart FastAPI Server
```bash
# Using supervisorctl
supervisorctl restart fastapi

# Or using systemctl
systemctl restart fastapi

# Or manually
pkill -f "uvicorn"
cd /app && .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
```

### Step 7: Verify API Endpoints
```bash
# Test feature toggles endpoint
curl -X GET https://live-server/api/ai/wave02/features/all

# Expected response:
# {"count": 5, "features": [{"feature_key": "wave_0_2_review_queue", "enabled": true, ...}]}

# Test dashboard summary
curl -X GET https://live-server/api/ai/wave02/dashboard/summary
```

### Step 8: Add Admin Dashboard to Frontend Routing
```javascript
// In your routing configuration (e.g., index.jsx)
import AdminDashboard from './AdminDashboard';

// Add route
<Route path="/dashboard" element={<AdminDashboard />} />
```

### Step 9: Share Dashboard Link
```
Dashboard URL: https://your-live-domain.com/dashboard
User Instructions:
1. Open the admin dashboard
2. All Wave 0.2 features are shown
3. Click toggle button to enable/disable any feature
4. Changes apply immediately (no server restart needed)
```

---

## 🎯 Feature Overview

### Wave 0.2 - Daily Review Queue
- **Status**: Enabled by default
- **Feature Toggle**: `wave_0_2_review_queue`
- **What it does**: Flags low-confidence AI responses for human review
- **Turn off when**: Testing without review queue

### Wave 0.2 - Learning Engine
- **Status**: Enabled by default
- **Feature Toggle**: `wave_0_2_learning_engine`
- **What it does**: Improves rule engine accuracy from user corrections
- **Turn off when**: Testing rule engine alone

### Wave 0.2 - Advanced Scoring
- **Status**: Enabled by default
- **Feature Toggle**: `wave_0_2_advanced_scoring`
- **What it does**: Calculates churn risk and response quality scores
- **Turn off when**: Testing without advanced scores

### Wave 0.2 - KB Auto-Organization
- **Status**: Enabled by default
- **Feature Toggle**: `wave_0_2_kb_organization`
- **What it does**: Tracks KB performance and suggests archiving
- **Turn off when**: Testing without KB organization

### Wave 1 - Product Affinity (Future)
- **Status**: Disabled by default
- **Feature Toggle**: `wave_1_product_affinity`
- **What it does**: Recommends complementary products
- **Turn on when**: Wave 1 development complete

---

## 📊 API Endpoints

### Feature Toggles (Prefix: `/api/ai/wave02`)

```
GET    /features/all                    # List all toggles
GET    /features/category/{category}    # Filter by Wave
GET    /features/status                 # Summary by category
POST   /features/toggle                 # Enable/disable feature
GET    /features/check/{feature_key}    # Check single feature

# Request body for toggle:
{
  "feature_key": "wave_0_2_review_queue",
  "enabled": false
}

# Response:
{
  "feature_key": "wave_0_2_review_queue",
  "enabled": false,
  "updated_at": "2024-06-01T10:30:00Z"
}
```

### Review Queue

```
GET    /review/pending                  # Get pending reviews (limit 50)
POST   /review/approve                  # Approve and correct
POST   /review/escalate                 # Escalate complex cases
GET    /review/stats                    # Queue metrics
GET    /review/daily-summary            # Email digest data
```

### Learning Engine

```
GET    /learning/progress               # Accuracy improvement metrics
GET    /learning/batch                  # Training examples
GET    /learning/intent-distribution    # Intent breakdown
GET    /learning/keywords/{intent}      # Suggested keywords
```

### Advanced Scoring

```
GET    /scoring/customer/{id}           # Get all scores
GET    /scoring/churn/{id}              # Churn + quality scores
POST   /scoring/batch-update            # Update all customers
```

### KB Organization

```
GET    /kb/top-performing               # Best KB entries
GET    /kb/low-performing               # Archiving candidates
POST   /kb/archive/{kb_id}              # Archive entry
GET    /kb/stats                        # Overall stats
```

### Dashboard

```
GET    /dashboard/summary               # All metrics for admin UI
```

---

## 🔙 Rollback Plan

If anything goes wrong:

### Option 1: Downgrade Migration
```bash
cd /app
source .venv/bin/activate
export DATABASE_URL="postgresql://db_user:db_password@localhost/pureleven_crm"

# Downgrade to version 007
alembic downgrade 007

# Verify
alembic current  # Should show 007
```

### Option 2: Restore from Backup
```bash
# Stop FastAPI server
supervisorctl stop fastapi

# Restore database
psql -U db_user -d pureleven_crm < /backups/pureleven_crm_backup_YYYYMMDD_HHMMSS.sql

# Restart server
supervisorctl start fastapi
```

---

## ✅ Testing Checklist

After deployment, verify:

- [ ] FastAPI server is running (check logs)
- [ ] Database migration successful (`\d feature_toggles`)
- [ ] API endpoints responding (curl test)
- [ ] Feature toggle endpoints work
- [ ] Dashboard loads without errors
- [ ] Toggle buttons update database
- [ ] Changes persist on page refresh
- [ ] All 5 default toggles present
- [ ] Wave 0.2 features enabled by default
- [ ] Wave 1 features disabled by default

---

## 📞 Troubleshooting

### "ModuleNotFoundError: No module named 'sqlalchemy'"
```bash
cd /app
source .venv/bin/activate
pip install sqlalchemy alembic
```

### "connection to server at localhost failed"
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify credentials and database name
psql -U db_user -d pureleven_crm -c "SELECT 1"
```

### "Table 'feature_toggles' already exists"
```bash
# Migration already run
alembic current  # Should show 008
```

### "Feature toggle API returning 500"
```bash
# Check FastAPI logs
tail -f /var/log/fastapi/app.log

# Verify wave02_router imported in main.py
grep "wave02_router" main.py

# Check route registration
grep "include_router" main.py
```

### "Admin dashboard not loading"
```bash
# Verify AdminDashboard.jsx copied
ls -la src/components/AdminDashboard.jsx

# Check routing in your React app
grep "AdminDashboard\|/dashboard" src/index.jsx
```

---

## 🎉 Success Criteria

Deployment is successful when:

✅ `alembic current` shows version 008
✅ `psql ... SELECT * FROM feature_toggles;` shows 5 rows
✅ `curl /api/ai/wave02/features/all` returns feature list
✅ Admin dashboard loads at `/dashboard`
✅ Toggle buttons work (enable/disable features)
✅ Changes persist in database

---

## 📧 Support

If you encounter issues:
1. Check the logs: `/var/log/fastapi/app.log`
2. Test database: `psql -U user -d pureleven_crm`
3. Verify file permissions: `ls -la app/ai_service/`
4. Check python packages: `pip list | grep -E "alembic|sqlalchemy"`

---

**Version**: Wave 0.2 Complete
**Date**: June 2024
**Status**: Ready for Production ✅
