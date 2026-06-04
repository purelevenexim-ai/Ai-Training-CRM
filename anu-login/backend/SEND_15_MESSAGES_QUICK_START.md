# 🚀 SEND ALL 15 MESSAGES - QUICK START GUIDE

**Status:** Ready to send  
**Recipient:** +919447744583  
**Interval:** 15 minutes (900 seconds) between each message  
**Total Time:** 3.5 hours (210 minutes)  
**Risk:** LOW (15-min intervals avoid Meta/WhatsApp rate limiting)  

---

## ⚡ QUICK START (1 minute)

### Option A: Send All 15 Now (Standard - Recommended)

```bash
cd /Users/bthomas/Documents/pureleven_dev/anu-login/backend

# Activate environment
source ../../.venv/bin/activate

# Start backend
python -m uvicorn app.main:app --reload --port 8000 &

# In another terminal, send all 15 messages at 15-min intervals
python automation/test_journey_cycle.py \
  --phone 9447744583 \
  --cycles 1 \
  --interval 900

# This will:
# - Send message 1 at T+0:00
# - Send message 2 at T+0:15
# - Send message 3 at T+0:30
# ... (continues for 3.5 hours total)
# - Send message 15 at T+3:30
```

### Option B: Send All 15 Immediately (Testing Only)

```bash
python automation/test_journey_cycle.py \
  --phone 9447744583 \
  --cycles 1 \
  --no-wait

# This will send all 15 messages instantly (no delays)
# ⚠️ Only for testing - avoid in production (Meta might rate limit)
```

### Option C: Send Custom Interval (For tuning)

```bash
# Send with 10-minute intervals instead
python automation/test_journey_cycle.py \
  --phone 9447744583 \
  --cycles 1 \
  --interval 600

# Send with 20-minute intervals
python automation/test_journey_cycle.py \
  --phone 9447744583 \
  --cycles 1 \
  --interval 1200
```

---

## 📊 WHAT TO EXPECT

### Timeline (15-minute intervals)

```
T+0:00   Message 1/15: lead_segment_question_v1 (Lead Journey starts)
T+0:15   Message 2/15: lead_trust_story_v1
T+0:30   Message 3/15: lead_social_proof_v1
T+0:45   Message 4/15: lead_education_v1
T+1:00   Message 5/15: lead_cta_urgency_v1 (Lead Journey ends)
         
T+1:15   Message 6/15: cart_curiosity_v1 (Abandoned Cart starts)
T+1:30   Message 7/15: cart_fomo_v1
T+1:45   Message 8/15: cart_risk_removal_v1
T+2:00   Message 9/15: cart_social_proof_v1
T+2:15   Message 10/15: cart_last_chance_v1 (Abandoned Cart ends)

T+2:30   Message 11/15: order_confirmed_trust_v1 (Purchased starts)
T+2:45   Message 12/15: order_excitement_v1
T+3:00   Message 13/15: order_quality_check_v1
T+3:15   Message 14/15: order_delight_story_v1
T+3:30   Message 15/15: order_repeat_offer_v1 (Purchased ends)

Total time: 3 hours 30 minutes
```

### What You'll See

**On your terminal (running the script):**
```
[2026-05-21T...] [INFO] Message 1/15 | Cycle 1/1 | LEAD Journey 1/5
[2026-05-21T...] [INFO] ✅ SENT
[2026-05-21T...] [INFO]    Template: lead_segment_question_v1
[2026-05-21T...] [INFO]    Psychology: explorer (confidence: 40%)
[2026-05-21T...] [INFO]    Conversion Probability: 30.0%
[2026-05-21T...] [INFO] ⏳ Waiting 900s (15min) before next message...
```

**On your WhatsApp phone (+919447744583):**
```
T+0:00  [Message 1] Hi Basil 👋 ... (lead segment question)
T+0:15  [Message 2] Hi Basil, ... (lead trust story)
T+0:30  [Message 3] Hi Basil, ... (lead social proof)
... (continues every 15 min)
```

