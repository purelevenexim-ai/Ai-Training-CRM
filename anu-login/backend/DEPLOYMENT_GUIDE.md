# 🚀 Marketing Psychology Journey - Deployment & Execution Guide

## 📊 Complete System Architecture

You now have a **6-layer AI-driven customer journey system** that sends 15 personalized WhatsApp messages over 5 hours, analyzing customer psychology at each step.

### Layers Implemented:

1. **Psychology Classification Engine** (`psychology_engine.py`)
   - Classifies customers into 5 psychology types: explorer, skeptic, price_sensitive, quality_focused, urgent_buyer
   - Calculates confidence scores, conversion probability
   - Enables adaptive messaging

2. **Story Generation & Rotation** (`story_engine.py`)
   - 4 story libraries (origin, transformation, founder, community)
   - Prevents message fatigue through rotation logic
   - Adapts storytelling based on customer psychology

3. **Message Template Library** (`whatsapp_templates.py`)
   - 15 new message stages (5 per journey type)
   - Dynamic parameter substitution
   - UTM tracking on all links

4. **REST API Endpoints** (`/api/test/journey/*`)
   - `POST /api/test/journey/cycle` - Send next message
   - `GET /api/test/journey/log` - View all messages
   - `GET /api/test/journey/export` - CSV export
   - `POST /api/test/journey/reset` - Clear test data

5. **Database Logging** (`test_journey_log` table)
   - Tracks every message with psychology metadata
   - Records conversion probability
   - Enables post-campaign analysis

6. **Automation Script** (`automation/test_journey_cycle.py`)
   - Sends 15 messages over 5 hours (20-min intervals)
   - Beautiful CLI with real-time logging
   - Can skip waits for rapid testing

---

## 📁 Files Created/Modified

### New Files:
```
backend/app/psychology_engine.py              (300 lines) ✅
backend/app/story_engine.py                   (400 lines) ✅
backend/app/routes/test_journey.py            (250 lines) ✅
backend/automation/test_journey_cycle.py      (400 lines) ✅
backend/WABIS_TEMPLATES_GUIDE.md              (Template specs)
```

### Modified Files:
```
backend/app/main.py                           (+ test_journey router) ✅
backend/app/storage.py                        (+ test_journey_log table) ✅
backend/app/whatsapp_templates.py             (+ 15 new message stages) ✅
```

---

## ✅ Pre-Deployment Checklist

### 1. Database Schema
- [ ] Run: `cd /Users/bthomas/Documents/pureleven_dev/anu-login && python -c "from app.storage import init_database; init_database()"`
- [ ] Verify: `sqlite3 anu_login.sqlite3 ".schema test_journey_log"`
- [ ] Expected output: Should show test_journey_log table with 13 columns

### 2. Python Dependencies
All required packages already installed. Verify:
```bash
pip list | grep -E "fastapi|requests|pydantic"
```

### 3. Backend Start
```bash
cd /Users/bthomas/Documents/pureleven_dev/anu-login/backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 4. Create Wabis Templates
1. Visit: https://app.wabis.in/dashboard
2. Go to: **Templates → Create New Template**
3. Create all 15 templates as specified in [WABIS_TEMPLATES_GUIDE.md](WABIS_TEMPLATES_GUIDE.md)
4. Approve each template
5. **Critical:** Template names must match exactly:
   - `lead_segment_question_v1` (not lead_segment_question)
   - `lead_trust_story_v1` (not lead_story_trust)
   - etc.

---

## 🎯 Execution Guide

### **Option A: Full 5-Hour Test (Recommended First Time)**

```bash
cd /Users/bthomas/Documents/pureleven_dev/anu-login/backend

python3 automation/test_journey_cycle.py \
  --phone 9447744583 \
  --cycles 3 \
  --interval 1200
