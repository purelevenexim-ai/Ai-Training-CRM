# ⚡ Wave 0.2 Deployment Quick Card

## 🚀 3-Step Deployment

### Step 1: Copy Files (5 min)
```bash
# From local pureleven_dev folder
scp -r app/ai_service/*.py user@live:/app/ai_service/
scp app/routes/wave02_routes.py user@live:/app/routes/
scp alembic/versions/008_*.py user@live:/alembic/versions/
scp src/components/AdminDashboard.jsx user@live:/src/components/
scp main.py user@live:/app/
scp deploy_wave_0_2.sh user@live:/app/
```

### Step 2: Deploy (10 min)
```bash
# SSH into live server
ssh user@live

# Run automated deployment
cd /app
bash deploy_wave_0_2.sh

# Provide database credentials when prompted
```

### Step 3: Verify (5 min)
```bash
# Check endpoints
curl https://your-domain/api/ai/wave02/features/all

# Open admin dashboard
https://your-domain/dashboard
```

---

## 📊 What Gets Deployed

| Component | Files | Purpose |
|-----------|-------|---------|
| Backend | 3 Python files | Advanced scoring, KB org, feature toggles |
| API | wave02_routes.py | 21 new endpoints |
| Database | 008 migration | New tables + columns |
| Frontend | AdminDashboard.jsx | Toggle UI + KPIs |
| Deployment | 2 scripts | Automated deployment + manual guide |

---

## 🎮 5 Features You Can Now Control

| Feature | Default | Toggle Off For |
|---------|---------|----------------|
| Daily Review Queue | ON | Skipping reviews |
| Learning Engine | ON | Testing rules only |
| Advanced Scoring | ON | Basic mode |
| KB Organization | ON | Disabling KB tracking |
| Wave 1 - Product Affinity | OFF | Enabling future features |

---

## 📍 Key Paths & URLs

| Item | Path/URL |
|------|----------|
| Admin Dashboard | https://your-domain/dashboard |
| Features API | https://your-domain/api/ai/wave02/features/all |
| Dashboard API | https://your-domain/api/ai/wave02/dashboard/summary |
| Backup Location | /backups/pureleven_crm_backup_*.sql |
| FastAPI Logs | /var/log/fastapi/app.log |

---

## 🔧 Common Commands (Post-Deployment)

```bash
# Check migration status
alembic current

# List all feature toggles
psql -U user -d pureleven_crm -c "SELECT * FROM feature_toggles;"

# Restart FastAPI
supervisorctl restart fastapi

# View FastAPI logs
tail -f /var/log/fastapi/app.log

# Test API endpoint
curl http://localhost:8000/api/ai/wave02/features/all

# Verify database connection
psql -U user -d pureleven_crm -c "SELECT 1;"
```

---

## ⚠️ Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| `Connection refused` | PostgreSQL not running: `sudo systemctl start postgresql` |
| `ModuleNotFoundError: alembic` | Install: `pip install alembic sqlalchemy` |
| Migration fails | Check DB credentials in `deploy_wave_0_2.sh` |
| API returns 404 | Verify `include_router` in `main.py` |
| Toggles won't save | Check database has `feature_toggles` table |
| Dashboard not loading | Verify `AdminDashboard.jsx` in React routing |

---

## 📋 Pre-Deployment Checklist

- [ ] SSH access to live server verified
- [ ] Database credentials collected
- [ ] PostgreSQL running on live server
- [ ] FastAPI running on live server
- [ ] All 6 files copied
- [ ] `deploy_wave_0_2.sh` is executable (`chmod +x`)
- [ ] Backup location accessible
- [ ] 30 min of downtime allowed (if needed)

---

## ✅ Post-Deployment Checklist

- [ ] Migration shows version 008 (`alembic current`)
- [ ] 5 toggles in database
- [ ] API responding with HTTP 200
- [ ] Dashboard page loads
- [ ] Toggle buttons work
- [ ] Changes persist on refresh
- [ ] FastAPI logs show no errors
- [ ] All team members can access dashboard

---

## 🔙 Rollback Quick Commands

```bash
# Option A: Downgrade migration (fast, safe)
cd /app
alembic downgrade 007
supervisorctl restart fastapi

# Option B: Restore database from backup
psql -U user -d pureleven_crm < /backups/pureleven_crm_backup_YYYYMMDD_HHMMSS.sql
supervisorctl restart fastapi
```

---

## 📞 Emergency Contacts

| Issue | Check |
|-------|-------|
| API not responding | `/var/log/fastapi/app.log` |
| Database issues | `psql -U user -d pureleven_crm -c "SELECT 1;"` |
| Migration failed | `alembic current` and `alembic history` |
| Features not loading | Browser console logs + `/api/admin/health` |

---

## 🎯 Success = All Green ✓

```
✓ Migration version 008 running
✓ 5 feature toggles in database
✓ All 21 API endpoints responding
✓ Admin dashboard loads
✓ Toggle buttons are clickable
✓ Toggle changes persist
✓ No errors in FastAPI logs
✓ Team can access dashboard
```

---

## 📞 Key Support Files

| File | Purpose | Location |
|------|---------|----------|
| Full Guide | Detailed steps | WAVE_0_2_DEPLOYMENT_GUIDE.md |
| Delivery Summary | What's included | WAVE_0_2_FINAL_DELIVERY.md |
| Quick Card | This file! | WAVE_0_2_QUICK_CARD.md |
| Script | Auto deployment | deploy_wave_0_2.sh |

---

## 💡 Pro Tips

1. **Always backup first** - It only takes 2 minutes
2. **Use deployment script** - It handles edge cases
3. **Monitor logs after** - Check first hour for errors
4. **Test toggles gently** - Try one at a time first
5. **Keep dashboard open** - Pin in browser for quick access

---

**Estimated Total Time**: 20-30 minutes
**Risk Level**: Low (easy rollback)
**Go-Live Confidence**: High ✅

**You've got this! 🚀**
