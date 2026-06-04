# 🚀 MULTI-CHANNEL MARKETING IMPLEMENTATION CHECKLIST
**Start Here — Follow This Checklist to Execute the Plan**

**Current Status:** Email working ✅ | Meta CAPI ready ✅ | Google Ads ready ✅ | Wabis ready ✅  
**Missing Piece:** Orchestration layer that coordinates all channels  
**Timeline:** 12 weeks, phased approach

---

## PHASE 1: FOUNDATION (Weeks 1-2)
### Goal: Build the unified data layer & segmentation engine

#### Week 1: Database & Segmentation

- [ ] **Create Database Tables**
  ```sql
  -- 1. crm_segments table (track segment membership)
  CREATE TABLE crm_segments (
    id UUID PRIMARY KEY,
    customer_id UUID NOT NULL,
    segment_name VARCHAR(100) NOT NULL,
    lifecycle_stage VARCHAR(50),  -- awareness|consideration|decision|purchased|loyal
    assigned_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
  );
  
  -- 2. crm_journeys table (track customer path)
  CREATE TABLE crm_journeys (
    id UUID PRIMARY KEY,
    customer_id UUID NOT NULL,
    event_type VARCHAR(50),  -- email_opened|whatsapp_clicked|meta_impression|etc
    channel VARCHAR(20),  -- email|whatsapp|meta|google|ga4
    campaign_id VARCHAR(100),
    event_data JSONB,
    created_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
  );
  
  -- 3. crm_message_logs table (detailed tracking)
  CREATE TABLE crm_message_logs (
    id UUID PRIMARY KEY,
    customer_id UUID NOT NULL,
    message_type VARCHAR(50),  -- welcome|cart_recovery|order_confirmation|etc
    channel VARCHAR(20),  -- email|whatsapp|meta|sms
    status VARCHAR(20),  -- sent|delivered|failed|opened|clicked
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    metadata JSONB,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
  );
  ```
  **Action:** Run migrations on VPS PostgreSQL

- [ ] **Build Segment Assignment Logic**
  File: `crm_routes.py` (add new function)
  ```python
  def assign_segment(customer):
      """Determine which segment customer belongs to"""
      # Logic from Part 3 of plan document
      # Returns: segment_name, lifecycle_stage
  ```

- [ ] **Test Segment Assignment**
  - [ ] Create test customers (5-10 with different behaviors)
  - [ ] Run segment assignment
  - [ ] Verify output matches expected segments

- [ ] **Document: Segment Definitions**
  - [ ] Export Part 3 segment matrix to a reference guide
  - [ ] Create visual flowchart (Mermaid)

---

#### Week 2: Scheduling & Monitoring

- [ ] **Setup APScheduler (or similar)**
  File: `crm_routes.py` or new `jobs.py`
  ```python
  from apscheduler.schedulers.background import BackgroundScheduler
  
  scheduler = BackgroundScheduler()
  
  @scheduler.scheduled_job('cron', hour=2, minute=0)  # 2 AM daily
  def segment_assignment_job():
      """Run segment assignment for all customers"""
      # Update crm_segments table
      # Log execution
  
  scheduler.start()
  ```

- [ ] **Create Monitoring Dashboard**
  - [ ] Google Sheets or Data Studio
  - [ ] Track daily: # of customers in each segment
  - [ ] Track weekly: funnel conversion rates

- [ ] **Write Tests**
  - [ ] Test segment assignment logic
  - [ ] Test with edge cases (no email, no purchase, etc.)

- [ ] **Deploy to VPS**
  - [ ] Copy updated files to `/opt/pureleven/ai-engine/app/`
  - [ ] Restart container
  - [ ] Verify jobs running via logs

---

## PHASE 2: CHANNEL INTEGRATION (Weeks 3-5)
### Goal: Connect Wabis, Meta, Google to the orchestration engine

#### Week 3: WhatsApp (Wabis) Setup

