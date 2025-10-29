#!/bin/bash

# Request Google Cloud API Quota Increase
# Run this BEFORE demo (takes 2-5 business days to process)

PROJECT_ID="presgen"

echo "📝 Requesting quota increases for project: ${PROJECT_ID}"
echo "⚠️  Note: Quota increase requests typically take 2-5 business days"
echo ""

request_quota() {
    local service="$1"
    local metric="$2"
    local new_limit="$3"
    local friendly_name="$4"

    echo "📤 Requesting: ${friendly_name} → ${new_limit}"

    gcloud alpha services quota update \
        --service="${service}" \
        --consumer="project:${PROJECT_ID}" \
        --metric="${metric}" \
        --value="${new_limit}" \
        --force 2>/dev/null && echo "  ✅ Request submitted" || echo "  ⚠️  Request failed or already at limit"
}

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI not found"
    echo "   Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo "❌ Error: Not authenticated with gcloud"
    echo "   Run: gcloud auth login"
    exit 1
fi

# Request increases for demo workload
echo "Submitting quota increase requests..."
echo ""

request_quota \
    "slides.googleapis.com" \
    "ReadRequests" \
    "1000" \
    "Slides API Read Requests (from 300 to 1000 per minute)"

request_quota \
    "slides.googleapis.com" \
    "WriteRequests" \
    "500" \
    "Slides API Write Requests (from 100 to 500 per minute)"

request_quota \
    "drive.googleapis.com" \
    "Queries" \
    "2000" \
    "Drive API Queries (from 1000 to 2000 per 100 seconds)"

request_quota \
    "forms.googleapis.com" \
    "ReadRequests" \
    "1000" \
    "Forms API Read Requests (from 300 to 1000 per minute)"

echo ""
echo "================================================================"
echo "✅ Quota increase requests submitted!"
echo ""
echo "📧 You'll receive email updates on request status"
echo "📊 Track requests at:"
echo "   https://console.cloud.google.com/apis/quotas?project=${PROJECT_ID}"
echo ""
echo "⏰ Timeline:"
echo "   - Auto-approved (instant): Small increases"
echo "   - Manual review (2-5 days): Larger increases"
echo ""
echo "💡 Tip: Submit these requests 1 week before your demo!"