**In database (logged):**
- All 15 messages recorded in `test_journey_log` table
- Each with: template_name, psychology_type, conversion_probability, status
- Timestamps showing exact send times

---

## 🛡️ AVOIDING META BLOCKING / RATE LIMITING

### ✅ Safe Rate: 15-minute intervals

**Why 15 minutes is safe:**
- Meta allows ~1,000+ messages per day from business account
- With 15-min intervals = 96 messages per day (safe)
- Standard WhatsApp template rate limit: 50 messages/minute (we're at 4/minute)
- Recommended minimum: 5-10 minute intervals for safety
- **15 minutes = Very conservative, zero risk**

### ⚠️ What to Avoid

**DON'T do this (will get rate limited):**
```bash
# Sending all instantly
--no-wait
→ 15 messages in <5 seconds
→ Risk: Medium (might get 1-2 hour temporary block)

# Sending very quickly
--interval 30
→ 15 messages in 7.5 minutes
→ Risk: Medium (similar to instant)

# Interval less than 5 minutes
--interval 300
→ 15 messages in 75 minutes (12 msgs/hr)
→ Risk: Low-Medium (borderline)
```

### ✅ What Meta Likes

```
Characteristics of safe sending:
- ✅ Consistent intervals (not random)
- ✅ Realistic timing (5+ minutes apart)
- ✅ Low volume per hour (not thousands)
- ✅ Using approved templates (we are)
- ✅ From verified business account (Wabis is verified)
- ✅ To opt-in customers (test number)

Our setup:
- 1 message every 15 minutes ✅ (Perfect)
- Total 15 messages ✅ (Low volume)
- 3.5 hour window ✅ (Spread out)
- All verified templates ✅ (Best practice)
- From Wabis API ✅ (Enterprise provider)
```

---

## 🔍 MONITORING DURING SEND

### What to watch for (all green = all good):

**Terminal Output:**
- ✅ Each message shows "✅ SENT"
- ✅ Template names are correct (lead_segment, lead_trust, etc.)
- ✅ Status shows "success" or "pending"
- ✅ Conversion probabilities range 30-50% (normal)
- ❌ If any message shows "❌ FAILED" → Note the error

**WhatsApp Phone:**
- ✅ Messages arrive roughly every 15 minutes
- ✅ Each message looks formatted correctly
- ✅ All verified facts present (pricing, contact, reviews)
- ❌ If message doesn't arrive → Check terminal for error
- ❌ If blocked message appears → Stop immediately

**Wabis Dashboard:**
- ✅ Go to: https://app.wabis.in/dashboard
- ✅ Check "Message Logs" for delivery status
- ✅ Should show 15 messages sent within 3.5 hour window
- ❌ If "Failed" or "Undelivered" → Investigate reason

### Error Codes & How to Handle

| Error | Meaning | Action |
|-------|---------|--------|
| `Network Timeout` | Connection issue | Retry send |
| `Template not found` | Template missing in Wabis | Create template first |
| `Rate Limited` | Meta blocked us | Wait 1-2 hours, retry |
| `Invalid Phone` | Phone number format wrong | Use E.164 format |
| `Conversation window closed` | Outside 24h window | New conversation needed |

---

## 🔧 BEFORE YOU SEND

### Checklist:

```
PREPARATION
[ ] Backend running (python -m uvicorn app.main:app --port 8000)
[ ] Database ready (anu_login.sqlite3 exists)
[ ] Wabis connected (API key in .env)
[ ] All 15 templates verified ✅
[ ] Manual review document reviewed ✅

READY TO SEND
[ ] Phone number is: +919447744583 (confirm)
[ ] Interval is: 15 minutes (900 sec) (confirm)
[ ] Cycles: 1 (15 messages total) (confirm)
[ ] You have 3.5 hours available to monitor (confirm)
[ ] WhatsApp app open on test phone (confirm)

GO
[ ] All checks passed ✅
[ ] Running: python automation/test_journey_cycle.py --phone 9447744583 --cycles 1 --interval 900
[ ] Monitoring terminal for errors
[ ] Watching messages arrive on phone
[ ] No blocks or errors after first 3 messages = All good!
```

---

## 📱 WHAT HAPPENS AFTER SEND

### Immediate (During 3.5 hour window):
- ✅ Each message sent via Wabis API
- ✅ Logged to database with timestamp
- ✅ Arrives on +919447744583 phone
- ✅ Includes psychology classification
- ✅ Tracks conversion probability

### After Complete:
- ✅ View all 15 messages in test_journey_log table
- ✅ Analyze which psychology type customer classified as
- ✅ Note conversion probability progression
- ✅ Check no rate limiting occurred
- ✅ Verify Meta didn't block account

### Next Steps:
1. Review all 15 messages received
2. Check database log for completeness
3. Analyze psychology classification accuracy
4. If no issues: Ready to deploy to Wabis for production
5. If issues: Debug and re-run

---

## 🎯 COMMAND COPY-PASTE

### Ready? Just copy-paste this:

```bash
# 1. Navigate to backend
cd /Users/bthomas/Documents/pureleven_dev/anu-login/backend

# 2. Activate environment
source ../../.venv/bin/activate

# 3. Ensure backend is running in another terminal
# (if not already running)
# python -m uvicorn app.main:app --reload --port 8000 &

# 4. Send all 15 messages at 15-minute intervals
python automation/test_journey_cycle.py \
  --phone 9447744583 \
  --cycles 1 \
  --interval 900

# Watch the output. Each message takes ~2-3 sec to send,
# then waits 15 minutes before next.
# Total time: 3.5 hours

# Keep this terminal open during entire 3.5 hour window
# (or let it run in background with nohup)
```

---

## 💡 PRO TIPS

### Run in Background (recommended):

```bash
# Start in background, save output to file
nohup python automation/test_journey_cycle.py \
  --phone 9447744583 \
  --cycles 1 \
  --interval 900 \
  > journey_send_log.txt 2>&1 &

# Check progress anytime:
tail -f journey_send_log.txt

# Find process if needed:
pgrep -f "test_journey_cycle.py"
```

### Run Multiple Times (not recommended):

If you want to send to different phone numbers:
```bash
# Send to phone A
python automation/test_journey_cycle.py --phone 9123456789 --cycles 1 --interval 900 &

# Send to phone B (in background, different terminal)
python automation/test_journey_cycle.py --phone 9987654321 --cycles 1 --interval 900 &

# Both will run in parallel, 15-min intervals on each
```

---

## ✨ SUCCESS CRITERIA

You're done when:
- ✅ All 15 messages sent (shown in terminal)
- ✅ All 15 messages received on phone
- ✅ No errors in terminal output
- ✅ No WhatsApp blocks or warnings
- ✅ Database shows 15 entries in test_journey_log
- ✅ Ready to proceed to Wabis template creation

---

## 🚀 READY?

**Say "SEND NOW" when you're ready to launch all 15 messages!**

I'll confirm setup and run the command.

---

## 📞 SUPPORT

If anything goes wrong during send:

**Message failed?**
- Check terminal output for error
- Verify backend is running (port 8000 open)
- Check Wabis dashboard for template issues
- Retry with `--no-wait` to test instantly

**Rate limited?**
- Wait 1-2 hours before retrying
- Use 20-minute intervals next time
- Contact Wabis if continues

**Not receiving on phone?**
- Verify +919447744583 is correct
- Check WhatsApp app has message notifications on
- Verify Wabis conversation window is open (24h from first message)

**Questions?**
- See MANUAL_REVIEW_ALL_15_MESSAGES.md for message content
- See WABIS_TEMPLATES_GUIDE_VERIFIED.md for template facts
- Check database: SELECT * FROM test_journey_log LIMIT 1

---

**All set! Ready to send all 15 messages?** ✅
