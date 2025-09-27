# Phase 4: PresGen-Core Integration
*AI-Powered Presentation Generation and Content Creation*

## Overview
Integration with PresGen-Core system for automated, AI-powered presentation generation based on assessment results and knowledge gaps. Creates personalized learning content, study materials, and remediation presentations tailored to individual user needs and certification requirements.

## 4.1 PresGen-Core Service Integration

### 4.1.1 Core Service Client
```python
# /presgen-assess/src/integrations/presgen/core_client.py
import httpx
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class PresentationStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class PresentationRequest:
    """Request structure for PresGen-Core presentation generation."""
    content_source: str  # Knowledge base or text content
    target_audience: str
    presentation_type: str  # "remediation", "overview", "deep_dive", "assessment_prep"
    slide_count: int
    focus_areas: List[str]
    learning_objectives: List[str]
    user_profile: Dict[str, Any]
    customization_preferences: Dict[str, Any]
    output_format: str = "google_slides"
    template_style: str = "professional"

@dataclass
class PresentationResult:
    """Result structure from PresGen-Core generation."""
    presentation_id: str
    status: PresentationStatus
    presentation_url: Optional[str]
    slide_count: int
    created_at: datetime
    completed_at: Optional[datetime]
    metadata: Dict[str, Any]
    error_message: Optional[str] = None

class PresGenCoreClient:
    """
    Client for communicating with PresGen-Core service.
    Handles presentation generation requests and monitoring.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 300,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries

        # Configure HTTP client with retries and timeouts
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "PresGen-Assess/1.0"
            }
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def create_presentation(
        self,
        request: PresentationRequest
    ) -> PresentationResult:
        """
        Submit a presentation generation request to PresGen-Core.
        Returns presentation ID and initial status.
        """
        try:
            endpoint = f"{self.base_url}/api/v1/presentations"

            # Convert request to JSON
            request_data = asdict(request)

            response = await self._make_request(
                method="POST",
                url=endpoint,
                json=request_data
            )

            # Parse response
            result_data = response.json()

            return PresentationResult(
                presentation_id=result_data["presentation_id"],
                status=PresentationStatus(result_data["status"]),
                presentation_url=result_data.get("presentation_url"),
                slide_count=result_data.get("slide_count", 0),
                created_at=datetime.fromisoformat(result_data["created_at"]),
                completed_at=None,
                metadata=result_data.get("metadata", {})
            )

        except Exception as e:
            logger.error(f"Failed to create presentation: {str(e)}")
            raise

    async def get_presentation_status(
        self,
        presentation_id: str
    ) -> PresentationResult:
        """Get current status of a presentation generation job."""
        try:
            endpoint = f"{self.base_url}/api/v1/presentations/{presentation_id}"

            response = await self._make_request(
                method="GET",
                url=endpoint
            )

            result_data = response.json()

            return PresentationResult(
                presentation_id=presentation_id,
                status=PresentationStatus(result_data["status"]),
                presentation_url=result_data.get("presentation_url"),
                slide_count=result_data.get("slide_count", 0),
                created_at=datetime.fromisoformat(result_data["created_at"]),
                completed_at=datetime.fromisoformat(result_data["completed_at"]) if result_data.get("completed_at") else None,
                metadata=result_data.get("metadata", {}),
                error_message=result_data.get("error_message")
            )

        except Exception as e:
            logger.error(f"Failed to get presentation status: {str(e)}")
            raise

    async def wait_for_completion(
        self,
        presentation_id: str,
        poll_interval: int = 10,
        max_wait_time: int = 1800  # 30 minutes
    ) -> PresentationResult:
        """
        Wait for presentation generation to complete.
        Polls status until completion or timeout.
        """
        start_time = datetime.utcnow()
        max_wait_delta = timedelta(seconds=max_wait_time)

        while datetime.utcnow() - start_time < max_wait_delta:
            try:
                result = await self.get_presentation_status(presentation_id)

                if result.status in [PresentationStatus.COMPLETED, PresentationStatus.FAILED, PresentationStatus.CANCELLED]:
                    return result

                logger.info(f"Presentation {presentation_id} status: {result.status.value}")
                await asyncio.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Error polling presentation status: {str(e)}")
                await asyncio.sleep(poll_interval)

        # Timeout reached
        raise TimeoutError(f"Presentation generation timed out after {max_wait_time} seconds")

    async def cancel_presentation(self, presentation_id: str) -> bool:
        """Cancel a presentation generation job."""
        try:
            endpoint = f"{self.base_url}/api/v1/presentations/{presentation_id}/cancel"

            response = await self._make_request(
                method="POST",
                url=endpoint
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Failed to cancel presentation: {str(e)}")
            return False

    async def list_presentations(
        self,
        user_id: Optional[str] = None,
        status: Optional[PresentationStatus] = None,
        limit: int = 50
    ) -> List[PresentationResult]:
        """List presentations with optional filtering."""
        try:
            endpoint = f"{self.base_url}/api/v1/presentations"

            params = {"limit": limit}
            if user_id:
                params["user_id"] = user_id
            if status:
                params["status"] = status.value

            response = await self._make_request(
                method="GET",
                url=endpoint,
                params=params
            )

            result_data = response.json()
            presentations = []

            for item in result_data.get("presentations", []):
                presentations.append(PresentationResult(
                    presentation_id=item["presentation_id"],
                    status=PresentationStatus(item["status"]),
                    presentation_url=item.get("presentation_url"),
                    slide_count=item.get("slide_count", 0),
                    created_at=datetime.fromisoformat(item["created_at"]),
                    completed_at=datetime.fromisoformat(item["completed_at"]) if item.get("completed_at") else None,
                    metadata=item.get("metadata", {}),
                    error_message=item.get("error_message")
                ))

            return presentations

        except Exception as e:
            logger.error(f"Failed to list presentations: {str(e)}")
            raise

    async def get_presentation_content(
        self,
        presentation_id: str
    ) -> Dict[str, Any]:
        """Get detailed content of a completed presentation."""
        try:
            endpoint = f"{self.base_url}/api/v1/presentations/{presentation_id}/content"

            response = await self._make_request(
                method="GET",
                url=endpoint
            )

            return response.json()

        except Exception as e:
            logger.error(f"Failed to get presentation content: {str(e)}")
            raise

    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                response = await self.client.request(method, url, **kwargs)

                if response.status_code == 429:  # Rate limited
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response

            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code < 500:  # Client error, don't retry
                    raise

                # Server error, retry with backoff
                wait_time = 2 ** attempt
                logger.warning(f"Server error, retrying in {wait_time} seconds (attempt {attempt + 1})")
                await asyncio.sleep(wait_time)

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                wait_time = 2 ** attempt
                logger.warning(f"Connection error, retrying in {wait_time} seconds (attempt {attempt + 1})")
                await asyncio.sleep(wait_time)

        raise last_exception

class PresentationOrchestrator:
    """
    Orchestrates presentation generation workflows based on assessment results.
    Manages multiple presentation requests and handles complex generation logic.
    """

    def __init__(
        self,
        presgen_client: PresGenCoreClient,
        knowledge_base_service,
        google_services
    ):
        self.presgen_client = presgen_client
        self.knowledge_base_service = knowledge_base_service
        self.google_services = google_services

    async def generate_remediation_presentations(
        self,
        assessment_results: Dict[str, Any],
        user_profile: Dict[str, Any],
        certification_name: str
    ) -> List[PresentationResult]:
        """
        Generate personalized remediation presentations based on assessment gaps.
        Creates targeted presentations for each identified knowledge gap.
        """
        gap_analysis = assessment_results.get("gap_analysis", {})
        weak_areas = gap_analysis.get("weak_areas", [])

        if not weak_areas:
            logger.info("No weak areas identified, skipping remediation presentation generation")
            return []

        presentations = []

        # Generate presentation for each weak area
        for area in weak_areas:
            try:
                # Get relevant knowledge base content for this area
                knowledge_content = await self.knowledge_base_service.search_content(
                    collection_name=certification_name,
                    query_terms=[area],
                    content_types=["concept", "procedure", "example"],
                    limit=20
                )

                # Create presentation request
                request = PresentationRequest(
                    content_source=self._format_knowledge_content(knowledge_content),
                    target_audience=f"{certification_name} certification candidate",
                    presentation_type="remediation",
                    slide_count=self._calculate_slide_count(area, knowledge_content),
                    focus_areas=[area],
                    learning_objectives=self._generate_learning_objectives(area, gap_analysis),
                    user_profile=user_profile,
                    customization_preferences=self._extract_customization_preferences(user_profile),
                    template_style=self._select_template_style(user_profile)
                )

                # Submit generation request
                result = await self.presgen_client.create_presentation(request)
                presentations.append(result)

                logger.info(f"Created remediation presentation for {area}: {result.presentation_id}")

            except Exception as e:
                logger.error(f"Failed to create remediation presentation for {area}: {str(e)}")

        return presentations

    async def generate_overview_presentation(
        self,
        certification_name: str,
        user_profile: Dict[str, Any],
        target_domains: Optional[List[str]] = None
    ) -> PresentationResult:
        """
        Generate comprehensive overview presentation for certification.
        Covers all major domains and concepts.
        """
        try:
            # Get overview content from knowledge base
            if target_domains:
                query_terms = target_domains
            else:
                # Get all domains for this certification
                certification_info = await self.knowledge_base_service.get_certification_info(
                    certification_name
                )
                query_terms = certification_info.get("domains", [])

            knowledge_content = await self.knowledge_base_service.search_content(
                collection_name=certification_name,
                query_terms=query_terms,
                content_types=["overview", "concept", "domain_summary"],
                limit=50
            )

            # Create presentation request
            request = PresentationRequest(
                content_source=self._format_knowledge_content(knowledge_content),
                target_audience=f"{certification_name} certification candidate",
                presentation_type="overview",
                slide_count=min(30, len(query_terms) * 4),  # ~4 slides per domain
                focus_areas=query_terms,
                learning_objectives=self._generate_overview_objectives(certification_name, query_terms),
                user_profile=user_profile,
                customization_preferences=self._extract_customization_preferences(user_profile),
                template_style="professional"
            )

            result = await self.presgen_client.create_presentation(request)
            logger.info(f"Created overview presentation: {result.presentation_id}")

            return result

        except Exception as e:
            logger.error(f"Failed to create overview presentation: {str(e)}")
            raise

    async def generate_assessment_prep_presentation(
        self,
        certification_name: str,
        assessment_results: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> PresentationResult:
        """
        Generate assessment preparation presentation focusing on exam strategies
        and areas where user performed poorly.
        """
        try:
            # Analyze assessment performance
            performance_analysis = self._analyze_assessment_performance(assessment_results)

            # Get content for challenging areas
            challenging_areas = performance_analysis.get("challenging_areas", [])
            exam_strategies_content = await self.knowledge_base_service.search_content(
                collection_name=certification_name,
                query_terms=challenging_areas + ["exam strategy", "test taking"],
                content_types=["strategy", "tips", "practice"],
                limit=25
            )

            # Create presentation request
            request = PresentationRequest(
                content_source=self._format_knowledge_content(exam_strategies_content),
                target_audience=f"{certification_name} exam candidate",
                presentation_type="assessment_prep",
                slide_count=20,
                focus_areas=challenging_areas,
                learning_objectives=self._generate_exam_prep_objectives(performance_analysis),
                user_profile=user_profile,
                customization_preferences={
                    **self._extract_customization_preferences(user_profile),
                    "include_practice_questions": True,
                    "include_exam_tips": True,
                    "highlight_common_mistakes": True
                },
                template_style="exam_focused"
            )

            result = await self.presgen_client.create_presentation(request)
            logger.info(f"Created assessment prep presentation: {result.presentation_id}")

            return result

        except Exception as e:
            logger.error(f"Failed to create assessment prep presentation: {str(e)}")
            raise

    async def batch_generate_presentations(
        self,
        requests: List[PresentationRequest],
        max_concurrent: int = 3
    ) -> List[PresentationResult]:
        """
        Generate multiple presentations concurrently with controlled concurrency.
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_single(request: PresentationRequest) -> PresentationResult:
            async with semaphore:
                return await self.presgen_client.create_presentation(request)

        # Submit all requests
        tasks = [generate_single(request) for request in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch generation failed for request {i}: {str(result)}")
            else:
                successful_results.append(result)

        return successful_results

    def _format_knowledge_content(self, knowledge_content: List[Dict[str, Any]]) -> str:
        """Format knowledge base content for PresGen-Core consumption."""
        formatted_sections = []

        for item in knowledge_content:
            section = f"## {item.get('title', 'Untitled')}\n\n"

            if item.get('summary'):
                section += f"{item['summary']}\n\n"

            if item.get('content'):
                section += f"{item['content']}\n\n"

            if item.get('key_points'):
                section += "Key Points:\n"
                for point in item['key_points']:
                    section += f"- {point}\n"
                section += "\n"

            formatted_sections.append(section)

        return "\n".join(formatted_sections)

    def _calculate_slide_count(self, focus_area: str, knowledge_content: List[Dict[str, Any]]) -> int:
        """Calculate appropriate slide count based on content complexity."""
        base_slides = 8  # Minimum slides for any topic

        # Add slides based on content amount
        content_slides = min(len(knowledge_content) // 2, 12)

        # Adjust for topic complexity (this could be enhanced with ML)
        complexity_multiplier = 1.0
        if any(keyword in focus_area.lower() for keyword in ["advanced", "architecture", "security"]):
            complexity_multiplier = 1.3
        elif any(keyword in focus_area.lower() for keyword in ["basic", "intro", "overview"]):
            complexity_multiplier = 0.8

        total_slides = int((base_slides + content_slides) * complexity_multiplier)
        return min(max(total_slides, 5), 25)  # Between 5 and 25 slides

    def _generate_learning_objectives(self, focus_area: str, gap_analysis: Dict[str, Any]) -> List[str]:
        """Generate learning objectives for a specific focus area."""
        objectives = [
            f"Understand core concepts in {focus_area}",
            f"Apply {focus_area} knowledge to practical scenarios",
            f"Identify common issues and solutions in {focus_area}"
        ]

        # Add specific objectives based on gap analysis
        gap_details = gap_analysis.get("area_details", {}).get(focus_area, {})
        if gap_details.get("weak_concepts"):
            objectives.extend([
                f"Master {concept}" for concept in gap_details["weak_concepts"][:2]
            ])

        return objectives

    def _generate_overview_objectives(self, certification_name: str, domains: List[str]) -> List[str]:
        """Generate learning objectives for overview presentation."""
        return [
            f"Understand the scope and structure of {certification_name}",
            "Identify key domains and their relationships",
            "Recognize exam objectives and requirements"
        ] + [f"Gain foundational knowledge in {domain}" for domain in domains[:3]]

    def _generate_exam_prep_objectives(self, performance_analysis: Dict[str, Any]) -> List[str]:
        """Generate objectives for exam preparation presentation."""
        objectives = [
            "Develop effective exam strategies and time management",
            "Identify and avoid common exam mistakes",
            "Practice with challenging question types"
        ]

        challenging_areas = performance_analysis.get("challenging_areas", [])
        if challenging_areas:
            objectives.extend([
                f"Strengthen understanding in {area}" for area in challenging_areas[:2]
            ])

        return objectives

    def _extract_customization_preferences(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Extract presentation customization preferences from user profile."""
        preferences = {}

        # Learning style preferences
        learning_style = user_profile.get("preferences", {}).get("learning_style", [])
        if "Visual (diagrams, charts, presentations)" in learning_style:
            preferences["emphasize_visuals"] = True
        if "Hands-on (labs, practice exercises)" in learning_style:
            preferences["include_practical_examples"] = True

        # Experience level adjustments
        experience = user_profile.get("demographics", {}).get("experience_level", "")
        if "0-1 years" in experience or "1-2 years" in experience:
            preferences["detail_level"] = "beginner"
            preferences["include_definitions"] = True
        elif "10+ years" in experience:
            preferences["detail_level"] = "advanced"
            preferences["focus_on_edge_cases"] = True
        else:
            preferences["detail_level"] = "intermediate"

        return preferences

    def _select_template_style(self, user_profile: Dict[str, Any]) -> str:
        """Select appropriate template style based on user profile."""
        role = user_profile.get("demographics", {}).get("role", "").lower()

        if any(keyword in role for keyword in ["developer", "engineer", "technical"]):
            return "technical"
        elif any(keyword in role for keyword in ["manager", "director", "lead"]):
            return "executive"
        elif any(keyword in role for keyword in ["student", "junior", "entry"]):
            return "educational"
        else:
            return "professional"

    def _analyze_assessment_performance(self, assessment_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze assessment performance to identify challenging areas."""
        analysis = {
            "overall_score": assessment_results.get("overall_score", 0),
            "challenging_areas": [],
            "strong_areas": [],
            "improvement_needed": []
        }

        # Analyze domain-specific performance
        domain_scores = assessment_results.get("domain_scores", {})
        for domain, score in domain_scores.items():
            if score < 60:
                analysis["challenging_areas"].append(domain)
                analysis["improvement_needed"].append(domain)
            elif score >= 80:
                analysis["strong_areas"].append(domain)

        # Analyze question-level performance
        question_analysis = assessment_results.get("question_analysis", {})
        for question_id, q_data in question_analysis.items():
            if q_data.get("correct", False) is False:
                topic = q_data.get("topic")
                if topic and topic not in analysis["challenging_areas"]:
                    analysis["challenging_areas"].append(topic)

        return analysis
```

