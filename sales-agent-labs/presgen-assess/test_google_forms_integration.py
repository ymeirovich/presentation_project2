"""End-to-end test for Google Forms integration with real question data.

This test validates:
1. Service account authentication works
2. Form creation succeeds
3. Questions with NO explanations can be added (the bug fix)
4. Questions WITH explanations can be added
5. Form can be cleaned up
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.services.assessment_forms_mapper import AssessmentFormsMapper


def test_forms_integration_with_real_questions():
    """Test Google Forms API with realistic assessment questions."""

    print("=" * 80)
    print("GOOGLE FORMS INTEGRATION TEST - REAL QUESTIONS")
    print("=" * 80)

    # Step 1: Setup credentials
    print("\n[1/6] Setting up service account credentials...")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    impersonate_user = os.getenv("GOOGLE_SERVICE_ACCOUNT_IMPERSONATE_USER")

    scopes = [
        "https://www.googleapis.com/auth/forms.body",
        "https://www.googleapis.com/auth/drive",
    ]

    credentials = service_account.Credentials.from_service_account_file(
        creds_path, scopes=scopes
    )

    if impersonate_user:
        credentials = credentials.with_subject(impersonate_user)

    forms_service = build("forms", "v1", credentials=credentials, cache_discovery=False)
    drive_service = build("drive", "v3", credentials=credentials, cache_discovery=False)

    print(f"  ✓ Credentials loaded and services built")

    # Step 2: Create test questions (mimicking real workflow data)
    print("\n[2/6] Preparing test questions...")

    # Question WITHOUT explanation (this was causing HTTP 500)
    questions_without_explanation = [
        {
            "question_text": "What is AWS Lambda?",
            "question_type": "multiple_choice",
            "options": ["Serverless compute service", "Database service", "Storage service", "Network service"],
        }
    ]

    # Question WITH explanation
    questions_with_explanation = [
        {
            "question_text": "Which AWS service provides object storage?",
            "question_type": "multiple_choice",
            "options": ["S3", "EBS", "EFS", "Glacier"],
            "explanation": "Amazon S3 is the primary object storage service in AWS"
        }
    ]

    print(f"  ✓ Created 2 test questions (1 without explanation, 1 with)")

    # Step 3: Map questions using the mapper
    print("\n[3/6] Mapping questions to Google Forms format...")
    mapper = AssessmentFormsMapper()

    requests_no_explanation = mapper.build_batch_update_requests(
        questions_without_explanation, start_index=0
    )
    requests_with_explanation = mapper.build_batch_update_requests(
        questions_with_explanation, start_index=1
    )

    # Verify no null descriptions in the requests
    for req in requests_no_explanation + requests_with_explanation:
        item = req.get("createItem", {}).get("item", {})
        if "description" in item and item["description"] is None:
            print(f"  ❌ ERROR: Found null description in request!")
            return False

    print(f"  ✓ Questions mapped successfully (no null descriptions)")

    # Step 4: Create form
    print("\n[4/6] Creating Google Form...")
    form_id = None
    form_url = None

    try:
        form_body = {
            "info": {
                "title": "🧪 Integration Test - Question Null Description Fix",
            }
        }

        result = forms_service.forms().create(body=form_body).execute()
        form_id = result.get("formId")
        form_url = result.get("responderUri")

        print(f"  ✓ Form created: {form_id}")
        print(f"  ✓ Form URL: {form_url}")

    except HttpError as e:
        print(f"  ❌ ERROR creating form: HTTP {e.resp.status}")
        print(f"  ❌ Details: {e.error_details}")
        return False

    # Step 5: Add questions to form (THE CRITICAL TEST)
    print("\n[5/6] Adding questions to form...")

    try:
        # Add question WITHOUT explanation
        print(f"  → Adding question without explanation...")
        batch_update_body = {"requests": requests_no_explanation}
        forms_service.forms().batchUpdate(
            formId=form_id,
            body=batch_update_body
        ).execute()
        print(f"  ✓ Question without explanation added successfully")

        # Add question WITH explanation
        print(f"  → Adding question with explanation...")
        batch_update_body = {"requests": requests_with_explanation}
        forms_service.forms().batchUpdate(
            formId=form_id,
            body=batch_update_body
        ).execute()
        print(f"  ✓ Question with explanation added successfully")

    except HttpError as e:
        print(f"  ❌ ERROR adding questions: HTTP {e.resp.status}")
        print(f"  ❌ Details: {e.error_details}")
        print(f"  ❌ This is the bug we were trying to fix!")
        return False

    # Step 6: Clean up
    print("\n[6/6] Cleaning up test form...")
    if form_id:
        try:
            drive_service.files().delete(fileId=form_id).execute()
            print(f"  ✓ Test form deleted successfully")
        except Exception as e:
            print(f"  ⚠️  Could not delete test form: {e}")
            print(f"  ⚠️  Manual cleanup needed: {form_url}")

    # Success!
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("✅ Google Forms API can now handle questions WITHOUT explanations")
    print("✅ The HTTP 500 'Internal error' bug is FIXED")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = test_forms_integration_with_real_questions()
    sys.exit(0 if success else 1)
