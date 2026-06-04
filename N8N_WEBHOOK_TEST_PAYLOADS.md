# N8N Webhook Payloads — Pure Leven CRM

This document provides example webhook payloads for testing the N8N → FastAPI integration.

**Webhook URL:** `https://track.pureleven.com/api/crm/webhooks/n8n`  
**Method:** `POST`  
**Content-Type:** `application/json`

---

## 1. Step Result Event

Sent **after each journey step completes** (email sent, audience synced, etc).

```json
{
  "event": "step_result",
  "data": {
    "step_id": "550e8400-e29b-41d4-a716-446655440000",
    "instance_id": "387596f9-f0d7-452c-8cfa-4fc706f14cbf",
    "journey_name": "welcome_sequence",
    "step_type": "email",
    "email": "customer@example.com",
    "customer_id": "6e89808a-7d30-451c-a90e-ad32fa7f8fac",
    "status": "EXECUTED",
    "result": {
      "message_id": "sg-msg-1234567890",
      "sent_at": "2026-05-19T10:15:30Z",
      "email_template": "welcome_day1"
    }
  }
}
```

### Fields:
- **event** *(string, required)*: `"step_result"`
- **data.step_id** *(uuid, required)*: Journey step ID (for logging)
- **data.instance_id** *(uuid, required)*: Active journey instance ID
- **data.journey_name** *(string, optional)*: Display name for logs
- **data.step_type** *(string, optional)*: `email`, `meta_audience`, `google_audience`, `whatsapp`, etc.
- **data.email** *(string, optional)*: Customer email (for Live Feed)
- **data.customer_id** *(uuid, optional)*: Customer ID (for Live Feed)
- **data.status** *(string, required)*: `EXECUTED`, `SKIPPED`, or `FAILED`
- **data.result** *(object, optional)*: Provider-specific response (logged + broadcast to WebSocket)

### Response:
```json
{
  "ok": true,
  "event": "step_result"
}
```

---

## 2. Journey Complete Event

Sent **when a journey successfully finishes all steps**.

```json
{
  "event": "journey_complete",
  "data": {
    "instance_id": "387596f9-f0d7-452c-8cfa-4fc706f14cbf",
    "journey_id": "27be9a5b-3429-475e-bcd5-9bfd5afec0e0",
    "customer_id": "6e89808a-7d30-451c-a90e-ad32fa7f8fac",
    "email": "customer@example.com",
    "result_data": {
      "converted": true,
      "revenue": 2500.00,
      "currency": "INR",
      "steps_executed": 5,
      "total_duration_days": 7
    }
  }
}
```

### Fields:
- **event** *(string, required)*: `"journey_complete"`
- **data.instance_id** *(uuid, required)*: Journey instance to mark COMPLETED
- **data.journey_id** *(uuid, optional)*: For logging
- **data.customer_id** *(uuid, optional)*: For logging
- **data.email** *(string, optional)*: For logging
- **data.result_data** *(object, optional)*: Journey outcome (conversion, revenue, etc) — stored in DB

### Response:
```json
{
  "ok": true,
  "event": "journey_complete"
}
```

---

## 3. Journey Error Event

Sent **when a journey fails or must exit early**.

```json
{
  "event": "journey_error",
  "data": {
    "instance_id": "387596f9-f0d7-452c-8cfa-4fc706f14cbf",
    "journey_id": "27be9a5b-3429-475e-bcd5-9bfd5afec0e0",
    "customer_id": "6e89808a-7d30-451c-a90e-ad32fa7f8fac",
    "error": "Email send failed: invalid recipient",
    "error_code": "INVALID_EMAIL",
    "step_number": 2
  }
}
```

### Fields:
- **event** *(string, required)*: `"journey_error"`
- **data.instance_id** *(uuid, required)*: Journey instance to mark EXITED
- **data.journey_id** *(uuid, optional)*: For logging
- **data.customer_id** *(uuid, optional)*: For logging
- **data.error** *(string, optional)*: Human-readable error message (stored in DB as `exit_reason`)
- **data.error_code** *(string, optional)*: Machine-readable code
- **data.step_number** *(integer, optional)*: Which step failed

### Response:
```json
{
  "ok": true,
  "event": "journey_error"
}
```

---

## Real-World Examples

