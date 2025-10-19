#!/usr/bin/env python3
"""
Test the file management endpoint directly
"""

import requests
import json

# Test the endpoint
profile_id = '455dae60-065c-4038-b3df-6d769b955dbb'
url = f'http://localhost:8000/api/v1/presgen-assess/files/profile/{profile_id}'

print(f"Testing endpoint: {url}\n")

try:
    response = requests.get(url, timeout=5)

    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}\n")

    try:
        data = response.json()
        print(f"Response JSON:")
        print(json.dumps(data, indent=2))
    except:
        print(f"Response Text:")
        print(response.text)

except requests.exceptions.ConnectionError:
    print("❌ Connection failed - is the backend server running on port 8000?")
except requests.exceptions.Timeout:
    print("❌ Request timed out")
except Exception as e:
    print(f"❌ Error: {e}")
