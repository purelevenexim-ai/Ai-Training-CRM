#!/bin/bash
# Stage 1 Deployment Script - Deploy Conversation Ownership Model to VPS

set -e

VPS_HOST="192.46.213.140"
VPS_USER="root"
VPS_PATH="/root/pureleven_dev"
LOCAL_PATH="/Users/bthomas/Documents/pureleven_dev"

echo "🚀 Stage 1 Deployment: Conversation Ownership Model"
echo "======================================================"
echo ""

# Step 1: Backup current database on VPS
echo "Step 1: Backing up database on VPS..."
ssh "$VPS_USER@$VPS_HOST" "cd $VPS_PATH && sqlite3 app.db '.backup backup_stage1_$(date +%s).db'" || true

# Step 2: Copy new files to VPS
echo "Step 2: Copying Stage 1 files to VPS..."

# Create directories
ssh "$VPS_USER@$VPS_HOST" "mkdir -p $VPS_PATH/anu-login/backend/app/ai"

# Copy core Stage 1 files
scp "$LOCAL_PATH/anu-login/backend/app/ai/message_normalizer.py" "$VPS_USER@$VPS_HOST:$VPS_PATH/anu-login/backend/app/ai/"
scp "$LOCAL_PATH/anu-login/backend/app/ai/conversation_owner.py" "$VPS_USER@$VPS_HOST:$VPS_PATH/anu-login/backend/app/ai/"
scp "$LOCAL_PATH/anu-login/backend/app/ai/flow_state_manager.py" "$VPS_USER@$VPS_HOST:$VPS_PATH/anu-login/backend/app/ai/"
scp "$LOCAL_PATH/anu-login/backend/app/ai/knowledge_retriever.py" "$VPS_USER@$VPS_HOST:$VPS_PATH/anu-login/backend/app/ai/"
scp "$LOCAL_PATH/anu-login/backend/app/ai/intent_router.py" "$VPS_USER@$VPS_HOST:$VPS_PATH/anu-login/backend/app/ai/"

# Copy modified files
scp "$LOCAL_PATH/anu-login/backend/app/storage.py" "$VPS_USER@$VPS_HOST:$VPS_PATH/anu-login/backend/app/"
scp "$LOCAL_PATH/anu-login/backend/app/routes/wave02_wabis_routes.py" "$VPS_USER@$VPS_HOST:$VPS_PATH/anu-login/backend/app/routes/"

echo "✅ Files copied successfully"
echo ""

# Step 3: Restart container
echo "Step 3: Restarting AI engine container..."
ssh "$VPS_USER@$VPS_HOST" "cd $VPS_PATH && docker compose down pureleven-ai-engine || true && sleep 3"
ssh "$VPS_USER@$VPS_HOST" "cd $VPS_PATH && docker compose up -d pureleven-ai-engine"

# Step 4: Wait for container to start
echo "Waiting for container to be ready (10 seconds)..."
sleep 10

# Step 5: Verify container status
echo "Step 4: Verifying deployment..."
HEALTH=$(ssh "$VPS_USER@$VPS_HOST" "docker compose logs pureleven-ai-engine 2>&1 | grep -i 'startup complete' || echo 'WAITING'")

if [[ $HEALTH == *"startup complete"* ]]; then
    echo "✅ Container startup successful"
else
    echo "⏳ Container starting... (may take a moment)"
    echo "Check logs: ssh $VPS_USER@$VPS_HOST 'cd $VPS_PATH && docker compose logs -f pureleven-ai-engine'"
fi

echo ""
echo "🎉 Stage 1 Deployment Complete!"
echo "======================================================"
echo ""
echo "What's new:"
echo "  ✅ conversation_owner table (tracks who owns each conversation)"
echo "  ✅ conversation_flow table (tracks active Wabis flows)"
echo "  ✅ routing_log table (audit trail of routing decisions)"
echo "  ✅ Intent Router (simple rule-based message routing)"
echo "  ✅ Conversation Owner Manager (ownership claims)"
echo "  ✅ Flow State Manager (Wabis flow tracking)"
echo "  ✅ Message Normalizer (input normalization)"
echo "  ✅ Knowledge Retriever (prevent AI hallucinations)"
echo ""
echo "Behavior changes:"
echo "  • Messages route to Wabis first (not AI anymore)"
echo "  • Greetings → Wabis Bot Replies (language selection)"
echo "  • Conversations owned by humans → AI stays silent"
echo "  • Product questions → Catalog/AI with knowledge"
echo "  • Complaints → Escalation queue"
echo ""
echo "Next steps:"
echo "  1. Send test message: 'Hi' (should trigger Wabis Bot Reply)"
echo "  2. Send test message: 'Black pepper' (should get product info)"
echo "  3. Monitor logs: ssh $VPS_USER@$VPS_HOST 'cd $VPS_PATH && docker compose logs -f pureleven-ai-engine'"
echo "  4. Check routing_log table for audit trail"
