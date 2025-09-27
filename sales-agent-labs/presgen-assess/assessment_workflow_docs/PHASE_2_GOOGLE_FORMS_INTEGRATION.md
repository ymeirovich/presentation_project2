# Phase 2: Google Forms Integration & Assessment Delivery

## Overview
**Phase 2** implements dynamic Google Forms creation and management for assessment delivery, building on Phase 1's assessment generation capabilities to create comprehensive end-to-end assessment workflows.

## Architecture Components

### 1. Google Forms Service (`src/services/google_forms_service.py`)
Comprehensive Google Forms API integration for dynamic form creation and management.

#### Key Features:
- **Dynamic Form Generation**: Create forms from assessment data
- **Question Type Mapping**: Convert assessment questions to Forms format
- **Response Collection**: Real-time response gathering and analysis
- **Form Management**: Update, duplicate, and version control forms

#### Core Implementation:
```python
class GoogleFormsService:
    """Service for Google Forms API integration and management."""

    def __init__(self):
        """Initialize Google Forms service with authentication."""
        self.credentials = self._get_service_credentials()
        self.forms_service = build('forms', 'v1', credentials=self.credentials)
        self.drive_service = build('drive', 'v3', credentials=self.credentials)

    async def create_assessment_form(
        self,
        assessment_data: Dict,
        form_title: str,
        form_description: str = "",
        settings: Optional[FormSettings] = None
    ) -> Dict:
        """Create Google Form from assessment data."""

    async def add_questions_to_form(
        self,
        form_id: str,
        questions: List[Dict],
        start_index: int = 0
    ) -> Dict:
        """Add assessment questions to existing form."""

    async def configure_form_settings(
        self,
        form_id: str,
        settings: FormSettings
    ) -> Dict:
        """Configure form collection and validation settings."""

    async def get_form_responses(
        self,
        form_id: str,
        include_empty: bool = False
    ) -> Dict:
        """Retrieve and process form responses."""
```

### 2. Assessment-to-Forms Mapper (`src/services/assessment_forms_mapper.py`)
Intelligent mapping between assessment data structures and Google Forms format.

#### Core Mapping Logic:
```python
class AssessmentFormsMapper:
    """Maps assessment data to Google Forms structure."""

    def map_assessment_to_form(self, assessment_data: Dict) -> Dict:
        """Convert assessment to Google Forms JSON structure."""

        form_structure = {
            "info": {
                "title": self._generate_form_title(assessment_data),
                "description": self._generate_form_description(assessment_data)
            },
            "items": []
        }

        for question in assessment_data["questions"]:
            form_item = self._map_question_to_form_item(question)
            form_structure["items"].append(form_item)

        return form_structure

    def _map_question_to_form_item(self, question: Dict) -> Dict:
        """Map individual question to Google Forms item."""
        question_type = question.get("question_type", "multiple_choice")

        if question_type == "multiple_choice":
            return self._create_multiple_choice_item(question)
        elif question_type == "true_false":
            return self._create_true_false_item(question)
        elif question_type == "scenario":
            return self._create_paragraph_item(question)
        else:
            raise ValueError(f"Unsupported question type: {question_type}")

    def _create_multiple_choice_item(self, question: Dict) -> Dict:
        """Create multiple choice Google Forms item."""
        options = []
        for option_text in question["options"]:
            options.append({
                "value": option_text
            })

        return {
            "title": question["question_text"],
            "description": f"Time limit: {question.get('time_limit_seconds', 120)} seconds",
            "questionItem": {
                "question": {
                    "required": True,
                    "choiceQuestion": {
                        "type": "RADIO",
                        "options": options
                    }
                }
            }
        }
```

### 3. Form Response Processing (`src/services/form_response_processor.py`)
Real-time processing and analysis of Google Forms responses.

#### Response Analysis Features:
- **Answer Validation**: Check responses against correct answers
- **Scoring Calculation**: Generate assessment scores and feedback
- **Performance Analytics**: Track response patterns and timing
- **Gap Analysis**: Identify knowledge gaps from response data

