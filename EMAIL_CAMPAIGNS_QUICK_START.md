# 📧 Email Campaign Setup — SendGrid + Plunk Routing

## Simple 2-Minute Setup

Your email system is ready to route campaigns intelligently:

### Email Routing Strategy
```
Customer Action
    ↓
sendgrid_handler.py routes by template:
    ├─ order_confirmation (D0)     → SendGrid ✉️ (critical)
    ├─ review_request_d3 (D3)      → SendGrid ✉️ (critical)
    ├─ repeat_offer_d7 (D7)        → Plunk 📤 (follow-up)
    ├─ replenishment_d30 (D30)     → Plunk 📤 (follow-up)
    ├─ winback_d60 (D60)           → Plunk 📤 (follow-up)
    └─ cart_abandonment            → Plunk 📤 (follow-up)
```

---

## STEP 1: Configure SendGrid

```bash
# On your VPS, add to /opt/pureleven/ai-engine/.env
echo 'SENDGRID_API_KEY=SG.xxxxxxxxxxxx' >> /opt/pureleven/ai-engine/.env

# Restart container
docker restart pureleven-ai-engine && sleep 10
```

**Get SENDGRID_API_KEY**:
1. Log in to SendGrid: https://app.sendgrid.com
2. Go to Settings → API Keys
3. Create an API Key with "Mail Send" permission
4. Copy the key value

---

## STEP 2: Test SendGrid Email

```bash
# Test order confirmation email (D0)
curl -X POST https://track.pureleven.com/api/crm/email/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer pk-prod-b5a739879a05532330946201cb59baca" \
  -d '{
    "to_email": "your-test@example.com",
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
```

Check your inbox — email should arrive in 1-2 minutes.

---

## STEP 3: Setup Plunk Later (When Ready)

When you want to deploy Plunk for follow-ups:

1. **Get AWS SES credentials** from AWS console
2. **Run deployment script**: `./deploy-plunk-selfhosted.sh`
3. **Done** — Follow-ups automatically route to Plunk

All the routing logic is already coded in `sendgrid_handler.py`.

---

## Email Templates Available

| Template | Trigger | Use Case |
|----------|---------|----------|
| `order_confirmation` | Order placed | Order confirmation |
| `review_request_d3` | 3 days after order | Ask for review |
| `repeat_offer_d7` | 7 days post-purchase | Similar product offer |
| `replenishment_d30` | 30 days post-purchase | Reorder prompt |
| `winback_d60` | 60 days no activity | Win-back campaign |
| `cart_abandonment` | Cart abandoned 24h | Cart recovery |

---

## How to Trigger Emails

### Via N8N Workflow (Recommended)
Already configured in 4 workflows:
- `n8n_lifecycle_email_workflow.json` — Sends all 6 templates daily at 6 AM
- Integrated with PropensityScore (Phase 8) for smart targeting

### Via API (Manual)
```bash
curl -X POST https://track.pureleven.com/api/crm/email/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer pk-prod-b5a739879a05532330946201cb59baca" \
  -d '{
    "to_email": "customer@example.com",
    "template_name": "template_name",
    "substitutions": {
      "customer_name": "Name",
      "product_name": "Product"
    }
  }'
```

### Via Shopify Webhook (Auto)
Triggered automatically when:
- Order created → `order_confirmation` sent
- Customer marked for review → `review_request_d3` sent
- (Other triggers via N8N scheduler)

---

## Email Tracking

All emails are logged in database:

```bash
# Check sent emails
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  "SELECT email, template_id, provider, status, sent_at FROM crm_messages ORDER BY sent_at DESC LIMIT 10;"
```

Columns:
- `email` — Recipient email
- `template_id` — Email template used
- `provider` — SendGrid or Plunk
- `status` — sent, pending, failed
- `sent_at` — Timestamp

---

## Troubleshooting

### SendGrid email not sending

```bash
# Check logs
docker logs pureleven-ai-engine | grep -i sendgrid

# Verify API key is set
ssh root@192.46.213.140 -c "grep SENDGRID_API_KEY /opt/pureleven/ai-engine/.env"

# Test SendGrid connectivity
curl -v https://api.sendgrid.com/v3/mail/send \
  -H "Authorization: Bearer SG.your_key_here" \
  -H "Content-Type: application/json" \
  -d '{"test": "1"}'
```

### Email bounces/marks as spam

1. **Verify sender domain** in SendGrid settings
2. **Set up SPF/DKIM/DMARC** records for `noreply@pureleven.com`
3. **Use SendGrid templates** (higher deliverability)
4. **Monitor bounce rates** in SendGrid dashboard

---

## Production Checklist

- [ ] SendGrid API key added to `.env`
- [ ] Test email sent successfully
- [ ] Email appears in customer inbox (not spam)
- [ ] Sender domain verified in SendGrid
- [ ] SPF/DKIM/DMARC records configured
- [ ] Monitor bounce/complaint rates weekly
- [ ] Deploy Plunk when ready for follow-ups
- [ ] Configure AWS SES for Plunk email delivery

---

## Files

- `sendgrid_handler.py` — Email routing engine (ready now)
- `crm_routes.py` — API endpoints for sending emails
- Plunk files (for Phase 2 deployment):
  - `docker-compose.plunk-official.yml`
  - `deploy-plunk-selfhosted.sh`
  - `PLUNK_SETUP_GUIDE.md`

---

## Next Steps

**Now**: Use SendGrid for all emails
**Later**: Deploy Plunk for cost-optimized follow-ups

The routing logic is already in place. Just deploy Plunk when ready!
