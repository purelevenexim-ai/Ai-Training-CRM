# Sprint 0 — Final Implementation Checklist ✅

**Status:** Architecture locked. Approved to begin.  
**Timeline:** 4 days  
**Risk Level:** Low (validated data)

---

## Architecture Lock (NO OPTIONS)

```
crm_customers, crm_orders, crm_events
        ↓
Repositories (CustomerRepository, OrderRepository, EventRepository)
        ↓
Customer360Service
        ↓
/360 endpoint (with customer_health + recent_activity_count)
/timeline endpoint
        ↓
UI (if exists)
```

**Non-negotiable:** No new tables, no duplicates, no sync layer.

---

## Pre-Deployment Technical Check

### CRITICAL: Nginx Routing Issue

Currently returns HTTP 000 (timeout). Before deployment:

```bash
# SSH to VPS and run:
ssh root@192.46.213.140

# Check Docker containers
docker ps

# Test FastAPI directly
curl localhost:8000/api/health
curl localhost:8080/api/health

# Validate Nginx config
nginx -t

# Check Nginx logs
tail -50 /var/log/nginx/error.log
tail -50 /var/log/nginx/access.log

# Restart if needed
systemctl restart nginx
docker restart pureleven-ai-engine
```

**Determine:**
- [ ] Is Nginx running? (ps aux | grep nginx)
- [ ] Is FastAPI responding on localhost:8000? (curl localhost:8000)
- [ ] Is Nginx config valid? (nginx -t)
- [ ] Is firewall blocking? (sudo ufw status)
- [ ] Is DNS resolving? (nslookup api.pureleven.com)

**Do NOT deploy until this is fixed.**

---

## Day 1: Foundation

### 1. Rewrite customer_profiles.py (1.5 hours)

**File:** `/opt/pureleven/ai-engine/app/routes/customer_profiles.py`

**Current issues:**
- Uses SQLite (broken)
- References non-existent tables
- Missing PostgreSQL integration

**Action:** Rewrite to use PostgreSQL + SQLAlchemy models from crm_models.py

**Keep existing patterns:**
- Use `Depends(get_db)` for database
- Use `_require_admin(admin_secret)` for authentication
- Follow existing endpoint naming conventions

---

### 2. Create Repository Layer (2 hours)

**New files:**
```
/opt/pureleven/ai-engine/app/repositories/
├── __init__.py
├── base.py (optional base class)
├── customer_repository.py
├── order_repository.py
└── event_repository.py
```

**CustomerRepository methods:**
```python
def get_by_id(customer_id: str) -> Customer
def get_by_email(email: str) -> Customer
def get_all() -> List[Customer]
```

**OrderRepository methods:**
```python
def get_by_customer_id(customer_id: str) -> List[Order]
def get_revenue_for_customer(customer_id: str) -> float
def get_latest_order(customer_id: str) -> Order
def get_order_count(customer_id: str) -> int
```

**EventRepository methods:**
```python
def get_linked_events(customer_id: str, limit: int) -> List[Event]
def get_recent_events(customer_id: str, hours: int = 24) -> List[Event]
def get_event_count(customer_id: str) -> int
```

**Benefits:**
- Clean separation between data access and business logic
- Easy to add messages/segments in Sprint 1 (just add MessageRepository, SegmentRepository)
- Testable without API layer
- Reusable across endpoints

---

### 3. Create Customer360Service (1 hour)

**New file:** `/opt/pureleven/ai-engine/app/services/customer360_service.py`

```python
class Customer360Service:
    def __init__(self, 
                 customer_repo: CustomerRepository,
                 order_repo: OrderRepository,
                 event_repo: EventRepository):
        self.customer_repo = customer_repo
        self.order_repo = order_repo
        self.event_repo = event_repo
    
    def get_customer_360_profile(self, customer_id: str):
        """Build complete customer profile with stats and health."""
        customer = self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise NotFound("Customer not found")
        
        orders = self.order_repo.get_by_customer_id(customer_id)
        recent_events = self.event_repo.get_recent_events(customer_id)
        
        # Calculate metrics
        total_revenue = self.order_repo.get_revenue_for_customer(customer_id)
        order_count = len(orders)
        latest_order = self.order_repo.get_latest_order(customer_id)
        
        # Determine health status
        health_status = "active" if recent_events else "inactive"
        
        return {
            "customer": {
                "id": customer.id,
                "email": customer.email,
                "phone": customer.phone,
                "name": customer.name,
                "created_at": customer.created_at
            },
            "stats": {
                "total_revenue": total_revenue,
                "order_count": order_count,
                "last_order_date": latest_order.order_date if latest_order else None
            },
            "latest_order": {
                "id": latest_order.id,
                "date": latest_order.order_date,
                "amount": latest_order.total_amount,
                "status": latest_order.status
            } if latest_order else None,
            "recent_activity_count": len(recent_events),
            "customer_health": {
                "status": health_status
            }
        }
    
    def get_customer_timeline(self, customer_id: str, limit: int = 50, offset: int = 0):
        """Get merged timeline of orders + linked events."""
        customer = self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise NotFound("Customer not found")
        
        orders = self.order_repo.get_by_customer_id(customer_id)
        events = self.event_repo.get_linked_events(customer_id, limit=limit)
        
        # Merge and sort by date
        timeline = []
        
        for order in orders:
            timeline.append({
                "type": "order",
                "date": order.order_date,
                "description": f"Order #{order.id[:8]} — ₹{order.total_amount}",
                "status": order.status
            })
        
        for event in events:
            timeline.append({
                "type": "event",
                "date": event.timestamp,
                "event_type": event.event_type,
                "description": f"Event: {event.event_type}",
                "source": event.source
            })
        
        # Sort by date DESC
        timeline.sort(key=lambda x: x['date'], reverse=True)
        
        # Apply pagination
        return timeline[offset:offset+limit]
```

**Why this structure:**
- Service orchestrates repositories
- Easy to mock for testing
- Business logic independent of FastAPI
- Clear dependency injection

---

## Day 2: API Endpoints

### 1. Add /360 Endpoint (1.5 hours)

**File:** `/opt/pureleven/ai-engine/app/routes/customers.py`

Add to existing file:

```python
from app.services.customer360_service import Customer360Service
from app.repositories.customer_repository import CustomerRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.event_repository import EventRepository

@router.get('/customers/{customer_id}/360')
async def get_customer_360(
    customer_id: str,
    db: Session = Depends(get_db),
    admin_secret: str = Query(...)
):
    """
    Get complete Customer360 profile with:
    - Customer details
    - Order stats (revenue, count, latest)
    - Recent activity count
    - Health status
    """
    _require_admin(admin_secret)  # Existing auth pattern
    
    # Instantiate repositories
    customer_repo = CustomerRepository(db)
    order_repo = OrderRepository(db)
    event_repo = EventRepository(db)
    
    # Create service and get profile
    service = Customer360Service(customer_repo, order_repo, event_repo)
    
    return service.get_customer_360_profile(customer_id)
```

**Response (from validated data):**
```json
{
  "customer": {
    "id": "573937e0-9479-411a-831f-6...",
    "email": "mirinternationalconsult@gmail.com",
    "phone": "+91...",
    "name": "Customer Name",
    "created_at": "2026-05-19T10:15:00Z"
  },
  "stats": {
    "total_revenue": 1658.00,
    "order_count": 1,
    "last_order_date": "2026-05-11T08:38:55Z"
  },
  "latest_order": {
    "id": "ord-123",
    "date": "2026-05-11T08:38:55Z",
    "amount": 1658.00,
    "status": "delivered"
  },
  "recent_activity_count": 12,
  "customer_health": {
    "status": "active"
  }
}
```

---

### 2. Add /timeline Endpoint (1.5 hours)

**File:** `/opt/pureleven/ai-engine/app/routes/customers.py`

```python
@router.get('/customers/{customer_id}/timeline')
async def get_customer_timeline(
    customer_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin_secret: str = Query(...)
):
    """
    Get merged timeline of customer orders + linked events.
    Sorted by date DESC.
    
    Data sources:
    - crm_orders (all 259 linked)
    - crm_events (146 linked events only, NULL excluded)
    """
    _require_admin(admin_secret)
    
    # Instantiate repositories
    customer_repo = CustomerRepository(db)
    order_repo = OrderRepository(db)
    event_repo = EventRepository(db)
    
    # Create service and get timeline
    service = Customer360Service(customer_repo, order_repo, event_repo)
    
    return {
        "customer_id": customer_id,
        "limit": limit,
        "offset": offset,
        "items": service.get_customer_timeline(customer_id, limit, offset)
    }
```

**Response (from validated data):**
```json
{
  "customer_id": "573937e0-9479-411a-831f-6...",
  "limit": 50,
  "offset": 0,
  "items": [
    {
      "type": "event",
      "date": "2026-05-20T09:20:15Z",
      "event_type": "pl_product_interest",
      "description": "Event: pl_product_interest",
      "source": "ga4"
    },
    {
      "type": "event",
      "date": "2026-05-20T09:16:30Z",
      "event_type": "pl_combo_interest",
      "description": "Event: pl_combo_interest",
      "source": "ga4"
    },
    {
      "type": "order",
      "date": "2026-05-11T08:38:55Z",
      "description": "Order #ord-123 — ₹1658.00",
      "status": "delivered"
    }
  ]
}
```

---

### 3. Add Health Endpoint (30 min)

**File:** `/opt/pureleven/ai-engine/app/routes/monitoring.py` (or health.py if doesn't exist)

```python
@router.get('/health/ciamp')
async def health_ciamp(db: Session = Depends(get_db)):
    """
    Health check for CIAMP (Customer Intelligence & Marketing Platform).
    Validates database connectivity.
    """
    try:
        # Test database connectivity
        db.execute("SELECT 1")
        
        return {
            "status": "ok",
            "service": "ciamp",
            "timestamp": datetime.now().isoformat(),
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "error",
            "service": "ciamp",
            "message": str(e),
            "database": "failed"
        }, 503
```

---

## Day 3: Testing & Validation

### 1. Swagger Testing (1 hour)

**Endpoints to test:**
- [ ] `GET /api/customers/{id}/360?admin_secret=basil`
- [ ] `GET /api/customers/{id}/timeline?admin_secret=basil&limit=20`
- [ ] `GET /api/health/ciamp`

**Use Swagger UI:** `https://api.pureleven.com/docs`

---

### 2. Verify Against Production Data (1 hour)

Use actual customer IDs from production:

```bash
# Get a real customer ID
CUSTOMER_ID="573937e0-9479-411a-831f-6..."

# Test /360
curl -s "https://api.pureleven.com/api/customers/$CUSTOMER_ID/360?admin_secret=basil" | jq .

# Test /timeline
curl -s "https://api.pureleven.com/api/customers/$CUSTOMER_ID/timeline?admin_secret=basil&limit=10" | jq .

# Verify data matches validation results:
# - order_count should match crm_orders join
# - total_revenue should match sum of order amounts
# - recent_events should match crm_events where customer_id IS NOT NULL
```

**Expected results** (from VALIDATION_RESULTS.md):
- Customer 573937e0-...: 1 order, ₹1658.00 revenue, last order 2026-05-11
- All 259 orders should appear in timeline
- All 146 linked events should appear in timeline
- NULL events (page_views, wabis_sent) should NOT appear

---

### 3. Nginx Verification (1 hour)

```bash
# SSH to VPS
ssh root@192.46.213.140

# Run diagnostics
curl -v https://api.pureleven.com/api/health/ciamp
curl -v localhost:8000/api/health/ciamp

# If timeout, debug:
docker ps
docker logs pureleven-ai-engine --tail 50
nginx -t
tail -50 /var/log/nginx/error.log

# Restart if needed
systemctl restart nginx
docker restart pureleven-ai-engine
```

---

## Day 4: Frontend Integration (If UI Exists)

### Determine:
- [ ] Does existing UI have customer detail page?
- [ ] If YES: Integrate /360 and /timeline endpoints
- [ ] If NO: Deployment complete, Swagger is proof-of-concept

---

## Files to Create/Modify

| File | Action | Priority |
|------|--------|----------|
| `repositories/customer_repository.py` | Create | P0 |
| `repositories/order_repository.py` | Create | P0 |
| `repositories/event_repository.py` | Create | P0 |
| `services/customer360_service.py` | Create | P0 |
| `routes/customer_profiles.py` | Rewrite | P0 |
| `routes/customers.py` | Add endpoints | P0 |
| `routes/monitoring.py` | Add health | P0 |

---

## Success Criteria (Data-Backed)

✅ `/360` returns customer + orders + revenue (verified: 573937e0-... = 1 order, ₹1658)

✅ `/timeline` shows 259 orders + 146 linked events (validated count)

✅ No NULL events in timeline (page_views, wabis_sent correctly excluded)

✅ Response time <100ms

✅ No duplicate data

✅ No sync layer needed

✅ Nginx routing works (HTTP 200, not 000)

---

## What NOT to Build (Sprint 0 Exclusions)

❌ Celery workers  
❌ Background jobs  
❌ Webhook idempotency  
❌ Message timeline (7 rows, defer)  
❌ Segment associations (incomplete schema, defer)  
❌ AI scoring  
❌ Lead scoring  
❌ Predictions  
❌ Automation  
❌ WhatsApp intelligence  
❌ Data migrations  
❌ New tables  

**Why:** Validation proves enough value in crm_customers + crm_orders + crm_events to justify Customer360. Everything else is Sprint 1+.

---

## Go/No-Go Decision

✅ **GO**

**Data:** Clean (validated)  
**Architecture:** Locked (approved)  
**Risk:** Low (extension of existing, no new tables)  
**Timeline:** 4 days to production  

**Blocker:** Nginx routing (must verify pre-deployment)

---

## Next Step

Ready to code. Awaiting signal to begin implementation.
