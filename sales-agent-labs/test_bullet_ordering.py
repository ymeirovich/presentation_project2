#!/usr/bin/env python3
"""
Test script to verify bullet ordering by timestamp
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

async def test_bullet_ordering():
    """Test that bullets are properly ordered by timestamp"""

    print("=" * 60)
    print("BULLET ORDERING TEST")
    print("=" * 60)

    # Create segments with deliberately mixed importance scores to test ordering
    segments = [
        TranscriptSegment(
            start_time=5.0, end_time=12.0,
            text="Welcome to our presentation on quarterly performance",  # Introduction - should be first
            confidence=0.9
        ),
        TranscriptSegment(
            start_time=73.0, end_time=80.0,
            text="Our key recommendation is to implement this critical strategy immediately",  # Very important but late - should be last
            confidence=0.9
        ),
        TranscriptSegment(
            start_time=25.0, end_time=32.0,
            text="The data analysis shows significant improvement in our key performance metrics",  # Important, middle
            confidence=0.9
        ),
        TranscriptSegment(
            start_time=45.0, end_time=52.0,
            text="We need to identify the major obstacles and challenges in our current workflow",  # Important, middle
            confidence=0.9
        ),
        TranscriptSegment(
            start_time=15.0, end_time=22.0,
            text="Let me just adjust the microphone for better audio quality",  # Filler - should be ignored
            confidence=0.9
        ),
        TranscriptSegment(
            start_time=60.0, end_time=67.0,
            text="Customer feedback has provided critical insights into our solution effectiveness",  # Important, late middle
            confidence=0.9
        )
    ]

    print(f"📊 TRANSCRIPT SEGMENTS (chronological order):")
    for i, segment in enumerate(sorted(segments, key=lambda s: s.start_time)):
        timestamp = f"{int(segment.start_time//60):02d}:{int(segment.start_time%60):02d}"
        print(f"  {i+1}. [{timestamp}] {segment.text}")

    agent = ContentAgent(job_id="bullet-ordering-test")

    print(f"\n🧠 Running content-importance algorithm...")
    result = await agent.batch_summarize(segments, max_bullets=5)

    if not result.success:
        print(f"❌ Processing failed: {result.error}")
        return False

    print(f"✅ Processing successful! Generated {len(result.summary.bullet_points)} bullets")

    print(f"\n🎯 GENERATED BULLETS (in returned order):")
    print("-" * 60)

    timestamps_seconds = []
    for i, bullet in enumerate(result.summary.bullet_points):
        time_parts = bullet.timestamp.split(":")
        bullet_seconds = int(time_parts[0]) * 60 + int(time_parts[1])
        timestamps_seconds.append(bullet_seconds)

        print(f"{i+1}. [{bullet.timestamp}] ({bullet_seconds}s) {bullet.text}")

    # Check if bullets are in chronological order
    print(f"\n📋 ORDERING ANALYSIS:")
    print(f"Timestamps in seconds: {timestamps_seconds}")

    is_sorted = all(timestamps_seconds[i] <= timestamps_seconds[i+1] for i in range(len(timestamps_seconds)-1))

    if is_sorted:
        print("✅ Bullets are correctly ordered by timestamp!")
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
    success = asyncio.run(test_bullet_ordering())

    print(f"\n{'='*60}")
    if success:
        print("🎉 BULLET ORDERING TEST PASSED!")
    else:
        print("💥 BULLET ORDERING TEST FAILED!")
    print(f"{'='*60}")