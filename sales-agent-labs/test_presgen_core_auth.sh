#!/bin/bash
# Test PresGen Core Service Account Authentication
# This will trigger a presentation creation to verify service account is being used

echo "Testing PresGen Core service account authentication..."
echo ""

# Test data
TEST_DATA='{
  "report_text": "Test presentation to verify service account authentication is working.",
  "num_slides": 1,
  "use_cache": false
}'

echo "Sending test request to presgen-core..."
echo ""

# Call the render endpoint
RESPONSE=$(curl -s -X POST http://localhost:8080/render \
  -H "Content-Type: application/json" \
  -d "$TEST_DATA")

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Check for OAuth error
if echo "$RESPONSE" | grep -q "oauth_slides_client.json"; then
    echo "❌ FAILED: Still getting OAuth error"
    echo "Service account authentication is NOT working"
    exit 1
elif echo "$RESPONSE" | grep -q "error"; then
    echo "⚠️  Got an error (check if it's auth-related):"
    echo "$RESPONSE" | grep -o "error.*"
    exit 1
else
    echo "✅ SUCCESS: No OAuth error detected"
    echo "Service account authentication appears to be working!"
    exit 0
fi
