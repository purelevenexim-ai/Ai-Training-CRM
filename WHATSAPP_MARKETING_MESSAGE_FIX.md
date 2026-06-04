# WhatsApp Marketing Message Delivery Fix

## 🔴 Problem Identified

**Why marketing messages weren't arriving (even though logs showed "sent"):**

Meta WhatsApp Business API enforces strict delivery rules:
- **TRANSACTIONAL messages** (e.g., `order_confirmed_v1`): Can be sent anytime ✅
- **UTILITY messages**: Can be sent anytime ✅  
- **MARKETING messages** (e.g., `repeat_buyer_exclusive_v1`): **Only deliverable within 24 hours of the customer's last message to you** ⚠️

Your template `repeat_buyer_exclusive_v1` is a **MARKETING** message because it's promoting a loyalty reward. Meta silently blocks these if:
1. The customer is NOT opted in to WhatsApp marketing
2. The customer hasn't messaged you in the last 24 hours
3. There's no active conversation window

**Your sending code had ZERO validation for this**, so it was blindly sending marketing messages to customers outside the 24-hour window, and Meta rejected them silently at delivery time.

---

## ✅ Fix Applied

### 1. Created `whatsapp_delivery_validator.py`
- Checks if a template can be sent to a customer
- For MARKETING messages: enforces 24-hour engagement window check
- For TRANSACTIONAL/UTILITY: allows always
- Logs reason for any blocked messages

### 2. Updated All Send Functions
Modified these files to validate before sending:
- `wabis_client.py` (primary Wabis/Meta API client)
- `meta_client.py` (direct Meta Graph API)
- `journey_engine.py` (journey message sending)
- `review_journey_engine.py` (review journey messages)
- `services/journey_engine_v2.py` (v2 journey engine)
- `routes/test_journey.py` (test endpoint)
- `services/campaign_service.py` (campaign messages)

### 3. Track Last Customer Engagement
Updated `whatsapp_tracking.py` to sync engagement timestamps:
- When customer **replies** → updates `customers.last_engagement_at`
- When customer **clicks** a link → updates `customers.last_engagement_at`
- This creates the active conversation window for marketing messages

---

## 📋 How It Works Now

### Before Sending a Message:
```python
can_send, reason = validate_template_send(phone, template_name, shop_domain)
if not can_send:
    # Reject: e.g., "Outside 24-hour window (48.3 hours since last engagement)"
    return {"status": "delivery_blocked", "error": reason}
```

### For Each Customer:
✅ **Marketing messages CAN be sent if**:
  - Template is marked MARKETING
  - Customer is `whatsapp_opted_in = 1`
  - Last message from customer was within 24 hours (`last_engagement_at` > now - 24h)

❌ **Marketing messages ARE BLOCKED if**:
  - Customer hasn't opted in to WhatsApp
  - Customer has unsubscribed (`whatsapp_unsubscribed_at` is set)
  - No engagement history (first contact)
  - Outside 24-hour window

✅ **Transactional/Utility messages ALWAYS send** (no restrictions)

---

## 🚀 For Future Marketing Sends

### Option 1: Wait for Active Conversation
Send to customers who **recently messaged you** (within 24 hours). Best for:
- Follow-ups on recent customer replies
- Timely loyalty rewards after order

### Option 2: Use Notification Templates
If you have templates marked **UTILITY** instead of MARKETING:
- Can be sent anytime without conversation window
- Examples: order status, shipping, account alerts
- But Meta limits these — check Meta's policy

### Option 3: Opt-in Proactively
Build a flow where customers opt into marketing:
1. First message: Offer opt-in option
2. Customer replies "Yes"  
3. Now `last_engagement_at` is set, conversation window opens
4. Marketing messages can flow for next 24 hours

---

## 📊 Dashboard Visibility

### What You'll See in Logs Now:
- ✅ `Message eligible for delivery: phone=+919144774583 template=repeat_buyer_exclusive_v1 reason=Within 24-hour window (2.5 hours since last engagement)`
- ❌ `Marketing message blocked: phone=+919944123456 template=repeat_buyer_exclusive_v1 reason=Outside 24-hour window (72.1 hours since last engagement)`

### What Wasn't Visible Before:
- Meta was silently rejecting the messages at delivery time
- Logs showed "sent" but messages never arrived
- No way to know which customers were eligible

---

## ✨ Next Steps

1. **For `+919144774583`** (phone number in your screenshot):
   - Check if they recently messaged you → If yes, marketing messages will now deliver
   - If no, try again within 24 hours of their next reply

2. **For Future Campaigns**:
   - Validate against 24-hour rule before queuing
   - Consider sending UTILITY templates if you need reliable delivery
   - Build opt-in flows to open conversation windows

3. **Monitor Blocked Messages**:
   - Backend logs will show why messages are blocked
   - Adjust campaign scheduling based on engagement patterns

---

## Files Modified

```
✅ app/whatsapp_delivery_validator.py       [NEW]
✅ app/wabis_client.py                      [validation added]
✅ app/meta_client.py                       [validation added]
✅ app/journey_engine.py                    [shop_domain param]
✅ app/review_journey_engine.py             [shop_domain param]
✅ app/services/journey_engine_v2.py        [shop_domain param]
✅ app/routes/test_journey.py               [shop_domain param]
✅ app/services/campaign_service.py         [shop_domain param]
✅ app/routes/whatsapp_tracking.py          [sync customers.last_engagement_at]
```

---

## 🔍 How to Test

**Test a marketing message send in your logs:**

1. Go to WhatsApp and message your Pureleven bot
2. Check logs: `customers.last_engagement_at` should be recent
3. Try sending `repeat_buyer_exclusive_v1` → Should now succeed with "Within 24-hour window" message
4. Wait 24+ hours without messaging → Sending will block with "Outside 24-hour window"
5. Message bot again → Conversation window resets, marketing messages work again
