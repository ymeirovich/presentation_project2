#!/bin/bash
# ============================================================================
# PresGen Services Startup Script
# ============================================================================
# Starts all three services in the correct order with proper port configuration
# Last Updated: 2025-10-04
#
# Architecture:
#   - PresGen-Assess: :8000 (Backend API for assessments)
#   - PresGen-Core:   :8080 (Video generation service)
#   - PresGen-UI:     :3000 (Next.js frontend)

set -e  # Exit on error

# Load environment variables
if [ -f .env ]; then
    echo "📁 Loading environment variables from .env"
    export $(grep -v '^#' .env | xargs)
else
    echo "⚠️  Warning: .env file not found - using defaults"
fi

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "============================================================================"
echo "🚀 Starting PresGen Services"
echo "============================================================================"
echo ""
echo "📡 Service Configuration:"
echo "  - PresGen-Assess: http://localhost:${PRESGEN_ASSESS_PORT:-8000}"
echo "  - PresGen-Core:   http://localhost:${PRESGEN_CORE_PORT:-8080}"
echo "  - PresGen-UI:     http://localhost:${PRESGEN_UI_PORT:-3000}"
echo ""

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo -e "${YELLOW}⚠️  Port $port is already in use${NC}"
        echo -e "${YELLOW}   Run 'lsof -ti:$port | xargs kill' to free it${NC}"
        return 1
    fi
    return 0
}

# Function to start a service
start_service() {
    local name=$1
    local port=$2
    local dir=$3
    local command=$4

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Starting: $name on port $port${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if ! check_port $port; then
        echo -e "${RED}✗ Cannot start $name - port $port is in use${NC}"
        return 1
    fi

    cd "$PROJECT_ROOT/$dir"
    echo -e "${GREEN}✓ Changed directory to: $(pwd)${NC}"
    echo -e "${GREEN}✓ Running command: $command${NC}"

    # Start the service in background
    eval "$command" &
    local pid=$!
    echo -e "${GREEN}✓ Started $name with PID: $pid${NC}"

    # Give it a moment to start
    sleep 2

    # Check if still running
    if ps -p $pid > /dev/null; then
        echo -e "${GREEN}✓ $name is running successfully${NC}"
    else
        echo -e "${RED}✗ $name failed to start${NC}"
        return 1
    fi
}

# Check ports before starting
echo "🔍 Checking ports..."
echo ""

PORTS_OK=true
if ! check_port ${PRESGEN_ASSESS_PORT:-8000}; then PORTS_OK=false; fi
if ! check_port ${PRESGEN_CORE_PORT:-8080}; then PORTS_OK=false; fi
if ! check_port ${PRESGEN_UI_PORT:-3000}; then PORTS_OK=false; fi

if [ "$PORTS_OK" = false ]; then
    echo ""
    echo -e "${RED}✗ Cannot start services - some ports are in use${NC}"
    echo -e "${YELLOW}Run the following to free ports:${NC}"
    echo -e "${YELLOW}  pkill -f 'uvicorn.*8000'${NC}"
    echo -e "${YELLOW}  pkill -f 'uvicorn.*8080'${NC}"
    echo -e "${YELLOW}  pkill -f 'next.*3000'${NC}"
    exit 1
fi

# Start services in order
echo -e "${GREEN}✓ All ports are available${NC}"
echo ""

# 1. Start PresGen-Core (port 8080)
start_service \
    "PresGen-Core" \
    "${PRESGEN_CORE_PORT:-8080}" \
    "." \
    "uvicorn src.service.http:app --reload --port ${PRESGEN_CORE_PORT:-8080} > logs/presgen-core.log 2>&1"

# 2. Start PresGen-Assess (port 8000)
start_service \
    "PresGen-Assess" \
    "${PRESGEN_ASSESS_PORT:-8000}" \
    "presgen-assess" \
    "uvicorn src.service.app:app --reload --port ${PRESGEN_ASSESS_PORT:-8000} > logs/presgen-assess.log 2>&1"

# 3. Start PresGen-UI (port 3000)
start_service \
    "PresGen-UI" \
    "${PRESGEN_UI_PORT:-3000}" \
    "presgen-ui" \
    "npm run dev -- --port ${PRESGEN_UI_PORT:-3000} > logs/presgen-ui.log 2>&1"

echo ""
echo "============================================================================"
echo -e "${GREEN}✓ All services started successfully!${NC}"
echo "============================================================================"
echo ""
echo "📡 Service URLs:"
echo "  - PresGen-Assess: http://localhost:${PRESGEN_ASSESS_PORT:-8000}"
echo "  - PresGen-Core:   http://localhost:${PRESGEN_CORE_PORT:-8080}"
echo "  - PresGen-UI:     http://localhost:${PRESGEN_UI_PORT:-3000}"
echo ""
echo "📋 Logs:"
echo "  - tail -f logs/presgen-assess.log"
echo "  - tail -f logs/presgen-core.log"
echo "  - tail -f logs/presgen-ui.log"
echo ""
echo "🛑 To stop all services:"
echo "  pkill -f 'uvicorn'"
echo "  pkill -f 'next'"
echo ""
echo "Press Ctrl+C to stop monitoring this script (services will continue running)"
echo ""

# Keep script running to show it's managing services
wait
