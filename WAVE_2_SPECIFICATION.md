# Wave 2.0 Implementation Specification

## Overview
20-day sprint (July 16 - August 31) after Wave 1 is complete and 1000+ conversations have been analyzed.

**Goals:**
- Automate customer campaigns with AI suggestions
- Implement churn prediction with ML
- Optimize offers with multi-armed bandit algorithm
- Integrate Claude AI for better intent detection
- Enable full audience lifecycle automation

**Expected Outcome:** Automated campaigns with 70%+ acceptance, churn prediction > 75% accuracy, Claude/Gemini hybrid with 5 new intent categories

---

## 1️⃣ Automated Campaign Orchestration (6 days) - HYBRID MODE

### Database Changes
**New table: `automated_campaigns`**
```sql
CREATE TABLE automated_campaigns (
  campaign_id VARCHAR(36) PRIMARY KEY,
  campaign_name VARCHAR(100),
  template_type VARCHAR(50),           -- hot_lead, churn_recovery, product_launch, loyalty
  enrollment_criteria JSON,             -- Who gets enrolled
  status VARCHAR(20),                   -- active, paused, completed
  approval_required BOOLEAN,            -- HYBRID: true = you approve first 50
  approval_count INTEGER DEFAULT 0,    -- Track approvals
  auto_enroll_threshold INT DEFAULT 50, -- After 50 approvals, go auto
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

CREATE TABLE campaign_enrollments (
  enrollment_id VARCHAR(36) PRIMARY KEY,
  campaign_id VARCHAR(36) FOREIGN KEY,
  customer_id VARCHAR(36) FOREIGN KEY,
  status VARCHAR(20),                  -- active, completed, failed
  enrolled_at TIMESTAMP,
  message_sent_at TIMESTAMP,
  delivered_at TIMESTAMP,
  opened_at TIMESTAMP,
  clicked_at TIMESTAMP,
  outcome VARCHAR(20),                 -- converted, lost, pending, escalated
  created_at TIMESTAMP
);
```

### Service: `campaign_orchestrator.py` (220 lines)
```python
class CampaignService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_campaign(
        self,
        campaign_name: str,
        template_type: str,
        enrollment_criteria: dict
    ) -> dict:
        """Create new campaign with enrollment rules"""
        
    def enroll_customer(
        self,
        campaign_id: str,
        customer_id: str,
        requires_approval: bool = True
    ) -> dict:
        """
        Enroll customer in campaign
        If requires_approval=True: Wait for human approval
        If requires_approval=False: Send immediately
        """
        
    def send_campaign_message(self, enrollment_id: str) -> dict:
        """Send pre-written campaign message via WhatsApp"""
        
    def track_campaign_event(
        self,
        enrollment_id: str,
        event_type: str  # delivered, opened, clicked, converted
    ) -> dict:
        """Track customer interaction with campaign"""
        
    def auto_enroll_if_ready(self, campaign_id: str):
        """
        Check: approval_count >= auto_enroll_threshold?
        If yes: Remove approval_required flag, start auto-enrolling
        """
```

### Campaign Templates (No Gemini Cost)

**Template 1: Hot Lead - Welcome**
```
Message: "Hi {name}! 🌶️ Welcome to Pureleven! 10% off your first order with code WELCOME10"
Trigger: lifecycle_stage == "new" AND score > 50
Approval: You confirm first 50, then auto
```

**Template 2: Churn Recovery - Step 1**
```
Message: "Hi {name}, we haven't seen you in a while. Miss you! 🤔 Come back for special treats."
Trigger: churn_risk > 70 AND last_message >= 30 days
Delay: Send on day 30
Approval: Auto (confidence: 0.9)
```

**Template 3: Churn Recovery - Step 2**
```
Message: "Don't go! 15% off your next order. Code: COMEBACK15"
Trigger: churn_risk > 70 AND last_message >= 37 days (7 days after step 1)
Delay: Send on day 37
Approval: Auto if step 1 didn't convert
```

**Template 4: Product Launch**
```
Message: "Exciting! We just launched {new_product}. Similar to {product_you_asked_about} but {unique_feature}. Pre-order now!"
Trigger: intent == "PRICE_INQUIRY" on {old_product} in past 14 days
Approval: You confirm, then send within 2 hours
```

