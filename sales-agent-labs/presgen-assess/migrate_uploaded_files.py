#!/usr/bin/env python3
"""
Migration Script: Populate knowledge_base_documents from uploaded_files_metadata

This script migrates existing file metadata from the certification_profiles.uploaded_files_metadata
JSON field into the knowledge_base_documents table to support persistent file tracking.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import models
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.models.certification import CertificationProfile, KnowledgeBaseDocument


def migrate_uploaded_files(db_path='test_database.db'):
    """Migrate uploaded file metadata to knowledge_base_documents table"""

    # Create database engine for SQLite
    database_url = f'sqlite:///{db_path}'
    engine = create_engine(database_url, echo=False)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        print("Starting file metadata migration...")

        # Get all certification profiles with uploaded files
        profiles = db.query(CertificationProfile).all()

        total_files_migrated = 0
        total_profiles_processed = 0

        for profile in profiles:
            print(f"\nProcessing profile: {profile.name} (ID: {profile.id})")

            if not profile.uploaded_files_metadata:
                print("  No uploaded files metadata found, skipping...")
                continue

            uploaded_metadata = profile.uploaded_files_metadata

            # Extract file lists
            exam_guides = uploaded_metadata.get('exam_guides', [])
            transcripts = uploaded_metadata.get('transcripts', [])
            supplemental = uploaded_metadata.get('supplemental', [])

            files_to_migrate = []

            # Process exam guides
            for file_info in exam_guides:
                files_to_migrate.append({
                    'filename': file_info['name'],
                    'size': file_info.get('size', 0),
                    'mime_type': file_info.get('type', 'application/octet-stream'),
                    'classification': 'exam_guide',
                    'ingested': file_info.get('ingested', False)
                })

            # Process transcripts
            for file_info in transcripts:
                files_to_migrate.append({
                    'filename': file_info['name'],
                    'size': file_info.get('size', 0),
                    'mime_type': file_info.get('type', 'application/octet-stream'),
                    'classification': 'transcript',
                    'ingested': file_info.get('ingested', False)
                })

            # Process supplemental
            for file_info in supplemental:
                files_to_migrate.append({
                    'filename': file_info['name'],
                    'size': file_info.get('size', 0),
                    'mime_type': file_info.get('type', 'application/octet-stream'),
                    'classification': 'supplemental',
                    'ingested': file_info.get('ingested', False)
                })

            print(f"  Found {len(files_to_migrate)} files to migrate")

            # Migrate each file
            for file_info in files_to_migrate:
                filename = file_info['filename']

                # Check if file already exists in knowledge_base_documents
                existing = db.query(KnowledgeBaseDocument).filter_by(
                    certification_profile_id=profile.id,
                    original_filename=filename
                ).first()

                if existing:
                    print(f"    File already exists: {filename}, skipping...")
                    continue

                # Construct stored path based on knowledge_base_path and classification
                kb_path = Path(profile.knowledge_base_path)
                stored_path = str(kb_path / filename)

                # Determine processing status
                processing_status = 'completed' if file_info['ingested'] else 'pending'

                # Create knowledge base document record
                doc = KnowledgeBaseDocument(
                    id=uuid.uuid4(),
                    certification_profile_id=profile.id,
                    original_filename=filename,
                    stored_path=stored_path,
                    document_type=file_info['mime_type'],
                    content_classification=file_info['classification'],
                    file_size_bytes=file_info['size'],
                    processing_status=processing_status,
                    chunk_count=None,  # Will be updated during actual processing
                    embedding_model=None,
                    processed_at=datetime.fromisoformat(uploaded_metadata.get('last_ingestion', datetime.now().isoformat()).replace('Z', '+00:00')) if file_info['ingested'] else None,
                    checksum=None,
                    created_at=profile.created_at or datetime.now()
                )

                db.add(doc)
                total_files_migrated += 1
                print(f"    Migrated: {filename} ({file_info['classification']}) - Status: {processing_status}")

            total_profiles_processed += 1
            db.commit()

        print(f"\n{'='*60}")
        print(f"Migration complete!")
        print(f"  Profiles processed: {total_profiles_processed}")
        print(f"  Files migrated: {total_files_migrated}")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    migrate_uploaded_files()
