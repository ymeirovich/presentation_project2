
#!/bin/bash

# PresGen with MuseTalk Startup Script
# Activates both the main project environment and ensures MuseTalk is available

set -e  # Exit on error

echo "🎬 Starting PresGen with MuseTalk Integration..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if main .venv exists
if [ ! -d ".venv" ]; then
    echo "❌ Main project .venv not found. Please run: python3 -m venv .venv && pip install -r requirements.txt"
    exit 1
fi

# Check if MuseTalk environment exists
if [ ! -d "musetalk_env" ]; then
    echo "❌ MuseTalk environment not found. Please run the MuseTalk installation first."
    exit 1
fi

# Check if MuseTalk directory exists
if [ ! -d "MuseTalk" ]; then
    echo "❌ MuseTalk directory not found. Please run the MuseTalk installation first."
    exit 1
fi

echo "✅ Main project environment: .venv"
echo "✅ MuseTalk environment: musetalk_env"
echo "✅ MuseTalk installation: MuseTalk/"

# Activate main environment
echo "🔄 Activating main project environment..."
source .venv/bin/activate

# Verify MuseTalk wrapper is executable
if [ ! -x "musetalk_wrapper.py" ]; then
    chmod +x musetalk_wrapper.py
    echo "✅ Made MuseTalk wrapper executable"
fi

# Test MuseTalk environment
echo "🔄 Testing MuseTalk environment..."
if musetalk_env/bin/python -c "import torch; print(f'PyTorch version: {torch.__version__}')"; then
    echo "✅ MuseTalk environment is working"
else
    echo "❌ MuseTalk environment test failed"
    exit 1
fi

# Check if presgen-training module is available
if python -c "from src.presgen_training.avatar_generator import AvatarGenerator; print('✅ Avatar generator ready')"; then
    echo "✅ PresGen training module loaded successfully"
else
    echo "❌ Failed to load PresGen training module"
    exit 1
fi

echo ""
echo "🎉 PresGen with MuseTalk is ready!"
echo ""
echo "Available commands:"
echo "  • Start video server: ./start_video_server.sh"
echo "  • Run orchestrator: make run-orchestrator"
echo "  • Test video processing: python3 -m src.mcp.tools.video_orchestrator"
echo "  • Direct avatar generation test: python3 -c \"from src.presgen_training.avatar_generator import AvatarGenerator; ag = AvatarGenerator(); print(ag.get_status())\""
echo ""
echo "Environment Details:"
echo "  • Main Python: $(which python)"
echo "  • MuseTalk Python: $(pwd)/musetalk_env/bin/python"
echo "  • Project Directory: $(pwd)"
echo ""

# Start an interactive shell with the environment active
echo "Starting shell with PresGen + MuseTalk environment..."
echo "Type 'exit' to quit."
echo ""

# Use the current shell or fallback to bash
exec "${SHELL:-/bin/bash}"