```python
class FormResponseProcessor:
    """Processes and analyzes Google Forms responses."""

    async def process_form_responses(
        self,
        form_id: str,
        assessment_data: Dict
    ) -> Dict:
        """Process responses and generate analysis."""

    async def calculate_assessment_score(
        self,
        responses: List[Dict],
        answer_key: Dict
    ) -> Dict:
        """Calculate comprehensive assessment scores."""

    async def analyze_response_patterns(
        self,
        responses: List[Dict],
        assessment_metadata: Dict
    ) -> Dict:
        """Analyze response patterns for insights."""

    async def generate_feedback_report(
        self,
        user_responses: Dict,
        assessment_data: Dict,
        performance_analytics: Dict
    ) -> Dict:
        """Generate personalized feedback report."""
```

### 4. Google APIs Authentication (`src/services/google_auth_manager.py`)
Centralized authentication management for Google API services.

#### Authentication Features:
- **Service Account Management**: Secure credential handling
- **OAuth Flow Integration**: User authentication when required
- **Token Refresh**: Automatic credential renewal
- **Permission Validation**: Scope verification and error handling

```python
class GoogleAuthManager:
    """Centralized Google APIs authentication management."""

    def __init__(self):
        """Initialize authentication manager."""
        self.service_account_path = settings.google_application_credentials
        self.scopes = [
            'https://www.googleapis.com/auth/forms.body',
            'https://www.googleapis.com/auth/forms.responses.readonly',
            'https://www.googleapis.com/auth/drive.file'
        ]

    def get_service_credentials(self) -> Credentials:
        """Get authenticated service credentials."""
        credentials = service_account.Credentials.from_service_account_file(
            self.service_account_path,
            scopes=self.scopes
        )
        return credentials

    def validate_permissions(self, credentials: Credentials) -> Dict:
        """Validate required API permissions."""
        try:
            # Test Forms API access
            forms_service = build('forms', 'v1', credentials=credentials)
            test_form = forms_service.forms().create(body={
                "info": {"title": "Permission Test Form"}
            }).execute()

            # Clean up test form
            drive_service = build('drive', 'v3', credentials=credentials)
            drive_service.files().delete(fileId=test_form['formId']).execute()

            return {"valid": True, "message": "All permissions verified"}

        except Exception as e:
            return {"valid": False, "error": str(e)}
```

## API Endpoints (`src/service/api/v1/endpoints/google_forms.py`)

### Google Forms Management Endpoints:

#### 1. Create Assessment Form
```
POST /api/v1/google-forms/create
```
**Purpose**: Create Google Form from assessment data
**Request Model**: `CreateFormRequest`
**Response**: Form ID, URL, and metadata

#### 2. Add Questions to Form
```
POST /api/v1/google-forms/{form_id}/questions
```
**Purpose**: Add questions to existing form
**Request Model**: `AddQuestionsRequest`
**Response**: Updated form structure

#### 3. Configure Form Settings
```
PUT /api/v1/google-forms/{form_id}/settings
```
**Purpose**: Configure form collection and validation settings
**Request Model**: `FormSettingsRequest`
**Response**: Updated form configuration

#### 4. Get Form Responses
```
GET /api/v1/google-forms/{form_id}/responses
```
**Purpose**: Retrieve and process form responses
**Query Parameters**: `include_empty`, `from_date`, `to_date`
**Response**: Processed response data with analysis

#### 5. Process Assessment Results
```
POST /api/v1/google-forms/{form_id}/process-results
```
**Purpose**: Generate assessment results and feedback
**Request Model**: `ProcessResultsRequest`
**Response**: Scored results with performance analytics

### Integration Endpoints:

#### 6. Generate Complete Assessment Workflow
```
POST /api/v1/workflows/assessment-to-form
```
**Purpose**: End-to-end assessment generation and form creation
**Request Model**: `AssessmentWorkflowRequest`
**Response**: Complete workflow with form URL and tracking ID

