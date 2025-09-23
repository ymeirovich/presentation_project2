"""Phase 3 API integration tests for PresGen-Assess."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import sys
import os
from unittest.mock import Mock

# Set testing environment variable
os.environ["TESTING"] = "1"

# Mock the problematic imports before they're loaded
sys.modules['src.services.llm_service'] = Mock()
sys.modules['src.services.assessment_engine'] = Mock()
sys.modules['src.services.gap_analysis'] = Mock()
sys.modules['src.services.presentation_service'] = Mock()
sys.modules['src.knowledge.base'] = Mock()
sys.modules['src.knowledge.embeddings'] = Mock()

from src.service.app import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def demo_token(client):
    """Get demo authentication token."""
    response = client.post(
        "/api/v1/auth/demo-token",
        json={"username": "test_user", "role": "educator"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(demo_token):
    """Create authorization headers."""
    return {"Authorization": f"Bearer {demo_token}"}


class TestAuthenticationAPI:
    """Test authentication endpoints."""

    def test_demo_token_creation(self, client):
        """Test demo token creation."""
        response = client.post(
            "/api/v1/auth/demo-token",
            json={"username": "test_user", "role": "educator"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["token_type"] == "bearer"
        assert "access_token" in data
        assert data["user_info"]["role"] == "educator"

    def test_invalid_role_demo_token(self, client):
        """Test demo token with invalid role."""
        response = client.post(
            "/api/v1/auth/demo-token",
            json={"username": "test_user", "role": "invalid_role"}
        )

        assert response.status_code == 400

    def test_login_valid_credentials(self, client):
        """Test login with valid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["token_type"] == "bearer"
        assert data["user_info"]["role"] == "admin"

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong_password"}
        )

        assert response.status_code == 401

    def test_get_user_info(self, client, auth_headers):
        """Test getting user information."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "test_user"
        assert data["role"] == "educator"
        assert isinstance(data["permissions"], list)

    def test_get_available_roles(self, client):
        """Test getting available roles."""
        response = client.get("/api/v1/auth/roles")

        assert response.status_code == 200
        data = response.json()
        assert "roles" in data
        assert "admin" in data["roles"]
        assert "educator" in data["roles"]


class TestLLMServiceAPI:
    """Test LLM service endpoints."""

    @patch('src.services.llm_service.LLMService.generate_assessment_questions')
    def test_generate_assessment_questions(self, mock_generate, client, auth_headers):
        """Test assessment question generation."""
        mock_generate.return_value = {
            "success": True,
            "questions": [{"id": "q1", "question_text": "Test question"}],
            "domain": "Test Domain"
        }

        response = client.post(
            "/api/v1/llm/questions/generate",
            json={
                "certification_id": "aws-saa",
                "domain": "Security",
                "question_count": 5
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["questions"]) == 1

    @patch('src.services.llm_service.LLMService.generate_course_outline')
    def test_generate_course_outline(self, mock_generate, client, auth_headers):
        """Test course outline generation."""
        mock_generate.return_value = {
            "success": True,
            "course_title": "Test Course",
            "sections": [{"section_title": "Test Section", "slide_count": 5}]
        }

        response = client.post(
            "/api/v1/llm/course-outline/generate",
            json={
                "assessment_results": {"score": 75},
                "gap_analysis": {"priority_learning_areas": ["Security"]},
                "target_slide_count": 10
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["course_title"] == "Test Course"

    @patch('src.services.llm_service.LLMService.health_check')
    def test_llm_health_check(self, mock_health, client):
        """Test LLM service health check."""
        mock_health.return_value = {
            "status": "healthy",
            "model_available": "gpt-4",
            "api_accessible": True
        }

        response = client.get("/api/v1/llm/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_get_model_info(self, client):
        """Test getting model information."""
        response = client.get("/api/v1/llm/models/info")

        assert response.status_code == 200
        data = response.json()
        assert "current_model" in data
        assert "supported_features" in data


class TestAssessmentEngineAPI:
    """Test assessment engine endpoints."""

    @patch('src.services.assessment_engine.AssessmentEngine.generate_comprehensive_assessment')
    def test_generate_comprehensive_assessment(self, mock_generate, client, auth_headers):
        """Test comprehensive assessment generation."""
        mock_generate.return_value = {
            "success": True,
            "assessment_id": "test-123",
            "questions": [{"id": "q1", "domain": "Security"}],
            "metadata": {"total_questions": 1}
        }

        response = client.post(
            "/api/v1/engine/comprehensive/generate",
            json={
                "certification_profile_id": "550e8400-e29b-41d4-a716-446655440000",
                "question_count": 30,
                "difficulty_level": "intermediate"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["questions"]) == 1

    @patch('src.services.assessment_engine.AssessmentEngine.generate_adaptive_assessment')
    def test_generate_adaptive_assessment(self, mock_generate, client, auth_headers):
        """Test adaptive assessment generation."""
        mock_generate.return_value = {
            "success": True,
            "assessment_id": "test-adaptive-123",
            "assessment_type": "adaptive",
            "questions": [{"id": "q1", "difficulty": 0.5}]
        }

        response = client.post(
            "/api/v1/engine/adaptive/generate",
            json={
                "certification_profile_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_skill_level": "beginner",
                "question_count": 10
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_engine_capabilities(self, client):
        """Test getting engine capabilities."""
        response = client.get("/api/v1/engine/capabilities")

        assert response.status_code == 200
        data = response.json()
        assert "assessment_types" in data
        assert "features" in data


class TestGapAnalysisAPI:
    """Test gap analysis endpoints."""

    @patch('src.services.gap_analysis.GapAnalysisEngine.analyze_assessment_results')
    def test_analyze_assessment_results(self, mock_analyze, client, auth_headers):
        """Test assessment results analysis."""
        mock_analyze.return_value = {
            "success": True,
            "assessment_id": "test-123",
            "student_identifier": "user-456",
            "overall_readiness_score": 75.0,
            "confidence_analysis": {"average_confidence": 3.5},
            "identified_gaps": [{"domain": "Security", "gap_severity": 0.6}],
            "skill_assessments": [
                {
                    "skill_name": "Security",
                    "current_level": "intermediate",
                    "target_level": "advanced",
                    "proficiency_score": 0.7,
                    "confidence_calibration": "good",
                    "estimated_improvement_time_hours": 15
                }
            ],
            "priority_learning_areas": ["Security"],
            "remediation_plan": {"rag_enhanced": True}
        }

        response = client.post(
            "/api/v1/gap-analysis/analyze",
            json={
                "assessment_results": {"score": 75, "domain_scores": {"Security": 65}},
                "certification_profile": {"name": "AWS SAA", "passing_score": 72},
                "confidence_ratings": {"q1": 3.5}
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["overall_readiness_score"] == 75.0

    def test_get_confidence_metrics(self, client):
        """Test getting confidence metrics."""
        response = client.get("/api/v1/gap-analysis/metrics/confidence")

        assert response.status_code == 200
        data = response.json()
        assert "confidence_scale" in data
        assert "calibration_quality" in data


class TestPresentationServiceAPI:
    """Test presentation service endpoints."""

    @patch('src.services.presentation_service.PresentationGenerationService.generate_personalized_presentation')
    def test_generate_personalized_presentation(self, mock_generate, client, auth_headers):
        """Test personalized presentation generation."""
        mock_generate.return_value = {
            "success": True,
            "generation_id": "gen-123",
            "presentation_url": "https://example.com/presentation",
            "slide_count": 20,
            "quality_metrics": {"overall_quality_score": 0.85},
            "gap_coverage": {"coverage_percentage": 80},
            "rag_sources_used": ["Source 1"],
            "estimated_duration_minutes": 45
        }

        response = client.post(
            "/api/v1/presentations/generate",
            json={
                "assessment_results": {"score": 75},
                "gap_analysis": {"priority_learning_areas": ["Security"]},
                "certification_profile": {"name": "AWS SAA"},
                "target_slide_count": 20
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["slide_count"] == 20

    @patch('src.services.presentation_service.PresentationGenerationService.get_presentation_status')
    def test_get_presentation_status(self, mock_status, client, auth_headers):
        """Test getting presentation status."""
        mock_status.return_value = {
            "status": "completed",
            "progress_percentage": 100.0,
            "result_url": "https://example.com/result"
        }

        response = client.get(
            "/api/v1/presentations/status/gen-123",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_get_presentation_capabilities(self, client):
        """Test getting presentation capabilities."""
        response = client.get("/api/v1/presentations/capabilities")

        assert response.status_code == 200
        data = response.json()
        assert "supported_formats" in data
        assert "customization_options" in data


class TestAPIDocumentation:
    """Test API documentation and metadata."""

    def test_openapi_schema(self, client):
        """Test OpenAPI schema generation."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "PresGen-Assess API"
        assert schema["info"]["version"] == "3.0.0"

    def test_health_endpoint(self, client):
        """Test application health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "presgen-assess"


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_headers(self, client):
        """Test rate limit headers in response."""
        response = client.get("/health")

        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    def test_rate_limit_stats(self, client):
        """Test rate limit statistics endpoint."""
        response = client.get("/api/v1/auth/rate-limit/stats")

        assert response.status_code == 200
        data = response.json()
        assert "requests_in_window" in data
        assert "remaining_capacity" in data


class TestErrorHandling:
    """Test API error handling."""

    def test_unauthorized_access(self, client):
        """Test unauthorized access to protected endpoint."""
        response = client.post(
            "/api/v1/llm/questions/generate",
            json={"certification_id": "aws-saa", "domain": "Security"}
        )

        assert response.status_code == 401

    def test_invalid_json_payload(self, client, auth_headers):
        """Test invalid JSON payload handling."""
        response = client.post(
            "/api/v1/llm/questions/generate",
            json={"invalid_field": "value"},
            headers=auth_headers
        )

        assert response.status_code == 422  # Validation error

    def test_method_not_allowed(self, client):
        """Test method not allowed handling."""
        response = client.patch("/api/v1/llm/health")

        assert response.status_code == 405