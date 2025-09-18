#!/usr/bin/env python3
"""
Test script to analyze real transcript segments from presgen_test.mp4
and verify timestamp assignment accuracy
"""

import asyncio
import logging
import sys
from pathlib import Path
import subprocess
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp.tools.video_transcription_subprocess import transcribe_video_file
from mcp.tools.video_content import ContentAgent

# Setup logging
logging.basicConfig(level=logging.INFO)

async def analyze_real_transcript():
    """Analyze the real transcript from presgen_test.mp4"""

    print("=" * 80)
    print("REAL TRANSCRIPT ANALYSIS - PRESGEN_TEST.MP4")
    print("=" * 80)

    video_path = "/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/examples/video/presgen_test.mp4"

    if not Path(video_path).exists():
        print(f"❌ Video file not found: {video_path}")
        return False

    print(f"✅ Video file found: {video_path}")

    try:
        # Step 1: Get real transcript segments using the actual transcription system
        print("\n🎤 Extracting real transcript segments...")
        result = await transcribe_video_file(video_path, job_id="real-transcript-test")

        if not result.success:
            print(f"❌ Transcription failed: {result.error}")
            return False

        segments = result.segments
        print(f"✅ Transcription successful! Got {len(segments)} segments")
        print(f"📊 Video duration: {result.total_duration:.2f} seconds")

        # Step 2: Display all transcript segments with their actual timestamps
        print(f"\n📝 REAL TRANSCRIPT SEGMENTS ({len(segments)} total):")
        print("-" * 80)

        for i, segment in enumerate(segments):
            timestamp_str = f"{int(segment.start_time//60):02d}:{int(segment.start_time%60):02d}"
            print(f"{i+1:2d}. [{timestamp_str}] {segment.text}")
            print(f"    Time: {segment.start_time:.1f}s - {segment.end_time:.1f}s | Confidence: {segment.confidence:.2f}")

        # Step 3: Run content-importance algorithm on real segments
        print(f"\n🧠 Running content-importance algorithm...")
        agent = ContentAgent(job_id="real-transcript-analysis")
        content_result = await agent.batch_summarize(segments, max_bullets=5)

        if not content_result.success:
            print(f"❌ Content analysis failed: {content_result.error}")
            return False

        print(f"✅ Content analysis successful!")

        # Step 4: Display bullet assignments and verify accuracy
        print(f"\n🎯 BULLET ASSIGNMENTS:")
        print("-" * 80)

        for i, bullet in enumerate(content_result.summary.bullet_points):
            print(f"{i+1}. [{bullet.timestamp}] {bullet.text}")

            # Parse bullet timestamp
            time_parts = bullet.timestamp.split(":")
            bullet_seconds = int(time_parts[0]) * 60 + int(time_parts[1])

            # Find which real segment this bullet corresponds to
            closest_segment = None
            min_distance = float('inf')

            for segment in segments:
                segment_midpoint = (segment.start_time + segment.end_time) / 2
                distance = abs(bullet_seconds - segment_midpoint)
                if distance < min_distance:
                    min_distance = distance
                    closest_segment = segment

            if closest_segment:
                actual_timestamp = f"{int(closest_segment.start_time//60):02d}:{int(closest_segment.start_time%60):02d}"
                print(f"   📍 Assigned to: {bullet.timestamp} ({bullet_seconds}s)")
                print(f"   🎯 Should be at: {actual_timestamp} ({closest_segment.start_time:.1f}s)")
                print(f"   📏 Distance: {abs(bullet_seconds - closest_segment.start_time):.1f}s")

                # Check if bullet content matches segment content
                content_similarity = len(set(bullet.text.lower().split()) & set(closest_segment.text.lower().split()))
                print(f"   🔍 Content overlap: {content_similarity} words")

                if abs(bullet_seconds - closest_segment.start_time) > 10:  # More than 10 seconds off
                    print(f"   ❌ TIMESTAMP MISMATCH!")
                else:
                    print(f"   ✅ Timestamp accurate")
            print()

        # Step 5: Look for the specific example mentioned by user
        print(f"\n🔍 SEARCHING FOR USER'S EXAMPLE:")
        print("Looking for bullet about 'workflow obstacles hindering sales teams'...")

        target_keywords = ['workflow', 'obstacles', 'hindering', 'sales', 'teams']

        for bullet in content_result.summary.bullet_points:
            bullet_words = bullet.text.lower().split()
            matches = sum(1 for word in target_keywords if any(word in bullet_word for bullet_word in bullet_words))

            if matches >= 2:  # At least 2 keyword matches
                print(f"📍 FOUND SIMILAR BULLET: [{bullet.timestamp}] {bullet.text}")

                # Find in original transcript
                for segment in segments:
                    segment_words = segment.text.lower().split()
                    seg_matches = sum(1 for word in target_keywords if any(word in seg_word for seg_word in segment_words))

                    if seg_matches >= 2:
                        actual_time = f"{int(segment.start_time//60):02d}:{int(segment.start_time%60):02d}"
                        print(f"📍 ACTUAL LOCATION: [{actual_time}] {segment.text}")

                        # Parse timestamps for comparison
                        bullet_time_parts = bullet.timestamp.split(":")
                        bullet_secs = int(bullet_time_parts[0]) * 60 + int(bullet_time_parts[1])

                        print(f"🚨 TIMESTAMP ANALYSIS:")
                        print(f"   Bullet assigned to: {bullet.timestamp} ({bullet_secs}s)")
                        print(f"   Content actually at: {actual_time} ({segment.start_time:.1f}s)")
                        print(f"   Difference: {abs(bullet_secs - segment.start_time):.1f} seconds")

                        if abs(bullet_secs - segment.start_time) > 10:
                            print(f"   ❌ MAJOR TIMESTAMP ERROR CONFIRMED!")
                            return False
                        else:
                            print(f"   ✅ Timestamp appears correct")
                        break
                break

        return True

    except Exception as e:
        print(f"❌ Analysis failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(analyze_real_transcript())

    print(f"\n{'='*80}")
    if success:
        print("🎉 REAL TRANSCRIPT ANALYSIS COMPLETED!")
    else:
        print("💥 REAL TRANSCRIPT ANALYSIS FAILED!")
    print(f"{'='*80}")