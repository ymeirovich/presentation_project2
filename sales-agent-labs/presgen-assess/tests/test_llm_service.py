"""Tests for LLM service integration."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from src.services.llm_service import LLMService


class TestLLMService:
    """Test cases for LLM service functionality."""

    @pytest.fixture
    def llm_service(self):
        """Create LLM service instance for testing."""
        with patch('src.services.llm_service.RAGKnowledgeBase'):
            service = LLMService()
            # Mock the OpenAI client
            service.client = AsyncMock()
            return service

    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI API response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''{
            "questions": [
                {
                    "id": "q1",
                    "question_text": "What is the primary benefit of using AWS Lambda?",
                    "question_type": "multiple_choice",
                    "options": [
                        {"letter": "A", "text": "Reduced costs"},
                        {"letter": "B", "text": "Serverless execution"},
                        {"letter": "C", "text": "Automatic scaling"},
                        {"letter": "D", "text": "All of the above"}
                    ],
                    "correct_answer": "D",
                    "explanation": "AWS Lambda provides serverless execution, automatic scaling, and can reduce costs by only charging for actual usage.",
                    "domain": "Compute",
                    "subdomain": "Serverless",
                    "bloom_level": "understand",
                    "difficulty": 0.6,
                    "time_limit_seconds": 120
                }
            ]
        }'''
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 500
        return mock_response

    @pytest.mark.asyncio
    async def test_generate_assessment_questions_success(self, llm_service, mock_openai_response):
        """Test successful assessment question generation."""
        # Setup
        llm_service.client.chat.completions.create.return_value = mock_openai_response
        llm_service.knowledge_base.retrieve_context_for_assessment = AsyncMock(return_value={
            "combined_context": "AWS Lambda is a serverless compute service...",
            "citations": ["AWS Lambda Developer Guide"]
        })

        # Execute
        result = await llm_service.generate_assessment_questions(
            certification_id="aws-saa",
            domain="Compute",
            question_count=1,
            difficulty_level="intermediate"
        )

        # Verify
        assert result["success"] is True
        assert len(result["questions"]) == 1
        assert result["questions"][0]["question_text"] == "What is the primary benefit of using AWS Lambda?"
        assert result["domain"] == "Compute"
        assert result["rag_context_used"] is True
        assert "AWS Lambda Developer Guide" in result["citations"]

    @pytest.mark.asyncio
    async def test_generate_assessment_questions_without_rag(self, llm_service, mock_openai_response):
        """Test question generation without RAG context."""
        # Setup
        llm_service.client.chat.completions.create.return_value = mock_openai_response

        # Execute
        result = await llm_service.generate_assessment_questions(
            certification_id="aws-saa",
            domain="Compute",
            question_count=1,
            use_rag_context=False
        )

        # Verify
        assert result["success"] is True
        assert result["rag_context_used"] is False
        assert result["citations"] == []

    @pytest.mark.asyncio
    async def test_generate_course_outline_success(self, llm_service):
        """Test successful course outline generation."""
        # Setup
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''{
            "course_title": "AWS Solutions Architect Associate - Personalized Path",
            "estimated_duration_minutes": 240,
            "learning_objectives": ["Master compute services", "Understand networking"],
            "sections": [
                {
                    "section_title": "Compute Services Deep Dive",
                    "slide_count": 8,
                    "learning_outcomes": ["EC2 mastery", "Lambda understanding"],
                    "content_outline": ["EC2 instances", "Auto Scaling", "Lambda functions"],
                    "estimated_minutes": 60
                }
            ],
            "target_gaps": ["Compute", "Networking"],
            "prerequisites": ["Basic AWS knowledge"],
            "success_criteria": ["80% on practice tests"]
        }'''
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 800

        llm_service.client.chat.completions.create.return_value = mock_response
        llm_service.knowledge_base.retrieve_context_for_assessment = AsyncMock(return_value={
            "combined_context": "Comprehensive AWS content...",
            "citations": ["AWS Well-Architected Framework"]
        })

        assessment_results = {"score": 65.0, "assessment_id": "test-123"}
        gap_analysis = {"priority_learning_areas": ["Compute", "Networking"]}

        # Execute
        result = await llm_service.generate_course_outline(
            assessment_results=assessment_results,
            gap_analysis=gap_analysis,
            target_slide_count=10,
            certification_id="aws-saa"
        )

        # Verify
        assert result["success"] is True
        assert result["course_title"] == "AWS Solutions Architect Associate - Personalized Path"
        assert len(result["sections"]) == 1
        assert result["sections"][0]["slide_count"] == 8
        assert result["rag_context_used"] is True

    @pytest.mark.asyncio
    async def test_generate_course_outline_invalid_slide_count(self, llm_service):
        """Test course outline generation with invalid slide count."""
        # Execute
        result = await llm_service.generate_course_outline(
            assessment_results={},
            gap_analysis={},
            target_slide_count=50  # Exceeds maximum
        )

        # Verify
        assert result["success"] is False
        assert "Slide count must be between 1 and 40" in result["error"]

    @pytest.mark.asyncio
    async def test_health_check_success(self, llm_service):
        """Test successful health check."""
        # Setup
        mock_response = MagicMock()
        llm_service.client.chat.completions.create.return_value = mock_response

        # Execute
        result = await llm_service.health_check()

        # Verify
        assert result["status"] == "healthy"
        assert result["model_available"] == "gpt-4"
        assert result["api_accessible"] is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, llm_service):
        """Test health check with API failure."""
        # Setup
        llm_service.client.chat.completions.create.side_effect = Exception("API Error")

        # Execute
        result = await llm_service.health_check()

        # Verify
        assert result["status"] == "unhealthy"
        assert result["api_accessible"] is False
        assert "API Error" in result["error"]

    def test_build_assessment_prompt(self, llm_service):
        """Test assessment prompt building."""
        # Execute
        prompt = llm_service._build_assessment_prompt(
            domain="Security",
            question_count=2,
            difficulty_level="advanced",
            question_types=["multiple_choice", "scenario"],
            rag_context="IAM best practices include..."
        )

        # Verify
        assert "Generate 2 high-quality certification exam questions" in prompt
        assert "Security domain" in prompt
        assert "advanced" in prompt
        assert "IAM best practices include..." in prompt
        assert "multiple_choice" in prompt and "scenario" in prompt

    def test_calculate_cost(self, llm_service):
        """Test token cost calculation."""
        # Execute
        cost = llm_service._calculate_cost(1000)

        # Verify
        assert cost == 0.03  # $0.03 for 1000 tokens

    def test_get_difficulty_range(self, llm_service):
        """Test difficulty range descriptions."""
        # Execute & Verify
        assert "0.2-0.4" in llm_service._get_difficulty_range("beginner")
        assert "0.5-0.7" in llm_service._get_difficulty_range("intermediate")
        assert "0.7-0.9" in llm_service._get_difficulty_range("advanced")
        assert "0.5-0.7" in llm_service._get_difficulty_range("unknown")

    @pytest.mark.asyncio
    async def test_get_usage_stats(self, llm_service):
        """Test usage statistics retrieval."""
        # Setup
        llm_service.token_usage = {"total_tokens": 5000, "total_cost": 0.15}

        # Execute
        stats = await llm_service.get_usage_stats()

        # Verify
        assert stats["total_tokens_used"] == 5000
        assert stats["estimated_cost_usd"] == 0.15
        assert stats["model"] == "gpt-4"
        assert "timestamp" in stats