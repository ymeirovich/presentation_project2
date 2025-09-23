"""Tests for assessment generation engine."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from src.services.assessment_engine import AssessmentEngine
from src.models.certification import CertificationProfile


class TestAssessmentEngine:
    """Test cases for assessment engine functionality."""

    @pytest.fixture
    def assessment_engine(self):
        """Create assessment engine instance for testing."""
        with patch('src.services.assessment_engine.LLMService'), \
             patch('src.services.assessment_engine.RAGKnowledgeBase'):
            engine = AssessmentEngine()
            engine.llm_service = AsyncMock()
            engine.knowledge_base = AsyncMock()
            return engine

    @pytest.fixture
    def sample_certification_profile(self):
        """Create sample certification profile for testing."""
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
    def mock_llm_response(self):
        """Mock LLM service response."""
        return {
            "success": True,
            "questions": [
                {
                    "id": "q1",
                    "question_text": "Which AWS service provides managed relational databases?",
                    "question_type": "multiple_choice",
                    "options": [
                        {"letter": "A", "text": "DynamoDB"},
                        {"letter": "B", "text": "RDS"},
                        {"letter": "C", "text": "S3"},
                        {"letter": "D", "text": "Lambda"}
                    ],
                    "correct_answer": "B",
                    "explanation": "RDS provides managed relational database services.",
                    "domain": "Design Resilient Architectures",
                    "subdomain": "Database",
                    "bloom_level": "remember",
                    "difficulty": 0.4,
                    "time_limit_seconds": 90
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_generate_comprehensive_assessment_success(
        self, assessment_engine, sample_certification_profile, mock_llm_response
    ):
        """Test successful comprehensive assessment generation."""
        # Setup
        assessment_engine.llm_service.generate_assessment_questions.return_value = mock_llm_response

        # Execute
        result = await assessment_engine.generate_comprehensive_assessment(
            certification_profile=sample_certification_profile,
            question_count=20,
            difficulty_level="intermediate"
        )

        # Verify
        assert result["success"] is True
        assert result["certification_profile_id"] == str(sample_certification_profile.id)
        assert len(result["questions"]) > 0
        assert "metadata" in result
        assert "domain_distribution" in result
        assert result["rag_context_used"] is True

        # Verify LLM service was called for each domain
        assert assessment_engine.llm_service.generate_assessment_questions.call_count == 4

    @pytest.mark.asyncio
    async def test_generate_comprehensive_assessment_invalid_question_count(
        self, assessment_engine, sample_certification_profile
    ):
        """Test assessment generation with invalid question count."""
        # Execute
        result = await assessment_engine.generate_comprehensive_assessment(
            certification_profile=sample_certification_profile,
            question_count=150  # Exceeds maximum
        )

        # Verify
        assert result["success"] is False
        assert "Question count must be between 1 and 100" in result["error"]

    @pytest.mark.asyncio
    async def test_generate_adaptive_assessment_beginner(
        self, assessment_engine, sample_certification_profile, mock_llm_response
    ):
        """Test adaptive assessment generation for beginner level."""
        # Setup
        assessment_engine.llm_service.generate_assessment_questions.return_value = mock_llm_response

        # Execute
        result = await assessment_engine.generate_adaptive_assessment(
            certification_profile=sample_certification_profile,
            user_skill_level="beginner",
            question_count=10
        )

        # Verify
        assert result["success"] is True
        assert result["assessment_type"] == "adaptive"
        assert result["user_skill_level"] == "beginner"
        assert len(result["difficulty_progression"]) == 10
        assert all(level == "beginner" for level in result["difficulty_progression"])

    @pytest.mark.asyncio
    async def test_generate_adaptive_assessment_with_focus_domains(
        self, assessment_engine, sample_certification_profile, mock_llm_response
    ):
        """Test adaptive assessment with specific focus domains."""
        # Setup
        assessment_engine.llm_service.generate_assessment_questions.return_value = mock_llm_response
        focus_domains = ["Design Secure Architectures", "Design Cost-Optimized Architectures"]

        # Execute
        result = await assessment_engine.generate_adaptive_assessment(
            certification_profile=sample_certification_profile,
            focus_domains=focus_domains,
            question_count=6
        )

        # Verify
        assert result["success"] is True
        assert result["focus_domains"] == focus_domains
        assert len(result["questions"]) <= 6

    def test_calculate_domain_distribution_balanced(self, assessment_engine):
        """Test balanced domain distribution calculation."""
        exam_domains = [
            {"name": "Domain A", "weight_percentage": 40},
            {"name": "Domain B", "weight_percentage": 35},
            {"name": "Domain C", "weight_percentage": 25}
        ]

        # Execute
        distribution = assessment_engine._calculate_domain_distribution(
            exam_domains=exam_domains,
            total_questions=20,
            balance_domains=True
        )

        # Verify
        assert sum(distribution.values()) == 20
        assert distribution["Domain A"] == 8  # 40% of 20
        assert distribution["Domain B"] == 7  # 35% of 20
        assert distribution["Domain C"] == 5  # 25% of 20

    def test_calculate_domain_distribution_equal(self, assessment_engine):
        """Test equal domain distribution calculation."""
        exam_domains = [
            {"name": "Domain A", "weight_percentage": 40},
            {"name": "Domain B", "weight_percentage": 35},
            {"name": "Domain C", "weight_percentage": 25}
        ]

        # Execute
        distribution = assessment_engine._calculate_domain_distribution(
            exam_domains=exam_domains,
            total_questions=21,
            balance_domains=False
        )

        # Verify
        assert sum(distribution.values()) == 21
        assert all(count >= 6 for count in distribution.values())  # Each domain gets at least 6 questions

    def test_get_question_type_distribution_large_count(self, assessment_engine):
        """Test question type distribution for large question count."""
        # Execute
        distribution = assessment_engine._get_question_type_distribution(10)

        # Verify
        assert distribution["multiple_choice"] == 7  # 70%
        assert distribution["scenario"] == 2  # 20%
        assert distribution["true_false"] == 1  # 10%

    def test_get_question_type_distribution_small_count(self, assessment_engine):
        """Test question type distribution for small question count."""
        # Execute
        distribution = assessment_engine._get_question_type_distribution(3)

        # Verify
        assert distribution == {"multiple_choice": 3}
        assert "scenario" not in distribution
        assert "true_false" not in distribution

    def test_calculate_assessment_metadata(self, assessment_engine, sample_certification_profile):
        """Test assessment metadata calculation."""
        questions = [
            {
                "domain": "Design Resilient Architectures",
                "bloom_level": "apply",
                "question_type": "multiple_choice",
                "difficulty": 0.6,
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

        # Execute
        metadata = assessment_engine._calculate_assessment_metadata(
            questions=questions,
            certification_profile=sample_certification_profile,
            difficulty_level="intermediate"
        )

        # Verify
        assert metadata["total_questions"] == 2
        assert metadata["estimated_duration_minutes"] == 5  # (120 + 180) / 60
        assert metadata["average_difficulty"] == 0.7  # (0.6 + 0.8) / 2
        assert metadata["difficulty_level"] == "intermediate"
        assert metadata["certification_name"] == "AWS Solutions Architect Associate"
        assert metadata["passing_score"] == 72

        # Check distributions
        assert metadata["domain_distribution"]["Design Resilient Architectures"] == 1
        assert metadata["domain_distribution"]["Design Secure Architectures"] == 1
        assert metadata["bloom_taxonomy_distribution"]["apply"] == 1
        assert metadata["bloom_taxonomy_distribution"]["analyze"] == 1
        assert metadata["question_type_distribution"]["multiple_choice"] == 1
        assert metadata["question_type_distribution"]["scenario"] == 1

    @pytest.mark.asyncio
    async def test_validate_assessment_quality_valid(self, assessment_engine):
        """Test assessment quality validation for valid assessment."""
        assessment_data = {
            "questions": [
                {
                    "question_text": "What is the primary purpose of AWS CloudFormation?",
                    "question_type": "multiple_choice",
                    "correct_answer": "A",
                    "explanation": "CloudFormation is used for infrastructure as code, allowing you to define AWS resources using templates.",
                    "options": [
                        {"letter": "A", "text": "Infrastructure as Code"},
                        {"letter": "B", "text": "Database Management"},
                        {"letter": "C", "text": "Network Security"},
                        {"letter": "D", "text": "Cost Optimization"}
                    ],
                    "domain": "Infrastructure"
                }
            ],
            "metadata": {
                "exam_domains": ["Infrastructure", "Security"]
            }
        }

        # Execute
        result = await assessment_engine.validate_assessment_quality(assessment_data)

        # Verify
        assert result["valid"] is True
        assert result["quality_score"] > 0.8
        assert len(result["issues"]) == 0
        assert result["question_count"] == 1

    @pytest.mark.asyncio
    async def test_validate_assessment_quality_invalid(self, assessment_engine):
        """Test assessment quality validation for invalid assessment."""
        assessment_data = {
            "questions": [
                {
                    "question_text": "Short?",  # Too short
                    "question_type": "multiple_choice",
                    # Missing correct_answer and explanation
                    "options": [
                        {"letter": "A", "text": "Yes"},
                        {"letter": "B", "text": "No"}
                    ]  # Only 2 options instead of 4
                }
            ]
        }

        # Execute
        result = await assessment_engine.validate_assessment_quality(assessment_data)

        # Verify
        assert result["valid"] is False
        assert result["quality_score"] < 0.5
        assert len(result["issues"]) > 0
        assert any("too short" in issue for issue in result["issues"])
        assert any("Missing correct_answer" in issue for issue in result["issues"])

    def test_validate_question_quality_valid(self, assessment_engine):
        """Test individual question quality validation for valid question."""
        question = {
            "question_text": "Which AWS service provides managed NoSQL database capabilities with single-digit millisecond latency?",
            "question_type": "multiple_choice",
            "correct_answer": "B",
            "explanation": "Amazon DynamoDB is a fast NoSQL database service that provides consistent, single-digit millisecond latency at any scale.",
            "options": [
                {"letter": "A", "text": "RDS"},
                {"letter": "B", "text": "DynamoDB"},
                {"letter": "C", "text": "ElastiCache"},
                {"letter": "D", "text": "DocumentDB"}
            ]
        }

        # Execute
        issues = assessment_engine._validate_question_quality(question, 1)

        # Verify
        assert len(issues) == 0

    def test_validate_question_quality_invalid(self, assessment_engine):
        """Test individual question quality validation for invalid question."""
        question = {
            "question_text": "What?",  # Too short
            "question_type": "multiple_choice",
            "correct_answer": "X",  # Invalid format
            "explanation": "Short",  # Too brief
            "options": [
                {"letter": "A", "text": "Option A"}
                # Missing options B, C, D
            ]
        }

        # Execute
        issues = assessment_engine._validate_question_quality(question, 1)

        # Verify
        assert len(issues) > 0
        assert any("too short" in issue for issue in issues)
        assert any("Invalid correct answer format" in issue for issue in issues)
        assert any("exactly 4 options" in issue for issue in issues)
        assert any("too brief" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_get_engine_stats(self, assessment_engine):
        """Test assessment engine statistics retrieval."""
        # Setup
        assessment_engine.llm_service.get_usage_stats.return_value = {
            "total_tokens_used": 10000,
            "estimated_cost_usd": 0.30
        }

        # Execute
        stats = await assessment_engine.get_engine_stats()

        # Verify
        assert stats["service_status"] == "active"
        assert "llm_integration" in stats
        assert stats["supported_question_types"] == ["multiple_choice", "true_false", "scenario"]
        assert stats["supported_difficulty_levels"] == ["beginner", "intermediate", "advanced"]
        assert stats["max_questions_per_assessment"] == 100
        assert stats["adaptive_assessment_supported"] is True