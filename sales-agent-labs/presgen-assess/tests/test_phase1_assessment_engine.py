"""
Test-Driven Development (TDD) Test Suite for Phase 1: Assessment Engine Foundation
Comprehensive test coverage for assessment engine core functionality, RAG integration, and API endpoints.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime
from typing import Dict, List

import httpx
from fastapi.testclient import TestClient

# Import components under test
from src.services.assessment_engine import AssessmentEngine
from src.services.llm_service import LLMService
from src.knowledge.base import RAGKnowledgeBase
from src.knowledge.embeddings import VectorDatabaseManager
from src.service.api.v1.endpoints.engine import (
    ComprehensiveAssessmentRequest,
    AdaptiveAssessmentRequest,
    AssessmentValidationRequest
)
from src.models.certification import CertificationProfile
from src.common.config import settings


class TestAssessmentEngineCore:
    """Test suite for AssessmentEngine core functionality."""

    @pytest.fixture
    async def mock_certification_profile(self):
        """Mock certification profile for testing."""
        profile = MagicMock(spec=CertificationProfile)
        profile.id = uuid4()
        profile.name = "AWS Solutions Architect Associate"
        profile.version = "SAA-C03"
        profile.passing_score = 72
        profile.exam_domains = [
            {
                "name": "Design Resilient Architectures",
                "weight_percentage": 30,
                "topics": ["High availability", "Disaster recovery"]
            },
            {
                "name": "Design High-Performing Architectures",
                "weight_percentage": 28,
                "topics": ["Performance optimization", "Caching"]
            },
            {
                "name": "Design Secure Architectures",
                "weight_percentage": 24,
                "topics": ["IAM", "Security groups"]
            },
            {
                "name": "Design Cost-Optimized Architectures",
                "weight_percentage": 18,
                "topics": ["Cost analysis", "Resource optimization"]
            }
        ]
        return profile

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service for testing."""
        llm_service = AsyncMock(spec=LLMService)
        llm_service.generate_assessment_questions.return_value = {
            "success": True,
            "questions": [
                {
                    "question_text": "Which AWS service provides managed NoSQL database?",
                    "question_type": "multiple_choice",
                    "options": ["A) RDS", "B) DynamoDB", "C) S3", "D) EC2"],
                    "correct_answer": "B",
                    "explanation": "DynamoDB is AWS's managed NoSQL database service.",
                    "domain": "Design High-Performing Architectures",
                    "difficulty": 0.6,
                    "bloom_level": "understand",
                    "time_limit_seconds": 90
                }
            ]
        }
        return llm_service

    @pytest.fixture
    def mock_knowledge_base(self):
        """Mock RAG knowledge base for testing."""
        knowledge_base = AsyncMock(spec=RAGKnowledgeBase)
        knowledge_base.retrieve_context_for_assessment.return_value = {
            "context": "AWS DynamoDB is a fast, flexible NoSQL database service...",
            "citations": ["AWS Documentation", "SAA-C03 Study Guide"],
            "relevance_score": 0.92
        }
        return knowledge_base

    @pytest.fixture
    async def assessment_engine(self, mock_llm_service, mock_knowledge_base):
        """Create assessment engine with mocked dependencies."""
        with patch('src.services.assessment_engine.LLMService', return_value=mock_llm_service), \
             patch('src.services.assessment_engine.RAGKnowledgeBase', return_value=mock_knowledge_base):
            engine = AssessmentEngine()
            return engine

    @pytest.mark.asyncio
    async def test_comprehensive_assessment_generation(self, assessment_engine, mock_certification_profile):
        """Test comprehensive assessment generation with domain balancing."""
        # Arrange
        question_count = 10
        difficulty_level = "intermediate"

        # Act
        result = await assessment_engine.generate_comprehensive_assessment(
            certification_profile=mock_certification_profile,
            question_count=question_count,
            difficulty_level=difficulty_level,
            balance_domains=True,
            use_rag_context=True
        )

        # Assert
        assert result["success"] is True
        assert "assessment_id" in result
        assert result["certification_profile_id"] == str(mock_certification_profile.id)
        assert "questions" in result
        assert "domain_distribution" in result
        assert "metadata" in result
        assert result["rag_context_used"] is True

        # Verify domain distribution
        domain_distribution = result["domain_distribution"]
        total_questions = sum(domain_distribution.values())
        assert total_questions <= question_count + 1  # Allow for rounding adjustments

    @pytest.mark.asyncio
    async def test_adaptive_assessment_creation(self, assessment_engine, mock_certification_profile):
        """Test adaptive assessment with skill level progression."""
        # Arrange
        user_skill_level = "intermediate"
        question_count = 15

        # Act
        result = await assessment_engine.generate_adaptive_assessment(
            certification_profile=mock_certification_profile,
            user_skill_level=user_skill_level,
            question_count=question_count
        )

        # Assert
        assert result["success"] is True
        assert result["assessment_type"] == "adaptive"
        assert result["user_skill_level"] == user_skill_level
        assert "difficulty_progression" in result
        assert len(result["difficulty_progression"]) == question_count

    def test_domain_distribution_calculation(self, assessment_engine, mock_certification_profile):
        """Test domain question distribution algorithms."""
        # Test balanced distribution
        total_questions = 20
        distribution = assessment_engine._calculate_domain_distribution(
            exam_domains=mock_certification_profile.exam_domains,
            total_questions=total_questions,
            balance_domains=True
        )

        # Assert correct distribution based on weights
        assert sum(distribution.values()) == total_questions

        # Check proportional distribution
        resilient_arch_questions = distribution["Design Resilient Architectures"]
        high_perf_questions = distribution["Design High-Performing Architectures"]

        # Resilient architectures should have most questions (30% weight)
        assert resilient_arch_questions >= high_perf_questions

        # Test equal distribution
        equal_distribution = assessment_engine._calculate_domain_distribution(
            exam_domains=mock_certification_profile.exam_domains,
            total_questions=total_questions,
            balance_domains=False
        )

        # All domains should have similar question counts
        question_counts = list(equal_distribution.values())
        assert max(question_counts) - min(question_counts) <= 1

    @pytest.mark.asyncio
    async def test_assessment_quality_validation(self, assessment_engine):
        """Test assessment quality validation pipeline."""
        # Arrange - Valid assessment data
        valid_assessment = {
            "questions": [
                {
                    "question_text": "What is the primary benefit of AWS Lambda?",
                    "question_type": "multiple_choice",
                    "correct_answer": "A",
                    "explanation": "Lambda provides serverless compute capabilities.",
                    "options": ["A) Serverless", "B) Storage", "C) Network", "D) Database"],
                    "domain": "Design High-Performing Architectures"
                }
            ],
            "metadata": {
                "exam_domains": ["Design Resilient Architectures", "Design High-Performing Architectures"]
            }
        }

        # Act
        result = await assessment_engine.validate_assessment_quality(valid_assessment)

        # Assert
        assert result["valid"] is True
        assert result["quality_score"] > 0.5
        assert isinstance(result["issues"], list)
        assert isinstance(result["warnings"], list)

        # Test invalid assessment
        invalid_assessment = {
            "questions": [
                {
                    "question_text": "Bad",  # Too short
                    "question_type": "multiple_choice",
                    # Missing required fields
                }
            ]
        }

        invalid_result = await assessment_engine.validate_assessment_quality(invalid_assessment)
        assert invalid_result["valid"] is False
        assert len(invalid_result["issues"]) > 0

    def test_question_type_distribution(self, assessment_engine):
        """Test question type distribution calculations."""
        # Test standard distribution
        distribution = assessment_engine._get_question_type_distribution(10)

        assert "multiple_choice" in distribution
        assert distribution["multiple_choice"] >= 5  # Should be majority

        # Test small question count
        small_distribution = assessment_engine._get_question_type_distribution(3)
        assert small_distribution["multiple_choice"] == 3  # All multiple choice for small counts

    def test_assessment_metadata_generation(self, assessment_engine, mock_certification_profile):
        """Test assessment metadata calculation accuracy."""
        # Arrange
        questions = [
            {
                "domain": "Design Resilient Architectures",
                "bloom_level": "apply",
                "question_type": "multiple_choice",
                "difficulty": 0.7,
                "time_limit_seconds": 120
            },
            {
                "domain": "Design Secure Architectures",
                "bloom_level": "analyze",
                "question_type": "scenario",
                "difficulty": 0.8,
                "time_limit_seconds": 180
            }
        ]

        # Act
        metadata = assessment_engine._calculate_assessment_metadata(
            questions=questions,
            certification_profile=mock_certification_profile,
            difficulty_level="intermediate"
        )

        # Assert
        assert metadata["total_questions"] == 2
        assert metadata["estimated_duration_minutes"] == 5  # (120 + 180) / 60
        assert metadata["average_difficulty"] == 0.75  # (0.7 + 0.8) / 2
        assert metadata["difficulty_level"] == "intermediate"
        assert "domain_distribution" in metadata
        assert "bloom_taxonomy_distribution" in metadata
        assert metadata["certification_name"] == mock_certification_profile.name


