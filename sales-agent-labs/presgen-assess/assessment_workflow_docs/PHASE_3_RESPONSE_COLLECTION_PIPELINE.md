# Phase 3: Response Collection Pipeline
*Automated Data Processing and Transformation System*

## Overview
Comprehensive response collection and processing pipeline that automatically monitors Google Forms, collects responses in real-time, transforms data into structured formats, and triggers downstream workflows for assessment analysis and personalized content generation.

## 3.1 Real-time Response Collection

### 3.1.1 Webhook Integration System
```python
# /presgen-assess/src/pipelines/response_collection/webhook_handler.py
from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional, List
import json
import hmac
import hashlib
import logging
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class GoogleFormsWebhookHandler:
    """
    Handles incoming webhooks from Google Forms when new responses are submitted.
    Validates webhook signatures and triggers response processing pipeline.
    """

    def __init__(self, app: FastAPI, webhook_secret: str, response_processor):
        self.app = app
        self.webhook_secret = webhook_secret
        self.response_processor = response_processor
        self.setup_webhook_endpoints()

    def setup_webhook_endpoints(self):
        """Setup FastAPI endpoints for webhook handling."""

        @self.app.post("/webhooks/forms/response")
        async def handle_form_response_webhook(
            request: Request,
            background_tasks: BackgroundTasks,
            signature: str = None
        ):
            """Handle incoming form response webhook."""
            try:
                # Get request body
                body = await request.body()

                # Verify webhook signature
                if not self._verify_webhook_signature(body, signature):
                    raise HTTPException(status_code=401, detail="Invalid webhook signature")

                # Parse webhook payload
                webhook_data = json.loads(body)

                # Add to background processing queue
                background_tasks.add_task(
                    self._process_webhook_data,
                    webhook_data
                )

                return {"status": "accepted", "timestamp": datetime.utcnow().isoformat()}

            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON payload")
            except Exception as e:
                logger.error(f"Webhook processing error: {str(e)}")
                raise HTTPException(status_code=500, detail="Webhook processing failed")

        @self.app.get("/webhooks/forms/health")
        async def webhook_health_check():
            """Health check endpoint for webhook service."""
            return {
                "status": "healthy",
                "service": "forms_webhook_handler",
                "timestamp": datetime.utcnow().isoformat()
            }

    def _verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """Verify webhook signature for security."""
        if not signature:
            return False

        expected_signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(f"sha256={expected_signature}", signature)

    async def _process_webhook_data(self, webhook_data: Dict[str, Any]):
        """Process webhook data in background task."""
        try:
            event_type = webhook_data.get("eventType")
            form_id = webhook_data.get("formId")
            response_id = webhook_data.get("responseId")

            if event_type == "RESPONSES" and form_id and response_id:
                await self.response_processor.process_new_response(
                    form_id=form_id,
                    response_id=response_id,
                    webhook_data=webhook_data
                )

            logger.info(f"Processed webhook for form {form_id}, response {response_id}")

        except Exception as e:
            logger.error(f"Background webhook processing failed: {str(e)}")

class PollingCollector:
    """
    Alternative collection method using polling for forms without webhook support.
    Checks forms periodically for new responses.
    """

    def __init__(self, google_services, response_processor, poll_interval: int = 300):
        self.google_services = google_services
        self.response_processor = response_processor
        self.poll_interval = poll_interval  # seconds
        self.active_forms = {}
        self.polling_active = False

    async def start_polling(self, form_configs: List[Dict[str, Any]]):
        """Start polling for specified forms."""
        self.active_forms = {config["form_id"]: config for config in form_configs}
        self.polling_active = True

        logger.info(f"Started polling {len(form_configs)} forms every {self.poll_interval} seconds")

        while self.polling_active:
            try:
                await self._poll_all_forms()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Polling error: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying

    async def stop_polling(self):
        """Stop the polling process."""
        self.polling_active = False
        logger.info("Stopped forms polling")

    async def _poll_all_forms(self):
        """Poll all active forms for new responses."""
        tasks = []
        for form_id, config in self.active_forms.items():
            task = self._poll_single_form(form_id, config)
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _poll_single_form(self, form_id: str, config: Dict[str, Any]):
        """Poll a single form for new responses."""
        try:
            forms_client = self.google_services.get_forms_client()

            # Get responses since last check
            last_check = config.get("last_check")

            # Get all responses (Google Forms API doesn't support filtering by date directly)
            responses = forms_client.forms().responses().list(formId=form_id).execute()

            new_responses = []
            latest_timestamp = last_check

            for response in responses.get("responses", []):
                response_time = response.get("lastSubmittedTime")

                if not last_check or response_time > last_check:
                    new_responses.append(response)

                    if not latest_timestamp or response_time > latest_timestamp:
                        latest_timestamp = response_time

            # Process new responses
            for response in new_responses:
                await self.response_processor.process_new_response(
                    form_id=form_id,
                    response_id=response["responseId"],
                    response_data=response
                )

            # Update last check timestamp
            self.active_forms[form_id]["last_check"] = latest_timestamp

            if new_responses:
                logger.info(f"Found {len(new_responses)} new responses for form {form_id}")

        except Exception as e:
            logger.error(f"Failed to poll form {form_id}: {str(e)}")
```

