# Phase 5: PresGen-Avatar Integration
*AI-Powered Video Avatar Generation for Personalized Learning*

## Overview
Integration with PresGen-Avatar system for creating personalized video content with AI-generated avatars. Converts assessment results and knowledge gaps into engaging video presentations with synchronized audio, visual content, and interactive elements tailored to individual learning preferences.

## 5.1 Avatar Generation Service Integration

### 5.1.1 Avatar Service Client
```python
# /presgen-assess/src/integrations/presgen/avatar_client.py
import httpx
import asyncio
from typing import Dict, Any, List, Optional, Union, BinaryIO
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import logging
from enum import Enum
import base64
import io

logger = logging.getLogger(__name__)

class AvatarStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class VideoQuality(Enum):
    HD = "1080p"
    STANDARD = "720p"
    MOBILE = "480p"

@dataclass
class AvatarRequest:
    """Request structure for PresGen-Avatar video generation."""
    script_content: str
    avatar_config: Dict[str, Any]
    voice_config: Dict[str, Any]
    video_config: Dict[str, Any]
    presentation_slides: Optional[List[str]] = None
    background_music: Optional[str] = None
    target_duration_minutes: Optional[int] = None
    quality: VideoQuality = VideoQuality.HD

@dataclass
class AvatarResult:
    """Result structure from PresGen-Avatar generation."""
    video_id: str
    status: AvatarStatus
    video_url: Optional[str]
    thumbnail_url: Optional[str]
    duration_seconds: Optional[float]
    file_size_mb: Optional[float]
    created_at: datetime
    completed_at: Optional[datetime]
    metadata: Dict[str, Any]
    error_message: Optional[str] = None

class PresGenAvatarClient:
    """
    Client for communicating with PresGen-Avatar service.
    Handles video generation requests, avatar customization, and monitoring.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 600,  # 10 minutes for video processing
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries

        # Configure HTTP client with extended timeouts for video processing
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "PresGen-Assess-Avatar/1.0"
            }
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def create_avatar_video(
        self,
        request: AvatarRequest
    ) -> AvatarResult:
        """
        Submit an avatar video generation request to PresGen-Avatar.
        Returns video ID and initial status.
        """
        try:
            endpoint = f"{self.base_url}/api/v1/avatar/videos"

            # Convert request to JSON
            request_data = asdict(request)

            response = await self._make_request(
                method="POST",
                url=endpoint,
                json=request_data
            )

            result_data = response.json()

            return AvatarResult(
                video_id=result_data["video_id"],
                status=AvatarStatus(result_data["status"]),
                video_url=result_data.get("video_url"),
                thumbnail_url=result_data.get("thumbnail_url"),
                duration_seconds=result_data.get("duration_seconds"),
                file_size_mb=result_data.get("file_size_mb"),
                created_at=datetime.fromisoformat(result_data["created_at"]),
                completed_at=None,
                metadata=result_data.get("metadata", {})
            )

        except Exception as e:
            logger.error(f"Failed to create avatar video: {str(e)}")
            raise

    async def get_video_status(
        self,
        video_id: str
    ) -> AvatarResult:
        """Get current status of an avatar video generation job."""
        try:
            endpoint = f"{self.base_url}/api/v1/avatar/videos/{video_id}"

            response = await self._make_request(
                method="GET",
                url=endpoint
            )

            result_data = response.json()

            return AvatarResult(
                video_id=video_id,
                status=AvatarStatus(result_data["status"]),
                video_url=result_data.get("video_url"),
                thumbnail_url=result_data.get("thumbnail_url"),
                duration_seconds=result_data.get("duration_seconds"),
                file_size_mb=result_data.get("file_size_mb"),
                created_at=datetime.fromisoformat(result_data["created_at"]),
                completed_at=datetime.fromisoformat(result_data["completed_at"]) if result_data.get("completed_at") else None,
                metadata=result_data.get("metadata", {}),
                error_message=result_data.get("error_message")
            )

        except Exception as e:
            logger.error(f"Failed to get video status: {str(e)}")
            raise

    async def wait_for_completion(
        self,
        video_id: str,
        poll_interval: int = 30,
        max_wait_time: int = 3600  # 1 hour
    ) -> AvatarResult:
        """
        Wait for avatar video generation to complete.
        Polls status until completion or timeout.
        """
        start_time = datetime.utcnow()
        max_wait_delta = timedelta(seconds=max_wait_time)

        while datetime.utcnow() - start_time < max_wait_delta:
            try:
                result = await self.get_video_status(video_id)

                if result.status in [AvatarStatus.COMPLETED, AvatarStatus.FAILED, AvatarStatus.CANCELLED]:
                    return result

                logger.info(f"Avatar video {video_id} status: {result.status.value}")
                await asyncio.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Error polling video status: {str(e)}")
                await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Avatar video generation timed out after {max_wait_time} seconds")

    async def get_available_avatars(self) -> List[Dict[str, Any]]:
        """Get list of available avatar models and configurations."""
        try:
            endpoint = f"{self.base_url}/api/v1/avatar/models"

            response = await self._make_request(
                method="GET",
                url=endpoint
            )

            return response.json().get("avatars", [])

        except Exception as e:
            logger.error(f"Failed to get available avatars: {str(e)}")
            raise

    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voice models and configurations."""
        try:
            endpoint = f"{self.base_url}/api/v1/avatar/voices"

            response = await self._make_request(
                method="GET",
                url=endpoint
            )

            return response.json().get("voices", [])

        except Exception as e:
            logger.error(f"Failed to get available voices: {str(e)}")
            raise

    async def upload_custom_avatar(
        self,
        avatar_name: str,
        image_data: BinaryIO,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Upload a custom avatar image for video generation."""
        try:
            endpoint = f"{self.base_url}/api/v1/avatar/custom"

            # Prepare multipart form data
            files = {
                "avatar_image": ("avatar.jpg", image_data, "image/jpeg"),
                "metadata": (None, json.dumps(metadata or {}), "application/json")
            }

            # Use separate client for file uploads
            async with httpx.AsyncClient(timeout=300) as upload_client:
                upload_client.headers.update({"Authorization": f"Bearer {self.api_key}"})

                response = await upload_client.post(endpoint, files=files)
                response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"Failed to upload custom avatar: {str(e)}")
            raise

    async def download_video(
        self,
        video_id: str,
        output_path: Optional[str] = None
    ) -> bytes:
        """Download completed avatar video."""
        try:
            endpoint = f"{self.base_url}/api/v1/avatar/videos/{video_id}/download"

            response = await self._make_request(
                method="GET",
                url=endpoint
            )

            video_content = response.content

            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(video_content)

            return video_content

        except Exception as e:
            logger.error(f"Failed to download video: {str(e)}")
            raise

    async def cancel_video_generation(self, video_id: str) -> bool:
        """Cancel an avatar video generation job."""
        try:
            endpoint = f"{self.base_url}/api/v1/avatar/videos/{video_id}/cancel"

            response = await self._make_request(
                method="POST",
                url=endpoint
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Failed to cancel video generation: {str(e)}")
            return False

    async def get_generation_metrics(self, video_id: str) -> Dict[str, Any]:
        """Get detailed metrics about video generation process."""
        try:
            endpoint = f"{self.base_url}/api/v1/avatar/videos/{video_id}/metrics"

            response = await self._make_request(
                method="GET",
                url=endpoint
            )

            return response.json()

        except Exception as e:
            logger.error(f"Failed to get generation metrics: {str(e)}")
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
                    retry_after = int(response.headers.get("Retry-After", 120))
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
                wait_time = 2 ** attempt * 5  # Longer backoff for video processing
                logger.warning(f"Server error, retrying in {wait_time} seconds (attempt {attempt + 1})")
                await asyncio.sleep(wait_time)

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                wait_time = 2 ** attempt * 5
                logger.warning(f"Connection error, retrying in {wait_time} seconds (attempt {attempt + 1})")
                await asyncio.sleep(wait_time)

        raise last_exception

class AvatarContentGenerator:
    """
    Generates avatar video content based on assessment results and learning needs.
    Creates personalized educational videos with AI avatars.
    """

    def __init__(
        self,
        avatar_client: PresGenAvatarClient,
        knowledge_base_service,
        assessment_analyzer
    ):
        self.avatar_client = avatar_client
        self.knowledge_base_service = knowledge_base_service
        self.assessment_analyzer = assessment_analyzer

    async def generate_remediation_video(
        self,
        assessment_results: Dict[str, Any],
        user_profile: Dict[str, Any],
        certification_name: str,
        focus_area: str
    ) -> AvatarResult:
        """
        Generate remediation video for specific knowledge gap.
        Creates targeted instructional content with personalized avatar.
        """
        try:
            # Get focused content for the area
            content = await self.knowledge_base_service.get_focused_content(
                collection_name=certification_name,
                focus_area=focus_area,
                include_examples=True,
                include_analogies=True
            )

            # Generate script for the video
            script = await self._generate_remediation_script(
                focus_area, content, user_profile, assessment_results
            )

            # Select appropriate avatar and voice
            avatar_config = await self._select_avatar_config(user_profile)
            voice_config = await self._select_voice_config(user_profile)

            # Configure video settings
            video_config = {
                "background": "educational",
                "include_slides": True,
                "include_annotations": True,
                "pace": self._determine_speaking_pace(user_profile),
                "include_captions": True
            }

            # Create avatar request
            request = AvatarRequest(
                script_content=script,
                avatar_config=avatar_config,
                voice_config=voice_config,
                video_config=video_config,
                target_duration_minutes=self._calculate_video_duration(script),
                quality=VideoQuality.HD
            )

            # Submit generation request
            result = await self.avatar_client.create_avatar_video(request)

            logger.info(f"Created remediation video for {focus_area}: {result.video_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to generate remediation video: {str(e)}")
            raise

    async def generate_overview_video(
        self,
        certification_name: str,
        user_profile: Dict[str, Any],
        target_domains: Optional[List[str]] = None
    ) -> AvatarResult:
        """
        Generate overview video for certification introduction.
        Provides comprehensive introduction to certification topics.
        """
        try:
            # Get overview content
            overview_content = await self.knowledge_base_service.get_overview_content(
                collection_name=certification_name,
                target_domains=target_domains,
                include_roadmap=True
            )

            # Generate comprehensive script
            script = await self._generate_overview_script(
                certification_name, overview_content, user_profile
            )

            # Use professional avatar and voice for overview
            avatar_config = await self._select_professional_avatar()
            voice_config = await self._select_professional_voice()

            video_config = {
                "background": "professional",
                "include_slides": True,
                "include_roadmap": True,
                "pace": "moderate",
                "include_captions": True,
                "branding": True
            }

            request = AvatarRequest(
                script_content=script,
                avatar_config=avatar_config,
                voice_config=voice_config,
                video_config=video_config,
                target_duration_minutes=20,  # Standard overview length
                quality=VideoQuality.HD
            )

            result = await self.avatar_client.create_avatar_video(request)
            logger.info(f"Created overview video: {result.video_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to generate overview video: {str(e)}")
            raise

    async def generate_motivational_video(
        self,
        assessment_results: Dict[str, Any],
        user_profile: Dict[str, Any],
        certification_name: str
    ) -> AvatarResult:
        """
        Generate motivational video based on user progress and goals.
        Provides encouragement and next steps.
        """
        try:
            # Analyze progress and achievements
            progress_analysis = await self.assessment_analyzer.analyze_progress(
                assessment_results, user_profile
            )

            # Generate motivational script
            script = await self._generate_motivational_script(
                progress_analysis, user_profile, certification_name
            )

            # Use engaging avatar and voice
            avatar_config = await self._select_engaging_avatar(user_profile)
            voice_config = await self._select_encouraging_voice()

            video_config = {
                "background": "inspiring",
                "include_progress_graphics": True,
                "include_achievements": True,
                "pace": "energetic",
                "include_captions": True,
                "motivational_music": True
            }

            request = AvatarRequest(
                script_content=script,
                avatar_config=avatar_config,
                voice_config=voice_config,
                video_config=video_config,
                background_music="motivational_light",
                target_duration_minutes=5,  # Short motivational video
                quality=VideoQuality.HD
            )

            result = await self.avatar_client.create_avatar_video(request)
            logger.info(f"Created motivational video: {result.video_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to generate motivational video: {str(e)}")
            raise

    async def generate_practice_session_video(
        self,
        certification_name: str,
        topic: str,
        difficulty_level: str,
        user_profile: Dict[str, Any]
    ) -> AvatarResult:
        """
        Generate interactive practice session video.
        Includes practice questions and guided problem-solving.
        """
        try:
            # Get practice content and questions
            practice_content = await self.knowledge_base_service.get_practice_content(
                collection_name=certification_name,
                topic=topic,
                difficulty=difficulty_level,
                include_questions=True
            )

            # Generate interactive script
            script = await self._generate_practice_script(
                topic, practice_content, difficulty_level, user_profile
            )

            # Use instructional avatar
            avatar_config = await self._select_instructor_avatar()
            voice_config = await self._select_clear_voice()

            video_config = {
                "background": "classroom",
                "include_interactive_elements": True,
                "include_questions": True,
                "pace": "measured",
                "include_captions": True,
                "allow_pauses": True
            }

            request = AvatarRequest(
                script_content=script,
                avatar_config=avatar_config,
                voice_config=voice_config,
                video_config=video_config,
                target_duration_minutes=15,
                quality=VideoQuality.HD
            )

            result = await self.avatar_client.create_avatar_video(request)
            logger.info(f"Created practice session video: {result.video_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to generate practice session video: {str(e)}")
            raise

    async def _generate_remediation_script(
        self,
        focus_area: str,
        content: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        assessment_results: Dict[str, Any]
    ) -> str:
        """Generate script for remediation video."""
        script_parts = []

        # Introduction
        user_name = user_profile.get("respondent_info", {}).get("name", "learner")
        script_parts.append(f"""
        Hello {user_name}! I'm here to help you strengthen your understanding of {focus_area}.
        Based on your recent assessment, this is an area where some additional focus will really benefit your certification preparation.
        Don't worry - everyone has areas to improve, and with the right approach, you'll master this topic.
        """)

        # Content sections
        for item in content[:3]:  # Limit to 3 main concepts
            script_parts.append(f"""
            Let's start with {item.get('title', 'this concept')}.
            {item.get('summary', '')}

            Here's what you need to understand:
            {item.get('content', '')[:500]}...
            """)

            # Add examples if available
            if item.get('examples'):
                example = item['examples'][0]
                script_parts.append(f"""
                Let me give you a practical example:
                {example.get('description', '')}
                This shows how {focus_area} works in real-world scenarios.
                """)

        # Conclusion with encouragement
        script_parts.append(f"""
        Great work following along! Remember, mastering {focus_area} takes practice.
        I recommend reviewing these concepts and then trying some practice questions.
        You're making excellent progress toward your certification goal!
        """)

        return "\n\n".join(script_parts)

    async def _generate_overview_script(
        self,
        certification_name: str,
        content: List[Dict[str, Any]],
        user_profile: Dict[str, Any]
    ) -> str:
        """Generate script for overview video."""
        script_parts = []

        # Welcome and introduction
        script_parts.append(f"""
        Welcome to your comprehensive overview of {certification_name}!
        I'm excited to guide you through this certification journey and help you understand
        what you'll be learning and how to prepare effectively.
        """)

        # Certification overview
        script_parts.append(f"""
        {certification_name} is a valuable certification that validates your expertise
        in this important technology domain. Let me walk you through the key areas
        you'll need to master.
        """)

        # Domain overview
        for item in content:
            if item.get('type') == 'domain':
                script_parts.append(f"""
                {item.get('title', '')} is one of the core domains.
                {item.get('summary', '')}
                This area typically represents about {item.get('exam_weight', '15')}% of the exam.
                """)

        # Study recommendations
        experience = user_profile.get("demographics", {}).get("experience_level", "")
        if "0-1 years" in experience:
            study_time = "3-4 months"
            approach = "Start with fundamentals and build up gradually"
        elif "10+ years" in experience:
            study_time = "6-8 weeks"
            approach = "Focus on certification-specific knowledge and exam strategies"
        else:
            study_time = "8-12 weeks"
            approach = "Balance foundational review with practical application"

        script_parts.append(f"""
        Based on your experience level, I recommend planning for {study_time} of preparation.
        {approach} will be the most effective strategy for you.
        """)

        # Closing motivation
        script_parts.append(f"""
        You're taking a great step toward advancing your career with {certification_name}.
        With focused study and practice, you'll be well-prepared for success.
        Let's begin your learning journey!
        """)

        return "\n\n".join(script_parts)

    async def _generate_motivational_script(
        self,
        progress_analysis: Dict[str, Any],
        user_profile: Dict[str, Any],
        certification_name: str
    ) -> str:
        """Generate script for motivational video."""
        script_parts = []

        user_name = user_profile.get("respondent_info", {}).get("name", "")
        if user_name:
            greeting = f"Hello {user_name}!"
        else:
            greeting = "Hello there!"

        # Progress acknowledgment
        overall_score = progress_analysis.get("overall_score", 0)
        if overall_score >= 80:
            performance_message = "You're doing excellent work! Your scores show you're well on track."
        elif overall_score >= 60:
            performance_message = "You're making solid progress! You're building a strong foundation."
        else:
            performance_message = "Every expert was once a beginner. You're learning and improving with each step."

        script_parts.append(f"""
        {greeting} I wanted to take a moment to recognize your dedication to earning your {certification_name} certification.
        {performance_message}
        """)

        # Achievements highlight
        strong_areas = progress_analysis.get("strong_areas", [])
        if strong_areas:
            script_parts.append(f"""
            You're showing particular strength in areas like {', '.join(strong_areas[:2])}.
            This demonstrates you have the capability to master all aspects of this certification.
            """)

        # Growth mindset encouragement
        script_parts.append(f"""
        Remember, every challenge you encounter is an opportunity to grow stronger.
        The areas where you're working to improve aren't weaknesses - they're your next victories waiting to happen.
        """)

        # Next steps motivation
        script_parts.append(f"""
        Your commitment to learning shows you have what it takes to succeed.
        Keep practicing, stay curious, and trust in your ability to master these concepts.
        You've got this!
        """)

        return "\n\n".join(script_parts)

    async def _generate_practice_script(
        self,
        topic: str,
        content: List[Dict[str, Any]],
        difficulty_level: str,
        user_profile: Dict[str, Any]
    ) -> str:
        """Generate script for practice session video."""
        script_parts = []

        # Introduction to practice session
        script_parts.append(f"""
        Welcome to your {difficulty_level} level practice session on {topic}!
        Today we'll work through some scenarios and questions to reinforce your understanding.
        This is your chance to apply what you've learned in a supportive environment.
        """)

        # Practice questions and explanations
        for i, item in enumerate(content[:3], 1):
            if item.get('question'):
                script_parts.append(f"""
                Practice Question {i}:
                {item['question']}

                Take a moment to think about this. What approach would you take?

                [Pause for thinking]

                Here's how I would approach this:
                {item.get('explanation', '')}

                The key concepts here are: {', '.join(item.get('key_concepts', []))}
                """)

        # Wrap-up and encouragement
        script_parts.append(f"""
        Excellent work! Practice sessions like this help build your confidence and reinforce your knowledge.
        Remember, it's normal to find some questions challenging - that's how you learn and grow.
        Keep practicing, and you'll see your skills continue to develop.
        """)

        return "\n\n".join(script_parts)

    async def _select_avatar_config(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate avatar based on user preferences and demographics."""
        # Get available avatars
        available_avatars = await self.avatar_client.get_available_avatars()

        # Default to professional avatar
        selected_avatar = next(
            (a for a in available_avatars if a.get("type") == "professional"),
            available_avatars[0] if available_avatars else {}
        )

        # Customize based on user preferences
        learning_style = user_profile.get("preferences", {}).get("learning_style", [])

        config = {
            "avatar_id": selected_avatar.get("id", "default_professional"),
            "expression": "friendly",
            "gesture_level": "moderate"
        }

        if "Visual (diagrams, charts, presentations)" in learning_style:
            config["use_gestures"] = True
            config["expression"] = "engaging"

        return config

    async def _select_voice_config(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate voice configuration."""
        available_voices = await self.avatar_client.get_available_voices()

        # Default to clear, professional voice
        selected_voice = next(
            (v for v in available_voices if v.get("style") == "professional"),
            available_voices[0] if available_voices else {}
        )

        config = {
            "voice_id": selected_voice.get("id", "default_professional"),
            "speed": "normal",
            "pitch": "normal",
            "emotion": "neutral"
        }

        # Adjust based on user experience level
        experience = user_profile.get("demographics", {}).get("experience_level", "")
        if "0-1 years" in experience:
            config["speed"] = "slightly_slow"
            config["emotion"] = "encouraging"

        return config

    async def _select_professional_avatar(self) -> Dict[str, Any]:
        """Select professional avatar for overview content."""
        return {
            "avatar_id": "professional_instructor",
            "expression": "confident",
            "gesture_level": "professional",
            "attire": "business_casual"
        }

    async def _select_professional_voice(self) -> Dict[str, Any]:
        """Select professional voice for overview content."""
        return {
            "voice_id": "professional_narrator",
            "speed": "normal",
            "pitch": "normal",
            "emotion": "authoritative"
        }

    async def _select_engaging_avatar(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Select engaging avatar for motivational content."""
        return {
            "avatar_id": "motivational_coach",
            "expression": "enthusiastic",
            "gesture_level": "animated",
            "energy": "high"
        }

    async def _select_encouraging_voice(self) -> Dict[str, Any]:
        """Select encouraging voice for motivational content."""
        return {
            "voice_id": "motivational_speaker",
            "speed": "normal",
            "pitch": "warm",
            "emotion": "encouraging"
        }

    async def _select_instructor_avatar(self) -> Dict[str, Any]:
        """Select instructor avatar for practice sessions."""
        return {
            "avatar_id": "practice_instructor",
            "expression": "helpful",
            "gesture_level": "instructional",
            "interaction_style": "guided"
        }

    async def _select_clear_voice(self) -> Dict[str, Any]:
        """Select clear voice for instructional content."""
        return {
            "voice_id": "clear_instructor",
            "speed": "measured",
            "pitch": "clear",
            "emotion": "patient"
        }

    def _determine_speaking_pace(self, user_profile: Dict[str, Any]) -> str:
        """Determine appropriate speaking pace based on user profile."""
        experience = user_profile.get("demographics", {}).get("experience_level", "")

        if "0-1 years" in experience:
            return "slow"
        elif "10+ years" in experience:
            return "normal"
        else:
            return "moderate"

    def _calculate_video_duration(self, script: str) -> int:
        """Calculate estimated video duration based on script length."""
        word_count = len(script.split())
        # Average speaking rate is ~150 words per minute
        estimated_minutes = word_count / 150
        return max(int(estimated_minutes), 2)  # Minimum 2 minutes
```

