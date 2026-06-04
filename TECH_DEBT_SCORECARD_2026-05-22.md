# 📊 TECHNICAL DEBT & FEATURE DEPENDENCY SCORECARD
**Pureleven CRM - Risk & Effort Matrix**  
**May 22, 2026**

---

# SECTION 1: TECH DEBT BY SEVERITY

## 🔴 CRITICAL (Blocks Production)

### TD-001: No Authentication/Authorization
```
Severity: CRITICAL
Impact: Security breach, compliance violation
Scope: All 68 endpoints
Effort: 16 hours
Status: NOT IMPLEMENTED
Cost: 2 devs × 1 week

Current State:
├─ No API key validation
├─ No JWT tokens
├─ No role-based access
└─ Anyone can call any endpoint

Fix Steps:
├─ Implement APIKey model
├─ Add auth middleware
├─ Protect all endpoints
├─ Test enforcement
└─ Document security policy

Files Changed: 12
Deploy Risk: MEDIUM (must test thoroughly)
```

---

### TD-002: Route Definition Duplication
```
Severity: CRITICAL
Impact: Confusing architecture, maintenance nightmare
Scope: Journey endpoints (19 routes)
Effort: 6 hours
Status: NEEDS CONSOLIDATION

Current State:
├─ crm_routes.py has 19 journey endpoints
├─ journeys_routes.py has 19 journey endpoints
├─ Both are active, causing confusion
└─ No clear ownership

Fix Steps:
├─ Audit both files
├─ Move to journeys_routes.py
├─ Remove from crm_routes.py
├─ Update router registration
└─ Test all routes

Files Changed: 2
Deploy Risk: LOW (routes already tested)
```

---

### TD-003: API Response Format Inconsistency
```
Severity: CRITICAL
Impact: Client integration errors, API confusion
Scope: All endpoints
Effort: 12 hours
Status: NEEDS STANDARDIZATION

Current State:
├─ Some return {data: {...}}
├─ Some return {status, message}
├─ Some return raw data
└─ Error responses vary

Fix Steps:
├─ Create BaseResponse model
├─ Create ErrorResponse model
├─ Add error middleware
├─ Update all 68 endpoints
└─ Test error cases

Files Changed: 25
Deploy Risk: MEDIUM (must test all endpoints)
```

---

## 🟠 HIGH (Degrades Quality)

### TD-004: Missing Input Validation
```
Severity: HIGH
Impact: Data corruption, injection attacks
Scope: All POST/PUT endpoints (25 endpoints)
Effort: 18 hours
Status: PARTIAL (some models have validation)

Current State:
├─ Journey endpoints: Validated ✅
├─ Email endpoints: Partial ⚠️
├─ Lead endpoints: Missing ❌
└─ Segments: Validated ✅

Fix Steps:
├─ Create Pydantic models for all inputs
├─ Add validation decorators
├─ Test invalid inputs
└─ Document validation rules

Files Changed: 15
Deploy Risk: LOW
```

---

### TD-005: Database Query Performance
```
Severity: HIGH
Impact: Slow dashboards, high DB load
Scope: Analytics endpoints (6 endpoints)
Effort: 20 hours
Status: NEEDS OPTIMIZATION

Current State:
├─ N+1 query problems
├─ Full table scans
├─ No query pagination
└─ Analytics queries: 2-5 seconds

Fix Steps:
├─ Add query optimization
├─ Implement pagination
├─ Add database indexes
├─ Cache frequent queries
└─ Profile & test

Files Changed: 8
Deploy Risk: LOW
```

---

### TD-006: Incomplete Logging Strategy
```
Severity: HIGH
Impact: Hard to debug production issues
Scope: All route files
Effort: 12 hours
Status: AD-HOC LOGGING

Current State:
├─ console.log scattered
├─ No structured logging
├─ No log levels
└─ No context propagation

Fix Steps:
├─ Implement structured logging
├─ Add request correlation ID
├─ Set proper log levels
├─ Integrate with monitoring
└─ Document logging strategy

Files Changed: 20
Deploy Risk: LOW
```

---

## 🟡 MEDIUM (Nice to Fix)

