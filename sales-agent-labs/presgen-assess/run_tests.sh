#!/bin/bash
# Test runner script for prompt system validation

set -e

echo "🧪 Running Prompt System Test Suite..."
echo "======================================="

# Run prompt system baseline tests
echo "1️⃣  Running baseline prompt system tests..."
python3 -m pytest tests/test_prompt_system.py -v

# Run full test suite
echo "2️⃣  Running full test suite..."
python3 -m pytest tests/ -v

# Run linting
echo "3️⃣  Running code linting..."
make lint 2>/dev/null || flake8 src/ --max-line-length=88 --extend-ignore=E203,W503

# Run formatting check
echo "4️⃣  Checking code formatting..."
make fmt 2>/dev/null || black --check src/

echo "✅ All tests and checks completed successfully!"
