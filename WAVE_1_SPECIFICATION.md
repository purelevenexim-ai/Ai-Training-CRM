# Wave 1.0 Implementation Specification

## Overview
15-day sprint (June 22 - July 15) after Wave 0.2 learning reaches 72%+ accuracy.

**Goals:**
- Build product affinity insights
- Create intelligent offer engine
- Develop audience segmentation for Meta/Google exports
- Establish conversation analytics

**Expected Outcome:** Product-intelligent customer recommendations, 5+ exportable audience segments, 1000+ conversations analyzed

---

## 1️⃣ Product Affinity Engine (5 days)

### Database Changes
**New table: `product_associations`**
```sql
CREATE TABLE product_associations (
  association_id VARCHAR(36) PRIMARY KEY,
  product_a_id VARCHAR(36) FOREIGN KEY (product_catalog.id),
  product_b_id VARCHAR(36) FOREIGN KEY (product_catalog.id),
  co_occurrence_count INTEGER,          -- How many times bought together
  correlation_score FLOAT (0-1),         -- Strength of association
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Service: `affinity_engine.py` (200 lines)
```python
class AffinityEngine:
    def __init__(self, db: Session):
        self.db = db
    
    def build_affinity_matrix(self) -> dict:
        """
        Analyze order history to find product pairs
        - Query crm_orders + order_items tables
        - Count product co-occurrences
        - Calculate correlation score
        - Store in product_associations
        """
        
    def get_complementary_products(
        self, 
        product_id: str, 
        limit: int = 5
    ) -> List[dict]:
        """Return best complement products for given product"""
        
    def get_affinity_matrix(self) -> List[List[float]]:
        """Return correlation matrix for visualization"""
        
    def refresh_affinity_daily():
        """Cron job to update associations nightly"""
```

### API Endpoints
```
POST /api/ai/affinity/build         - Trigger affinity calculation
GET  /api/ai/affinity/matrix        - Get correlation matrix
GET  /api/ai/affinity/{product_id}  - Get complementary products
GET  /api/ai/affinity/stats         - Affinity stats
```

### React UI: `ProductAffinityAnalyzer.jsx`
```
- Heatmap of product associations
- "Customers who bought X also bought Y" insights
- Correlation strength visualization
- Top product pairs table
```

### Integration
- Update `gemini_provider.py` to inject top 3 complementary products into context
- When customer asks about Product A, context includes: "Also available: Product B, Product C"

---

## 2️⃣ Enhanced 6D Scoring (3 days)

### Database Changes
**Add columns to `customer_ai_profile`:**
```sql
ALTER TABLE customer_ai_profile ADD COLUMN product_affinity_score FLOAT;
ALTER TABLE customer_ai_profile ADD COLUMN lifecycle_stage VARCHAR(20);
ALTER TABLE customer_ai_profile ADD COLUMN seasonal_demand_score FLOAT;
```

### Enhanced Scoring Engine
**Update `scoring_engine.py` (add 3 new methods):**

```python
def calculate_product_affinity_score(self, customer_id: str) -> int:
    """
    Based on purchase history:
    - Get customer's products
    - Find complementary products they DON'T own
    - Score = readiness to buy complements (0-100)
    """
    
def get_lifecycle_stage(self, customer_id: str) -> str:
    """
    new: 0-1 conversations
    engaged: 2-20 conversations + activity last 14 days
    repeat: 2+ orders
    dormant: no activity 30+ days
    churn: 60+ days no activity
    """
    
def calculate_seasonal_demand_score(self, customer_id: str) -> int:
    """
    - Query time-based purchase patterns
    - Detect seasonal products (pepper in winter, saffron at Diwali)
    - Score customer's likelihood to buy seasonal (0-100)
    """
    
def update_customer_score(self, customer_id: str):
    """
    Enhanced to calculate 6D:
    - engagement (existing)
    - purchase_intent (existing)
    - customer_value (existing)
    - product_affinity (NEW)
    - lifecycle_stage (NEW)
    - seasonal_demand (NEW)
    """
```

### Business Logic

**Lifecycle Stage Logic:**
```
new: profile_created < 24h OR message_count < 2
engaged: message_count 2-20 AND last_message < 14 days
repeat: order_count >= 2 AND last_order < 90 days
dormant: last_message >= 30 days AND last_order < 90 days
churn: last_message >= 60 days OR last_order >= 90 days
```

**Seasonal Demand Score:**
```
Current month = July?
  → Check: Customer bought cardamom/turmeric before July in prior years?
    → YES: seasonal_demand_score = 75
    → NO: seasonal_demand_score = 25

