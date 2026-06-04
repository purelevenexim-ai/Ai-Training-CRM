# Critical Implementation Questions (45+)

**Purpose:** Surface implementation risks before Sprint 0 coding begins.

---

## Database & Schema (8 Questions)

**Q1:** For existing `crm_orders` linked by email:
- What if customer changes email address after placing order?
- Should we fallback to Shopify customer ID for linking?
- Or is email → customer the permanent link?

**Q2:** The `dirty` flag on `customer_profiles`:
- When do we mark it dirty? Only on new events, or also on order updates?
- Should order webhooks from Shopify also mark profile dirty?
- What if dirty flag never gets cleared (Celery fails)?

**Q3:** `retroactively_linked_event_count` in `customer_identities`:
- After retroactively linking 10,000 events, does this slow down the identity_service?
- Should there be a limit (e.g., max 100 events retroactively linked)?
- Or link all historical events regardless of volume?

**Q4:** Session table `ended_at`:
- How do we detect 30-min inactivity if user never closes browser?
- Do we run a Celery job every 5 minutes to check `last_activity < NOW() - 30min`?
- Or rely on next event to calculate and backfill?

**Q5:** Index strategy for timeline queries:
- `customer_activity_feed(customer_id, occurred_at DESC)` — correct?
- Do we need `(customer_id, event_type, occurred_at)` for filtering by type?
- Or is one composite index enough?

**Q6:** Archiving old data:
- How long do we keep behavior_events? Forever?
- Do we partition tables by date for faster queries on old data?
- Or accept full-table scan on 1M+ events?

**Q7:** Customer master table uniqueness:
- Three unique columns: `shopify_customer_id`, `email`, `phone`
- What if same person has multiple emails? Create multiple customers?
- Or allow NULL and handle manually?

**Q8:** Foreign key constraints:
- Should `behavior_events.customer_id` have `ON DELETE SET NULL`?
- If customer deleted, keep event data for audit trail?
- Or cascade delete (lose all history)?

---

## Integration & Webhooks (8 Questions)

**Q9:** Shopify webhook deduplication:
- If Shopify retries webhook 3 times (same webhook_id), we insert 1 event?
- Or ignore all retries after first successful insert?
- What's the timeout for "ignore retry" (1 hour? 24 hours)?

**Q10:** Order timestamp discrepancy:
- Shopify webhook `created_at` vs. our processing time
- Should `behavior_events.occurred_at` be webhook timestamp or NOW()?
- If 1 hour old, do we still accept it or reject?

**Q11:** Webhook failure handling:
- If Shopify webhook fails to process (exception), do we:
  - Return 500 to Shopify (retry)?
  - Return 200 but log error (ignore)?
  - Queue for async retry?

**Q12:** Existing crm_orders updates:
- Shopify orders/paid webhook arrives again (duplicate customer)?
- Do we skip creating behavior_events if order already in crm_orders?
- Or always create (allows same order → multiple events)?

**Q13:** Browser attribution data:
- crm-attribution.js captures gclid/fbclid/utm_* on storefront
- Do we wait for Shopify webhook to link attribution to order?
- Or emit events immediately when user clicks (pre-purchase)?

**Q14:** Meta CAPI integration:
- Current: crm_routes.py sends to Meta (90% orders)
- New: Should behavior_events purchase also send to Meta?
- Or keep single integration point in crm_routes.py?

**Q15:** GA4 integration:
- Current: crm_routes.py sends purchase events
- New: Should page_view/product_view also emit to GA4?
- Or GA4 already captured client-side (no server send)?

**Q16:** Email capture timing:
- If visitor doesn't enter email until Order 2:
- Do we retroactively link all Session 1 events to customer?
- Retroactively emit "viewed product" events to Meta for order 1?

---

## Performance & Concurrency (8 Questions)

**Q17:** Profile rebuild Celery task:
- 100 customers marked dirty simultaneously
- 100 `rebuild_profile` tasks queue
- Does this hammer PostgreSQL (100 parallel reads)?
- Should we throttle (max 10 concurrent rebuilds)?

