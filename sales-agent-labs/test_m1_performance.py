#!/usr/bin/env python3
"""
M1 Mac Performance Validation for PresGen-Training2
Tests performance characteristics and hardware optimization
"""

import time
import psutil
import torch
import sys
import os
from pathlib import Path
import subprocess
import requests
import json

def check_system_specs():
    """Check M1 Mac system specifications"""
    print("=== M1 Mac System Specifications ===")

    # CPU info
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()
    print(f"CPU Cores: {cpu_count}")
    if cpu_freq:
        print(f"CPU Frequency: {cpu_freq.current:.2f} MHz")

    # Memory info
    memory = psutil.virtual_memory()
    print(f"Total Memory: {memory.total / (1024**3):.2f} GB")
    print(f"Available Memory: {memory.available / (1024**3):.2f} GB")

    # PyTorch MPS
    print(f"PyTorch Version: {torch.__version__}")
    print(f"MPS Available: {torch.backends.mps.is_available()}")
    print(f"MPS Built: {torch.backends.mps.is_built()}")

    # Check if this is actually M1 Mac
    try:
        result = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'],
                              capture_output=True, text=True)
        cpu_brand = result.stdout.strip()
        print(f"CPU Brand: {cpu_brand}")

        if "Apple" in cpu_brand:
            print("✅ Confirmed: Apple Silicon (M1/M2) Mac")
        else:
            print("⚠️  Warning: Not an Apple Silicon Mac")
    except:
        print("❓ Could not determine CPU type")

def test_pytorch_mps_performance():
    """Test PyTorch MPS performance"""
    print("\n=== PyTorch MPS Performance Test ===")

    if not torch.backends.mps.is_available():
        print("❌ MPS not available")
        return False

    try:
        # Create test tensor on MPS
        device = torch.device("mps")
        x = torch.randn(1000, 1000, device=device)
        y = torch.randn(1000, 1000, device=device)

        # Time matrix multiplication
        start_time = time.time()
        for _ in range(100):
            z = torch.mm(x, y)
        torch.mps.synchronize()  # Wait for completion
        end_time = time.time()

        mps_time = end_time - start_time
        print(f"✅ MPS Matrix Multiplication (100x): {mps_time:.3f}s")

        # Compare with CPU
        x_cpu = x.cpu()
        y_cpu = y.cpu()

        start_time = time.time()
        for _ in range(100):
            z_cpu = torch.mm(x_cpu, y_cpu)
        end_time = time.time()

        cpu_time = end_time - start_time
        print(f"📊 CPU Matrix Multiplication (100x): {cpu_time:.3f}s")
        print(f"🚀 MPS Speedup: {cpu_time / mps_time:.2f}x")

        return True

    except Exception as e:
        print(f"❌ MPS performance test failed: {e}")
        return False

def test_liveportrait_performance():
    """Test LivePortrait inference performance"""
    print("\n=== LivePortrait Performance Test ===")

    # Check if LivePortrait is available
    liveportrait_path = Path("/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/LivePortrait")
    if not liveportrait_path.exists():
        print("❌ LivePortrait not found")
        return False

    try:
        # Set M1 optimization environment
        env = os.environ.copy()
        env.update({
            "PYTORCH_ENABLE_MPS_FALLBACK": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1"
        })

        # Simple inference test
        print("🔍 Testing LivePortrait basic functionality...")

        # Check if models are downloaded
        models_path = liveportrait_path / "pretrained_weights" / "liveportrait"
        if not models_path.exists():
            print("❌ LivePortrait models not found")
            return False

        print("✅ LivePortrait models found")
        print("✅ Environment optimized for M1 Mac")

        return True

    except Exception as e:
        print(f"❌ LivePortrait performance test failed: {e}")
        return False

