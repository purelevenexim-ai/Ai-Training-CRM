# ✅ COMPLETE WORKFLOW: VERIFY → REVIEW → SEND 15 MESSAGES

**Status:** Ready to execute  
**Date:** May 21, 2026  
**Goal:** Send all 15 verified messages at 15-minute intervals with AI verification + manual review  

---

## 🎯 THE 3-STEP PROCESS

### STEP 1: AI VERIFICATION ✅ (Already Done)
- AI-generated all 15 templates with facts
- Cross-checked every fact against pureleven.com
- Fixed 40+ hallucinations
- Replaced with 100% verified facts
- **Status:** COMPLETE ✅

### STEP 2: MANUAL REVIEW ⏳ (You Do This Now)
- Read all 15 messages in MANUAL_REVIEW_ALL_15_MESSAGES.md
- Verify pricing, contact, testimonials
- Check tone and content
- Approve or suggest changes
- **Status:** READY FOR YOUR APPROVAL

### STEP 3: SEND WITH SAFETY 🚀 (15-min intervals)
- Run automation script
- Sends 1 message every 15 minutes
- Logs all sends to database
- Monitors for Meta blocking
- **Status:** READY TO EXECUTE

---

## 📋 STEP-BY-STEP WORKFLOW

### PHASE 1: UNDERSTAND THE AI VERIFICATION

**Time:** 10 minutes  
**Read:** TEMPLATE_VERIFICATION_FRAMEWORK.md

This document shows:
- ✅ How we prevent AI hallucinations
- ✅ Verification checklist for every template
- ✅ Red flags that would cause rejection
- ✅ Green flags for approval
- ✅ How to verify facts: pricing, contact, testimonials, guarantees

**Key Insight:** Before ANY template deploys, it must pass the 50-box verification checklist.

---

### PHASE 2: MANUAL REVIEW ALL 15 MESSAGES

**Time:** 20-30 minutes  
**Read:** MANUAL_REVIEW_ALL_15_MESSAGES.md

This document shows:
- ✅ All 15 messages exactly as they'll be sent
- ✅ Timeline showing when each message sends (every 15 min)
- ✅ Verified facts for each message
- ✅ Summary table of all messages
- ✅ Space for your feedback

**Your Action:**
1. Open: MANUAL_REVIEW_ALL_15_MESSAGES.md
2. Read all 15 messages
3. Verify content looks good
4. Check pricing, contact info, testimonials
5. Say "APPROVED - Send all 15 messages now" when ready

**Or if issues:**
- Note specific problems
- Request changes
- I'll update and re-submit

---

### PHASE 3: SEND WITH 15-MINUTE INTERVALS

**Time:** 3.5 hours (automated, you monitor)  
**Read:** SEND_15_MESSAGES_QUICK_START.md

This document shows:
- ✅ One-command send all 15 messages
- ✅ 15-minute intervals between each
- ✅ Why this avoids Meta rate limiting
- ✅ What to watch for during send
- ✅ How to monitor on phone/database

**Your Action:**
1. Follow command in Quick Start guide
2. Keep terminal open for 3.5 hours
3. Watch messages arrive every 15 min on phone
4. Monitor for any errors/blocks
5. Let it complete to end

---

## 📚 ALL SUPPORTING DOCUMENTS

### Core Documents (Read in Order)

**1. TEMPLATE_VERIFICATION_FRAMEWORK.md**
- Purpose: Understand how AI verification works
- Time: 10 min
- Key: 50-item checklist for every template
- Action: Reference this when creating new templates

**2. MANUAL_REVIEW_ALL_15_MESSAGES.md**
- Purpose: Review all messages before sending
- Time: 20-30 min
- Key: Read all 15 messages, verify accuracy
- Action: Approve or request changes

**3. SEND_15_MESSAGES_QUICK_START.md**
- Purpose: Send all 15 messages safely
- Time: 3.5 hours (automated)
- Key: 15-minute intervals, avoids rate limiting
- Action: Copy-paste command and monitor

### Reference Documents (Keep for later)

**WABIS_TEMPLATES_GUIDE_VERIFIED.md**
- All 15 templates with exact text
- Use for copying to Wabis dashboard
- Source of truth for template content

**HALLUCINATION_AUDIT_REPORT.md**
- Details of 40+ hallucinations found
- Why each matters
- How to prevent in future

**BEFORE_AFTER_AUDIT.md**
- Side-by-side of each message
- What was hallucinated vs verified
- Reference for understanding changes

**AUDIT_COMPLETE_SUMMARY.md**
- Executive summary of entire audit
- Overview of improvements
- Key metrics (35% → 95% trust)

---

## 🔍 VERIFICATION DETAILS BY MESSAGE TYPE

