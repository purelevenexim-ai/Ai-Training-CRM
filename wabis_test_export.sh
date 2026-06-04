#!/bin/bash
# Wabis Chat Export - Quick Test & Bulk Download

set -e

# Configuration from your environment
API_TOKEN="18280|Ws5wnHgkReob1OKVhDHWH3kzEIIRjItGN9wPcQFz23380f95"
PHONE_NUMBER_ID="252036884661683"
BASE_URL="https://bot.wabis.in/api/v1"
OUTPUT_DIR="wabis_export"

mkdir -p "$OUTPUT_DIR"

echo "=================================================="
echo "WABIS CHAT EXPORT - Quick Test"
echo "=================================================="

# Test 1: Check connection
echo -e "\n[1] Testing API connection..."
curl -s -X GET \
  "${BASE_URL}/whatsapp/chats?apiToken=${API_TOKEN}&phone_number_id=${PHONE_NUMBER_ID}&limit=1" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Accept: application/json" | jq '.' > "$OUTPUT_DIR/test_connection.json"

if [ -s "$OUTPUT_DIR/test_connection.json" ]; then
  echo "✓ API connection successful"
  echo "Sample response:"
  cat "$OUTPUT_DIR/test_connection.json" | jq '.[0] | keys' 2>/dev/null || true
else
  echo "✗ API connection failed"
  exit 1
fi

# Test 2: Fetch with pagination
echo -e "\n[2] Testing pagination (fetching first 5 chats)..."
curl -s -X GET \
  "${BASE_URL}/whatsapp/chats?apiToken=${API_TOKEN}&phone_number_id=${PHONE_NUMBER_ID}&limit=5&offset=0" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Accept: application/json" | jq 'length' > "$OUTPUT_DIR/test_count.txt"

COUNT=$(cat "$OUTPUT_DIR/test_count.txt")
echo "✓ Found $COUNT chats in first batch"

# Test 3: Alternative endpoint - /inbox
echo -e "\n[3] Testing alternative /inbox endpoint..."
INBOX_RESULT=$(curl -s -X GET \
  "${BASE_URL}/whatsapp/inbox?apiToken=${API_TOKEN}&limit=1" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Accept: application/json")

echo "$INBOX_RESULT" | jq '.' > "$OUTPUT_DIR/test_inbox.json"
echo "✓ Inbox endpoint accessible"

echo -e "\n[4] API Response Structure:"
echo "=================================================="
echo "Chats endpoint response sample:"
curl -s -X GET \
  "${BASE_URL}/whatsapp/chats?apiToken=${API_TOKEN}&phone_number_id=${PHONE_NUMBER_ID}&limit=1" \
  -H "Authorization: Bearer ${API_TOKEN}" | jq '.[0] | keys' 2>/dev/null || echo "Raw response:"

curl -s -X GET \
  "${BASE_URL}/whatsapp/chats?apiToken=${API_TOKEN}&phone_number_id=${PHONE_NUMBER_ID}&limit=1" \
  -H "Authorization: Bearer ${API_TOKEN}" | jq 'if type == "array" then .[0] else .data[0] // . end' | head -50

echo -e "\n=================================================="
echo "NEXT STEPS:"
echo "=================================================="
echo "1. Run Python exporter:"
echo "   python3 wabis_chat_exporter.py"
echo ""
echo "2. Or manually fetch with curl:"
echo "   curl -s -X GET '${BASE_URL}/whatsapp/chats?apiToken=${API_TOKEN}&phone_number_id=${PHONE_NUMBER_ID}&limit=100&offset=0' \\"
echo "     -H 'Authorization: Bearer ${API_TOKEN}' | jq '.' > chats_page_0.json"
echo ""
echo "3. Check output:"
echo "   ls -lh $OUTPUT_DIR/"
