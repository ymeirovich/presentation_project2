"""
Test suite for Sprint 2: Workflow Orchestration and Response Collection
Tests the new orchestration services and response ingestion pipeline.
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from typing import Dict, List, Any

from src.services.workflow_orchestrator import WorkflowOrchestrator
from src.services.response_ingestion_service import ResponseIngestionService
from src.models.workflow import WorkflowExecution, WorkflowStatus
from src.schemas.google_forms import AssessmentWorkflowRequest


class TestWorkflowOrchestrator:
    """Test suite for workflow orchestration service."""

    @pytest_asyncio.fixture
    async def workflow_orchestrator(self):
        """Create workflow orchestrator instance with mocked dependencies."""
        with patch('src.services.workflow_orchestrator.get_async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()
            with patch('src.services.workflow_orchestrator.GoogleFormsService') as mock_forms:
                with patch('src.services.workflow_orchestrator.AssessmentFormsMapper') as mock_mapper:
                    with patch('src.services.workflow_orchestrator.FormResponseProcessor') as mock_processor:
                        orchestrator = WorkflowOrchestrator()
                        yield orchestrator

    @pytest.fixture
    def sample_assessment_data(self):
        """Sample assessment data for testing."""
        return {
            "assessment_id": str(uuid4()),
            "questions": [
                {
                    "id": "q1",
                    "question_text": "What is AWS Lambda?",
                    "question_type": "multiple_choice",
                    "options": ["A) Storage", "B) Compute", "C) Database", "D) Network"],
                    "correct_answer": "B",
                    "domain": "Compute Services",
                    "difficulty": 0.6
                },
                {
                    "id": "q2",
                    "question_text": "S3 provides block storage.",
                    "question_type": "true_false",
                    "correct_answer": "False",
                    "domain": "Storage Services",
                    "difficulty": 0.4
                }
            ],
            "metadata": {
                "certification_name": "AWS Solutions Architect",
                "total_questions": 2,
                "estimated_duration_minutes": 10
            }
        }

    @pytest.fixture
    def mock_workflow_execution(self):
        """Mock workflow execution record."""
        return WorkflowExecution(
            id=uuid4(),
            user_id="test_user",
            certification_profile_id=uuid4(),
            current_step="create_form",
            execution_status=WorkflowStatus.INITIATED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    @pytest.mark.asyncio
    async def test_execute_assessment_to_form_workflow_success(
        self,
        workflow_orchestrator,
        sample_assessment_data,
        mock_workflow_execution
    ):
        """Test successful assessment-to-form workflow execution."""
        # Arrange
        certification_profile_id = uuid4()
        user_id = "test_user"

        # Mock successful form creation
        mock_form_result = {
            "success": True,
            "form_id": "test_form_123",
            "form_url": "https://forms.google.com/test_form_123",
            "form_title": "AWS Solutions Architect Assessment"
        }

        with patch.object(workflow_orchestrator, '_create_workflow_execution') as mock_create:
            mock_create.return_value = mock_workflow_execution
            with patch.object(workflow_orchestrator, '_create_google_form_phase') as mock_form:
                mock_form.return_value = mock_form_result
                with patch.object(workflow_orchestrator, '_configure_form_phase') as mock_config:
                    with patch.object(workflow_orchestrator, '_start_response_collection_phase') as mock_collection:

                        # Act
                        result = await workflow_orchestrator.execute_assessment_to_form_workflow(
                            certification_profile_id=certification_profile_id,
                            user_id=user_id,
                            assessment_data=sample_assessment_data
                        )

                        # Assert
                        assert result["success"] is True
                        assert "workflow_id" in result
                        assert result["form_id"] == "test_form_123"
                        assert result["form_url"] == "https://forms.google.com/test_form_123"
                        assert result["status"] == WorkflowStatus.AWAITING_COMPLETION

                        # Verify all phases were called
                        mock_create.assert_called_once()
                        mock_form.assert_called_once()
                        mock_config.assert_called_once()
                        mock_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_assessment_to_form_workflow_form_creation_failure(
        self,
        workflow_orchestrator,
        sample_assessment_data,
        mock_workflow_execution
    ):
        """Test workflow failure during form creation phase."""
        # Arrange
        certification_profile_id = uuid4()
        user_id = "test_user"

        # Mock form creation failure
        mock_form_result = {
            "success": False,
            "error": "Google Forms API quota exceeded"
        }

        with patch.object(workflow_orchestrator, '_create_workflow_execution') as mock_create:
            mock_create.return_value = mock_workflow_execution
            with patch.object(workflow_orchestrator, '_create_google_form_phase') as mock_form:
                mock_form.return_value = mock_form_result
                with patch.object(workflow_orchestrator, '_mark_workflow_error') as mock_error:

                    # Act
                    result = await workflow_orchestrator.execute_assessment_to_form_workflow(
                        certification_profile_id=certification_profile_id,
                        user_id=user_id,
                        assessment_data=sample_assessment_data
                    )

                    # Assert
                    assert result["success"] is False
                    assert result["error"] == "Google Forms API quota exceeded"
                    mock_error.assert_called_once_with(
                        mock_workflow_execution.id,
                        "Google Forms API quota exceeded"
                    )

    def test_generate_form_title(self, workflow_orchestrator, sample_assessment_data):
        """Test form title generation from assessment data."""
        # Act
        title = workflow_orchestrator._generate_form_title(sample_assessment_data)

        # Assert
        assert "AWS Solutions Architect" in title
        assert "Assessment" in title

    def test_generate_form_description(self, workflow_orchestrator, sample_assessment_data):
        """Test form description generation from assessment data."""
        # Act
        description = workflow_orchestrator._generate_form_description(sample_assessment_data)

        # Assert
        assert "2 questions" in description
        assert "10 minutes" in description
        assert "best of your ability" in description

    def test_extract_answer_key(self, workflow_orchestrator, sample_assessment_data):
        """Test answer key extraction from assessment data."""
        # Act
        answer_key = workflow_orchestrator._extract_answer_key(sample_assessment_data)

        # Assert
        assert "q1" in answer_key
        assert "q2" in answer_key
        assert answer_key["q1"]["correct_answer"] == "B"
        assert answer_key["q2"]["correct_answer"] == "False"
        assert answer_key["q1"]["question_type"] == "multiple_choice"
        assert answer_key["q2"]["question_type"] == "true_false"

    @pytest.mark.asyncio
    async def test_get_workflow_status(self, workflow_orchestrator):
        """Test retrieving workflow status."""
        # Arrange
        workflow_id = uuid4()

        mock_workflow = MagicMock()
        mock_workflow.id = workflow_id
        mock_workflow.execution_status = WorkflowStatus.AWAITING_COMPLETION
        mock_workflow.current_step = "collect_responses"
        mock_workflow.created_at = datetime.utcnow()
        mock_workflow.updated_at = datetime.utcnow()
        mock_workflow.google_form_id = "test_form_123"
        mock_workflow.generated_content_urls = {"form_url": "https://forms.google.com/test"}
        mock_workflow.collected_responses = [{"response_id": "resp_1"}]
        mock_workflow.paused_at = None
        mock_workflow.resumed_at = None

        with patch('src.services.workflow_orchestrator.get_async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = mock_workflow

            # Act
            result = await workflow_orchestrator.get_workflow_status(workflow_id)

            # Assert
            assert result["success"] is True
            assert result["workflow_id"] == str(workflow_id)
            assert result["status"] == WorkflowStatus.AWAITING_COMPLETION
            assert result["current_step"] == "collect_responses"
            assert result["response_count"] == 1


class TestResponseIngestionService:
    """Test suite for response ingestion service."""

    @pytest_asyncio.fixture
    async def response_ingestion_service(self):
        """Create response ingestion service with mocked dependencies."""
        with patch('src.services.response_ingestion_service.GoogleFormsService') as mock_forms:
            with patch('src.services.response_ingestion_service.FormResponseProcessor') as mock_processor:
                service = ResponseIngestionService()
                yield service

    @pytest.fixture
    def sample_google_forms_responses(self):
        """Sample Google Forms API responses."""
        return [
            {
                "responseId": "resp_001",
                "respondentEmail": "student1@example.com",
                "lastSubmittedTime": "2024-01-01T12:00:00Z",
                "createTime": "2024-01-01T11:55:00Z",
                "answers": {
                    "q1": {
                        "textAnswers": {
                            "answers": [{"value": "B) Compute"}]
                        }
                    },
                    "q2": {
                        "textAnswers": {
                            "answers": [{"value": "False"}]
                        }
                    }
                }
            },
            {
                "responseId": "resp_002",
                "respondentEmail": "student2@example.com",
                "lastSubmittedTime": "2024-01-01T12:30:00Z",
                "createTime": "2024-01-01T12:25:00Z",
                "answers": {
                    "q1": {
                        "textAnswers": {
                            "answers": [{"value": "A) Storage"}]
                        }
                    },
                    "q2": {
                        "textAnswers": {
                            "answers": [{"value": "True"}]
                        }
                    }
                }
            }
        ]

    @pytest.fixture
    def mock_workflow_awaiting_completion(self):
        """Mock workflow in awaiting completion status."""
        workflow = MagicMock()
        workflow.id = uuid4()
        workflow.google_form_id = "test_form_123"
        workflow.execution_status = WorkflowStatus.AWAITING_COMPLETION
        workflow.collected_responses = []
        workflow.paused_at = datetime.utcnow() - timedelta(hours=1)
        return workflow

    def test_filter_new_responses(self, response_ingestion_service, sample_google_forms_responses):
        """Test filtering of new vs already processed responses."""
        # Arrange
        response_ingestion_service._processed_responses.add("resp_001")

        # Act
        new_responses = response_ingestion_service._filter_new_responses(sample_google_forms_responses)

        # Assert
        assert len(new_responses) == 1
        assert new_responses[0]["responseId"] == "resp_002"
        assert "resp_002" in response_ingestion_service._processed_responses

    def test_normalize_answers(self, response_ingestion_service):
        """Test normalization of Google Forms answer format."""
        # Arrange
        raw_answers = {
            "q1": {
                "textAnswers": {
                    "answers": [{"value": "B) Compute service"}]
                }
            },
            "q2": {
                "fileUploadAnswers": {
                    "answers": [{"fileId": "file_123"}]
                }
            },
            "q3": "Simple string answer"
        }

        # Act
        normalized = response_ingestion_service._normalize_answers(raw_answers)

        # Assert
        assert normalized["q1"] == "B) Compute service"
        assert normalized["q2"] == "FILE_UPLOAD"
        assert normalized["q3"] == "Simple string answer"

    def test_parse_timestamp(self, response_ingestion_service):
        """Test timestamp parsing from Google Forms format."""
        # Test cases
        test_cases = [
            ("2024-01-01T12:00:00Z", datetime(2024, 1, 1, 12, 0, 0)),
            ("2024-01-01T12:00:00+00:00", datetime(2024, 1, 1, 12, 0, 0)),
            ("invalid_timestamp", None),
            (None, None)
        ]

        for timestamp_str, expected in test_cases:
            result = response_ingestion_service._parse_timestamp(timestamp_str)
            if expected:
                assert result is not None
                assert result.replace(tzinfo=None) == expected
            else:
                assert result is None

    @pytest.mark.asyncio
    async def test_normalize_responses(
        self,
        response_ingestion_service,
        sample_google_forms_responses,
        mock_workflow_awaiting_completion
    ):
        """Test response normalization process."""
        # Act
        normalized = await response_ingestion_service._normalize_responses(
            sample_google_forms_responses,
            mock_workflow_awaiting_completion
        )

        # Assert
        assert len(normalized) == 2

        # Check first response
        resp1 = normalized[0]
        assert resp1["response_id"] == "resp_001"
        assert resp1["workflow_id"] == str(mock_workflow_awaiting_completion.id)
        assert resp1["respondent_email"] == "student1@example.com"
        assert resp1["answers"]["q1"] == "B) Compute"
        assert resp1["answers"]["q2"] == "False"
        assert "metadata" in resp1

        # Check second response
        resp2 = normalized[1]
        assert resp2["response_id"] == "resp_002"
        assert resp2["answers"]["q1"] == "A) Storage"
        assert resp2["answers"]["q2"] == "True"

    def test_should_timeout_and_proceed(self, response_ingestion_service, mock_workflow_awaiting_completion):
        """Test timeout evaluation for workflow progression."""
        # Test case 1: Recent pause - should not timeout
        mock_workflow_awaiting_completion.paused_at = datetime.utcnow() - timedelta(hours=1)
        result = response_ingestion_service._should_timeout_and_proceed(
            mock_workflow_awaiting_completion, 24
        )
        assert result is False

        # Test case 2: Old pause - should timeout
        mock_workflow_awaiting_completion.paused_at = datetime.utcnow() - timedelta(hours=25)
        result = response_ingestion_service._should_timeout_and_proceed(
            mock_workflow_awaiting_completion, 24
        )
        assert result is True

        # Test case 3: No pause time - should not timeout
        mock_workflow_awaiting_completion.paused_at = None
        result = response_ingestion_service._should_timeout_and_proceed(
            mock_workflow_awaiting_completion, 24
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_force_ingest_workflow_responses_success(
        self,
        response_ingestion_service,
        mock_workflow_awaiting_completion
    ):
        """Test manual response ingestion trigger."""
        # Arrange
        workflow_id = mock_workflow_awaiting_completion.id

        with patch('src.services.response_ingestion_service.get_async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = mock_workflow_awaiting_completion
            with patch.object(response_ingestion_service, '_process_workflow_responses') as mock_process:

                # Act
                result = await response_ingestion_service.force_ingest_workflow_responses(workflow_id)

                # Assert
                assert result["success"] is True
                assert result["workflow_id"] == str(workflow_id)
                mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_ingest_workflow_responses_not_found(self, response_ingestion_service):
        """Test manual ingestion for non-existent workflow."""
        # Arrange
        workflow_id = uuid4()

        with patch('src.services.response_ingestion_service.get_async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = None

            # Act
            result = await response_ingestion_service.force_ingest_workflow_responses(workflow_id)

            # Assert
            assert result["success"] is False
            assert "not found" in result["error"]


class TestWorkflowOrchestrationAPI:
    """Test suite for workflow orchestration API endpoints."""

    @pytest.fixture
    def sample_assessment_workflow_request(self):
        """Sample assessment workflow request data."""
        return {
            "certification_profile_id": str(uuid4()),
            "user_id": "test_user",
            "assessment_data": {
                "questions": [
                    {
                        "id": "q1",
                        "question_text": "Test question",
                        "question_type": "multiple_choice",
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": "A"
                    }
                ],
                "metadata": {
                    "certification_name": "Test Certification"
                }
            },
            "form_settings": {
                "collect_email": True,
                "require_login": False
            }
        }

    @pytest.mark.asyncio
    async def test_create_assessment_form_workflow_endpoint(
        self,
        sample_assessment_workflow_request
    ):
        """Test the assessment-to-form workflow endpoint."""
        # This would require FastAPI test client setup
        # For now, validate the request structure
        assert "certification_profile_id" in sample_assessment_workflow_request
        assert "assessment_data" in sample_assessment_workflow_request
        assert "questions" in sample_assessment_workflow_request["assessment_data"]

    def test_workflow_orchestration_integration_points(self):
        """Test integration points between orchestration components."""
        # Verify that all required services can be imported
        from src.services.workflow_orchestrator import WorkflowOrchestrator
        from src.services.response_ingestion_service import ResponseIngestionService
        from src.services.google_forms_service import GoogleFormsService
        from src.services.form_response_processor import FormResponseProcessor

        # Verify key methods exist
        orchestrator = WorkflowOrchestrator()
        assert hasattr(orchestrator, 'execute_assessment_to_form_workflow')
        assert hasattr(orchestrator, 'process_completed_responses')
        assert hasattr(orchestrator, 'get_workflow_status')

        ingestion = ResponseIngestionService()
        assert hasattr(ingestion, 'start_ingestion_worker')
        assert hasattr(ingestion, 'force_ingest_workflow_responses')
        assert hasattr(ingestion, 'get_ingestion_stats')


if __name__ == "__main__":
    pytest.main([__file__])