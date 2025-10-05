#!/usr/bin/env python3
"""Test script to fetch and inspect Google Form responses."""

import asyncio
import json
import sys
sys.path.insert(0, '/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess')

from src.services.google_forms_service import GoogleFormsService

async def main():
    form_id = "1oIdDbfZR8RHP2P-ht2ej7KMY_XJgFZCMJ0QSb7UVnng"

    print(f"Fetching responses from form: {form_id}")

    service = GoogleFormsService()
    result = await service.get_form_responses(form_id=form_id)

    print("\n" + "="*80)
    print("RAW RESPONSE DATA:")
    print("="*80)
    print(json.dumps(result, indent=2, default=str))

    responses = result.get('responses', [])
    print(f"\n\nTotal responses: {len(responses)}")

    if responses:
        print("\n" + "="*80)
        print("FIRST RESPONSE DETAILS:")
        print("="*80)
        first_response = responses[0]
        print(json.dumps(first_response, indent=2, default=str))

        print("\n" + "="*80)
        print("ANSWERS BREAKDOWN:")
        print("="*80)
        answers = first_response.get('answers', {})
        for question_id, answer_data in answers.items():
            print(f"\nQuestion ID: {question_id}")
            print(f"Answer Data: {json.dumps(answer_data, indent=2, default=str)}")

if __name__ == "__main__":
    asyncio.run(main())
