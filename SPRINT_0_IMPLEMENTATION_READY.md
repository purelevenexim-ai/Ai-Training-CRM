# Sprint 0 — IMPLEMENTATION READY ✅

**Date:** 2026-05-25  
**Status:** Validation complete, all data confirmed good  
**Next Step:** Start coding (3-4 days to completion)

---

## Validation Summary (Evidence-Based)

See [VALIDATION_RESULTS.md](VALIDATION_RESULTS.md) for full query outputs.

### Data Quality: GOOD

| Component | Status | Usable | Action |
|-----------|--------|--------|--------|
| crm_orders (259 rows) | ✅ Perfect | 100% | Use immediately |
| crm_events (146 linked) | ✅ Good | 100% | Use immediately |
| crm_events (224 NULL) | ✅ Legitimate | N/A | Ignore (anonymous/automated) |
| crm_customers (3,809 rows) | ✅ Perfect | 100% | Use immediately |
| crm_messages (7 rows) | ⚠️ Minimal | 5% | Defer to Sprint 1 |
| crm_segments | ❌ Incomplete | 0% | Defer to Sprint 2 |

**Key insight:** NULL customer_id in events is NOT a data quality problem. 197 NULL are anonymous page_views, 27 NULL are automated WhatsApp sends. Both legitimate.

---

## Architecture Decision: Customer360Service

Instead of putting all logic in SQL joins, create a dedicated service layer:

```
API Endpoint (/360, /timeline)
        ↓
Customer360Service
    ├── Load customer
    ├── Load orders
    ├── Load linked events
    ├── Calculate metrics
    └── Return DTO
        ↓
Response (JSON)
```

**Benefits:**
- Clean separation of concerns
- Easy to add more data sources (messages, segments post-Sprint 1)
- Testable business logic independent of FastAPI
- Maintainable as requirements evolve

---

## Implementation Plan (NO OPTIONS — DIRECT PATH)

### Day 1: Setup & Fix

**1. Rewrite customer_profiles.py** (2 hours)
- Remove SQLite references
- Rewrite to use PostgreSQL + SQLAlchemy
- Endpoints should map to crm_customers + crm_customer_identities

**2. Create Customer360Service** (2 hours)
```python
# File: /opt/pureleven/ai-engine/app/services/customer360_service.py

class Customer360Service:
    def __init__(self, db_session):
        self.db = db_session
    
    def get_profile(self, customer_id: str):
        # Query crm_customers
        customer = self.db.query(Customer).filter(...).first()
        if not customer:
            raise HTTPException(404, "Customer not found")
        
        # Query orders
        orders = self.db.query(Order).filter(...).all()
        
        # Calculate metrics
        total_revenue = sum(o.total_amount for o in orders)
        order_count = len(orders)
        last_order = max(orders, key=lambda o: o.order_date) if orders else None
        
        return {
            "customer": {...},
            "stats": {
                "total_revenue": total_revenue,
                "order_count": order_count,
                "last_order_date": last_order.order_date if last_order else None
            },
            "latest_order": {...}
        }
    
    def get_timeline(self, customer_id: str, limit: int = 50, offset: int = 0):
        # UNION query: crm_orders + crm_events (where linked)
        # Return sorted by date DESC
        pass
```

---

### Day 2: Implement Endpoints

**1. Add to routes/customers.py** (4 hours)

```python
from app.services.customer360_service import Customer360Service

@router.get('/customers/{customer_id}/360')
async def get_customer_360(
    customer_id: str,
    db: Session = Depends(get_db),
    admin_secret: str = Query(...)
):
    _require_admin(admin_secret)  # Reuse existing auth
    
    service = Customer360Service(db)
    return service.get_profile(customer_id)

@router.get('/customers/{customer_id}/timeline')
async def get_customer_timeline(
    customer_id: str,
    limit: int = Query(50),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    admin_secret: str = Query(...)
):
    _require_admin(admin_secret)
    
    service = Customer360Service(db)
    return service.get_timeline(customer_id, limit, offset)
```

