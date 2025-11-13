#!/bin/bash
# PresGen Baseline Testing Script
# Purpose: Establish performance and functionality baseline before AWS migration
# Version: 1.0
# Date: 2025-11-13

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="http://localhost"
AUTH="demo_user:AllCloud2024!"
OUTPUT_DIR="aws_migration/test-results"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
RESULTS_FILE="$OUTPUT_DIR/baseline-results-$TIMESTAMP.md"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Initialize results file
cat > "$RESULTS_FILE" <<EOF
# PresGen Baseline Test Results

**Date:** $(date)
**Environment:** Local Docker Compose
**Purpose:** Pre-AWS migration baseline

---

## Test Summary

EOF

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PresGen Baseline Testing${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Test counter
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to record test result
record_test() {
    local test_name="$1"
    local status="$2"
    local duration="$3"
    local notes="$4"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ "$status" == "PASS" ]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo -e "${GREEN}✓ PASS${NC} - $test_name (${duration}s)"
        echo "- [x] **$test_name** - ${duration}s - $notes" >> "$RESULTS_FILE"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "${RED}✗ FAIL${NC} - $test_name"
        echo "- [ ] **$test_name** - FAILED - $notes" >> "$RESULTS_FILE"
    fi
}

# Function to measure execution time
measure_time() {
    local start=$(date +%s)
    "$@"
    local end=$(date +%s)
    echo $((end - start))
}

echo -e "${YELLOW}Step 1: Health Check Tests${NC}"
echo "" >> "$RESULTS_FILE"
echo "## Health Check Tests" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Test 1: nginx health
echo -n "Testing nginx... "
if curl -s -f -u "$AUTH" "$BASE_URL/" > /dev/null 2>&1; then
    record_test "nginx health check" "PASS" "0" "nginx responding"
else
    record_test "nginx health check" "FAIL" "0" "nginx not responding"
fi

# Test 2: presgen-core health
echo -n "Testing presgen-core... "
if curl -s -f "$BASE_URL:8080/healthz" > /dev/null 2>&1; then
    record_test "presgen-core health check" "PASS" "0" "Core service healthy"
else
    record_test "presgen-core health check" "FAIL" "0" "Core service not responding"
fi

# Test 3: presgen-assess health
echo -n "Testing presgen-assess... "
if curl -s -f -u "$AUTH" "$BASE_URL/api/presgen-assess/health" > /dev/null 2>&1; then
    record_test "presgen-assess health check" "PASS" "0" "Assess service healthy"
else
    record_test "presgen-assess health check" "FAIL" "0" "Assess service not responding"
fi

# Test 4: presgen-avatar health
echo -n "Testing presgen-avatar... "
if curl -s -f "$BASE_URL:8002/healthz" > /dev/null 2>&1; then
    record_test "presgen-avatar health check" "PASS" "0" "Avatar service healthy"
else
    record_test "presgen-avatar health check" "FAIL" "0" "Avatar service not responding"
fi

# Test 5: Redis connectivity
echo -n "Testing Redis... "
if docker exec presgen-redis redis-cli ping > /dev/null 2>&1; then
    record_test "Redis connectivity" "PASS" "0" "Redis responding to PING"
else
    record_test "Redis connectivity" "FAIL" "0" "Redis not responding"
fi

echo ""
echo -e "${YELLOW}Step 2: Simple Presentation Generation${NC}"
echo "" >> "$RESULTS_FILE"
echo "## Presentation Generation Tests" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Test 6: Simple presentation (5 slides, no AI images)
echo "Generating simple presentation (5 slides, no AI images)..."
START_TIME=$(date +%s)

RESPONSE=$(curl -s -u "$AUTH" -X POST "$BASE_URL/api/presgen/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Baseline Test - Simple Presentation",
    "slides": 5,
    "use_ai_images": false
  }' 2>&1)

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if echo "$RESPONSE" | grep -q "presentation"; then
    record_test "Simple presentation (5 slides, no AI)" "PASS" "$DURATION" "Generated successfully"
else
    record_test "Simple presentation (5 slides, no AI)" "FAIL" "$DURATION" "Generation failed: $RESPONSE"
fi

echo ""
echo -e "${YELLOW}Step 3: Presentation with AI Images${NC}"

# Test 7: Presentation with AI images
echo "Generating presentation with AI images (5 slides)..."
START_TIME=$(date +%s)

RESPONSE=$(curl -s -u "$AUTH" -X POST "$BASE_URL/api/presgen/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Baseline Test - AI Images",
    "slides": 5,
    "use_ai_images": true
  }' 2>&1)

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if echo "$RESPONSE" | grep -q "presentation"; then
    record_test "Presentation with AI images (5 slides)" "PASS" "$DURATION" "Generated with Imagen"
else
    record_test "Presentation with AI images (5 slides)" "FAIL" "$DURATION" "Generation failed: $RESPONSE"
fi

echo ""
echo -e "${YELLOW}Step 4: Complex Presentation (Timeout Test)${NC}"

# Test 8: Complex presentation (30 slides) - Tests timeout fix
echo "Generating complex presentation (30 slides)..."
echo -e "${YELLOW}This will take 6-10 minutes...${NC}"
START_TIME=$(date +%s)

RESPONSE=$(curl -s -u "$AUTH" -X POST "$BASE_URL/api/presgen/generate" \
  -H "Content-Type: application/json" \
  --max-time 720 \
  -d '{
    "topic": "Baseline Test - Complex AWS Architecture",
    "slides": 30,
    "use_ai_images": false
  }' 2>&1)

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if echo "$RESPONSE" | grep -q "presentation" && [ $DURATION -lt 660 ]; then
    record_test "Complex presentation (30 slides, timeout fix)" "PASS" "$DURATION" "Completed within 11 minutes (timeout: 10 min)"
else
    record_test "Complex presentation (30 slides, timeout fix)" "FAIL" "$DURATION" "Timeout or generation failed"
fi

echo ""
echo -e "${YELLOW}Step 5: Resource Usage Metrics${NC}"
echo "" >> "$RESULTS_FILE"
echo "## Resource Usage" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Docker stats
echo "Collecting Docker resource usage..."
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" > "$OUTPUT_DIR/docker-stats-$TIMESTAMP.txt"

cat "$OUTPUT_DIR/docker-stats-$TIMESTAMP.txt" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"
echo -e "Success Rate: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%"
echo ""
echo -e "Results saved to: ${BLUE}$RESULTS_FILE${NC}"

# Add summary to results file
cat >> "$RESULTS_FILE" <<EOF

---

## Summary

- **Total Tests:** $TOTAL_TESTS
- **Passed:** $PASSED_TESTS
- **Failed:** $FAILED_TESTS
- **Success Rate:** $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%

---

## Notes

1. **Timeout Fix Verification:** Complex presentation test validates the 10-minute timeout increase.
2. **Performance Baseline:** These metrics will be compared against AWS deployment.
3. **Next Steps:** Proceed with Phase 2 (AWS Infrastructure Setup) if all critical tests pass.

---

**Test Environment:**
- Platform: Local Docker Compose
- Machine: $(uname -a)
- Docker Version: $(docker --version)

**Generated:** $(date)
EOF

# Exit with failure if any tests failed
if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "${RED}Some tests failed. Review results before proceeding with migration.${NC}"
    exit 1
else
    echo -e "${GREEN}All tests passed! Ready for AWS migration.${NC}"
    exit 0
fi