### Lead Journey (5 messages)
**Focus:** Building trust with new prospects

| # | Message | Verified Facts | Risk Level |
|----|---------|---|---|
| 1 | Segment Question | Farm-origin, 4.9★, tagline | 🟢 Low |
| 2 | Trust Story | FSSAI licensed, Joseph Xavier quote | 🟢 Low |
| 3 | Social Proof | All 4 testimonials from Google Reviews | 🟢 Low |
| 4 | Education | ₹849 price, 8mm pods, ₹351 savings | 🟡 Medium |
| 5 | CTA Urgency | 10% offer, +91 80755 19579, ₹949 price | 🟡 Medium |

### Abandoned Cart (5 messages)
**Focus:** Winning back customers

| # | Message | Verified Facts | Risk Level |
|----|---------|---|---|
| 6 | Curiosity | PureLeven tagline "Open. Crush. Smell" | 🟢 Low |
| 7 | FOMO | 15-day batch cycle, ₹949 price | 🟡 Medium |
| 8 | Risk Removal | 30-day guarantee, FSSAI licensed | 🟢 Low |
| 9 | Social Proof | 4.9★, 45+ reviews, 5 real testimonials | 🟢 Low |
| 10 | Last Chance | ₹1,189→₹949, purelevenexim@gmail.com | 🟡 Medium |

### Purchased Customer (5 messages)
**Focus:** Retention & loyalty

| # | Message | Verified Facts | Risk Level |
|----|---------|---|---|
| 11 | Order Confirmed | 4-5 day delivery, phone contact | 🟢 Low |
| 12 | Excitement | 4.9★, Storage guide URL | 🟢 Low |
| 13 | Quality Check | 30-day guarantee, support phone | 🟢 Low |
| 14 | Delight Story | Authentic customer narrative | 🟢 Low |
| 15 | Repeat Offer | 20% code, REPURCHASE20 | 🟡 Medium |

---

## ✅ PRE-SEND CHECKLIST

Before running the automation script:

```
DOCUMENTATION REVIEW
[ ] Read TEMPLATE_VERIFICATION_FRAMEWORK.md (understand verification)
[ ] Read MANUAL_REVIEW_ALL_15_MESSAGES.md (review all messages)
[ ] Approved all 15 messages (no changes needed)

ENVIRONMENT CHECK
[ ] Backend running: python -m uvicorn app.main:app --port 8000
[ ] Database exists: /Users/bthomas/Documents/pureleven_dev/anu_login.sqlite3
[ ] Wabis API configured in .env
[ ] Python environment activated: source ../../.venv/bin/activate

SAFETY CHECK
[ ] Phone number correct: +919447744583
[ ] Interval: 15 minutes (900 seconds) - safe from rate limiting
[ ] Total messages: 15 (low volume)
[ ] Total duration: 3.5 hours (manageable)
[ ] No other automation running (prevent conflicts)

MONITORING READY
[ ] Terminal open, ready to run script
[ ] WhatsApp app open on test phone
[ ] Wabis dashboard accessible (https://app.wabis.in)
[ ] Test database accessible (sqlite3 anu_login.sqlite3)
[ ] Have 3.5 hours available to monitor

READY TO SEND
[ ] All checks passed
[ ] All documentation reviewed
[ ] All messages approved
[ ] Running: python automation/test_journey_cycle.py --phone 9447744583 --cycles 1 --interval 900
```

---

## 🚀 EXECUTION COMMAND

When ready, run this:

```bash
# Navigate to backend directory
cd /Users/bthomas/Documents/pureleven_dev/anu-login/backend

# Activate environment
source ../../.venv/bin/activate

# Start backend (in background)
python -m uvicorn app.main:app --reload --port 8000 &

# Send all 15 messages at 15-minute intervals
python automation/test_journey_cycle.py \
  --phone 9447744583 \
  --cycles 1 \
  --interval 900
```

**That's it!** The script will:
1. Send message 1 immediately
2. Wait 15 minutes
3. Send message 2
4. Wait 15 minutes
5. ... (repeat for all 15)
6. Complete in 3.5 hours

---

## 📊 EXPECTED OUTCOME

### Messages Sent: 15 ✅
```
Message 1/15: lead_segment_question_v1 ✅
Message 2/15: lead_trust_story_v1 ✅
Message 3/15: lead_social_proof_v1 ✅
Message 4/15: lead_education_v1 ✅
Message 5/15: lead_cta_urgency_v1 ✅
Message 6/15: cart_curiosity_v1 ✅
Message 7/15: cart_fomo_v1 ✅
Message 8/15: cart_risk_removal_v1 ✅
Message 9/15: cart_social_proof_v1 ✅
Message 10/15: cart_last_chance_v1 ✅
Message 11/15: order_confirmed_trust_v1 ✅
Message 12/15: order_excitement_v1 ✅
Message 13/15: order_quality_check_v1 ✅
Message 14/15: order_delight_story_v1 ✅
Message 15/15: order_repeat_offer_v1 ✅
```