**2. Add health endpoint to routes/monitoring.py** (1 hour)

```python
@router.get('/health/ciamp')
async def health_ciamp(db: Session = Depends(get_db)):
    try:
        # Test DB
        db.execute("SELECT 1")
        
        # Test Redis (if needed later)
        # redis_client.ping()
        
        return {"status": "ok", "timestamp": datetime.now()}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 503
```

---

### Day 3: Test & Deploy

**1. Local testing** (2 hours)
```bash
# Test with sample customer ID from production
curl "https://api.pureleven.com/api/customers/{real_id}/360?admin_secret=basil"
curl "https://api.pureleven.com/api/customers/{real_id}/timeline?admin_secret=basil"
```

**2. Verify data** (1 hour)
- Check response matches production data
- Confirm orders appear with correct amounts
- Confirm 146 linked events appear in timeline
- Verify NULL events are excluded

**3. Deploy** (1 hour)
- Copy files to /opt/pureleven/ai-engine/app/
- Rebuild Docker container (if needed)
- Restart service
- Confirm endpoints are live

---

## Success Checklist (Data-Backed Targets)

- [ ] `curl https://api.pureleven.com/api/health/ciamp` returns 200
- [ ] `GET /360` returns customer + orders + revenue (verified against SQL)
- [ ] `GET /timeline` returns 50 items max, sorted by date DESC
- [ ] Timeline includes 146 linked events (verified in validation)
- [ ] Timeline includes all 259 orders (verified in validation)
- [ ] Response time <100ms
- [ ] No duplicates, no sync issues
- [ ] Ready for Phase 2 (UI integration)

---

## Post-Sprint 0 (Sprint 1+)

### NOT building in Sprint 0 (by design):
- ❌ Celery workers
- ❌ Background jobs
- ❌ Webhook idempotency
- ❌ Message timeline (only 7 rows)
- ❌ Segment associations (incomplete schema)
- ❌ Frontend UI

### Sprint 1 priorities (after Sprint 0):
✅ Add Celery for profile scoring  
✅ Materialize segment membership  
✅ Add messages to timeline (after data fix)  
✅ Begin frontend development  

---

## One Pre-Deployment Check

**Before deploying to production:**

```bash
# SSH to VPS and test Nginx routing manually
curl -I https://api.pureleven.com/api/health

# If times out (HTTP 000):
#   1. Check Nginx config: cat /etc/nginx/sites-enabled/api.pureleven.com
#   2. Restart Nginx: systemctl restart nginx
#   3. Verify FastAPI service: docker logs pureleven-ai-engine
```

---

## Files Summary

| File | Action | Size | Est. Time |
|------|--------|------|-----------|
| `services/customer360_service.py` | Create | 300 lines | 2 hours |
| `routes/customers.py` | Add 2 endpoints | ~100 lines | 2 hours |
| `routes/customer_profiles.py` | Rewrite | 400 lines | 2 hours |
| `routes/monitoring.py` | Add 1 endpoint | 20 lines | 30 min |

**Total implementation time:** ~7 hours (spread across 3 days with testing)

---

## Go / No-Go Decision

✅ **GO** — Data is clean, architecture is sound, risk is low. Start coding.

### Questions resolved:
- ✅ Is crm_orders linked properly? (100% yes)
- ✅ Can we build timeline from existing data? (Yes, 146 linked events)
- ✅ Are NULL events broken? (No, legitimate anonymous/automated)
- ✅ Is architecture sound? (Yes, minimal, extends existing)
- ✅ Can we verify it works? (Yes, tested in SQL)

### Remaining items before code:
- ⚠️ Verify Nginx routing manually (SSH test)
- ⚠️ Confirm frontend exists or plan Swagger-only validation

**Recommendation:** Start coding now. Address Nginx routing in deployment phase if issue found.