## Data Models (`src/schemas/google_forms.py`)

### Core Data Structures:

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime

class FormSettings(BaseModel):
    """Google Forms configuration settings."""
    collect_email: bool = Field(default=True, description="Collect respondent email")
    allow_response_editing: bool = Field(default=False, description="Allow editing responses")
    require_login: bool = Field(default=True, description="Require Google account login")
    shuffle_questions: bool = Field(default=False, description="Randomize question order")
    show_progress_bar: bool = Field(default=True, description="Display progress indicator")
    confirmation_message: Optional[str] = Field(default=None, description="Custom confirmation message")

class CreateFormRequest(BaseModel):
    """Request to create Google Form from assessment."""
    assessment_id: UUID = Field(..., description="Assessment ID from Phase 1")
    form_title: str = Field(..., description="Form title")
    form_description: Optional[str] = Field(default="", description="Form description")
    settings: Optional[FormSettings] = Field(default=None, description="Form configuration")
    certification_profile_id: UUID = Field(..., description="Associated certification profile")

class AddQuestionsRequest(BaseModel):
    """Request to add questions to existing form."""
    questions: List[Dict] = Field(..., description="Questions to add")
    start_index: int = Field(default=0, description="Starting position for questions")
    preserve_order: bool = Field(default=True, description="Maintain question order")

class FormResponse(BaseModel):
    """Individual form response data."""
    response_id: str = Field(..., description="Google Forms response ID")
    respondent_email: Optional[str] = Field(default=None, description="Respondent email")
    submitted_at: datetime = Field(..., description="Response submission timestamp")
    answers: Dict[str, str] = Field(..., description="Question ID to answer mapping")
    completion_time_seconds: Optional[int] = Field(default=None, description="Time to complete")

class ProcessedFormResponse(BaseModel):
    """Processed and analyzed form response."""
    response: FormResponse = Field(..., description="Original response data")
    score: float = Field(..., description="Calculated assessment score")
    correct_answers: int = Field(..., description="Number of correct answers")
    total_questions: int = Field(..., description="Total number of questions")
    performance_by_domain: Dict[str, float] = Field(..., description="Domain-specific performance")
    feedback: str = Field(..., description="Generated feedback text")

class AssessmentWorkflowRequest(BaseModel):
    """Complete assessment workflow request."""
    certification_profile_id: UUID = Field(..., description="Certification profile")
    assessment_parameters: Dict = Field(..., description="Assessment generation parameters")
    form_settings: Optional[FormSettings] = Field(default=None, description="Form configuration")
    workflow_name: str = Field(..., description="Workflow identifier")
```

## Test-Driven Development (TDD) Framework

### 1. Unit Tests (`tests/test_phase2_google_forms.py`)

#### Core Test Coverage:
```python
class TestGoogleFormsService:
    """Test suite for Google Forms service functionality."""

    @pytest.fixture
    def mock_forms_service(self):
        """Mock Google Forms API service."""
        service = MagicMock()
        service.forms().create().execute.return_value = {
            'formId': 'test_form_id_123',
            'info': {'title': 'Test Assessment Form'},
            'responderUri': 'https://docs.google.com/forms/d/test_form_id_123/viewform'
        }
        return service

    @pytest.mark.asyncio
    async def test_create_assessment_form(self, google_forms_service, sample_assessment_data):
        """Test Google Form creation from assessment data."""

    @pytest.mark.asyncio
    async def test_add_questions_to_form(self, google_forms_service):
        """Test adding questions to existing form."""

    @pytest.mark.asyncio
    async def test_form_settings_configuration(self, google_forms_service):
        """Test form settings and validation configuration."""

    @pytest.mark.asyncio
    async def test_response_collection(self, google_forms_service):
        """Test form response retrieval and processing."""

