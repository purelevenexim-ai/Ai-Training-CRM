# 🚀 Plunk Self-Hosted Implementation — NEXT STEPS

## ✅ What's Ready

All files prepared for self-hosted Plunk setup on your VPS:

```
/Users/bthomas/Documents/pureleven_dev/
├── docker-compose.plunk-official.yml  ← Official Plunk Docker stack
├── .env.plunk.example                  ← Configuration template
├── deploy-plunk-selfhosted.sh          ← Deployment automation script
├── PLUNK_SETUP_GUIDE.md                ← Full setup & troubleshooting guide
└── sendgrid_handler.py                 ← Updated to call Plunk API
```

---

## 📋 Required Actions (IN ORDER)

### STEP 1️⃣: Get AWS SES Credentials
**Time: ~10 minutes**

You MUST have AWS SES credentials for Plunk to send emails.

1. Log in: https://console.aws.amazon.com
2. Go to **SES (Simple Email Service)**
3. Click **SMTP Settings**
4. Click **Create SMTP credentials**
5. **Save these values** (you'll need them in Step 3):
   - AWS_SES_ACCESS_KEY_ID
   - AWS_SES_SECRET_ACCESS_KEY

**Alternative**: If you already have SES SMTP credentials, just collect them.

---

### STEP 2️⃣: Prepare Configuration
**Time: ~5 minutes**

```bash
# On your local machine

cd /Users/bthomas/Documents/pureleven_dev

# Copy template to .env.plunk
cp .env.plunk.example .env.plunk

# Edit with your AWS SES credentials
nano .env.plunk

# Update these values:
# - AWS_SES_ACCESS_KEY_ID=YOUR_KEY_HERE
# - AWS_SES_SECRET_ACCESS_KEY=YOUR_SECRET_HERE
# - DB_PASSWORD=random-password (will be generated)
# - JWT_SECRET=random-secret (will be generated)

# Save & close (Ctrl+X, Y, Enter)
```

---

### STEP 3️⃣: Deploy to VPS
**Time: ~5-10 minutes (+ 3 min startup time)**

```bash
cd /Users/bthomas/Documents/pureleven_dev

# Make script executable
chmod +x deploy-plunk-selfhosted.sh

# Run deployment
./deploy-plunk-selfhosted.sh
```

**What this does**:
1. ✅ Generates secrets (JWT_SECRET, DB_PASSWORD)
2. ✅ Uploads `.env.plunk` to VPS
3. ✅ Uploads `docker-compose.plunk.yml` to VPS
4. ✅ Starts Plunk containers on VPS
5. ✅ Updates AI-Engine `.env` with `PLUNK_API_URL`
6. ✅ Restarts AI-Engine container

**Output**: You'll see deployment progress + next steps

---

### STEP 4️⃣: Verify Deployment
**Time: ~5 minutes**

```bash
# SSH to VPS
ssh root@192.46.213.140

# Check if Plunk containers are running
cd /opt/pureleven
docker-compose -f docker-compose.plunk.yml ps

# Expected output:
# pureleven-plunk               Up (healthy)
# pureleven-plunk-postgres      Up (healthy)
# pureleven-plunk-redis         Up (healthy)
# pureleven-plunk-minio         Up (healthy)

# Check API health (may take 2-3 min on first startup)
curl http://localhost:80/health

# Check logs for any errors
docker logs pureleven-plunk | tail -30
```

---

### STEP 5️⃣: Test Email Routing
**Time: ~10 minutes**

```bash
# SSH to VPS
ssh root@192.46.213.140

# Test 1: SendGrid email (D0)
curl -X POST https://track.pureleven.com/api/crm/email/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer pk-prod-b5a739879a05532330946201cb59baca" \
  -d '{
    "to_email": "your-test-email@example.com",
    "template_name": "order_confirmation",
    "substitutions": {
      "customer_name": "Test User",
      "order_id": "TEST123",
      "order_date": "2025-05-18",
      "total": "1500",
      "items": "Cardamom",
      "delivery_address": "123 Main St",
      "payment_method": "Card",
      "delivery_date": "2025-05-22",
      "tracking_url": "https://example.com/track",
      "unsubscribe_url": "https://example.com/unsub"
    }
  }'

# Test 2: Plunk email (D7)
curl -X POST https://track.pureleven.com/api/crm/email/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer pk-prod-b5a739879a05532330946201cb59baca" \
  -d '{
    "to_email": "your-test-email@example.com",
    "template_name": "repeat_offer_d7",
    "substitutions": {
      "customer_name": "Test User",
      "product_name": "Cardamom",
      "offer": "20% Off",
      "offer_link": "https://pureleven.com/cardamom",
      "unsubscribe_url": "https://pureleven.com/unsub"
    }
  }'

# Check if emails were recorded
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  "SELECT email, template_id, provider, status FROM crm_messages ORDER BY created_at DESC LIMIT 5;"
```

---

## 📊 What Happens Next

### Email Flow
```
Customer places order on Shopify
    ↓
Webhook → CRM API
    ↓
sendgrid_handler.py routes based on template:
    ├─ order_confirmation (D0)     → SendGrid ✉️
    ├─ review_request_d3 (D3)      → SendGrid ✉️
    ├─ repeat_offer_d7 (D7)        → Plunk ✉️
    ├─ replenishment_d30 (D30)     → Plunk ✉️
    ├─ winback_d60 (D60)           → Plunk ✉️
    └─ cart_abandonment (follow-up) → Plunk ✉️
    ↓
AWS SES (via Plunk SMTP relay)
    ↓
Customer inbox
```

### Cost Savings
- **SendGrid**: 2 critical emails per customer ($0.10 × 2 = $0.20/customer)
- **Plunk**: 4 follow-ups per customer via AWS SES (~$0.002/email via Plunk = $0.008/customer)
- **Savings**: 96% cheaper for follow-up emails

---

## 🆘 Troubleshooting

### If deployment fails

```bash
# Check deployment error
tail -20 ~/.bash_history  # See what failed

# Manual check
ssh root@192.46.213.140
docker ps | grep plunk  # See if containers started

# Check Plunk logs
docker logs pureleven-plunk | grep -i error
```

### If emails aren't sending

**Check 1: AWS SES credentials**
```bash
ssh root@192.46.213.140
nano /opt/pureleven/.env.plunk
# Verify: AWS_SES_ACCESS_KEY_ID and AWS_SES_SECRET_ACCESS_KEY are correct
docker restart pureleven-plunk
```

**Check 2: Plunk API reachable**
```bash
docker exec pureleven-ai-engine curl http://pureleven-plunk:8080/health
# Should return 200 OK
```

**Check 3: Email queue**
```bash
docker exec pureleven-postgres psql -U pureleven -d pureleven \
  -c "SELECT * FROM crm_messages WHERE status = 'pending' LIMIT 1;"
```

---

## 📚 Documentation

- **Full Setup Guide**: `PLUNK_SETUP_GUIDE.md` (comprehensive)
- **Plunk Docs**: https://docs.useplunk.com/self-hosting/introduction
- **AWS SES Docs**: https://docs.aws.amazon.com/ses/

---

## 🎯 Summary

| Step | Task | Time | Status |
|------|------|------|--------|
| 1 | Get AWS SES credentials | 10 min | ⏳ Your action |
| 2 | Prepare `.env.plunk` | 5 min | ⏳ Your action |
| 3 | Run `deploy-plunk-selfhosted.sh` | 10 min | ⏳ Your action |
| 4 | Verify containers running | 5 min | ⏳ Your action |
| 5 | Test email routing | 10 min | ⏳ Your action |

**Total time**: ~40 minutes

---

## ✨ After Deployment

Once verified, Pureleven's email system will:
- ✅ Send critical conversion emails via SendGrid (D0, D3)
- ✅ Send cost-optimized follow-ups via self-hosted Plunk (D7, D30, D60)
- ✅ Automatically track open/click data via AWS SES
- ✅ Integrate with N8N workflows for lifecycle automation
- ✅ Reduce email costs by 96% for follow-ups

---

**Ready to start? Begin with STEP 1: Get AWS SES Credentials**

Questions? Check `PLUNK_SETUP_GUIDE.md` or your repo memory notes.
