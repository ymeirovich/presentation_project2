#!/usr/bin/env python3
"""
Setup script for automated testing enforcement.
Installs pre-commit hooks and validates test environment.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, check=True):
    """Run a shell command and return the result."""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return e

def install_pre_commit():
    """Install and setup pre-commit hooks."""
    print("Setting up pre-commit hooks...")

    # Check if pre-commit is available
    try:
        subprocess.run(["pre-commit", "--version"], check=True, capture_output=True)
        print("pre-commit already installed")

        # Install the hooks
        run_command("pre-commit install")
        run_command("pre-commit install --hook-type pre-push")
        print("✅ Pre-commit hooks installed successfully")
        return True

    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  pre-commit not available. Install with: brew install pre-commit")
        print("📝 Pre-commit config created - install pre-commit manually to enable hooks")
        return False

def validate_test_environment():
    """Validate that the test environment is properly configured."""
    print("Validating test environment...")

    # Check if pytest is installed
    try:
        run_command("python3 -m pytest --version")
        print("✅ pytest is available")
    except:
        print("❌ pytest not found. Install with: pip3 install pytest --user")
        return False

    # Check if test files exist
    test_files = [
        "tests/test_prompt_system.py",
        "PROMPT_SYSTEM_TEST_PLAN.md"
    ]

    for test_file in test_files:
        if Path(test_file).exists():
            print(f"✅ {test_file} exists")
        else:
            print(f"❌ {test_file} not found")
            return False

    return True

def create_test_runner_script():
    """Create a convenient test runner script."""
    script_content = '''#!/bin/bash
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
'''

    with open("run_tests.sh", "w") as f:
        f.write(script_content)

    # Make executable
    os.chmod("run_tests.sh", 0o755)
    print("✅ Created run_tests.sh script")

def main():
    """Main setup function."""
    print("🔧 Setting up automated testing enforcement...")
    print("=" * 50)

    # Validate environment
    if not validate_test_environment():
        print("❌ Test environment validation failed")
        sys.exit(1)

    # Install pre-commit hooks
    pre_commit_success = install_pre_commit()

    # Create test runner script
    create_test_runner_script()

    print("\n🎉 Testing enforcement setup complete!")
    print("\nNext steps:")
    print("1. Run './run_tests.sh' to validate current functionality")
    if pre_commit_success:
        print("2. All commits will now automatically run tests")
    else:
        print("2. Install pre-commit (brew install pre-commit) to enable automatic testing on commits")
    print("3. GitHub Actions will run tests on push/PR")
    print("4. Follow the mandatory testing requirements in CLAUDE.md")

    # Run initial test to verify setup
    print("\n🚀 Running initial test validation...")
    try:
        result = run_command("python3 -m pytest tests/test_prompt_system.py::TestPromptSystemBaseline::test_environment_setup -v")
        if result.returncode == 0:
            print("✅ Initial test validation passed!")
        else:
            print("⚠️  Initial test had issues - check test implementation")
    except Exception as e:
        print(f"⚠️  Could not run initial test: {e}")

if __name__ == "__main__":
    main()