**Template 5: Loyalty Bonus**
```
Message: "Loyalty milestone! 🎉 You've ordered 5+ times. Here's 20% off just for you!"
Trigger: order_count >= 5 AND lifetime_value >= 3000
Approval: Auto (confidence: 0.95)
```

### HYBRID Mode: You → Auto Progression

**Week 1: Manual Approval Phase**
```
New enrollments → notification to you
You review: "Should we send this message?"
  ├─ Approve ✅ → Send to customer
  └─ Reject ❌ → Don't send, log feedback

After 50 approvals on same campaign:
  → Toggle approval_required = false
  → Start auto-sending for remaining customers
  → Log decision: "After 50 approvals, campaign WON'T improve further"
```

**Week 2: Auto Sending Phase**
```
Matching customers automatically enrolled
Messages auto-sent on schedule
You monitor: Conversion rate, delivery failures
If conversion drops < 30%:
  → Pause campaign
  → Review templates
  → Adjust trigger criteria
```

### API Endpoints
```
POST   /api/ai/campaign/create              - Create campaign
GET    /api/ai/campaign/{campaign_id}       - Campaign details
POST   /api/ai/campaign/{campaign_id}/enroll/{customer_id}  - Manual enroll
POST   /api/ai/campaign/{campaign_id}/approve             - Approve 50
GET    /api/ai/campaign/pending-approvals   - Your approval queue
POST   /api/ai/campaign/{enrollment_id}/send             - Send message
POST   /api/ai/campaign/{enrollment_id}/track            - Track event
GET    /api/ai/campaign/all/stats           - All campaigns stats
```

### React UI: `CampaignOrchestrator.jsx`
```
Left: Campaign list
  - Hot Lead (enrolled: 127, sent: 89, converted: 32, 36%)
  - Churn Recovery (enrolled: 45, sent: 28, converted: 8, 29%)
  - Product Launch (enrolled: 0, sent: 0, mode: APPROVAL PENDING)

Right: Campaign details
  - Template preview
  - Enrollment criteria
  - [Approve & Auto-Send] button (when approval_count >= 50)
  - Performance chart (sent vs converted over time)
  
Approval Queue:
  - Shows 50 pending customer enrollments
  - [Approve All] or [Reject All] buttons
  - After clicking: Campaign auto-sends going forward
```

---

## 2️⃣ Campaign Analytics Dashboard (4 days)

### Metrics

**Funnel Metrics:**
- Enrolled → Sent → Delivered → Opened → Clicked → Converted
- Calculate conversion rate at each step

**ROI Calculation:**
```
campaign_cost = message_count × $0.005 (SMS/WhatsApp)
revenue_generated = converted_customers × avg_order_value
roi = (revenue_generated - cost) / cost
```

### React UI Screens

**1. `CampaignDashboard.jsx`**
```
KPI Cards:
  - Active Campaigns: 5
  - Total Enrolled: 312
  - Conversion Rate: 34%
  - Revenue Influenced: ₹45,600 (est.)

Charts:
  - Line: Messages sent per day (last 30 days)
  - Bar: Conversion rate by campaign
  - Funnel: Enrolled → Delivered → Clicked → Converted
```

**2. `ABTestResults.jsx`**
```
Test: "10% discount" vs "Free shipping"
  
Template A: "10% off"
  - Enrolled: 156
  - Conversion: 58 (37%)
  - Revenue: ₹21,400

Template B: "Free shipping"
  - Enrolled: 154
  - Conversion: 45 (29%)
  - Revenue: ₹16,500

Winner: Template A by 8%
Recommendation: Use "discount" language going forward
```

**3. `CustomerJourneyHeatmap.jsx`**
```
Sankey Diagram:
Enrolled (312)
  ├─ Message Sent (278) 89%
  │  ├─ Delivered (256) 92%
  │  │  ├─ Opened (178) 70%
  │  │  │  ├─ Clicked (64) 36%
  │  │  │  │  └─ Purchased (45) 70%
  │  │  │  └─ Not Clicked (114)
  │  │  └─ Not Opened (78)
  │  └─ Bounced (22)
  └─ Failed (34)

Biggest drop: Message Delivery (89% → 92% delivered)
```