**Q18:** Event validation performance:
- EventValidator.validate() on every event
- If validation takes 10ms, and you get 100 events/sec:
- Does API response time become 1 second (blocked)?
- Need async validation?

**Q19:** Timeline pagination:
- Retrieve 50 timeline entries + context JSON:
- For 10,000 customer lookups/day, is this query N+1 problem?
- Or should we pre-fetch in batch?

**Q20:** Search customer by email:
- `ILIKE "%email%"` on 100k customers
- Full table scan each time?
- Or do indexes make this fast enough?
- What's acceptable response time (< 100ms? < 500ms)?

**Q21:** Retroactive event linking:
- Customer enters email on Order 2
- Query: 10,000 unlinked events for this visitor
- UPDATE 10k rows in behavior_events:
- Locks the table during UPDATE?
- Should we do this in batches?

**Q22:** Celery worker concurrency:
- docker-compose.yml specifies `--concurrency=4`
- Is 4 workers enough for 100 events/sec?
- Or need auto-scaling (10-20 workers)?

**Q23:** Redis memory:
- Celery task queue, result backend, sessions cache
- How much memory do we allocate?
- What happens when Redis memory full (evict?)?

**Q24:** Database connection pooling:
- pgBouncer pool_size=20, max_overflow=40
- Is 20 enough for 4 Celery workers + 1 API server?
- Or need 50+?

---

## Authentication & Authorization (5 Questions)

**Q25:** JWT token issuance:
- Who issues JWT tokens initially?
- Do we have a /auth/login endpoint?
- Or manual token generation?

**Q26:** Token expiration:
- JWT expires in 24 hours
- What happens when expired?
- Force re-login or auto-refresh?

**Q27:** Role-based access control:
- Support role: Can read single customer or all customers?
- Can Support export customer data (CSV)?
- Should search be limited by region/segment?

**Q28:** API key alternative:
- Should we support API keys (for integrations)?
- Or JWT tokens only?
- If API keys, store hashed in database?

**Q29:** Audit logging:
- Who accessed customer data?
- When? What fields?
- Should this be logged separately?

---

## Error Handling & Recovery (7 Questions)

**Q30:** Event validation failure:
- Invalid event stored in `event_errors`
- How do we alert? Slack? Email?
- Or just log and ignore?

**Q31:** Celery task failure:
- Profile rebuild task fails (DB connection error)
- Does Celery retry automatically?
- How many retries before giving up?

**Q32:** Missing customer identity:
- Event arrives without email/phone/shopify_id
- Can't link to customer
- Do we create anonymous event or reject?

**Q33:** Shopify webhook signature verification:
- Do we verify HMAC signature of webhook?
- Or trust all POST to /webhooks/shopify?
- What's the secret stored?

**Q34:** Database connection failure:
- API can't reach PostgreSQL
- Do we return 503 (service unavailable)?
- Or queue events in Redis and retry?

**Q35:** Timeline ordering corruption:
- Events arrive out of order (network delay)
- Order: Event A (10:30), Event B (10:29)
- Do we reorder by `occurred_at` or accept insertion order?

**Q36:** Duplicate event deduplication:
- Same browser emits "page_view" twice in 1 second
- Is it a duplicate or two separate views?
- How do we detect?

---

## Data & Privacy (6 Questions)

**Q37:** PII storage:
- We store email, phone, Shopify customer ID
- GDPR: Can customer request deletion?
- Do we delete behavior_events or anonymize?

**Q38:** Data retention policy:
- Delete behavior_events after 2 years?
- Keep customer_profiles forever?
- What about event_errors and processing_log?

**Q39:** Cross-order linking:
- Customer A buys on May 1, May 15, May 30
- Are all three orders linked to same customer?
- Or separate purchase events?

**Q40:** Customer merge:
- Duplicate customer records (same email, different ID)?
- How do we detect and merge?
- What happens to historical events?

**Q41:** Shopify webhook data retention:
- Shopify retries webhook for 48 hours
- We process in 1 second
- Safe to ignore after 48 hours?