### TD-007: Frontend State Management
```
Severity: MEDIUM
Impact: Hard to add features, state bugs
Scope: crmStore.js, component props
Effort: 15 hours
Status: NEEDS RESTRUCTURING

Current State:
├─ Zustand store exists
├─ No clear state structure
├─ Prop drilling in places
└─ State mutations scattered

Fix Steps:
├─ Restructure Zustand store
├─ Define clear state schema
├─ Reduce prop drilling
└─ Document state flow

Files Changed: 10
Deploy Risk: LOW
```

---

### TD-008: Dead Code & Cleanup
```
Severity: MEDIUM
Impact: Confusion, repository bloat
Scope: /tmp folder, old components, migrations
Effort: 5 hours
Status: NEEDS CLEANUP

Current State:
├─ /tmp folder: Old code
├─ Deleted components: Refs remain?
├─ Old migrations: Historical
└─ Commented code: Scattered

Fix Steps:
├─ Delete /tmp folder
├─ Remove dead imports
├─ Clean commented code
├─ Update .gitignore
└─ Document what was removed

Files Changed: 3
Deploy Risk: NONE
```

---

### TD-009: No Type Safety (JavaScript)
```
Severity: MEDIUM
Impact: Runtime errors, IDE limited help
Scope: All .jsx files (10 components)
Effort: 40 hours
Status: OPTIONAL (LOW PRIORITY)

Current State:
├─ Plain JavaScript
├─ No prop types
├─ No JSDoc types
└─ React DevTools only

Fix Steps:
├─ Add JSDoc types
├─ Add prop-types package (temporary)
├─ Or: Migrate to TypeScript (future)

Files Changed: 10
Deploy Risk: NONE (non-breaking)
```

---

## 🔵 LOW (Polish)

### TD-010: Test Coverage
```
Severity: LOW
Impact: Regressions slip through
Scope: All modules
Effort: 50 hours
Status: NOT STARTED (OPTIONAL)

Current State:
├─ 0% unit test coverage
├─ 0% integration tests
└─ Manual testing only

Plan:
├─ Backend: pytest + 70% coverage
├─ Frontend: Jest + React Testing Library
└─ E2E: Playwright tests

Benefit: High (prevents regressions)
ROI: Medium (time intensive)
Timeline: Weeks 10-12
```

---

### TD-011: Documentation Gaps
```
Severity: LOW
Impact: Slow onboarding, knowledge loss
Scope: Code comments, API docs, architecture
Effort: 15 hours
Status: GOOD (85% done)

Current State:
├─ API docs: Comprehensive ✅
├─ Database docs: Complete ✅
├─ Code comments: Partial ⚠️
├─ Architecture: Documented ✅
└─ Setup guide: Complete ✅

Fix Steps:
├─ Add function docstrings
├─ Add complex algorithm comments
├─ Update architecture diagram
└─ Create troubleshooting guide

Files Changed: 15
Impact: Knowledge base improvement
```

---

# SECTION 2: FEATURE DEPENDENCY MATRIX

## Feature Dependencies (What Must Be Done First)

```
┌─────────────────────────────────────────────────────────┐
│ FOUNDATION LAYER (MUST COMPLETE FIRST)                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  • Auth/Security (TD-001) ←── CRITICAL                  │
│  • API Standardization (TD-003)                         │
│  • Input Validation (TD-004)                            │
│  • Database Indexes                                     │
│  • Config Centralization                               │
│                                                         │
│  Approx Time: 1 week (40 hours)                        │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ FEATURE LAYER (DEPENDS ON FOUNDATION)                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Tier 1 (HIGH PRIORITY - 2 weeks):                      │
│  ├─ Lead Management (30% → 100%)                        │
│  ├─ Offline Conversion Matching (45% → 100%)            │
│  └─ CSV Import/Export (40% → 100%)                      │
│                                                         │
│  Tier 2 (MEDIUM PRIORITY - 2 weeks):                    │
│  ├─ Delhivery Integration (20% → 100%)                  │
│  ├─ Google Forms Integration (25% → 100%)               │
│  ├─ Meta Lead Ads (35% → 100%)                          │
│  └─ SMS Provider (30% → 100%)                           │
│                                                         │
│  Tier 3 (OPTIMIZATION - 2 weeks):                       │
│  ├─ Propensity Scoring (50% → 100%)                     │
│  ├─ Inventory Sync (0% → 100%)                          │
│  ├─ Abandoned Cart Automation (60% → 100%)              │
│  └─ Fraud Detection (20% → 100%)                        │
│                                                         │
│  Approx Time: 6 weeks (240 hours)                       │
└─────────────────────────────────────────────────────────┘
```

