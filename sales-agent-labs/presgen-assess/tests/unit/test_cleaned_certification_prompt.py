"""Tests for the Tier 1 certification prompt template formatting."""

from pathlib import Path
import re


class _SafeDict(dict):
    """Replicate SafeDict behavior from the workflow template formatter."""

    def __missing__(self, key: str) -> str:  # pragma: no cover - defensive
        return "{" + key + "}"


def test_cleaned_prompt_template_formats_without_unresolved_placeholders():
    """The enhanced prompt template should format cleanly with available variables."""
    project_root = Path(__file__).resolve().parents[2]
    template_path = project_root / "CLEANED_CERTIFICATION_PROMPT.md"
    template_text = template_path.read_text()

    sample_values = _SafeDict(
        {
            "skill_name": "Data Engineering",
            "exam_domain": "AWS Machine Learning Specialty",
            "learning_objectives": '["Apply ETL workflows", "Optimize data pipelines"]',
            "content_outline_sections": '[{"section_title": "Intro", "slide_count": 3}]',
            "knowledge_base_context": (
                "### Domain: Data Engineering | Source: transcript | Relevance: 0.92\n"
                "**Learning Objective**: Apply ETL workflows\n"
                "**Task**: Task 1.1\n"
                "Paraphrased chunk content demonstrating accurate sourcing.\n"
                "---"
            ),
            "slide_count": 12,
            "difficulty_level": "intermediate",
            "estimated_duration_minutes": 45,
        }
    )

    formatted = template_text.format_map(sample_values)

    unresolved = re.findall(r"{([a-zA-Z_][a-zA-Z0-9_]*)}", formatted)

    assert not unresolved, f"Unresolved placeholders remain: {unresolved}"
    assert "chunk_text" not in formatted, "Sample context placeholder leaked into formatted prompt"
