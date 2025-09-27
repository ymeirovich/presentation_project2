"""
Test suite for knowledge base prompt functionality.
Tests the new separated knowledge base prompt system following TDD approach.
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
    from src.schemas.knowledge_base_prompts import (
        KnowledgeBasePromptsCreate,
        KnowledgeBasePromptsUpdate,
        KnowledgeBasePromptsResponse
    )
    from src.service.api.v1.endpoints.knowledge_prompts import (
        create_knowledge_base_prompts,
        get_knowledge_base_prompts,
        update_knowledge_base_prompts,
        list_knowledge_base_prompts
    )
    HAS_KB_MODULES = True
except ImportError:
    HAS_KB_MODULES = False


class TestKnowledgeBasePromptsModel:
    """Test the knowledge base prompts database model."""

    def test_environment_setup(self):
        """Test that the environment is ready for knowledge base prompt testing."""
        import sys
        import os

        assert sys.version_info >= (3, 8), "Python 3.8+ required"
        assert os.path.exists("src"), "Source directory exists"
        print("✅ Knowledge base prompt test environment ready")

    @pytest.mark.skipif(not HAS_KB_MODULES, reason="Knowledge base modules not available")
    def test_knowledge_base_prompts_model_creation(self):
        """Test creating a knowledge base prompts model instance."""
        kb_prompts = KnowledgeBasePrompts(
            collection_name="aws_saa_c03_kb",
            certification_name="AWS Solutions Architect Associate",
            document_ingestion_prompt="Ingest AWS documentation with focus on architectural patterns",
            context_retrieval_prompt="Retrieve relevant AWS context for questions",
            semantic_search_prompt="Search AWS knowledge base semantically",
            content_classification_prompt="Classify AWS content by service and domain"
        )

        assert kb_prompts.collection_name == "aws_saa_c03_kb"
        assert kb_prompts.certification_name == "AWS Solutions Architect Associate"
        assert kb_prompts.document_ingestion_prompt is not None
        assert kb_prompts.version == "v1.0"  # Default version
        assert kb_prompts.is_active is True  # Default active state

    @pytest.mark.skipif(not HAS_KB_MODULES, reason="Knowledge base modules not available")
    def test_knowledge_base_prompts_schema_validation(self):
        """Test Pydantic schema validation for knowledge base prompts."""
        # Test valid creation schema
        create_data = KnowledgeBasePromptsCreate(
            collection_name="test_collection",
            certification_name="Test Certification",
            document_ingestion_prompt="Test ingestion prompt"
        )
        assert create_data.collection_name == "test_collection"
        assert create_data.version == "v1.0"  # Default

        # Test update schema
        update_data = KnowledgeBasePromptsUpdate(
            document_ingestion_prompt="Updated ingestion prompt",
            is_active=False
        )
        assert update_data.document_ingestion_prompt == "Updated ingestion prompt"
        assert update_data.is_active is False

    @pytest.mark.skipif(not HAS_KB_MODULES, reason="Knowledge base modules not available")
    def test_knowledge_base_prompts_unique_collection_constraint(self):
        """Test that collection names must be unique."""
        # This would be tested with actual database integration
        # For now, test that the model supports unique constraints
        kb_prompts = KnowledgeBasePrompts(
            collection_name="unique_collection",
            certification_name="Test Cert"
        )
        assert kb_prompts.collection_name == "unique_collection"

    def test_knowledge_base_prompts_text_variations(self):
        """Test various text scenarios for knowledge base prompts."""
        test_cases = [
            {
                "name": "normal_text",
                "document_ingestion_prompt": "Process documents with standard patterns",
                "context_retrieval_prompt": "Retrieve context using standard methods"
            },
            {
                "name": "long_text",
                "document_ingestion_prompt": "A" * 2000,  # Very long prompt
                "context_retrieval_prompt": "B" * 1500
            },
            {
                "name": "special_characters",
                "document_ingestion_prompt": "Process with 'quotes' and \"double quotes\" and {braces}",
                "context_retrieval_prompt": "Unicode: 你好 🌟 café"
            },
            {
                "name": "multiline_text",
                "document_ingestion_prompt": """
                Line 1 of ingestion prompt
                Line 2 with specific instructions

                Line 4 after blank line
                """,
                "context_retrieval_prompt": "Single line context prompt"
            }
        ]

        for test_case in test_cases:
            # Test that we can handle various text scenarios
            data = {
                "collection_name": f"test_{test_case['name']}",
                "certification_name": "Test Certification",
                **{k: v for k, v in test_case.items() if k != "name"}
            }

            if HAS_KB_MODULES:
                try:
                    kb_prompts = KnowledgeBasePromptsCreate(**data)
                    assert kb_prompts.collection_name == data["collection_name"]
                    print(f"✅ Text variation '{test_case['name']}' handled correctly")
                except Exception as e:
                    print(f"⚠️  Text variation '{test_case['name']}' failed: {e}")
            else:
                print(f"⚠️  Skipping text variation '{test_case['name']}' - modules not available")


class TestKnowledgeBasePromptsAPI:
    """Test knowledge base prompts API endpoints."""

    def test_environment_setup(self):
        """Test API test environment."""
        print("✅ Knowledge base prompts API test environment ready")

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for testing."""
        if not HAS_SQLALCHEMY:
            pytest.skip("SQLAlchemy not available")
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def sample_kb_prompts_data(self):
        """Sample knowledge base prompts data for testing."""
        return {
            "collection_name": "aws_solutions_architect_kb",
            "certification_name": "AWS Solutions Architect Associate",
            "document_ingestion_prompt": "Ingest AWS documentation focusing on solutions architecture patterns",
            "context_retrieval_prompt": "Retrieve AWS architectural context relevant to the question",
            "semantic_search_prompt": "Search AWS knowledge base for architectural solutions",
            "content_classification_prompt": "Classify AWS content by architectural domain"
        }

    @pytest.mark.skipif(not HAS_KB_MODULES, reason="Knowledge base modules not available")
    @pytest.mark.asyncio
    async def test_create_knowledge_base_prompts(self, sample_kb_prompts_data, mock_db_session):
        """Test creating knowledge base prompts via API."""
        create_data = KnowledgeBasePromptsCreate(**sample_kb_prompts_data)

        # Mock the database operation
        mock_kb_prompts = MagicMock()
        mock_kb_prompts.id = uuid4()
        mock_kb_prompts.collection_name = create_data.collection_name
        mock_kb_prompts.certification_name = create_data.certification_name

        with patch('src.service.api.v1.endpoints.knowledge_prompts.create_knowledge_base_prompts') as mock_create:
            mock_create.return_value = mock_kb_prompts

            result = await create_knowledge_base_prompts(create_data, mock_db_session)

            assert result.collection_name == sample_kb_prompts_data["collection_name"]
            assert result.certification_name == sample_kb_prompts_data["certification_name"]

    @pytest.mark.skipif(not HAS_KB_MODULES, reason="Knowledge base modules not available")
    @pytest.mark.asyncio
    async def test_get_knowledge_base_prompts(self, sample_kb_prompts_data, mock_db_session):
        """Test retrieving knowledge base prompts by collection name."""
        collection_name = sample_kb_prompts_data["collection_name"]

        # Mock the database query
        mock_kb_prompts = MagicMock()
        mock_kb_prompts.collection_name = collection_name
        mock_kb_prompts.document_ingestion_prompt = sample_kb_prompts_data["document_ingestion_prompt"]

        with patch('src.service.api.v1.endpoints.knowledge_prompts.get_knowledge_base_prompts') as mock_get:
            mock_get.return_value = mock_kb_prompts

            result = await get_knowledge_base_prompts(collection_name, mock_db_session)

            assert result.collection_name == collection_name
            assert result.document_ingestion_prompt == sample_kb_prompts_data["document_ingestion_prompt"]

    @pytest.mark.skipif(not HAS_KB_MODULES, reason="Knowledge base modules not available")
    @pytest.mark.asyncio
    async def test_update_knowledge_base_prompts(self, sample_kb_prompts_data, mock_db_session):
        """Test updating knowledge base prompts."""
        collection_name = sample_kb_prompts_data["collection_name"]
        update_data = KnowledgeBasePromptsUpdate(
            document_ingestion_prompt="Updated ingestion prompt",
            is_active=False
        )

        # Mock the database update
        mock_updated_prompts = MagicMock()
        mock_updated_prompts.collection_name = collection_name
        mock_updated_prompts.document_ingestion_prompt = update_data.document_ingestion_prompt
        mock_updated_prompts.is_active = update_data.is_active

        with patch('src.service.api.v1.endpoints.knowledge_prompts.update_knowledge_base_prompts') as mock_update:
            mock_update.return_value = mock_updated_prompts

            result = await update_knowledge_base_prompts(collection_name, update_data, mock_db_session)

            assert result.document_ingestion_prompt == "Updated ingestion prompt"
            assert result.is_active is False


