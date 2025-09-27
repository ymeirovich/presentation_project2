# Phase 2: Google Forms Automation
*Dynamic Form Generation and Response Collection System*

## Overview
Automated Google Forms creation and management system that dynamically generates assessment forms, collects responses, and integrates with the certification workflow. Builds on Phase 1's Google API foundation to provide comprehensive form lifecycle management.

## 2.1 Dynamic Form Generation

### 2.1.1 Form Template Engine
```python
# /presgen-assess/src/integrations/google/forms/form_generator.py
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)

class QuestionType(Enum):
    """Supported Google Forms question types."""
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    CHECKBOX = "CHECKBOX"
    SHORT_ANSWER = "SHORT_ANSWER"
    PARAGRAPH = "PARAGRAPH"
    DROPDOWN = "DROP_DOWN"
    LINEAR_SCALE = "LINEAR_SCALE"
    MULTIPLE_CHOICE_GRID = "MULTIPLE_CHOICE_GRID"
    CHECKBOX_GRID = "CHECKBOX_GRID"
    DATE = "DATE"
    TIME = "TIME"
    FILE_UPLOAD = "FILE_UPLOAD"

@dataclass
class FormQuestion:
    """Data class representing a form question."""
    title: str
    question_type: QuestionType
    description: Optional[str] = None
    required: bool = False
    options: Optional[List[str]] = None
    scale_low_label: Optional[str] = None
    scale_high_label: Optional[str] = None
    scale_min: Optional[int] = None
    scale_max: Optional[int] = None
    validation: Optional[Dict[str, Any]] = None
    points: Optional[int] = None
    correct_answers: Optional[List[str]] = None

@dataclass
class FormTemplate:
    """Data class representing a complete form template."""
    title: str
    description: str
    questions: List[FormQuestion] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    theme_color: Optional[str] = None
    header_image_url: Optional[str] = None

class FormGenerator:
    """
    Service for generating Google Forms from templates and question specifications.
    Handles dynamic form creation based on certification requirements.
    """

    def __init__(self, google_services):
        self.google_services = google_services
        self.forms_client = google_services.get_forms_client()

    async def create_form_from_template(
        self,
        template: FormTemplate,
        folder_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Google Form from a template specification.
        Returns form details including ID and public URL.
        """
        try:
            # Create the basic form
            form_body = {
                "info": {
                    "title": template.title,
                    "description": template.description
                }
            }

            # Add theme settings if provided
            if template.theme_color or template.header_image_url:
                form_body["settings"] = {}
                if template.theme_color:
                    form_body["settings"]["theme"] = {
                        "primaryColor": template.theme_color
                    }

            # Create the form
            form = self.forms_client.forms().create(body=form_body).execute()
            form_id = form["formId"]

            logger.info(f"Created Google Form: {form_id}")

            # Add questions to the form
            if template.questions:
                await self._add_questions_to_form(form_id, template.questions)

            # Apply form settings
            if template.settings:
                await self._apply_form_settings(form_id, template.settings)

            # Move to specified folder if provided
            if folder_id:
                await self._move_form_to_folder(form_id, folder_id)

            # Get complete form details
            complete_form = self.forms_client.forms().get(formId=form_id).execute()

            return {
                "form_id": form_id,
                "title": complete_form["info"]["title"],
                "public_url": complete_form["responderUri"],
                "edit_url": f"https://docs.google.com/forms/d/{form_id}/edit",
                "question_count": len(template.questions),
                "created_at": complete_form.get("createTime"),
                "settings": complete_form.get("settings", {})
            }

        except Exception as e:
            logger.error(f"Failed to create form from template: {str(e)}")
            raise

    async def _add_questions_to_form(
        self,
        form_id: str,
        questions: List[FormQuestion]
    ) -> None:
        """Add questions to an existing form."""
        requests = []

        for i, question in enumerate(questions):
            request = self._create_question_request(question, i)
            requests.append(request)

        if requests:
            batch_update_body = {"requests": requests}
            self.forms_client.forms().batchUpdate(
                formId=form_id,
                body=batch_update_body
            ).execute()

            logger.info(f"Added {len(questions)} questions to form {form_id}")

    def _create_question_request(
        self,
        question: FormQuestion,
        index: int
    ) -> Dict[str, Any]:
        """Create a batch update request for adding a question."""
        question_item = {
            "title": question.title,
            "questionItem": {
                "question": {
                    "required": question.required,
                    **self._build_question_spec(question)
                }
            }
        }

        if question.description:
            question_item["description"] = question.description

        return {
            "createItem": {
                "item": question_item,
                "location": {"index": index}
            }
        }

    def _build_question_spec(self, question: FormQuestion) -> Dict[str, Any]:
        """Build question specification based on question type."""
        spec = {}

        if question.question_type == QuestionType.MULTIPLE_CHOICE:
            spec["choiceQuestion"] = {
                "type": "RADIO",
                "options": [{"value": option} for option in (question.options or [])]
            }

        elif question.question_type == QuestionType.CHECKBOX:
            spec["choiceQuestion"] = {
                "type": "CHECKBOX",
                "options": [{"value": option} for option in (question.options or [])]
            }

        elif question.question_type == QuestionType.SHORT_ANSWER:
            spec["textQuestion"] = {"paragraph": False}

        elif question.question_type == QuestionType.PARAGRAPH:
            spec["textQuestion"] = {"paragraph": True}

        elif question.question_type == QuestionType.DROPDOWN:
            spec["choiceQuestion"] = {
                "type": "DROP_DOWN",
                "options": [{"value": option} for option in (question.options or [])]
            }

        elif question.question_type == QuestionType.LINEAR_SCALE:
            scale_spec = {
                "low": question.scale_min or 1,
                "high": question.scale_max or 5
            }
            if question.scale_low_label:
                scale_spec["lowLabel"] = question.scale_low_label
            if question.scale_high_label:
                scale_spec["highLabel"] = question.scale_high_label

            spec["scaleQuestion"] = scale_spec

        elif question.question_type == QuestionType.DATE:
            spec["dateQuestion"] = {"includeTime": False}

        elif question.question_type == QuestionType.TIME:
            spec["timeQuestion"] = {"duration": False}

        elif question.question_type == QuestionType.FILE_UPLOAD:
            spec["fileUploadQuestion"] = {
                "folderId": "root",  # Can be configured per question
                "maxFiles": 1,
                "maxFileSize": 10485760  # 10MB
            }

        # Add validation if specified
        if question.validation:
            spec.setdefault("textQuestion", {})["validation"] = question.validation

        return spec

    async def _apply_form_settings(
        self,
        form_id: str,
        settings: Dict[str, Any]
    ) -> None:
        """Apply additional settings to the form."""
        requests = []

        # Quiz settings
        if settings.get("is_quiz", False):
            requests.append({
                "updateSettings": {
                    "settings": {
                        "quizSettings": {
                            "isQuiz": True
                        }
                    },
                    "updateMask": "quizSettings.isQuiz"
                }
            })

        # Response collection settings
        if "collect_email" in settings:
            requests.append({
                "updateSettings": {
                    "settings": {
                        "requiresLogin": settings["collect_email"]
                    },
                    "updateMask": "requiresLogin"
                }
            })

        # Submit settings
        if "confirmation_message" in settings:
            requests.append({
                "updateSettings": {
                    "settings": {
                        "submitText": settings["confirmation_message"]
                    },
                    "updateMask": "submitText"
                }
            })

        if requests:
            batch_update_body = {"requests": requests}
            self.forms_client.forms().batchUpdate(
                formId=form_id,
                body=batch_update_body
            ).execute()

    async def _move_form_to_folder(self, form_id: str, folder_id: str) -> None:
        """Move form to specified Google Drive folder."""
        drive_client = self.google_services.get_drive_client()

        # Get current parents
        file_metadata = drive_client.files().get(
            fileId=form_id,
            fields='parents'
        ).execute()

        previous_parents = ",".join(file_metadata.get('parents', []))

        # Move to new folder
        drive_client.files().update(
            fileId=form_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()

        logger.info(f"Moved form {form_id} to folder {folder_id}")

class AssessmentFormGenerator:
    """
    Specialized form generator for certification assessments.
    Creates forms based on knowledge base content and certification requirements.
    """

    def __init__(self, form_generator: FormGenerator):
        self.form_generator = form_generator

    async def create_pre_assessment_form(
        self,
        certification_name: str,
        domains: List[str],
        folder_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a pre-assessment form to gauge baseline knowledge.
        """
        questions = [
            FormQuestion(
                title="Full Name",
                question_type=QuestionType.SHORT_ANSWER,
                required=True
            ),
            FormQuestion(
                title="Email Address",
                question_type=QuestionType.SHORT_ANSWER,
                required=True,
                validation={
                    "emailAddress": True
                }
            ),
            FormQuestion(
                title="Current Role/Position",
                question_type=QuestionType.SHORT_ANSWER,
                required=True
            ),
            FormQuestion(
                title="Years of Experience in Related Field",
                question_type=QuestionType.DROPDOWN,
                required=True,
                options=["Less than 1 year", "1-2 years", "3-5 years", "6-10 years", "More than 10 years"]
            ),
            FormQuestion(
                title=f"Rate your current knowledge level in {certification_name}",
                question_type=QuestionType.LINEAR_SCALE,
                required=True,
                scale_min=1,
                scale_max=5,
                scale_low_label="Beginner",
                scale_high_label="Expert"
            )
        ]

        # Add domain-specific questions
        for domain in domains:
            questions.append(
                FormQuestion(
                    title=f"Rate your experience with {domain}",
                    question_type=QuestionType.LINEAR_SCALE,
                    required=True,
                    scale_min=1,
                    scale_max=5,
                    scale_low_label="No experience",
                    scale_high_label="Highly experienced"
                )
            )

        # Learning preferences and goals
        questions.extend([
            FormQuestion(
                title="Preferred Learning Style",
                question_type=QuestionType.CHECKBOX,
                required=False,
                options=[
                    "Visual (diagrams, charts, presentations)",
                    "Auditory (lectures, discussions)",
                    "Hands-on (labs, practice exercises)",
                    "Reading (documentation, articles)",
                    "Video tutorials"
                ]
            ),
            FormQuestion(
                title="Primary Goal for Taking This Assessment",
                question_type=QuestionType.MULTIPLE_CHOICE,
                required=True,
                options=[
                    "Prepare for certification exam",
                    "Assess current knowledge gaps",
                    "Professional development",
                    "Job requirement",
                    "Personal interest"
                ]
            ),
            FormQuestion(
                title="Additional Comments or Specific Areas of Interest",
                question_type=QuestionType.PARAGRAPH,
                required=False
            )
        ])

        template = FormTemplate(
            title=f"{certification_name} - Pre-Assessment Survey",
            description=f"This survey helps us understand your current knowledge level and learning preferences for {certification_name}. Your responses will be used to customize your learning experience.",
            questions=questions,
            settings={
                "collect_email": True,
                "confirmation_message": "Thank you for completing the pre-assessment! We'll use your responses to personalize your learning journey."
            },
            theme_color="#1976D2"
        )

        return await self.form_generator.create_form_from_template(template, folder_id)

    async def create_knowledge_assessment_form(
        self,
        certification_name: str,
        questions_data: List[Dict[str, Any]],
        is_quiz: bool = True,
        folder_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a knowledge assessment form with generated questions.
        """
        form_questions = []

        # Add user identification
        form_questions.extend([
            FormQuestion(
                title="Full Name",
                question_type=QuestionType.SHORT_ANSWER,
                required=True
            ),
            FormQuestion(
                title="Email Address",
                question_type=QuestionType.SHORT_ANSWER,
                required=True,
                validation={"emailAddress": True}
            )
        ])

        # Convert knowledge questions to form questions
        for i, q_data in enumerate(questions_data, 1):
            question_title = f"Question {i}: {q_data['question']}"

            if q_data.get('type') == 'multiple_choice':
                form_question = FormQuestion(
                    title=question_title,
                    question_type=QuestionType.MULTIPLE_CHOICE,
                    required=True,
                    options=q_data['options'],
                    points=q_data.get('points', 1),
                    correct_answers=[q_data.get('correct_answer')] if is_quiz else None
                )
            elif q_data.get('type') == 'multiple_select':
                form_question = FormQuestion(
                    title=question_title,
                    question_type=QuestionType.CHECKBOX,
                    required=True,
                    options=q_data['options'],
                    points=q_data.get('points', 1),
                    correct_answers=q_data.get('correct_answers', []) if is_quiz else None
                )
            else:
                # Default to short answer
                form_question = FormQuestion(
                    title=question_title,
                    question_type=QuestionType.PARAGRAPH,
                    required=True,
                    points=q_data.get('points', 1)
                )

            form_questions.append(form_question)

        # Add feedback question
        form_questions.append(
            FormQuestion(
                title="Any additional comments about this assessment?",
                question_type=QuestionType.PARAGRAPH,
                required=False
            )
        )

        template = FormTemplate(
            title=f"{certification_name} - Knowledge Assessment",
            description=f"This assessment evaluates your knowledge in {certification_name}. Please answer all questions to the best of your ability.",
            questions=form_questions,
            settings={
                "is_quiz": is_quiz,
                "collect_email": True,
                "confirmation_message": "Assessment submitted successfully! You will receive your results shortly."
            },
            theme_color="#4CAF50"
        )

        return await self.form_generator.create_form_from_template(template, folder_id)
```

