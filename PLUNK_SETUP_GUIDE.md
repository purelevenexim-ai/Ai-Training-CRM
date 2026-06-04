# 🚀 Plunk Self-Hosted Setup Guide

## Overview

You are setting up **Plunk** (open-source email platform) on your VPS to handle cost-optimized follow-up emails:

| Email Template | Provider | Use Case |
|---|---|---|
| `order_confirmation` | **SendGrid** | D0 - High deliverability |
| `review_request_d3` | **SendGrid** | D3 - Critical conversion email |
| `repeat_offer_d7` | **Plunk** | D7 - Follow-up offer |
| `replenishment_d30` | **Plunk** | D30 - Reorder prompt |
| `winback_d60` | **Plunk** | D60 - Win-back campaign |
| `cart_abandonment` | **Plunk** | Abandoned cart follow-up |

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Pureleven VPS (192.46.213.140)                          │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │ AI-Engine Container (pureleven-ai-engine)        │   │
│  │ - sendgrid_handler.py                            │   │
│  │ - Routes emails → SendGrid or Plunk              │   │
│  └──────────────────────────────────────────────────┘   │
│         ↓ HTTP API                                       │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Plunk Stack (docker-compose.plunk.yml)           │   │
│  ├──────────────────────────────────────────────────┤   │
│  │ • Plunk API (port 8080)                          │   │
│  │ • Plunk Web (port 3000)                          │   │
│  │ • PostgreSQL (port 5433)                         │   │
│  │ • Redis (port 6380)                              │   │
│  │ • Minio/S3 (ports 9000/9001)                     │   │
│  │ • Nginx reverse proxy (port 80)                  │   │
│  └──────────────────────────────────────────────────┘   │
│         ↓ AWS SES                                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Email Delivery                                   │   │
│  └──────────────────────────────────────────────────┘   │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## Prerequisites

Before deploying, you need:

1. **AWS SES Account** - For email delivery
   - Region: `us-east-1`
   - Access Key ID
   - Secret Access Key
   - Configuration Set: `plunk-tracking`

2. **VPS Access** - SSH credentials
   - IP: `192.46.213.140`
   - User: `root`
   - Password: `QazPlm123!@#`

3. **Docker & Docker Compose** - Already installed on VPS

4. **SendGrid API Key** - For D0/D3 emails (already configured)

---

## Quick Start

### Step 1: Prepare Configuration

```bash
# On your local machine

# Copy the template
cp .env.plunk.example .env.plunk

# Edit with your AWS SES credentials
nano .env.plunk

# Required values to update:
# - DB_PASSWORD (generate: openssl rand -base64 16)
# - JWT_SECRET (generate: openssl rand -base64 32)
# - AWS_SES_ACCESS_KEY_ID (from AWS SES)
# - AWS_SES_SECRET_ACCESS_KEY (from AWS SES)
```

### Step 2: Deploy to VPS

```bash
# Run deployment script
chmod +x deploy-plunk-selfhosted.sh
./deploy-plunk-selfhosted.sh

# This will:
# 1. Generate secrets
# 2. Copy .env.plunk to VPS
# 3. Copy docker-compose file to VPS
# 4. Start all Plunk containers
# 5. Update AI-Engine .env with PLUNK_API_URL
# 6. Restart AI-Engine container
```

### Step 3: Verify Deployment

```bash
# SSH to VPS
ssh root@192.46.213.140

# Check container status
cd /opt/pureleven
docker-compose -f docker-compose.plunk.yml ps

# Check Plunk API health (wait 2-3 min after startup)
curl -s http://localhost:80/health | jq .

# Check logs
docker logs pureleven-plunk | tail -20
```

### Step 4: Configure AWS SES (if not done)