**Q42:** Sensitive data in logs:
- Do we log event_data (contains email, prices)?
- Should sensitive fields be redacted?
- How to balance debugging vs. privacy?

---

## Business Logic (6 Questions)

**Q43:** Segment rules edge cases:
- Customer with LTV = 5000.01 is VIP?
- Or only > 5000?
- What about LTV = 4999.99 (repeat)?

**Q44:** Health score calculation:
- Formula: +25 for each metric
- What if only 1 metric true (health_score = 25)?
- Is 25 considered "at-risk"?

**Q45:** Activity feed aggregation:
- "Viewed Homepage (4 times)" — correct?
- Or should we show each separately?
- When do we aggregate (> 3 same views?)?

**Q46:** First-time customer detection:
- Customer segment = "first_time" means total_orders = 1?
- But profile might show first_seen yesterday, so not "new"?
- What's the correct definition for business?

**Q47:** At-risk segment:
- 60+ days since last activity
- But never purchased (prospect with no orders)
- Should they be "at_risk" or "prospect"?

---

## Operations & Deployment (7 Questions)

**Q48:** Monitoring & alerting:
- What metrics matter most?
- Event processing latency?
- Profile rebuild failures?
- Webhook processing lag?

**Q49:** Logging strategy:
- JSON structured logs or plain text?
- Which events to log (all or errors only)?
- Log retention (7 days? 30 days? Sentry?)?

**Q50:** VPS single point of failure:
- All services on one VPS (192.46.213.140)
- If VPS down, entire system down?
- Need backup strategy?

**Q51:** Database backup:
- How often backup PostgreSQL?
- Where stored (local? S3?)?
- RTO/RPO targets?

**Q52:** Zero-downtime deployment:
- How do we deploy new code without downtime?
- Docker rolling update?
- Separate staging environment?

**Q53:** Customer 360 UI deployment:
- Where is frontend hosted?
- Same VPS or separate?
- CDN for static assets?

**Q54:** Celery task idempotence:
- What if rebuild_profile task runs twice (duplication)?
- Safe to re-run or causes issues?
- How to ensure idempotency?

---

## Testing & QA (5 Questions)

**Q55:** E2E test scenario:
- Browser: User views product → adds to cart → purchases
- Should emit: page_view + product_view + add_to_cart + purchase?
- In that exact order?

**Q56:** Load testing:
- What's expected peak load?
- 1000 events/sec? 10,000?
- At what point do we need scaling?

**Q57:** Data integrity test:
- After 1M events, does customer_profiles match reality?
- Should we have reconciliation query?

**Q58:** Timeline consistency:
- Can user see events before they've entered email?
- Or only after identity linked?

**Q59:** Test data cleanup:
- After testing, delete test orders from crm_orders?
- Or mark with test_data = TRUE?

---

## Additional Edge Cases (8+ Questions)

**Q60:** Timezone handling:
- All timestamps UTC?
- Or convert to customer timezone?
- DST transitions?

**Q61:** Multi-currency:
- Future: Support multiple currencies?
- Exchange rate storage?
- For now, INR only?

**Q62:** Partial refunds:
- Order placed for ₹1000, refunded ₹300
- What's LTV (₹1000 or ₹700)?
- Does profile need order-level granularity?

**Q63:** Guest checkout:
- Non-registered customer purchases
- Where do we store email/phone?
- In crm_orders only, or create customer record?

**Q64:** Shopify customer ID format:
- `gid://shopify/Customer/123456` — correct?
- Or just numeric `123456`?
- How to normalize if inconsistent?

---

## Your Priorities

**Out of these 64 questions, which 10-15 are most critical for YOUR business?**

Pick the ones that matter most, and I'll lock in the implementation details before Sprint 0.

**Examples of priority picks:**
- Q17, Q20, Q21 (Performance concerns)
- Q37, Q38, Q41, Q42 (Privacy/Compliance concerns)
- Q9, Q10, Q11, Q12 (Webhook reliability concerns)
- Q48, Q50, Q51, Q54 (Operations/Reliability concerns)

Let me know which ones to focus on.