### Email Step Completion (SendGrid)
```bash
curl -X POST https://track.pureleven.com/api/crm/webhooks/n8n \
  -H "Content-Type: application/json" \
  -d '{
    "event": "step_result",
    "data": {
      "step_id": "'$(python3 -c "import uuid; print(uuid.uuid4())")'"
      "instance_id": "387596f9-f0d7-452c-8cfa-4fc706f14cbf",
      "step_type": "email",
      "status": "EXECUTED",
      "email": "test@example.com",
      "result": {
        "message_id": "13526289786234066",
        "sent_at": "2026-05-19T10:15:00Z"
      }
    }
  }'
```

### Meta Audience Sync Completion
```bash
curl -X POST https://track.pureleven.com/api/crm/webhooks/n8n \
  -H "Content-Type: application/json" \
  -d '{
    "event": "step_result",
    "data": {
      "step_id": "'$(python3 -c "import uuid; print(uuid.uuid4())")'"
      "instance_id": "387596f9-f0d7-452c-8cfa-4fc706f14cbf",
      "step_type": "meta_audience",
      "status": "EXECUTED",
      "customer_id": "6e89808a-7d30-451c-a90e-ad32fa7f8fac",
      "result": {
        "audience_id": "1234567890",
        "added_count": 1
      }
    }
  }'
```

### Journey Conversion Flow
```bash
# 1. Email sent
curl -X POST https://track.pureleven.com/api/crm/webhooks/n8n \
  -H "Content-Type: application/json" \
  -d '{"event":"step_result","data":{"step_id":"'$(python3 -c "import uuid; print(uuid.uuid4())")'","instance_id":"387596f9-f0d7-452c-8cfa-4fc706f14cbf","step_type":"email","status":"EXECUTED","result":{"message_id":"sg-1"}}}'

# 2. Wait for conversion...

# 3. Journey completes with revenue
curl -X POST https://track.pureleven.com/api/crm/webhooks/n8n \
  -H "Content-Type: application/json" \
  -d '{
    "event": "journey_complete",
    "data": {
      "instance_id": "387596f9-f0d7-452c-8cfa-4fc706f14cbf",
      "result_data": {
        "converted": true,
        "revenue": 5000.00,
        "attribution_model": "last_touch"
      }
    }
  }'
```

---

## WebSocket Broadcasting

When `step_result` is received, the backend:
1. Updates the `JourneyStep` record in DB
2. **Broadcasts to live dashboard** via Redis pub/sub on channel `pubsub:steps`

**Live Dashboard receives:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "step_type": "email",
  "step_name": "Welcome Day 1",
  "status": "EXECUTED",
  "result": {
    "message_id": "sg-msg-1234567890",
    "sent_at": "2026-05-19T10:15:30Z"
  },
  "journey_instance_id": "387596f9-f0d7-452c-8cfa-4fc706f14cbf",
  "email": "customer@example.com",
  "customer_id": "6e89808a-7d30-451c-a90e-ad32fa7f8fac",
  "journey_name": "welcome_sequence",
  "timestamp": "2026-05-19T10:15:30.123456"
}
```

This message appears in the "⚡ Live Feed" tab of the CRM dashboard in real-time.

---

## Testing via cURL

Save this to `test_webhook.sh`:

```bash
#!/bin/bash

WEBHOOK_URL="https://track.pureleven.com/api/crm/webhooks/n8n"
INSTANCE_ID="387596f9-f0d7-452c-8cfa-4fc706f14cbf"

echo "Testing step_result webhook..."
curl -s -k -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "step_result",
    "data": {
      "step_id": "'$(python3 -c "import uuid; print(uuid.uuid4())")'",
      "instance_id": "'$INSTANCE_ID'",
      "step_type": "email",
      "status": "EXECUTED",
      "result": {"message_id": "test-123"}
    }
  }' | python3 -m json.tool

echo ""
echo "Testing journey_complete webhook..."
curl -s -k -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "journey_complete",
    "data": {
      "instance_id": "'$INSTANCE_ID'",
      "result_data": {"converted": true, "revenue": 1000}
    }
  }' | python3 -m json.tool
```

Run: `bash test_webhook.sh`

---

## Integration Checklist

- [ ] N8N workflow ready to send webhooks
- [ ] Instance ID and customer IDs correctly passed through N8N
- [ ] Email/SMS templates configured in N8N
- [ ] Webhook URL is `https://track.pureleven.com/api/crm/webhooks/n8n`
- [ ] Test step_result payload in browser DevTools Network tab
- [ ] Verify Live Feed dashboard shows step logs in real-time
- [ ] Check attribution after journey_complete event
