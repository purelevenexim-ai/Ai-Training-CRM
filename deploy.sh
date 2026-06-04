#!/bin/bash
# Pureleven Unified Tracking System — Server Deployment Script
# Run on: 192.46.213.140 (server)
# Usage: ./deploy.sh

set -e

echo "🚀 Pureleven CRM Deployment Started..."
echo "=====================================\n"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ============================================
# PHASE 1: Verify Environment Variables
# ============================================
echo -e "${YELLOW}PHASE 1: Checking Environment Variables${NC}"

required_vars=(
    "META_CAPI_PIXEL_ID"
    "META_CAPI_ACCESS_TOKEN"
    "GADS_DEVELOPER_TOKEN"
    "GADS_CUSTOMER_ID"
    "GADS_CONVERSION_ACTION_ID"
    "GADS_OAUTH_REFRESH_TOKEN"
    "GA4_MEASUREMENT_ID"
    "GA4_API_SECRET"
    "SHIPROCKET_WEBHOOK_TOKEN"
    "INTERNAL_API_KEY"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
        echo -e "${RED}✗ $var NOT SET${NC}"
    else
        echo -e "${GREEN}✓ $var is set${NC}"
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo -e "\n${RED}ERROR: Missing environment variables:${NC}"
    printf '%s\n' "${missing_vars[@]}"
    echo -e "\n${YELLOW}Add these to your .env file and try again${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All required environment variables are set\n${NC}"

# ============================================
# PHASE 2: Pull Latest Code
# ============================================
echo -e "${YELLOW}PHASE 2: Pulling Latest Code${NC}"

cd /root/pureleven_dev  # Adjust path as needed

git fetch origin
git pull origin main

echo -e "${GREEN}✓ Code updated\n${NC}"

# ============================================
# PHASE 3: Run Database Migration
# ============================================
echo -e "${YELLOW}PHASE 3: Running Database Migration${NC}"

python alembic_migration_crm_v2.py

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Migration failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Migration completed\n${NC}"

# ============================================
# PHASE 4: Restart Docker Services
# ============================================
echo -e "${YELLOW}PHASE 4: Restarting Docker Services${NC}"

docker compose restart crm-api

# Wait for service to be ready
echo "Waiting for API to become healthy..."
sleep 5

# ============================================
# PHASE 5: Health Check
# ============================================
echo -e "${YELLOW}PHASE 5: Health Check${NC}"

health_check=$(curl -s https://ai.pureleven.com/api/crm/health)

if echo "$health_check" | grep -q "healthy"; then
    echo -e "${GREEN}✓ API Health: OK${NC}"
    echo "Response: $health_check\n"
else
    echo -e "${RED}✗ API Health Check Failed${NC}"
    echo "Response: $health_check"
    exit 1
fi

# ============================================
# PHASE 6: Verify Database
# ============================================
echo -e "${YELLOW}PHASE 6: Verifying Database${NC}"

# Check if unified_identity table exists
table_check=$(psql -U postgres -d pureleven -t -c "
    SELECT table_name FROM information_schema.tables 
    WHERE table_name = 'unified_identity' 
    AND table_schema = 'public';
" 2>&1)

if [ -n "$table_check" ]; then
    echo -e "${GREEN}✓ unified_identity table exists${NC}"
else
    echo -e "${RED}✗ unified_identity table NOT found${NC}"
    exit 1
fi

# Count existing records
record_count=$(psql -U postgres -d pureleven -t -c "SELECT COUNT(*) FROM unified_identity;" 2>&1)
echo -e "${GREEN}✓ Current records in unified_identity: $record_count${NC}\n"

# ============================================
# PHASE 7: Test API Endpoints
# ============================================
echo -e "${YELLOW}PHASE 7: Testing API Endpoints${NC}"

# Test /identify endpoint
identify_test=$(curl -s -X POST https://ai.pureleven.com/api/crm/identify \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-'$(date +%s)'",
    "email": "test@example.com",
    "phone": "9876543210",
    "utm_source": "deploy_test"
  }')

if echo "$identify_test" | grep -q "identity_id"; then
    echo -e "${GREEN}✓ /identify endpoint working${NC}"
else
    echo -e "${RED}✗ /identify endpoint failed${NC}"
    echo "Response: $identify_test"
fi

# Test /abandonment/checkout endpoint
abandonment_test=$(curl -s "https://ai.pureleven.com/api/crm/abandonment/checkout?window_minutes=15")

if echo "$abandonment_test" | grep -q "count"; then
    echo -e "${GREEN}✓ /abandonment/checkout endpoint working${NC}"
else
    echo -e "${RED}✗ /abandonment/checkout endpoint failed${NC}"
    echo "Response: $abandonment_test"
fi

echo ""

# ============================================
# PHASE 8: Summary
# ============================================
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE!${NC}"
echo "=====================================\n"

echo "Next Steps:"
echo "1. Import N8N workflows at: https://automation.pureleven.com"
echo "   - workflow_checkout_abandonment.json"
echo "   - workflow_cart_abandonment.json"
echo "   - workflow_replenishment.json"
echo "   - workflow_winback.json"
echo ""
echo "2. Configure Wabis API credential in N8N with your API token"
echo ""
echo "3. Create/verify Wabis message templates (7 templates)"
echo ""
echo "4. Place a test order with COD to verify Meta CAPI/Google Ads/GA4"
echo ""
echo "5. Activate N8N workflows one by one"
echo ""
echo "See DEPLOYMENT_CHECKLIST.md for detailed instructions"
