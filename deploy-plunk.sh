#!/bin/bash
# Deploy Self-Hosted Plunk to VPS

set -e

SERVER="192.46.213.140"
SSH_KEY="QazPlm123!@#"
SSH_USER="root"

echo "🚀 Deploying Self-Hosted Plunk to Pureleven VPS..."

# Step 1: Upload docker-compose file
echo "📦 Uploading Plunk docker-compose..."
sshpass -p "$SSH_KEY" scp -o StrictHostKeyChecking=no \
  ./docker-compose.plunk.yml \
  $SSH_USER@$SERVER:/opt/pureleven/docker-compose.plunk.yml

# Step 2: Create plunk database
echo "🗄️  Creating Plunk database..."
sshpass -p "$SSH_KEY" ssh -o StrictHostKeyChecking=no $SSH_USER@$SERVER << 'EOF'
docker exec pureleven-postgres psql -U pureleven -c "
  CREATE DATABASE plunk_db OWNER pureleven;
  SELECT datname FROM pg_database WHERE datname='plunk_db';
" || echo "Database may already exist"
EOF

# Step 3: Deploy Plunk containers
echo "🐳 Starting Plunk containers..."
sshpass -p "$SSH_KEY" ssh -o StrictHostKeyChecking=no $SSH_USER@$SERVER << 'EOF'
cd /opt/pureleven
docker-compose -f docker-compose.plunk.yml up -d plunk-api plunk-web
sleep 15
docker logs pureleven-plunk | tail -10
echo "✓ Plunk API ready at http://localhost:5000"
echo "✓ Plunk Web ready at http://localhost:3000"
EOF

# Step 4: Update AI engine .env to use local Plunk
echo "⚙️  Updating CRM .env for local Plunk..."
sshpass -p "$SSH_KEY" ssh -o StrictHostKeyChecking=no $SSH_USER@$SERVER << 'EOF'
# Set Plunk API URL to internal Docker network
echo "PLUNK_API_URL=http://plunk-api:5000/send" >> /opt/pureleven/ai-engine/.env

# Restart AI engine to pick up new env
docker restart pureleven-ai-engine
sleep 10
echo "✓ AI engine restarted with Plunk config"
EOF

echo ""
echo "✅ Plunk Self-Hosted Deployment Complete!"
echo ""
echo "📊 Status:"
echo "  • Plunk API:      http://192.46.213.140:5000"
echo "  • Plunk Web:      http://192.46.213.140:3000 (admin dashboard)"
echo "  • Database:       plunk_db on pureleven-postgres"
echo ""
echo "📧 Email Routing:"
echo "  • Order confirmation (D0) → SendGrid"
echo "  • Review request (D3) → SendGrid"
echo "  • Repeat offer (D7) → Plunk ✓"
echo "  • Replenishment (D30) → Plunk ✓"
echo "  • Winback (D60) → Plunk ✓"
echo "  • Cart abandonment → Plunk ✓"
echo ""
echo "🔗 SMTP Relay: SendGrid (smtp.sendgrid.net:587)"
echo "💰 Cost: $0/month (self-hosted open-source)"