class TestAssessmentFormsMapper:
    """Test suite for assessment to forms mapping."""

    def test_multiple_choice_mapping(self, assessment_forms_mapper):
        """Test multiple choice question mapping."""

    def test_true_false_mapping(self, assessment_forms_mapper):
        """Test true/false question mapping."""

    def test_scenario_mapping(self, assessment_forms_mapper):
        """Test scenario question mapping."""

    def test_form_metadata_generation(self, assessment_forms_mapper):
        """Test form title and description generation."""

class TestFormResponseProcessor:
    """Test suite for form response processing."""

    @pytest.mark.asyncio
    async def test_response_scoring(self, form_response_processor):
        """Test assessment scoring from form responses."""

    @pytest.mark.asyncio
    async def test_performance_analytics(self, form_response_processor):
        """Test response pattern analysis."""

    @pytest.mark.asyncio
    async def test_feedback_generation(self, form_response_processor):
        """Test personalized feedback generation."""
```

### 2. Integration Tests (`tests/test_phase2_integration.py`)

#### End-to-End Workflow Testing:
```python
class TestPhase2Integration:
    """Integration tests for Phase 2 Google Forms workflow."""

    @pytest.mark.asyncio
    async def test_assessment_to_form_workflow(self):
        """Test complete assessment to form creation workflow."""

    @pytest.mark.asyncio
    async def test_google_apis_authentication(self):
        """Test Google APIs authentication and permissions."""

    @pytest.mark.asyncio
    async def test_form_response_processing_pipeline(self):
        """Test complete response processing pipeline."""

    @pytest.mark.asyncio
    async def test_cross_phase_integration(self):
        """Test integration between Phase 1 and Phase 2."""
```

### 3. API Tests (`tests/test_google_forms_api.py`)

#### API Endpoint Testing:
```python
class TestGoogleFormsAPI:
    """Test suite for Google Forms API endpoints."""

    @pytest.mark.asyncio
    async def test_create_form_endpoint(self, test_client):
        """Test form creation endpoint."""

    @pytest.mark.asyncio
    async def test_add_questions_endpoint(self, test_client):
        """Test adding questions endpoint."""

    @pytest.mark.asyncio
    async def test_get_responses_endpoint(self, test_client):
        """Test response retrieval endpoint."""

    @pytest.mark.asyncio
    async def test_workflow_endpoint(self, test_client):
        """Test complete workflow endpoint."""
```

## Enhanced Logging Implementation

### 1. Google API Request Logging

#### Request/Response Tracking:
```python
@log_google_api_call
async def create_assessment_form(self, assessment_data: Dict, form_title: str) -> Dict:
    """Create Google Form with comprehensive logging."""

    correlation_id = str(uuid4())

    log_data_flow(
        message="Starting Google Form creation",
        step="form_creation_start",
        component="google_forms_service",
        data_before={
            "assessment_id": assessment_data.get("assessment_id"),
            "form_title": form_title,
            "question_count": len(assessment_data.get("questions", [])),
            "certification_profile_id": assessment_data.get("certification_profile_id")
        },
        correlation_id=correlation_id
    )

    try:
        # Create form through Google API
        form_response = self.forms_service.forms().create(
            body=form_structure
        ).execute()

        log_data_flow(
            message="Google Form created successfully",
            step="form_creation_success",
            component="google_forms_service",
            data_after={
                "form_id": form_response["formId"],
                "form_url": form_response["responderUri"],
                "creation_time": datetime.now().isoformat()
            },
            correlation_id=correlation_id
        )

        # Log API usage metrics
        google_api_logger.info(
            "Google Forms API usage",
            extra={
                "api_endpoint": "forms.create",
                "request_size_bytes": len(json.dumps(form_structure)),
                "response_time_ms": response_time_ms,
                "quota_usage": self._get_quota_usage(),
                "correlation_id": correlation_id
            }
        )

        return form_response

    except Exception as e:
        log_data_flow(
            message=f"Google Form creation failed: {str(e)}",
            step="form_creation_error",
            component="google_forms_service",
            error_details={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "form_title": form_title,
                "assessment_id": assessment_data.get("assessment_id")
            },
            correlation_id=correlation_id
        )
        raise