### API Endpoints
```
GET /api/ai/analytics/campaign-funnel     - Funnel metrics
GET /api/ai/analytics/campaign-roi        - ROI by campaign
GET /api/ai/analytics/ab-test-results     - A/B test analysis
GET /api/ai/analytics/customer-journey    - Journey heatmap
```

---

## 3️⃣ Churn Prediction ML Model (4 days)

### Database Changes
**New table: `churn_predictions`**
```sql
CREATE TABLE churn_predictions (
  prediction_id VARCHAR(36) PRIMARY KEY,
  customer_id VARCHAR(36) FOREIGN KEY,
  churn_probability FLOAT (0-1),    -- 0.75 = 75% chance of churn in 60 days
  predicted_at TIMESTAMP,
  created_at TIMESTAMP,
  INDEX (churn_probability DESC, created_at DESC)
);

CREATE TABLE ml_model_metrics (
  metric_id VARCHAR(36) PRIMARY KEY,
  model_version VARCHAR(20),  -- v1, v2, etc
  accuracy FLOAT,
  precision FLOAT,
  recall FLOAT,
  f1_score FLOAT,
  trained_at TIMESTAMP
);
```

### ML Model: Logistic Regression

**Features:**
```
1. days_since_last_order (0-365 days)
2. message_frequency (0-50 messages/month)
3. purchase_intent_score (0-100)
4. response_engagement_score (0-100)  # From Wave 0.2 feedback
5. lifetime_value (₹0 - ₹50,000)
6. order_frequency (0-100 orders)
7. days_since_last_message (0-365)
8. product_affinity_score (0-100)  # From Wave 1
```

**Target Variable:**
```
churned = 1 if (days_since_last_order > 60 AND current_date - last_order_date >= 60)
churned = 0 if active in last 60 days
```

**Training Data:**
```
- Historical period: Last 12 months
- Positive samples (churned): Customers who had 60+ days inactive
- Negative samples (active): Customers with order in last 60 days
- Validation: 80% train / 20% test
```

### Implementation: `churn_model.py`
```python
import pickle
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

class ChurnPredictionModel:
    def __init__(self):
        self.model = LogisticRegression(max_iter=1000)
        self.scaler = StandardScaler()
        self.feature_names = [
            'days_since_last_order',
            'message_frequency',
            'purchase_intent_score',
            'response_engagement_score',
            'lifetime_value',
            'order_frequency',
            'days_since_last_message',
            'product_affinity_score'
        ]
    
    def train(self, X_train, y_train):
        """Train on historical data"""
        X_scaled = self.scaler.fit_transform(X_train)
        self.model.fit(X_scaled, y_train)
        self.save_model()
    
    def predict(self, customer_features: dict) -> float:
        """
        Predict churn probability for customer
        Returns: 0.0 - 1.0 (0 = will stay, 1 = will churn)
        """
        X = np.array([[
            customer_features['days_since_last_order'],
            customer_features['message_frequency'],
            customer_features['purchase_intent_score'],
            customer_features['response_engagement_score'],
            customer_features['lifetime_value'],
            customer_features['order_frequency'],
            customer_features['days_since_last_message'],
            customer_features['product_affinity_score'],
        ]])
        X_scaled = self.scaler.transform(X)
        probability = self.model.predict_proba(X_scaled)[0][1]
        return probability
    
    def evaluate(self, X_test, y_test) -> dict:
        """Evaluate model on test set"""
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        y_pred = self.model.predict(self.scaler.transform(X_test))
        return {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred),
            "recall": recall_score(y_test, y_pred),
            "f1": f1_score(y_test, y_pred)
        }
    
    def save_model(self):
        with open('models/churn_model.pkl', 'wb') as f:
            pickle.dump(self.model, f)
```

### Batch Prediction Job

