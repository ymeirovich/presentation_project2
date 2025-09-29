#!/usr/bin/env python3
"""Test script to verify workflow generates real AI questions instead of mock questions."""

import asyncio
import json
import aiohttp

async def test_workflow_real_questions():
    """Test creating a workflow and verifying it uses real AI questions."""

    print("🧪 Testing Workflow with Real AI Question Generation")
    print("=" * 60)

    # Test workflow creation with real AI questions
    workflow_data = {
        "user_id": "test-real-questions",
        "certification_profile_id": "455dae60-065c-4038-b3df-6d769b955dbb",
        "workflow_type": "assessment_generation",
        "parameters": {
            "title": "Real AI Questions Test",
            "summary_markdown": "Testing real AI question generation from knowledge base",
            "difficulty_level": "intermediate",
            "question_count": 8,  # Small count for quick testing
            "passing_score": 70,
            "time_limit_minutes": 30,
            "slide_count": 4,
            "domain_distribution": {
                "Data Engineering": 2,
                "Exploratory Data Analysis": 2,
                "Modeling": 2,
                "Machine Learning Implementation and Operations": 2
            },
            "include_avatar": False,
            "notes_markdown": ""
        }
    }

    try:
        async with aiohttp.ClientSession() as session:
            # Create workflow
            print("🚀 Creating workflow with real AI question generation...")
            async with session.post(
                "http://localhost:8081/api/v1/workflows/",
                json=workflow_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    workflow_result = await response.json()
                    workflow_id = workflow_result.get('id')
                    print(f"✅ Workflow created successfully | id={workflow_id}")

                    # Wait a bit for orchestration to complete
                    print("⏳ Waiting for orchestration to complete...")
                    await asyncio.sleep(35)  # AI question generation takes ~25-30 seconds

                    # Get workflow details to check the results
                    print("🔍 Checking workflow results...")
                    async with session.get(f"http://localhost:8081/api/v1/workflows/{workflow_id}") as details_response:
                        if details_response.status == 200:
                            workflow_details = await details_response.json()
                            print(f"📊 Workflow status: {workflow_details.get('status')}")
                            print(f"📋 Current step: {workflow_details.get('current_step')}")

                            # Check if Google Form was created
                            form_url = workflow_details.get('generated_content_urls', {}).get('form_url')
                            if form_url:
                                print(f"✅ Google Form created: {form_url}")
                                print("🎯 Test completed! Check the Google Form to verify it contains real AI questions instead of mock questions.")
                            else:
                                print("❌ No Google Form URL found in workflow results")
                        else:
                            print(f"❌ Failed to get workflow details: {details_response.status}")
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to create workflow: {response.status} - {error_text}")

    except Exception as e:
        print(f"💥 Error during workflow test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_workflow_real_questions())