1. Log in to [AWS Console](https://console.aws.amazon.com)
2. Navigate to **SES (Simple Email Service)**
3. Go to **SMTP Settings** → **Create SMTP Credentials**
4. Save the credentials
5. SSH to VPS and update credentials:

```bash
ssh root@192.46.213.140

# Edit Plunk .env
nano /opt/pureleven/.env.plunk

# Update:
AWS_SES_ACCESS_KEY_ID=your_key
AWS_SES_SECRET_ACCESS_KEY=your_secret

# Restart Plunk
docker restart pureleven-plunk
```

---

## Testing

### Test SendGrid Email (D0)

```bash
# SSH to VPS
ssh root@192.46.213.140

# Connect to API container
docker exec pureleven-ai-engine python -c "
from sendgrid_handler import send_email

result = send_email(
    to_email='test@example.com',
    template_name='order_confirmation',
    substitutions={
        'customer_name': 'Test User',
        'order_id': '12345',
        'order_date': '2025-05-18',
        'total': '1500',
        'items': 'Kerala Cardamom 50g',
        'delivery_address': '123 Main St',
        'payment_method': 'Card',
        'delivery_date': '2025-05-22',
        'tracking_url': 'https://example.com/track/12345',
        'unsubscribe_url': 'https://example.com/unsub'
    }
)
print(f'SendGrid Result: {result}')
"
```

### Test Plunk Email (D7)

```bash
# SSH to VPS
ssh root@192.46.213.140

# Connect to API container
docker exec pureleven-ai-engine python -c "
from sendgrid_handler import send_email

result = send_email(
    to_email='test@example.com',
    template_name='repeat_offer_d7',
    substitutions={
        'customer_name': 'Test User',
        'product_name': 'Cardamom',
        'offer': '20% Off',
        'offer_link': 'https://example.com/offers/cardamom',
        'unsubscribe_url': 'https://example.com/unsub'
    }
)
print(f'Plunk Result: {result}')
"
```

### Test via API Endpoint

```bash
# Test email send via API
curl -X POST https://track.pureleven.com/api/crm/email/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer pk-prod-b5a739879a05532330946201cb59baca" \
  -d '{
    "to_email": "test@example.com",
    "template_name": "order_confirmation",
    "substitutions": {
      "customer_name": "Test User",
      "order_id": "12345"
    }
  }' -w '\nStatus: %{http_code}\n'
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs pureleven-plunk

# Check if ports are in use
netstat -tlnp | grep -E ":(80|3000|8080|5433|6380|9000)"

# Restart
docker-compose -f /opt/pureleven/docker-compose.plunk.yml restart
```

### Database migration failed

```bash
# Check PostgreSQL logs
docker logs pureleven-plunk-postgres

# Verify database exists
docker exec pureleven-plunk-postgres psql -U plunk -d plunk -c "\dt"
```

### Emails not sending

1. Check AWS SES credentials in `.env.plunk`
2. Verify sender email is verified in AWS SES
3. Check Plunk logs: `docker logs pureleven-plunk | grep -i email`
4. Verify SMTP service is running: `docker ps | grep plunk`

### Network connectivity issues

```bash
# Test network connectivity from AI-Engine to Plunk
docker exec pureleven-ai-engine curl -v http://pureleven-plunk:8080/health

# Test from VPS
curl -v http://localhost:8080/health
```

---

## Environment Variables Reference

### Critical (Required)

| Variable | Example | Description |
|---|---|---|
| `JWT_SECRET` | `abc123...` | Secret for JWT tokens |
| `DB_PASSWORD` | `secure123` | PostgreSQL password |
| `AWS_SES_ACCESS_KEY_ID` | `AKIAIOSFODNN7EXAMPLE` | AWS SES access key |
| `AWS_SES_SECRET_ACCESS_KEY` | `wJalrXUtnFEMI/K7MDENG...` | AWS SES secret key |

### Domain Configuration (Development)

| Variable | Default | Description |
|---|---|---|
| `API_DOMAIN` | `api.pureleven.local` | API subdomain |
| `DASHBOARD_DOMAIN` | `app.pureleven.local` | Dashboard subdomain |
| `LANDING_DOMAIN` | `www.pureleven.local` | Landing page subdomain |
| `WIKI_DOMAIN` | `docs.pureleven.local` | Documentation subdomain |
| `SMTP_DOMAIN` | `smtp.pureleven.local` | SMTP relay subdomain |
| `USE_HTTPS` | `false` | Use HTTPS (set to `true` in production) |

### Storage (Minio)

| Variable | Default | Description |
|---|---|---|
| `MINIO_ROOT_USER` | `plunk` | Minio username |
| `MINIO_ROOT_PASSWORD` | `plunkminiopass` | Minio password |

---

## Post-Deployment

### 1. Verify sendgrid_handler.py is Updated

```bash
ssh root@192.46.213.140

# Check if sendgrid_handler.py has Plunk support
grep -n "PLUNK_API_URL" /app/app/sendgrid_handler.py

# Should show Plunk configuration
```

### 2. Test End-to-End Email Flow

```bash
# Simulate a Shopify order webhook
curl -X POST https://track.pureleven.com/api/crm/events/shopify \
  -H "Content-Type: application/json" \
  -d '{
    "type": "orders/create",
    "email": "customer@example.com",
    "order_id": "123456",
    "total": "1500.00",
    "currency": "INR"
  }'

# Check if email was sent
ssh root@192.46.213.140 -c "
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  \"SELECT * FROM crm_messages WHERE customer_email = 'customer@example.com' LIMIT 1;\"
"
```

### 3. Monitor Email Queue

```bash
# SSH to VPS
ssh root@192.46.213.140

# Check pending emails
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  "SELECT COUNT(*) as pending FROM crm_messages WHERE status = 'pending';"

# Check sent emails
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  "SELECT template_id, provider, COUNT(*) as sent_count FROM crm_messages WHERE status = 'sent' GROUP BY template_id, provider;"
```

---

## Scaling & Optimization

### Performance Tuning

```bash
# Increase worker concurrency in .env.plunk
MAX_RECIPIENTS=10  # Default 5

# Increase SMTP relay connections
docker restart pureleven-plunk
```

### Backup Strategy

```bash
# Backup PostgreSQL daily
docker exec pureleven-plunk-postgres pg_dump -U plunk plunk | gzip > /opt/backups/plunk-$(date +%Y%m%d).sql.gz

# Backup Minio S3 data
docker exec pureleven-plunk-minio mc cp -r minio/plunk /opt/backups/minio-$(date +%Y%m%d)/
```

---

## Support & Resources

- **Plunk Docs**: https://docs.useplunk.com
- **GitHub**: https://github.com/useplunk/plunk
- **AWS SES**: https://docs.aws.amazon.com/ses/
- **Docker Compose**: https://docs.docker.com/compose/

---

## Checklist

- [ ] AWS SES account created and credentials obtained
- [ ] `.env.plunk` created with all required values
- [ ] `deploy-plunk-selfhosted.sh` executed successfully
- [ ] Plunk containers running (`docker ps`)
- [ ] API health check passing (`curl http://localhost/health`)
- [ ] SendGrid test email sent successfully
- [ ] Plunk test email sent successfully
- [ ] Database migrations completed without errors
- [ ] AI-Engine restarted with `PLUNK_API_URL` env var
- [ ] End-to-end test passed (Shopify webhook → email sent)

---

**Status**: ✅ Ready for production testing

**Next Steps**:
1. Deploy Plunk to VPS
2. Configure AWS SES credentials
3. Test email routing
4. Monitor logs for 24 hours
5. Scale to full production email volume
