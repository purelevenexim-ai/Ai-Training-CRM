# Phase 4-5 Implementation Roadmap

**Status:** ✅ All services built | 🔄 Integration pending  
**Last Updated:** 2026-05-19  

---

## 📊 Phase 4: Integrations & Scaling

### Phase 4.1: AWS SES Email Integration (2-3 hours)

**What was built:**
- `backend/email_service.py` - Complete AWS SES wrapper

**Integration Steps:**

#### Step 1: Set AWS Credentials

```bash
# SSH to VPS
ssh root@192.46.213.140

# Update .env file with AWS credentials
vi /opt/pureleven/ai-engine/.env
```

Add these lines:
```env
AWS_SES_REGION=us-east-1
AWS_SES_ACCESS_KEY_ID=AKIA...
AWS_SES_SECRET_ACCESS_KEY=...
SES_FROM_EMAIL=noreply@pureleven.com
SES_CONFIGURATION_SET=pureleven-prod
```

#### Step 2: Copy email_service.py to Backend

```bash
scp -o StrictHostKeyChecking=no \
  /Users/bthomas/Documents/pureleven_dev/backend/email_service.py \
  root@192.46.213.140:/opt/pureleven/ai-engine/app/
```

#### Step 3: Update crm_routes.py to use SES

**File:** `backend/crm_routes.py`

Find the N8N workflow trigger function and update it:

```python
# OLD (using Plunk):
# response = await plunk_client.send_email(...)

# NEW (using AWS SES):
from email_service import get_ses_service

@router.post("/journey-steps/{step_id}/log")
async def log_journey_step(step_id: str, log_data: dict):
    # ... existing code ...
    
    if step_data['type'] == 'email':
        ses = get_ses_service()
        email_result = await ses.send_templated_email(
            to_email=customer.email,
            template_name=step_data.get('template_id'),
            template_data={
                'customer_name': customer.name,
                'journey_name': journey.name,
                # ... other data ...
            },
            tags=['journey', journey.id, 'step', step_id]
        )
        log_data['email_status'] = email_result.get('status')
```

#### Step 4: Test Email Sending

```bash
# SSH to VPS
ssh root@192.46.213.140

# Test SES configuration
docker exec pureleven-ai-engine python3 -c "
from app.email_service import get_ses_service
ses = get_ses_service()
result = ses.send_email(
    to_email='test@pureleven.com',
    subject='Test from Pure Leven',
    html_body='<p>Testing AWS SES integration</p>'
)
print('Result:', result)
"
```

---

### Phase 4.2: Meta & Google Audience Sync (2-3 hours)

**What was built:**
- `backend/meta_audience_sync.py` - Meta Custom Audience
- `backend/google_audience_sync.py` - Google Customer Match

**Integration Steps:**

#### Step 1: Copy Services to Backend

```bash
scp -o StrictHostKeyChecking=no \
  /Users/bthomas/Documents/pureleven_dev/backend/meta_audience_sync.py \
  /Users/bthomas/Documents/pureleven_dev/backend/google_audience_sync.py \
  root@192.46.213.140:/opt/pureleven/ai-engine/app/
```

#### Step 2: Add API Credentials to .env

```env
# Meta (Pure Leven account: 237007475595482)
FACEBOOK_ACCESS_TOKEN=EAABSBZC...
FACEBOOK_APP_ID=3434...
FACEBOOK_APP_SECRET=...
FACEBOOK_ACCOUNT_ID=237007475595482

# Google Ads (Pure Leven account: 7225234563)
GOOGLE_ADS_DEVELOPER_TOKEN=abc...
GOOGLE_ADS_CLIENT_ID=...@developer.gserviceaccount.com
GOOGLE_ADS_CLIENT_SECRET=...
GOOGLE_ADS_CUSTOMER_ID=7225234563
GOOGLE_ADS_REFRESH_TOKEN=...
```

#### Step 3: Update enrollCustomerInJourney to Sync Audiences