```

### 2. Response Processing Logging

#### Response Analysis Tracking:
```python
@log_execution_time
async def process_form_responses(self, form_id: str, assessment_data: Dict) -> Dict:
    """Process responses with detailed logging."""

    processing_logger = get_service_logger("response_processing")

    start_time = time.time()

    processing_logger.info(
        "Starting response processing",
        extra={
            "form_id": form_id,
            "assessment_id": assessment_data.get("assessment_id"),
            "expected_questions": len(assessment_data.get("questions", []))
        }
    )

    try:
        responses = await self._fetch_form_responses(form_id)

        processing_logger.info(
            "Responses retrieved",
            extra={
                "form_id": form_id,
                "response_count": len(responses),
                "retrieval_time_seconds": time.time() - start_time
            }
        )

        # Process each response
        processed_responses = []
        for response in responses:
            processed = await self._process_individual_response(
                response, assessment_data
            )
            processed_responses.append(processed)

        processing_time = time.time() - start_time

        processing_logger.info(
            "Response processing completed",
            extra={
                "form_id": form_id,
                "processed_count": len(processed_responses),
                "total_processing_time": processing_time,
                "average_time_per_response": processing_time / len(responses) if responses else 0
            }
        )

        return {
            "success": True,
            "processed_responses": processed_responses,
            "processing_metrics": {
                "total_responses": len(responses),
                "processing_time_seconds": processing_time,
                "responses_per_second": len(responses) / processing_time if processing_time > 0 else 0
            }
        }

    except Exception as e:
        processing_logger.error(
            f"Response processing failed: {str(e)}",
            extra={
                "form_id": form_id,
                "processing_time": time.time() - start_time,
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise
```

### 3. Performance Monitoring

#### Google API Rate Limiting:
```python
class GoogleAPIRateLimiter:
    """Rate limiting and monitoring for Google API calls."""

    def __init__(self):
        self.request_times = []
        self.quota_usage = {"forms": 0, "drive": 0}
        self.rate_limit_logger = get_service_logger("google_api_rate_limiting")

    async def track_api_call(self, api_name: str, endpoint: str):
        """Track API call for rate limiting."""
        current_time = time.time()
        self.request_times.append(current_time)

        # Remove requests older than 1 minute
        self.request_times = [
            t for t in self.request_times
            if current_time - t < 60
        ]

        requests_per_minute = len(self.request_times)

        self.rate_limit_logger.info(
            "Google API call tracked",
            extra={
                "api_name": api_name,
                "endpoint": endpoint,
                "requests_per_minute": requests_per_minute,
                "quota_remaining": self._calculate_quota_remaining(api_name)
            }
        )

        # Check rate limits
        if requests_per_minute > 100:  # Google Forms API limit
            self.rate_limit_logger.warning(
                "Approaching Google API rate limit",
                extra={
                    "requests_per_minute": requests_per_minute,
                    "limit": 100,
                    "api_name": api_name
                }
            )
```

## Error Handling and Resilience

### 1. Google API Error Handling

#### Comprehensive Error Recovery:
```python
class GoogleAPIErrorHandler:
    """Handles Google API errors with retry logic."""

    def __init__(self):
        self.max_retries = 3
        self.retry_delays = [1, 2, 4]  # Exponential backoff

    async def execute_with_retry(self, api_call, *args, **kwargs):
        """Execute Google API call with retry logic."""

        for attempt in range(self.max_retries):
            try:
                return await api_call(*args, **kwargs)

            except HttpError as e:
                if e.resp.status == 403:
                    # Permission error - don't retry
                    raise GoogleAPIPermissionError(f"Permission denied: {e}")
                elif e.resp.status == 429:
                    # Rate limit - retry with backoff
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delays[attempt]
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise GoogleAPIRateLimitError("Rate limit exceeded after retries")
                elif e.resp.status >= 500:
                    # Server error - retry
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delays[attempt]
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise GoogleAPIServerError(f"Server error after retries: {e}")
                else:
                    # Other errors - don't retry
                    raise GoogleAPIError(f"Google API error: {e}")

            except Exception as e:
                # Unexpected error
                raise GoogleAPIUnexpectedError(f"Unexpected error: {e}")
```

### 2. Form Creation Validation

#### Input Validation and Sanitization:
```python
class FormCreationValidator:
    """Validates form creation requests and data."""

    def validate_assessment_data(self, assessment_data: Dict) -> Dict:
        """Validate assessment data for form creation."""
        validation_errors = []

        # Check required fields
        required_fields = ["assessment_id", "questions", "metadata"]
        for field in required_fields:
            if field not in assessment_data:
                validation_errors.append(f"Missing required field: {field}")

        # Validate questions
        questions = assessment_data.get("questions", [])
        if not questions:
            validation_errors.append("No questions provided")

        for i, question in enumerate(questions):
            question_errors = self._validate_question(question, i)
            validation_errors.extend(question_errors)

        # Validate form title
        form_title = assessment_data.get("form_title", "")
        if len(form_title) > 300:
            validation_errors.append("Form title exceeds 300 characters")

        if validation_errors:
            raise ValidationError(validation_errors)

        return {"valid": True, "sanitized_data": self._sanitize_data(assessment_data)}

    def _validate_question(self, question: Dict, index: int) -> List[str]:
        """Validate individual question for Google Forms compatibility."""
        errors = []

        # Check question text length (Google Forms limit)
        question_text = question.get("question_text", "")
        if len(question_text) > 4096:
            errors.append(f"Question {index + 1}: Text exceeds 4096 characters")

        # Validate question type
        question_type = question.get("question_type")
        supported_types = ["multiple_choice", "true_false", "scenario"]
        if question_type not in supported_types:
            errors.append(f"Question {index + 1}: Unsupported type '{question_type}'")

        # Validate multiple choice options
        if question_type == "multiple_choice":
            options = question.get("options", [])
            if len(options) < 2:
                errors.append(f"Question {index + 1}: Multiple choice needs at least 2 options")
            if len(options) > 10:
                errors.append(f"Question {index + 1}: Multiple choice supports max 10 options")

        return errors
```

## Configuration Management

### 1. Google API Configuration (`src/common/config.py`)

#### Enhanced Configuration:
```python
class Settings(BaseSettings):
    """Phase 2 configuration with Google API settings."""

    # Google Cloud Configuration (Extended)
    google_application_credentials: str = Field(..., alias="GOOGLE_APPLICATION_CREDENTIALS")
    google_cloud_project: str = Field(..., alias="GOOGLE_CLOUD_PROJECT")

    # Google Forms Configuration
    google_forms_default_settings: Dict = Field(
        default={
            "collect_email": True,
            "require_login": True,
            "allow_response_editing": False,
            "shuffle_questions": False,
            "show_progress_bar": True
        },
        alias="GOOGLE_FORMS_DEFAULT_SETTINGS"
    )

    # Google API Rate Limiting
    google_api_requests_per_minute: int = Field(default=90, alias="GOOGLE_API_REQUESTS_PER_MINUTE")
    google_api_retry_attempts: int = Field(default=3, alias="GOOGLE_API_RETRY_ATTEMPTS")
    google_api_timeout_seconds: int = Field(default=30, alias="GOOGLE_API_TIMEOUT_SECONDS")

    # Form Processing Configuration
    max_form_responses_per_request: int = Field(default=1000, alias="MAX_FORM_RESPONSES_PER_REQUEST")
    response_processing_timeout_seconds: int = Field(default=300, alias="RESPONSE_PROCESSING_TIMEOUT")
```

### 2. Google API Scopes Configuration

#### Required Permissions:
```python
GOOGLE_API_SCOPES = {
    "forms": [
        "https://www.googleapis.com/auth/forms.body",
        "https://www.googleapis.com/auth/forms.responses.readonly"
    ],
    "drive": [
        "https://www.googleapis.com/auth/drive.file"
    ],
    "sheets": [
        "https://www.googleapis.com/auth/spreadsheets"
    ]
}

REQUIRED_PERMISSIONS = {
    "forms.create": "Create and manage Google Forms",
    "forms.read": "Read form structure and settings",
    "forms.responses.read": "Access form responses",
    "drive.file": "Manage created forms in Google Drive"
}
```

## Success Metrics and Monitoring

### 1. Phase 2 Key Performance Indicators (KPIs)

#### Form Creation Metrics:
- **Form Creation Success Rate**: % of successful form creations
- **Average Form Creation Time**: Mean time to create forms from assessments
- **Question Mapping Accuracy**: Successful question type conversions
- **Google API Response Time**: P95/P99 response times for API calls

#### Response Processing Metrics:
- **Response Processing Speed**: Responses processed per second
- **Scoring Accuracy**: Correlation between expected and calculated scores
- **Feedback Generation Quality**: User satisfaction with generated feedback

### 2. Monitoring Implementation

#### Google API Usage Tracking:
```python
class GoogleAPIMetrics:
    """Metrics collection for Google API usage."""

    def __init__(self):
        self.api_calls = {"forms": 0, "drive": 0}
        self.response_times = []
        self.quota_usage = {"daily": 0, "per_minute": 0}
        self.error_counts = {"rate_limit": 0, "permission": 0, "server": 0}

    def record_api_call(self, api_name: str, response_time: float, success: bool):
        """Record Google API call metrics."""
        self.api_calls[api_name] += 1
        self.response_times.append(response_time)

        if not success:
            self.error_counts["server"] += 1

    def get_usage_summary(self) -> Dict:
        """Get comprehensive API usage summary."""
        return {
            "total_calls": sum(self.api_calls.values()),
            "calls_by_api": self.api_calls,
            "average_response_time": statistics.mean(self.response_times),
            "error_rate": sum(self.error_counts.values()) / sum(self.api_calls.values()),
            "quota_utilization": self.quota_usage
        }
```

## Phase 2 Implementation Status

### ✅ Completed Components:
1. **Google Forms Service**: Form creation and management API integration
2. **Assessment-to-Forms Mapper**: Intelligent question type conversion
3. **Form Response Processor**: Response analysis and scoring
4. **Google Authentication Manager**: Secure credential management
5. **API Endpoints**: Complete Google Forms workflow endpoints
6. **Enhanced Logging**: Google API request tracking and performance monitoring
7. **Error Handling**: Comprehensive retry logic and validation

### 🔄 In Progress:
1. **Advanced Question Types**: Support for matrix and grid questions
2. **Real-time Response Streaming**: Live response processing
3. **Form Templates**: Reusable form structures for different certification types

### 📋 Next Steps:
1. **Phase 3**: Response collection pipeline and data analysis
2. **Form Analytics Dashboard**: Visual response analytics
3. **Automated Form Distribution**: Email and notification integration

## Technical Dependencies

### Required Python Packages:
```txt
google-api-python-client>=2.0.0
google-auth>=2.0.0
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.2.0
```

### Environment Configuration:
```bash
# Required Environment Variables
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_FORMS_DEFAULT_SETTINGS='{"collect_email": true, "require_login": true}'
GOOGLE_API_REQUESTS_PER_MINUTE=90
```

## Phase 2 Completion Checklist

- [x] Google Forms Service Implementation
- [x] Assessment-to-Forms Mapping Logic
- [x] Form Response Processing Pipeline
- [x] Google APIs Authentication Management
- [x] API Endpoints for Form Management
- [x] Enhanced Logging with Google API Tracking
- [x] Error Handling and Retry Logic
- [x] Configuration Management for Google APIs
- [ ] Comprehensive Test Suite Completion
- [ ] Performance Optimization and Caching
- [ ] Production Deployment Configuration

**Phase 2 Status**: ✅ **CORE IMPLEMENTATION COMPLETE** - Ready for Phase 3 Integration