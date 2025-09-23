"""Integration tests for PresGen-Assess end-to-end workflows."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from src.services.assessment_engine import AssessmentEngine
from src.services.gap_analysis import GapAnalysisEngine
from src.services.presentation_service import PresentationGenerationService


class TestIntegrationWorkflows:
    """Test cases for end-to-end workflow integration."""

    @pytest.fixture
    def mock_certification_profile(self):
        """Mock certification profile for integration tests."""
        profile = MagicMock()
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
                "name": "Design Secure Architectures",
                "weight_percentage": 24,
                "topics": ["IAM", "Security groups"]
            }
        ]
        return profile

    @pytest.fixture
    def assessment_engine(self):
        """Create assessment engine with mocked dependencies."""
        with patch('src.services.assessment_engine.LLMService'), \
             patch('src.services.assessment_engine.RAGKnowledgeBase'):
            engine = AssessmentEngine()
            engine.llm_service = AsyncMock()
            engine.knowledge_base = AsyncMock()
            return engine

    @pytest.fixture
    def gap_engine(self):
        """Create gap analysis engine with mocked dependencies."""
        with patch('src.services.gap_analysis.RAGKnowledgeBase'), \
             patch('src.services.gap_analysis.LLMService'):
            engine = GapAnalysisEngine()
            engine.knowledge_base = AsyncMock()
            engine.llm_service = AsyncMock()
            return engine

    @pytest.fixture
    def presentation_service(self):
        """Create presentation service with mocked dependencies."""
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

    @pytest.mark.asyncio
    async def test_complete_assessment_to_presentation_workflow(
        self, assessment_engine, gap_engine, presentation_service, mock_certification_profile
    ):
        """Test complete workflow from assessment generation to presentation creation."""

        # Step 1: Generate Assessment
        assessment_engine.llm_service.generate_assessment_questions.return_value = {
            "success": True,
            "questions": [
                {
                    "id": "q1",
                    "question_text": "Which AWS service provides managed relational databases?",
                    "question_type": "multiple_choice",
                    "correct_answer": "B",
                    "domain": "Design Resilient Architectures",
                    "subdomain": "Database",
                    "difficulty": 0.6,
                    "time_limit_seconds": 120
                },
                {
                    "id": "q2",
                    "question_text": "What is the primary purpose of IAM?",
                    "question_type": "multiple_choice",
                    "correct_answer": "A",
                    "domain": "Design Secure Architectures",
                    "subdomain": "IAM",
                    "difficulty": 0.5,
                    "time_limit_seconds": 90
                }
            ]
        }

        assessment_result = await assessment_engine.generate_comprehensive_assessment(
            certification_profile=mock_certification_profile,
            question_count=10,
            difficulty_level="intermediate"
        )

        assert assessment_result["success"] is True
        assert len(assessment_result["questions"]) > 0

        # Step 2: Simulate Assessment Taking (Mock Results)
        assessment_answers = {
            "assessment_id": assessment_result["assessment_id"],
            "certification_profile_id": str(mock_certification_profile.id),
            "user_id": "test-user-123",
            "score": 65.0,
            "domain_scores": {
                "Design Resilient Architectures": 70.0,
                "Design Secure Architectures": 45.0
            },
            "questions": assessment_result["questions"],
            "answers": {
                "q1": {"is_correct": True, "response_time_seconds": 45},
                "q2": {"is_correct": False, "response_time_seconds": 120}
            }
        }

        # Step 3: Perform Gap Analysis
        gap_engine.knowledge_base.retrieve_context_for_assessment.return_value = {
            "combined_context": "IAM security best practices and database recommendations...",
            "citations": ["AWS IAM User Guide", "RDS Best Practices"]
        }

        certification_profile_dict = {
            "name": mock_certification_profile.name,
            "passing_score": mock_certification_profile.passing_score,
            "exam_domains": mock_certification_profile.exam_domains
        }

        confidence_ratings = {"q1": 3.5, "q2": 4.0}  # Overconfident on wrong answer

        gap_analysis_result = await gap_engine.analyze_assessment_results(
            assessment_results=assessment_answers,
            certification_profile=certification_profile_dict,
            confidence_ratings=confidence_ratings
        )

        assert gap_analysis_result["success"] is True
        assert len(gap_analysis_result["identified_gaps"]) > 0
        assert len(gap_analysis_result["priority_learning_areas"]) > 0

        # Step 4: Generate Personalized Presentation
        presentation_service.llm_service.generate_course_outline.return_value = {
            "success": True,
            "course_title": "Personalized AWS SAA Learning Path",
            "estimated_duration_minutes": 240,
            "learning_objectives": ["Master IAM security", "Understand database options"],
            "sections": [
                {
                    "section_title": "IAM Security Deep Dive",
                    "slide_count": 8,
                    "learning_outcomes": ["IAM policies", "IAM roles"],
                    "content_outline": ["IAM basics", "Policy structure", "Role assumptions"],
                    "estimated_minutes": 60
                },
                {
                    "section_title": "Database Services Overview",
                    "slide_count": 6,
                    "learning_outcomes": ["RDS understanding", "DynamoDB basics"],
                    "content_outline": ["RDS types", "Database selection", "Performance tuning"],
                    "estimated_minutes": 45
                }
            ],
            "citations": ["AWS IAM User Guide", "RDS Documentation"],
            "rag_context_used": True
        }

        mock_presgen_response = MagicMock()
        mock_presgen_response.status_code = 200
        mock_presgen_response.json.return_value = {
            "success": True,
            "presentation_url": "https://docs.google.com/presentation/d/test123",
            "slide_count": 20,
            "generation_id": "gen-456"
        }
        presentation_service.http_client.post.return_value = mock_presgen_response

        presentation_result = await presentation_service.generate_personalized_presentation(
            assessment_results=assessment_answers,
            gap_analysis=gap_analysis_result,
            certification_profile=certification_profile_dict,
            target_slide_count=20
        )

        assert presentation_result["success"] is True
        assert presentation_result["presentation_url"] is not None
        assert presentation_result["slide_count"] == 20

        # Step 5: Verify End-to-End Integration
        assert assessment_result["assessment_id"] == assessment_answers["assessment_id"]
        assert gap_analysis_result["assessment_id"] == assessment_answers["assessment_id"]
        assert len(presentation_result["rag_sources_used"]) > 0

        # Verify gap coverage in presentation
        gap_coverage = presentation_result["gap_coverage"]
        assert gap_coverage["total_priority_areas"] > 0
        assert gap_coverage["coverage_percentage"] > 0

        # Verify quality metrics
        quality_metrics = presentation_result["quality_metrics"]
        assert quality_metrics["overall_quality_score"] > 0.5

    @pytest.mark.asyncio
    async def test_adaptive_assessment_workflow(
        self, assessment_engine, gap_engine, mock_certification_profile
    ):
        """Test adaptive assessment workflow with skill level progression."""

        # Generate initial adaptive assessment for beginner
        assessment_engine.llm_service.generate_assessment_questions.return_value = {
            "success": True,
            "questions": [
                {
                    "id": "q1",
                    "difficulty": 0.3,
                    "domain": "Design Resilient Architectures",
                    "adaptive_difficulty": "beginner"
                }
            ]
        }

        adaptive_result = await assessment_engine.generate_adaptive_assessment(
            certification_profile=mock_certification_profile,
            user_skill_level="beginner",
            question_count=5
        )

        assert adaptive_result["success"] is True
        assert adaptive_result["user_skill_level"] == "beginner"
        assert len(adaptive_result["difficulty_progression"]) == 5

        # Simulate good performance to trigger skill level upgrade
        mock_answers = {
            "assessment_id": adaptive_result["assessment_id"],
            "score": 85.0,  # High score
            "domain_scores": {"Design Resilient Architectures": 85.0}
        }

        # Analyze for skill level assessment
        gap_engine.knowledge_base.retrieve_context_for_assessment.return_value = {
            "combined_context": "Advanced concepts...",
            "citations": ["Advanced Guide"]
        }

        skill_analysis = await gap_engine.analyze_assessment_results(
            assessment_results=mock_answers,
            certification_profile={
                "name": mock_certification_profile.name,
                "passing_score": 72,
                "exam_domains": mock_certification_profile.exam_domains
            }
        )

        # Verify skill level progression
        skill_assessments = skill_analysis["skill_assessments"]
        resilient_skill = next(
            (s for s in skill_assessments if s["skill_name"] == "Design Resilient Architectures"),
            None
        )
        assert resilient_skill is not None
        assert resilient_skill["current_level"] in ["advanced", "expert"]

    @pytest.mark.asyncio
    async def test_bulk_presentation_generation_workflow(
        self, presentation_service, assessment_engine, gap_engine, mock_certification_profile
    ):
        """Test bulk presentation generation for multiple users."""

        # Setup multiple assessment results
        assessment_results_list = []
        gap_analysis_list = []

        for i in range(3):
            # Mock assessment results for each user
            assessment_results = {
                "assessment_id": f"test-{i}",
                "user_id": f"user-{i}",
                "score": 60.0 + (i * 10),  # Varying scores
                "domain_scores": {
                    "Design Secure Architectures": 50.0 + (i * 15)
                }
            }

            # Mock gap analysis for each user
            gap_analysis = {
                "overall_readiness_score": 55.0 + (i * 10),
                "priority_learning_areas": ["Security"],
                "identified_gaps": [{"domain": "Security", "gap_severity": 0.8 - (i * 0.1)}]
            }

            assessment_results_list.append(assessment_results)
            gap_analysis_list.append(gap_analysis)

        # Prepare bulk generation requests
        generation_requests = []
        for i in range(3):
            request = {
                "assessment_results": assessment_results_list[i],
                "gap_analysis": gap_analysis_list[i],
                "certification_profile": {
                    "name": mock_certification_profile.name,
                    "exam_domains": mock_certification_profile.exam_domains
                },
                "target_slide_count": 15 + (i * 5)  # Varying slide counts
            }
            generation_requests.append(request)

        # Mock successful individual generation
        presentation_service.generate_personalized_presentation = AsyncMock(return_value={
            "success": True,
            "generation_id": "gen-bulk-test",
            "presentation_url": "https://example.com/presentation",
            "slide_count": 20
        })

        # Execute bulk generation
        bulk_result = await presentation_service.generate_bulk_presentations(
            generation_requests=generation_requests,
            max_concurrent=2
        )

        # Verify bulk results
        assert bulk_result["success"] is True
        assert bulk_result["total_requests"] == 3
        assert len(bulk_result["successful_generations"]) == 3
        assert bulk_result["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_error_handling_workflow(
        self, assessment_engine, gap_engine, presentation_service, mock_certification_profile
    ):
        """Test error handling throughout the workflow."""

        # Test assessment generation failure
        assessment_engine.llm_service.generate_assessment_questions.side_effect = Exception("LLM API Error")

        assessment_result = await assessment_engine.generate_comprehensive_assessment(
            certification_profile=mock_certification_profile,
            question_count=10
        )

        assert assessment_result["success"] is False
        assert "LLM API Error" in assessment_result["error"]

        # Test gap analysis with missing data
        incomplete_assessment = {
            "assessment_id": "incomplete",
            "score": None,  # Missing score
            "domain_scores": {}
        }

        gap_result = await gap_engine.analyze_assessment_results(
            assessment_results=incomplete_assessment,
            certification_profile={
                "name": "Test Cert",
                "passing_score": 70,
                "exam_domains": []
            }
        )

        # Should handle gracefully with default values
        assert gap_result["overall_readiness_score"] >= 0

        # Test presentation service with invalid slide count
        invalid_presentation_result = await presentation_service.generate_personalized_presentation(
            assessment_results={"score": 70},
            gap_analysis={"priority_learning_areas": []},
            certification_profile={"name": "Test"},
            target_slide_count=50  # Invalid: exceeds maximum
        )

        assert invalid_presentation_result["success"] is False
        assert "Slide count must be between 1 and 40" in invalid_presentation_result["error"]

    @pytest.mark.asyncio
    async def test_rag_context_integration_workflow(
        self, assessment_engine, gap_engine, presentation_service, mock_certification_profile
    ):
        """Test RAG context integration throughout the workflow."""

        # Setup RAG responses for different stages
        assessment_rag_context = {
            "combined_context": "AWS assessment context from exam guides...",
            "citations": ["AWS Exam Guide", "Practice Questions"]
        }

        gap_analysis_rag_context = {
            "combined_context": "Learning resources for identified gaps...",
            "citations": ["AWS Learning Paths", "Best Practices Guide"]
        }

        presentation_rag_context = {
            "combined_context": "Comprehensive study materials...",
            "citations": ["AWS Documentation", "Case Studies"]
        }

        # Configure RAG responses
        assessment_engine.knowledge_base.retrieve_context_for_assessment.return_value = assessment_rag_context
        gap_engine.knowledge_base.retrieve_context_for_assessment.return_value = gap_analysis_rag_context
        presentation_service.knowledge_base.retrieve_context_for_assessment.return_value = presentation_rag_context

        # Mock LLM responses
        assessment_engine.llm_service.generate_assessment_questions.return_value = {
            "success": True,
            "questions": [{"id": "q1", "domain": "Security"}],
            "rag_context_used": True,
            "citations": assessment_rag_context["citations"]
        }

        presentation_service.llm_service.generate_course_outline.return_value = {
            "success": True,
            "course_title": "RAG-Enhanced Learning Path",
            "sections": [{"section_title": "Security", "slide_count": 10}],
            "citations": presentation_rag_context["citations"],
            "rag_context_used": True
        }

        # Execute workflow with RAG enhancement
        assessment_result = await assessment_engine.generate_comprehensive_assessment(
            certification_profile=mock_certification_profile,
            question_count=5,
            use_rag_context=True
        )

        # Verify RAG context was used in assessment
        assert assessment_result["rag_context_used"] is True

        # Mock assessment results for gap analysis
        assessment_answers = {
            "assessment_id": assessment_result["assessment_id"],
            "score": 65.0,
            "domain_scores": {"Security": 45.0},
            "questions": assessment_result["questions"],
            "answers": {"q1": {"is_correct": False}}
        }

        gap_analysis_result = await gap_engine.analyze_assessment_results(
            assessment_results=assessment_answers,
            certification_profile={
                "name": mock_certification_profile.name,
                "passing_score": 72,
                "exam_domains": mock_certification_profile.exam_domains
            }
        )

        # Verify gap analysis includes RAG-enhanced remediation
        remediation_plan = gap_analysis_result["remediation_plan"]
        assert remediation_plan["rag_enhanced"] is True

        # Generate presentation with RAG context
        mock_presgen_response = MagicMock()
        mock_presgen_response.status_code = 200
        mock_presgen_response.json.return_value = {
            "success": True,
            "presentation_url": "https://example.com/rag-presentation",
            "slide_count": 15
        }
        presentation_service.http_client.post.return_value = mock_presgen_response

        presentation_result = await presentation_service.generate_personalized_presentation(
            assessment_results=assessment_answers,
            gap_analysis=gap_analysis_result,
            certification_profile={"name": mock_certification_profile.name},
            target_slide_count=15
        )

        # Verify RAG sources are carried through entire workflow
        assert len(presentation_result["rag_sources_used"]) > 0
        assert any("AWS" in source for source in presentation_result["rag_sources_used"])

        # Verify quality metrics reflect RAG enhancement
        quality_metrics = presentation_result["quality_metrics"]
        assert quality_metrics["source_attribution_quality"] > 0.5