### 4.1.2 Content Generation Pipeline
```python
# /presgen-assess/src/integrations/presgen/content_pipeline.py
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class ContentType(Enum):
    REMEDIATION = "remediation"
    OVERVIEW = "overview"
    ASSESSMENT_PREP = "assessment_prep"
    DEEP_DIVE = "deep_dive"
    QUICK_REVIEW = "quick_review"

@dataclass
class ContentGenerationJob:
    """Job definition for content generation pipeline."""
    job_id: str
    user_id: str
    certification_name: str
    content_type: ContentType
    priority: int  # 1 = highest, 5 = lowest
    parameters: Dict[str, Any]
    created_at: datetime
    status: str = "pending"

class ContentGenerationPipeline:
    """
    Pipeline for generating various types of educational content
    based on assessment results and user needs.
    """

    def __init__(
        self,
        presgen_client: PresGenCoreClient,
        knowledge_base_service,
        assessment_analyzer,
        notification_service
    ):
        self.presgen_client = presgen_client
        self.knowledge_base_service = knowledge_base_service
        self.assessment_analyzer = assessment_analyzer
        self.notification_service = notification_service
        self.job_queue = asyncio.PriorityQueue()
        self.active_jobs = {}
        self.pipeline_active = False

    async def start_pipeline(self, max_workers: int = 3):
        """Start the content generation pipeline with specified number of workers."""
        self.pipeline_active = True

        # Start worker coroutines
        workers = [
            self._worker(f"worker_{i}")
            for i in range(max_workers)
        ]

        await asyncio.gather(*workers)

    async def stop_pipeline(self):
        """Stop the content generation pipeline."""
        self.pipeline_active = False

    async def queue_content_generation(
        self,
        user_id: str,
        certification_name: str,
        content_type: ContentType,
        parameters: Dict[str, Any],
        priority: int = 3
    ) -> str:
        """Queue a content generation job."""
        job_id = f"{user_id}_{content_type.value}_{datetime.utcnow().timestamp()}"

        job = ContentGenerationJob(
            job_id=job_id,
            user_id=user_id,
            certification_name=certification_name,
            content_type=content_type,
            priority=priority,
            parameters=parameters,
            created_at=datetime.utcnow()
        )

        # Add to priority queue (lower number = higher priority)
        await self.job_queue.put((priority, job))

        logger.info(f"Queued content generation job: {job_id}")
        return job_id

    async def _worker(self, worker_name: str):
        """Worker coroutine for processing content generation jobs."""
        logger.info(f"Started content generation worker: {worker_name}")

        while self.pipeline_active:
            try:
                # Get job from queue with timeout
                priority, job = await asyncio.wait_for(
                    self.job_queue.get(),
                    timeout=1.0
                )

                await self._process_content_job(job, worker_name)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {str(e)}")

    async def _process_content_job(self, job: ContentGenerationJob, worker_name: str):
        """Process a single content generation job."""
        try:
            job.status = "processing"
            self.active_jobs[job.job_id] = job

            logger.info(f"Worker {worker_name} processing job {job.job_id}")

            # Process based on content type
            if job.content_type == ContentType.REMEDIATION:
                result = await self._generate_remediation_content(job)
            elif job.content_type == ContentType.OVERVIEW:
                result = await self._generate_overview_content(job)
            elif job.content_type == ContentType.ASSESSMENT_PREP:
                result = await self._generate_assessment_prep_content(job)
            elif job.content_type == ContentType.DEEP_DIVE:
                result = await self._generate_deep_dive_content(job)
            elif job.content_type == ContentType.QUICK_REVIEW:
                result = await self._generate_quick_review_content(job)
            else:
                raise ValueError(f"Unknown content type: {job.content_type}")

            job.status = "completed"

            # Notify user of completion
            await self.notification_service.notify_user(
                user_id=job.user_id,
                message=f"Your {job.content_type.value} content is ready!",
                data={
                    "job_id": job.job_id,
                    "content_url": result.presentation_url,
                    "slide_count": result.slide_count
                }
            )

            logger.info(f"Completed content generation job: {job.job_id}")

        except Exception as e:
            job.status = "failed"
            logger.error(f"Content generation job {job.job_id} failed: {str(e)}")

            # Notify user of failure
            await self.notification_service.notify_user(
                user_id=job.user_id,
                message=f"Content generation failed: {str(e)}",
                data={"job_id": job.job_id}
            )

        finally:
            if job.job_id in self.active_jobs:
                del self.active_jobs[job.job_id]

    async def _generate_remediation_content(self, job: ContentGenerationJob) -> PresentationResult:
        """Generate remediation content for knowledge gaps."""
        assessment_results = job.parameters.get("assessment_results", {})
        user_profile = job.parameters.get("user_profile", {})

        # Analyze gaps from assessment
        gap_analysis = await self.assessment_analyzer.analyze_knowledge_gaps(
            assessment_results, job.certification_name
        )

        # Get knowledge base content for weak areas
        weak_areas = gap_analysis.get("weak_areas", [])
        knowledge_content = await self.knowledge_base_service.get_remediation_content(
            collection_name=job.certification_name,
            focus_areas=weak_areas,
            user_profile=user_profile
        )

        # Create presentation request
        request = PresentationRequest(
            content_source=self._format_content_for_presgen(knowledge_content),
            target_audience=f"{job.certification_name} learner needing remediation",
            presentation_type="remediation",
            slide_count=self._calculate_remediation_slides(weak_areas),
            focus_areas=weak_areas,
            learning_objectives=self._generate_remediation_objectives(gap_analysis),
            user_profile=user_profile,
            customization_preferences={
                "include_examples": True,
                "include_practice_exercises": True,
                "emphasize_misconceptions": True,
                "progressive_difficulty": True
            }
        )

        # Generate presentation
        result = await self.presgen_client.create_presentation(request)

        # Wait for completion
        completed_result = await self.presgen_client.wait_for_completion(
            result.presentation_id,
            max_wait_time=1800  # 30 minutes
        )

        return completed_result

    async def _generate_overview_content(self, job: ContentGenerationJob) -> PresentationResult:
        """Generate overview content for certification."""
        user_profile = job.parameters.get("user_profile", {})
        target_domains = job.parameters.get("target_domains")

        # Get certification overview content
        overview_content = await self.knowledge_base_service.get_overview_content(
            collection_name=job.certification_name,
            target_domains=target_domains
        )

        # Create presentation request
        request = PresentationRequest(
            content_source=self._format_content_for_presgen(overview_content),
            target_audience=f"{job.certification_name} certification candidate",
            presentation_type="overview",
            slide_count=25,
            focus_areas=target_domains or [],
            learning_objectives=self._generate_overview_objectives(job.certification_name),
            user_profile=user_profile,
            customization_preferences={
                "include_roadmap": True,
                "include_prerequisites": True,
                "highlight_exam_objectives": True
            }
        )

        result = await self.presgen_client.create_presentation(request)
        return await self.presgen_client.wait_for_completion(result.presentation_id)

    async def _generate_assessment_prep_content(self, job: ContentGenerationJob) -> PresentationResult:
        """Generate assessment preparation content."""
        assessment_results = job.parameters.get("assessment_results", {})
        user_profile = job.parameters.get("user_profile", {})

        # Analyze performance patterns
        performance_analysis = await self.assessment_analyzer.analyze_performance_patterns(
            assessment_results
        )

        # Get exam preparation content
        prep_content = await self.knowledge_base_service.get_exam_prep_content(
            collection_name=job.certification_name,
            challenging_areas=performance_analysis.get("challenging_areas", []),
            question_types=performance_analysis.get("difficult_question_types", [])
        )

        request = PresentationRequest(
            content_source=self._format_content_for_presgen(prep_content),
            target_audience=f"{job.certification_name} exam candidate",
            presentation_type="assessment_prep",
            slide_count=20,
            focus_areas=performance_analysis.get("challenging_areas", []),
            learning_objectives=self._generate_exam_prep_objectives(performance_analysis),
            user_profile=user_profile,
            customization_preferences={
                "include_test_strategies": True,
                "include_time_management": True,
                "include_practice_questions": True,
                "highlight_common_mistakes": True
            }
        )

        result = await self.presgen_client.create_presentation(request)
        return await self.presgen_client.wait_for_completion(result.presentation_id)

    async def _generate_deep_dive_content(self, job: ContentGenerationJob) -> PresentationResult:
        """Generate deep-dive content for specific topics."""
        topic = job.parameters.get("topic")
        user_profile = job.parameters.get("user_profile", {})

        if not topic:
            raise ValueError("Deep dive content requires a specific topic")

        # Get detailed content for the topic
        deep_content = await self.knowledge_base_service.get_detailed_content(
            collection_name=job.certification_name,
            topic=topic,
            include_advanced=True
        )

        request = PresentationRequest(
            content_source=self._format_content_for_presgen(deep_content),
            target_audience=f"{job.certification_name} advanced learner",
            presentation_type="deep_dive",
            slide_count=30,
            focus_areas=[topic],
            learning_objectives=self._generate_deep_dive_objectives(topic),
            user_profile=user_profile,
            customization_preferences={
                "include_advanced_concepts": True,
                "include_real_world_examples": True,
                "include_troubleshooting": True,
                "detail_level": "expert"
            }
        )

        result = await self.presgen_client.create_presentation(request)
        return await self.presgen_client.wait_for_completion(result.presentation_id)

    async def _generate_quick_review_content(self, job: ContentGenerationJob) -> PresentationResult:
        """Generate quick review content for exam preparation."""
        topics = job.parameters.get("topics", [])
        user_profile = job.parameters.get("user_profile", {})

        # Get summary content for topics
        review_content = await self.knowledge_base_service.get_summary_content(
            collection_name=job.certification_name,
            topics=topics
        )

        request = PresentationRequest(
            content_source=self._format_content_for_presgen(review_content),
            target_audience=f"{job.certification_name} exam candidate",
            presentation_type="quick_review",
            slide_count=15,
            focus_areas=topics,
            learning_objectives=self._generate_review_objectives(topics),
            user_profile=user_profile,
            customization_preferences={
                "condensed_format": True,
                "bullet_points": True,
                "key_facts_only": True,
                "include_mnemonics": True
            }
        )

        result = await self.presgen_client.create_presentation(request)
        return await self.presgen_client.wait_for_completion(result.presentation_id)

    def _format_content_for_presgen(self, content_items: List[Dict[str, Any]]) -> str:
        """Format knowledge base content for PresGen consumption."""
        formatted_content = []

        for item in content_items:
            section = f"# {item.get('title', 'Untitled Section')}\n\n"

            if item.get('summary'):
                section += f"## Summary\n{item['summary']}\n\n"

            if item.get('key_points'):
                section += "## Key Points\n"
                for point in item['key_points']:
                    section += f"- {point}\n"
                section += "\n"

            if item.get('content'):
                section += f"## Details\n{item['content']}\n\n"

            if item.get('examples'):
                section += "## Examples\n"
                for example in item['examples']:
                    section += f"**{example.get('title', 'Example')}**: {example.get('description', '')}\n\n"

            if item.get('best_practices'):
                section += "## Best Practices\n"
                for practice in item['best_practices']:
                    section += f"- {practice}\n"
                section += "\n"

            formatted_content.append(section)

        return "\n---\n\n".join(formatted_content)

    def _calculate_remediation_slides(self, weak_areas: List[str]) -> int:
        """Calculate appropriate number of slides for remediation content."""
        base_slides = 5  # Introduction, summary, next steps
        per_area_slides = 8  # Concept, examples, practice, assessment

        total_slides = base_slides + (len(weak_areas) * per_area_slides)
        return min(total_slides, 40)  # Cap at 40 slides

    def _generate_remediation_objectives(self, gap_analysis: Dict[str, Any]) -> List[str]:
        """Generate learning objectives for remediation content."""
        weak_areas = gap_analysis.get("weak_areas", [])

        objectives = [
            "Identify and understand knowledge gaps",
            "Apply corrective learning strategies"
        ]

        for area in weak_areas[:3]:  # Top 3 areas
            objectives.append(f"Master key concepts in {area}")
            objectives.append(f"Practice applying {area} knowledge")

        return objectives

    def _generate_overview_objectives(self, certification_name: str) -> List[str]:
        """Generate learning objectives for overview content."""
        return [
            f"Understand the scope and structure of {certification_name}",
            "Identify key domains and exam objectives",
            "Develop a study plan and timeline",
            "Recognize prerequisites and recommended experience",
            "Understand exam format and question types"
        ]

    def _generate_exam_prep_objectives(self, performance_analysis: Dict[str, Any]) -> List[str]:
        """Generate learning objectives for exam preparation."""
        objectives = [
            "Develop effective exam strategies",
            "Manage time efficiently during the exam",
            "Recognize and avoid common mistakes",
            "Practice with challenging question types"
        ]

        challenging_areas = performance_analysis.get("challenging_areas", [])
        for area in challenging_areas[:2]:
            objectives.append(f"Strengthen knowledge in {area}")

        return objectives

    def _generate_deep_dive_objectives(self, topic: str) -> List[str]:
        """Generate learning objectives for deep-dive content."""
        return [
            f"Gain comprehensive understanding of {topic}",
            f"Explore advanced concepts and edge cases in {topic}",
            f"Apply {topic} knowledge to complex scenarios",
            f"Troubleshoot common issues related to {topic}",
            f"Implement best practices for {topic}"
        ]

    def _generate_review_objectives(self, topics: List[str]) -> List[str]:
        """Generate learning objectives for quick review content."""
        return [
            "Quickly review key concepts before the exam",
            "Reinforce understanding of critical topics",
            "Identify areas needing last-minute review"
        ] + [f"Review essential facts about {topic}" for topic in topics[:2]]
```

