#!/bin/bash
set -euo pipefail

# Shopify Theme Snippet Deployment Script
# Uses Shopify CLI theme push with a Theme Access / app automation token.

STORE_URL="rwxtic-gz.myshopify.com"
LIVE_THEME_ID="185391776037"
QA_THEME_ID="185391808805"
SNIPPET_FILE="snippets/audience-tracking.liquid"

TOKEN="${SHOPIFY_THEME_PASSWORD:-${SHOPIFY_ADMIN_TOKEN:-}}"

if [ -z "$TOKEN" ]; then
  echo "SHOPIFY_THEME_PASSWORD not found in environment."
  echo "Please provide your Shopify Theme Access / app automation token:"
  read -r -s TOKEN
  echo
fi

if [ ! -f "$SNIPPET_FILE" ]; then
  echo "ERROR: $SNIPPET_FILE not found"
  exit 1
fi

if ! command -v shopify >/dev/null 2>&1; then
  echo "ERROR: Shopify CLI is not installed or not on PATH"
  exit 1
fi

deploy_to_theme() {
  local theme_id="$1"
  local theme_name="$2"
  local -a extra_flags=()

  if [ "$theme_id" = "$LIVE_THEME_ID" ]; then
    extra_flags+=(--allow-live)
  fi

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Deploying to $theme_name (Theme ID: $theme_id)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  shopify theme push \
    --store "$STORE_URL" \
    --theme "$theme_id" \
    --password "$TOKEN" \
    --path "$(pwd)" \
    --only "$SNIPPET_FILE" \
    --no-color \
    "${extra_flags[@]}"

  echo "✅ SUCCESS: Snippet deployed to $theme_name"
}

echo "Starting deployment of audience-tracking.liquid"
echo "Store: $STORE_URL"
echo ""

deploy_to_theme "$LIVE_THEME_ID" "LIVE THEME"
deploy_to_theme "$QA_THEME_ID" "QA THEME"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DEPLOYMENT COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo "1. Visit https://pureleven.com/products/any-product"
echo "2. Open browser DevTools → Network tab"
echo "3. Look for POST requests to https://track.pureleven.com/api/crm/events/ga4"
echo "4. Visit https://ai.pureleven.com/static/dashboard.html to monitor events"
echo ""
