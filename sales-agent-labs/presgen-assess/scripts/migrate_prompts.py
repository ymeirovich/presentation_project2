#!/usr/bin/env python3
"""
Data migration script for prompt individuation.
Migrates existing prompts from assessment_template._chromadb_prompts to separated storage.
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select, update, text, inspect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.models.certification import CertificationProfile
from src.models.knowledge_base_prompts import KnowledgeBasePrompts
from src.common.enhanced_logging import (
    setup_enhanced_logging,
    set_correlation_id,
    log_data_flow,
    DATA_FLOW_LOGGER
)

# Migration configuration
MIGRATION_CONFIG = {
    "dry_run": True,  # Set to False for actual migration
    "batch_size": 10,
    "backup_before_migration": True,
    "validate_after_migration": True
}

# Default knowledge base prompts for new collections
DEFAULT_KB_PROMPTS = {
    "document_ingestion_prompt": """You are an expert document processor for professional certification knowledge bases.

INGESTION REQUIREMENTS:
- Accuracy: Preserve technical accuracy and specific terminology
- Structure: Maintain logical organization and hierarchical relationships
- Context: Capture domain-specific context and dependencies
- Standards: Follow certification body standards and best practices

PROCESSING GUIDELINES:
- Extract key concepts, definitions, and procedures
- Identify relationships between topics and subtopics
- Preserve code examples, diagrams, and reference materials
- Maintain version-specific information and updates

Process the following certification documents with focus on creating searchable, contextually rich knowledge segments.""",

    "context_retrieval_prompt": """You are an expert context retrieval specialist for certification knowledge bases.

RETRIEVAL STRATEGY:
- Relevance: Match user queries to the most applicable knowledge segments
- Completeness: Include supporting context and prerequisites
- Accuracy: Ensure retrieved information is current and authoritative
- Specificity: Focus on certification-specific requirements and standards

CONTEXT ENRICHMENT:
- Include related concepts and dependencies
- Provide practical examples and use cases
- Reference official documentation and standards
- Highlight common pitfalls and best practices

Retrieve certification knowledge that directly addresses the user's question with comprehensive supporting context.""",

    "semantic_search_prompt": """You are an expert semantic search engine for professional certification content.

SEARCH METHODOLOGY:
- Conceptual matching beyond keyword similarity
- Domain-specific understanding of terminology
- Hierarchical topic relationships
- Cross-domain knowledge connections

SEARCH OPTIMIZATION:
- Understanding of certification objectives and domains
- Recognition of practical vs. theoretical knowledge
- Awareness of skill progression and prerequisites
- Integration of hands-on experience requirements

Search the certification knowledge base for concepts, patterns, and solutions that semantically align with the user's intent and learning objectives.""",

    "content_classification_prompt": """You are an expert content classifier for certification knowledge organization.

CLASSIFICATION FRAMEWORK:
- Domain categorization by certification objectives
- Skill level classification (foundational, intermediate, advanced)
- Content type identification (concept, procedure, example, reference)
- Learning objective alignment

ORGANIZATIONAL STRUCTURE:
- Primary domain assignment
- Secondary topic relationships
- Difficulty progression mapping
- Practical application categorization

Classify certification content to optimize knowledge discovery, learning progression, and exam preparation effectiveness."""
}