**Runs nightly (via Celery/APScheduler):**
```python
@scheduler.scheduled_job('cron', hour=2, minute=0)  # 2 AM daily
def predict_churn_nightly():
    """
    1. Get all active customers
    2. Extract 8 features for each
    3. Run through model
    4. Store predictions in churn_predictions table
    5. Auto-enroll high-risk customers in recovery campaigns
    """
    model = ChurnPredictionModel()
    model.load_model()
    
    customers = db.query(Customer).all()
    
    for customer in customers:
        features = extract_features(customer)
        prob = model.predict(features)
        
        # Store prediction
        prediction = ChurnPrediction(
            prediction_id=uuid4(),
            customer_id=customer.id,
            churn_probability=prob,
            predicted_at=datetime.utcnow()
        )
        db.add(prediction)
        
        # If very high risk, auto-enroll in recovery campaign
        if prob > 0.85:
            enroll_in_campaign('churn_recovery_urgent', customer.id)
    
    db.commit()
```

### Model Accuracy & Validation

**Success Criteria:**
```
Accuracy > 75%          # Can predict correctly 3 out of 4 times
Recall > 70%            # Catch 70% of actual churners
Precision > 80%         # When we say someone will churn, 80% actually do
F1 Score > 0.74         # Balanced metric
```

**Validation Process:**
```
1. Split data: 80% train, 20% test
2. Train on 12-month historical data
3. Evaluate on holdout test set
4. If metrics < threshold: Retrain with different features
5. If metrics > threshold: Deploy and monitor
6. Monthly retraining with new data
```

### API Endpoints
```
GET  /api/ai/churn/prediction/{customer_id}        - Churn probability
GET  /api/ai/churn/high-risk?threshold=0.7        - High-risk customers
POST /api/ai/churn/model/train                     - Retrain model
GET  /api/ai/churn/model/metrics                   - Model performance
```

### React UI: `ChurnAnalysis.jsx`
```
KPI Cards:
  - High Risk (>80%): 23 customers
  - Medium Risk (50-80%): 67 customers
  - Low Risk (<50%): 512 customers

Table:
  - Customer name, days_since_order, churn_prob, last_activity
  - Color code: >80% red, 50-80% orange, <50% green
  - [Enroll in Recovery] button

Model Performance:
  - Accuracy: 76%
  - Last trained: 2 days ago
  - Next training: In 3 days
```

---

## 4️⃣ Offer Optimization - Bandit Algorithm (3 days)

### Database Changes
**New table: `bandit_state`**
```sql
CREATE TABLE bandit_state (
  bandit_id VARCHAR(36) PRIMARY KEY,
  customer_segment VARCHAR(50),           -- new, repeat, high_value, etc
  arm_1_name VARCHAR(50),                 -- "10% discount"
  arm_1_successes INT DEFAULT 0,          -- Conversions
  arm_1_trials INT DEFAULT 0,             -- Total shown
  arm_2_name VARCHAR(50),                 -- "Free shipping"
  arm_2_successes INT DEFAULT 0,
  arm_2_trials INT DEFAULT 0,
  arm_3_name VARCHAR(50),                 -- "Bundle offer"
  arm_3_successes INT DEFAULT 0,
  arm_3_trials INT DEFAULT 0,
  current_best_arm INT,                   -- Which arm is winning
  updated_at TIMESTAMP
);
```

### Thompson Sampling Implementation