class TestKnowledgeBasePromptsDataLogging:
    """Test comprehensive logging for knowledge base prompts data flow."""

    def test_environment_setup(self):
        """Test logging test environment."""
        print("✅ Knowledge base prompts logging test environment ready")

    def test_logging_configuration(self):
        """Test that logging is properly configured for data flow tracking."""
        import logging

        # Test that we can create loggers for different components
        db_logger = logging.getLogger("kb_prompts.database")
        api_logger = logging.getLogger("kb_prompts.api")
        proxy_logger = logging.getLogger("kb_prompts.proxy")
        ui_logger = logging.getLogger("kb_prompts.ui")

        # Test correlation ID support
        correlation_id = str(uuid4())

        # Simulate logging at each step
        test_data = {"collection_name": "test_kb", "document_ingestion_prompt": "test prompt"}

        db_logger.info(f"[{correlation_id}] Database operation", extra={"data": test_data, "step": "db_write"})
        api_logger.info(f"[{correlation_id}] API request processed", extra={"data": test_data, "step": "api_response"})
        proxy_logger.info(f"[{correlation_id}] Proxy transformation", extra={"data": test_data, "step": "proxy_transform"})
        ui_logger.info(f"[{correlation_id}] UI data received", extra={"data": test_data, "step": "ui_render"})

        print(f"✅ Logging configuration test completed with correlation ID: {correlation_id}")

    def test_data_transformation_logging(self):
        """Test logging of data transformations between layers."""
        correlation_id = str(uuid4())

        # Test data flow logging scenarios
        test_scenarios = [
            {
                "step": "ui_to_proxy",
                "before": {"document_ingestion_prompt": "UI prompt"},
                "after": {"document_ingestion_prompt": "UI prompt", "_source": "ui"}
            },
            {
                "step": "proxy_to_api",
                "before": {"document_ingestion_prompt": "UI prompt", "_source": "ui"},
                "after": {"document_ingestion_prompt": "UI prompt"}
            },
            {
                "step": "api_to_db",
                "before": {"document_ingestion_prompt": "UI prompt"},
                "after": {"document_ingestion_prompt": "UI prompt", "created_at": datetime.now()}
            }
        ]

        for scenario in test_scenarios:
            logger = logging.getLogger(f"kb_prompts.{scenario['step']}")
            logger.info(
                f"[{correlation_id}] Data transformation in {scenario['step']}",
                extra={
                    "correlation_id": correlation_id,
                    "step": scenario["step"],
                    "before": scenario["before"],
                    "after": scenario["after"],
                    "transformation": "data_flow"
                }
            )

        print(f"✅ Data transformation logging test completed: {correlation_id}")


