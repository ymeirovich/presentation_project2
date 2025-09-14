#!/usr/bin/env python3
"""
Test script for the complete PresGen presentation API
Tests the /presentation/generate endpoint with full integration
"""

import requests
import json
import time

def test_presentation_api():
    """Test the presentation generation API endpoint"""
    
    print("🎬 Testing Complete Presentation API Integration")
    print("=" * 60)
    
    # API endpoint (assuming server runs on port 8080)
    url = "http://localhost:8080/presentation/generate"
    
    # Test script
    test_script = """
    Welcome to our quarterly business review. I'm excited to share our company's 
    significant achievements and growth milestones with you today.
    
    Our innovative technology solutions have revolutionized how businesses operate 
    in the digital age. We have successfully expanded our market presence across 
    three new regions this quarter.
    
    The financial results demonstrate remarkable progress with 40% revenue growth 
    year-over-year. Our customer satisfaction scores have reached an all-time high 
    of 95% positive feedback.
    
    Looking ahead, we are well-positioned for continued success with our strategic 
    roadmap and talented team. Thank you for your continued support and partnership.
    """
    
    # Request payload
    payload = {
        "script": test_script.strip(),
        "options": {
            "avatar_quality": "standard",
            "bullet_style": "professional"
        }
    }
    
    print(f"📝 Script length: {len(test_script)} characters")
    print(f"🚀 Sending request to: {url}")
    
    try:
        # Make API request
        start_time = time.time()
        
        response = requests.post(
            url, 
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60  # 60 second timeout
        )
        
        request_time = time.time() - start_time
        
        print(f"⏱️ API request completed in {request_time:.1f}s")
        print(f"📡 HTTP Status: {response.status_code}")
        
        # Parse response
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n📊 Results:")
            print(f"✅ Success: {result['success']}")
            print(f"🆔 Job ID: {result['job_id']}")
            print(f"⏱️ Total Processing Time: {result['total_processing_time']:.1f}s")
            print(f"📈 Phase Times:")
            
            for phase, time_taken in result['phase_times'].items():
                print(f"   • {phase}: {time_taken:.1f}s")
            
            if result['success'] and result['output_path']:
                print(f"📁 Output File: {result['output_path']}")
                print(f"\n🎉 Presentation generation completed successfully!")
            else:
                print(f"❌ Error: {result.get('error', 'Unknown error')}")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Is the FastAPI server running?")
        print("💡 Start server with: uvicorn src.service.http:app --port 8080 --reload")
    except requests.exceptions.Timeout:
        print("⏱️ Request timeout: Presentation generation took longer than 60s")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

def test_server_status():
    """Test if the server is running"""
    try:
        response = requests.get("http://localhost:8080/healthz", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
            return True
        else:
            print(f"⚠️ Server responded with status {response.status_code}")
            return False
    except:
        print("❌ Server is not running")
        return False

if __name__ == "__main__":
    print("🎬 PresGen Complete Integration Test")
    print("===================================")
    
    # Check server status first
    print("1. Checking server status...")
    if test_server_status():
        print("\n2. Testing presentation generation...")
        test_presentation_api()
    else:
        print("\n💡 To start the server, run:")
        print("   uvicorn src.service.http:app --port 8080 --reload")