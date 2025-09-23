"""Tests for presentation generation service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from src.services.presentation_service import PresentationGenerationService


class TestPresentationGenerationService:
    """Test cases for presentation generation service functionality."""

    @pytest.fixture
    def presentation_service(self):
        """Create presentation service instance for testing."""
        with patch('src.services.presentation_service.settings') as mock_settings, \
             patch('src.services.presentation_service.LLMService'), \
             patch('src.services.presentation_service.RAGKnowledgeBase'):

            mock_settings.presgen_core_url = "http://localhost:8001"
            mock_settings.presgen_core_max_slides = 40

            service = PresentationGenerationService()
            service.llm_service = AsyncMock()
            service.knowledge_base = AsyncMock()
            service.http_client = AsyncMock()
            return service

    @pytest.fixture
    def sample_assessment_results(self):
        """Sample assessment results for testing."""
        return {
            "assessment_id": "test-123",
            "certification_profile_id": "cert-789",
            "score": 68.5,
            "domain_scores": {
                "Design Secure Architectures": 45.0,
                "Design High-Performing Architectures": 60.0
            }
        }

    @pytest.fixture
    def sample_gap_analysis(self):
        """Sample gap analysis for testing."""
        return {
            "overall_readiness_score": 65.0,
            "priority_learning_areas": ["Security", "Performance"],
            "identified_gaps": [
                {
                    "domain": "Security",
                    "gap_severity": 0.7
                }
            ]
        }

    @pytest.fixture
    def sample_certification_profile(self):
        """Sample certification profile for testing."""
        return {
            "name": "AWS Solutions Architect Associate",
            "version": "SAA-C03",
            "exam_domains": [
                {
                    "name": "Design Secure Architectures",
                    "weight_percentage": 24
                }
            ]
        }

    @pytest.fixture
    def mock_course_outline(self):
        """Mock course outline from LLM service."""
        return {
            "success": True,
            "course_title": "Personalized AWS Learning Path",
            "estimated_duration_minutes": 180,
            "learning_objectives": ["Master IAM", "Understand VPC"],
            "sections": [
                {
                    "section_title": "Security Fundamentals",
                    "slide_count": 8,
                    "learning_outcomes": ["IAM mastery"],
                    "content_outline": ["IAM basics", "IAM policies", "IAM roles"],
                    "estimated_minutes": 60
                }
            ],
            "citations": ["AWS IAM User Guide"],
            "rag_context_used": True
        }

    @pytest.fixture
    def mock_presgen_response(self):
        """Mock PresGen-Core API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "presentation_url": "https://docs.google.com/presentation/d/abc123",
            "slide_count": 20,
            "generation_id": "gen-456"
        }
        return mock_response

    @pytest.mark.asyncio
    async def test_generate_personalized_presentation_success(
        self, presentation_service, sample_assessment_results, sample_gap_analysis,
        sample_certification_profile, mock_course_outline, mock_presgen_response
    ):
        """Test successful personalized presentation generation."""
        # Setup
        presentation_service.llm_service.generate_course_outline.return_value = mock_course_outline
        presentation_service.http_client.post.return_value = mock_presgen_response

        # Execute
        result = await presentation_service.generate_personalized_presentation(
            assessment_results=sample_assessment_results,
            gap_analysis=sample_gap_analysis,
            certification_profile=sample_certification_profile,
            target_slide_count=20
        )

        # Verify
        assert result["success"] is True
        assert result["presentation_url"] == "https://docs.google.com/presentation/d/abc123"
        assert result["slide_count"] == 20
        assert "course_outline" in result
        assert "gap_coverage" in result
        assert len(result["rag_sources_used"]) > 0
        assert "quality_metrics" in result

        # Verify LLM service was called
        presentation_service.llm_service.generate_course_outline.assert_called_once()

        # Verify PresGen-Core API was called
        presentation_service.http_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_presentation_invalid_slide_count(
        self, presentation_service, sample_assessment_results, sample_gap_analysis,
        sample_certification_profile
    ):
        """Test presentation generation with invalid slide count."""
        # Execute
        result = await presentation_service.generate_personalized_presentation(
            assessment_results=sample_assessment_results,
            gap_analysis=sample_gap_analysis,
            certification_profile=sample_certification_profile,
            target_slide_count=50  # Exceeds maximum
        )

        # Verify
        assert result["success"] is False
        assert "Slide count must be between 1 and 40" in result["error"]

    @pytest.mark.asyncio
    async def test_generate_presentation_course_outline_failure(
        self, presentation_service, sample_assessment_results, sample_gap_analysis,
        sample_certification_profile
    ):
        """Test presentation generation with course outline failure."""
        # Setup
        presentation_service.llm_service.generate_course_outline.return_value = {
            "success": False,
            "error": "LLM service unavailable"
        }

        # Execute
        result = await presentation_service.generate_personalized_presentation(
            assessment_results=sample_assessment_results,
            gap_analysis=sample_gap_analysis,
            certification_profile=sample_certification_profile,
            target_slide_count=20
        )

        # Verify
        assert result["success"] is False
        assert "Course outline generation failed" in result["error"]

    @pytest.mark.asyncio
    async def test_generate_via_presgen_core_success(self, presentation_service, mock_presgen_response):
        """Test successful PresGen-Core API call."""
        # Setup
        presentation_service.http_client.post.return_value = mock_presgen_response
        presentation_request = {
            "title": "Test Presentation",
            "slide_count": 10,
            "content_outline": [],
            "learning_objectives": [],
            "difficulty_level": "intermediate"
        }

        # Execute
        result = await presentation_service._generate_via_presgen_core(
            presentation_request=presentation_request,
            generation_id="test-gen-123"
        )

        # Verify
        assert result["success"] is True
        assert result["presentation_url"] == "https://docs.google.com/presentation/d/abc123"

        # Verify API call
        presentation_service.http_client.post.assert_called_once_with(
            "http://localhost:8001/api/presentations/generate",
            json={
                "title": "Test Presentation",
                "slide_count": 10,
                "content_outline": [],
                "learning_objectives": [],
                "difficulty_level": "intermediate",
                "source_attribution": True,
                "generation_id": "test-gen-123",
                "service": "presgen-assess"
            },
            headers={"Content-Type": "application/json"}
        )

    @pytest.mark.asyncio
    async def test_generate_via_presgen_core_http_error(self, presentation_service):
        """Test PresGen-Core API call with HTTP error."""
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        http_error = httpx.HTTPStatusError("Server error", request=MagicMock(), response=mock_response)
        presentation_service.http_client.post.side_effect = http_error

        presentation_request = {
            "title": "Test",
            "slide_count": 10,
            "content_outline": "Test outline",
            "learning_objectives": ["Test objective"],
            "difficulty_level": "intermediate"
        }

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            await presentation_service._generate_via_presgen_core(
                presentation_request=presentation_request,
                generation_id="test-gen-123"
            )

        assert "PresGen-Core API error: 500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_via_presgen_core_connection_error(self, presentation_service):
        """Test PresGen-Core API call with connection error."""
        # Setup
        connection_error = httpx.RequestError("Connection failed")
        presentation_service.http_client.post.side_effect = connection_error

        presentation_request = {
            "title": "Test",
            "slide_count": 10,
            "content_outline": "Test outline",
            "learning_objectives": ["Test objective"],
            "difficulty_level": "intermediate"
        }

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            await presentation_service._generate_via_presgen_core(
                presentation_request=presentation_request,
                generation_id="test-gen-123"
            )

        assert "Failed to connect to PresGen-Core" in str(exc_info.value)

    def test_adapt_content_for_presentation(self, presentation_service, mock_course_outline):
        """Test content adaptation for presentation generation."""
        assessment_results = {"score": 75.0}
        gap_analysis = {
            "priority_learning_areas": ["Security", "Networking"],
            "overall_readiness_score": 70.0
        }
        certification_profile = {"name": "AWS SAA"}

        # Execute
        result = presentation_service._adapt_content_for_presentation(
            course_outline=mock_course_outline,
            assessment_results=assessment_results,
            gap_analysis=gap_analysis,
            certification_profile=certification_profile,
            target_slide_count=15,
            presentation_title=None
        )

        # Verify
        assert result["title"] == "Personalized Learning Path: AWS SAA"
        assert result["slide_count"] == 15
        assert "content_outline" in result
        assert result["focus_areas"] == ["Security", "Networking"]
        assert result["rag_context"]["sources_used"] == ["AWS IAM User Guide"]
        assert result["rag_context"]["context_enhanced"] is True

    def test_structure_presentation_content(self, presentation_service, mock_course_outline):
        """Test presentation content structuring."""
        gap_analysis = {"priority_learning_areas": ["Security", "Performance"]}

        # Execute
        result = presentation_service._structure_presentation_content(
            course_outline=mock_course_outline,
            gap_analysis=gap_analysis
        )

        # Verify
        assert len(result) >= 3  # Introduction, content sections, conclusion

        # Check introduction section
        intro_section = result[0]
        assert intro_section["section"] == "Introduction"
        assert len(intro_section["slides"]) == 2

        # Check content section
        content_sections = [s for s in result if s["section"] == "Security Fundamentals"]
        assert len(content_sections) == 1

        # Check conclusion section
        conclusion_section = result[-1]
        assert conclusion_section["section"] == "Next Steps & Resources"

    def test_determine_difficulty_level(self, presentation_service):
        """Test difficulty level determination from gap analysis."""
        # Advanced level
        gap_analysis = {"overall_readiness_score": 85.0}
        level = presentation_service._determine_difficulty_level(gap_analysis)
        assert level == "advanced"

        # Intermediate level
        gap_analysis = {"overall_readiness_score": 70.0}
        level = presentation_service._determine_difficulty_level(gap_analysis)
        assert level == "intermediate"

        # Beginner level
        gap_analysis = {"overall_readiness_score": 45.0}
        level = presentation_service._determine_difficulty_level(gap_analysis)
        assert level == "beginner"

    def test_calculate_slide_distribution(self, presentation_service):
        """Test slide distribution calculation."""
        sections = [
            {"section_title": "Security Basics", "slide_count": 5},
            {"section_title": "Advanced Security", "slide_count": 3},
            {"section_title": "Performance Optimization", "slide_count": 4}
        ]
        priority_areas = ["Security"]

        # Execute
        distribution = presentation_service._calculate_slide_distribution(
            sections=sections,
            target_slide_count=20,
            priority_areas=priority_areas
        )

        # Verify
        assert "Introduction" in distribution
        assert "Conclusion & Next Steps" in distribution
        assert distribution["Introduction"] == 2
        assert distribution["Conclusion & Next Steps"] == 2

        # Security sections should get higher allocation due to priority
        security_slides = (distribution.get("Security Basics", 0) +
                          distribution.get("Advanced Security", 0))
        performance_slides = distribution.get("Performance Optimization", 0)
        assert security_slides >= performance_slides

    def test_analyze_gap_coverage(self, presentation_service, mock_course_outline):
        """Test gap coverage analysis."""
        gap_analysis = {
            "priority_learning_areas": ["Security", "Performance", "Networking"]
        }

        # Execute
        result = presentation_service._analyze_gap_coverage(
            gap_analysis=gap_analysis,
            course_outline=mock_course_outline
        )

        # Verify
        assert result["total_priority_areas"] == 3
        assert "coverage_details" in result
        assert "coverage_percentage" in result

        # Security should be covered (present in course outline)
        assert result["coverage_details"]["Security"]["covered"] is True

    def test_calculate_quality_metrics(self, presentation_service):
        """Test quality metrics calculation."""
        presentation_request = {
            "slide_count": 20,
            "rag_context": {
                "sources_used": ["Source 1", "Source 2", "Source 3", "Source 4", "Source 5"]
            }
        }
        presentation_result = {"slide_count": 20}
        gap_analysis = {}

        # Execute
        metrics = presentation_service._calculate_quality_metrics(
            presentation_request=presentation_request,
            presentation_result=presentation_result,
            gap_analysis=gap_analysis
        )

        # Verify
        assert "slide_count_accuracy" in metrics
        assert "gap_coverage_score" in metrics
        assert "content_relevance_score" in metrics
        assert "source_attribution_quality" in metrics
        assert "overall_quality_score" in metrics

        # Perfect slide count accuracy
        assert metrics["slide_count_accuracy"] == 1.0

        # Good source attribution (5 sources)
        assert metrics["source_attribution_quality"] == 1.0

    def test_check_slide_count_accuracy(self, presentation_service):
        """Test slide count accuracy checking."""
        # Perfect accuracy
        accuracy = presentation_service._check_slide_count_accuracy(
            {"slide_count": 20}, {"slide_count": 20}
        )
        assert accuracy == 1.0

        # Partial accuracy
        accuracy = presentation_service._check_slide_count_accuracy(
            {"slide_count": 20}, {"slide_count": 18}
        )
        assert accuracy == 0.9  # 1 - 2/20

        # Zero accuracy for no requested slides
        accuracy = presentation_service._check_slide_count_accuracy(
            {"slide_count": 0}, {"slide_count": 10}
        )
        assert accuracy == 0.0

    def test_evaluate_source_attribution(self, presentation_service):
        """Test source attribution evaluation."""
        # Excellent attribution (5+ sources)
        request = {"rag_context": {"sources_used": ["S1", "S2", "S3", "S4", "S5"]}}
        score = presentation_service._evaluate_source_attribution(request)
        assert score == 1.0

        # Good attribution (3-4 sources)
        request = {"rag_context": {"sources_used": ["S1", "S2", "S3"]}}
        score = presentation_service._evaluate_source_attribution(request)
        assert score == 0.8

        # Fair attribution (1-2 sources)
        request = {"rag_context": {"sources_used": ["S1"]}}
        score = presentation_service._evaluate_source_attribution(request)
        assert score == 0.6

        # Poor attribution (no sources)
        request = {"rag_context": {"sources_used": []}}
        score = presentation_service._evaluate_source_attribution(request)
        assert score == 0.3

    @pytest.mark.asyncio
    async def test_generate_bulk_presentations_success(self, presentation_service):
        """Test successful bulk presentation generation."""
        # Setup
        presentation_service.generate_personalized_presentation = AsyncMock(return_value={
            "success": True,
            "generation_id": "gen-123",
            "presentation_url": "https://example.com/presentation"
        })

        requests = [
            {"assessment_results": {}, "gap_analysis": {}, "certification_profile": {}},
            {"assessment_results": {}, "gap_analysis": {}, "certification_profile": {}}
        ]

        # Execute
        result = await presentation_service.generate_bulk_presentations(
            generation_requests=requests,
            max_concurrent=2
        )

        # Verify
        assert result["success"] is True
        assert result["total_requests"] == 2
        assert len(result["successful_generations"]) == 2
        assert len(result["failed_generations"]) == 0
        assert result["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_get_presentation_status_success(self, presentation_service):
        """Test successful presentation status retrieval."""
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "completed",
            "generation_id": "gen-123",
            "progress": 100
        }
        presentation_service.http_client.get.return_value = mock_response

        # Execute
        result = await presentation_service.get_presentation_status("gen-123")

        # Verify
        assert result["status"] == "completed"
        assert result["generation_id"] == "gen-123"

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, presentation_service):
        """Test health check with healthy services."""
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        presentation_service.http_client.get.return_value = mock_response
        presentation_service.llm_service.health_check.return_value = {"status": "healthy"}

        # Execute
        result = await presentation_service.health_check()

        # Verify
        assert result["status"] == "healthy"
        assert result["presgen_core_connection"] is True
        assert result["llm_service_status"] == "healthy"
        assert result["max_slides_supported"] == 40

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, presentation_service):
        """Test health check with unhealthy services."""
        # Setup
        presentation_service.http_client.get.side_effect = Exception("Connection failed")

        # Execute
        result = await presentation_service.health_check()

        # Verify
        assert result["status"] == "unhealthy"
        assert result["presgen_core_connection"] is False
        assert "Connection failed" in result["error"]