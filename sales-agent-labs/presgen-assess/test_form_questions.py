#!/usr/bin/env python3
"""Test script to fetch questions from Google Form."""

import asyncio
import json
import sys
sys.path.insert(0, '/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess')

from src.services.google_forms_service import GoogleFormsService

async def main():
    form_id = "1oIdDbfZR8RHP2P-ht2ej7KMY_XJgFZCMJ0QSb7UVnng"

    print(f"Fetching form structure: {form_id}")

    service = GoogleFormsService()

    # Fetch form structure
    form_data = await service.get_form(form_id=form_id)

    print("\n" + "="*80)
    print("FORM STRUCTURE:")
    print("="*80)
    print(json.dumps(form_data, indent=2, default=str)[:3000])

if __name__ == "__main__":
    asyncio.run(main())
