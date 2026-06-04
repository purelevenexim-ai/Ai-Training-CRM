#!/bin/bash
# Credential Collection Helper — Pureleven Unified Tracking System
# Follow this guide to collect all 8 credentials

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     CREDENTIAL COLLECTION GUIDE — Pureleven CRM System        ║"
echo "║     Follow instructions below for each platform               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Create a temporary credentials file
CREDS_FILE="/tmp/pureleven_credentials_$(date +%s).txt"
touch "$CREDS_FILE"
chmod 600 "$CREDS_FILE"

echo "📁 Credentials will be saved to: $CREDS_FILE"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Function to collect credential
collect_credential() {
    local num=$1
    local name=$2
    local instructions=$3
    local url=$4
    
    echo ""
    echo "CREDENTIAL $num: $name"
    echo "─────────────────────────────────────────────────────────────"
    echo "Instructions: $instructions"
    echo ""
    if [ ! -z "$url" ]; then
        echo "🔗 Open this URL: $url"
        echo ""
    fi
    
    read -p "Enter the value for $name: " credential_value
    
    if [ -z "$credential_value" ]; then
        echo "⚠️  Warning: Credential is empty. Skipping..."
    else
        echo "✓ Saved"
        echo "$name=$credential_value" >> "$CREDS_FILE"
    fi
}

echo "🚀 Let's collect the 8 credentials needed for deployment!"
echo ""

# Credential 1: META_CAPI_ACCESS_TOKEN
collect_credential 1 "META_CAPI_ACCESS_TOKEN" \
    "Go to business.facebook.com → Settings → System Users → Create/Copy existing token" \
    "https://business.facebook.com/settings/system-users"

# Credential 2: GADS_DEVELOPER_TOKEN
collect_credential 2 "GADS_DEVELOPER_TOKEN" \
    "Go to ads.google.com → Tools → API Center → Copy Developer Token (admin approval required)" \
    "https://ads.google.com"

# Credential 3: GADS_OAUTH_REFRESH_TOKEN
collect_credential 3 "GADS_OAUTH_REFRESH_TOKEN" \
    "From Google Cloud Console → OAuth 2.0 Credentials → Copy Refresh Token from OAuth flow" \
    "https://console.cloud.google.com/apis/credentials"

# Credential 4: GADS_CONVERSION_ACTION_ID
collect_credential 4 "GADS_CONVERSION_ACTION_ID" \
    "Go to ads.google.com → Tools → Conversions → Select/Create 'Offline purchases' → Copy ID" \
    "https://ads.google.com/aw/conversions"

# Credential 5: GA4_API_SECRET
collect_credential 5 "GA4_API_SECRET" \
    "Go to analytics.google.com → Admin → Data API → Create API property access → Copy secret" \
    "https://analytics.google.com"

# Credential 6: SHIPROCKET_WEBHOOK_TOKEN
collect_credential 6 "SHIPROCKET_WEBHOOK_TOKEN" \
    "Go to Shiprocket Dashboard → Settings → Webhooks → Enable & copy token" \
    "https://shiprocket.in/dashboard"

# Credential 7: WABIS_API_TOKEN
collect_credential 7 "WABIS_API_TOKEN" \
    "Go to wabis.in → Dashboard → API Keys → Copy Bearer token" \
    "https://app.wabis.in/dashboard"

# Credential 8: INTERNAL_API_KEY
echo ""
echo "CREDENTIAL 8: INTERNAL_API_KEY"
echo "─────────────────────────────────────────────────────────────"
echo "Instructions: Generate a random 32-character string"
echo ""
GENERATED_KEY=$(openssl rand -base64 32 | tr -d '=' | head -c 32)
echo "Generated key: $GENERATED_KEY"
read -p "Use this? (y/n, or paste your own): " use_generated

if [ "$use_generated" = "n" ] || [ "$use_generated" = "N" ]; then
    read -p "Enter your own INTERNAL_API_KEY: " custom_key
    echo "INTERNAL_API_KEY=$custom_key" >> "$CREDS_FILE"
    echo "PURELEVEN_INTERNAL_API_KEY=$custom_key" >> "$CREDS_FILE"
else
    echo "INTERNAL_API_KEY=$GENERATED_KEY" >> "$CREDS_FILE"
    echo "PURELEVEN_INTERNAL_API_KEY=$GENERATED_KEY" >> "$CREDS_FILE"
    echo "✓ Saved"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "✅ All credentials collected!"
echo ""
echo "📋 Summary of collected credentials:"
echo "───────────────────────────────────────────────────────────────"
cat "$CREDS_FILE"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "1. SSH to server: ssh root@192.46.213.140"
echo "2. Edit .env: nano .env"
echo "3. Add these credentials to your .env file"
echo "4. Save and exit (Ctrl+X, Y, Enter)"
echo "5. Run: git pull && python alembic_migration_crm_v2.py && docker compose restart crm-api"
echo ""
echo "✋ IMPORTANT: Keep the credentials file safe!"
echo "   Temp file: $CREDS_FILE"
echo ""
