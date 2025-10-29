#!/bin/bash
# Check if APIs are actually enabled and service account has access

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}Checking Google Cloud Project Configuration${NC}"
echo -e "${BLUE}======================================================================${NC}\n"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}gcloud CLI not installed${NC}"
    echo -e "${YELLOW}Install from: https://cloud.google.com/sdk/docs/install${NC}"
    echo ""
    echo "For macOS:"
    echo "  brew install --cask google-cloud-sdk"
    exit 1
fi

# Get current project
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")

if [ -z "$CURRENT_PROJECT" ]; then
    echo -e "${YELLOW}No project currently set${NC}"
    echo "Setting project to 'presgen'..."
    gcloud config set project presgen
fi

echo -e "${GREEN}Current project: ${CURRENT_PROJECT:-presgen}${NC}\n"

# Check if user is authenticated
echo -e "${BLUE}[1] Checking authentication...${NC}"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q .; then
    echo -e "${RED}Not authenticated!${NC}"
    echo "Run: gcloud auth login"
    exit 1
fi

ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
echo -e "    ${GREEN}✓ Authenticated as: ${ACCOUNT}${NC}\n"

# Check enabled services
echo -e "${BLUE}[2] Checking enabled APIs...${NC}"

REQUIRED_APIS=(
    "slides.googleapis.com"
    "drive.googleapis.com"
    "forms.googleapis.com"
    "sheets.googleapis.com"
)

ALL_ENABLED=true

for API in "${REQUIRED_APIS[@]}"; do
    if gcloud services list --enabled --filter="name:$API" --format="value(name)" 2>/dev/null | grep -q "$API"; then
        echo -e "    ${GREEN}✓ $API${NC}"
    else
        echo -e "    ${RED}✗ $API NOT ENABLED${NC}"
        ALL_ENABLED=false
    fi
done

if [ "$ALL_ENABLED" = false ]; then
    echo -e "\n${YELLOW}Enabling missing APIs...${NC}"
    for API in "${REQUIRED_APIS[@]}"; do
        echo "Enabling $API..."
        gcloud services enable "$API" --project=presgen
    done
    echo -e "${GREEN}APIs enabled. Waiting 2 minutes for propagation...${NC}"
    sleep 120
fi

# Check service account
echo -e "\n${BLUE}[3] Checking service account...${NC}"

SA_EMAIL="presgen-service-account-test@presgen.iam.gserviceaccount.com"

if gcloud iam service-accounts list --filter="email:$SA_EMAIL" --format="value(email)" 2>/dev/null | grep -q "$SA_EMAIL"; then
    echo -e "    ${GREEN}✓ Service account exists: $SA_EMAIL${NC}"

    # Check IAM bindings
    echo -e "\n${BLUE}[4] Checking IAM roles...${NC}"

    ROLES=$(gcloud projects get-iam-policy presgen \
        --flatten="bindings[].members" \
        --filter="bindings.members:serviceAccount:$SA_EMAIL" \
        --format="value(bindings.role)" 2>/dev/null)

    if [ -z "$ROLES" ]; then
        echo -e "    ${RED}✗ No roles assigned to service account!${NC}"
        echo -e "\n${YELLOW}This is the problem!${NC}"
        echo "The service account has no IAM roles."
        echo ""
        echo "Fix by running:"
        echo "  gcloud projects add-iam-policy-binding presgen \\"
        echo "    --member='serviceAccount:$SA_EMAIL' \\"
        echo "    --role='roles/editor'"
    else
        echo -e "    ${GREEN}Assigned roles:${NC}"
        echo "$ROLES" | while read -r role; do
            echo -e "      ${GREEN}✓ $role${NC}"
        done
    fi
else
    echo -e "    ${RED}✗ Service account NOT found: $SA_EMAIL${NC}"
    echo -e "\n${YELLOW}Create service account:${NC}"
    echo "  gcloud iam service-accounts create presgen-service-account-test \\"
    echo "    --display-name='PresGen Service Account' \\"
    echo "    --project=presgen"
fi

