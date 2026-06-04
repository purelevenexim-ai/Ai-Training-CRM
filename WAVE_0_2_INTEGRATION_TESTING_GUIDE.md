# Wave 0.2 Integration Testing Guide - START HERE

## Current Status
✅ **Wave 0.1:** Code complete (6 tables, 5 services, 10 endpoints, 6 React screens)
✅ **Wave 0.2:** Code complete (4 new tables, 2 services, 10 endpoints, 2 React screens)
⏳ **Next:** Integration testing & deployment

---

## Pre-Integration Checklist

Before running migrations, ensure:
- [ ] PostgreSQL running and accessible
- [ ] Alembic initialized in project
- [ ] Database connection string in environment
- [ ] Python virtual environment active
- [ ] Git repository clean (no uncommitted changes)

```bash
# Verify setup
cd /Users/bthomas/Documents/pureleven_dev
psql -U your_user -d pureleven_crm -c "SELECT version();"  # Check DB
alembic current                                              # Check Alembic
python -c "import sqlalchemy; print(sqlalchemy.__version__)" # Check SQLAlchemy
```

---

## Phase 1: Database Migration (30 minutes)

### Step 1: Run Wave 0.1 Migration (if not done)
```bash
cd /Users/bthomas/Documents/pureleven_dev

# Check which migration is currently applied
alembic current
# Expected output: 006_ai_crm_v1_core_tables (or similar)

# If not at 006, upgrade to it
alembic upgrade 006
```

### Step 2: Run Wave 0.2 Migration
```bash
# Apply Wave 0.2 tables
alembic upgrade 007

# Verify tables created
psql -U your_user -d pureleven_crm -c "\dt ai_review_queue ai_recommendation ai_logs"

# Expected output:
#              List of relations
#  Schema |        Name        | Type  | Owner
# --------+--------------------+-------+-------
#  public | ai_review_queue    | table | user
#  public | manual_training... | table | user
#  public | kb_performance     | table | user
#  public | response_quality..| table | user
```

### Step 3: Verify Schema
```bash
# Check ai_review_queue structure
psql -U your_user -d pureleven_crm -c "\d ai_review_queue"

# Expected columns:
#  queue_id              | character varying(36) | primary key
#  conversation_id       | character varying(36) | 
#  customer_id           | character varying(36) | 
#  customer_message      | text                  |
#  detected_intent       | character varying(50) |
#  intent_confidence     | double precision      |
#  detected_language     | character varying(20) |
#  ai_response           | text                  |
#  review_status         | character varying(20) | default: pending
#  human_intent_correction | varchar(50)        |
#  human_notes           | text                  |
#  should_add_to_kb      | boolean              | default: false
#  kb_category           | character varying(50) |
#  created_at            | timestamp            | indexed
#  reviewed_at           | timestamp            |
#  reviewed_by           | character varying(100)|
```

---

## Phase 2: Verify Python Models (15 minutes)

### Step 1: Check Models Import
```bash
cd /Users/bthomas/Documents/pureleven_dev
python3 -c "from crm_models import AIReviewQueue, ManualTrainingExample, KBPerformance, ResponseQualityFeedback; print('✅ All models import successfully')"
```

**If error:** Check that all 4 new models are in `crm_models.py` with proper import at top:
```python
from uuid import uuid4
from datetime import datetime
```

### Step 2: Verify Services Import
```bash
python3 -c "from app.ai_service.review_queue_service import ReviewQueueService; print('✅ ReviewQueueService imports')"
python3 -c "from app.ai_service.learning_engine import LearningEngine; print('✅ LearningEngine imports')"
```

**If error:** Ensure both service files exist:
- `/app/ai_service/review_queue_service.py` (260 lines)
- `/app/ai_service/learning_engine.py` (240 lines)

### Step 3: Verify Routes Registration
```bash
python3 -c "from app.routes.review_routes import router; print(f'✅ Review routes registered: {len(router.routes)} endpoints')"
```

**Expected output:** `✅ Review routes registered: 10 endpoints`

---

## Phase 3: Start Server & Test API (45 minutes)

