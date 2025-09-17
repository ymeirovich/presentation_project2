#!/usr/bin/env python3
"""
Test OpenAI TTS setup with comprehensive error handling for API issues.
Handles permission scope, rate limits, invalid keys, and other API errors.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the presgen-training2 src directory to Python path
sys.path.insert(0, "presgen-training2/src")

def test_openai_api():
    """Test OpenAI API access with comprehensive error handling"""

    print("🔑 Testing OpenAI API Access")
    print("-" * 40)

    # Check if API key exists
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return False

    print(f"✅ API key found (length: {len(api_key)})")

    try:
        import openai
        print("✅ OpenAI library imported successfully")
    except ImportError as e:
        print(f"❌ OpenAI library not installed: {e}")
        print("💡 Run: pip3 install openai")
        return False

    # Initialize client with error handling
    try:
        client = openai.OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize OpenAI client: {e}")
        return False

    # Test basic API access with models endpoint (lowest cost)
    print("\n🧪 Testing API permissions...")
    try:
        models = client.models.list()
        model_names = [model.id for model in models.data if 'tts' in model.id.lower()]
        if model_names:
            print(f"✅ TTS models available: {model_names}")
        else:
            print("⚠️  No TTS-specific models found, checking general access...")

        # Check if we have basic access
        if models.data:
            print(f"✅ API access confirmed ({len(models.data)} models available)")
        else:
            print("❌ No models accessible - check API key permissions")
            return False

    except openai.AuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print("💡 Check your API key is valid and active")
        return False
    except openai.PermissionDeniedError as e:
        print(f"❌ Permission denied: {e}")
        print("💡 Your API key may not have TTS permissions")
        return False
    except openai.RateLimitError as e:
        print(f"⚠️  Rate limit exceeded: {e}")
        print("💡 Wait a moment and try again")
        return False
    except openai.APIError as e:
        print(f"❌ API error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

    # Test TTS functionality with minimal request
    print("\n🎤 Testing TTS functionality...")
    try:
        # Test with shortest possible text to minimize cost
        response = client.audio.speech.create(
            model="tts-1",  # Use cheaper model
            voice="alloy",  # Default voice
            input="Test"    # Minimal text (4 chars = ~$0.00006)
        )

        # Save to temporary file
        test_output = "temp/openai_tts_test.mp3"
        Path("temp").mkdir(exist_ok=True)

        with open(test_output, "wb") as f:
            f.write(response.content)

        file_size = Path(test_output).stat().st_size
        print(f"✅ TTS test successful!")
        print(f"📁 Generated: {test_output} ({file_size} bytes)")
        return True

    except openai.AuthenticationError as e:
        print(f"❌ TTS Authentication failed: {e}")
        return False
    except openai.PermissionDeniedError as e:
        print(f"❌ TTS Permission denied: {e}")
        print("💡 Your OpenAI plan may not include TTS access")
        return False
    except openai.RateLimitError as e:
        print(f"⚠️  TTS Rate limit: {e}")
        return False
    except openai.BadRequestError as e:
        print(f"❌ TTS Bad request: {e}")
        return False
    except Exception as e:
        print(f"❌ TTS Unexpected error: {e}")
        return False

def test_voice_manager_openai():
    """Test VoiceManager OpenAI integration"""

    print("\n🔧 Testing VoiceManager OpenAI Integration")
    print("-" * 50)

    try:
        from modes.orchestrator import ModeOrchestrator

        orchestrator = ModeOrchestrator()
        print("✅ ModeOrchestrator initialized")

        # Check TTS engines availability
        engines = orchestrator.voice_manager.tts_engines
        openai_available = engines.get('openai', {}).get('available', False)

        print(f"📊 TTS Engine Status:")
        for name, config in engines.items():
            status = "✅" if config['available'] else "❌"
            print(f"  {status} {name}: priority {config['priority']}")

        if openai_available:
            print("✅ OpenAI TTS engine is available!")
            return True
        else:
            print("❌ OpenAI TTS engine not available")
            return False

    except Exception as e:
        print(f"❌ VoiceManager test failed: {e}")
        return False

def main():
    """Main test function"""

    print("🤖 OpenAI TTS Setup Test with Error Handling")
    print("=" * 60)

    # Test 1: OpenAI API access
    api_success = test_openai_api()

    # Test 2: VoiceManager integration
    if api_success:
        vm_success = test_voice_manager_openai()
    else:
        print("\n⏭️  Skipping VoiceManager test due to API issues")
        vm_success = False

    # Summary
    print("\n📋 Test Summary")
    print("-" * 20)
    print(f"OpenAI API: {'✅ PASS' if api_success else '❌ FAIL'}")
    print(f"VoiceManager: {'✅ PASS' if vm_success else '❌ FAIL'}")

    if api_success and vm_success:
        print("\n🎉 OpenAI TTS is ready for use!")
        print("💡 Next: Test voice profile creation with your .wav file")
    else:
        print("\n🔧 Issues detected. Check the errors above.")

    return api_success and vm_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)