### 3.1.2 Response Processing Engine
```python
# /presgen-assess/src/pipelines/response_collection/response_processor.py
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import asyncio
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class ProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"

@dataclass
class ResponseProcessingJob:
    """Data class for response processing jobs."""
    job_id: str
    form_id: str
    response_id: str
    status: ProcessingStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = None

class ResponseProcessor:
    """
    Core response processing engine that handles data transformation,
    validation, and routing to appropriate analysis workflows.
    """

    def __init__(
        self,
        google_services,
        database_service,
        notification_service,
        max_concurrent_jobs: int = 10
    ):
        self.google_services = google_services
        self.database_service = database_service
        self.notification_service = notification_service
        self.max_concurrent_jobs = max_concurrent_jobs
        self.processing_queue = asyncio.Queue()
        self.active_jobs = {}
        self.processors_running = False

    async def start_processing(self):
        """Start the response processing workers."""
        self.processors_running = True

        # Start multiple worker coroutines
        workers = [
            self._worker(f"worker_{i}")
            for i in range(self.max_concurrent_jobs)
        ]

        await asyncio.gather(*workers)

    async def stop_processing(self):
        """Stop the response processing workers."""
        self.processors_running = False

    async def process_new_response(
        self,
        form_id: str,
        response_id: str,
        webhook_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        """Queue a new response for processing."""
        job_id = f"{form_id}_{response_id}_{datetime.utcnow().timestamp()}"

        job = ResponseProcessingJob(
            job_id=job_id,
            form_id=form_id,
            response_id=response_id,
            status=ProcessingStatus.PENDING,
            created_at=datetime.utcnow(),
            metadata={
                "webhook_data": webhook_data,
                "response_data": response_data
            }
        )

        await self.processing_queue.put(job)
        logger.info(f"Queued response processing job: {job_id}")

    async def _worker(self, worker_name: str):
        """Worker coroutine for processing responses."""
        logger.info(f"Started response processing worker: {worker_name}")

        while self.processors_running:
            try:
                # Get job from queue with timeout
                job = await asyncio.wait_for(
                    self.processing_queue.get(),
                    timeout=1.0
                )

                await self._process_job(job, worker_name)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {str(e)}")

    async def _process_job(self, job: ResponseProcessingJob, worker_name: str):
        """Process a single response job."""
        try:
            job.status = ProcessingStatus.PROCESSING
            job.started_at = datetime.utcnow()
            self.active_jobs[job.job_id] = job

            logger.info(f"Worker {worker_name} processing job {job.job_id}")

            # Get form metadata
            form_metadata = await self._get_form_metadata(job.form_id)

            # Get complete response data
            response_data = await self._get_complete_response_data(
                job.form_id,
                job.response_id,
                job.metadata.get("response_data")
            )

            # Transform response data
            structured_response = await self._transform_response_data(
                response_data,
                form_metadata
            )

            # Validate response data
            validation_result = await self._validate_response_data(
                structured_response,
                form_metadata
            )

            if not validation_result["valid"]:
                raise ValueError(f"Response validation failed: {validation_result['errors']}")

            # Store processed response
            stored_response = await self._store_response_data(
                job.form_id,
                job.response_id,
                structured_response,
                form_metadata
            )

            # Trigger downstream processing
            await self._trigger_downstream_processing(
                stored_response,
                form_metadata
            )

            # Mark job as completed
            job.status = ProcessingStatus.COMPLETED
            job.completed_at = datetime.utcnow()

            logger.info(f"Successfully processed job {job.job_id}")

        except Exception as e:
            await self._handle_job_error(job, e)

        finally:
            if job.job_id in self.active_jobs:
                del self.active_jobs[job.job_id]

    async def _get_form_metadata(self, form_id: str) -> Dict[str, Any]:
        """Get form metadata and configuration."""
        try:
            # Check database cache first
            cached_metadata = await self.database_service.get_form_metadata(form_id)

            if cached_metadata and not self._is_metadata_stale(cached_metadata):
                return cached_metadata

            # Fetch from Google Forms API
            forms_client = self.google_services.get_forms_client()
            form = forms_client.forms().get(formId=form_id).execute()

            # Transform to our metadata format
            metadata = {
                "form_id": form_id,
                "title": form["info"]["title"],
                "description": form["info"].get("description", ""),
                "created_time": form.get("createTime"),
                "settings": form.get("settings", {}),
                "questions": self._extract_question_metadata(form),
                "cached_at": datetime.utcnow().isoformat()
            }

            # Cache for future use
            await self.database_service.cache_form_metadata(form_id, metadata)

            return metadata

        except Exception as e:
            logger.error(f"Failed to get form metadata for {form_id}: {str(e)}")
            raise

    async def _get_complete_response_data(
        self,
        form_id: str,
        response_id: str,
        cached_response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get complete response data from Google Forms."""
        if cached_response:
            return cached_response

        try:
            forms_client = self.google_services.get_forms_client()
            response = forms_client.forms().responses().get(
                formId=form_id,
                responseId=response_id
            ).execute()

            return response

        except Exception as e:
            logger.error(f"Failed to get response data for {response_id}: {str(e)}")
            raise

    async def _transform_response_data(
        self,
        response_data: Dict[str, Any],
        form_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform raw response data into structured format."""
        questions_map = {
            q["question_id"]: q for q in form_metadata["questions"]
        }

        structured_response = {
            "response_id": response_data["responseId"],
            "form_id": response_data["formId"],
            "create_time": response_data["createTime"],
            "last_submitted_time": response_data["lastSubmittedTime"],
            "respondent_email": response_data.get("respondentEmail"),
            "answers": {},
            "metadata": {
                "total_time": response_data.get("totalTime"),
                "response_count": len(response_data.get("answers", {}))
            }
        }

        # Transform answers
        for question_id, answer in response_data.get("answers", {}).items():
            if question_id in questions_map:
                question_info = questions_map[question_id]

                structured_answer = {
                    "question_id": question_id,
                    "question_title": question_info["title"],
                    "question_type": question_info["type"],
                    "answer_value": self._extract_answer_value(answer, question_info["type"]),
                    "answer_raw": answer
                }

                structured_response["answers"][question_id] = structured_answer

        return structured_response

    def _extract_answer_value(self, answer: Dict[str, Any], question_type: str) -> Any:
        """Extract clean answer value based on question type."""
        if "textAnswers" in answer:
            values = [text_answer["value"] for text_answer in answer["textAnswers"]["answers"]]
            return values[0] if len(values) == 1 else values
        elif "choiceAnswers" in answer:
            values = [choice_answer["value"] for choice_answer in answer["choiceAnswers"]["answers"]]
            return values[0] if len(values) == 1 else values
        elif "scaleAnswer" in answer:
            return answer["scaleAnswer"]["value"]
        elif "dateAnswer" in answer:
            date_answer = answer["dateAnswer"]
            return f"{date_answer['year']}-{date_answer['month']:02d}-{date_answer['day']:02d}"
        elif "timeAnswer" in answer:
            time_answer = answer["timeAnswer"]
            return f"{time_answer['hours']:02d}:{time_answer['minutes']:02d}"
        elif "fileUploadAnswers" in answer:
            return [file_answer["fileId"] for file_answer in answer["fileUploadAnswers"]["answers"]]

        return None

    def _extract_question_metadata(self, form: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract question metadata from form structure."""
        questions = []

        for item in form.get("items", []):
            if "questionItem" in item:
                question = item["questionItem"]["question"]
                question_id = question["questionId"]

                question_info = {
                    "question_id": question_id,
                    "title": item["title"],
                    "description": item.get("description"),
                    "type": self._determine_question_type(question),
                    "required": question.get("required", False),
                    "options": self._extract_question_options(question)
                }

                questions.append(question_info)

        return questions

    def _determine_question_type(self, question: Dict[str, Any]) -> str:
        """Determine question type from Google Forms structure."""
        if "choiceQuestion" in question:
            choice_type = question["choiceQuestion"]["type"]
            return {
                "RADIO": "multiple_choice",
                "CHECKBOX": "checkbox",
                "DROP_DOWN": "dropdown"
            }.get(choice_type, "choice")
        elif "textQuestion" in question:
            return "paragraph" if question["textQuestion"]["paragraph"] else "short_answer"
        elif "scaleQuestion" in question:
            return "linear_scale"
        elif "dateQuestion" in question:
            return "date"
        elif "timeQuestion" in question:
            return "time"
        elif "fileUploadQuestion" in question:
            return "file_upload"

        return "unknown"

    def _extract_question_options(self, question: Dict[str, Any]) -> List[str]:
        """Extract answer options from question."""
        if "choiceQuestion" in question:
            return [option["value"] for option in question["choiceQuestion"].get("options", [])]
        elif "scaleQuestion" in question:
            scale = question["scaleQuestion"]
            return [str(i) for i in range(scale["low"], scale["high"] + 1)]

        return []

    async def _validate_response_data(
        self,
        response_data: Dict[str, Any],
        form_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate response data for completeness and consistency."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # Check required fields
        required_questions = [
            q for q in form_metadata["questions"] if q["required"]
        ]

        for question in required_questions:
            question_id = question["question_id"]
            if question_id not in response_data["answers"]:
                validation_result["errors"].append(
                    f"Missing required answer for question: {question['title']}"
                )

        # Check data types and formats
        for question_id, answer in response_data["answers"].items():
            question_type = answer["question_type"]
            answer_value = answer["answer_value"]

            if not self._validate_answer_format(answer_value, question_type):
                validation_result["warnings"].append(
                    f"Unexpected format for {question_type} answer: {answer['question_title']}"
                )

        validation_result["valid"] = len(validation_result["errors"]) == 0

        return validation_result

    def _validate_answer_format(self, answer_value: Any, question_type: str) -> bool:
        """Validate answer format for specific question type."""
        if answer_value is None:
            return True  # Allow empty answers

        if question_type in ["multiple_choice", "dropdown"]:
            return isinstance(answer_value, str)
        elif question_type == "checkbox":
            return isinstance(answer_value, list)
        elif question_type in ["short_answer", "paragraph"]:
            return isinstance(answer_value, str)
        elif question_type == "linear_scale":
            return isinstance(answer_value, (int, float))
        elif question_type == "date":
            return isinstance(answer_value, str) and len(answer_value) == 10
        elif question_type == "time":
            return isinstance(answer_value, str) and ":" in answer_value
        elif question_type == "file_upload":
            return isinstance(answer_value, list)

        return True

    async def _store_response_data(
        self,
        form_id: str,
        response_id: str,
        structured_response: Dict[str, Any],
        form_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store processed response in database."""
        try:
            stored_response = await self.database_service.store_form_response(
                response_data=structured_response,
                form_metadata=form_metadata
            )

            logger.info(f"Stored response {response_id} for form {form_id}")
            return stored_response

        except Exception as e:
            logger.error(f"Failed to store response {response_id}: {str(e)}")
            raise

    async def _trigger_downstream_processing(
        self,
        stored_response: Dict[str, Any],
        form_metadata: Dict[str, Any]
    ):
        """Trigger downstream processing based on form type and configuration."""
        try:
            form_type = form_metadata.get("settings", {}).get("form_type")

            if form_type == "pre_assessment":
                await self._trigger_pre_assessment_analysis(stored_response, form_metadata)
            elif form_type == "knowledge_assessment":
                await self._trigger_assessment_scoring(stored_response, form_metadata)
            elif form_type == "feedback":
                await self._trigger_feedback_analysis(stored_response, form_metadata)

            # General notifications
            await self._send_response_notifications(stored_response, form_metadata)

        except Exception as e:
            logger.error(f"Downstream processing failed: {str(e)}")
            # Don't re-raise - response is already stored

    async def _trigger_pre_assessment_analysis(
        self,
        response: Dict[str, Any],
        form_metadata: Dict[str, Any]
    ):
        """Trigger pre-assessment analysis workflow."""
        # This would trigger the gap analysis and personalization pipeline
        await self.notification_service.send_event(
            event_type="pre_assessment_completed",
            data={
                "response_id": response["response_id"],
                "form_id": response["form_id"],
                "respondent_email": response["respondent_email"]
            }
        )

    async def _trigger_assessment_scoring(
        self,
        response: Dict[str, Any],
        form_metadata: Dict[str, Any]
    ):
        """Trigger assessment scoring and analysis."""
        await self.notification_service.send_event(
            event_type="assessment_submitted",
            data={
                "response_id": response["response_id"],
                "form_id": response["form_id"],
                "respondent_email": response["respondent_email"],
                "needs_scoring": True
            }
        )

    async def _trigger_feedback_analysis(
        self,
        response: Dict[str, Any],
        form_metadata: Dict[str, Any]
    ):
        """Trigger feedback analysis workflow."""
        await self.notification_service.send_event(
            event_type="feedback_received",
            data={
                "response_id": response["response_id"],
                "form_id": response["form_id"],
                "respondent_email": response["respondent_email"]
            }
        )

    async def _send_response_notifications(
        self,
        response: Dict[str, Any],
        form_metadata: Dict[str, Any]
    ):
        """Send notifications about new response."""
        # Notify administrators
        await self.notification_service.notify_administrators(
            subject=f"New response to {form_metadata['title']}",
            message=f"Response received from {response['respondent_email']}",
            data=response
        )

    async def _handle_job_error(self, job: ResponseProcessingJob, error: Exception):
        """Handle job processing errors with retry logic."""
        job.retry_count += 1
        job.error_message = str(error)

        if job.retry_count < 3:  # Max 3 retries
            job.status = ProcessingStatus.RETRY

            # Re-queue with exponential backoff
            retry_delay = 2 ** job.retry_count
            await asyncio.sleep(retry_delay)
            await self.processing_queue.put(job)

            logger.warning(f"Retrying job {job.job_id} (attempt {job.retry_count})")
        else:
            job.status = ProcessingStatus.FAILED
            job.completed_at = datetime.utcnow()

            logger.error(f"Job {job.job_id} failed permanently: {error}")

            # Notify about permanent failure
            await self.notification_service.send_event(
                event_type="response_processing_failed",
                data=asdict(job)
            )

    def _is_metadata_stale(self, metadata: Dict[str, Any], max_age_hours: int = 24) -> bool:
        """Check if cached metadata is stale."""
        cached_at = datetime.fromisoformat(metadata.get("cached_at", ""))
        age = datetime.utcnow() - cached_at
        return age.total_seconds() > (max_age_hours * 3600)
```