```python
import numpy as np

class BanditOptimizer:
    def __init__(self, db: Session):
        self.db = db
    
    def select_offer(self, customer_segment: str) -> str:
        """
        Use Thompson Sampling to select best offer
        
        For each arm (offer type):
          - Calculate Beta distribution from (successes, failures)
          - Sample from distribution
          - Select arm with highest sample
        
        This balances:
          - Exploitation: Show winning offers more
          - Exploration: Try new offers to find winners
        """
        bandit = self.db.query(BanditState).filter_by(
            customer_segment=customer_segment
        ).first()
        
        # Calculate Beta distribution for each arm
        arm_1_sample = np.random.beta(
            a=bandit.arm_1_successes + 1,
            b=bandit.arm_1_trials - bandit.arm_1_successes + 1
        )
        
        arm_2_sample = np.random.beta(
            a=bandit.arm_2_successes + 1,
            b=bandit.arm_2_trials - bandit.arm_2_successes + 1
        )
        
        arm_3_sample = np.random.beta(
            a=bandit.arm_3_successes + 1,
            b=bandit.arm_3_trials - bandit.arm_3_successes + 1
        )
        
        # Select best arm
        samples = [arm_1_sample, arm_2_sample, arm_3_sample]
        best_arm = np.argmax(samples)
        
        if best_arm == 0:
            return bandit.arm_1_name
        elif best_arm == 1:
            return bandit.arm_2_name
        else:
            return bandit.arm_3_name
    
    def record_outcome(
        self,
        customer_segment: str,
        offer: str,
        accepted: bool
    ):
        """Record if customer accepted offer (for learning)"""
        bandit = self.db.query(BanditState).filter_by(
            customer_segment=customer_segment
        ).first()
        
        if offer == bandit.arm_1_name:
            bandit.arm_1_trials += 1
            if accepted:
                bandit.arm_1_successes += 1
        elif offer == bandit.arm_2_name:
            bandit.arm_2_trials += 1
            if accepted:
                bandit.arm_2_successes += 1
        else:
            bandit.arm_3_trials += 1
            if accepted:
                bandit.arm_3_successes += 1
        
        self.db.commit()
```

### Setup: Offers to Test

**For "repeat" customer segment:**
- Arm 1: "10% off next order"
- Arm 2: "Free shipping on orders > ₹2000"
- Arm 3: "Bundle: Pepper + Turmeric + Cinnamon at 15% off"

**Thompson Sampling will:**
- Start: 33% traffic to each arm
- Week 1: If Arm 1 wins (40% acceptance), shift to 50% Arm 1, 25% each other
- Week 2: Gradually favor winning arm (70% / 15% / 15%)
- Result: Win within 2-3 weeks, then 80%+ traffic to best offer

### React UI: `OfferOptimization.jsx`
```
Left: Segment list
  - new: Arm 1 (10% off) is winning 45% vs 32% vs 28%
  - repeat: Arm 2 (Free shipping) is winning 58% vs 38% vs 24%
  - high_value: Testing... 35% vs 33% vs 32%

Right: Convergence chart
  - X-axis: Days
  - Y-axis: Acceptance rate by arm
  - Shows how Thompson Sampling converges to winner
  
  Chart shows:
    Arm 1: 35% → 38% → 40% → 42% → 45% ✨
    Arm 2: 32% → 28% → 24% → 20% → 18%
    Arm 3: 33% → 34% → 36% → 38% → 37%
```

---

## 5️⃣ Claude 3.5 Integration (3 days)

### New Intent Categories (Claude Only)

**Category 1: REVIEW_REQUEST**
```
Customer: "Can you send me a review link?"
Claude: "Sure! Here's our review link: [url]. Your feedback helps us improve!"
Confidence: 85% (Claude better at understanding intent nuance)
```

**Category 2: BULK_INQUIRY**
```
Customer: "I want to order 50kg of pepper for my restaurant"
Claude: "Great! For bulk orders, I recommend contacting our wholesale team..."
Confidence: 88%
```

**Category 3: COMPLAINT_RESOLUTION**
```
Customer: "My pepper arrived stale and the packaging was damaged"
Claude: "I'm sorry to hear that. Let me help you immediately. [escalate to team]"
Confidence: 90%
```

**Category 4: LOYALTY_INQUIRY**
```
Customer: "Do you have a loyalty program or rewards?"
Claude: "Yes! Our loyalty program gives 5% back on every purchase..."
Confidence: 87%
```

**Category 5: SEASONAL_DEMAND**
```
Customer: "What's special about your products for Diwali?"
Claude: "For Diwali, we recommend our premium saffron and cardamom collections..."
Confidence: 89%
```

### A/B Testing Framework

```python
class LLMComparison:
    """Compare Gemini vs Claude on same messages"""
    
    def should_use_claude(self) -> bool:
        """
        Sample 10% of messages for Claude
        If response_quality > 4.5/5, migrate 100%
        """
        import random
        return random.random() < 0.1  # 10% to Claude
    
    def generate_response(self, message, context, language):
        """
        Call both APIs in parallel
        Log quality metrics
        """
        if self.should_use_claude():
            return self.call_claude(message, context, language)
        else:
            return self.call_gemini(message, context, language)
```

