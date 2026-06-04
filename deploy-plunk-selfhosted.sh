#!/bin/bash
# Deploy Plunk self-hosted instance to production VPS

set -e

echo "📦 Deploying Plunk self-hosted instance..."

VPS_IP="192.46.213.140"
VPS_USER="root"
VPS_SSH_KEY=""

# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo "STEP 1: Generate secrets for .env.plunk"
echo "──────────────────────────────────────────────────────────────────────────"

JWT_SECRET=$(openssl rand -base64 32)
DB_PASSWORD=$(openssl rand -base64 16)

echo "✓ JWT_SECRET: ${JWT_SECRET}"
echo "✓ DB_PASSWORD: ${DB_PASSWORD}"

# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo "STEP 2: Create .env.plunk on VPS"
echo "──────────────────────────────────────────────────────────────────────────"

# Create .env.plunk with your values
cat > /tmp/.env.plunk << EOF
# Database
DB_PASSWORD=${DB_PASSWORD}

# JWT Secret
JWT_SECRET=${JWT_SECRET}

# Domain Configuration (update these for production)
API_DOMAIN=api.pureleven.local
DASHBOARD_DOMAIN=app.pureleven.local
LANDING_DOMAIN=www.pureleven.local
WIKI_DOMAIN=docs.pureleven.local
SMTP_DOMAIN=smtp.pureleven.local
USE_HTTPS=false

# AWS SES Configuration (required for email sending)
# Get these from AWS SES console
AWS_SES_REGION=us-east-1
AWS_SES_ACCESS_KEY_ID=YOUR_AWS_SES_ACCESS_KEY
AWS_SES_SECRET_ACCESS_KEY=YOUR_AWS_SES_SECRET_KEY
SES_CONFIGURATION_SET=plunk-tracking

# Minio (auto-configured, change if needed)
MINIO_ROOT_USER=plunk
MINIO_ROOT_PASSWORD=plunkminiopass
EOF

# Copy to VPS
sshpass -p 'QazPlm123!@#' scp -o StrictHostKeyChecking=no /tmp/.env.plunk root@${VPS_IP}:/opt/pureleven/.env.plunk

echo "✓ .env.plunk deployed to /opt/pureleven/"

# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo "STEP 3: Deploy docker-compose.plunk-official.yml"
echo "──────────────────────────────────────────────────────────────────────────"

sshpass -p 'QazPlm123!@#' scp -o StrictHostKeyChecking=no docker-compose.plunk-official.yml root@${VPS_IP}:/opt/pureleven/docker-compose.plunk.yml

echo "✓ Docker Compose file deployed"

# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo "STEP 4: Start Plunk containers on VPS"
echo "──────────────────────────────────────────────────────────────────────────"

sshpass -p 'QazPlm123!@#' ssh -o StrictHostKeyChecking=no root@${VPS_IP} << 'EOSSH'
cd /opt/pureleven

# Load environment from .env.plunk
export $(cat .env.plunk | grep -v '#' | xargs)

echo "🚀 Starting Plunk services..."
docker-compose -f docker-compose.plunk.yml up -d

echo "⏳ Waiting for services to be healthy (30s)..."
sleep 30

# Check container status
echo ""
echo "📊 Container status:"
docker-compose -f docker-compose.plunk.yml ps

# Check Plunk API health
echo ""
echo "🔍 Testing Plunk API health..."
curl -s -k -i http://localhost:80/health || echo "API not yet ready (can take 2-3 min)"

echo ""
echo "✓ Plunk services started!"
EOSSH

# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo "STEP 5: Update AI-Engine .env with PLUNK_API_URL"
echo "──────────────────────────────────────────────────────────────────────────"

sshpass -p 'QazPlm123!@#' ssh -o StrictHostKeyChecking=no root@${VPS_IP} << 'EOSSH'
echo "PLUNK_API_URL=http://pureleven-plunk:8080" >> /opt/pureleven/ai-engine/.env

echo "✓ PLUNK_API_URL added to AI-Engine .env"

# Restart AI-Engine container to pick up new env var
docker restart pureleven-ai-engine && sleep 10

echo "✓ AI-Engine container restarted"
EOSSH

# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo "STEP 6: Configure AWS SES credentials"
echo "──────────────────────────────────────────────────────────────────────────"

cat << 'EOF'
⚠️  MANUAL STEP REQUIRED:

AWS SES credentials must be set in .env.plunk on the VPS:

1. Log in to AWS Console → SES (Simple Email Service)
2. Go to SMTP settings → Create SMTP credentials
3. You'll get:
   - AWS_SES_ACCESS_KEY_ID
   - AWS_SES_SECRET_ACCESS_KEY
   
4. Update on VPS:
   ssh root@192.46.213.140
   
5. Edit /opt/pureleven/.env.plunk and add/update:
   AWS_SES_ACCESS_KEY_ID=YOUR_KEY
   AWS_SES_SECRET_ACCESS_KEY=YOUR_SECRET
   
6. Restart Plunk container:
   docker restart pureleven-plunk
   
Without AWS SES configured, Plunk cannot send emails.

EOF

# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo "✅ DEPLOYMENT COMPLETE!"
echo "──────────────────────────────────────────────────────────────────────────"
echo ""
echo "📍 Plunk Services:"
echo "   Web Dashboard:  http://localhost:3000  (if using port forwarding)"
echo "   API Endpoint:   http://pureleven-plunk:8080"
echo "   SMTP Port:      587 (STARTTLS) / 465 (implicit TLS)"
echo ""
echo "🔐 Credentials:"
echo "   JWT_SECRET:      ${JWT_SECRET}"
echo "   DB_PASSWORD:     ${DB_PASSWORD}"
echo ""
echo "📧 Email Status:"
echo "   SendGrid:        noreply@pureleven.com (order_confirmation, review_request_d3)"
echo "   Plunk:          Self-hosted at http://pureleven-plunk:8080"
echo ""
echo "⏳ Next: Plunk will perform database migrations and start within 2-3 minutes."
echo "   Check logs: docker logs pureleven-plunk"
echo ""