### 2.1.2 Question Bank Integration
```python
# /presgen-assess/src/integrations/google/forms/question_bank.py
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import random
import logging

logger = logging.getLogger(__name__)

@dataclass
class QuestionMetadata:
    """Metadata for assessment questions."""
    domain: str
    difficulty: str  # beginner, intermediate, advanced
    topic: str
    bloom_level: str  # remember, understand, apply, analyze, evaluate, create
    estimated_time_minutes: int
    tags: List[str]

class QuestionBankManager:
    """
    Manages question banks for different certifications and dynamically
    generates assessment questions based on user profiles and knowledge gaps.
    """

    def __init__(self, knowledge_base_service):
        self.knowledge_base_service = knowledge_base_service
        self.question_templates = self._load_question_templates()

    def _load_question_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load question templates for different types and formats."""
        return {
            "multiple_choice": {
                "template": "Based on the following content: {context}\n\nQuestion: {question}\n\nA) {option_a}\nB) {option_b}\nC) {option_c}\nD) {option_d}",
                "answer_format": "single_select"
            },
            "scenario_based": {
                "template": "Scenario: {scenario}\n\nQuestion: {question}\n\nSelect all that apply:\n{options}",
                "answer_format": "multiple_select"
            },
            "practical_application": {
                "template": "Given the following situation: {situation}\n\nWhat would you do? Explain your approach and reasoning.",
                "answer_format": "open_ended"
            },
            "troubleshooting": {
                "template": "Problem: {problem_description}\n\nSymptoms: {symptoms}\n\nWhat are the most likely causes and how would you resolve this issue?",
                "answer_format": "open_ended"
            }
        }

    async def generate_adaptive_questions(
        self,
        certification_name: str,
        user_profile: Dict[str, Any],
        question_count: int = 20,
        difficulty_distribution: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate adaptive questions based on user profile and knowledge gaps.
        Adjusts difficulty and topics based on pre-assessment results.
        """
        if difficulty_distribution is None:
            difficulty_distribution = {"beginner": 0.3, "intermediate": 0.5, "advanced": 0.2}

        # Analyze user profile for knowledge gaps
        focus_areas = self._identify_focus_areas(user_profile)

        # Generate question distribution
        questions_by_difficulty = {
            level: int(question_count * percentage)
            for level, percentage in difficulty_distribution.items()
        }

        # Adjust for rounding
        total_assigned = sum(questions_by_difficulty.values())
        if total_assigned < question_count:
            questions_by_difficulty["intermediate"] += question_count - total_assigned

        generated_questions = []

        for difficulty, count in questions_by_difficulty.items():
            if count > 0:
                questions = await self._generate_questions_for_difficulty(
                    certification_name=certification_name,
                    difficulty=difficulty,
                    count=count,
                    focus_areas=focus_areas,
                    user_profile=user_profile
                )
                generated_questions.extend(questions)

        # Shuffle questions to avoid patterns
        random.shuffle(generated_questions)

        return generated_questions

    def _identify_focus_areas(self, user_profile: Dict[str, Any]) -> List[str]:
        """
        Identify areas where user needs more focus based on profile data.
        Uses pre-assessment responses and experience levels.
        """
        focus_areas = []

        # Analyze domain ratings from pre-assessment
        domain_ratings = user_profile.get("domain_ratings", {})
        for domain, rating in domain_ratings.items():
            if rating <= 2:  # Low self-assessment rating
                focus_areas.append(domain)

        # Consider experience level
        experience_level = user_profile.get("experience_years", "Less than 1 year")
        if experience_level in ["Less than 1 year", "1-2 years"]:
            focus_areas.extend(["fundamentals", "basic_concepts"])

        # Add learning preferences
        learning_style = user_profile.get("learning_style", [])
        if "Hands-on (labs, practice exercises)" in learning_style:
            focus_areas.append("practical_application")

        return list(set(focus_areas))  # Remove duplicates

    async def _generate_questions_for_difficulty(
        self,
        certification_name: str,
        difficulty: str,
        count: int,
        focus_areas: List[str],
        user_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate questions for a specific difficulty level."""
        questions = []

        # Get relevant knowledge base content
        knowledge_content = await self.knowledge_base_service.search_content(
            collection_name=certification_name,
            query_terms=focus_areas,
            difficulty_filter=difficulty,
            limit=count * 3  # Get more content than needed for variety
        )

        for i in range(min(count, len(knowledge_content))):
            content = knowledge_content[i]

            # Select question type based on difficulty and content
            question_type = self._select_question_type(difficulty, content, user_profile)

            # Generate question
            question = await self._generate_question_from_content(
                content=content,
                question_type=question_type,
                difficulty=difficulty
            )

            if question:
                questions.append(question)

        return questions

    def _select_question_type(
        self,
        difficulty: str,
        content: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> str:
        """Select appropriate question type based on difficulty and content."""
        content_type = content.get("content_type", "general")

        if difficulty == "beginner":
            # Focus on recall and understanding
            return "multiple_choice"
        elif difficulty == "intermediate":
            # Mix of application and analysis
            if content_type in ["procedure", "configuration"]:
                return "scenario_based"
            else:
                return "multiple_choice"
        else:  # advanced
            # Evaluation and creation
            if "hands-on" in user_profile.get("learning_style", []):
                return "practical_application"
            elif content_type == "troubleshooting":
                return "troubleshooting"
            else:
                return "scenario_based"

    async def _generate_question_from_content(
        self,
        content: Dict[str, Any],
        question_type: str,
        difficulty: str
    ) -> Optional[Dict[str, Any]]:
        """Generate a specific question from knowledge base content."""
        try:
            template = self.question_templates[question_type]

            if question_type == "multiple_choice":
                return await self._generate_multiple_choice_question(content, difficulty)
            elif question_type == "scenario_based":
                return await self._generate_scenario_question(content, difficulty)
            elif question_type == "practical_application":
                return await self._generate_practical_question(content, difficulty)
            elif question_type == "troubleshooting":
                return await self._generate_troubleshooting_question(content, difficulty)

        except Exception as e:
            logger.error(f"Failed to generate question: {str(e)}")
            return None

    async def _generate_multiple_choice_question(
        self,
        content: Dict[str, Any],
        difficulty: str
    ) -> Dict[str, Any]:
        """Generate multiple choice question from content."""
        # This would integrate with an LLM service to generate questions
        # For now, returning a template structure

        return {
            "type": "multiple_choice",
            "question": f"Based on {content['title']}, which statement is correct?",
            "options": [
                "Option A (correct answer would be generated)",
                "Option B (distractor)",
                "Option C (distractor)",
                "Option D (distractor)"
            ],
            "correct_answer": "Option A (correct answer would be generated)",
            "explanation": "Explanation would be generated based on content",
            "points": 1,
            "difficulty": difficulty,
            "metadata": QuestionMetadata(
                domain=content.get("domain", "general"),
                difficulty=difficulty,
                topic=content.get("topic", "general"),
                bloom_level="understand" if difficulty == "beginner" else "apply",
                estimated_time_minutes=2,
                tags=content.get("tags", [])
            ).__dict__
        }

class FormResponseCollector:
    """
    Collects and processes responses from Google Forms.
    Integrates with assessment analysis and gap identification.
    """

    def __init__(self, google_services):
        self.google_services = google_services
        self.forms_client = google_services.get_forms_client()

    async def collect_form_responses(
        self,
        form_id: str,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Collect all responses from a Google Form.
        Returns structured response data.
        """
        try:
            # Get form structure first
            form = self.forms_client.forms().get(formId=form_id).execute()
            questions_map = self._build_questions_map(form)

            # Get responses
            responses = self.forms_client.forms().responses().list(formId=form_id).execute()

            structured_responses = []
            for response in responses.get("responses", []):
                structured_response = self._structure_response(
                    response, questions_map, include_metadata
                )
                structured_responses.append(structured_response)

            logger.info(f"Collected {len(structured_responses)} responses from form {form_id}")
            return structured_responses

        except Exception as e:
            logger.error(f"Failed to collect form responses: {str(e)}")
            raise

    def _build_questions_map(self, form: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Build mapping of question IDs to question details."""
        questions_map = {}

        for item in form.get("items", []):
            if "questionItem" in item:
                question_id = item["questionItem"]["question"]["questionId"]
                questions_map[question_id] = {
                    "title": item["title"],
                    "type": self._determine_question_type(item["questionItem"]["question"]),
                    "options": self._extract_options(item["questionItem"]["question"])
                }

        return questions_map

    def _determine_question_type(self, question: Dict[str, Any]) -> str:
        """Determine the type of question from Google Forms structure."""
        if "choiceQuestion" in question:
            choice_type = question["choiceQuestion"]["type"]
            if choice_type == "RADIO":
                return "multiple_choice"
            elif choice_type == "CHECKBOX":
                return "checkbox"
            elif choice_type == "DROP_DOWN":
                return "dropdown"
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

    def _extract_options(self, question: Dict[str, Any]) -> List[str]:
        """Extract answer options from question structure."""
        if "choiceQuestion" in question:
            return [option["value"] for option in question["choiceQuestion"].get("options", [])]
        elif "scaleQuestion" in question:
            scale = question["scaleQuestion"]
            return [str(i) for i in range(scale["low"], scale["high"] + 1)]

        return []

    def _structure_response(
        self,
        response: Dict[str, Any],
        questions_map: Dict[str, Dict[str, Any]],
        include_metadata: bool
    ) -> Dict[str, Any]:
        """Structure a single form response into a readable format."""
        structured = {
            "response_id": response["responseId"],
            "create_time": response["createTime"],
            "last_submitted_time": response["lastSubmittedTime"],
            "answers": {}
        }

        if include_metadata:
            structured["metadata"] = {
                "total_time_spent": response.get("totalTime"),
                "respondent_email": response.get("respondentEmail")
            }

        # Process answers
        for question_id, answer in response.get("answers", {}).items():
            if question_id in questions_map:
                question_info = questions_map[question_id]
                structured["answers"][question_info["title"]] = {
                    "question_type": question_info["type"],
                    "answer": self._extract_answer_value(answer, question_info["type"]),
                    "question_id": question_id
                }

        return structured

    def _extract_answer_value(self, answer: Dict[str, Any], question_type: str) -> Any:
        """Extract the actual answer value based on question type."""
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
```