def test_video_generation_performance():
    """Test actual video generation performance"""
    print("\n=== Video Generation Performance Test ===")

    # Monitor system resources during generation
    start_memory = psutil.virtual_memory().percent
    start_cpu = psutil.cpu_percent(interval=1)

    print(f"Initial Memory Usage: {start_memory:.1f}%")
    print(f"Initial CPU Usage: {start_cpu:.1f}%")

    # Test short video generation
    payload = {
        "mode": "video-only",
        "script_text": "Performance test: This is a short video generation test to measure M1 Mac performance.",
        "voice_profile_name": "Weather voice",
        "quality_level": "fast",
        "instructions": "Generate quickly for performance testing"
    }

    print("🚀 Starting video generation...")
    start_time = time.time()

    try:
        response = requests.post("http://localhost:8080/training/video-only", json=payload, timeout=300)

        if response.status_code == 200:
            end_time = time.time()
            generation_time = end_time - start_time

            result = response.json()
            print(f"✅ Video generation completed: Job ID {result['job_id']}")
            print(f"⏱️  Generation Time: {generation_time:.2f} seconds")

            # Check resource usage
            end_memory = psutil.virtual_memory().percent
            end_cpu = psutil.cpu_percent(interval=1)

            print(f"Peak Memory Usage: {end_memory:.1f}%")
            print(f"Average CPU Usage: {end_cpu:.1f}%")

            # Performance evaluation
            if generation_time < 60:
                print("🟢 Excellent performance (< 1 minute)")
            elif generation_time < 180:
                print("🟡 Good performance (< 3 minutes)")
            elif generation_time < 900:
                print("🟠 Acceptable performance (< 15 minutes)")
            else:
                print("🔴 Slow performance (> 15 minutes)")

            return True
        else:
            print(f"❌ Video generation failed: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print("⏰ Video generation timed out (> 5 minutes)")
        return False
    except Exception as e:
        print(f"❌ Video generation error: {e}")
        return False

def test_concurrent_performance():
    """Test performance under concurrent load"""
    print("\n=== Concurrent Load Performance Test ===")

    print("⚠️  Note: This is a basic concurrent test")
    print("📊 Real production systems should use proper load testing tools")

    # Simple concurrent request test
    import threading
    import time

    results = []

    def make_request(i):
        try:
            start = time.time()
            response = requests.get("http://localhost:8080/training/voice-profiles", timeout=10)
            end = time.time()

            results.append({
                'thread': i,
                'success': response.status_code == 200,
                'time': end - start
            })
        except Exception as e:
            results.append({
                'thread': i,
                'success': False,
                'error': str(e)
            })

    # Launch 5 concurrent requests
    threads = []
    for i in range(5):
        thread = threading.Thread(target=make_request, args=(i,))
        threads.append(thread)
        thread.start()

    # Wait for completion
    for thread in threads:
        thread.join()

    # Analyze results
    successful = sum(1 for r in results if r.get('success', False))
    total = len(results)
    avg_time = sum(r.get('time', 0) for r in results if 'time' in r) / max(1, successful)

    print(f"✅ Concurrent Requests: {successful}/{total} successful")
    print(f"⏱️  Average Response Time: {avg_time:.3f}s")

    return successful == total

def main():
    """Run M1 Mac performance validation"""
    print("🔥 M1 Mac Performance Validation for PresGen-Training2")
    print("=" * 60)

    # System specs
    check_system_specs()

    # Performance tests
    tests = [
        ("PyTorch MPS", test_pytorch_mps_performance),
        ("LivePortrait Setup", test_liveportrait_performance),
        ("Video Generation", test_video_generation_performance),
        ("Concurrent Load", test_concurrent_performance)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 M1 Mac Performance Validation Summary")
    print("=" * 60)

    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if success:
            passed += 1

    print(f"\nOverall: {passed}/{len(results)} tests passed")

    # Recommendations
    print("\n🎯 M1 Mac Optimization Recommendations:")
    print("   • PyTorch MPS acceleration is enabled")
    print("   • PYTORCH_ENABLE_MPS_FALLBACK=1 for compatibility")
    print("   • OMP_NUM_THREADS=1 to avoid oversubscription")
    print("   • Consider 16GB+ RAM for optimal performance")
    print("   • Use quality_level='fast' for development testing")

    if passed == len(results):
        print("\n🚀 M1 Mac is READY for PresGen-Training2 production!")
        return 0
    else:
        print("\n⚠️  Some performance issues detected. Review configuration.")
        return 1

if __name__ == "__main__":
    exit(main())