### Cost Comparison

**Gemini 2.5 Flash:**
- Cost: Free tier (1M tokens/month)
- Quality: 4.2/5 average
- Speed: 2.1s average
- Strengths: Fast, good for price/shipping

**Claude 3.5 Haiku:**
- Cost: Free tier (1M tokens/month via Anthropic credits)
- Quality: 4.7/5 average
- Speed: 2.8s average
- Strengths: Better intent nuance, complaint handling, bulk orders

### Decision Logic
```
IF intent in [BULK_INQUIRY, COMPLAINT_RESOLUTION, LOYALTY_INQUIRY]:
  → Use Claude (better quality)
ELSE:
  → Use Gemini (faster, sufficient quality)
```

### Implementation
```python
# In gemini_provider.py, rename to llm_provider.py

class LLMProvider:
    def __init__(self, gemini_api_key=None, claude_api_key=None):
        self.gemini = GeminiClient(gemini_api_key)
        self.claude = ClaudeClient(claude_api_key)
    
    def generate_response(self, message, intent, language, context):
        """Route to Claude or Gemini based on intent"""
        
        if intent in ['BULK_INQUIRY', 'COMPLAINT_RESOLUTION', 'LOYALTY_INQUIRY', 'SEASONAL_DEMAND']:
            return self.claude.generate(message, context, language)
        else:
            return self.gemini.generate(message, context, language)
```

### A/B Test Results Template
```json
{
  "comparison": {
    "total_messages": 1000,
    "claude_messages": 100,
    "gemini_messages": 900
  },
  "quality_metrics": {
    "claude": {
      "avg_rating": 4.7,
      "thumbs_up": 82,
      "thumbs_down": 18
    },
    "gemini": {
      "avg_rating": 4.2,
      "thumbs_up": 74,
      "thumbs_down": 26
    }
  },
  "performance": {
    "claude_latency_ms": 2800,
    "gemini_latency_ms": 2100
  },
  "recommendation": "Claude is 12% better quality. Migrate to 100% Claude for better customer experience."
}
```

---

## 6️⃣ Audience Export Integrations (2 days)

### Meta Ads Customer List Upload

**Format Requirement:**
```json
{
  "data": [
    {
      "email": "sha256(user@email.com)",
      "phone": "sha256(+919876543210)",
      "fn": "sha256(FirstName)",
      "ln": "sha256(LastName)"
    }
  ]
}
```

**Implementation:**
```python
import hashlib

def hash_field(value: str) -> str:
    """Hash PII for privacy"""
    return hashlib.sha256(value.lower().strip().encode()).hexdigest()

def export_to_meta(segment_id: str, access_token: str):
    """Upload segment to Meta Ads"""
    segment_members = get_segment_members(segment_id)
    
    data = []
    for member in segment_members:
        data.append({
            "email": hash_field(member.email) if member.email else None,
            "phone": hash_field(member.phone) if member.phone else None,
            "fn": hash_field(member.first_name) if member.first_name else None,
            "ln": hash_field(member.last_name) if member.last_name else None,
        })
    
    # Upload to Meta API
    response = requests.post(
        f"https://graph.facebook.com/v18.0/{ad_account_id}/audiences/{audience_id}/users",
        json={"data": data},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return response.json()
```

### Google Ads Customer Match

**Format Requirement:**
```
email,phone,first_name,last_name,country,state,postal_code,city
user@example.com,+919876543210,John,Doe,IN,KL,673591,Kochi
```

**Implementation:**
```python
def export_to_google_ads(segment_id: str, customer_match_id: str):
    """Upload segment to Google Ads"""
    segment_members = get_segment_members(segment_id)
    
    csv_data = "email,phone,first_name,last_name,country,state,postal_code,city\n"
    
    for member in segment_members:
        csv_data += f"{member.email},{member.phone},{member.first_name},{member.last_name},IN,KL,{member.postal_code},{member.city}\n"
    
    # Upload to Google Ads API
    google_ads_client.upload_customer_list(
        customer_match_id=customer_match_id,
        file_data=csv_data
    )
```