```

**What happens:**
- ✅ Cycle 1 (Lead): 5 messages over ~100 minutes
- ✅ Cycle 2 (Abandoned): 5 messages over ~100 minutes
- ✅ Cycle 3 (Purchased): 5 messages over ~100 minutes
- ✅ Total: 15 messages over 300 minutes (5 hours)
- ✅ You receive WhatsApp message every 20 minutes
- ✅ All messages logged to database with psychology analysis

**Timeline:**
```
00:00  → Message 1: Lead segment question
20:00  → Message 2: Lead trust story
40:00  → Message 3: Lead social proof
60:00  → Message 4: Lead education
80:00  → Message 5: Lead CTA urgency
100:00 → Message 6: Abandoned cart curiosity
...
300:00 → Message 15: Purchase repeat offer
```

---

### **Option B: Rapid Test (5 Minutes)**

For quick validation without waiting:

```bash
python3 automation/test_journey_cycle.py \
  --phone 9447744583 \
  --cycles 3 \
  --no-wait
```

**What happens:**
- ✅ All 15 messages sent immediately (no 20-minute waits)
- ✅ You receive rapid-fire WhatsApp messages
- ✅ Same logging and psychology analysis
- ⏱️ Total duration: ~30 seconds (much faster for testing)

---

### **Option C: Single Journey Test**

Test just one journey type (5 messages):

```bash
# Test lead journey only
for i in 1 2 3 4 5; do
  curl -X POST http://localhost:8000/api/test/journey/cycle \
    -H "Content-Type: application/json" \
    -d "{\"phone\": \"9447744583\", \"journey_type\": \"lead\", \"iteration\": $i, \"shop_domain\": \"pureleven.com\"}"
  sleep 2
done
```

---

### **Option D: Monitor Live**

View messages being sent in real-time:

```bash
# In a separate terminal:
watch -n 5 "curl -s http://localhost:8000/api/test/journey/log?phone=9447744583 | python -m json.tool"
```

This will refresh every 5 seconds showing all messages sent.

---

## 📊 Expected Output

### Console Output
```
================================================================================
  🎯 PURELEVEN MARKETING PSYCHOLOGY JOURNEY DEMO
================================================================================

[2025-01-15T10:30:45.123456+00:00] [INFO] Phone: +919447744583
[2025-01-15T10:30:45.234567+00:00] [INFO] Cycles: 3
[2025-01-15T10:30:45.345678+00:00] [INFO] Interval: 1200s (20min)
[2025-01-15T10:30:45.456789+00:00] [INFO] Total Messages: 15
[2025-01-15T10:30:45.567890+00:00] [INFO] Total Duration: ~300 minutes

================================================================================
  📤 SENDING MESSAGES
================================================================================

[2025-01-15T10:30:50.000000+00:00] [INFO] Message 1/15 | Cycle 1/3 | LEAD Journey 1/5
[2025-01-15T10:30:52.123456+00:00] [INFO] ✅ SENT
[2025-01-15T10:30:52.234567+00:00] [INFO]    Template: lead_segment_question_v1
[2025-01-15T10:30:52.345678+00:00] [INFO]    Stage: lead_segment_question
[2025-01-15T10:30:52.456789+00:00] [INFO]    Psychology: explorer (confidence: 72%)
[2025-01-15T10:30:52.567890+00:00] [INFO]    Conversion Probability: 42.5%
[2025-01-15T10:30:52.678901+00:00] [INFO] ⏳ Waiting 1200s (20min) before next message...
[2025-01-15T10:30:52.789012+00:00] [INFO]    1200s remaining...
[2025-01-15T10:30:52.890123+00:00] [INFO]    1140s remaining...
...
```

### WhatsApp Messages You'll Receive

**Message 1 (Lead):**
```
Hi there 👋

Thanks for reaching out to Pureleven.

Can I quickly ask?

Are you looking for products for:

1️⃣ Home use
2️⃣ Retail shop
3️⃣ Wholesale / Bulk

Reply with 1, 2 or 3 😊

Check out: https://pureleven.com...
```

**Message 2 (Lead):**
```
Hi,

Most people who contact us are surprised by one thing.

They've often been buying products that look pure but contain fillers or low-grade ingredients.

That's exactly why Pureleven was started.

We wanted products we'd confidently give our own family ❤️

You can check our products here:
👉 https://pureleven.com...