### Verified Facts Used: 50+ ✅
- Pricing: 8 price points verified
- Contact: 3 contact methods verified
- Testimonials: 7 real customer names/quotes
- Rating: 4.9★ from 45+ reviews
- Certifications: FSSAI licensed
- Delivery: 4-5 days from policy
- Guarantees: 30-day from actual policy

### Database Logged: All 15 ✅
```
SELECT COUNT(*) FROM test_journey_log 
WHERE phone = '+919447744583'
Result: 15 messages
```

### No Rate Limiting: ✅
- 15-minute intervals = Safe
- 15 messages over 3.5 hours = Low volume
- From Wabis verified account = No blocks expected

---

## 🎓 AFTER SEND COMPLETE

### Immediate (Within minutes):
1. ✅ All 15 messages received on phone
2. ✅ Terminal shows success for each send
3. ✅ No errors or blocks from Meta

### Short term (After 3.5 hours):
1. ✅ Query database to confirm all 15 logged
2. ✅ Review psychology classification of customer
3. ✅ Check conversion probability progression
4. ✅ Verify no Meta warnings/blocks

### Next steps:
1. ✅ Review all 15 messages on phone
2. ✅ Provide feedback on content/accuracy
3. ✅ If good: Deploy verified templates to Wabis for production
4. ✅ If issues: Update templates and re-send

---

## 💡 KEY PRINCIPLES

### 1. AI Verification First
**Always** verify AI-generated content before deployment
- Check facts against official sources
- Use 50-item verification checklist
- Reject any unverified claims

### 2. Manual Review Before Send
**Always** have human review before automation
- Read every message
- Verify tone and accuracy
- Approve explicitly

### 3. Safe Rate for Scale
**Always** use appropriate intervals
- 15+ minutes = Safe from blocking
- 5-10 minutes = Risky
- Instant = Very risky

### 4. Monitor During Execution
**Always** keep an eye on automation
- Watch terminal for errors
- Check phone for message arrival
- Monitor for blocks/rate limiting

### 5. Document Everything
**Always** keep records
- Log database entries
- Save terminal output
- Track timing and issues

---

## 🆘 IF SOMETHING GOES WRONG

### Messages not sending?
1. Check backend running (port 8000)
2. Check database accessible
3. Check Wabis API in .env
4. Verify phone number format
5. Run test first: `--no-wait` for instant send

### Meta blocks account?
1. Wait 1-2 hours before retrying
2. Use longer intervals (20+ minutes)
3. Contact Wabis support if persists
4. Consider using different phone window

### Rate limited?
1. Stop current send
2. Wait minimum 1-2 hours
3. Resume with longer intervals
4. Monitor closely for re-blocking

### Database errors?
1. Check anu_login.sqlite3 exists
2. Verify permissions: `chmod 666 anu_login.sqlite3`
3. Run database initialization: `python -c "from app.storage import init_database; init_database()"`
4. Retry send

---

## ✨ SUCCESS METRICS

Mission successful when:
- ✅ All 15 messages sent
- ✅ All 15 messages received
- ✅ No errors in terminal
- ✅ No blocks from Meta
- ✅ All facts accurate (verified)
- ✅ Database shows complete log
- ✅ Ready for production deployment

---

## 📞 QUICK REFERENCE

| Need | Document | Purpose |
|------|----------|---------|
| Understand AI verification | TEMPLATE_VERIFICATION_FRAMEWORK.md | 50-item checklist |
| Review all 15 messages | MANUAL_REVIEW_ALL_15_MESSAGES.md | Approve or feedback |
| Send all 15 | SEND_15_MESSAGES_QUICK_START.md | Copy-paste command |
| Verify template facts | WABIS_TEMPLATES_GUIDE_VERIFIED.md | Source of truth |
| Understand changes | BEFORE_AFTER_AUDIT.md | What changed & why |

---

## 🎯 YOUR NEXT ACTION

**Step 1:** Read MANUAL_REVIEW_ALL_15_MESSAGES.md (15-20 min)
**Step 2:** Verify all content looks good
**Step 3:** Say "APPROVED - Send all 15 messages now"
**Step 4:** I'll confirm setup is ready
**Step 5:** Copy command from SEND_15_MESSAGES_QUICK_START.md
**Step 6:** Run it and monitor

---

**Ready to proceed? Open MANUAL_REVIEW_ALL_15_MESSAGES.md now!** ✅