## 3.2 Data Transformation and Normalization

### 3.2.1 Response Data Transformer
```python
# /presgen-assess/src/pipelines/response_collection/data_transformer.py
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import re
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class AnswerType(Enum):
    TEXT = "text"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    LIST = "list"
    DATE = "date"
    TIME = "time"
    FILE = "file"

@dataclass
class TransformationRule:
    """Rule for transforming response data."""
    field_name: str
    source_question_id: str
    target_type: AnswerType
    transformation_function: str
    validation_pattern: Optional[str] = None
    default_value: Optional[Any] = None

class ResponseDataTransformer:
    """
    Transforms raw Google Forms responses into standardized,
    analysis-ready format with type conversion and normalization.
    """

    def __init__(self):
        self.transformation_rules = {}
        self.normalization_functions = {
            "normalize_email": self._normalize_email,
            "normalize_phone": self._normalize_phone,
            "normalize_experience": self._normalize_experience,
            "normalize_rating": self._normalize_rating,
            "parse_multiple_choice": self._parse_multiple_choice,
            "parse_checkbox_list": self._parse_checkbox_list,
            "extract_numeric": self._extract_numeric,
            "clean_text": self._clean_text
        }

    def register_transformation_rules(
        self,
        form_id: str,
        rules: List[TransformationRule]
    ):
        """Register transformation rules for a specific form."""
        self.transformation_rules[form_id] = {rule.field_name: rule for rule in rules}
        logger.info(f"Registered {len(rules)} transformation rules for form {form_id}")

    async def transform_response(
        self,
        response_data: Dict[str, Any],
        form_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transform raw response data into standardized format.
        """
        form_id = response_data["form_id"]

        # Start with base structure
        transformed_response = {
            "response_id": response_data["response_id"],
            "form_id": form_id,
            "submission_time": self._parse_timestamp(response_data["last_submitted_time"]),
            "respondent_info": {},
            "assessment_data": {},
            "demographics": {},
            "preferences": {},
            "raw_answers": response_data["answers"],
            "metadata": response_data.get("metadata", {})
        }

        # Apply transformation rules if available
        rules = self.transformation_rules.get(form_id, {})

        if rules:
            await self._apply_transformation_rules(
                response_data,
                transformed_response,
                rules
            )
        else:
            # Apply default transformations
            await self._apply_default_transformations(
                response_data,
                transformed_response,
                form_metadata
            )

        # Post-processing validation and cleanup
        await self._validate_transformed_data(transformed_response)

        return transformed_response

    async def _apply_transformation_rules(
        self,
        source_data: Dict[str, Any],
        target_data: Dict[str, Any],
        rules: Dict[str, TransformationRule]
    ):
        """Apply registered transformation rules."""
        for field_name, rule in rules.items():
            try:
                source_answer = source_data["answers"].get(rule.source_question_id)

                if not source_answer:
                    if rule.default_value is not None:
                        self._set_nested_value(target_data, field_name, rule.default_value)
                    continue

                # Get raw answer value
                raw_value = source_answer["answer_value"]

                # Apply transformation function
                if rule.transformation_function in self.normalization_functions:
                    transform_func = self.normalization_functions[rule.transformation_function]
                    transformed_value = transform_func(raw_value)
                else:
                    transformed_value = raw_value

                # Validate against pattern if provided
                if rule.validation_pattern and isinstance(transformed_value, str):
                    if not re.match(rule.validation_pattern, transformed_value):
                        logger.warning(f"Value '{transformed_value}' doesn't match pattern for {field_name}")
                        transformed_value = rule.default_value

                # Set in target structure
                self._set_nested_value(target_data, field_name, transformed_value)

            except Exception as e:
                logger.error(f"Transformation failed for field {field_name}: {str(e)}")

    async def _apply_default_transformations(
        self,
        source_data: Dict[str, Any],
        target_data: Dict[str, Any],
        form_metadata: Dict[str, Any]
    ):
        """Apply default transformations based on question patterns."""
        for question_id, answer in source_data["answers"].items():
            question_title = answer["question_title"].lower()
            answer_value = answer["answer_value"]

            # Identify respondent information
            if any(keyword in question_title for keyword in ["name", "full name"]):
                target_data["respondent_info"]["name"] = self._clean_text(answer_value)

            elif any(keyword in question_title for keyword in ["email", "e-mail"]):
                target_data["respondent_info"]["email"] = self._normalize_email(answer_value)

            elif any(keyword in question_title for keyword in ["phone", "telephone"]):
                target_data["respondent_info"]["phone"] = self._normalize_phone(answer_value)

            # Identify demographic information
            elif "experience" in question_title:
                target_data["demographics"]["experience_level"] = self._normalize_experience(answer_value)

            elif any(keyword in question_title for keyword in ["role", "position", "job"]):
                target_data["demographics"]["role"] = self._clean_text(answer_value)

            elif "age" in question_title:
                target_data["demographics"]["age_range"] = answer_value

            # Identify preferences
            elif "learning" in question_title and "style" in question_title:
                target_data["preferences"]["learning_style"] = self._parse_checkbox_list(answer_value)

            elif "goal" in question_title:
                target_data["preferences"]["primary_goal"] = answer_value

            # Identify assessment data (ratings, knowledge checks)
            elif any(keyword in question_title for keyword in ["rate", "rating", "level"]):
                domain = self._extract_domain_from_question(question_title)
                if domain:
                    if "domain_ratings" not in target_data["assessment_data"]:
                        target_data["assessment_data"]["domain_ratings"] = {}
                    target_data["assessment_data"]["domain_ratings"][domain] = self._normalize_rating(answer_value)

            # General assessment answers
            else:
                if "assessment_answers" not in target_data["assessment_data"]:
                    target_data["assessment_data"]["assessment_answers"] = {}
                target_data["assessment_data"]["assessment_answers"][question_id] = answer_value

    def _normalize_email(self, email: Union[str, Any]) -> Optional[str]:
        """Normalize email address format."""
        if not isinstance(email, str):
            return None

        email = email.strip().lower()

        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, email):
            return email

        return None

    def _normalize_phone(self, phone: Union[str, Any]) -> Optional[str]:
        """Normalize phone number format."""
        if not isinstance(phone, str):
            return None

        # Remove non-digit characters
        digits = re.sub(r'\D', '', phone)

        # Format based on length
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"1-({digits[1:4]}) {digits[4:7]}-{digits[7:]}"

        return phone  # Return original if can't normalize

    def _normalize_experience(self, experience: Union[str, Any]) -> Optional[str]:
        """Normalize experience level to standard categories."""
        if not isinstance(experience, str):
            return None

        experience_lower = experience.lower()

        if any(term in experience_lower for term in ["less than 1", "0-1", "beginner"]):
            return "0-1 years"
        elif any(term in experience_lower for term in ["1-2", "1 to 2"]):
            return "1-2 years"
        elif any(term in experience_lower for term in ["3-5", "3 to 5"]):
            return "3-5 years"
        elif any(term in experience_lower for term in ["6-10", "6 to 10"]):
            return "6-10 years"
        elif any(term in experience_lower for term in ["more than 10", "10+", "expert"]):
            return "10+ years"

        return experience

    def _normalize_rating(self, rating: Union[str, int, float, Any]) -> Optional[int]:
        """Normalize rating to integer scale."""
        if isinstance(rating, (int, float)):
            return int(rating)
        elif isinstance(rating, str):
            # Try to extract number
            numbers = re.findall(r'\d+', rating)
            if numbers:
                return int(numbers[0])

        return None

    def _parse_multiple_choice(self, value: Any) -> Optional[str]:
        """Parse multiple choice answer."""
        if isinstance(value, str):
            return value.strip()
        return None

    def _parse_checkbox_list(self, value: Any) -> List[str]:
        """Parse checkbox answers into list."""
        if isinstance(value, list):
            return [str(item).strip() for item in value]
        elif isinstance(value, str):
            return [value.strip()]
        return []

    def _extract_numeric(self, value: Any) -> Optional[float]:
        """Extract numeric value from text."""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            numbers = re.findall(r'-?\d+\.?\d*', value)
            if numbers:
                return float(numbers[0])
        return None

    def _clean_text(self, text: Any) -> Optional[str]:
        """Clean and normalize text input."""
        if not isinstance(text, str):
            return None

        # Remove extra whitespace and normalize
        cleaned = ' '.join(text.strip().split())

        # Remove special characters if needed
        # cleaned = re.sub(r'[^\w\s-.]', '', cleaned)

        return cleaned if cleaned else None

    def _extract_domain_from_question(self, question_title: str) -> Optional[str]:
        """Extract domain name from question title."""
        # Common patterns for domain extraction
        patterns = [
            r"rate.*(?:knowledge|experience).*(?:with|in)\s+(.+)",
            r"(.+?)\s+(?:knowledge|experience|rating)",
            r"how.*(?:familiar|experienced).*with\s+(.+)"
        ]

        for pattern in patterns:
            match = re.search(pattern, question_title, re.IGNORECASE)
            if match:
                domain = match.group(1).strip()
                # Clean up common words
                domain = re.sub(r'^(?:your|the|a|an)\s+', '', domain, flags=re.IGNORECASE)
                domain = re.sub(r'\s+(?:domain|area|field|technology)$', '', domain, flags=re.IGNORECASE)
                return domain.title()

        return None

    def _set_nested_value(self, data: Dict[str, Any], field_path: str, value: Any):
        """Set value in nested dictionary using dot notation."""
        keys = field_path.split('.')
        current = data

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse Google Forms timestamp to datetime object."""
        try:
            # Google Forms uses RFC3339 format
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except Exception:
            return datetime.utcnow()

    async def _validate_transformed_data(self, data: Dict[str, Any]):
        """Validate transformed data for completeness and consistency."""
        # Check required fields
        required_fields = ["response_id", "form_id", "submission_time"]

        for field in required_fields:
            if field not in data or data[field] is None:
                logger.warning(f"Missing required field: {field}")

        # Validate email format if present
        email = data.get("respondent_info", {}).get("email")
        if email and not self._normalize_email(email):
            logger.warning(f"Invalid email format: {email}")

        # Validate numeric ranges
        for domain, rating in data.get("assessment_data", {}).get("domain_ratings", {}).items():
            if rating is not None and not (1 <= rating <= 10):
                logger.warning(f"Rating out of range for {domain}: {rating}")

class DataQualityChecker:
    """
    Analyzes data quality and completeness of collected responses.
    Provides insights for improving data collection processes.
    """

    def __init__(self):
        self.quality_metrics = [
            "completeness_rate",
            "email_validity_rate",
            "response_time_consistency",
            "answer_quality_score",
            "data_type_compliance"
        ]

    async def analyze_data_quality(
        self,
        responses: List[Dict[str, Any]],
        form_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze overall data quality for a set of responses."""
        if not responses:
            return {"error": "No responses to analyze"}

        quality_report = {
            "total_responses": len(responses),
            "quality_metrics": {},
            "recommendations": [],
            "data_issues": []
        }

        # Calculate completeness rate
        quality_report["quality_metrics"]["completeness_rate"] = \
            self._calculate_completeness_rate(responses, form_metadata)

        # Calculate email validity rate
        quality_report["quality_metrics"]["email_validity_rate"] = \
            self._calculate_email_validity_rate(responses)

        # Analyze response time consistency
        quality_report["quality_metrics"]["response_time_consistency"] = \
            self._analyze_response_time_consistency(responses)

        # Calculate answer quality score
        quality_report["quality_metrics"]["answer_quality_score"] = \
            self._calculate_answer_quality_score(responses)

        # Generate recommendations
        quality_report["recommendations"] = self._generate_quality_recommendations(
            quality_report["quality_metrics"]
        )

        return quality_report

    def _calculate_completeness_rate(
        self,
        responses: List[Dict[str, Any]],
        form_metadata: Dict[str, Any]
    ) -> float:
        """Calculate percentage of complete responses."""
        if not responses:
            return 0.0

        required_questions = [
            q["question_id"] for q in form_metadata.get("questions", [])
            if q.get("required", False)
        ]

        if not required_questions:
            return 100.0

        complete_responses = 0
        for response in responses:
            answered_required = 0
            for question_id in required_questions:
                if question_id in response.get("raw_answers", {}):
                    answered_required += 1

            if answered_required == len(required_questions):
                complete_responses += 1

        return (complete_responses / len(responses)) * 100

    def _calculate_email_validity_rate(self, responses: List[Dict[str, Any]]) -> float:
        """Calculate percentage of valid email addresses."""
        email_responses = []

        for response in responses:
            email = response.get("respondent_info", {}).get("email")
            if email:
                email_responses.append(email)

        if not email_responses:
            return 100.0  # No emails to validate

        valid_emails = 0
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        for email in email_responses:
            if re.match(email_pattern, email):
                valid_emails += 1

        return (valid_emails / len(email_responses)) * 100

    def _analyze_response_time_consistency(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze consistency in response times."""
        response_times = []

        for response in responses:
            metadata = response.get("metadata", {})
            total_time = metadata.get("total_time")

            if total_time and isinstance(total_time, (int, float)):
                response_times.append(total_time)

        if len(response_times) < 2:
            return {"status": "insufficient_data"}

        import statistics

        mean_time = statistics.mean(response_times)
        std_dev = statistics.stdev(response_times) if len(response_times) > 1 else 0

        # Calculate coefficient of variation
        cv = (std_dev / mean_time) if mean_time > 0 else 0

        return {
            "mean_time_seconds": mean_time,
            "std_deviation": std_dev,
            "coefficient_of_variation": cv,
            "consistency_score": max(0, 100 - (cv * 100))  # Lower CV = higher consistency
        }

    def _calculate_answer_quality_score(self, responses: List[Dict[str, Any]]) -> float:
        """Calculate overall answer quality score."""
        if not responses:
            return 0.0

        total_score = 0
        total_answers = 0

        for response in responses:
            for answer in response.get("raw_answers", {}).values():
                answer_value = answer.get("answer_value")

                if answer_value is None or answer_value == "":
                    score = 0
                elif isinstance(answer_value, str) and len(answer_value.strip()) < 3:
                    score = 30  # Very short text
                elif isinstance(answer_value, str) and len(answer_value.strip()) < 10:
                    score = 70  # Short but meaningful
                else:
                    score = 100  # Good quality answer

                total_score += score
                total_answers += 1

        return (total_score / total_answers) if total_answers > 0 else 0

    def _generate_quality_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on quality metrics."""
        recommendations = []

        completeness_rate = metrics.get("completeness_rate", 100)
        if completeness_rate < 80:
            recommendations.append(
                "Consider reducing the number of required questions or improving question clarity to increase completion rate"
            )

        email_validity_rate = metrics.get("email_validity_rate", 100)
        if email_validity_rate < 90:
            recommendations.append(
                "Add email format validation to the form to improve email data quality"
            )

        time_consistency = metrics.get("response_time_consistency", {})
        if isinstance(time_consistency, dict) and time_consistency.get("consistency_score", 100) < 70:
            recommendations.append(
                "High variation in response times may indicate form usability issues or unclear questions"
            )

        answer_quality = metrics.get("answer_quality_score", 100)
        if answer_quality < 70:
            recommendations.append(
                "Consider adding help text or examples to improve answer quality"
            )

        return recommendations
```

