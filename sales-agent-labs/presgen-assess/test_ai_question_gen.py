#!/usr/bin/env python3
"""Test script to debug AI question generation with knowledge base."""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, '/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess')

from src.services.ai_question_generator import AIQuestionGenerator

async def test_ai_question_generation():
    """Test the AI question generator with ML certification."""

    print("🧪 Testing AI Question Generation with Knowledge Base")
    print("=" * 60)

    # Initialize the AI question generator
    question_generator = AIQuestionGenerator()

    # Use the ML certification ID from our test
    certification_profile_id = "455dae60-065c-4038-b3df-6d769b955dbb"

    print(f"📝 Testing with certification profile: {certification_profile_id}")

    # Define test parameters
    user_profile = "senior_engineer"
    difficulty_level = "intermediate"
    domain_distribution = {
        "Data Engineering": 2,
        "Exploratory Data Analysis": 2
    }
    question_count = 4

    print(f"🎯 Domain distribution: {domain_distribution}")
    print(f"🔧 Difficulty: {difficulty_level}")
    print(f"📊 Total questions: {question_count}")
    print()

    try:
        # Generate questions
        print("🚀 Starting question generation...")
        result = await question_generator.generate_contextual_assessment(
            certification_profile_id=certification_profile_id,
            user_profile=user_profile,
            difficulty_level=difficulty_level,
            domain_distribution=domain_distribution,
            question_count=question_count
        )

        print(f"✅ Generation completed! Success: {result.get('success', False)}")

        if result.get('success'):
            assessment_data = result.get('assessment_data', {})
            questions = assessment_data.get('questions', [])
            metadata = assessment_data.get('metadata', {})

            print(f"📈 Generated {len(questions)} questions")
            print(f"⏱️  Generation time: {metadata.get('generation_time_ms', 0)}ms")
            print(f"🏆 Average quality: {metadata.get('quality_scores', {}).get('overall', 0):.1f}")

            print("\n🔍 Sample Questions:")
            print("-" * 40)

            for i, question in enumerate(questions[:2], 1):  # Show first 2 questions
                print(f"\nQuestion {i}:")
                print(f"  ID: {question.get('id', 'N/A')}")
                print(f"  Domain: {question.get('domain', 'N/A')}")
                print(f"  Type: {question.get('question_type', 'N/A')}")
                print(f"  Text: {question.get('question_text', 'N/A')[:100]}...")
                print(f"  Quality: {question.get('quality_score', 0):.1f}")

                if question.get('source_references'):
                    print(f"  Sources: {', '.join(question.get('source_references', []))}")
        else:
            print(f"❌ Generation failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"💥 Exception during generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ai_question_generation())