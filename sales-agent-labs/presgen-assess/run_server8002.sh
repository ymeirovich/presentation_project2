#!/bin/bash
#
# PresGen-Assess Development Server Launcher
#
# This script ensures proper PYTHONPATH setup for Google Slides integration
# and starts the FastAPI server with uvicorn.
#
# Usage:
#   ./run_server.sh [--production]
#
# Options:
#   --production    Run without auto-reload (for production)
#

set -e

# Get the absolute path to sales-agent-labs (parent of presgen-assess)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SALES_AGENT_LABS_DIR="$(dirname "$SCRIPT_DIR")"

# Export PYTHONPATH to include sales-agent-labs for src.agent.slides_google imports
export PYTHONPATH="${SALES_AGENT_LABS_DIR}:${PYTHONPATH}"

echo "🚀 Starting PresGen-Assess server..."
echo "📁 Working directory: $SCRIPT_DIR"
echo "🔧 PYTHONPATH: $PYTHONPATH"
echo ""

# Check if virtualenv is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Warning: Virtual environment not activated"
    echo "💡 Activate with: source .venv/bin/activate"
    echo ""
fi

# Validate Google Slides module is importable
echo "🔍 Validating Google Slides integration..."
if python3 -c "import sys; sys.path.insert(0, '${SALES_AGENT_LABS_DIR}'); import src.agent.slides_google" 2>/dev/null; then
    echo "✅ Google Slides module verified"
else
    echo "❌ ERROR: Cannot import src.agent.slides_google"
    echo "📍 SALES_AGENT_LABS_DIR: ${SALES_AGENT_LABS_DIR}"
    echo "🔧 PYTHONPATH: ${PYTHONPATH}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Verify sales-agent-labs directory exists: ls -d '${SALES_AGENT_LABS_DIR}'"
    echo "2. Check if src/agent/slides_google.py exists: ls '${SALES_AGENT_LABS_DIR}/src/agent/slides_google.py'"
    echo "3. Ensure virtual environment is activated: source .venv/bin/activate"
    exit 1
fi
echo ""

# Navigate to presgen-assess directory
cd "$SCRIPT_DIR"

echo "📍 Starting from: $(pwd)"
echo ""

# Use python3 -m to ensure module resolution works correctly
# The main.py already has path setup code
if [[ "$1" == "--production" ]]; then
    echo "🏭 Running in production mode (no auto-reload)"
    python3 main8002.py
else
    echo "🔧 Running in development mode (with auto-reload)"
    python3 main8002.py
fi