### CSV Export (for manual use)
```python
def export_to_csv(segment_id: str) -> bytes:
    """Export segment as CSV"""
    segment_members = get_segment_members(segment_id)
    
    csv_data = "customer_id,phone,email,lifecycle_stage,churn_risk,lifetime_value_inr\n"
    
    for member in segment_members:
        customer = get_customer(member.customer_id)
        profile = get_ai_profile(member.customer_id)
        
        csv_data += f"{customer.id},{customer.phone},{customer.email},{profile.lifecycle_stage},{profile.churn_risk_score},{profile.customer_value_score}\n"
    
    return csv_data.encode()
```

### API Endpoints
```
GET  /api/ai/export/segment/{segment_id}?format=csv               - CSV download
POST /api/ai/export/segment/{segment_id}/meta?access_token=...    - Upload to Meta
POST /api/ai/export/segment/{segment_id}/google?cust_match_id=... - Upload to Google
GET  /api/ai/export/sync-status                                   - Check sync status
```

### React UI: `AudienceExportUI.jsx`
```
Segment: "Hot Leads" (18 members)

[Download CSV] [↗️ Send to Meta Ads] [↗️ Send to Google Ads]

Sync History:
  - 2024-08-15 → Meta Ads ✅ (18 users uploaded)
  - 2024-08-14 → Google Ads ✅ (18 users uploaded)
  - 2024-08-13 → CSV ✅ (downloaded)
```

---

## 7️⃣ Conversational Insights Summary (3 days)

### Weekly Batch Job (Uses Remaining Gemini Tokens)

```python
@scheduler.scheduled_job('cron', day_of_week='monday', hour=9, minute=0)
def generate_weekly_insights():
    """Generate weekly summary of conversations"""
    
    # Collect last 7 days of data
    logs = get_ai_logs(last_days=7)
    
    # Call Gemini once per week (uses ~10-20K tokens, within free tier)
    insights = generate_gemini_summary(logs)
    
    # Parse insights and store
    save_weekly_summary(insights)
```

### Insight Categories

**1. Top Questions**
```
"Price inquiries most common (35% of messages)"
"Customers asking about Black Pepper + Cardamom combination"
```

**2. Emerging Issues**
```
"3 complaints about packaging in last 3 days"
"2 customers asking about bulk discounts (new pattern)"
```

**3. Seasonal Trends**
```
"Cardamom inquiries up 40% (Diwali season)"
"Saffron is trending (wedding season approaching)"
```

**4. Competitor Mentions**
```
"Everest Spices mentioned 5 times"
"MDH mentioned 2 times"
"Recommendation: Emphasize quality difference"
```

**5. Sentiment Analysis**
```
"Overall sentiment: 80% positive, 10% negative, 10% neutral"
"Negative feedback mainly about delivery delays (not your fault)"
```

### React UI: `InsightsSummary.jsx`
```
Weekly Summary Card (on Dashboard):

📊 This Week's Highlights

🎯 Top Questions
  - Price inquiries: 35% of conversations
  - Bulk order inquiries (NEW): 8% of conversations

⚠️ Emerging Issues
  - 3 packaging complaints (action: check with supplier)
  - 2 slow delivery reports

📈 Trends
  - Cardamom interest up 40% (Diwali prep)
  - Saffron trending (weddings coming)

🔍 Competitor Mentions
  - Everest: 5 mentions
  - MDH: 2 mentions
  → You're winning on freshness claims!

😊 Sentiment
  80% ➕ | 10% ➖ | 10% ➖
```

---

## Wave 2 Database Migrations

**Alembic Migration 009:**
- automated_campaigns, campaign_enrollments
- bandit_state, churn_predictions, ml_model_metrics
- weekly_insights table

**Alembic Migration 010:**
- Add columns for Claude integration (if needed)
- Segment export audit logs

---

## Wave 2 Implementation Checklist