This completes Phase 4 - PresGen-Core Integration, providing comprehensive integration with the presentation generation system for creating personalized learning content.

## Implementation Roadmap (Detailed)

1. **API Contract Alignment**
   - Formalize request/response contracts between PresGen-Assess and PresGen-Core (slide quotas, themes, asset links) via shared schema package.
   - Implement adapter layer translating assessment outputs into PresGen prompt payloads.
2. **Content Orchestration**
   - Build pipeline that ingests gap-analysis results, maps them to storyline segments, and sequences modules for slide generation.
   - Support multiple templates (executive summary, deep dive) with configuration flags.
3. **Asset Management**
   - Store generated presentations (slide IDs, share links) in `generated_content_urls` and replicate metadata to Google Drive structure.
4. **Error Recovery & Idempotency**
   - Detect partial presentation generations, allow resumption, and avoid duplicate slide decks.
5. **Workflow Hooks**
   - Update workflow statuses (`generating_presentation`, `presentations_generated`) and emit notifications when assets ready.

## Test-Driven Development Strategy

1. **Adapter Tests**
   - TDD transformation functions converting gap analysis into PresGen content sections, ensuring deterministic outputs.
2. **API Interaction Tests**
   - Mock PresGen-Core endpoints to simulate successes, partial failures, and timeouts, asserting retries and error reporting.