### Step 1: Start FastAPI Server
```bash
# Terminal 1: Start server
cd /Users/bthomas/Documents/pureleven_dev
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

### Step 2: Open Swagger API Docs
```bash
# In browser: http://localhost:8000/docs
# You should see:
#   - Green "Authorize" button (for auth tokens)
#   - /api/ai/* endpoints (Wave 0.1)
#   - /api/ai/review/* endpoints (Wave 0.2) ← NEW
```

### Step 3: Test Wave 0.1 Endpoints (Sanity Check)

**Test 1: POST /api/ai/sandbox/test**
```bash
curl -X POST "http://localhost:8000/api/ai/sandbox/test" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How much is black pepper?",
    "language": "english"
  }'

# Expected response (200 OK):
# {
#   "message": "How much is black pepper?",
#   "detected_language": "english",
#   "language_confidence": 0.95,
#   "detected_intent": "PRICE_INQUIRY",
#   "intent_confidence": 0.87,
#   "detection_method": "rule_engine",
#   "sample_response": "Black Pepper prices...",
#   "context_available": {
#     "products": 12,
#     "kb_matches": 3
#   }
# }
```

**Test 2: GET /api/ai/customers?limit=10**
```bash
curl "http://localhost:8000/api/ai/customers?limit=10"

# Expected: 200 OK with customer list (may be empty if no customers yet)
```

### Step 4: Test Wave 0.2 Endpoints

**Test 1: GET /api/ai/review/stats**
```bash
curl "http://localhost:8000/api/ai/review/stats"

# Expected response (200 OK):
# {
#   "pending": 0,
#   "approved": 0,
#   "reclassified": 0,
#   "total_training_examples": 0,
#   "learning_accuracy_improvement": "0%"
# }
```

**Test 2: GET /api/ai/review/learning/progress**
```bash
curl "http://localhost:8000/api/ai/review/learning/progress"

# Expected response (200 OK):
# {
#   "total_training_examples": 0,
#   "reclassified_from_reviews": 0,
#   "base_accuracy": 65,
#   "estimated_current_accuracy": 65,
#   "learning_progress_pct": 0,
#   "next_milestone": "72%"
# }
```

**Test 3: GET /api/ai/review/pending**
```bash
curl "http://localhost:8000/api/ai/review/pending?limit=10"

# Expected response (200 OK):
# {
#   "count": 0,
#   "reviews": []
# }
# (Empty because no low-confidence messages added yet)
```

**Test 4: GET /api/ai/review/daily-summary**
```bash
curl "http://localhost:8000/api/ai/review/daily-summary"

# Expected response (200 OK):
# {
#   "date": "2024-08-01",
#   "pending_count": 0,
#   "pending_samples": [],
#   "review_stats": { ... },
#   "learning_progress": { ... }
# }
```

---

## Phase 4: Frontend Integration (1 hour)

### Step 1: Identify React File Locations
```bash
# Check that new screens exist
ls -la src/components/AICenter/

# Expected files:
#   AIReviewQueue.jsx          ← NEW
#   LearningProgress.jsx       ← NEW
#   Dashboard.jsx              (exists)
#   Customers.jsx              (exists)
#   Conversations.jsx          (exists)
#   ProductCatalog.jsx         (exists)
#   KnowledgeBase.jsx          (exists)
#   AISandbox.jsx              (exists)
```

### Step 2: Add Screens to Navigation
**Edit `src/components/AICenter/index.jsx`:**

Find the screens array and add Wave 0.2 screens:
```javascript
const screens = [
  { id: 'dashboard', label: 'Dashboard', icon: '📊' },
  { id: 'customers', label: 'Customers', icon: '👥' },
  { id: 'conversations', label: 'Conversations', icon: '💬' },
  { id: 'review-queue', label: 'Review Queue', icon: '📋' },        // ← ADD
  { id: 'learning', label: 'Learning Progress', icon: '📈' },       // ← ADD
  { id: 'products', label: 'Products', icon: '🛒' },
  { id: 'knowledge', label: 'Knowledge Base', icon: '📚' },
  { id: 'sandbox', label: 'Sandbox', icon: '🔬' },
];
```

Then add rendering logic:
```javascript
import AIReviewQueue from './AIReviewQueue';
import LearningProgress from './LearningProgress';

// In the render switch:
case 'review-queue':
  return <AIReviewQueue />;