Use time-series aggregation:
  SELECT product_id, EXTRACT(MONTH FROM order_date) as month, COUNT(*) as purchases
  GROUP BY product_id, month
  ORDER BY purchases DESC
```

### React UI: `CustomerLifecycleMatrix.jsx`
```
- Scatter plot: X=spend, Y=purchase_frequency, bubble_size=engagement
- Color by lifecycle stage (new=blue, engaged=green, repeat=gold, dormant=orange, churn=red)
- Hover: Show customer name, stage, next best action
- Enable exporting segments from matrix
```

---

## 3️⃣ Intelligent Offer Engine (4 days)

### Database Changes
**New table: `ai_recommendations`**
```sql
CREATE TABLE ai_recommendations (
  rec_id VARCHAR(36) PRIMARY KEY,
  customer_id VARCHAR(36) FOREIGN KEY (crm_customers.id),
  offer_text TEXT,
  offer_type VARCHAR(30),  -- discount, free_shipping, product_bundle, loyalty_bonus
  offer_value FLOAT,       -- 10 for "10% off", etc
  confidence_score FLOAT,  -- How confident in this offer working
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP
);
```

### Service: `offer_engine.py` (180 lines)
```python
class OfferEngine:
    def __init__(self, db: Session, affinity_engine, scoring_engine):
        self.db = db
        self.affinity = affinity_engine
        self.scoring = scoring_engine
    
    def generate_offer(self, customer_id: str) -> dict:
        """
        Rule-based offer selection (NO LLM):
        
        IF score > 75 AND stage == repeat:
          "10% off next order" (confidence: 0.85)
        
        IF score < 30 AND last_message >= 30 days:
          "Come back! 15% off" (confidence: 0.80)
        
        IF product_affinity_score > 60:
          "We have [complementary] in stock!" (confidence: 0.75)
        
        IF seasonal_demand > 70 AND current_month in [season]:
          "Diwali Special: [seasonal_product] 20% off" (confidence: 0.82)
        """
    
    def get_active_offers(self, customer_id: str) -> List[dict]:
        """Get current active offers for customer"""
        
    def track_offer_acceptance(self, rec_id: str, accepted: bool):
        """Track if customer responded to offer"""
```

### Rule-Based Offer Templates

**Template 1: VIP Customer**
```
IF overall_score >= 75 AND orders >= 3 AND churn_risk < 30:
  → "VIP: 10% off all orders" (expires: 30 days)
  → confidence: 0.88
```

**Template 2: Churn Recovery**
```
IF churn_risk >= 70 AND lifetime_value >= ₹5000:
  → "We miss you! 15% off + Free Shipping"
  → confidence: 0.85
```

**Template 3: Product Bundle**
```
IF product_affinity_score >= 70:
  → "Bundle: Pepper + Turmeric [combo_price]"
  → confidence: 0.78
```

**Template 4: Seasonal Push**
```
IF seasonal_demand >= 70 AND (current_month in [seasonal_months]):
  → "Diwali Special: Premium Saffron 20% off"
  → confidence: 0.82
```

**Template 5: New Customer**
```
IF lifecycle_stage == new AND score >= 50:
  → "Welcome! 10% off your first order"
  → confidence: 0.90
```

### API Endpoints
```
POST /api/ai/offer/generate/{customer_id}      - Generate offer
GET  /api/ai/offer/active/{customer_id}        - Active offers
POST /api/ai/offer/{rec_id}/track              - Track acceptance
GET  /api/ai/offer/performance                 - Offer effectiveness
```

### Integration with Gemini
**Update `gemini_provider.py` system prompt:**
```
If customer is interested in purchase:
  - Check if offer available via OfferEngine.generate_offer()
  - Inject into response: "Great choice! We have [offer] for you"
  - Response is more compelling with offer context
```

### React UI: `OfferPerformance.jsx`
```
- Table: Offer type, customer count, acceptance rate, revenue impact
- Chart: Acceptance rate by offer type
- Recommendation: "15% off" beats "free shipping" by 12%
```

---

## 4️⃣ Response Personalization (3 days)

### Database Changes
**New table: `response_templates`**
```sql
CREATE TABLE response_templates (
  template_id VARCHAR(36) PRIMARY KEY,
  template_type VARCHAR(50),      -- value_customer, new_customer, price_sensitive, bulk_buyer
  content_style VARCHAR(200),     -- "formal", "friendly", "urgent", "playful"
  examples TEXT,                  -- Sample responses for this style
  created_at TIMESTAMP
);
```

### Personalization Logic
**Update `gemini_provider.py`:**

```python
def generate_response(
    self,
    message: str,
    context: dict = None,
    language: str = "english",
    customer_profile: dict = None  # NEW: customer lifecycle, score, etc
) -> tuple:
    """
    If customer_profile provided:
    
    IF lifecycle_stage == 'new':
      system_prompt += "Tone: Warm and welcoming. Emphasize ease and trust."
    
    IF lifecycle_stage == 'repeat':
      system_prompt += "Tone: Friendly and familiar. Reference past purchases."
    
    IF churn_risk > 70:
      system_prompt += "Tone: Urgent and caring. Ask why they've gone quiet."
    
    IF score > 80:
      system_prompt += "Tone: VIP treatment. Acknowledge their loyalty."
    """