### 5.1.2 Video Content Pipeline
```python
# /presgen-assess/src/integrations/presgen/video_pipeline.py
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class VideoContentType(Enum):
    REMEDIATION = "remediation"
    OVERVIEW = "overview"
    MOTIVATIONAL = "motivational"
    PRACTICE_SESSION = "practice_session"
    EXAM_PREP = "exam_prep"
    CELEBRATION = "celebration"

@dataclass
class VideoGenerationJob:
    """Job definition for video content generation pipeline."""
    job_id: str
    user_id: str
    certification_name: str
    video_type: VideoContentType
    priority: int
    parameters: Dict[str, Any]
    created_at: datetime
    status: str = "pending"

class VideoContentPipeline:
    """
    Pipeline for generating avatar video content based on assessment results.
    Manages video generation workflow and delivery.
    """

    def __init__(
        self,
        avatar_client: PresGenAvatarClient,
        content_generator: AvatarContentGenerator,
        google_services,
        notification_service
    ):
        self.avatar_client = avatar_client
        self.content_generator = content_generator
        self.google_services = google_services
        self.notification_service = notification_service
        self.job_queue = asyncio.PriorityQueue()
        self.active_jobs = {}
        self.pipeline_active = False

    async def start_pipeline(self, max_workers: int = 2):
        """Start the video generation pipeline."""
        self.pipeline_active = True

        # Video generation is resource-intensive, use fewer workers
        workers = [
            self._worker(f"video_worker_{i}")
            for i in range(max_workers)
        ]

        await asyncio.gather(*workers)

    async def stop_pipeline(self):
        """Stop the video generation pipeline."""
        self.pipeline_active = False

    async def queue_video_generation(
        self,
        user_id: str,
        certification_name: str,
        video_type: VideoContentType,
        parameters: Dict[str, Any],
        priority: int = 3
    ) -> str:
        """Queue a video generation job."""
        job_id = f"{user_id}_{video_type.value}_{datetime.utcnow().timestamp()}"

        job = VideoGenerationJob(
            job_id=job_id,
            user_id=user_id,
            certification_name=certification_name,
            video_type=video_type,
            priority=priority,
            parameters=parameters,
            created_at=datetime.utcnow()
        )

        await self.job_queue.put((priority, job))

        logger.info(f"Queued video generation job: {job_id}")
        return job_id

    async def generate_personalized_video_series(
        self,
        user_id: str,
        certification_name: str,
        assessment_results: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> List[str]:
        """
        Generate a complete series of personalized videos for a user.
        Returns list of job IDs for tracking.
        """
        job_ids = []

        # Analyze assessment to determine video needs
        gap_analysis = assessment_results.get("gap_analysis", {})
        weak_areas = gap_analysis.get("weak_areas", [])
        overall_score = assessment_results.get("overall_score", 0)

        # Overview video (high priority)
        overview_job_id = await self.queue_video_generation(
            user_id=user_id,
            certification_name=certification_name,
            video_type=VideoContentType.OVERVIEW,
            parameters={"user_profile": user_profile},
            priority=1
        )
        job_ids.append(overview_job_id)

        # Remediation videos for each weak area
        for area in weak_areas[:3]:  # Limit to top 3 areas
            remediation_job_id = await self.queue_video_generation(
                user_id=user_id,
                certification_name=certification_name,
                video_type=VideoContentType.REMEDIATION,
                parameters={
                    "focus_area": area,
                    "assessment_results": assessment_results,
                    "user_profile": user_profile
                },
                priority=2
            )
            job_ids.append(remediation_job_id)

        # Motivational video
        motivational_job_id = await self.queue_video_generation(
            user_id=user_id,
            certification_name=certification_name,
            video_type=VideoContentType.MOTIVATIONAL,
            parameters={
                "assessment_results": assessment_results,
                "user_profile": user_profile
            },
            priority=3
        )
        job_ids.append(motivational_job_id)

        # Exam prep video if score is reasonable
        if overall_score >= 50:
            exam_prep_job_id = await self.queue_video_generation(
                user_id=user_id,
                certification_name=certification_name,
                video_type=VideoContentType.EXAM_PREP,
                parameters={
                    "assessment_results": assessment_results,
                    "user_profile": user_profile
                },
                priority=4
            )
            job_ids.append(exam_prep_job_id)

        return job_ids

    async def _worker(self, worker_name: str):
        """Worker coroutine for processing video generation jobs."""
        logger.info(f"Started video generation worker: {worker_name}")

        while self.pipeline_active:
            try:
                priority, job = await asyncio.wait_for(
                    self.job_queue.get(),
                    timeout=1.0
                )

                await self._process_video_job(job, worker_name)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Video worker {worker_name} error: {str(e)}")

    async def _process_video_job(self, job: VideoGenerationJob, worker_name: str):
        """Process a single video generation job."""
        try:
            job.status = "processing"
            self.active_jobs[job.job_id] = job

            logger.info(f"Worker {worker_name} processing video job {job.job_id}")

            # Generate video based on type
            if job.video_type == VideoContentType.REMEDIATION:
                result = await self._generate_remediation_video(job)
            elif job.video_type == VideoContentType.OVERVIEW:
                result = await self._generate_overview_video(job)
            elif job.video_type == VideoContentType.MOTIVATIONAL:
                result = await self._generate_motivational_video(job)
            elif job.video_type == VideoContentType.PRACTICE_SESSION:
                result = await self._generate_practice_video(job)
            elif job.video_type == VideoContentType.EXAM_PREP:
                result = await self._generate_exam_prep_video(job)
            elif job.video_type == VideoContentType.CELEBRATION:
                result = await self._generate_celebration_video(job)
            else:
                raise ValueError(f"Unknown video type: {job.video_type}")

            # Wait for video completion
            completed_result = await self.avatar_client.wait_for_completion(
                result.video_id,
                max_wait_time=3600  # 1 hour timeout
            )

            if completed_result.status == AvatarStatus.COMPLETED:
                # Store video in Google Drive if configured
                await self._store_video_in_drive(completed_result, job)

                # Notify user of completion
                await self.notification_service.notify_user(
                    user_id=job.user_id,
                    message=f"Your {job.video_type.value} video is ready!",
                    data={
                        "video_url": completed_result.video_url,
                        "duration_seconds": completed_result.duration_seconds,
                        "thumbnail_url": completed_result.thumbnail_url
                    }
                )

                job.status = "completed"
                logger.info(f"Completed video generation job: {job.job_id}")

            else:
                job.status = "failed"
                logger.error(f"Video generation failed: {completed_result.error_message}")

        except Exception as e:
            job.status = "failed"
            logger.error(f"Video generation job {job.job_id} failed: {str(e)}")

            await self.notification_service.notify_user(
                user_id=job.user_id,
                message=f"Video generation failed: {str(e)}",
                data={"job_id": job.job_id}
            )

        finally:
            if job.job_id in self.active_jobs:
                del self.active_jobs[job.job_id]

    async def _generate_remediation_video(self, job: VideoGenerationJob) -> AvatarResult:
        """Generate remediation video."""
        return await self.content_generator.generate_remediation_video(
            assessment_results=job.parameters["assessment_results"],
            user_profile=job.parameters["user_profile"],
            certification_name=job.certification_name,
            focus_area=job.parameters["focus_area"]
        )

    async def _generate_overview_video(self, job: VideoGenerationJob) -> AvatarResult:
        """Generate overview video."""
        return await self.content_generator.generate_overview_video(
            certification_name=job.certification_name,
            user_profile=job.parameters["user_profile"],
            target_domains=job.parameters.get("target_domains")
        )

    async def _generate_motivational_video(self, job: VideoGenerationJob) -> AvatarResult:
        """Generate motivational video."""
        return await self.content_generator.generate_motivational_video(
            assessment_results=job.parameters["assessment_results"],
            user_profile=job.parameters["user_profile"],
            certification_name=job.certification_name
        )

    async def _generate_practice_video(self, job: VideoGenerationJob) -> AvatarResult:
        """Generate practice session video."""
        return await self.content_generator.generate_practice_session_video(
            certification_name=job.certification_name,
            topic=job.parameters["topic"],
            difficulty_level=job.parameters.get("difficulty_level", "intermediate"),
            user_profile=job.parameters["user_profile"]
        )

    async def _generate_exam_prep_video(self, job: VideoGenerationJob) -> AvatarResult:
        """Generate exam preparation video."""
        # This would be implemented similar to practice video but focused on exam strategies
        return await self.content_generator.generate_practice_session_video(
            certification_name=job.certification_name,
            topic="exam_strategies",
            difficulty_level="advanced",
            user_profile=job.parameters["user_profile"]
        )

    async def _generate_celebration_video(self, job: VideoGenerationJob) -> AvatarResult:
        """Generate celebration video for achievements."""
        # This would generate a congratulatory video for milestones
        return await self.content_generator.generate_motivational_video(
            assessment_results=job.parameters["assessment_results"],
            user_profile=job.parameters["user_profile"],
            certification_name=job.certification_name
        )

    async def _store_video_in_drive(
        self,
        video_result: AvatarResult,
        job: VideoGenerationJob
    ):
        """Store completed video in Google Drive."""
        try:
            # Download video content
            video_content = await self.avatar_client.download_video(video_result.video_id)

            # Upload to Google Drive
            storage_service = self.google_services.storage

            video_filename = f"{job.certification_name}_{job.video_type.value}_{job.user_id}.mp4"
            drive_path = f"users/{job.user_id}/videos/{video_filename}"

            upload_result = await storage_service.upload_file(
                file_content=io.BytesIO(video_content),
                destination_path=drive_path,
                content_type="video/mp4",
                metadata={
                    "user_id": job.user_id,
                    "certification": job.certification_name,
                    "video_type": job.video_type.value,
                    "original_video_id": video_result.video_id,
                    "duration_seconds": str(video_result.duration_seconds),
                    "generated_at": datetime.utcnow().isoformat()
                }
            )

            logger.info(f"Stored video in Drive: {upload_result['public_url']}")

        except Exception as e:
            logger.error(f"Failed to store video in Drive: {str(e)}")
            # Don't fail the entire job if Drive storage fails

class VideoLibraryManager:
    """
    Manages a library of generated videos for users.
    Provides organization, search, and recommendation capabilities.
    """

    def __init__(self, database_service, google_services):
        self.database_service = database_service
        self.google_services = google_services

    async def organize_user_videos(
        self,
        user_id: str,
        certification_name: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Organize user's videos by type and topic."""
        videos = await self.database_service.get_user_videos(
            user_id=user_id,
            certification_name=certification_name
        )

        organized = {
            "overview": [],
            "remediation": [],
            "practice": [],
            "motivational": [],
            "exam_prep": []
        }

        for video in videos:
            video_type = video.get("video_type", "other")
            if video_type in organized:
                organized[video_type].append(video)

        return organized

    async def recommend_next_videos(
        self,
        user_id: str,
        certification_name: str,
        current_progress: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Recommend next videos based on user progress."""
        recommendations = []

        # Analyze progress to suggest next content
        weak_areas = current_progress.get("weak_areas", [])
        completed_videos = current_progress.get("completed_videos", [])

        # Recommend remediation videos for weak areas
        for area in weak_areas:
            if not any(v.get("focus_area") == area for v in completed_videos):
                recommendations.append({
                    "type": "remediation",
                    "focus_area": area,
                    "priority": "high",
                    "reason": f"Strengthen understanding in {area}"
                })

        # Recommend practice sessions
        if len(completed_videos) >= 2:  # User has watched some content
            recommendations.append({
                "type": "practice_session",
                "topic": "comprehensive_review",
                "priority": "medium",
                "reason": "Practice applying your knowledge"
            })

        return recommendations[:5]  # Limit to top 5 recommendations

    async def create_playlist(
        self,
        user_id: str,
        certification_name: str,
        playlist_type: str = "complete_preparation"
    ) -> List[Dict[str, Any]]:
        """Create curated playlist for user's learning journey."""
        if playlist_type == "complete_preparation":
            return [
                {"type": "overview", "order": 1, "description": "Introduction to certification"},
                {"type": "remediation", "order": 2, "description": "Address knowledge gaps"},
                {"type": "practice_session", "order": 3, "description": "Apply your knowledge"},
                {"type": "exam_prep", "order": 4, "description": "Prepare for the exam"},
                {"type": "motivational", "order": 5, "description": "Stay motivated"}
            ]
        elif playlist_type == "quick_review":
            return [
                {"type": "overview", "order": 1, "description": "Quick overview"},
                {"type": "practice_session", "order": 2, "description": "Practice key concepts"}
            ]

        return []
```

This completes Phase 5 - PresGen-Avatar Integration, providing comprehensive avatar video generation capabilities for personalized learning experiences.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create detailed Phase 1 document - Google APIs Foundation", "status": "completed", "activeForm": "Creating detailed Phase 1 document - Google APIs Foundation"}, {"content": "Create detailed Phase 2 document - Google Forms Automation", "status": "completed", "activeForm": "Creating detailed Phase 2 document - Google Forms Automation"}, {"content": "Create detailed Phase 3 document - Response Collection Pipeline", "status": "completed", "activeForm": "Creating detailed Phase 3 document - Response Collection Pipeline"}, {"content": "Create detailed Phase 4 document - PresGen-Core Integration", "status": "completed", "activeForm": "Creating detailed Phase 4 document - PresGen-Core Integration"}, {"content": "Create detailed Phase 5 document - PresGen-Avatar Integration", "status": "completed", "activeForm": "Creating detailed Phase 5 document - PresGen-Avatar Integration"}, {"content": "Fix UUID serialization issue in enhanced logging", "status": "completed", "activeForm": "Fixing UUID serialization issue in enhanced logging"}]