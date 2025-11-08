"""Trigger a simple workflow to test the Google Forms API fix."""

import json
import requests

# Test workflow data with simple question (no explanation field)
test_assessment_data = {
    "questions": [
        {
            "question_text": "What does AWS Lambda provide?",
            "question_type": "multiple_choice",
            "options": [
                "Serverless compute",
                "Managed database",
                "Object storage",
                "Content delivery"
            ]
            # NOTE: No 'explanation' field - this was causing HTTP 500
        }
    ],
    "metadata": {
        "certification_name": "Test Certification",
        "total_questions": 1,
        "estimated_duration_minutes": 5
    }
}

# Get API endpoint
api_url = "http://localhost/api/workflows/execute"

print("=" * 80)
print("TRIGGERING TEST WORKFLOW")
print("=" * 80)
print(f"\nAPI URL: {api_url}")
print(f"Question count: {len(test_assessment_data['questions'])}")
print(f"Question has explanation: {'explanation' in test_assessment_data['questions'][0]}")
print("\nSending request...")

try:
    response = requests.post(
        api_url,
        json={
            "certification_profile_id": "00000000-0000-0000-0000-000000000001",
            "user_id": "test-user",
            "assessment_data": test_assessment_data,
            "use_ai_generation": False
        },
        headers={"Content-Type": "application/json"},
        timeout=30
    )

    print(f"\nResponse status: {response.status_code}")
    print(f"Response body:")
    print(json.dumps(response.json(), indent=2))

except Exception as e:
    print(f"\n❌ Error: {e}")
    print(f"\nCheck if the service is running:")
    print(f"  docker logs presgen-assess 2>&1 | tail -50")

print("\n" + "=" * 80)
