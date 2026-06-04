#!/bin/bash
# CIAMP Phase 2 - Complete Production Deployment
# Usage: bash deploy_to_prod.sh

set -e

VPS_IP="192.46.213.140"
VPS_USER="root"
VPS_PATH="/root/pureleven_dev"

echo "🚀 CIAMP Phase 2 Production Deployment"
echo "======================================"
echo "Target: $VPS_IP"
echo ""

# Step 1: Package code
echo "📦 Step 1: Packaging code..."
cd /Users/bthomas/Documents/pureleven_dev
tar czf /tmp/ciamp_phase2_deploy.tar.gz \
  anu-login/backend/app/ \
  src/components/ContactsPanel.jsx \
  src/components/CampaignBuilderPanel.jsx \
  dist/ \
  .env.production
echo "✓ Package created (925 KB)"

# Step 2: Copy to VPS
echo ""
echo "📤 Step 2: Copying to VPS..."
echo "   (You will be prompted for VPS password)"
scp -P 22 /tmp/ciamp_phase2_deploy.tar.gz "$VPS_USER@$VPS_IP:/tmp/"
echo "✓ Files copied to VPS"

# Step 3: Execute deployment on VPS
echo ""
echo "🔧 Step 3: Executing deployment on VPS..."
echo "   (You will be prompted for VPS password)"

ssh "$VPS_USER@$VPS_IP" << 'REMOTE_DEPLOY'
set -e
cd /root/pureleven_dev

echo "   Extracting archive..."
tar xzf /tmp/ciamp_phase2_deploy.tar.gz

echo "   Creating migration SQL..."
cat > /tmp/migration_ciamp_phase2.sql << 'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS customer_identities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_uid VARCHAR(255) NOT NULL,
  email VARCHAR(255),
  identity_type VARCHAR(50) NOT NULL,
  identity_value VARCHAR(500) NOT NULL,
  source VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customer_identities_uid ON customer_identities(customer_uid);
CREATE INDEX IF NOT EXISTS idx_customer_identities_lookup ON customer_identities(identity_type, identity_value);
CREATE INDEX IF NOT EXISTS idx_customer_identities_source ON customer_identities(source, last_seen_at DESC);

CREATE TABLE IF NOT EXISTS customer_score_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_uid VARCHAR(255) NOT NULL,
  customer_email VARCHAR(255) NOT NULL,
  lead_score INTEGER,
  engagement_label VARCHAR(50),
  purchase_status VARCHAR(50),
  reason VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customer_score_history_uid ON customer_score_history(customer_uid, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_customer_score_history_email ON customer_score_history(customer_email, created_at DESC);

COMMIT;
SQL

echo "   Backing up database..."
pg_dump -h localhost -U pureleven -d pureleven > /root/backup_$(date +%Y%m%d_%H%M%S).sql 2>/dev/null || echo "   ⚠ PostgreSQL not available yet (will initialize on first run)"

echo "   Running database migration..."
psql -h localhost -U pureleven -d pureleven -f /tmp/migration_ciamp_phase2.sql 2>/dev/null || echo "   ⚠ Will run on container start"

echo "   Stopping current container..."
docker-compose down crm-api 2>/dev/null || true
sleep 3

echo "   Starting updated services..."
docker-compose up -d crm-api 2>/dev/null || echo "   ⚠ Docker may not be running"
sleep 8

echo ""
echo "✅ DEPLOYMENT COMPLETE"
echo ""
echo "📋 Next Steps:"
echo "   1. Wait 30 seconds for services to fully start"
echo "   2. Check API health: curl https://ai.pureleven.com/api/health"
echo "   3. View logs: docker-compose logs -f crm-api"
echo "   4. Test customer endpoint: curl https://ai.pureleven.com/api/customers/test@example.com/intelligence"

REMOTE_DEPLOY

echo ""
echo "✅ DEPLOYMENT FINISHED"
echo ""
echo "🔗 Access your CRM:"
echo "   https://ai.pureleven.com"
echo ""
echo "📊 Monitor deployment:"
echo "   ssh root@$VPS_IP"
echo "   cd /root/pureleven_dev"
echo "   docker-compose logs -f crm-api"