case 'learning':
  return <LearningProgress />;
```

### Step 3: Test UI Navigation
1. Open the app: http://localhost:3000 (or your React dev server)
2. Navigate to AICenter
3. Click "Review Queue" → Should see empty review list with message "All caught up!"
4. Click "Learning Progress" → Should see 65% accuracy, 0 examples

If UI appears:
- ✅ Screen loads correctly
- ✅ State management works
- ✅ API calls functioning

### Step 4: Test Review Workflow (Simulated)

**Manually add test review to database:**
```bash
# Open PostgreSQL
psql -U your_user -d pureleven_crm

# Insert test review
INSERT INTO ai_review_queue (
  queue_id, customer_id, customer_message, 
  detected_intent, intent_confidence, 
  detected_language, ai_response, review_status, created_at
) VALUES (
  'test-review-001',
  (SELECT id FROM crm_customers LIMIT 1),
  'Do you have cardamom in bulk?',
  'PRICE_INQUIRY',
  0.68,
  'english',
  'Yes, we have bulk cardamom available...',
  'pending',
  NOW()
);
```

Then refresh UI:
- [ ] Review appears in list
- [ ] Click on it → Detail panel shows
- [ ] Can approve/correct/escalate

**Test Approval:**
```javascript
// Use browser console to test API
fetch('/api/ai/review/approve', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    queue_id: 'test-review-001',
    approved_intent: 'BULK_INQUIRY',
    add_to_kb: false,
    notes: 'Test approval'
  })
}).then(r => r.json()).then(console.log)
```

Expected: Success response with status "approved" or "reclassified"

---

## Phase 5: Verify Wave 0.1 + 0.2 Integration

### Test Complete Flow: Message → Review Queue → Learning

**Step 1: Create test customer (if needed)**
```bash
# In PostgreSQL:
INSERT INTO crm_customers (id, phone, email, full_name) 
VALUES ('cust-test-001', '+919123456789', 'test@example.com', 'Test Customer')
```

**Step 2: Send low-confidence message to review queue**
```bash
# Via API (simulating Wabis webhook with low confidence)
curl -X POST "http://localhost:8000/api/ai/webhook/wabis" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust-test-001",
    "message": "What about your cardamom?",
    "phone": "+919123456789",
    "language": "english"
  }'

# This should:
# 1. Detect language: english
# 2. Detect intent: PRICE_INQUIRY (confidence 0.85 - high)
# 3. NOT flag to review queue (confidence > 0.70)

# To test review queue, send intentionally ambiguous message:
curl -X POST "http://localhost:8000/api/ai/webhook/wabis" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust-test-001",
    "message": "എനിക്ക് വേണ്ടത് എന്ത് പറയാം",
    "phone": "+919123456789",
    "language": "malayalam"
  }'

# This will:
# 1. Detect language: malayalam (high confidence)
# 2. Try to detect intent (may be low confidence)
# 3. If confidence < 0.70 → Flag to ai_review_queue
```

**Step 3: Check review queue**
```bash
curl "http://localhost:8000/api/ai/review/pending?limit=10"

# Should return any flagged messages
```

**Step 4: Approve with intent correction**
```bash
curl -X POST "http://localhost:8000/api/ai/review/approve" \
  -H "Content-Type: application/json" \
  -d '{
    "queue_id": "YOUR_QUEUE_ID_FROM_PENDING",
    "approved_intent": "GENERAL",
    "add_to_kb": false,
    "notes": "This was ambiguous Malayalam"
  }'

# Should return success
```

**Step 5: Check learning progress**
```bash
curl "http://localhost:8000/api/ai/review/learning/progress"