Not selling. Storytelling.
```

*...and so on for 15 messages total...*

### Database Log

Query the results:
```bash
sqlite3 anu_login.sqlite3 << 'EOF'
SELECT 
  timestamp,
  message_stage,
  template_name,
  psychology_type,
  conversion_probability,
  status
FROM test_journey_log
WHERE phone = '+919447744583'
ORDER BY created_at ASC;
EOF
```

Expected output:
```
timestamp                     | message_stage          | template_name          | psychology | probability | status
------------------------------|------------------------|------------------------|-----------|-------------|--------
2025-01-15 10:30:52.123456   | lead_segment_question | lead_segment_question_v1 | explorer  | 42.5        | sent
2025-01-15 10:50:52.234567   | lead_trust_story      | lead_trust_story_v1      | explorer  | 45.2        | sent
...
```

---

## 🔧 Troubleshooting

### Problem: "Template does not exist"
**Solution:** Check WABIS_TEMPLATES_GUIDE.md and create missing templates. Template names are case-sensitive.

### Problem: "Phone number invalid"
**Solution:** Use either:
- 10-digit format: `9447744583`
- 12-digit format: `919447744583`
- E.164 format: `+919447744583`

### Problem: "No messages received on WhatsApp"
**Check:**
1. Verify WhatsApp conversation window is open (24h after first contact)
2. Check API logs: `curl http://localhost:8000/api/test/journey/log?phone=9447744583`
3. Check Wabis dashboard for send failures
4. Verify templates are APPROVED (not just PENDING)

### Problem: Backend won't start
**Solution:**
```bash
# Check Python version
python --version  # Should be 3.10+

# Reinstall dependencies
pip install -r backend/requirements.txt

# Run init_database
python -c "from app.storage import init_database; init_database()"

# Try starting again
python -m uvicorn app.main:app --reload
```

### Problem: Psychology classification seems wrong
**Solution:** Edit `psychology_engine.py` line 80-120 to adjust scoring rules based on test results

---

## 📈 Post-Execution Analysis

### Export CSV
```bash
curl -s http://localhost:8000/api/test/journey/export?phone=9447744583 \
  > journey_messages.csv
```

### Key Metrics to Track

1. **Delivery Rate**: How many of 15 sent successfully?
2. **Psychology Distribution**: Which types most common?
3. **Conversion Probability Trend**: Does it increase over journey?
4. **Stage Performance**: Which message stage gets best engagement?

### Example Analysis
```python
import pandas as pd

df = pd.read_csv('journey_messages.csv')

# Delivery rate by journey
print(df.groupby('journey_type')['status'].value_counts())

# Average conversion probability by journey
print(df.groupby('journey_type')['conversion_probability'].mean())

# Psychology type distribution
print(df['psychology_type'].value_counts())
```

---

## 🎓 Learning & Extension

### What You Learned
- ✅ Psychology-based customer segmentation
- ✅ Dynamic message adaptation without hard-coding
- ✅ Story rotation to prevent fatigue
- ✅ Real-time conversion probability scoring
- ✅ Complete customer journey orchestration

### Next Steps
1. **Analyze Results**: Review which messages converted best
2. **Refine Psychology**: Adjust rules in `psychology_engine.py` based on real behavior
3. **Expand Stories**: Add more variants to `story_engine.py`
4. **Scale**: Deploy to production with real customer phone numbers
5. **Monitor**: Set up alerts for failed sends and low conversion rates

---

## 📞 Support & Debug

**Enable debug logging:**
```bash
export LOG_LEVEL=DEBUG
python -m uvicorn app.main:app --reload --log-level debug
```

**Check API status:**
```bash
curl http://localhost:8000/health
```

**Inspect database directly:**
```bash
sqlite3 anu_login.sqlite3
> SELECT COUNT(*) FROM test_journey_log WHERE journey_type = 'lead';
> SELECT * FROM test_journey_log LIMIT 5;
> .exit
```

---

## ✨ You're All Set!

Everything is configured and ready to run. Choose your test option above and start sending! 🚀

Questions? Check the journey logs at `/api/test/journey/log` for detailed insights.
