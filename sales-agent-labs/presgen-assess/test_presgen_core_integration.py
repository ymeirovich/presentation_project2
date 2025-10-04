"""
Test PresGen-Core production integration.

This script tests the real HTTP call to PresGen-Core API.
"""
import asyncio
import sys
from pathlib import Path

# Add both presgen-assess and sales-agent-labs to path
presgen_assess_dir = Path(__file__).parent
sales_agent_labs_dir = presgen_assess_dir.parent
sys.path.insert(0, str(presgen_assess_dir))
sys.path.insert(0, str(sales_agent_labs_dir))

from datetime import datetime
from uuid import uuid4
from src.service.presgen_core_client import PresGenCoreClient
from src.schemas.presentation import PresentationContentSpec


async def test_presgen_core():
    """Test production PresGen-Core integration."""

    print("🧪 Testing PresGen-Core Production Integration")
    print("=" * 60)

    # Create test content spec
    content_spec = PresentationContentSpec(
        workflow_id=uuid4(),
        skill_id="test_security",
        skill_name="Security Best Practices",
        title="AWS Security - Best Practices",
        subtitle="Gap Analysis Presentation",
        skill_gap={
            "skill_id": "test_security",
            "skill_name": "Security Best Practices",
            "severity": 8,
            "confidence_delta": -3.5
        },
        content_outline={
            "skill_id": "test_security",
            "content_items": [
                {"topic": "IAM Policies", "source": "AWS Docs", "page": 42},
                {"topic": "MFA Setup", "source": "AWS Docs", "page": 45},
                {"topic": "Security Groups", "source": "AWS Docs", "page": 50}
            ]
        },
        exam_name="AWS Solutions Architect Associate",
        assessment_title="AWS Security Assessment",
        assessment_date=datetime.utcnow(),
        overall_score=75.5
    )

    # Create client
    client = PresGenCoreClient()

    print(f"\n📋 Test Spec:")
    print(f"  - Skill: {content_spec.skill_name}")
    print(f"  - Title: {content_spec.title}")
    print(f"  - Severity: {content_spec.skill_gap['severity']}")
    print(f"  - Content Items: {len(content_spec.content_outline['content_items'])}")

    # Progress callback
    def progress_update(progress: int, step: str):
        print(f"  ⏳ [{progress:3d}%] {step}")

    try:
        print(f"\n🚀 Generating presentation...")
        result = await client.generate_presentation(
            content_spec,
            progress_callback=progress_update
        )

        print(f"\n✅ SUCCESS!")
        print(f"  - URL: {result.presentation_url}")
        print(f"  - Slides: {result.slide_count}")
        print(f"  - Duration: {result.generation_duration_ms}ms")
        print(f"  - File Size: {len(result.file_data)} bytes")

        return True

    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_presgen_core())
    sys.exit(0 if success else 1)