**File:** `backend/crm_routes.py`

```python
from meta_audience_sync import MetaAudienceSync
from google_audience_sync import GoogleAudienceSync
from sqlalchemy.orm import Session

@router.post("/customers/{customer_id}/journeys/{journey_id}/enroll")
async def enroll_customer_in_journey(
    customer_id: str,
    journey_id: str,
    db: Session
):
    # ... existing enrollment code ...
    
    # Get journey details
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    
    # Check if journey has audience nodes
    template = json.loads(journey.template_json)
    
    for node in template.get('nodes', []):
        if node['type'] == 'meta_audience':
            # Sync to Meta
            meta_sync = MetaAudienceSync(db)
            meta_sync.sync_customers_to_audience(
                audience_id=node['audience_id'],
                customers=[{
                    'email': customer.email,
                    'phone': customer.phone_number,
                }],
                sync_type='add',
                fields=['em', 'ph']  # email, phone hashed
            )
        
        elif node['type'] == 'google_audience':
            # Sync to Google
            google_sync = GoogleAudienceSync(db)
            google_sync.sync_customers_to_audience(
                customer_list_id=node['customer_list_id'],
                customers=[{
                    'email': customer.email,
                    'phone': customer.phone_number,
                }],
                sync_type='add',
                fields=['email', 'phone']
            )
    
    return {'status': 'enrolled', 'synced': True}
```

#### Step 4: Test Audience Sync

```bash
# Manually test Meta sync
curl -X POST https://track.pureleven.com/api/crm/customers/test-id/journeys/test-journey/enroll \
  -H "Content-Type: application/json"

# Check Meta Ads Manager to verify audience size increased
# https://adsmanager.facebook.com/ → Audiences → Look for Pure Leven audience
```

---

### Phase 4.3: ROAS Attribution Pipeline (2-3 hours)

**What was built:**
- `backend/attribution_service.py` - 3 attribution models

**Integration Steps:**

#### Step 1: Create Database Tables

```bash
# SSH to VPS
ssh root@192.46.213.140

# Add migration for JourneyAttribution table
docker exec pureleven-ai-engine python3 << 'EOF'
# Run in alembic
# Create migration: alembic revision --autogenerate -m "Add JourneyAttribution table"
# Edit migration to add:

class Migration:
    def upgrade():
        op.create_table(
            'journey_attribution',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('journey_id', sa.String(36), sa.ForeignKey('journeys.id')),
            sa.Column('journey_instance_id', sa.String(36), sa.ForeignKey('journey_instances.id')),
            sa.Column('customer_id', sa.String(36), sa.ForeignKey('customers.id')),
            sa.Column('order_id', sa.String(100)),
            sa.Column('order_value', sa.Float),
            sa.Column('currency', sa.String(3)),
            sa.Column('attributed_revenue', sa.Float),
            sa.Column('attribution_model', sa.String(20)),  # first_touch, last_touch, multi_touch
            sa.Column('conversion_date', sa.DateTime),
            sa.Column('created_at', sa.DateTime),
        )
        op.create_index('ix_journey_attribution_customer', 'journey_attribution', ['customer_id'])
        op.create_index('ix_journey_attribution_order', 'journey_attribution', ['order_id'])
EOF
```

#### Step 2: Copy attribution_service.py

```bash
scp -o StrictHostKeyChecking=no \
  /Users/bthomas/Documents/pureleven_dev/backend/attribution_service.py \
  root@192.46.213.140:/opt/pureleven/ai-engine/app/
```

#### Step 3: Hook to Shopify Order Webhook

**File:** `backend/crm_routes.py`