```
Campaign Orchestration (6 days):
☐ Create alembic migration 009
☐ Create campaign_orchestrator.py service
☐ Implement HYBRID mode (manual → auto progression)
☐ Create 10+ API endpoints for campaigns
☐ Create CampaignOrchestrator.jsx UI
☐ Pre-write 5 campaign templates
☐ Test approval workflow

Campaign Analytics (4 days):
☐ Create CampaignDashboard.jsx (KPIs + funnels)
☐ Create ABTestResults.jsx (template comparison)
☐ Create CustomerJourneyHeatmap.jsx (Sankey)
☐ Implement conversion tracking
☐ Calculate ROI and revenue influenced

Churn Prediction ML (4 days):
☐ Create churn_model.py with Logistic Regression
☐ Train on 12-month historical data
☐ Validate: Accuracy > 75%, Precision > 80%
☐ Create batch job for nightly predictions
☐ Create ChurnAnalysis.jsx UI
☐ Auto-enroll high-risk customers

Offer Optimization (3 days):
☐ Implement Thompson Sampling algorithm
☐ Create bandit_state table tracking
☐ Setup 3 arms per customer segment (discount/free_shipping/bundle)
☐ Create OfferOptimization.jsx convergence chart
☐ Test for 2 weeks, see which arm wins

Claude Integration (3 days):
☐ Add Claude API wrapper
☐ Define 5 new intent categories
☐ A/B test Claude vs Gemini
☐ Implement routing logic (use Claude for complex intents)
☐ Update LLMProvider class
☐ Quality monitoring

Audience Export (2 days):
☐ Meta Ads integration (hash email/phone)
☐ Google Ads integration (customer match format)
☐ CSV export with all attributes
☐ Create AudienceExportUI.jsx
☐ Test meta/google upload flows
☐ Error handling for failed uploads

Conversational Insights (3 days):
☐ Create weekly batch job
☐ Implement Gemini summary generation
☐ Parse insights into structured format
☐ Create InsightsSummary.jsx widget
☐ Add to Dashboard
☐ Test weekly cadence

Testing & Validation (2 days):
☐ Campaign: Test 5 templates with 10 customers each
☐ Churn: Validate accuracy on holdout test set
☐ Bandit: Verify convergence (arm selection changes over time)
☐ Claude: Compare quality ratings vs Gemini
☐ Exports: Upload segment to Meta/Google manually
☐ Insights: Review first weekly summary

Timeline: 20 days (full sprint)
```

---

## Success Metrics for Wave 2

**Week 1 (Campaigns):**
- ✅ 5 campaign templates working
- ✅ 300+ customers enrolled across campaigns
- ✅ First 50 approvals completed (HYBRID → auto mode)
- ✅ Conversion rate > 30%

**Week 2 (Churn Prediction + Optimization):**
- ✅ ML model trained: Accuracy > 75%
- ✅ Nightly predictions running, 50+ high-risk customers identified
- ✅ Bandit algorithm converging (clear winner emerging)
- ✅ Thompson Sampling reducing exploration cost

**Week 3 (Claude + Exports):**
- ✅ Claude A/B test: Quality 4.7/5 vs Gemini 4.2/5 (+12%)
- ✅ Decision made: Use Claude for 5 new intent categories
- ✅ Meta Ads: 1000+ customers uploaded from segments
- ✅ Google Ads: Customer match list syncing daily

**Week 4 (Analytics + Insights):**
- ✅ Campaign Dashboard: ROI calculated, best campaigns identified
- ✅ Churn: Win-back campaign ready to deploy
- ✅ Weekly insights generated, trends identified
- ✅ All systems stable, ready for production

---

## Cost Impact (Wave 2)

**Gemini + Claude APIs:**
- Before: 35% of messages to Gemini (~100K tokens/month)
- After: 
  - Gemini: 25% of messages (65% rule engine + 10% samples)
  - Claude: 10% of messages (new categories)
  - Cost: $0 (within 1M free tier for both)

**ML Model:**
- Training: 1 time, ~5 mins, free
- Batch predictions: Nightly, ~2 mins, free
- Hardware: Existing server, no additional cost

**Campaign Infrastructure:**
- WhatsApp messages: $0.005 per message (estimate 1000/week = $5/week)
- Storage: Negligible (1000s of records per month)
- No additional infrastructure cost

---

## Start Date: July 16

After Wave 1 is complete and 1000+ conversations have been analyzed.

All decisions made using RECOMMENDED critical decision points.
