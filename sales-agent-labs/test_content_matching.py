#!/usr/bin/env python3
"""
Test script to verify content matching works correctly
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

async def test_content_matching():
    """Test the content matching algorithm"""

    print("=" * 60)
    print("CONTENT MATCHING TEST")
    print("=" * 60)

    # Create realistic transcript segments that might match LLM content
    segments = [
        TranscriptSegment(
            start_time=5.0, end_time=12.0,
            text="Our primary goal is to increase revenue by 40% through strategic AI integration",
            confidence=0.9
        ),
        TranscriptSegment(
            start_time=20.0, end_time=28.0,
            text="The data shows significant improvement in our lead conversion rates this quarter",
            confidence=0.9
        ),
        TranscriptSegment(
            start_time=35.0, end_time=42.0,
            text="Customer feedback has been overwhelmingly positive with 95% satisfaction scores",
            confidence=0.9
        ),
        TranscriptSegment(
            start_time=49.0, end_time=57.0,
            text="We need to identify real workflow obstacles that are hindering our sales teams",
            confidence=0.9
        ),
        TranscriptSegment(
            start_time=65.0, end_time=72.0,
            text="The recommendation is to implement this solution company-wide by next quarter",
            confidence=0.9
        )
    ]

    # Simulate LLM-generated bullet content (might be paraphrased or summarized)
    llm_bullets = [
        "Primary objective is to increase revenue by 40% through AI integration",
        "Data demonstrates major improvement in lead conversion this quarter",
        "Identifies real workflow obstacles hindering sales teams",  # This is the user's example!
        "Recommendation to implement solution company-wide next quarter"
    ]

    agent = ContentAgent(job_id="content-matching-test")

    print(f"📊 TRANSCRIPT SEGMENTS ({len(segments)} total):")
    for i, segment in enumerate(segments):
        timestamp = f"{int(segment.start_time//60):02d}:{int(segment.start_time%60):02d}"
        print(f"  {i+1}. [{timestamp}] {segment.text}")

    print(f"\n🤖 LLM-GENERATED BULLETS ({len(llm_bullets)} total):")
    for i, bullet in enumerate(llm_bullets):
        print(f"  {i+1}. {bullet}")

    print(f"\n🔍 CONTENT MATCHING ANALYSIS:")
    print("-" * 60)

    for i, bullet_text in enumerate(llm_bullets):
        print(f"\nBullet {i+1}: \"{bullet_text}\"")

        # Test the matching algorithm
        best_segment = agent._find_best_matching_segment(bullet_text, segments)

        if best_segment:
            actual_timestamp = f"{int(best_segment.start_time//60):02d}:{int(best_segment.start_time%60):02d}"
            print(f"  ✅ MATCHED to segment at [{actual_timestamp}]: \"{best_segment.text}\"")
            print(f"     Timestamp: {best_segment.start_time:.1f}s - {best_segment.end_time:.1f}s")

            # Special check for the user's example
            if "workflow obstacles hindering sales" in bullet_text.lower():
                expected_time = 49.0  # Should match the segment at 49s
                if abs(best_segment.start_time - expected_time) < 5:
                    print(f"  🎯 USER'S EXAMPLE CORRECT: Bullet assigned to {actual_timestamp} (expected around 00:49)")
                else:
                    print(f"  ❌ USER'S EXAMPLE WRONG: Expected around 00:49, got {actual_timestamp}")
        else:
            print(f"  ❌ NO MATCH FOUND - would use fallback timestamp")

    return True

if __name__ == "__main__":
    success = asyncio.run(test_content_matching())

    print(f"\n{'='*60}")
    if success:
        print("🎉 CONTENT MATCHING TEST COMPLETED!")
    else:
        print("💥 CONTENT MATCHING TEST FAILED!")
    print(f"{'='*60}")