```python
from attribution_service import AttributionService

@router.post("/webhooks/shopify/order/create")
async def on_shopify_order_created(webhook_data: dict, db: Session):
    """
    Called by Shopify when order is created
    Backtracks active journeys for customer and attributes revenue
    """
    order_id = webhook_data.get('id')
    customer_email = webhook_data.get('customer', {}).get('email')
    order_value = float(webhook_data.get('total_price', 0))
    currency = webhook_data.get('currency', 'INR')
    
    # Get customer
    customer = db.query(Customer).filter(Customer.email == customer_email).first()
    if not customer:
        return {'status': 'customer_not_found'}
    
    # Run attribution backtracking
    attribution_svc = AttributionService(db)
    result = attribution_svc.backtrack_attributions(
        customer_id=customer.id,
        order_id=order_id,
        order_value=order_value,
        currency=currency,
        model='multi_touch',  # Split credit among active journeys
        lookback_days=30  # Look at last 30 days of active journeys
    )
    
    return result
```

#### Step 4: Configure Shopify Webhook

1. **Go to:** Shopify Admin → Settings → Apps and integrations → Webhooks
2. **Add webhook:**
   - Event: Order → Created
   - URL: `https://track.pureleven.com/api/crm/webhooks/shopify/order/create`
   - API version: Latest

3. **Test webhook:**
   ```bash
   # Create test order in Shopify
   # Check backend logs for webhook receipt
   docker logs -f pureleven-ai-engine | grep "Shopify"
   ```

#### Step 5: Query Attribution Data

```python
# Get ROAS for a journey
attribution_svc = AttributionService(db)
stats = attribution_svc.get_journey_attribution_stats(journey_id='test-id')
print(f"Revenue: ${stats['total_revenue']}")
print(f"Conversions: {stats['conversion_count']}")
print(f"ROAS: {stats['roas']}")
```

---

## 📊 Phase 5: Advanced UX & Testing

### Phase 5.1: A/B Testing Framework (1-2 hours)

**What was built:**
- `backend/ab_testing_service.py` - ABTestingService class

**Integration Steps:**

#### Step 1: Create JourneyVariant Table

```python
# In crm_models.py, add:

class JourneyVariant(Base):
    __tablename__ = 'journey_variants'
    
    id = Column(String(36), primary_key=True)
    journey_id = Column(String(36), ForeignKey('journeys.id'))
    name = Column(String(255))
    template_json = Column(JSON)  # Different template per variant
    traffic_split_percent = Column(Integer, default=50)
    config_changes = Column(JSON)  # Delta from base
    status = Column(String(20))  # draft, active, paused, winner
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Run migration
alembic revision --autogenerate -m "Add JourneyVariant table"
alembic upgrade head
```

#### Step 2: Copy ab_testing_service.py

```bash
scp -o StrictHostKeyChecking=no \
  /Users/bthomas/Documents/pureleven_dev/backend/ab_testing_service.py \
  root@192.46.213.140:/opt/pureleven/ai-engine/app/
```

#### Step 3: Create Frontend UI for A/B Testing

**File:** `src/components/VariantBuilder.jsx`

```jsx
import React, { useState } from 'react';
import useCrmStore from '../crmStore';

export const VariantBuilder = ({ journeyId }) => {
  const [variantName, setVariantName] = useState('');
  const [trafficSplit, setTrafficSplit] = useState(50);
  
  const handleCreateVariant = async () => {
    // Call API to create variant
    const response = await fetch(
      `/api/crm/journeys/${journeyId}/variants`,
      {
        method: 'POST',
        body: JSON.stringify({
          name: variantName,
          traffic_split_percent: trafficSplit,
        })
      }
    );
    const data = await response.json();
    console.log('Variant created:', data);
  };
  
  return (
    <div>
      <h3>Create A/B Test Variant</h3>
      <input 
        value={variantName}
        onChange={(e) => setVariantName(e.target.value)}
        placeholder="e.g., Subject Line B"
      />
      <div>
        <label>Traffic Split: {trafficSplit}%</label>
        <input 
          type="range"
          min={10}
          max={90}
          value={trafficSplit}
          onChange={(e) => setTrafficSplit(parseInt(e.target.value))}
        />
      </div>
      <button onClick={handleCreateVariant}>Create Variant</button>
    </div>
  );
};
```