This completes Phase 3 - Response Collection Pipeline, providing a comprehensive system for automated response collection, processing, and data quality management.

## Implementation Roadmap (Detailed)

1. **Ingestion Scheduler**
   - Implement polling/webhook handlers that fetch responses incrementally using the Forms API, respecting pagination and timestamps.
   - Ensure idempotency by tracking `response_id` and `update_time` per submission.
2. **Normalization & Enrichment**
   - Map raw answers to question metadata, convert types, and enrich with workflow context (domain, Bloom level, confidence fields).
   - Apply anonymization when storing PII in analytics databases.
3. **Quality Controls**
   - Evaluate response completeness, detect duplicates, and flag suspicious patterns (e.g., same IP, extremely fast submissions).
4. **Storage & Exposure**
   - Persist normalized responses in dedicated tables (raw + processed) and expose APIs for downstream analysis pipelines.
5. **Workflow Hooks**
   - Update `WorkflowExecution` statuses as responses arrive, triggering analytics once thresholds are met or deadlines reached.

## Test-Driven Development Strategy

1. **Ingestion Tests**
   - Start with failing tests verifying pagination, duplicate prevention, and resume token handling.
2. **Normalization Tests**
   - Use fixtures to ensure type coercion, question mapping, and domain tagging behave correctly.