# Should now show:
# {
#   "total_training_examples": 1,
#   "reclassified_from_reviews": 1,
#   "base_accuracy": 65,
#   "estimated_current_accuracy": 66,  # Up by 1%
#   "learning_progress_pct": 5,
# }
```

---

## Phase 6: Load Testing (Optional)

### Simulate 100 Low-Confidence Messages
```python
# Create test_wave_0_2.py

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_review_queue_load():
    """Simulate 100 messages, expect ~35 in review queue"""
    
    # Get first 100 customers
    response = requests.get(f"{BASE_URL}/api/ai/customers?limit=100")
    customers = response.json().get('customers', [])
    
    reviewed = 0
    for i, customer in enumerate(customers[:100]):
        message = f"Test message {i}: {['Do you have', 'How much', 'When can', 'What about'][i % 4]} cardamom?"
        
        response = requests.post(
            f"{BASE_URL}/api/ai/webhook/wabis",
            json={
                "customer_id": customer['customer_id'],
                "message": message,
                "phone": customer.get('phone'),
                "language": "english"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('flagged_for_review'):
                reviewed += 1
        
        if i % 20 == 0:
            print(f"Processed {i}/100 messages...")
        
        time.sleep(0.1)  # Slow down to not spam
    
    # Check final review queue
    response = requests.get(f"{BASE_URL}/api/ai/review/stats")
    stats = response.json()
    
    print(f"\n✅ Load Test Complete:")
    print(f"   Messages processed: 100")
    print(f"   Pending reviews: {stats['pending']} (expected ~35)")
    print(f"   Approved: {stats['approved']}")
    print(f"   Reclassified: {stats['reclassified']}")

if __name__ == "__main__":
    test_review_queue_load()
```

Run it:
```bash
python test_wave_0_2.py
```

Expected: ~35 messages in review queue, ~65 handled by rule engine

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'app.ai_service.review_queue_service'"
**Solution:** Ensure file exists at correct path:
```bash
ls -la app/ai_service/review_queue_service.py
# If missing, create it from the specification above
```

### Issue: "Relation 'ai_review_queue' does not exist"
**Solution:** Run migration:
```bash
alembic upgrade 007
psql -U your_user -d pureleven_crm -c "\dt ai_review_queue"
```

### Issue: API returns 404 for `/api/ai/review/pending`
**Solution:** Ensure review_router is registered in main.py:
```bash
grep "review_router" main.py
# Should show: app.include_router(review_router)
```

### Issue: React component doesn't appear
**Solution:** Check that it's imported and added to screens array in `AICenter/index.jsx`
```bash
grep "AIReviewQueue" src/components/AICenter/index.jsx
```

---

## Deployment Checklist

After all tests pass:

```
Database:
☐ Alembic migration 007 applied
☐ All 4 new tables created
☐ Verify schema matches specification

Backend:
☐ All 2 services created (review_queue, learning_engine)
☐ All 4 SQLAlchemy models added to crm_models.py
☐ All 10 API endpoints working
☐ review_router registered in main.py
☐ No import errors on startup

Frontend:
☐ AIReviewQueue.jsx created
☐ LearningProgress.jsx created
☐ Both screens added to AICenter navigation
☐ UI responsive and interactive

Integration:
☐ Wave 0.1 + Wave 0.2 work together
☐ Low-confidence messages auto-flagged
☐ Approval workflow tested
☐ Learning progress tracks correctly

API Tests:
☐ All 10 /api/ai/review/* endpoints respond
☐ Database operations (create/read/update) working
☐ Error handling returns 5xx on failures

Load:
☐ 100 messages processed without errors
☐ Review queue fills as expected (~35%)
☐ Response times < 500ms per request

Ready for Production:
☐ All tests passing
☐ No console errors
☐ Database backed up before going live
☐ Team notified of new features
```

---

## Next Steps After Integration Testing

### Option A: Start Wave 0.2 Active Learning (Recommended)
```
1. Spend 2h/day reviewing 50 pending messages
2. Correct intents that rule engine missed
3. Watch learning progress increase 65% → 72%+
4. Takes 2-3 weeks of active learning
5. Then proceed to Wave 1
```

### Option B: Proceed Directly to Wave 1 (Speed)
```
1. Skip manual learning phase
2. Deploy Wave 1 with 65% accuracy (acceptable)
3. Learn automatically from user feedback in Wave 1
4. Faster to market but higher Gemini API costs early on
```

**Recommendation:** Choose Option A for better accuracy and cost control.

---

## Support

If you encounter issues:
1. Check the **Troubleshooting** section above
2. Review `/memories/repo/` for known pitfalls
3. Check application logs: `tail -f logs/app.log`
4. Test individual API endpoints manually first
5. Verify database schema matches migration
