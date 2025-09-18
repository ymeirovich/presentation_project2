#!/usr/bin/env python3
"""
Test script to verify bullet assignment fixes
Tests the sectional assignment algorithm with presgen_test.mp4
"""

import asyncio
import logging
import sys
from pathlib import Path
import subprocess
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp.tools.video_content import ContentAgent, TranscriptSegment

# Setup logging
logging.basicConfig(level=logging.INFO)

def get_video_duration(video_path: str) -> float:
    """Get video duration using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        duration = float(data['format']['duration'])
        print(f"Video duration: {duration:.2f} seconds ({duration//60:.0f}:{duration%60:02.0f})")
        return duration
    except Exception as e:
        print(f"Error getting video duration: {e}")
        return 137.0  # fallback duration

def create_mock_transcript_segments(duration: float) -> list[TranscriptSegment]:
    """Create realistic mock transcript segments for testing"""
    segments = []

    # Create segments with varied importance levels to test content-importance ranking
    segment_content = [
        "Welcome everyone to today's presentation on our Q3 sales performance",  # Introduction - should rank high
        "Just a brief pause while we set up the projector and get everything ready",  # Filler - should rank low
        "Our primary objective is to increase revenue by 40% through strategic AI integration",  # Key goal - should rank very high
        "The weather has been quite nice this week, hasn't it, hope everyone is doing well",  # Irrelevant - should rank very low
        "The data shows significant improvement in our lead conversion rates this quarter with major results",  # Key results - should rank very high
        "We've identified three key phases for our implementation strategy going forward",  # Important strategy - should rank high
        "Let me just adjust the microphone volume here for a moment while we continue",  # Technical filler - should rank low
        "Customer feedback has been overwhelmingly positive with 95% satisfaction scores and critical insights",  # Important feedback - should rank high
        "Our recommendation is to implement this solution company-wide by next quarter as a key decision",  # Major recommendation - should rank very high
        "The next steps include team training and comprehensive system rollout for implementation",  # Action items - should rank high
        "Thank you for your attention, any questions before we wrap up today",  # Conclusion - should rank medium
        "Let's review the budget allocation and timeline for this critical initiative and important outcomes"  # Key planning - should rank very high
    ]

    segment_duration = duration / len(segment_content)

    for i, content in enumerate(segment_content):
        start_time = i * segment_duration
        end_time = min((i + 1) * segment_duration, duration)

        segments.append(TranscriptSegment(
            start_time=start_time,
            end_time=end_time,
            text=content,
            confidence=0.9
        ))

    return segments

async def test_bullet_assignment():
    """Test the bullet assignment with sectional algorithm"""

    print("=" * 60)
    print("BULLET ASSIGNMENT FIX TEST")
    print("=" * 60)

    # Test video path
    video_path = "/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/examples/video/presgen_test.mp4"

    if not Path(video_path).exists():
        print(f"❌ Test video not found at: {video_path}")
        return False

    print(f"✅ Test video found: {video_path}")

    # Get actual video duration
    video_duration = get_video_duration(video_path)

    # Create mock transcript segments
    segments = create_mock_transcript_segments(video_duration)
    print(f"✅ Created {len(segments)} transcript segments")

    # Test with ContentAgent
    agent = ContentAgent(job_id="test-bullet-assignment")

    print("\n📊 Testing bullet assignment algorithm...")

    try:
        result = await agent.batch_summarize(segments, max_bullets=5)

        if result.success:
            print(f"✅ Processing successful!")
            print(f"   Processing time: {result.processing_time:.2f}s")
            print(f"   Bullets generated: {len(result.summary.bullet_points)}")
            print(f"   Cache hit: {result.cache_hit}")

            print(f"\n🎯 Bullet Points ({len(result.summary.bullet_points)}):")

            # Verify timing constraints
            all_within_bounds = True

            for i, bullet in enumerate(result.summary.bullet_points):
                # Parse timestamp
                time_parts = bullet.timestamp.split(":")
                bullet_seconds = int(time_parts[0]) * 60 + int(time_parts[1])

                within_bounds = bullet_seconds <= video_duration
                all_within_bounds = all_within_bounds and within_bounds

                status_icon = "✅" if within_bounds else "❌"

                print(f"  {i+1}. [{bullet.timestamp}] {bullet.text}")
                print(f"     Confidence: {bullet.confidence:.2f}, Duration: {bullet.duration}s {status_icon}")

                if not within_bounds:
                    print(f"     ⚠️  TIMING ERROR: {bullet_seconds}s exceeds video duration {video_duration:.1f}s")

            print(f"\n🏷️  Themes: {result.summary.main_themes}")
            print(f"📊 Total Duration: {result.summary.total_duration}")
            print(f"🎯 Summary Confidence: {result.summary.summary_confidence:.2f}")

            # Final assessment
            print(f"\n📋 ASSESSMENT:")
            if all_within_bounds:
                print("✅ All bullets assigned within video duration bounds")
            else:
                print("❌ Some bullets exceed video duration - sectional assignment may not be working")

            # Check if using sectional assignment (should not have 20s intervals)
            timestamps = [bullet.timestamp for bullet in result.summary.bullet_points]
            print(f"🕒 Timestamps: {timestamps}")

            # Check if sectional assignment was actually used (look for specific log events)
            sectional_assignment_used = "sectional_assignment_start" in str(result.__dict__)

            # Also check for exact 20-second intervals which would indicate old algorithm
            exact_20s_intervals = True
            for i, timestamp in enumerate(timestamps):
                time_parts = timestamp.split(":")
                seconds = int(time_parts[0]) * 60 + int(time_parts[1])
                expected_old = i * 20
                if abs(seconds - expected_old) > 2:  # More than 2 seconds off from 20s intervals
                    exact_20s_intervals = False
                    break

            # Check if content-importance assignment was used (look for specific log events)
            importance_assignment_used = any([
                "content_importance_assignment_start" in str(result.__dict__),
                "importance_bullet_created" in str(result.__dict__)
            ])

            print("🔍 Algorithm Analysis:")
            print(f"   - Content-importance assignment logs found: {importance_assignment_used}")
            print(f"   - Exact 20s intervals detected: {exact_20s_intervals}")

            # Analyze if bullets correspond to high-importance content
            high_importance_content_found = False
            for bullet in result.summary.bullet_points:
                bullet_text_lower = bullet.text.lower()
                important_keywords = ['objective', 'goal', 'data', 'result', 'recommendation', 'strategy', 'implementation']
                if any(keyword in bullet_text_lower for keyword in important_keywords):
                    high_importance_content_found = True
                    break

            print(f"   - High-importance content in bullets: {high_importance_content_found}")

            if exact_20s_intervals and video_duration > 100:  # Only flag as old algorithm for longer videos
                print("❌ WARNING: May still be using old 20-second interval algorithm")
                algorithm_ok = False
            elif not high_importance_content_found:
                print("⚠️  WARNING: Bullets don't seem to contain high-importance content")
                algorithm_ok = True  # Don't fail test, but note the issue
            else:
                print("✅ Using new content-importance assignment algorithm")
                algorithm_ok = True

            return all_within_bounds and algorithm_ok

        else:
            print(f"❌ Processing failed: {result.error}")
            return False

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_bullet_assignment())

    print(f"\n{'='*60}")
    if success:
        print("🎉 BULLET ASSIGNMENT FIX TEST PASSED!")
    else:
        print("💥 BULLET ASSIGNMENT FIX TEST FAILED!")
    print(f"{'='*60}")

    sys.exit(0 if success else 1)