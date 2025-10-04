#!/usr/bin/env python3
"""
Create a clean test workflow for production mode testing.
"""
import asyncio
import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.service.database import AsyncSessionLocal
from src.models.gap_analysis import GapAnalysisResult, RecommendedCourse
from src.models.workflow import WorkflowExecution
from sqlalchemy import select


async def create_test_workflow():
    """Create a clean test workflow with gap analysis data."""

    async with AsyncSessionLocal() as session:
        # Create workflow
        workflow_id = str(uuid4())

        workflow = WorkflowExecution(
            id=workflow_id,
            workflow_type="gap_analysis_to_presentation",
            execution_status="completed",
            current_step="gap_analysis_complete",
            assessment_id="test_production_mode",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(workflow)

        # Create gap analysis result
        gap_analysis = GapAnalysisResult(
            id=str(uuid4()),
            workflow_id=workflow_id,
            overall_score=72.5,
            total_questions=50,
            correct_answers=36,
            incorrect_answers=14,
            skill_gaps='[{"skill_id": "ec2_compute", "skill_name": "EC2 Compute", "severity": 8, "confidence_delta": -3.5}]',
            text_summary="Test gap analysis for production mode testing",
            generated_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(gap_analysis)

        # Create recommended course
        course_id = str(uuid4())
        course = RecommendedCourse(
            id=course_id,
            workflow_id=workflow_id,
            gap_analysis_id=gap_analysis.id,
            skill_id="ec2_compute",
            skill_name="EC2 Compute",
            course_title="AWS EC2 Fundamentals",
            course_description="Understanding EC2 instance types, pricing, and best practices",
            priority=8,
            difficulty_level="intermediate",
            estimated_duration_minutes=180,
            learning_objectives="Master EC2 fundamentals",
            content_outline='{"topics": ["EC2 Instance Types", "Pricing Models", "Security Groups", "Auto Scaling"]}',
            generation_status="pending",
            recommended_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(course)

        await session.commit()

        print(f"✅ Created test workflow")
        print(f"   Workflow ID: {workflow_id}")
        print(f"   Course ID: {course_id}")
        print(f"   Skill: EC2 Compute")
        print(f"\n📝 Test command:")
        print(f'curl -X POST "http://localhost:8000/api/v1/workflows/{workflow_id}/courses/{course_id}/generate-presentation" \\')
        print(f'  -H "Content-Type: application/json" \\')
        print(f'  -d \'{{')
        print(f'    "workflow_id": "{workflow_id}",')
        print(f'    "course_id": "{course_id}",')
        print(f'    "custom_title": "Production Mode Test - EC2 Compute"')
        print(f'  }}\'')

        return workflow_id, course_id


if __name__ == "__main__":
    workflow_id, course_id = asyncio.run(create_test_workflow())