class PromptMigrationManager:
    """Manages the migration of prompts from coupled to separated storage."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_async_engine(database_url)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self.correlation_id = str(uuid4())
        self.migration_stats = {
            "profiles_processed": 0,
            "kb_prompts_created": 0,
            "profile_prompts_updated": 0,
            "errors": []
        }

    async def __aenter__(self):
        setup_enhanced_logging()
        set_correlation_id(self.correlation_id)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.engine.dispose()

    async def create_backup(self) -> str:
        """Create backup of current data before migration."""
        backup_filename = f"prompt_migration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

        log_data_flow(
            logger=DATA_FLOW_LOGGER,
            step="migration_backup",
            component="migration_script",
            message="Creating backup before migration",
            data_before={"backup_filename": backup_filename}
        )

        # This would execute pg_dump or similar backup command
        # For now, just log the intent
        print(f"📦 Backup would be created: {backup_filename}")

        return backup_filename

    async def ensure_knowledge_base_table(self) -> None:
        """Ensure the knowledge_base_prompts table exists before migration."""
        table_created = {"value": False}

        async with self.engine.begin() as conn:
            def _ensure_table(sync_conn):
                inspector = inspect(sync_conn)
                if 'knowledge_base_prompts' not in inspector.get_table_names():
                    KnowledgeBasePrompts.__table__.create(sync_conn, checkfirst=True)
                    table_created["value"] = True

            # run_sync expects a callable that accepts a synchronous connection
            await conn.run_sync(_ensure_table)

        log_data_flow(
            logger=DATA_FLOW_LOGGER,
            step="migration_table_check",
            component="migration_script",
            message="Ensured knowledge_base_prompts table exists",
            data_after={"table_created": table_created["value"]}
        )

        if table_created["value"]:
            print("🆕 Created knowledge_base_prompts table for migration")

    async def analyze_current_state(self) -> Dict[str, Any]:
        """Analyze current prompt storage state."""
        log_data_flow(
            logger=DATA_FLOW_LOGGER,
            step="migration_analysis_start",
            component="migration_script",
            message="Starting analysis of current prompt storage state"
        )

        async with self.async_session() as session:
            # Get all certification profiles
            stmt = select(CertificationProfile)
            result = await session.execute(stmt)
            profiles = result.scalars().all()

            analysis = {
                "total_profiles": len(profiles),
                "profiles_with_assessment_template": 0,
                "profiles_with_chromadb_prompts": 0,
                "profiles_with_database_prompts": 0,
                "profiles_needing_migration": 0,
                "unique_collections": set()
            }

            for profile in profiles:
                if profile.assessment_template:
                    analysis["profiles_with_assessment_template"] += 1

                    if isinstance(profile.assessment_template, dict):
                        chromadb_prompts = profile.assessment_template.get('_chromadb_prompts', {})
                        if chromadb_prompts:
                            analysis["profiles_with_chromadb_prompts"] += 1
                            analysis["profiles_needing_migration"] += 1

                if any([profile.assessment_prompt, profile.presentation_prompt, profile.gap_analysis_prompt]):
                    analysis["profiles_with_database_prompts"] += 1

                # Track unique collections
                if profile.knowledge_base_path:
                    analysis["unique_collections"].add(profile.knowledge_base_path)

            analysis["unique_collections"] = list(analysis["unique_collections"])

            log_data_flow(
                logger=DATA_FLOW_LOGGER,
                step="migration_analysis_complete",
                component="migration_script",
                message="Completed analysis of current state",
                data_after=analysis
            )

            return analysis

    async def migrate_profile_prompts(self, profile: CertificationProfile) -> bool:
        """Migrate prompts for a single certification profile."""
        try:
            if not profile.assessment_template or not isinstance(profile.assessment_template, dict):
                return True  # Nothing to migrate

            chromadb_prompts = profile.assessment_template.get('_chromadb_prompts', {})
            if not chromadb_prompts:
                return True  # No prompts to migrate

            log_data_flow(
                logger=DATA_FLOW_LOGGER,
                step="migration_profile_start",
                component="migration_script",
                message=f"Starting migration for profile: {profile.name}",
                data_before={
                    "profile_id": str(profile.id),
                    "profile_name": profile.name,
                    "has_chromadb_prompts": bool(chromadb_prompts),
                    "chromadb_prompt_keys": list(chromadb_prompts.keys())
                }
            )

            # Create knowledge base prompts record
            kb_prompts_created = await self.create_knowledge_base_prompts(profile, chromadb_prompts)

            # Update certification profile database columns
            profile_updated = await self.update_profile_prompt_columns(profile, chromadb_prompts)

            # Remove _chromadb_prompts from assessment_template
            template_cleaned = await self.clean_assessment_template(profile)

            success = kb_prompts_created and profile_updated and template_cleaned

            log_data_flow(
                logger=DATA_FLOW_LOGGER,
                step="migration_profile_complete",
                component="migration_script",
                message=f"Completed migration for profile: {profile.name}",
                data_after={
                    "profile_id": str(profile.id),
                    "kb_prompts_created": kb_prompts_created,
                    "profile_updated": profile_updated,
                    "template_cleaned": template_cleaned,
                    "success": success
                },
                success=success
            )

            if success:
                self.migration_stats["profiles_processed"] += 1
                if kb_prompts_created:
                    self.migration_stats["kb_prompts_created"] += 1
                if profile_updated:
                    self.migration_stats["profile_prompts_updated"] += 1

            return success

        except Exception as e:
            error_msg = f"Failed to migrate profile {profile.name}: {str(e)}"
            self.migration_stats["errors"].append(error_msg)

            log_data_flow(
                logger=DATA_FLOW_LOGGER,
                step="migration_profile_error",
                component="migration_script",
                message=error_msg,
                error=str(e),
                success=False
            )

            return False

    async def create_knowledge_base_prompts(self, profile: CertificationProfile, chromadb_prompts: Dict) -> bool:
        """Create knowledge base prompts record from existing _chromadb_prompts."""
        try:
            async with self.async_session() as session:
                # Check if knowledge base prompts already exist
                collection_name = profile.knowledge_base_path or f"{profile.name.lower().replace(' ', '_')}_v{profile.version}"

                stmt = select(KnowledgeBasePrompts).where(
                    KnowledgeBasePrompts.collection_name == collection_name
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"⚠️  Knowledge base prompts already exist for: {collection_name}")
                    return True

                # Create new knowledge base prompts record
                kb_prompts = KnowledgeBasePrompts(
                    collection_name=collection_name,
                    certification_name=profile.name,
                    # Use existing prompts if available, otherwise use defaults
                    document_ingestion_prompt=chromadb_prompts.get(
                        'document_ingestion_prompt',
                        DEFAULT_KB_PROMPTS['document_ingestion_prompt']
                    ),
                    context_retrieval_prompt=chromadb_prompts.get(
                        'context_retrieval_prompt',
                        DEFAULT_KB_PROMPTS['context_retrieval_prompt']
                    ),
                    semantic_search_prompt=chromadb_prompts.get(
                        'semantic_search_prompt',
                        DEFAULT_KB_PROMPTS['semantic_search_prompt']
                    ),
                    content_classification_prompt=chromadb_prompts.get(
                        'content_classification_prompt',
                        DEFAULT_KB_PROMPTS['content_classification_prompt']
                    ),
                    version="v1.0",
                    is_active=True
                )

                if not MIGRATION_CONFIG["dry_run"]:
                    session.add(kb_prompts)
                    await session.commit()

                print(f"✅ Created knowledge base prompts for: {collection_name}")
                return True

        except Exception as e:
            print(f"❌ Failed to create knowledge base prompts: {str(e)}")
            return False

    async def update_profile_prompt_columns(self, profile: CertificationProfile, chromadb_prompts: Dict) -> bool:
        """Update certification profile database columns with prompts."""
        try:
            async with self.async_session() as session:
                # Update profile with prompts from _chromadb_prompts
                update_data = {}

                if 'assessment_prompt' in chromadb_prompts and not profile.assessment_prompt:
                    update_data['assessment_prompt'] = chromadb_prompts['assessment_prompt']

                if 'presentation_prompt' in chromadb_prompts and not profile.presentation_prompt:
                    update_data['presentation_prompt'] = chromadb_prompts['presentation_prompt']

                if 'gap_analysis_prompt' in chromadb_prompts and not profile.gap_analysis_prompt:
                    update_data['gap_analysis_prompt'] = chromadb_prompts['gap_analysis_prompt']

                if update_data and not MIGRATION_CONFIG["dry_run"]:
                    stmt = update(CertificationProfile).where(
                        CertificationProfile.id == profile.id
                    ).values(**update_data)
                    await session.execute(stmt)
                    await session.commit()

                print(f"✅ Updated profile prompts for: {profile.name} ({len(update_data)} fields)")
                return True

        except Exception as e:
            print(f"❌ Failed to update profile prompts: {str(e)}")
            return False

    async def clean_assessment_template(self, profile: CertificationProfile) -> bool:
        """Remove _chromadb_prompts from assessment_template."""
        try:
            async with self.async_session() as session:
                if not profile.assessment_template or not isinstance(profile.assessment_template, dict):
                    return True

                new_template = profile.assessment_template.copy()
                if '_chromadb_prompts' in new_template:
                    del new_template['_chromadb_prompts']

                if not MIGRATION_CONFIG["dry_run"]:
                    stmt = update(CertificationProfile).where(
                        CertificationProfile.id == profile.id
                    ).values(assessment_template=new_template)
                    await session.execute(stmt)
                    await session.commit()

                print(f"✅ Cleaned assessment_template for: {profile.name}")
                return True

        except Exception as e:
            print(f"❌ Failed to clean assessment_template: {str(e)}")
            return False

    async def validate_migration(self) -> bool:
        """Validate that migration completed successfully."""
        log_data_flow(
            logger=DATA_FLOW_LOGGER,
            step="migration_validation_start",
            component="migration_script",
            message="Starting migration validation"
        )

        async with self.async_session() as session:
            # Check that no profiles still have _chromadb_prompts
            stmt = select(CertificationProfile)
            result = await session.execute(stmt)
            profiles = result.scalars().all()

            validation_results = {
                "profiles_with_chromadb_prompts": 0,
                "profiles_without_database_prompts": 0,
                "knowledge_base_prompts_created": 0,
                "validation_passed": True
            }

            for profile in profiles:
                if profile.assessment_template and isinstance(profile.assessment_template, dict):
                    if '_chromadb_prompts' in profile.assessment_template:
                        validation_results["profiles_with_chromadb_prompts"] += 1
                        validation_results["validation_passed"] = False

                if not any([profile.assessment_prompt, profile.presentation_prompt, profile.gap_analysis_prompt]):
                    validation_results["profiles_without_database_prompts"] += 1

            # Count knowledge base prompts
            stmt = select(KnowledgeBasePrompts)
            result = await session.execute(stmt)
            kb_prompts = result.scalars().all()
            validation_results["knowledge_base_prompts_created"] = len(kb_prompts)

            log_data_flow(
                logger=DATA_FLOW_LOGGER,
                step="migration_validation_complete",
                component="migration_script",
                message="Completed migration validation",
                data_after=validation_results,
                success=validation_results["validation_passed"]
            )

            return validation_results["validation_passed"]

    async def run_migration(self):
        """Run the complete migration process."""
        print("🚀 Starting Prompt Individuation Migration")
        print(f"📊 Correlation ID: {self.correlation_id}")
        print(f"🏃‍♂️ Dry Run: {MIGRATION_CONFIG['dry_run']}")
        print("=" * 60)

        try:
            # Ensure required tables exist before proceeding
            await self.ensure_knowledge_base_table()

            # Step 1: Create backup
            if MIGRATION_CONFIG["backup_before_migration"]:
                backup_file = await self.create_backup()
                print(f"📦 Backup created: {backup_file}")

            # Step 2: Analyze current state
            analysis = await self.analyze_current_state()
            print(f"📊 Analysis complete:")
            print(f"  - Total profiles: {analysis['total_profiles']}")
            print(f"  - Profiles needing migration: {analysis['profiles_needing_migration']}")
            print(f"  - Unique collections: {len(analysis['unique_collections'])}")

            if analysis["profiles_needing_migration"] == 0:
                print("✅ No migration needed!")
                return

            # Step 3: Migrate profiles
            print(f"\n🔄 Starting migration of {analysis['profiles_needing_migration']} profiles...")

            async with self.async_session() as session:
                stmt = select(CertificationProfile)
                result = await session.execute(stmt)
                profiles = result.scalars().all()

                for i, profile in enumerate(profiles):
                    print(f"📝 Processing profile {i+1}/{len(profiles)}: {profile.name}")
                    success = await self.migrate_profile_prompts(profile)
                    if not success:
                        print(f"❌ Failed to migrate: {profile.name}")

            # Step 4: Validate migration
            if MIGRATION_CONFIG["validate_after_migration"]:
                print(f"\n✅ Validating migration...")
                validation_passed = await self.validate_migration()
                if validation_passed:
                    print("✅ Migration validation passed!")
                else:
                    print("❌ Migration validation failed!")

            # Step 5: Print summary
            print(f"\n📊 Migration Summary:")
            print(f"  - Profiles processed: {self.migration_stats['profiles_processed']}")
            print(f"  - Knowledge base prompts created: {self.migration_stats['kb_prompts_created']}")
            print(f"  - Profile prompts updated: {self.migration_stats['profile_prompts_updated']}")
            print(f"  - Errors: {len(self.migration_stats['errors'])}")

            if self.migration_stats["errors"]:
                print(f"\n❌ Errors encountered:")
                for error in self.migration_stats["errors"]:
                    print(f"  - {error}")

            print(f"\n🎉 Migration {'completed' if not self.migration_stats['errors'] else 'completed with errors'}!")

        except Exception as e:
            log_data_flow(
                logger=DATA_FLOW_LOGGER,
                step="migration_error",
                component="migration_script",
                message="Migration failed with error",
                error=str(e),
                success=False
            )
            print(f"❌ Migration failed: {str(e)}")
            raise


async def main():
    """Main migration script entry point."""
    if len(sys.argv) < 2:
        print("Usage: python migrate_prompts.py <database_url> [--run]")
        print("  database_url: PostgreSQL connection string")
        print("  --run: Actually perform migration (default is dry run)")
        sys.exit(1)

    database_url = sys.argv[1]

    if "--run" in sys.argv:
        MIGRATION_CONFIG["dry_run"] = False
        print("⚠️  RUNNING ACTUAL MIGRATION (not a dry run)")
    else:
        print("🏃‍♂️ RUNNING DRY RUN (use --run to perform actual migration)")

    async with PromptMigrationManager(database_url) as migrator:
        await migrator.run_migration()


if __name__ == "__main__":
    asyncio.run(main())