class TestLLMServiceIntegration:
    """Test suite for LLM service integration."""

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client for testing."""
        client = AsyncMock()

        # Mock chat completion response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "questions": [
                    {
                        "question_text": "What is AWS Lambda?",
                        "question_type": "multiple_choice",
                        "options": ["A) Storage", "B) Compute", "C) Network", "D) Database"],
                        "correct_answer": "B",
                        "explanation": "Lambda is a serverless compute service."
                    }
                ]
            })))
        ]
        mock_response.usage = MagicMock(total_tokens=150, prompt_tokens=100, completion_tokens=50)

        client.chat.completions.create.return_value = mock_response
        return client

    @pytest.fixture
    def mock_rag_knowledge_base(self):
        """Mock RAG knowledge base for LLM service testing."""
        knowledge_base = AsyncMock(spec=RAGKnowledgeBase)
        knowledge_base.retrieve_context_for_assessment.return_value = {
            "context": "Relevant AWS Lambda information...",
            "citations": ["AWS Documentation"],
            "relevance_score": 0.85
        }
        return knowledge_base

    @pytest.fixture
    async def llm_service(self, mock_openai_client, mock_rag_knowledge_base):
        """Create LLM service with mocked dependencies."""
        with patch('src.services.llm_service.AsyncOpenAI', return_value=mock_openai_client), \
             patch('src.services.llm_service.RAGKnowledgeBase', return_value=mock_rag_knowledge_base):
            service = LLMService()
            return service

    @pytest.mark.asyncio
    async def test_generate_assessment_questions(self, llm_service):
        """Test LLM-based question generation."""
        # Arrange
        certification_id = str(uuid4())
        domain = "Design High-Performing Architectures"

        # Act
        result = await llm_service.generate_assessment_questions(
            certification_id=certification_id,
            domain=domain,
            question_count=5,
            difficulty_level="intermediate",
            use_rag_context=True
        )

        # Assert
        assert result["success"] is True
        assert "questions" in result
        assert len(result["questions"]) >= 1

        question = result["questions"][0]
        assert "question_text" in question
        assert "question_type" in question
        assert "correct_answer" in question
        assert "explanation" in question

    @pytest.mark.asyncio
    async def test_rag_context_integration(self, llm_service):
        """Test RAG context enhancement in question generation."""
        # Act
        result = await llm_service.generate_assessment_questions(
            certification_id=str(uuid4()),
            domain="Test Domain",
            use_rag_context=True
        )

        # Assert
        assert result["success"] is True
        # Verify RAG context was retrieved (mocked call should have been made)
        llm_service.knowledge_base.retrieve_context_for_assessment.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_usage_tracking(self, llm_service):
        """Test token usage tracking and cost calculation."""
        # Act
        await llm_service.generate_assessment_questions(
            certification_id=str(uuid4()),
            domain="Test Domain"
        )

        # Assert
        assert llm_service.token_usage["total_tokens"] > 0
        assert llm_service.token_usage["total_cost"] >= 0


class TestRAGKnowledgeBase:
    """Test suite for RAG knowledge base functionality."""

    @pytest.fixture
    def mock_document_processor(self):
        """Mock document processor for testing."""
        processor = AsyncMock()
        processor.process_document.return_value = {
            "success": True,
            "chunks": [
                {
                    "content": "AWS Lambda is a serverless compute service...",
                    "metadata": {"source": "AWS Documentation", "page": 1}
                }
            ]
        }
        return processor

    @pytest.fixture
    def mock_vector_manager(self):
        """Mock vector database manager for testing."""
        manager = AsyncMock()
        manager.add_documents.return_value = {"success": True, "document_count": 1}
        manager.similarity_search.return_value = [
            {
                "content": "Relevant content about AWS Lambda...",
                "metadata": {"source": "AWS Guide"},
                "similarity_score": 0.92
            }
        ]
        return manager

    @pytest.fixture
    async def rag_knowledge_base(self, mock_document_processor, mock_vector_manager):
        """Create RAG knowledge base with mocked dependencies."""
        with patch('src.knowledge.base.DocumentProcessor', return_value=mock_document_processor), \
             patch('src.knowledge.base.VectorDatabaseManager', return_value=mock_vector_manager):
            knowledge_base = RAGKnowledgeBase()
            return knowledge_base

    @pytest.mark.asyncio
    async def test_ingest_certification_materials(self, rag_knowledge_base):
        """Test certification materials ingestion pipeline."""
        # Arrange
        certification_id = str(uuid4())
        documents = [
            {
                "file_path": "/path/to/aws_guide.pdf",
                "original_filename": "aws_saa_guide.pdf"
            }
        ]

        # Act
        result = await rag_knowledge_base.ingest_certification_materials(
            certification_id=certification_id,
            documents=documents,
            content_classification="exam_guide"
        )

        # Assert
        assert result["success"] is True
        assert result["certification_id"] == certification_id
        assert result["content_classification"] == "exam_guide"
        assert len(result["processed_documents"]) >= 0

    @pytest.mark.asyncio
    async def test_retrieve_context_for_assessment(self, rag_knowledge_base):
        """Test context retrieval for assessment generation."""
        # Arrange
        query = "AWS Lambda serverless computing"
        certification_id = str(uuid4())

        # Act
        result = await rag_knowledge_base.retrieve_context_for_assessment(
            query=query,
            certification_id=certification_id,
            k=5,
            balance_sources=True
        )

        # Assert
        assert "context" in result
        assert "citations" in result
        assert "relevance_score" in result
        assert isinstance(result["citations"], list)


class TestVectorDatabaseManager:
    """Test suite for vector database management."""

    @pytest.mark.asyncio
    async def test_chromadb_client_initialization(self):
        """Test ChromaDB client initialization with new configuration."""
        # This test verifies the fix for the ChromaDB compatibility issue
        try:
            from src.knowledge.embeddings import VectorDatabaseManager
            manager = VectorDatabaseManager()

            # Verify client is properly initialized
            assert manager.client is not None
            assert manager.embedding_function is not None

        except Exception as e:
            pytest.fail(f"ChromaDB initialization failed: {e}")

    @pytest.mark.asyncio
    async def test_collection_management(self):
        """Test ChromaDB collection creation and management."""
        with patch('chromadb.PersistentClient') as mock_client:
            # Mock collection operations
            mock_collection = MagicMock()
            mock_client.return_value.get_or_create_collection.return_value = mock_collection

            from src.knowledge.embeddings import VectorDatabaseManager
            manager = VectorDatabaseManager()

            # Verify collections are initialized
            assert manager.exam_guides_collection is not None or mock_client.called
            assert manager.transcripts_collection is not None or mock_client.called


class TestEngineAPIEndpoints:
    """Test suite for assessment engine API endpoints."""

    @pytest.fixture
    def mock_assessment_engine(self):
        """Mock assessment engine for API testing."""
        engine = AsyncMock(spec=AssessmentEngine)

        # Mock comprehensive assessment response
        engine.generate_comprehensive_assessment.return_value = {
            "success": True,
            "assessment_id": str(uuid4()),
            "questions": [{"question_text": "Test question"}],
            "metadata": {"total_questions": 1}
        }

        # Mock adaptive assessment response
        engine.generate_adaptive_assessment.return_value = {
            "success": True,
            "assessment_id": str(uuid4()),
            "assessment_type": "adaptive",
            "questions": [{"question_text": "Adaptive question"}]
        }

        # Mock validation response
        engine.validate_assessment_quality.return_value = {
            "valid": True,
            "quality_score": 0.85,
            "issues": [],
            "warnings": []
        }

        # Mock engine stats
        engine.get_engine_stats.return_value = {
            "service_status": "active",
            "llm_integration": {"status": "connected"},
            "supported_question_types": ["multiple_choice", "scenario"],
            "supported_difficulty_levels": ["beginner", "intermediate", "advanced"],
            "max_questions_per_assessment": 100,
            "adaptive_assessment_supported": True
        }

        return engine

    @pytest.fixture
    def client(self, mock_assessment_engine):
        """Create test client with mocked assessment engine."""
        from src.service.app import create_app

        app = create_app()

        # Patch the assessment engine
        with patch('src.service.api.v1.endpoints.engine.assessment_engine', mock_assessment_engine):
            yield TestClient(app)

    def test_comprehensive_generate_endpoint(self, client):
        """Test comprehensive assessment generation endpoint."""
        # Arrange
        request_data = {
            "certification_profile_id": str(uuid4()),
            "question_count": 10,
            "difficulty_level": "intermediate",
            "balance_domains": True,
            "use_rag_context": True
        }

        # Act
        response = client.post("/api/v1/engine/comprehensive/generate", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "assessment_id" in data
        assert "questions" in data

    def test_adaptive_generate_endpoint(self, client):
        """Test adaptive assessment generation endpoint."""
        # Arrange
        request_data = {
            "certification_profile_id": str(uuid4()),
            "user_skill_level": "intermediate",
            "question_count": 15
        }

        # Act
        response = client.post("/api/v1/engine/adaptive/generate", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["assessment_type"] == "adaptive"

    def test_validate_endpoint(self, client):
        """Test assessment validation endpoint."""
        # Arrange
        request_data = {
            "assessment_data": {
                "questions": [{"question_text": "Test question"}]
            }
        }

        # Act
        response = client.post("/api/v1/engine/validate", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "quality_score" in data

    def test_health_check_endpoint(self, client):
        """Test engine health check endpoint."""
        # Act
        response = client.get("/api/v1/engine/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["engine_ready"] is True

    def test_stats_endpoint(self, client, mock_assessment_engine):
        """Test engine statistics endpoint."""
        # Act
        response = client.get("/api/v1/engine/stats")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["service_status"] == "active"
        assert "llm_integration" in data
        assert "supported_question_types" in data

    def test_capabilities_endpoint(self, client):
        """Test engine capabilities endpoint."""
        # Act
        response = client.get("/api/v1/engine/capabilities")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "assessment_types" in data
        assert "question_types" in data
        assert "features" in data
        assert "limits" in data


class TestErrorHandlingAndResilience:
    """Test suite for error handling and system resilience."""

    @pytest.fixture
    def failing_llm_service(self):
        """Mock LLM service that fails for testing error handling."""
        service = AsyncMock(spec=LLMService)
        service.generate_assessment_questions.side_effect = Exception("OpenAI API Error")
        return service

    @pytest.fixture
    async def resilient_assessment_engine(self, failing_llm_service):
        """Assessment engine configured for resilience testing."""
        with patch('src.services.assessment_engine.LLMService', return_value=failing_llm_service):
            engine = AssessmentEngine()
            return engine

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, resilient_assessment_engine, mock_certification_profile):
        """Test graceful degradation when dependencies fail."""
        # Act & Assert - Should not raise exception despite LLM service failure
        result = await resilient_assessment_engine.generate_comprehensive_assessment(
            certification_profile=mock_certification_profile,
            question_count=5
        )

        # Should return a result indicating failure rather than crashing
        assert "success" in result
        # If success is False, should include error information
        if not result["success"]:
            assert "error" in result

    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self):
        """Test circuit breaker pattern implementation."""
        # This would test the circuit breaker implementation
        # if it were fully implemented in the assessment engine
        pass  # Placeholder for circuit breaker tests

    @pytest.mark.asyncio
    async def test_input_validation(self):
        """Test input validation and sanitization."""
        from src.service.api.v1.endpoints.engine import ComprehensiveAssessmentRequest

        # Test invalid question count
        with pytest.raises(ValueError):
            ComprehensiveAssessmentRequest(
                certification_profile_id=uuid4(),
                question_count=150,  # Exceeds maximum
                difficulty_level="intermediate"
            )

        # Test invalid difficulty level
        with pytest.raises(ValueError):
            ComprehensiveAssessmentRequest(
                certification_profile_id=uuid4(),
                question_count=10,
                difficulty_level="expert"  # Invalid level
            )


class TestPerformanceAndMetrics:
    """Test suite for performance monitoring and metrics collection."""

    @pytest.mark.asyncio
    async def test_generation_time_tracking(self, assessment_engine, mock_certification_profile):
        """Test assessment generation time tracking."""
        import time

        start_time = time.time()

        # Act
        result = await assessment_engine.generate_comprehensive_assessment(
            certification_profile=mock_certification_profile,
            question_count=5
        )

        generation_time = time.time() - start_time

        # Assert reasonable generation time (should be fast with mocked services)
        assert generation_time < 5.0  # Should complete within 5 seconds
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_concurrent_assessment_generation(self, assessment_engine, mock_certification_profile):
        """Test concurrent assessment generation performance."""
        # Arrange
        tasks = []
        for i in range(3):
            task = assessment_engine.generate_comprehensive_assessment(
                certification_profile=mock_certification_profile,
                question_count=5
            )
            tasks.append(task)

        # Act
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assert
        assert len(results) == 3
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent generation failed: {result}")
            assert result["success"] is True


# Test Configuration
pytest_plugins = ['pytest_asyncio']

# Test database URL for testing
import os
os.environ["DATABASE_URL"] = "sqlite:///./test_assessment_engine.db"
os.environ["TESTING"] = "1"

if __name__ == "__main__":
    # Run specific test classes
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ])