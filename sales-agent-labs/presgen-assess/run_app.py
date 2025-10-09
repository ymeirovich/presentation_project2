#!/usr/bin/env python3
"""
Startup wrapper for PresGen-Assess that ensures correct module resolution.

This wrapper sets up sys.path to ensure:
1. sales-agent-labs is available for src.agent.slides_google imports
2. presgen-assess modules can still import their own src packages
"""

import sys
from pathlib import Path

# Get absolute paths
presgen_assess_dir = Path(__file__).parent.resolve()
sales_agent_labs_dir = presgen_assess_dir.parent

# CRITICAL: Add sales-agent-labs FIRST to ensure src.agent is found
# Then add presgen-assess for local src modules
if str(sales_agent_labs_dir) not in sys.path:
    sys.path.insert(0, str(sales_agent_labs_dir))

# Add presgen-assess/src to path for local module imports
presgen_src = presgen_assess_dir / "src"
if str(presgen_src) not in sys.path:
    sys.path.insert(0, str(presgen_src))

print(f"🔧 Python path configured:")
print(f"   1. {sales_agent_labs_dir} (for src.agent.slides_google)")
print(f"   2. {presgen_src} (for local modules)")
print()

# Verify Google Slides module is importable
try:
    import src.agent.slides_google
    print("✅ Google Slides integration verified")
except ImportError as e:
    print(f"❌ ERROR: Cannot import src.agent.slides_google: {e}")
    print(f"\nCurrent sys.path:")
    for i, p in enumerate(sys.path[:10]):
        print(f"   {i}: {p}")
    sys.exit(1)

# Now import and run the app
from service.app import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "run_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(presgen_assess_dir)],
    )