# Check billing
echo -e "\n${BLUE}[5] Checking billing...${NC}"

BILLING=$(gcloud beta billing projects describe presgen --format="value(billingEnabled)" 2>/dev/null || echo "unknown")

if [ "$BILLING" = "True" ]; then
    echo -e "    ${GREEN}✓ Billing enabled${NC}"
elif [ "$BILLING" = "False" ]; then
    echo -e "    ${RED}✗ Billing NOT enabled${NC}"
    echo -e "\n${YELLOW}Some APIs require billing to be enabled${NC}"
    echo "Enable at: https://console.cloud.google.com/billing?project=presgen"
else
    echo -e "    ${YELLOW}⚠ Cannot determine billing status${NC}"
    echo "Check manually: https://console.cloud.google.com/billing?project=presgen"
fi

# Check project status
echo -e "\n${BLUE}[6] Checking project status...${NC}"

PROJECT_STATUS=$(gcloud projects describe presgen --format="value(lifecycleState)" 2>/dev/null || echo "unknown")

if [ "$PROJECT_STATUS" = "ACTIVE" ]; then
    echo -e "    ${GREEN}✓ Project is active${NC}"
else
    echo -e "    ${RED}✗ Project status: $PROJECT_STATUS${NC}"
fi

# Test API directly with gcloud
echo -e "\n${BLUE}[7] Testing Slides API with gcloud...${NC}"

echo "Creating test presentation using service account..."

# Try to impersonate service account and create presentation
if gcloud auth application-default print-access-token --impersonate-service-account="$SA_EMAIL" &>/dev/null; then

    ACCESS_TOKEN=$(gcloud auth application-default print-access-token --impersonate-service-account="$SA_EMAIL")

    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"title": "gcloud Test Presentation"}' \
        "https://slides.googleapis.com/v1/presentations" 2>&1)

    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)

    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "    ${GREEN}✓ Successfully created presentation via gcloud!${NC}"
        PRES_ID=$(echo "$BODY" | grep -o '"presentationId":"[^"]*"' | cut -d'"' -f4)
        echo -e "    ${GREEN}Presentation ID: $PRES_ID${NC}"
        echo ""
        echo -e "${GREEN}This means the service account DOES have permission!${NC}"
        echo -e "${YELLOW}The issue is with the Python library or key file.${NC}"
        echo ""
        echo "Try creating a NEW service account key:"
        echo "  1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts?project=presgen"
        echo "  2. Click on service account"
        echo "  3. Keys → Add Key → Create new key → JSON"
        echo "  4. Replace secrets/google-creds.json"
    else
        echo -e "    ${RED}✗ Failed with HTTP $HTTP_CODE${NC}"
        echo "Response: $BODY"

        if [ "$HTTP_CODE" = "403" ]; then
            echo ""
            echo -e "${RED}403 error even with gcloud!${NC}"
            echo -e "${YELLOW}This confirms a service account permission issue.${NC}"
            echo ""
            echo "Grant Editor role:"
            echo "  gcloud projects add-iam-policy-binding presgen \\"
            echo "    --member='serviceAccount:$SA_EMAIL' \\"
            echo "    --role='roles/editor'"
        fi
    fi
else
    echo -e "    ${RED}✗ Cannot impersonate service account${NC}"
    echo "You may lack 'Service Account Token Creator' role"
    echo ""
    echo "Grant yourself the role:"
    echo "  gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \\"
    echo "    --member='user:$ACCOUNT' \\"
    echo "    --role='roles/iam.serviceAccountTokenCreator' \\"
    echo "    --project=presgen"
fi

echo ""
echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}======================================================================${NC}\n"

echo "If gcloud test succeeded but Python fails:"
echo "  → Create new service account key"
echo ""
echo "If gcloud test also failed with 403:"
echo "  → Grant Editor role to service account"
echo "  → Run: gcloud projects add-iam-policy-binding presgen \\"
echo "           --member='serviceAccount:$SA_EMAIL' \\"
echo "           --role='roles/editor'"
echo ""