---

## Prerequisite Graph

```
REQUIRED FOR MULTIPLE FEATURES:
┌─ Auth/Security (TD-001)
│  ├─ Needed by: Lead Mgmt, All APIs
│  └─ Blocks: Everything until done
│
├─ API Standards (TD-003)
│  ├─ Needed by: New endpoints, existing endpoints
│  └─ Blocks: Feature deployment
│
├─ Input Validation (TD-004)
│  ├─ Needed by: Lead Mgmt, CSV Import, Integrations
│  └─ Blocks: Data integrity
│
├─ Database Enhancements
│  ├─ Needed by: Lead Mgmt, Inventory, Shipments
│  └─ Blocks: Data storage
│
└─ Config System
   ├─ Needed by: All integrations, APIs
   └─ Blocks: Configuration management

LEAD MANAGEMENT DEPENDS ON:
├─ Auth ✓ (needed first)
├─ API Standards ✓ (needed first)
├─ Database schema ✓ (in foundation)
└─ Input validation ✓ (in foundation)
   → Can START: Week 2

OFFLINE MATCHING DEPENDS ON:
├─ Auth ✓ (needed first)
├─ API Standards ✓ (needed first)
├─ ConversionFeed model ✓ (exists)
└─ Error handling ✓ (add in foundation)
   → Can START: Week 2 (parallel to Lead Mgmt)

INTEGRATIONS DEPEND ON:
├─ Auth ✓
├─ API Standards ✓
├─ Config System ✓
└─ Webhook/Event infrastructure ✓ (exists)
   → Can START: Week 4 (after foundation + features)
```

---

# SECTION 3: EFFORT ESTIMATES BY CATEGORY

## Breakdown of the 480-hour Recovery Plan

```
FOUNDATION (Week 1): 40 hours
├─ Auth Implementation: 16h
├─ Route Consolidation: 6h
├─ API Standardization: 12h
└─ Database Enhancements: 6h

FEATURES (Weeks 2-3): 80 hours
├─ Lead Management: 40h
│  ├─ Database & models: 6h
│  ├─ API endpoints: 12h
│  ├─ Backend logic: 15h
│  └─ Frontend UI: 7h
├─ Offline Matching: 25h
│  ├─ Email matching: 8h
│  ├─ Phone/address: 12h
│  └─ Error handling: 5h
└─ CSV Import/Export: 15h
   ├─ Backend: 7h
   ├─ Frontend: 3h
   └─ Validation: 5h

INTEGRATIONS (Weeks 4-5): 80 hours
├─ Delhivery: 30h
├─ Google Forms: 20h
├─ Meta Lead Ads: 15h
└─ SMS Provider: 15h

FEATURES (Weeks 6-7): 80 hours
├─ Propensity Scoring: 30h
├─ Abandoned Cart: 25h
├─ Inventory Sync: 15h
└─ Fraud Detection: 10h

OPTIMIZATION (Weeks 8-9): 80 hours
├─ Advanced Analytics: 35h
├─ Performance Tuning: 30h
└─ Security Hardening: 15h

POLISH & TESTING (Weeks 10-12): 120 hours
├─ Unit Tests: 40h
├─ Integration Tests: 30h
├─ Documentation: 20h
├─ Training: 15h
└─ Buffer/Contingency: 15h

TOTAL: 480 hours (12 weeks, 2 devs full-time)
```

---

## Effort Distribution by Team Size

