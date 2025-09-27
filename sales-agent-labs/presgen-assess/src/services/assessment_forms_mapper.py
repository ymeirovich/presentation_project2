"""Utilities for translating assessment data into Google Forms payloads."""

from __future__ import annotations

from typing import Any, Dict, List


class AssessmentFormsMapper:
    """Convert assessment questions into Google Forms structures."""

    TITLE_TEMPLATE = "{cert_name} Assessment ({question_count} Questions)"
    DESCRIPTION_TEMPLATE = (
        "This assessment contains {question_count} questions and should take approximately"
        " {estimated_minutes} minutes to complete."
    )

    def map_assessment_to_form(self, assessment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create base form payload from assessment metadata."""
        questions = assessment_data.get("questions", [])
        form_items = [self._map_question_to_form_item(question) for question in questions]

        title = self._generate_form_title(assessment_data)
        description = self._generate_form_description(assessment_data)

        return {
            "info": {
                "title": title,
                "description": description,
            },
            "items": form_items,
        }

    def build_batch_update_requests(
        self,
        questions: List[Dict[str, Any]],
        start_index: int = 0,
    ) -> List[Dict[str, Any]]:
        """Generate batchUpdate requests for inserting questions into a form."""
        requests: List[Dict[str, Any]] = []
        current_index = start_index
        for question in questions:
            item = self._map_question_to_form_item(question)
            requests.append(
                {
                    "createItem": {
                        "item": item,
                        "location": {"index": current_index},
                    }
                }
            )
            current_index += 1
        return requests

    def _map_question_to_form_item(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Map a single assessment question to a Google Forms item."""
        question_type = question.get("question_type", "multiple_choice")

        if question_type == "multiple_choice":
            return self._create_multiple_choice_item(question)
        if question_type == "true_false":
            return self._create_true_false_item(question)
        if question_type in {"scenario", "paragraph", "short_answer"}:
            return self._create_paragraph_item(question)

        raise ValueError("Unsupported question type")

    def _create_multiple_choice_item(self, question: Dict[str, Any]) -> Dict[str, Any]:
        options = question.get("options", [])
        choice_options = [{"value": option} for option in options]

        return {
            "title": question.get("question_text", ""),
            "description": question.get("explanation"),
            "questionItem": {
                "question": {
                    "required": True,
                    "choiceQuestion": {
                        "type": "RADIO",
                        "options": choice_options,
                        "shuffle": False,
                    },
                }
            },
        }

    def _create_true_false_item(self, question: Dict[str, Any]) -> Dict[str, Any]:
        options = [{"value": "True"}, {"value": "False"}]
        return {
            "title": question.get("question_text", ""),
            "description": question.get("explanation"),
            "questionItem": {
                "question": {
                    "required": True,
                    "choiceQuestion": {
                        "type": "RADIO",
                        "options": options,
                        "shuffle": False,
                    },
                }
            },
        }

    def _create_paragraph_item(self, question: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "title": question.get("question_text", ""),
            "description": question.get("explanation"),
            "questionItem": {
                "question": {
                    "required": True,
                    "textQuestion": {
                        "paragraph": True,
                    },
                }
            },
        }

    def _generate_form_title(self, assessment_data: Dict[str, Any]) -> str:
        metadata = assessment_data.get("metadata", {})
        cert_name = metadata.get("certification_name", "Assessment")
        cert_version = metadata.get("certification_version")
        question_count = metadata.get("total_questions") or len(assessment_data.get("questions", []))

        title = cert_name
        if cert_version:
            title = f"{title} ({cert_version})"

        return self.TITLE_TEMPLATE.format(cert_name=title, question_count=question_count or 0)

    def _generate_form_description(self, assessment_data: Dict[str, Any]) -> str:
        metadata = assessment_data.get("metadata", {})
        question_count = metadata.get("total_questions") or len(assessment_data.get("questions", []))
        estimated_minutes = metadata.get("estimated_duration_minutes", max(5, question_count * 2))

        return self.DESCRIPTION_TEMPLATE.format(
            question_count=question_count or 0,
            estimated_minutes=estimated_minutes,
        )
