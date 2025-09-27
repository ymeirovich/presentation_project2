"""
Test-Driven Development (TDD) Test Suite for Phase 2: Google Forms Integration
Comprehensive test coverage for Google Forms service, assessment mapping, and response processing.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from typing import Dict, List

import httpx
from fastapi.testclient import TestClient
from googleapiclient.errors import HttpError

# Import components under test
from src.services.google_forms_service import GoogleFormsService
from src.services.assessment_forms_mapper import AssessmentFormsMapper
from src.services.form_response_processor import FormResponseProcessor
from src.services.google_auth_manager import GoogleAuthManager
from src.schemas.google_forms import (
    FormSettings,
    CreateFormRequest,
    AddQuestionsRequest,
    FormResponse,
    ProcessedFormResponse,
    AssessmentWorkflowRequest
)


class TestGoogleFormsService:
    """Test suite for Google Forms service functionality."""

    @pytest.fixture
    def mock_forms_service(self):
        """Mock Google Forms API service."""
        service = MagicMock()

        # Mock form creation
        service.forms().create().execute.return_value = {
            'formId': 'test_form_id_123',
            'info': {
                'title': 'AWS Assessment Form',
                'description': 'Comprehensive AWS certification assessment'
            },
            'responderUri': 'https://docs.google.com/forms/d/test_form_id_123/viewform',
            'items': []
        }

        # Mock batch update (for adding questions)
        service.forms().batchUpdate().execute.return_value = {
            'form': {
                'formId': 'test_form_id_123',
                'items': [
                    {
                        'itemId': 'question_1',
                        'title': 'What is AWS Lambda?',
                        'questionItem': {
                            'question': {
                                'choiceQuestion': {
                                    'type': 'RADIO',
                                    'options': [
                                        {'value': 'A) Storage service'},
                                        {'value': 'B) Compute service'},
                                        {'value': 'C) Database service'},
                                        {'value': 'D) Network service'}
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }

        # Mock responses retrieval
        service.forms().responses().list().execute.return_value = {
            'responses': [
                {
                    'responseId': 'response_123',
                    'createTime': '2024-01-01T12:00:00Z',
                    'lastSubmittedTime': '2024-01-01T12:05:00Z',
                    'respondentEmail': 'test@example.com',
                    'answers': {
                        'question_1': {
                            'textAnswers': {
                                'answers': [{'value': 'B) Compute service'}]
                            }
                        }
                    }
                }
            ]
        }

        return service

    @pytest.fixture
    def mock_drive_service(self):
        """Mock Google Drive API service."""
        service = MagicMock()

        # Mock file permissions update
        service.permissions().create().execute.return_value = {
            'id': 'permission_123'
        }

        # Mock file metadata update
        service.files().update().execute.return_value = {
            'id': 'test_form_id_123',
            'name': 'AWS Assessment Form'
        }

        return service

    @pytest.fixture
    def sample_assessment_data(self):
        """Sample assessment data for testing."""
        return {
            "assessment_id": str(uuid4()),
            "certification_profile_id": str(uuid4()),
            "questions": [
                {
                    "id": "q1",
                    "question_text": "What is the primary benefit of AWS Lambda?",
                    "question_type": "multiple_choice",
                    "options": [
                        "A) Low cost storage",
                        "B) Serverless computing",
                        "C) High availability",
                        "D) Data encryption"
                    ],
                    "correct_answer": "B",
                    "explanation": "AWS Lambda provides serverless computing capabilities.",
                    "domain": "Compute Services",
                    "difficulty": 0.6,
                    "time_limit_seconds": 90
                },
                {
                    "id": "q2",
                    "question_text": "True or False: S3 provides block storage.",
                    "question_type": "true_false",
                    "correct_answer": "False",
                    "explanation": "S3 provides object storage, not block storage.",
                    "domain": "Storage Services",
                    "difficulty": 0.4,
                    "time_limit_seconds": 60
                }
            ],
            "metadata": {
                "certification_name": "AWS Solutions Architect Associate",
                "total_questions": 2,
                "estimated_duration_minutes": 3
            }
        }

    @pytest.fixture
    async def google_forms_service(self, mock_forms_service, mock_drive_service):
        """Create Google Forms service with mocked dependencies."""
        with patch('src.services.google_forms_service.build') as mock_build:
            mock_build.side_effect = lambda service, version, credentials: {
                'forms': mock_forms_service,
                'drive': mock_drive_service
            }[service]

            with patch('src.services.google_forms_service.service_account'):
                service = GoogleFormsService()
                return service

    @pytest.mark.asyncio
    async def test_create_assessment_form(self, google_forms_service, sample_assessment_data):
        """Test Google Form creation from assessment data."""
        # Arrange
        form_title = "AWS Assessment Test Form"
        form_description = "Test assessment for AWS certification"
        settings = FormSettings(
            collect_email=True,
            require_login=True,
            show_progress_bar=True
        )

        # Act
        result = await google_forms_service.create_assessment_form(
            assessment_data=sample_assessment_data,
            form_title=form_title,
            form_description=form_description,
            settings=settings
        )

        # Assert
        assert result["success"] is True
        assert "form_id" in result
        assert result["form_id"] == "test_form_id_123"
        assert "form_url" in result
        assert result["form_url"].startswith("https://docs.google.com/forms/")
        assert result["form_title"] == form_title

    @pytest.mark.asyncio
    async def test_add_questions_to_form(self, google_forms_service, sample_assessment_data):
        """Test adding questions to existing form."""
        # Arrange
        form_id = "test_form_id_123"
        questions = sample_assessment_data["questions"]

        # Act
        result = await google_forms_service.add_questions_to_form(
            form_id=form_id,
            questions=questions,
            start_index=0
        )

        # Assert
        assert result["success"] is True
        assert result["form_id"] == form_id
        assert result["questions_added"] == len(questions)
        assert "updated_form" in result

    @pytest.mark.asyncio
    async def test_configure_form_settings(self, google_forms_service):
        """Test form settings and validation configuration."""
        # Arrange
        form_id = "test_form_id_123"
        settings = FormSettings(
            collect_email=True,
            require_login=True,
            allow_response_editing=False,
            shuffle_questions=True,
            show_progress_bar=True,
            confirmation_message="Thank you for completing the assessment!"
        )

        # Act
        result = await google_forms_service.configure_form_settings(
            form_id=form_id,
            settings=settings
        )

        # Assert
        assert result["success"] is True
        assert result["form_id"] == form_id
        assert result["settings_applied"]["collect_email"] is True
        assert result["settings_applied"]["require_login"] is True

    @pytest.mark.asyncio
    async def test_get_form_responses(self, google_forms_service):
        """Test form response retrieval and processing."""
        # Arrange
        form_id = "test_form_id_123"

        # Act
        result = await google_forms_service.get_form_responses(
            form_id=form_id,
            include_empty=False
        )

        # Assert
        assert result["success"] is True
        assert "responses" in result
        assert len(result["responses"]) > 0

        response = result["responses"][0]
        assert "response_id" in response
        assert "submitted_at" in response
        assert "answers" in response

    @pytest.mark.asyncio
    async def test_error_handling_invalid_form_id(self, google_forms_service, sample_assessment_data):
        """Test error handling for invalid form operations."""
        # Arrange - Mock API error
        with patch.object(google_forms_service.forms_service.forms(), 'create') as mock_create:
            mock_create().execute.side_effect = HttpError(
                resp=Mock(status=404),
                content=b'{"error": {"message": "Form not found"}}'
            )

            # Act & Assert
            with pytest.raises(Exception):  # Should raise appropriate exception
                await google_forms_service.create_assessment_form(
                    assessment_data=sample_assessment_data,
                    form_title="Test Form"
                )

    @pytest.mark.asyncio
    async def test_rate_limiting_retry_logic(self, google_forms_service, sample_assessment_data):
        """Test rate limiting and retry logic for Google API calls."""
        # Arrange - Mock rate limit error then success
        with patch.object(google_forms_service.forms_service.forms(), 'create') as mock_create:
            # First call returns rate limit error
            rate_limit_error = HttpError(
                resp=Mock(status=429),
                content=b'{"error": {"message": "Rate limit exceeded"}}'
            )

            # Second call succeeds
            success_response = {
                'formId': 'retry_form_123',
                'info': {'title': 'Retry Test Form'},
                'responderUri': 'https://docs.google.com/forms/d/retry_form_123/viewform'
            }

            mock_create().execute.side_effect = [rate_limit_error, success_response]

            # Act
            with patch('asyncio.sleep'):  # Mock sleep to speed up test
                result = await google_forms_service.create_assessment_form(
                    assessment_data=sample_assessment_data,
                    form_title="Retry Test Form"
                )

            # Assert
            assert result["success"] is True
            assert result["form_id"] == "retry_form_123"
            assert mock_create().execute.call_count == 2  # Retry was attempted


class TestAssessmentFormsMapper:
    """Test suite for assessment to forms mapping."""

    @pytest.fixture
    def assessment_forms_mapper(self):
        """Create assessment forms mapper instance."""
        return AssessmentFormsMapper()

    @pytest.fixture
    def sample_questions(self):
        """Sample questions for mapping tests."""
        return [
            {
                "id": "q1",
                "question_text": "Which AWS service provides managed NoSQL database?",
                "question_type": "multiple_choice",
                "options": ["A) RDS", "B) DynamoDB", "C) S3", "D) EC2"],
                "correct_answer": "B",
                "explanation": "DynamoDB is AWS's managed NoSQL database service.",
                "domain": "Database Services",
                "time_limit_seconds": 90
            },
            {
                "id": "q2",
                "question_text": "AWS Lambda supports serverless computing.",
                "question_type": "true_false",
                "correct_answer": "True",
                "explanation": "AWS Lambda is a serverless compute service.",
                "domain": "Compute Services",
                "time_limit_seconds": 60
            },
            {
                "id": "q3",
                "question_text": "Describe how you would design a fault-tolerant architecture for a web application using AWS services. Include specific services and explain your reasoning.",
                "question_type": "scenario",
                "correct_answer": "Sample answer involving ELB, Auto Scaling, Multi-AZ RDS, etc.",
                "explanation": "A comprehensive fault-tolerant architecture should include...",
                "domain": "Architecture Design",
                "time_limit_seconds": 300
            }
        ]

    def test_multiple_choice_mapping(self, assessment_forms_mapper, sample_questions):
        """Test multiple choice question mapping."""
        # Arrange
        mc_question = sample_questions[0]

        # Act
        form_item = assessment_forms_mapper._create_multiple_choice_item(mc_question)

        # Assert
        assert form_item["title"] == mc_question["question_text"]
        assert "questionItem" in form_item
        assert form_item["questionItem"]["question"]["required"] is True

        choice_question = form_item["questionItem"]["question"]["choiceQuestion"]
        assert choice_question["type"] == "RADIO"
        assert len(choice_question["options"]) == 4

        # Verify options are correctly mapped
        expected_options = ["A) RDS", "B) DynamoDB", "C) S3", "D) EC2"]
        actual_options = [opt["value"] for opt in choice_question["options"]]
        assert actual_options == expected_options

    def test_true_false_mapping(self, assessment_forms_mapper, sample_questions):
        """Test true/false question mapping."""
        # Arrange
        tf_question = sample_questions[1]

        # Act
        form_item = assessment_forms_mapper._create_true_false_item(tf_question)

        # Assert
        assert form_item["title"] == tf_question["question_text"]

        choice_question = form_item["questionItem"]["question"]["choiceQuestion"]
        assert choice_question["type"] == "RADIO"
        assert len(choice_question["options"]) == 2

        # Verify True/False options
        option_values = [opt["value"] for opt in choice_question["options"]]
        assert "True" in option_values
        assert "False" in option_values

    def test_scenario_mapping(self, assessment_forms_mapper, sample_questions):
        """Test scenario question mapping."""
        # Arrange
        scenario_question = sample_questions[2]

        # Act
        form_item = assessment_forms_mapper._create_paragraph_item(scenario_question)

        # Assert
        assert form_item["title"] == scenario_question["question_text"]
        assert "questionItem" in form_item

        text_question = form_item["questionItem"]["question"]["textQuestion"]
        assert text_question["paragraph"] is True  # Paragraph text for long answers

    def test_form_metadata_generation(self, assessment_forms_mapper):
        """Test form title and description generation."""
        # Arrange
        assessment_data = {
            "metadata": {
                "certification_name": "AWS Solutions Architect Associate",
                "certification_version": "SAA-C03",
                "total_questions": 10,
                "estimated_duration_minutes": 45
            },
            "questions": []
        }

        # Act
        title = assessment_forms_mapper._generate_form_title(assessment_data)
        description = assessment_forms_mapper._generate_form_description(assessment_data)

        # Assert
        assert "AWS Solutions Architect Associate" in title
        assert "SAA-C03" in title
        assert "10 questions" in description
        assert "45 minutes" in description

    def test_complete_assessment_mapping(self, assessment_forms_mapper, sample_questions):
        """Test complete assessment to form mapping."""
        # Arrange
        assessment_data = {
            "assessment_id": str(uuid4()),
            "questions": sample_questions,
            "metadata": {
                "certification_name": "AWS Solutions Architect Associate",
                "total_questions": len(sample_questions)
            }
        }

        # Act
        form_structure = assessment_forms_mapper.map_assessment_to_form(assessment_data)

        # Assert
        assert "info" in form_structure
        assert "items" in form_structure
        assert len(form_structure["items"]) == len(sample_questions)

        # Verify each question type is mapped correctly
        items = form_structure["items"]
        assert "choiceQuestion" in items[0]["questionItem"]["question"]  # Multiple choice
        assert "choiceQuestion" in items[1]["questionItem"]["question"]  # True/false
        assert "textQuestion" in items[2]["questionItem"]["question"]    # Scenario

    def test_unsupported_question_type(self, assessment_forms_mapper):
        """Test handling of unsupported question types."""
        # Arrange
        unsupported_question = {
            "question_text": "Test question",
            "question_type": "fill_in_blank",  # Unsupported type
            "correct_answer": "test"
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported question type"):
            assessment_forms_mapper._map_question_to_form_item(unsupported_question)


class TestFormResponseProcessor:
    """Test suite for form response processing."""

    @pytest.fixture
    def form_response_processor(self):
        """Create form response processor instance."""
        return FormResponseProcessor()

    @pytest.fixture
    def sample_form_responses(self):
        """Sample form responses for testing."""
        return [
            {
                "response_id": "resp_001",
                "respondent_email": "student1@example.com",
                "submitted_at": "2024-01-01T12:00:00Z",
                "answers": {
                    "q1": "B) DynamoDB",
                    "q2": "True",
                    "q3": "I would use ELB for load balancing, Auto Scaling for elasticity..."
                },
                "completion_time_seconds": 180
            },
            {
                "response_id": "resp_002",
                "respondent_email": "student2@example.com",
                "submitted_at": "2024-01-01T12:30:00Z",
                "answers": {
                    "q1": "A) RDS",  # Incorrect
                    "q2": "True",
                    "q3": "Use multiple EC2 instances across different AZs..."
                },
                "completion_time_seconds": 240
            }
        ]

    @pytest.fixture
    def sample_answer_key(self):
        """Sample answer key for scoring."""
        return {
            "q1": {
                "correct_answer": "B) DynamoDB",
                "points": 1,
                "domain": "Database Services"
            },
            "q2": {
                "correct_answer": "True",
                "points": 1,
                "domain": "Compute Services"
            },
            "q3": {
                "correct_answer": "scenario_rubric",
                "points": 3,
                "domain": "Architecture Design",
                "rubric": {
                    "keywords": ["load balancer", "auto scaling", "multi-az", "fault tolerant"],
                    "partial_credit": True
                }
            }
        }

    @pytest.mark.asyncio
    async def test_response_scoring(self, form_response_processor, sample_form_responses, sample_answer_key):
        """Test assessment scoring from form responses."""
        # Arrange
        responses = sample_form_responses
        answer_key = sample_answer_key

        # Act
        scoring_results = await form_response_processor.calculate_assessment_score(
            responses=responses,
            answer_key=answer_key
        )

        # Assert
        assert "results" in scoring_results
        assert len(scoring_results["results"]) == len(responses)

        # Check first response (all correct)
        result1 = scoring_results["results"][0]
        assert result1["response_id"] == "resp_001"
        assert result1["total_score"] >= 4  # Should get points for all questions
        assert result1["percentage"] >= 80   # High percentage

        # Check second response (one incorrect)
        result2 = scoring_results["results"][1]
        assert result2["response_id"] == "resp_002"
        assert result2["total_score"] < result1["total_score"]  # Lower score

    @pytest.mark.asyncio
    async def test_scenario_question_scoring(self, form_response_processor):
        """Test scenario question scoring with rubric."""
        # Arrange
        scenario_response = "I would implement load balancing with ELB, use Auto Scaling groups for elasticity, deploy across multiple AZs for fault tolerance, and use RDS Multi-AZ for database redundancy."

        rubric = {
            "keywords": ["load balancer", "auto scaling", "multi-az", "fault tolerant"],
            "partial_credit": True,
            "max_points": 3
        }

        # Act
        score = await form_response_processor._score_scenario_response(
            response=scenario_response,
            rubric=rubric
        )

        # Assert
        assert score["points"] > 0
        assert score["points"] <= 3
        assert "matched_keywords" in score
        assert len(score["matched_keywords"]) >= 2  # Should match several keywords

    @pytest.mark.asyncio
    async def test_performance_analytics(self, form_response_processor, sample_form_responses, sample_answer_key):
        """Test response pattern analysis."""
        # Arrange
        assessment_metadata = {
            "domains": ["Database Services", "Compute Services", "Architecture Design"],
            "difficulty_levels": {"q1": 0.6, "q2": 0.4, "q3": 0.8},
            "total_questions": 3
        }

        # Act
        analytics = await form_response_processor.analyze_response_patterns(
            responses=sample_form_responses,
            assessment_metadata=assessment_metadata
        )

        # Assert
        assert "domain_performance" in analytics
        assert "question_difficulty_analysis" in analytics
        assert "completion_time_stats" in analytics
        assert "common_mistakes" in analytics

        # Check domain performance tracking
        domain_perf = analytics["domain_performance"]
        assert "Database Services" in domain_perf
        assert "success_rate" in domain_perf["Database Services"]

    @pytest.mark.asyncio
    async def test_feedback_generation(self, form_response_processor):
        """Test personalized feedback generation."""
        # Arrange
        user_response = {
            "response_id": "resp_001",
            "answers": {"q1": "B) DynamoDB", "q2": "True"},
            "scores": {"q1": 1, "q2": 1},
            "total_score": 2,
            "percentage": 100
        }

        assessment_data = {
            "questions": [
                {
                    "id": "q1",
                    "domain": "Database Services",
                    "explanation": "DynamoDB is AWS's managed NoSQL database service."
                },
                {
                    "id": "q2",
                    "domain": "Compute Services",
                    "explanation": "AWS Lambda provides serverless computing."
                }
            ]
        }

        performance_analytics = {
            "strengths": ["Database Services"],
            "weaknesses": [],
            "recommendations": ["Continue studying advanced database features"]
        }

        # Act
        feedback = await form_response_processor.generate_feedback_report(
            user_responses=user_response,
            assessment_data=assessment_data,
            performance_analytics=performance_analytics
        )

        # Assert
        assert "overall_performance" in feedback
        assert "strengths" in feedback
        assert "areas_for_improvement" in feedback
        assert "recommendations" in feedback
        assert feedback["overall_performance"]["percentage"] == 100

    @pytest.mark.asyncio
    async def test_bulk_response_processing(self, form_response_processor, sample_answer_key):
        """Test processing large numbers of responses efficiently."""
        # Arrange - Create many responses
        bulk_responses = []
        for i in range(100):
            response = {
                "response_id": f"resp_{i:03d}",
                "respondent_email": f"student{i}@example.com",
                "answers": {
                    "q1": "B) DynamoDB" if i % 2 == 0 else "A) RDS",  # 50% correct
                    "q2": "True"
                },
                "completion_time_seconds": 120 + (i % 60)  # Varying completion times
            }
            bulk_responses.append(response)

        # Act
        import time
        start_time = time.time()

        results = await form_response_processor.calculate_assessment_score(
            responses=bulk_responses,
            answer_key=sample_answer_key
        )

        processing_time = time.time() - start_time

        # Assert
        assert len(results["results"]) == 100
        assert processing_time < 5.0  # Should process 100 responses quickly

        # Verify statistics
        scores = [r["percentage"] for r in results["results"]]
        average_score = sum(scores) / len(scores)
        assert 40 <= average_score <= 80  # Should be around 50% due to setup


class TestGoogleAuthManager:
    """Test suite for Google authentication management."""

    @pytest.fixture
    def mock_service_account_credentials(self):
        """Mock service account credentials."""
        with patch('google.auth.service_account.Credentials') as mock_creds:
            mock_instance = MagicMock()
            mock_instance.valid = True
            mock_instance.expired = False
            mock_creds.from_service_account_file.return_value = mock_instance
            return mock_creds

    @pytest.fixture
    def google_auth_manager(self, mock_service_account_credentials):
        """Create Google auth manager with mocked credentials."""
        with patch('src.services.google_auth_manager.settings') as mock_settings:
            mock_settings.google_application_credentials = "/path/to/service-account.json"
            return GoogleAuthManager()

    def test_get_service_credentials(self, google_auth_manager, mock_service_account_credentials):
        """Test service account credentials retrieval."""
        # Act
        credentials = google_auth_manager.get_service_credentials()

        # Assert
        assert credentials is not None
        assert credentials.valid is True
        mock_service_account_credentials.from_service_account_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_permissions(self, google_auth_manager):
        """Test API permissions validation."""
        # Arrange
        mock_credentials = MagicMock()

        with patch('googleapiclient.discovery.build') as mock_build:
            # Mock successful API calls
            mock_forms_service = MagicMock()
            mock_drive_service = MagicMock()

            mock_forms_service.forms().create().execute.return_value = {
                'formId': 'test_permission_form'
            }
            mock_drive_service.files().delete().execute.return_value = {}

            mock_build.side_effect = lambda service, version, credentials: {
                'forms': mock_forms_service,
                'drive': mock_drive_service
            }[service]

            # Act
            result = google_auth_manager.validate_permissions(mock_credentials)

            # Assert
            assert result["valid"] is True
            assert "message" in result

    def test_permission_validation_failure(self, google_auth_manager):
        """Test permission validation with insufficient permissions."""
        # Arrange
        mock_credentials = MagicMock()

        with patch('googleapiclient.discovery.build') as mock_build:
            # Mock permission error
            mock_build.side_effect = HttpError(
                resp=Mock(status=403),
                content=b'{"error": {"message": "Insufficient permissions"}}'
            )

            # Act
            result = google_auth_manager.validate_permissions(mock_credentials)

            # Assert
            assert result["valid"] is False
            assert "error" in result


class TestGoogleFormsAPIEndpoints:
    """Test suite for Google Forms API endpoints."""

    @pytest.fixture
    def mock_google_forms_service(self):
        """Mock Google Forms service for API testing."""
        service = AsyncMock()

        # Mock successful form creation
        service.create_assessment_form.return_value = {
            "success": True,
            "form_id": "api_test_form_123",
            "form_url": "https://docs.google.com/forms/d/api_test_form_123/viewform",
            "form_title": "API Test Form"
        }

        # Mock successful question addition
        service.add_questions_to_form.return_value = {
            "success": True,
            "form_id": "api_test_form_123",
            "questions_added": 2
        }

        # Mock successful response retrieval
        service.get_form_responses.return_value = {
            "success": True,
            "responses": [
                {
                    "response_id": "api_resp_001",
                    "answers": {"q1": "Test answer"}
                }
            ]
        }

        return service

    @pytest.fixture
    def client(self, mock_google_forms_service):
        """Create test client with mocked Google Forms service."""
        from src.service.app import create_app

        app = create_app()

        # Patch the Google Forms service
        with patch('src.service.api.v1.endpoints.google_forms.google_forms_service', mock_google_forms_service):
            yield TestClient(app)

    def test_create_form_endpoint(self, client):
        """Test form creation endpoint."""
        # Arrange
        request_data = {
            "assessment_id": str(uuid4()),
            "form_title": "API Test Assessment",
            "form_description": "Test form created via API",
            "certification_profile_id": str(uuid4()),
            "settings": {
                "collect_email": True,
                "require_login": True,
                "show_progress_bar": True
            }
        }

        # Act
        response = client.post("/api/v1/google-forms/create", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "form_id" in data
        assert "form_url" in data

    def test_add_questions_endpoint(self, client):
        """Test adding questions endpoint."""
        # Arrange
        form_id = "test_form_123"
        request_data = {
            "questions": [
                {
                    "question_text": "What is AWS?",
                    "question_type": "multiple_choice",
                    "options": ["A) Cloud platform", "B) Database", "C) Server", "D) Network"]
                }
            ],
            "start_index": 0
        }

        # Act
        response = client.post(f"/api/v1/google-forms/{form_id}/questions", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["questions_added"] > 0

    def test_get_responses_endpoint(self, client):
        """Test response retrieval endpoint."""
        # Arrange
        form_id = "test_form_123"

        # Act
        response = client.get(f"/api/v1/google-forms/{form_id}/responses")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "responses" in data

    def test_workflow_endpoint(self, client, mock_google_forms_service):
        """Test complete workflow endpoint."""
        # Arrange
        request_data = {
            "certification_profile_id": str(uuid4()),
            "assessment_parameters": {
                "question_count": 10,
                "difficulty_level": "intermediate"
            },
            "workflow_name": "API Test Workflow"
        }

        # Mock the workflow service
        with patch('src.service.api.v1.endpoints.workflows.assessment_engine') as mock_engine:
            mock_engine.generate_comprehensive_assessment.return_value = {
                "success": True,
                "assessment_id": str(uuid4()),
                "questions": [{"question_text": "Test question"}]
            }

            # Act
            response = client.post("/api/v1/workflows/assessment-to-form", json=request_data)

            # Assert
            assert response.status_code == 200 or response.status_code == 201
            # Further assertions would depend on actual implementation


class TestErrorHandlingAndResilience:
    """Test suite for error handling and system resilience."""

    @pytest.mark.asyncio
    async def test_google_api_rate_limit_handling(self):
        """Test handling of Google API rate limits."""
        from src.services.google_forms_service import GoogleAPIErrorHandler

        error_handler = GoogleAPIErrorHandler()

        # Mock API call that hits rate limit then succeeds
        call_count = 0
        async def mock_api_call():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise HttpError(
                    resp=Mock(status=429),
                    content=b'{"error": {"message": "Rate limit exceeded"}}'
                )
            return {"success": True, "data": "test"}

        # Act
        with patch('asyncio.sleep'):  # Mock sleep for faster testing
            result = await error_handler.execute_with_retry(mock_api_call)

        # Assert
        assert result["success"] is True
        assert call_count == 2  # Should have retried once

    @pytest.mark.asyncio
    async def test_form_creation_input_validation(self):
        """Test input validation for form creation."""
        from src.services.google_forms_service import FormCreationValidator

        validator = FormCreationValidator()

        # Test invalid assessment data
        invalid_data = {
            "questions": [],  # Empty questions
            "form_title": "A" * 400  # Too long title
        }

        # Act & Assert
        with pytest.raises(Exception):  # Should raise validation error
            validator.validate_assessment_data(invalid_data)

    @pytest.mark.asyncio
    async def test_concurrent_form_operations(self):
        """Test concurrent form creation and management."""
        # This test would verify that multiple form operations
        # can be handled concurrently without conflicts
        pass  # Placeholder for concurrent operation tests


class TestPerformanceAndScaling:
    """Test suite for performance and scaling requirements."""

    @pytest.mark.asyncio
    async def test_large_form_creation_performance(self):
        """Test performance with forms containing many questions."""
        # Create assessment with 100 questions
        large_assessment = {
            "assessment_id": str(uuid4()),
            "questions": [
                {
                    "id": f"q{i}",
                    "question_text": f"Question {i}: What is AWS service {i}?",
                    "question_type": "multiple_choice",
                    "options": [f"A) Option {i}A", f"B) Option {i}B", f"C) Option {i}C", f"D) Option {i}D"],
                    "correct_answer": "A"
                }
                for i in range(100)
            ]
        }

        # Test should verify that large forms can be created efficiently
        # and within reasonable time limits
        pass  # Placeholder for performance tests

    @pytest.mark.asyncio
    async def test_response_processing_scalability(self):
        """Test response processing with large numbers of responses."""
        # Test processing 1000+ responses efficiently
        pass  # Placeholder for scalability tests


# Test Configuration
pytest_plugins = ['pytest_asyncio']

# Mock Google API credentials for testing
import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/path/to/test-service-account.json"
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
os.environ["TESTING"] = "1"

if __name__ == "__main__":
    # Run specific test classes
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ])