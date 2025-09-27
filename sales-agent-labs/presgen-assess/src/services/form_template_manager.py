"""Form template management service for standardized assessment forms."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.common.enhanced_logging import get_enhanced_logger


class FormTemplateManager:
    """Manages form templates for different certification types and question formats."""

    def __init__(self, templates_dir: Optional[Path] = None):
        self.logger = get_enhanced_logger(__name__)
        self.templates_dir = templates_dir or Path(__file__).parent.parent / "templates" / "forms"
        self._template_cache: Dict[str, Dict] = {}

    def get_template(self, certification_type: str, template_version: str = "v1") -> Dict[str, Any]:
        """Get form template for a specific certification type."""
        template_key = f"{certification_type}_{template_version}"

        if template_key in self._template_cache:
            self.logger.debug("Using cached template", extra={
                "certification_type": certification_type,
                "template_version": template_version
            })
            return self._template_cache[template_key]

        template_path = self.templates_dir / f"{certification_type}_{template_version}.json"

        if not template_path.exists():
            # Fall back to default template
            template_path = self.templates_dir / "default_v1.json"
            if not template_path.exists():
                self.logger.warning("No template found, using built-in default", extra={
                    "certification_type": certification_type,
                    "template_version": template_version
                })
                return self._get_builtin_default_template()

        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = json.load(f)

            self._template_cache[template_key] = template

            self.logger.info("Loaded form template", extra={
                "certification_type": certification_type,
                "template_version": template_version,
                "template_path": str(template_path),
                "section_count": len(template.get("sections", []))
            })

            return template

        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error("Failed to load template", extra={
                "certification_type": certification_type,
                "template_path": str(template_path),
                "error": str(e)
            })
            return self._get_builtin_default_template()

    def _get_builtin_default_template(self) -> Dict[str, Any]:
        """Get built-in default template when no file templates are available."""
        return {
            "template_id": "default_v1",
            "name": "Default Assessment Template",
            "description": "Standard assessment form template",
            "version": "1.0",
            "sections": [
                {
                    "id": "instructions",
                    "title": "Assessment Instructions",
                    "type": "description",
                    "content": "Please read all questions carefully and select the best answer for each question.",
                    "required": False
                },
                {
                    "id": "questions",
                    "title": "Assessment Questions",
                    "type": "questions",
                    "settings": {
                        "shuffle_questions": False,
                        "show_progress": True,
                        "required_all": True
                    }
                },
                {
                    "id": "completion",
                    "title": "Assessment Complete",
                    "type": "description",
                    "content": "Thank you for completing this assessment. Your responses have been recorded.",
                    "required": False
                }
            ],
            "form_settings": {
                "collect_email": True,
                "require_login": False,
                "allow_response_editing": False,
                "show_progress_bar": True,
                "confirmation_message": "Your assessment has been submitted successfully."
            },
            "question_type_mappings": {
                "multiple_choice": "choiceQuestion",
                "true_false": "choiceQuestion",
                "scenario": "textQuestion",
                "short_answer": "textQuestion",
                "essay": "textQuestion"
            }
        }

    def create_template_from_assessment(
        self,
        assessment_data: Dict[str, Any],
        certification_type: str,
        template_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new template based on an assessment structure."""
        metadata = assessment_data.get("metadata", {})
        questions = assessment_data.get("questions", [])

        template_name = template_name or f"{certification_type}_custom"

        # Analyze question types and domains
        question_types = set()
        domains = set()
        difficulty_levels = []

        for question in questions:
            question_types.add(question.get("question_type", "multiple_choice"))
            domains.add(question.get("domain", "General"))
            difficulty_levels.append(question.get("difficulty", 0.5))

        avg_difficulty = sum(difficulty_levels) / len(difficulty_levels) if difficulty_levels else 0.5

        template = {
            "template_id": f"{certification_type}_custom_{len(self._template_cache)}",
            "name": template_name,
            "description": f"Custom template for {certification_type} based on assessment data",
            "version": "1.0",
            "created_from_assessment": assessment_data.get("assessment_id"),
            "statistics": {
                "question_count": len(questions),
                "question_types": list(question_types),
                "domains": list(domains),
                "average_difficulty": avg_difficulty,
                "estimated_duration_minutes": metadata.get("estimated_duration_minutes", 30)
            },
            "sections": self._generate_sections_from_questions(questions, domains),
            "form_settings": self._generate_form_settings(metadata),
            "question_type_mappings": self._get_question_type_mappings()
        }

        self.logger.info("Created custom template", extra={
            "template_id": template["template_id"],
            "certification_type": certification_type,
            "question_count": len(questions),
            "question_types": list(question_types),
            "domains": list(domains)
        })

        return template

    def _generate_sections_from_questions(
        self,
        questions: List[Dict],
        domains: set
    ) -> List[Dict[str, Any]]:
        """Generate form sections based on question structure."""
        sections = []

        # Add instructions section
        sections.append({
            "id": "instructions",
            "title": "Assessment Instructions",
            "type": "description",
            "content": self._generate_instructions_text(len(questions), domains),
            "required": False
        })

        # Group questions by domain if multiple domains exist
        if len(domains) > 1:
            for domain in sorted(domains):
                domain_questions = [q for q in questions if q.get("domain") == domain]
                if domain_questions:
                    sections.append({
                        "id": f"section_{domain.lower().replace(' ', '_')}",
                        "title": f"{domain} Questions",
                        "type": "questions",
                        "domain_filter": domain,
                        "question_count": len(domain_questions),
                        "settings": {
                            "shuffle_questions": False,
                            "show_progress": True,
                            "required_all": True
                        }
                    })
        else:
            # Single section for all questions
            sections.append({
                "id": "questions",
                "title": "Assessment Questions",
                "type": "questions",
                "settings": {
                    "shuffle_questions": False,
                    "show_progress": True,
                    "required_all": True
                }
            })

        # Add completion section
        sections.append({
            "id": "completion",
            "title": "Assessment Complete",
            "type": "description",
            "content": "Thank you for completing this assessment. Your responses have been recorded and will be analyzed to provide personalized feedback.",
            "required": False
        })

        return sections

    def _generate_instructions_text(self, question_count: int, domains: set) -> str:
        """Generate appropriate instructions text."""
        instructions = f"This assessment contains {question_count} questions"

        if len(domains) > 1:
            domain_list = ", ".join(sorted(domains))
            instructions += f" covering the following areas: {domain_list}."
        else:
            instructions += f" covering {list(domains)[0]}." if domains else "."

        instructions += "\n\nPlease read each question carefully and select the best answer. "
        instructions += "All questions are required to be answered to complete the assessment."

        return instructions

    def _generate_form_settings(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate appropriate form settings based on metadata."""
        return {
            "collect_email": True,
            "require_login": False,
            "allow_response_editing": False,
            "show_progress_bar": True,
            "shuffle_questions": metadata.get("shuffle_questions", False),
            "time_limit_minutes": metadata.get("time_limit_minutes"),
            "confirmation_message": metadata.get(
                "completion_message",
                "Your assessment has been submitted successfully."
            ),
            "description": metadata.get("description", ""),
            "privacy_notice": "Your responses will be used to generate personalized learning recommendations."
        }

    def _get_question_type_mappings(self) -> Dict[str, str]:
        """Get mappings from assessment question types to Google Forms types."""
        return {
            "multiple_choice": "choiceQuestion",
            "single_choice": "choiceQuestion",
            "true_false": "choiceQuestion",
            "scenario": "textQuestion",
            "short_answer": "textQuestion",
            "essay": "textQuestion",
            "paragraph": "textQuestion",
            "scale": "scaleQuestion",
            "grid": "rowQuestion"
        }

    def apply_template_to_form_structure(
        self,
        template: Dict[str, Any],
        assessment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply a template to create a complete form structure."""
        questions = assessment_data.get("questions", [])
        metadata = assessment_data.get("metadata", {})

        # Start with template form settings
        form_structure = {
            "info": {
                "title": self._generate_title_from_template(template, metadata),
                "description": self._generate_description_from_template(template, metadata)
            },
            "settings": template.get("form_settings", {}),
            "items": []
        }

        # Process template sections
        for section in template.get("sections", []):
            if section["type"] == "description":
                form_structure["items"].append({
                    "title": section["content"],
                    "description": section.get("additional_content", "")
                })
            elif section["type"] == "questions":
                # Add questions for this section
                section_questions = self._filter_questions_for_section(questions, section)
                for question in section_questions:
                    form_item = self._convert_question_to_form_item(question, template)
                    if form_item:
                        form_structure["items"].append(form_item)

        self.logger.info("Applied template to form structure", extra={
            "template_id": template.get("template_id"),
            "section_count": len(template.get("sections", [])),
            "item_count": len(form_structure["items"]),
            "total_questions": len(questions)
        })

        return form_structure

    def _generate_title_from_template(
        self,
        template: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> str:
        """Generate form title using template and metadata."""
        cert_name = metadata.get("certification_name", "Assessment")
        template_name = template.get("name", "Assessment")

        if "Default" in template_name:
            return f"{cert_name} Assessment"
        else:
            return f"{cert_name} - {template_name}"

    def _generate_description_from_template(
        self,
        template: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> str:
        """Generate form description using template and metadata."""
        base_description = template.get("description", "Assessment form")

        duration = metadata.get("estimated_duration_minutes")
        if duration:
            base_description += f"\n\nEstimated completion time: {duration} minutes"

        return base_description

    def _filter_questions_for_section(
        self,
        questions: List[Dict],
        section: Dict[str, Any]
    ) -> List[Dict]:
        """Filter questions that belong to a specific section."""
        if "domain_filter" in section:
            return [q for q in questions if q.get("domain") == section["domain_filter"]]
        else:
            return questions

    def _convert_question_to_form_item(
        self,
        question: Dict[str, Any],
        template: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Convert an assessment question to a Google Forms item using template mappings."""
        question_type = question.get("question_type", "multiple_choice")
        mappings = template.get("question_type_mappings", {})

        if question_type not in mappings:
            self.logger.warning("Unsupported question type in template", extra={
                "question_type": question_type,
                "question_id": question.get("id")
            })
            return None

        forms_type = mappings[question_type]

        item = {
            "title": question.get("question_text", ""),
            "description": question.get("explanation", ""),
            "questionItem": {
                "question": {
                    "required": True
                }
            }
        }

        # Configure based on Google Forms question type
        if forms_type == "choiceQuestion":
            if question_type == "true_false":
                options = [{"value": "True"}, {"value": "False"}]
            else:
                options = [{"value": opt} for opt in question.get("options", [])]

            item["questionItem"]["question"]["choiceQuestion"] = {
                "type": "RADIO",
                "options": options,
                "shuffle": template.get("form_settings", {}).get("shuffle_questions", False)
            }

        elif forms_type == "textQuestion":
            item["questionItem"]["question"]["textQuestion"] = {
                "paragraph": question_type in ["scenario", "essay", "paragraph"]
            }

        elif forms_type == "scaleQuestion":
            item["questionItem"]["question"]["scaleQuestion"] = {
                "low": 1,
                "high": question.get("scale_max", 5),
                "lowLabel": question.get("scale_low_label", "Strongly Disagree"),
                "highLabel": question.get("scale_high_label", "Strongly Agree")
            }

        return item

    def save_template(
        self,
        template: Dict[str, Any],
        certification_type: str,
        version: str = "v1"
    ) -> Path:
        """Save a template to file for reuse."""
        # Ensure templates directory exists
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        template_path = self.templates_dir / f"{certification_type}_{version}.json"

        try:
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, ensure_ascii=False)

            self.logger.info("Saved template to file", extra={
                "certification_type": certification_type,
                "version": version,
                "template_path": str(template_path),
                "template_id": template.get("template_id")
            })

            # Update cache
            template_key = f"{certification_type}_{version}"
            self._template_cache[template_key] = template

            return template_path

        except Exception as e:
            self.logger.error("Failed to save template", extra={
                "certification_type": certification_type,
                "template_path": str(template_path),
                "error": str(e)
            })
            raise

    def list_available_templates(self) -> List[Dict[str, Any]]:
        """List all available templates with their metadata."""
        templates = []

        # Check file system templates
        if self.templates_dir.exists():
            for template_file in self.templates_dir.glob("*.json"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template = json.load(f)

                    templates.append({
                        "certification_type": template_file.stem.split('_')[0],
                        "version": template_file.stem.split('_')[-1],
                        "template_id": template.get("template_id"),
                        "name": template.get("name"),
                        "description": template.get("description"),
                        "file_path": str(template_file),
                        "statistics": template.get("statistics", {})
                    })

                except (json.JSONDecodeError, KeyError) as e:
                    self.logger.warning("Invalid template file", extra={
                        "template_file": str(template_file),
                        "error": str(e)
                    })

        # Add built-in default template
        templates.append({
            "certification_type": "default",
            "version": "v1",
            "template_id": "default_v1",
            "name": "Default Assessment Template",
            "description": "Built-in default template",
            "file_path": "built-in",
            "statistics": {"question_count": "variable"}
        })

        return templates

    def clear_template_cache(self):
        """Clear the template cache to force reload from files."""
        self._template_cache.clear()
        self.logger.info("Template cache cleared")