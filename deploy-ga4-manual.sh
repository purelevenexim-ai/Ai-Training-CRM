#!/bin/bash
# Quick GA4 relay deployment using Shopify REST API
# Usage: bash deploy-manual.sh SHOPIFY_TOKEN

if [ -z "$1" ]; then
  echo "❌ Usage: bash $0 <SHOPIFY_ADMIN_TOKEN>"
  echo ""
  echo "Get your token from:"
  echo "https://admin.shopify.com/store/rwxtic-gz/settings/apps-and-integrations/admin-api-access-tokens"
  exit 1
fi

TOKEN="$1"
STORE="rwxtic-gz.myshopify.com"
LIVE_THEME_ID="185391776037"
QA_THEME_ID="185391808805"
API_VERSION="2024-01"

# Read the snippet file and encode for JSON
SNIPPET_CONTENT=$(cat snippets/audience-tracking.liquid)

echo "Deploying GA4 relay to themes..."
echo "Store: $STORE"
echo ""

# Function to update theme asset
update_theme_asset() {
  local theme_id=$1
  local theme_name=$2
  
  echo "→ Updating $theme_name (ID: $theme_id)..."
  
  curl -s -X PUT \
    "https://${STORE}/admin/api/${API_VERSION}/themes/${theme_id}/assets.json" \
    -H "X-Shopify-Access-Token: ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"asset\": {\"key\": \"snippets/audience-tracking.liquid\", \"value\": $(echo "$SNIPPET_CONTENT" | jq -Rs .)}}" \
    | jq '.asset | {key, updated_at, content_type}'
    
  if [ $? -eq 0 ]; then
    echo "✅ $theme_name deployed successfully"
  else
    echo "❌ Failed to deploy to $theme_name"
  fi
  echo ""
}

update_theme_asset "$LIVE_THEME_ID" "LIVE"
update_theme_asset "$QA_THEME_ID" "QA"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DEPLOYMENT COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🧪 TEST THE DEPLOYMENT:"
echo "1. Visit: https://pureleven.com/products/any-product"
echo "2. Open DevTools → Network tab"
echo "3. Look for POST to: https://track.pureleven.com/api/crm/events/ga4"
echo "4. Should see pl_product_interest event"
echo ""
echo "📊 MONITOR:"
echo "Visit https://ai.pureleven.com/static/dashboard.html"
echo ""
