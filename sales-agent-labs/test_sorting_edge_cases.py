#!/usr/bin/env python3
"""
Test script to verify bullet sorting works with edge cases and mixed timestamp orders
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp.tools.video_content import ContentAgent, TranscriptSegment

# Setup logging
logging.basicConfig(level=logging.INFO)

async def test_sorting_edge_cases():
    """Test sorting with various edge cases and timestamp patterns"""

    print("=" * 60)
    print("BULLET SORTING EDGE CASES TEST")
    print("=" * 60)

    # Create segments with timestamps that might cause sorting issues
    segments = [
        TranscriptSegment(
            start_time=125.0, end_time=132.0,  # 2:05
            text="Final recommendations and next steps for implementation",
            confidence=0.9
        ),
        TranscriptSegment(
            start_time=15.0, end_time=22.0,    # 0:15
            text="Introduction to our quarterly business analysis",
            confidence=0.9
        ),
        TranscriptSegment(
            start_time=185.0, end_time=192.0,  # 3:05
            text="Questions and discussion period begins now",
            confidence=0.9
        ),
        TranscriptSegment(
            start_time=65.0, end_time=72.0,    # 1:05
            text="Customer satisfaction metrics show dramatic improvement",
            confidence=0.9
        ),
        TranscriptSegment(
            start_time=5.0, end_time=12.0,     # 0:05
            text="Welcome everyone to today's presentation",
            confidence=0.9
        ),
        TranscriptSegment(
            start_time=95.0, end_time=102.0,   # 1:35
            text="Key performance indicators exceeded all expectations this quarter",
            confidence=0.9
        )
    ]

    print(f"📊 TRANSCRIPT SEGMENTS (original order):")
    for i, segment in enumerate(segments):
        timestamp = f"{int(segment.start_time//60):02d}:{int(segment.start_time%60):02d}"
        print(f"  {i+1}. [{timestamp}] {segment.text}")

    agent = ContentAgent(job_id="sorting-edge-cases-test")

    print(f"\n🧠 Running content-importance algorithm...")
    result = await agent.batch_summarize(segments, max_bullets=5)

    if not result.success:
        print(f"❌ Processing failed: {result.error}")
        return False

    print(f"✅ Processing successful! Generated {len(result.summary.bullet_points)} bullets")

    print(f"\n🎯 GENERATED BULLETS (should be chronologically sorted):")
    print("-" * 60)

    timestamps_seconds = []
    for i, bullet in enumerate(result.summary.bullet_points):
        time_parts = bullet.timestamp.split(":")
        bullet_seconds = int(time_parts[0]) * 60 + int(time_parts[1])
        timestamps_seconds.append(bullet_seconds)

        print(f"{i+1}. [{bullet.timestamp}] ({bullet_seconds}s) {bullet.text}")

    # Check if bullets are in chronological order
    print(f"\n📋 SORTING ANALYSIS:")
    print(f"Timestamps in seconds: {timestamps_seconds}")

    is_sorted = all(timestamps_seconds[i] <= timestamps_seconds[i+1] for i in range(len(timestamps_seconds)-1))

    if is_sorted:
        print("✅ Bullets are correctly sorted chronologically!")

        # Additional checks for edge cases
        print(f"\n🔍 EDGE CASE VALIDATION:")

        # Check for proper minute transitions (0:XX to 1:XX to 2:XX etc.)
        minute_transitions = []
        for ts in timestamps_seconds:
            minute = ts // 60
            minute_transitions.append(minute)

        print(f"Minutes progression: {minute_transitions}")

        # Verify no backwards time jumps
        has_backwards_jump = any(timestamps_seconds[i] > timestamps_seconds[i+1] for i in range(len(timestamps_seconds)-1))

        if not has_backwards_jump:
            print("✅ No backwards time jumps detected!")
        else:
            print("❌ Backwards time jumps found!")
            return False

        return True
    else:
        print("❌ Bullets are NOT in chronological order!")

        # Show the correct order
        sorted_bullets = sorted(enumerate(result.summary.bullet_points),
                               key=lambda x: int(x[1].timestamp.split(':')[0]) * 60 + int(x[1].timestamp.split(':')[1]))

        print(f"\n🔧 CORRECT CHRONOLOGICAL ORDER should be:")
        for i, (original_index, bullet) in enumerate(sorted_bullets):
            print(f"{i+1}. [{bullet.timestamp}] {bullet.text}")
            print(f"   (was position {original_index+1} in returned order)")

        return False

if __name__ == "__main__":
    success = asyncio.run(test_sorting_edge_cases())

    print(f"\n{'='*60}")
    if success:
        print("🎉 BULLET SORTING EDGE CASES TEST PASSED!")
    else:
        print("💥 BULLET SORTING EDGE CASES TEST FAILED!")
    print(f"{'='*60}")