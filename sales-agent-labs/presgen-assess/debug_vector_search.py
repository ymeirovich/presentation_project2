#!/usr/bin/env python3
"""Debug vector database search to understand why no context is found."""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, '/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess')

from src.knowledge.embeddings import VectorDatabaseManager

async def debug_vector_search():
    """Debug vector database search."""

    print("🔍 Debugging Vector Database Search")
    print("=" * 50)

    # Initialize the vector database manager
    vector_db = VectorDatabaseManager()

    # Test certification profile ID
    cert_profile_id = "455dae60-065c-4038-b3df-6d769b955dbb"

    print(f"📋 Testing with certification profile: {cert_profile_id}")

    try:
        # First, check what's in the database
        print("\n📊 Getting collection statistics...")
        stats = await vector_db.get_collection_stats()
        print(f"Exam guides count: {stats.get('exam_guides_count', 0)}")
        print(f"Transcripts count: {stats.get('transcripts_count', 0)}")
        print(f"Total chunks: {stats.get('total_chunks', 0)}")

        if stats.get('total_chunks', 0) == 0:
            print("❌ No content in vector database!")
            return

        # Test different search queries
        test_queries = [
            "Data Engineering intermediate certification concepts and best practices",
            "Data Engineering",
            "machine learning data engineering",
            "AWS machine learning",
            "data preprocessing",
            "Exploratory Data Analysis",
            "data analysis techniques",
            "modeling machine learning",
            "ML implementation operations"
        ]

        print(f"\n🔍 Testing {len(test_queries)} different search queries...")

        for i, query in enumerate(test_queries, 1):
            print(f"\n--- Query {i}: '{query}' ---")

            # Try the search
            context = await vector_db.retrieve_context(
                query=query,
                certification_id=cert_profile_id,
                k=3,
                include_sources=True
            )

            if context:
                print(f"✅ Found {len(context)} results")
                for j, result in enumerate(context[:2], 1):  # Show first 2 results
                    print(f"  Result {j}:")
                    print(f"    Distance: {result.get('distance', 'N/A'):.3f}")
                    print(f"    Source: {result.get('source_type', 'N/A')}")
                    print(f"    Content: {result.get('content', '')[:100]}...")
                    print(f"    Citation: {result.get('citation', 'N/A')}")
            else:
                print("❌ No results found")

        # Test with a very simple query to see what content exists
        print(f"\n🎯 Testing simple search to see any content...")
        simple_context = await vector_db.retrieve_context(
            query="machine",
            certification_id=cert_profile_id,
            k=5,
            include_sources=True
        )

        if simple_context:
            print(f"✅ Simple search found {len(simple_context)} results")
            for i, result in enumerate(simple_context[:3], 1):
                print(f"\nContent sample {i}:")
                print(f"  Source: {result.get('source_type', 'N/A')}")
                print(f"  Distance: {result.get('distance', 'N/A'):.3f}")
                print(f"  Text: {result.get('content', '')[:200]}...")
                if result.get('metadata'):
                    print(f"  Metadata: {result['metadata']}")
        else:
            print("❌ Even simple search found no results")

    except Exception as e:
        print(f"💥 Error during search: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_vector_search())