#!/usr/bin/env python3
"""Debug vector database metadata to find actual certification IDs."""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, '/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess')

from src.knowledge.embeddings import VectorDatabaseManager

async def debug_vector_metadata():
    """Debug vector database metadata."""

    print("🔍 Debugging Vector Database Metadata")
    print("=" * 50)

    # Initialize the vector database manager
    vector_db = VectorDatabaseManager()

    print(f"📋 Investigating stored metadata...")

    try:
        # Get some chunks without filtering by certification_id to see what's there
        print("\n📊 Checking exam guides collection...")

        # Try to get all data from exam guides collection (without certification filter)
        exam_results = vector_db.exam_guides_collection.get(
            limit=5,  # Get first 5 items
            include=['metadatas', 'documents']
        )

        if exam_results and exam_results.get('metadatas'):
            print(f"Found {len(exam_results['metadatas'])} exam guide items")
            for i, metadata in enumerate(exam_results['metadatas'][:3]):
                print(f"\nExam Guide {i+1} metadata:")
                for key, value in metadata.items():
                    print(f"  {key}: {value}")
                print(f"  Content preview: {exam_results['documents'][i][:100]}...")
        else:
            print("No exam guides found")

        print("\n📊 Checking transcripts collection...")

        # Try to get all data from transcripts collection
        transcript_results = vector_db.transcripts_collection.get(
            limit=5,  # Get first 5 items
            include=['metadatas', 'documents']
        )

        if transcript_results and transcript_results.get('metadatas'):
            print(f"Found {len(transcript_results['metadatas'])} transcript items")
            for i, metadata in enumerate(transcript_results['metadatas'][:3]):
                print(f"\nTranscript {i+1} metadata:")
                for key, value in metadata.items():
                    print(f"  {key}: {value}")
                print(f"  Content preview: {transcript_results['documents'][i][:100]}...")
        else:
            print("No transcripts found")

        # Check what certification IDs are actually stored
        print(f"\n🔍 Checking for unique certification IDs...")
        all_cert_ids = set()

        if exam_results and exam_results.get('metadatas'):
            for metadata in exam_results['metadatas']:
                cert_id = metadata.get('certification_id')
                if cert_id:
                    all_cert_ids.add(cert_id)

        if transcript_results and transcript_results.get('metadatas'):
            for metadata in transcript_results['metadatas']:
                cert_id = metadata.get('certification_id')
                if cert_id:
                    all_cert_ids.add(cert_id)

        if all_cert_ids:
            print(f"Found certification IDs: {list(all_cert_ids)}")

            # Try searching with one of the found IDs
            test_cert_id = list(all_cert_ids)[0]
            print(f"\n🧪 Testing search with found cert ID: {test_cert_id}")

            context = await vector_db.retrieve_context(
                query="machine learning",
                certification_id=test_cert_id,
                k=3,
                include_sources=True
            )

            if context:
                print(f"✅ Success! Found {len(context)} results with cert ID {test_cert_id}")
                for i, result in enumerate(context[:2], 1):
                    print(f"  Result {i}: {result.get('content', '')[:150]}...")
            else:
                print(f"❌ Still no results even with stored cert ID: {test_cert_id}")
        else:
            print("❌ No certification IDs found in metadata!")

    except Exception as e:
        print(f"💥 Error during metadata debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_vector_metadata())