3. **Quality Rule Tests**
   - Simulate problematic responses (blank answers, repeated submissions) confirming they trigger alerts and remediation steps.
4. **API Tests**
   - Validate response retrieval endpoints support filtering, pagination, and security checks.
5. **Performance Tests**
   - Benchmark ingestion under load (e.g., 10k responses) ensuring throughput and latency targets.

## Logging & Observability Enhancements

1. **Ingestion Logs**
   - Log each fetch cycle with counts of new/duplicate responses, latency, and workflow correlation.
2. **Quality Alerts**
   - Emit WARN/ERROR logs when quality thresholds are breached, including actionable remediation suggestions.
3. **Metrics**
   - Track `responses_processed_total`, `responses_duplicate_total`, and processing duration histograms.
4. **Dashboards**
   - Build Grafana panels (or equivalent) showing ingestion backlog, response volume trends, and quality KPI heatmaps.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create detailed Phase 1 document - Google APIs Foundation", "status": "completed", "activeForm": "Creating detailed Phase 1 document - Google APIs Foundation"}, {"content": "Create detailed Phase 2 document - Google Forms Automation", "status": "completed", "activeForm": "Creating detailed Phase 2 document - Google Forms Automation"}, {"content": "Create detailed Phase 3 document - Response Collection Pipeline", "status": "completed", "activeForm": "Creating detailed Phase 3 document - Response Collection Pipeline"}, {"content": "Create detailed Phase 4 document - PresGen-Core Integration", "status": "in_progress", "activeForm": "Creating detailed Phase 4 document - PresGen-Core Integration"}, {"content": "Create detailed Phase 5 document - PresGen-Avatar Integration", "status": "pending", "activeForm": "Creating detailed Phase 5 document - PresGen-Avatar Integration"}, {"content": "Fix UUID serialization issue in enhanced logging", "status": "completed", "activeForm": "Fixing UUID serialization issue in enhanced logging"}]