- [ ] **Create WhatsApp Message Templates in Wabis Dashboard**
  Go to: https://app.wabis.in → Templates
  
  Create 8 templates:
  - [ ] Template 1: "welcome" (new customer intro)
  - [ ] Template 2: "product_education" (why we're different)
  - [ ] Template 3: "browse_abandonment" (products you viewed)
  - [ ] Template 4: "cart_recovery_urgent" (₹X in cart, claim discount)
  - [ ] Template 5: "order_confirmation" (order #, next steps)
  - [ ] Template 6: "shipping_notification" (tracking link)
  - [ ] Template 7: "review_request" (leave review, get ₹100)
  - [ ] Template 8: "replenishment_reminder" (time to restock)
  
  **Action:** Write templates in `WABIS_TEMPLATES.md` first, then copy to Wabis dashboard

- [ ] **Setup Wabis Webhook in CRM**
  Endpoint: `POST /api/crm/webhooks/wabis`
  
  File: `crm_routes.py`
  ```python
  @router.post("/webhooks/wabis")
  async def wabis_webhook(request: dict):
      # Capture: message_id, phone_id, event_type (sent|delivered|clicked|read)
      # Log to crm_journeys table
      # Update customer last_engagement_at
  ```

- [ ] **Build Message Sending Function**
  File: `sendgrid_handler.py` → add `send_whatsapp()`
  ```python
  async def send_whatsapp(phone_number, template_name, substitutions):
      """Send WhatsApp message via Wabis API"""
      # Call Wabis API
      # Log to crm_message_logs
      # Return status (sent|failed)
  ```

- [ ] **Test WhatsApp Sending**
  - [ ] Send test message to yourself
  - [ ] Verify delivery in Wabis logs
  - [ ] Verify webhook received click event

---

#### Week 4: Meta Audiences & Sync

- [ ] **Add Meta Pixel Events Beyond Current**
  File: Shopify theme settings (Product → Additional scripts)
  
  Current pixel events (working): `Purchase`
  
  Add:
  - [ ] `ViewContent` (product page view)
  - [ ] `AddToCart` (cart events)
  - [ ] `InitiateCheckout` (checkout started)
  - [ ] `CompleteRegistration` (email signup)
  - [ ] `AddPaymentInfo` (payment attempted)
  
  **Action:** Test via Meta Events Manager

- [ ] **Build Audience Sync Job**
  File: `jobs.py`
  ```python
  @scheduler.scheduled_job('cron', hour=2, minute=30)
  async def meta_audience_sync_job():
      """Nightly sync of audiences to Meta"""
      # Query segments from crm_segments table
      # Build audience lists:
      #   - All website visitors (30 days)
      #   - Cart abandoners (7 days)
      #   - Converters (30 days)
      #   - VIP customers (2+ purchases)
      # Upload to Meta via Conversions API
  ```

- [ ] **Hash Email/Phone for Meta**
  ```python
  import hashlib
  
  def hash_pii(value):
      """SHA256 hash for Meta custom audiences"""
      return hashlib.sha256(value.lower().strip().encode()).hexdigest()
  ```

- [ ] **Test Meta Sync**
  - [ ] Export 10 test emails
  - [ ] Hash them
  - [ ] Upload to Meta via API
  - [ ] Verify in Meta Ads Manager (Audiences)

---

#### Week 5: Google Ads Integration

- [ ] **Build Google Ads List Upload**
  File: `jobs.py`
  ```python
  @scheduler.scheduled_job('cron', hour=2, minute=45)
  async def google_ads_list_sync():
      """Nightly sync to Google Ads remarketing/customer match"""
      # Query segments
      # Build lists:
      #   - Website visitors (30 days)
      #   - Cart abandoners (7 days)
      #   - Converters (30 days)
      # Upload via Google Ads API (Customer Match)
  ```

- [ ] **Test Google Ads Upload**
  - [ ] Export 10 test emails
  - [ ] Upload to Google Ads
  - [ ] Verify in Google Ads → Audiences

- [ ] **Verify GA4 Event Tracking**
  - [ ] Check: GA4 shows purchase events ✅
  - [ ] Check: utm_source tracked correctly
  - [ ] Check: product_view events logged

---

## PHASE 3: ORCHESTRATION (Weeks 6-8)
### Goal: Automate multi-channel customer journeys

#### Week 6: Journey Engine

- [ ] **Build Journey Trigger System**
  File: `crm_routes.py` → new function
  ```python
  async def on_segment_entry(customer_id, segment_name):
      """Triggered when customer enters new segment"""
      
      if segment_name == "cold_awareness":
          # Schedule: Welcome email Day 0
          schedule_message("welcome", customer_id, delay_hours=0)
      
      elif segment_name == "warm_consideration":
          # Schedule: Education email Day 1
          schedule_message("product_education", customer_id, delay_hours=24)
          # Schedule: WhatsApp message Day 2
          schedule_whatsapp("product_education", customer_id, delay_hours=48)
      
      elif segment_name == "hot_decision":
          # Immediate: Cart recovery email
          schedule_message("cart_recovery", customer_id, delay_hours=0)
          # In 2h: WhatsApp
          schedule_whatsapp("cart_recovery", customer_id, delay_hours=2)
  ```

- [ ] **Build Message Scheduler**
  File: `jobs.py`
  ```python
  async def process_scheduled_messages():
      """Check for messages ready to send"""
      # Query crm_scheduled_messages where send_at <= now
      # Send via appropriate channel (email|whatsapp|etc)
      # Log result to crm_message_logs
  ```

- [ ] **Implement Frequency Capping**
  ```python
  def can_send_message(customer_id, channel):
      """Check if customer can receive message"""
      # For WhatsApp: max 2 per week
      # For Email: max 1 per day
      # For Meta: frequency set at ad level
      
      if channel == "whatsapp":
          recent = get_recent_messages(customer_id, "whatsapp", days=7)
          return len(recent) < 2
      
      elif channel == "email":
          recent = get_recent_messages(customer_id, "email", days=1)
          return len(recent) < 1
      
      return True
  ```

- [ ] **Test Journey Automation**
  - [ ] Create test customer → cold_awareness segment
  - [ ] Verify welcome email scheduled
  - [ ] Wait, verify email sent
  - [ ] Move to warm_consideration segment
  - [ ] Verify WhatsApp scheduled next day

---

#### Week 7: Message Templates & Copy

- [ ] **Write Email Templates**
  Create: `EMAIL_TEMPLATES.md`
  - [ ] Welcome email (Part 4)
  - [ ] Browse abandonment (Part 4)
  - [ ] Cart recovery (Part 4)
  - [ ] Order confirmation (Part 4)
  - [ ] Review request (Part 4)
  - [ ] Replenishment reminder (Part 4)
  
  **Update:** `sendgrid_handler.py` with new templates

- [ ] **Write WhatsApp Templates**
  Create: `WABIS_TEMPLATES.md`
  - [ ] Product education (Part 4)
  - [ ] Cart recovery (Part 4)
  - [ ] Order confirmation (Part 4)
  - [ ] Review request (Part 4)
  
  **Action:** Copy to Wabis dashboard

- [ ] **Setup Meta Ad Creatives**
  Goto: Meta Ads Manager
  - [ ] Create awareness campaign ads (carousel, video)
  - [ ] Create consideration campaign ads (testimonials)
  - [ ] Create decision campaign ads (urgency)
  - [ ] Create loyalty campaign ads (upsell)

- [ ] **A/B Test Subjects & Copy**
  - [ ] Email subject: Urgency vs. Value
  - [ ] Send time: Morning vs. Evening
  - [ ] WhatsApp: Short vs. Detailed

---

#### Week 8: Monitoring & Adjustments

- [ ] **Setup Funnel Dashboard**
  Google Data Studio or Metabase
  - [ ] Awareness → Consideration → Decision → Purchase
  - [ ] Conversion rates at each stage
  - [ ] Segment sizes
  - [ ] Metrics by source (Google Ads, Meta, Organic, etc.)

- [ ] **Monitor Key Metrics**
  Track daily/weekly:
  - [ ] Email open rate (target: 30-45%)
  - [ ] Email click rate (target: 15-25%)
  - [ ] Cart recovery rate (target: 5-8%)
  - [ ] Cold → Customer conversion (target: 2-4%)
  - [ ] Meta ROAS (target: 3-5:1)
  - [ ] Google Ads ROAS (target: 2-4:1)

- [ ] **Adjust Messaging Based on Performance**
  - [ ] If low email open: Test subject lines
  - [ ] If low click: Test CTA button text
  - [ ] If low conversion: Test discount amounts
  - [ ] If high unsubscribe: Space out emails more

---

## PHASE 4: LIST SYNC & AUDIENCES (Weeks 9-10)
### Goal: Keep audiences fresh in all platforms

#### Week 9: Audience Sync Jobs

- [ ] **Test Segment Query Logic**
  Query and export:
  - [ ] All Google Ads visitors (last 30 days) → 50-200 emails expected
  - [ ] All Meta visitors (last 30 days) → 50-200 emails expected
  - [ ] Cart abandoners (last 7 days) → 10-30 emails expected
  - [ ] Converters (last 30 days) → 10-50 emails expected
  - [ ] VIP customers (2+ purchases) → 5-20 emails expected

- [ ] **Deploy Nightly Sync Jobs**
  File: `jobs.py`
  
  Schedule:
  - [ ] Meta sync: 2:30 AM daily
  - [ ] Google Ads sync: 2:45 AM daily
  - [ ] Wabis sync: 3:00 AM daily

- [ ] **Monitor Sync Logs**
  - [ ] Check: Jobs run daily
  - [ ] Check: No errors in logs
  - [ ] Check: Audience sizes match expectations
  - [ ] Alert: If audience size drops 50%+ (data issue)

---

#### Week 10: Audience Validation

- [ ] **Verify Meta Audiences Updated**
  Go to: Meta Ads Manager → Audiences
  - [ ] Check: Audience sizes
  - [ ] Check: Last updated timestamp
  - [ ] Check: Can create campaigns targeting these audiences

- [ ] **Verify Google Ads Lists Updated**
  Go to: Google Ads → Audiences → Customer Match
  - [ ] Check: Audience sizes
  - [ ] Check: Last updated timestamp
  - [ ] Check: Can use in remarketing campaigns

- [ ] **Monitor for Errors**
  - [ ] Log failed API calls
  - [ ] Alert on > 5 consecutive failures
  - [ ] Manually re-run sync if failed

---

## PHASE 5: TESTING & OPTIMIZATION (Weeks 11-12)
### Goal: Verify system works, measure results, optimize

#### Week 11: End-to-End Testing

- [ ] **Test Cold → Warm → Customer Journey**
  
  **Test 1: Cold Awareness**
  - [ ] Simulate new website visitor (GA4 event)
  - [ ] Verify: Customer created in CRM
  - [ ] Verify: Assigned to cold_awareness segment
  - [ ] Verify: Welcome email queued (Day 0)
  - [ ] Verify: Added to Meta website audience
  - [ ] Verify: Added to Google Ads remarketing list

  **Test 2: Move to Warm (2nd Visit)**
  - [ ] Simulate return visit (GA4 event)
  - [ ] Verify: Product added to browse history
  - [ ] Verify: Segment updated to warm_consideration
  - [ ] Verify: Education email queued (Day 1)
  - [ ] Verify: WhatsApp queued (Day 2)
  - [ ] Verify: Meta ad frequency increased

  **Test 3: Move to Hot (Cart Added)**
  - [ ] Simulate add-to-cart event
  - [ ] Verify: Segment updated to hot_decision
  - [ ] Verify: Cart recovery email sent immediately
  - [ ] Verify: WhatsApp queued (2 hours later)
  - [ ] Verify: Meta ads show urgency messaging

  **Test 4: Purchase**
  - [ ] Simulate purchase (Shopify webhook)
  - [ ] Verify: Order confirmation email sent
  - [ ] Verify: Meta CAPI conversion event fired
  - [ ] Verify: Google Ads offline conversion logged
  - [ ] Verify: Customer moved to "customer" segment
  - [ ] Verify: Added to Meta "converters" audience
  - [ ] Verify: Added to Google Ads "converters" list

  **Test 5: Post-Purchase Nurture**
  - [ ] Verify: Shipping email sent (Day 1)
  - [ ] Verify: Out for delivery WhatsApp (Day 2)
  - [ ] Verify: Review request email (Day 3)
  - [ ] Verify: Replenishment reminder queued (Day 30)

- [ ] **Test Frequency Capping**
  - [ ] Send 2 WhatsApp messages on same day
  - [ ] Verify: 2nd message doesn't send (frequency capped)
  - [ ] Send after 7 days
  - [ ] Verify: Message sent (new week)

- [ ] **Test Unsubscribe Flow**
  - [ ] Click unsubscribe link in email
  - [ ] Verify: Customer marked as unsubscribed
  - [ ] Verify: No more emails sent
  - [ ] Verify: Can still receive WhatsApp (if opted in)

---

#### Week 12: Metrics & Optimization

- [ ] **Setup Analytics Dashboard**
  
  Create dashboard with:
  - [ ] **Funnel Metrics**
    - Total visitors (this week)
    - Converted to cold_awareness (%)
    - Moved to warm_consideration (%)
    - Moved to hot_decision (%)
    - Purchased (%)
    - Repeat purchased (%)

  - [ ] **Channel Performance**
    ```
    Email:
      - Sent: [count]
      - Delivered: [count] ([%])
      - Opened: [count] ([%])
      - Clicked: [count] ([%])
      - Unsubscribed: [count] ([%])
    
    WhatsApp:
      - Sent: [count]
      - Delivered: [count] ([%])
      - Read: [count] ([%])
      - Clicked: [count] ([%])
      - Replied: [count] ([%])
    
    Meta Ads:
      - Impressions: [count]
      - Clicks: [count]
      - CTR: [%]
      - Spend: ₹[amount]
      - ROAS: [ratio]
    
    Google Ads:
      - Impressions: [count]
      - Clicks: [count]
      - CTR: [%]
      - Spend: ₹[amount]
      - ROAS: [ratio]
    ```

  - [ ] **Segment Health**
    - Size of each segment (trending)
    - Conversion rate by segment
    - Engagement rate by segment
    - Churn rate by segment

- [ ] **Run A/B Tests**
  
  **Test 1: Email Subject Lines**
  - [ ] Version A: "Your ₹150 discount is waiting" (urgency)
  - [ ] Version B: "Get 30% off farm-fresh spices" (value)
  - [ ] Split 50/50 to warm_consideration segment
  - [ ] Measure: Open rate, click rate
  - [ ] Winner: Implement for all future emails

  **Test 2: Send Time Optimization**
  - [ ] Group A: Email at 9 AM (morning)
  - [ ] Group B: Email at 5 PM (evening)
  - [ ] Measure: Open time, click time
  - [ ] Winner: Use optimal time for future sends

  **Test 3: WhatsApp Message Length**
  - [ ] Version A: Short (2 sentences + link)
  - [ ] Version B: Detailed (5 sentences + benefits + link)
  - [ ] Measure: Read rate, click rate
  - [ ] Winner: Use for future WhatsApp sends

  **Test 4: Cart Recovery Discount**
  - [ ] Version A: ₹50 OFF
  - [ ] Version B: ₹100 OFF
  - [ ] Measure: Conversion rate, average order value
  - [ ] Winner: Optimize between conversion & margin

- [ ] **Write Weekly Report**
  Document:
  - [ ] Metrics for the week (vs. targets)
  - [ ] What worked, what didn't
  - [ ] Segments with highest conversion
  - [ ] Channels with best ROAS
  - [ ] Optimization recommendations for next week

- [ ] **Share with Stakeholders**
  - [ ] Present funnel metrics
  - [ ] Show customer journey visualization
  - [ ] Highlight top-performing segments
  - [ ] Plan optimizations for next month

---

## QUICK WINS (Do These FIRST to See Immediate Impact)

1. **Week 1-2 Quick Win: Welcome Email Series** ✅ (Already done)
   - Set up welcome + product education emails
   - Should boost engagement by 20-30% immediately

2. **Week 3 Quick Win: WhatsApp Cart Recovery** 
   - Single WhatsApp message to cart abandoners
   - 5-8% conversion rate = immediate revenue boost

3. **Week 4 Quick Win: Meta Audience Lists**
   - Export converters list to Meta
   - Create lookalike audience
   - Target lookalikes with ads
   - 3-5x ROI expected

4. **Week 5 Quick Win: Google Ads Remarketing**
   - Create remarking list from website visitors
   - Create remarketing campaign in Google Ads
   - Target with "last chance" messaging
   - 2-4x ROI expected

---

## CRITICAL DEPENDENCIES

These must be done in order:
1. ✅ Email templates (done)
2. ✅ Wabis integration (done)
3. ✅ Meta CAPI (done)
4. ✅ Google Ads (done)
5. → **Segmentation Engine** (foundation for everything else)
6. → **Journey Orchestration** (uses segments to trigger messages)
7. → **Audience Sync** (pulls from segments, pushes to platforms)
8. → **Monitoring & Optimization** (measures success)

---

## RESOURCES NEEDED

- **Development Time:** 4 hours/day × 12 weeks = ~250 hours
- **Testing:** Continuous (included above)
- **Monitoring:** 30 min/day ongoing
- **Tools:**
  - PostgreSQL (have ✅)
  - Wabis API (have ✅)
  - Meta API (have ✅)
  - Google Ads API (have ✅)
  - GA4 (have ✅)
  - APScheduler (Python library)
  - Google Data Studio (free)

---

## SUCCESS CRITERIA

**By Week 12, you should have:**
- ✅ Unified customer data layer (segments + journeys)
- ✅ Automated email sequences (6+ templates)
- ✅ WhatsApp messaging (8+ templates, high engagement)
- ✅ Meta audience sync (nightly, growing audiences)
- ✅ Google Ads list sync (nightly, targeting)
- ✅ Multi-touch attribution (understand which channel drove conversion)
- ✅ Real-time monitoring (funnel dashboard)
- ✅ A/B testing framework (continuous optimization)

**Metrics that matter:**
- Cold → Customer conversion: 2-4% (vs. 0.5% before)
- Email open rate: 30-45%
- WhatsApp click rate: 15-25%
- Meta ROAS: 3-5:1
- Customer lifetime value: ₹2,000+

---

**Ready to start? Pick one task from Week 1 and get moving. This is how you build 7-figure ecommerce businesses.**