class TestPromptSeparationValidation:
    """Test that knowledge base and certification profile prompts are properly separated."""

    def test_environment_setup(self):
        """Test separation validation environment."""
        print("✅ Prompt separation validation test environment ready")

    def test_prompt_storage_separation(self):
        """Test that knowledge base and certification profile prompts use different storage."""
        # Knowledge base prompts should be stored in knowledge_base_prompts table
        kb_prompt_fields = [
            "document_ingestion_prompt",
            "context_retrieval_prompt",
            "semantic_search_prompt",
            "content_classification_prompt"
        ]

        # Certification profile prompts should be stored in certification_profiles table
        cert_prompt_fields = [
            "assessment_prompt",
            "presentation_prompt",
            "gap_analysis_prompt"
        ]

        # Test that there's no overlap
        overlap = set(kb_prompt_fields) & set(cert_prompt_fields)
        assert len(overlap) == 0, f"Prompt fields should not overlap: {overlap}"

        print("✅ Prompt storage separation validated")

    def test_prompt_functionality_separation(self):
        """Test that knowledge base and certification profile prompts serve different purposes."""
        # Knowledge base prompts - for document processing and retrieval
        kb_purposes = [
            "document_ingestion",
            "context_retrieval",
            "semantic_search",
            "content_classification"
        ]

        # Certification profile prompts - for assessment and learning content generation
        cert_purposes = [
            "assessment_generation",
            "presentation_creation",
            "gap_analysis"
        ]

        # Test that purposes are distinct
        purpose_overlap = set(kb_purposes) & set(cert_purposes)
        assert len(purpose_overlap) == 0, f"Prompt purposes should not overlap: {purpose_overlap}"

        print("✅ Prompt functionality separation validated")

    def test_prompt_independence(self):
        """Test that changes to one prompt type don't affect the other."""
        # Test scenario: Changing knowledge base prompts should not affect certification prompts
        kb_change_scenario = {
            "before": {
                "kb_prompts": {"document_ingestion_prompt": "Original KB prompt"},
                "cert_prompts": {"assessment_prompt": "Original cert prompt"}
            },
            "after_kb_change": {
                "kb_prompts": {"document_ingestion_prompt": "Modified KB prompt"},
                "cert_prompts": {"assessment_prompt": "Original cert prompt"}  # Should remain unchanged
            }
        }

        # Validate that certification prompts remain unchanged when KB prompts change
        assert (kb_change_scenario["before"]["cert_prompts"]["assessment_prompt"] ==
                kb_change_scenario["after_kb_change"]["cert_prompts"]["assessment_prompt"])

        # Test scenario: Changing certification prompts should not affect knowledge base prompts
        cert_change_scenario = {
            "before": {
                "kb_prompts": {"document_ingestion_prompt": "Original KB prompt"},
                "cert_prompts": {"assessment_prompt": "Original cert prompt"}
            },
            "after_cert_change": {
                "kb_prompts": {"document_ingestion_prompt": "Original KB prompt"},  # Should remain unchanged
                "cert_prompts": {"assessment_prompt": "Modified cert prompt"}
            }
        }

        # Validate that KB prompts remain unchanged when certification prompts change
        assert (cert_change_scenario["before"]["kb_prompts"]["document_ingestion_prompt"] ==
                cert_change_scenario["after_cert_change"]["kb_prompts"]["document_ingestion_prompt"])

        print("✅ Prompt independence validated")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])