## 2.2 Response Analysis and Processing

### 2.2.1 Response Analysis Engine
```python
# /presgen-assess/src/integrations/google/forms/response_analyzer.py
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import statistics
import logging

logger = logging.getLogger(__name__)

@dataclass
class AnalysisResult:
    """Results from response analysis."""
    total_responses: int
    completion_rate: float
    average_score: Optional[float]
    score_distribution: Dict[str, int]
    question_analytics: Dict[str, Dict[str, Any]]
    time_analytics: Dict[str, Any]
    demographic_insights: Dict[str, Any]

class ResponseAnalyzer:
    """
    Analyzes form responses to generate insights about user performance,
    knowledge gaps, and assessment effectiveness.
    """

    def __init__(self):
        self.scoring_methods = {
            "multiple_choice": self._score_multiple_choice,
            "checkbox": self._score_checkbox,
            "linear_scale": self._score_linear_scale,
            "paragraph": self._score_open_ended,
            "short_answer": self._score_short_answer
        }

    async def analyze_assessment_responses(
        self,
        responses: List[Dict[str, Any]],
        form_metadata: Dict[str, Any],
        scoring_rubric: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """
        Comprehensive analysis of assessment responses.
        Returns detailed analytics for performance evaluation.
        """
        if not responses:
            return AnalysisResult(
                total_responses=0,
                completion_rate=0.0,
                average_score=None,
                score_distribution={},
                question_analytics={},
                time_analytics={},
                demographic_insights={}
            )

        # Calculate completion rate
        completed_responses = [r for r in responses if self._is_complete_response(r)]
        completion_rate = len(completed_responses) / len(responses)

        # Score responses if it's a quiz/assessment
        scores = []
        if form_metadata.get("is_quiz", False) and scoring_rubric:
            for response in completed_responses:
                score = await self._score_response(response, scoring_rubric)
                scores.append(score)

        # Calculate score statistics
        average_score = statistics.mean(scores) if scores else None
        score_distribution = self._calculate_score_distribution(scores)

        # Analyze individual questions
        question_analytics = self._analyze_questions(completed_responses, form_metadata)

        # Time analytics
        time_analytics = self._analyze_response_times(completed_responses)

        # Demographic insights
        demographic_insights = self._analyze_demographics(completed_responses)

        return AnalysisResult(
            total_responses=len(responses),
            completion_rate=completion_rate,
            average_score=average_score,
            score_distribution=score_distribution,
            question_analytics=question_analytics,
            time_analytics=time_analytics,
            demographic_insights=demographic_insights
        )

    def _is_complete_response(self, response: Dict[str, Any]) -> bool:
        """Check if a response is complete (answered required questions)."""
        # This would check against form requirements
        # For now, assume response is complete if it has answers
        return len(response.get("answers", {})) > 0

    async def _score_response(
        self,
        response: Dict[str, Any],
        scoring_rubric: Dict[str, Any]
    ) -> float:
        """Score an individual response based on the rubric."""
        total_score = 0
        max_possible_score = 0

        for question_title, answer_data in response["answers"].items():
            if question_title in scoring_rubric:
                rubric_item = scoring_rubric[question_title]
                question_type = answer_data["question_type"]

                if question_type in self.scoring_methods:
                    score = self.scoring_methods[question_type](
                        answer_data["answer"],
                        rubric_item
                    )
                    total_score += score

                max_possible_score += rubric_item.get("points", 1)

        return (total_score / max_possible_score * 100) if max_possible_score > 0 else 0

    def _score_multiple_choice(self, answer: str, rubric: Dict[str, Any]) -> float:
        """Score multiple choice questions."""
        correct_answer = rubric.get("correct_answer")
        points = rubric.get("points", 1)

        return points if answer == correct_answer else 0

    def _score_checkbox(self, answers: List[str], rubric: Dict[str, Any]) -> float:
        """Score checkbox (multiple select) questions."""
        correct_answers = set(rubric.get("correct_answers", []))
        user_answers = set(answers) if isinstance(answers, list) else {answers}
        points = rubric.get("points", 1)

        # Partial credit based on overlap
        if correct_answers:
            overlap = len(correct_answers.intersection(user_answers))
            total_correct = len(correct_answers)
            return (overlap / total_correct) * points

        return 0

    def _score_linear_scale(self, answer: int, rubric: Dict[str, Any]) -> float:
        """Score linear scale questions."""
        # For scale questions, might award points based on proximity to target
        target_answer = rubric.get("target_answer")
        points = rubric.get("points", 1)
        tolerance = rubric.get("tolerance", 1)

        if target_answer is not None:
            if abs(answer - target_answer) <= tolerance:
                return points

        return 0

    def _score_open_ended(self, answer: str, rubric: Dict[str, Any]) -> float:
        """Score open-ended/paragraph questions."""
        # This would typically use NLP/AI for scoring
        # For now, return partial points for non-empty answers
        points = rubric.get("points", 1)

        if answer and len(answer.strip()) > 10:  # Basic length check
            return points * 0.8  # Partial credit for attempt

        return 0

    def _score_short_answer(self, answer: str, rubric: Dict[str, Any]) -> float:
        """Score short answer questions."""
        acceptable_answers = rubric.get("acceptable_answers", [])
        points = rubric.get("points", 1)

        # Check for exact matches or keyword presence
        answer_lower = answer.lower().strip()

        for acceptable in acceptable_answers:
            if acceptable.lower() in answer_lower:
                return points

        return 0

    def _calculate_score_distribution(self, scores: List[float]) -> Dict[str, int]:
        """Calculate distribution of scores in ranges."""
        if not scores:
            return {}

        distribution = {
            "90-100": 0,
            "80-89": 0,
            "70-79": 0,
            "60-69": 0,
            "Below 60": 0
        }

        for score in scores:
            if score >= 90:
                distribution["90-100"] += 1
            elif score >= 80:
                distribution["80-89"] += 1
            elif score >= 70:
                distribution["70-79"] += 1
            elif score >= 60:
                distribution["60-69"] += 1
            else:
                distribution["Below 60"] += 1

        return distribution

    def _analyze_questions(
        self,
        responses: List[Dict[str, Any]],
        form_metadata: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Analyze performance on individual questions."""
        question_analytics = {}

        # Get all unique questions
        all_questions = set()
        for response in responses:
            all_questions.update(response["answers"].keys())

        for question in all_questions:
            answers = []
            for response in responses:
                if question in response["answers"]:
                    answers.append(response["answers"][question]["answer"])

            analytics = self._analyze_single_question(question, answers)
            question_analytics[question] = analytics

        return question_analytics

    def _analyze_single_question(
        self,
        question: str,
        answers: List[Any]
    ) -> Dict[str, Any]:
        """Analyze a single question's responses."""
        if not answers:
            return {"response_count": 0}

        analytics = {
            "response_count": len(answers),
            "response_rate": len([a for a in answers if a is not None]) / len(answers)
        }

        # Analyze based on answer type
        first_answer = answers[0]

        if isinstance(first_answer, str):
            # Text answers
            analytics.update(self._analyze_text_answers(answers))
        elif isinstance(first_answer, (int, float)):
            # Numeric answers (scale questions)
            analytics.update(self._analyze_numeric_answers(answers))
        elif isinstance(first_answer, list):
            # Multiple selection answers
            analytics.update(self._analyze_multiple_selection_answers(answers))

        return analytics

    def _analyze_text_answers(self, answers: List[str]) -> Dict[str, Any]:
        """Analyze text-based answers."""
        valid_answers = [a for a in answers if a and a.strip()]

        return {
            "unique_responses": len(set(valid_answers)),
            "average_length": statistics.mean([len(a) for a in valid_answers]) if valid_answers else 0,
            "most_common": self._get_most_common_answer(valid_answers)
        }

    def _analyze_numeric_answers(self, answers: List[Union[int, float]]) -> Dict[str, Any]:
        """Analyze numeric answers (scales, ratings)."""
        valid_answers = [a for a in answers if a is not None]

        if not valid_answers:
            return {}

        return {
            "average": statistics.mean(valid_answers),
            "median": statistics.median(valid_answers),
            "standard_deviation": statistics.stdev(valid_answers) if len(valid_answers) > 1 else 0,
            "min": min(valid_answers),
            "max": max(valid_answers),
            "distribution": self._calculate_numeric_distribution(valid_answers)
        }

    def _analyze_multiple_selection_answers(self, answers: List[List[str]]) -> Dict[str, Any]:
        """Analyze multiple selection (checkbox) answers."""
        all_selections = []
        for answer in answers:
            if isinstance(answer, list):
                all_selections.extend(answer)
            elif answer:
                all_selections.append(answer)

        selection_counts = {}
        for selection in all_selections:
            selection_counts[selection] = selection_counts.get(selection, 0) + 1

        return {
            "total_selections": len(all_selections),
            "unique_options_selected": len(selection_counts),
            "selection_frequency": selection_counts,
            "most_popular": max(selection_counts.items(), key=lambda x: x[1]) if selection_counts else None
        }

    def _get_most_common_answer(self, answers: List[str]) -> Optional[str]:
        """Get the most common text answer."""
        if not answers:
            return None

        answer_counts = {}
        for answer in answers:
            normalized = answer.lower().strip()
            answer_counts[normalized] = answer_counts.get(normalized, 0) + 1

        return max(answer_counts.items(), key=lambda x: x[1])[0] if answer_counts else None

    def _calculate_numeric_distribution(self, values: List[Union[int, float]]) -> Dict[str, int]:
        """Calculate distribution of numeric values."""
        if not values:
            return {}

        min_val, max_val = min(values), max(values)
        range_size = (max_val - min_val) / 5 if max_val > min_val else 1

        distribution = {}
        for i in range(5):
            range_start = min_val + i * range_size
            range_end = min_val + (i + 1) * range_size
            range_key = f"{range_start:.1f}-{range_end:.1f}"

            count = len([v for v in values if range_start <= v < range_end])
            if i == 4:  # Include max value in last range
                count = len([v for v in values if range_start <= v <= range_end])

            distribution[range_key] = count

        return distribution

    def _analyze_response_times(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze response timing patterns."""
        times = []
        for response in responses:
            create_time = response.get("create_time")
            submit_time = response.get("last_submitted_time")

            if create_time and submit_time:
                # Calculate duration (this would need proper datetime parsing)
                # For now, using placeholder logic
                times.append(response.get("metadata", {}).get("total_time_spent", 0))

        valid_times = [t for t in times if t and t > 0]

        if not valid_times:
            return {"average_completion_time": None}

        return {
            "average_completion_time": statistics.mean(valid_times),
            "median_completion_time": statistics.median(valid_times),
            "fastest_completion": min(valid_times),
            "slowest_completion": max(valid_times)
        }

    def _analyze_demographics(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract demographic insights from responses."""
        demographics = {}

        # Look for common demographic questions
        demographic_fields = [
            "Years of Experience in Related Field",
            "Current Role/Position",
            "Preferred Learning Style"
        ]

        for field in demographic_fields:
            values = []
            for response in responses:
                if field in response["answers"]:
                    answer = response["answers"][field]["answer"]
                    if isinstance(answer, list):
                        values.extend(answer)
                    else:
                        values.append(answer)

            if values:
                value_counts = {}
                for value in values:
                    value_counts[value] = value_counts.get(value, 0) + 1

                demographics[field] = {
                    "distribution": value_counts,
                    "most_common": max(value_counts.items(), key=lambda x: x[1])[0]
                }

        return demographics
```

This completes Phase 2 - Google Forms Automation, providing comprehensive form generation, response collection, and analysis capabilities.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create detailed Phase 1 document - Google APIs Foundation", "status": "completed", "activeForm": "Creating detailed Phase 1 document - Google APIs Foundation"}, {"content": "Create detailed Phase 2 document - Google Forms Automation", "status": "completed", "activeForm": "Creating detailed Phase 2 document - Google Forms Automation"}, {"content": "Create detailed Phase 3 document - Response Collection Pipeline", "status": "in_progress", "activeForm": "Creating detailed Phase 3 document - Response Collection Pipeline"}, {"content": "Create detailed Phase 4 document - PresGen-Core Integration", "status": "pending", "activeForm": "Creating detailed Phase 4 document - PresGen-Core Integration"}, {"content": "Create detailed Phase 5 document - PresGen-Avatar Integration", "status": "pending", "activeForm": "Creating detailed Phase 5 document - PresGen-Avatar Integration"}, {"content": "Fix UUID serialization issue in enhanced logging", "status": "completed", "activeForm": "Fixing UUID serialization issue in enhanced logging"}]