| Team Size | Timeline | Quality | Risk | Cost |
|-----------|----------|---------|------|------|
| 2 devs | 12 weeks | High | Medium | $40K |
| 4 devs | 6 weeks | High | Low | $80K |
| 6 devs | 4 weeks | Medium | Very Low | $120K |
| 8 devs | 3 weeks | Medium | Low | $160K |

**Recommended**: 6 devs for 4 weeks = Best ROI/timeline balance

---

# SECTION 4: IMPACT & ROI ANALYSIS

## Feature Completion Impact on Revenue

```
Current State (71% complete):
├─ Missing Lead Management → Lost lead qualification → -5-10% pipeline
├─ Broken Offline Matching → Wrong attribution → -3-5% decision quality
├─ No Lead Scoring → Wasted marketing spend → -5% ROAS
├─ Incomplete Integrations → Manual work → +20% ops cost
└─ Total Revenue Impact: -13-20% / +20% ops cost

After Phase 0 (Auth + Standards): 75% complete
├─ Security risk eliminated
├─ Better data integrity
├─ No revenue change yet

After Phase 1 (Lead + Matching): 85% complete
├─ Lead management working
├─ Attribution correct
├─ Revenue impact: +8-12% (better targeting)
├─ Ops impact: -15% (less manual work)

After Phase 2 (Integrations): 90% complete
├─ All data sources connected
├─ Full automation possible
├─ Revenue impact: +5-8% (new channels)
├─ Ops impact: -20% (full automation)

After Phase 3 (Features): 95% complete
├─ Propensity model active
├─ Inventory managed
├─ Fraud prevented
├─ Revenue impact: +3-5% (better personalization)
├─ Ops impact: -10% (automation + prevention)

PROJECTED ROI:
├─ Investment: $120K (6 devs × 4 weeks)
├─ Revenue Gain: +20-35% (from -13-20% state)
├─ OpEx Savings: -$50K/year
├─ Payback Period: 1-2 months
└─ 12-Month ROI: 400-600%
```

---

# SECTION 5: RISK ASSESSMENT MATRIX

## Risks by Phase

```
PHASE 0 (Foundation):
┌─────────────────────────────────────────────┐
│ Risk: Auth middleware breaks existing code  │
│ Probability: MEDIUM (20%)                   │
│ Impact: HIGH (system down)                  │
│ Mitigation: Test in staging first           │
│ Contingency: Rollback plan in place         │
│                                             │
│ Risk: Route consolidation causes 404s       │
│ Probability: MEDIUM (15%)                   │
│ Impact: MEDIUM (users confused)             │
│ Mitigation: Thorough testing before deploy  │
│ Contingency: Keep duplicate routes temporary│
│                                             │
│ Risk: Config system doesn't load            │
│ Probability: LOW (5%)                       │
│ Impact: HIGH (system won't start)           │
│ Mitigation: Validate config before app init │
│ Contingency: Fallback to env vars           │
└─────────────────────────────────────────────┘

PHASE 1 (Lead Management):
┌─────────────────────────────────────────────┐
│ Risk: Lead table migration fails            │
│ Probability: LOW (5%)                       │
│ Impact: HIGH (data loss risk)               │
│ Mitigation: Backup before migration         │
│ Contingency: Rollback script ready          │
│                                             │
│ Risk: Lead scoring algorithm wrong          │
│ Probability: MEDIUM (25%)                   │
│ Impact: MEDIUM (bad leads ranked high)      │
│ Mitigation: Start with simple model         │
│ Contingency: Tune/improve iteratively       │
│                                             │
│ Risk: Lead → Customer conversion broken     │
│ Probability: LOW (10%)                      │
│ Impact: MEDIUM (leads lost)                 │
│ Mitigation: Unit test conversion logic      │
│ Contingency: Manual leads merge process     │
└─────────────────────────────────────────────┘

PHASE 2 (Integrations):
┌─────────────────────────────────────────────┐
│ Risk: Delhivery API unreliable              │
│ Probability: MEDIUM (30%)                   │
│ Impact: MEDIUM (tracking delayed)           │
│ Mitigation: Implement polling + retry       │
│ Contingency: Manual tracking URL override   │
│                                             │
│ Risk: Google Forms API auth fails           │
│ Probability: LOW (10%)                      │
│ Impact: MEDIUM (forms not linked)           │
│ Mitigation: OAuth flow tested thoroughly    │
│ Contingency: Admin can reauth manually      │
│                                             │
│ Risk: SMS provider rate limits              │
│ Probability: MEDIUM (20%)                   │
│ Impact: LOW (messages queued)               │
│ Mitigation: Implement queue + backoff       │
│ Contingency: Built-in retry system          │
└─────────────────────────────────────────────┘
```