3. **Asset Persistence Tests**
   - Verify presentation metadata is stored correctly and accessible through API detail endpoints.
4. **Workflow Progress Tests**
   - Ensure status changes happen only after successful responses and that failures roll back/mark workflows accordingly.

## Logging & Observability Enhancements

1. **Integration Logs**
   - Log each PresGen-Core call with payload summary, asset IDs, and latency.
2. **Metrics**
   - Track number of presentations generated, success vs failure rates, and average slide generation time.
3. **Audit Trail**
   - Persist version history of generated decks and link to underlying assessment data for traceability.
4. **Alerting**
   - Notify on repeated generation failures, large latency spikes, or asset persistence errors.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create detailed Phase 1 document - Google APIs Foundation", "status": "completed", "activeForm": "Creating detailed Phase 1 document - Google APIs Foundation"}, {"content": "Create detailed Phase 2 document - Google Forms Automation", "status": "completed", "activeForm": "Creating detailed Phase 2 document - Google Forms Automation"}, {"content": "Create detailed Phase 3 document - Response Collection Pipeline", "status": "completed", "activeForm": "Creating detailed Phase 3 document - Response Collection Pipeline"}, {"content": "Create detailed Phase 4 document - PresGen-Core Integration", "status": "completed", "activeForm": "Creating detailed Phase 4 document - PresGen-Core Integration"}, {"content": "Create detailed Phase 5 document - PresGen-Avatar Integration", "status": "in_progress", "activeForm": "Creating detailed Phase 5 document - PresGen-Avatar Integration"}, {"content": "Fix UUID serialization issue in enhanced logging", "status": "completed", "activeForm": "Fixing UUID serialization issue in enhanced logging"}]