---

### Phase 5.2: Journey Cloning (30 min)

**What was built:**
- JourneyCloneService in ab_testing_service.py

**Integration:**

```python
# In crm_routes.py:
from ab_testing_service import JourneyCloneService

@router.post("/journeys/{journey_id}/clone")
async def clone_journey(journey_id: str, clone_name: str, db: Session):
    clone_svc = JourneyCloneService(db)
    result = clone_svc.clone_journey(journey_id, clone_name)
    return result
```

---

### Phase 5.3: Bulk Enrollment (1-2 hours)

**What was built:**
- BulkEnrollmentService in ab_testing_service.py

**Integration Steps:**

#### Step 1: Create BulkEnrollmentJob Table

```python
# In crm_models.py:
class BulkEnrollmentJob(Base):
    __tablename__ = 'bulk_enrollment_jobs'
    
    id = Column(String(36), primary_key=True)
    journey_id = Column(String(36), ForeignKey('journeys.id'))
    total_count = Column(Integer)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    status = Column(String(20))  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
```

#### Step 2: Create Frontend Upload Component

**File:** `src/components/BulkEnrollmentWizard.jsx`

```jsx
import React, { useState } from 'react';

export const BulkEnrollmentWizard = ({ journeyId }) => {
  const [csvFile, setCsvFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  
  const handleUpload = async () => {
    setUploading(true);
    
    const reader = new FileReader();
    reader.onload = async (e) => {
      const csv = e.target.result;
      
      // Upload CSV
      const response = await fetch(
        `/api/crm/journeys/${journeyId}/enroll-bulk`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'text/csv' },
          body: csv
        }
      );
      
      const data = await response.json();
      setResult(data);
      setUploading(false);
    };
    
    reader.readAsText(csvFile);
  };
  
  return (
    <div>
      <h3>Bulk Enrollment</h3>
      <p>Upload CSV with customer_email header</p>
      <input 
        type="file"
        accept=".csv"
        onChange={(e) => setCsvFile(e.target.files[0])}
      />
      <button 
        onClick={handleUpload}
        disabled={uploading || !csvFile}
      >
        {uploading ? 'Uploading...' : 'Upload & Enroll'}
      </button>
      
      {result && (
        <div>
          <p>✅ Success: {result.success_count}</p>
          <p>❌ Errors: {result.error_count}</p>
        </div>
      )}
    </div>
  );
};
```

---

## 🎯 Complete Integration Timeline

| Phase | Component | Time | Status |
|-------|-----------|------|--------|
| 4.1 | AWS SES Email | 2-3h | Code ✅ → Integrate 🔄 |
| 4.2 | Audience Sync (Meta/Google) | 2-3h | Code ✅ → Integrate 🔄 |
| 4.3 | ROAS Attribution | 2-3h | Code ✅ → Integrate 🔄 |
| 5.1 | A/B Testing | 1-2h | Code ✅ → Integrate 🔄 |
| 5.2 | Journey Cloning | 30m | Code ✅ → Integrate 🔄 |
| 5.3 | Bulk Enrollment | 1-2h | Code ✅ → Integrate 🔄 |

**Total Integration Time:** 10-14 hours ⏰

---

## 🚀 Deployment Checklist

- [ ] Phase 3: FlowCanvas + WebSocket live
- [ ] Phase 4.1: AWS SES sending emails
- [ ] Phase 4.2: Audience sync working (check Meta/Google admin)
- [ ] Phase 4.3: Shopify webhook configured (test with order)
- [ ] Phase 5.1: Create A/B variant (check DB)
- [ ] Phase 5.2: Clone journey (check journey list)
- [ ] Phase 5.3: Bulk upload 10 customers (check DB for new instances)

---

## 📞 Support

For integration help, see:
- Backend services: Check individual service files for docstrings
- Frontend components: Check component files for JSX comments
- Configuration: Check `.env` template files in each service directory