---

# SECTION 6: SUCCESS CRITERIA

## Phase-by-Phase Success Metrics

### Phase 0 (Foundation) ✓
```
✓ All 68 endpoints require valid API key
✓ No duplicate route definitions
✓ All responses follow BaseResponse format
✓ All errors follow ErrorResponse format
✓ All inputs validated with Pydantic
✓ All config from environment
✓ Database indexes added, performance improved 30%
✓ Logging structured across all endpoints
```

### Phase 1 (Lead Management) ✓
```
✓ Lead CRUD endpoints working
✓ Lead-to-customer conversion working
✓ Lead scoring algorithm scoring 100+ leads
✓ Lead manager UI displaying all leads
✓ Lead status workflow (new → contacted → qualified → converted → lost)
✓ Lead enrichment hooks in place
✓ 0 errors in 1000 lead test
```

### Phase 2 (Integrations) ✓
```
✓ Delhivery API connected, 100 orders tracked
✓ Google Forms API working, 50 leads ingested
✓ Meta Lead Ads API working, leads auto-enrolled
✓ SMS provider sending messages, 100/100 success
✓ No critical errors in integration tests
✓ 0 data loss in conversion feeds
```

### Phase 3 (Features) ✓
```
✓ Propensity model scoring 10K+ customers
✓ Abandoned cart emails sending automatically
✓ Inventory synced from Shopify every hour
✓ Fraud detection flagging 100+ high-risk orders
✓ Performance: Analytics queries < 2 seconds
```

### Phase 4 (Optimization) ✓
```
✓ Advanced analytics dashboard rendering in < 1 second
✓ Database query count reduced by 60%
✓ Cache hit rate 80%+
✓ API error rate < 0.1%
✓ 99.9% uptime maintained
✓ Security audit passed
```

---

# SECTION 7: QUICK REFERENCE CHECKLIST

## Pre-Phase 0 Checklist (Do Before Starting)
- [ ] Read COMPREHENSIVE_PROJECT_AUDIT_2026-05-22.md
- [ ] Read this scorecard
- [ ] Assign Phase 0 lead (1 senior dev)
- [ ] Assign Phase 0 reviewer (1 senior dev)
- [ ] Create GitHub/Jira tasks
- [ ] Schedule daily standup
- [ ] Set up staging environment
- [ ] Backup production database
- [ ] Create rollback plan document
- [ ] Get team agreement on approach

## Phase 0 Completion Checklist
- [ ] Auth implemented + all endpoints protected
- [ ] Routes consolidated + all tests passing
- [ ] API responses standardized + docs updated
- [ ] Database indexes added + query time improved
- [ ] Config system implemented + all env vars documented
- [ ] Code cleaned up + old code removed
- [ ] Full regression test completed + passed
- [ ] Staging deployment successful
- [ ] Production deployment successful
- [ ] Monitoring alerts working
- [ ] Stakeholder notification sent

## Monitoring During Phases
```
Real-time Monitoring:
├─ API error rate (target: < 0.1%)
├─ API response time (target: < 500ms)
├─ Database connection pool (target: < 80% usage)
├─ WebSocket connections (target: stable)
├─ Queueing system depth (target: < 1000 items)
└─ Failed webhook deliveries (target: < 1%)

Daily Review:
├─ Slack notifications of errors
├─ Database size growth
├─ API rate limiting hits
└─ Customer complaints/support tickets
```

---

**END OF SCORECARD**

For detailed implementation instructions, see:
- `COMPREHENSIVE_PROJECT_AUDIT_2026-05-22.md` (Full audit, 5000+ lines)
- `EXECUTIVE_ACTION_PLAN_2026-05-22.md` (Quick action guide)