```

### A/B Testing Framework
```
Track for each response:
- customer_lifecycle_stage
- response_style_used
- customer_accepted_offer (yes/no)
- conversation_continued (yes/no)
- converted_to_order (yes/no)

Analyze acceptance rate by:
- Template + Lifecycle combination
- Template + Language combination
```

### React UI Enhancement
**Update `Conversations.jsx`:**
```
- Show which template was used for each response
- Add A/B test stats (Template A: 45% acceptance vs Template B: 52%)
- Recommendation: "Use friendly tone for new customers (+8%)"
```

---

## 5️⃣ Audience Segmentation (2 days)

### Database Changes
**New table: `customer_segments`**
```sql
CREATE TABLE customer_segments (
  segment_id VARCHAR(36) PRIMARY KEY,
  segment_name VARCHAR(100),
  filter_criteria JSON,        -- Rule definition
  member_count INTEGER,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

CREATE TABLE segment_members (
  member_id VARCHAR(36) PRIMARY KEY,
  segment_id VARCHAR(36) FOREIGN KEY,
  customer_id VARCHAR(36) FOREIGN KEY,
  added_at TIMESTAMP
);
```

### Pre-built Segments

**Segment 1: Hot Leads**
```json
{
  "name": "Hot Leads",
  "rule": {
    "overall_score": { ">": 75 },
    "lifecycle_stage": ["repeat", "engaged"],
    "churn_risk": { "<": 30 }
  },
  "size": "~15-20 customers"
}
```

**Segment 2: Churn Risk**
```json
{
  "name": "Churn Risk - High Value",
  "rule": {
    "churn_risk": { ">": 70 },
    "lifetime_value_inr": { ">": 5000 }
  },
  "size": "~30-50 customers"
}
```

**Segment 3: Product Affinity**
```json
{
  "name": "Cardamom Lovers",
  "rule": {
    "has_product_purchased": "cardamom",
    "product_affinity_score": { ">": 60 }
  },
  "size": "~200-300 customers"
}
```

**Segment 4: New & Active**
```json
{
  "name": "New Customers (Engaged)",
  "rule": {
    "lifecycle_stage": "new",
    "last_message_days": { "<": 7 }
  },
  "size": "~40-60 customers"
}
```

**Segment 5: Seasonal Buyers**
```json
{
  "name": "Seasonal Spice Buyers",
  "rule": {
    "seasonal_demand_score": { ">": 70 },
    "current_season_match": true
  },
  "size": "~100-150 customers"
}
```

### API Endpoints
```
POST /api/ai/segment/create                    - Create custom segment
GET  /api/ai/segment/{segment_id}              - Get segment details
GET  /api/ai/segment/{segment_id}/members      - List members (paginated)
GET  /api/ai/export/segment/{segment_id}?format=csv   - CSV export
GET  /api/ai/export/segment/{segment_id}?format=meta  - Meta upload format
GET  /api/ai/export/segment/{segment_id}?format=google - Google Ads format
```

### React UI: `AudienceBuilder.jsx`
```
Left panel: Segment list with counts
  - Hot Leads (18)
  - Churn Risk (42)
  - Cardamom Lovers (267)
  - New & Active (54)
  - Seasonal (125)

Right panel: Selected segment details
  - Visualization of filter rules
  - [Export CSV] button
  - [Send to Meta] button
  - [Send to Google] button
  - Real-time member count update
```

### Export Formats

**CSV Format:**
```csv
phone,email,lifecycle_stage,churn_risk,product_affinity,lifetime_value_inr
+919876543210,customer@email.com,repeat,15,75,5400
...
```

**Meta Ads Format (Customer List):**
```json
{
  "data": [
    {
      "email_hash": "sha256_hash_of_email",
      "phone_hash": "sha256_hash_of_phone"
    }
  ]
}
```

**Google Ads Format (Customer Match):**
```csv
email,phone,first_name,last_name,country,state,zip
customer@email.com,+919876543210,Priya,Kumar,IN,KL,673591
...
```

---

## 6️⃣ Conversation Analytics (3 days)

### New API Endpoints
```
GET /api/ai/analytics/metrics           - Overall metrics
GET /api/ai/analytics/products          - Product performance
GET /api/ai/analytics/trends            - Time series data
GET /api/ai/analytics/intent-heatmap    - Intent by hour/day
GET /api/ai/analytics/language-stats    - Language usage over time
```

### React UI Screens

**1. `ConversationMetrics.jsx`**
```
- Pie chart: Intent distribution
  ├─ PRICE_INQUIRY: 35%
  ├─ SHIPPING_INQUIRY: 22%
  ├─ PURCHASE: 18%
  ├─ COD_INQUIRY: 15%
  └─ Others: 10%

- Bar chart: Language breakdown
  ├─ English: 60%
  ├─ Malayalam: 25%
  └─ Manglish: 15%

- KPI cards:
  ├─ Avg response time: 2.3s
  ├─ Gemini fallback rate: 35%
  └─ Conversation completion: 72%
```

**2. `ProductPerformance.jsx`**
```
- Table: Most mentioned products in conversations
  ├─ Black Pepper (234 mentions)
  ├─ Cardamom (189 mentions)
  ├─ Turmeric (156 mentions)
  ├─ Cinnamon (134 mentions)
  └─ Cumin (98 mentions)

- Chart: Product mentions by category
- Chart: Product mention trends (last 30 days)
```

**3. `TimeSeriesAnalytics.jsx`**
```
- Line chart: Messages per day (last 30 days)
- Line chart: Price inquiries trend
- Line chart: Conversion rate trend
- Seasonal pattern detection
```

---

## Wave 1 Database Migrations

**Alembic Migration 008:**
```python
# Add product_associations table
# Add columns to customer_ai_profile (product_affinity, lifecycle_stage, seasonal_demand)

# Add ai_recommendations table
# Add response_templates table
# Add customer_segments and segment_members tables
```

---

## Integration Checklist for Wave 1

```
Database:
☐ Create alembic migration 008
☐ Add product_associations table
☐ Add columns to customer_ai_profile
☐ Add ai_recommendations table
☐ Create response_templates with initial templates
☐ Create customer_segments and segment_members tables

Backend Services:
☐ Create affinity_engine.py (200 lines)
☐ Create offer_engine.py (180 lines)
☐ Update scoring_engine.py (add 3 new methods, 150 lines)
☐ Update gemini_provider.py (add product context, offer context)
☐ Create 20+ new API endpoints

API Routes:
☐ Create affinity_routes.py (8 endpoints)
☐ Create offer_routes.py (5 endpoints)
☐ Create segment_routes.py (8 endpoints)
☐ Create analytics_routes.py (5 endpoints)
☐ Update ai_routes.py (integrate affinity + offers)

Frontend:
☐ Create ProductAffinityAnalyzer.jsx
☐ Create CustomerLifecycleMatrix.jsx
☐ Create AudienceBuilder.jsx
☐ Create ConversationMetrics.jsx
☐ Create ProductPerformance.jsx
☐ Create TimeSeriesAnalytics.jsx
☐ Create OfferPerformance.jsx
☐ Update AICenter/index.jsx (add 7 new screens)
☐ Update Dashboard.jsx (show affinity insights)

Testing:
☐ Verify affinity matrix calculation
☐ Test offer generation for 10 customer profiles
☐ Export segments to CSV
☐ A/B test response personalization
☐ Validate analytics data

Timeline: 15 days (full sprint)
```

---

## Success Metrics for Wave 1

**Week 1 (Affinity + Scoring):**
- ✅ Product affinity matrix built (500+ associations)
- ✅ All customers have 6D scores calculated
- ✅ Lifecycle stages assigned correctly
- ✅ Seasonal demand scores populated

**Week 2 (Offers + Personalization):**
- ✅ 5+ offer templates working
- ✅ Offers showing in Gemini responses
- ✅ A/B test running (track acceptance by template)
- ✅ Response personalization by lifecycle stage

**Week 3 (Segmentation + Analytics):**
- ✅ 5+ pre-built segments with members
- ✅ CSV export working
- ✅ Meta/Google exports formatted correctly
- ✅ Analytics dashboard populated with 30 days data

---

## Cost Impact (Wave 1)

**Gemini API:**
- Before: 35% of messages to Gemini
- After: Still 35%, but better context (products, offers, personalization)
- Cost: UNCHANGED (same token usage, better decisions)

**Human Time:**
- 3 engineers × 2 weeks = 120 engineer-hours
- Infrastructure: Existing PostgreSQL (no new cost)
- Data: Analyze 1000+ conversations (no cost)

---

## Start Date: June 22

After Wave 0.2 reaches 72%+ accuracy and integration testing is complete.
