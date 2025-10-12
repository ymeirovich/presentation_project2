import logging
import uuid
from typing import Optional

from dataclasses import dataclass

from src.mcp_lab.rpc_client import MCPClient, ToolError
from .google_slides_processor import SlideData


@dataclass
class GeneratedNotes:
    text: str
    tokens_used: Optional[int] = None


class SlideNotesGenerator:
    """Generate speaker notes for slides using the MCP LLM summarize tool."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("presgen_training2.notes")

    def _format_slide_context(self, slide: SlideData, presentation_title: Optional[str]) -> str:
        """Format slide content into a prompt-friendly text block."""
        parts = []
        if presentation_title:
            parts.append(f"Presentation Title: {presentation_title}")
        if slide.title:
            parts.append(f"Slide Title: {slide.title}")

        if slide.body_text:
            parts.append("Visible Slide Content:")
            parts.append(slide.body_text)
        else:
            parts.append("Visible Slide Content: (not available)")

        # Guarantee minimum length for LLM requirements
        combined = "\n".join(parts).strip()
        if len(combined) < 60:
            combined += "\n\nAdditional Context: Provide a concise explanation for this slide."
        return combined

    def generate_notes(self, slide: SlideData, presentation_title: Optional[str] = None) -> Optional[GeneratedNotes]:
        """Call MCP service to synthesize speaker notes for a slide."""
        report_text = self._format_slide_context(slide, presentation_title)

        params = {
            "report_text": report_text,
            "max_bullets": 3,
            "max_script_chars": 600,
            "max_sections": 1,
        }

        req_id = f"auto-notes-{uuid.uuid4().hex[:8]}"

        try:
            with MCPClient() as client:
                result = client.call("llm.summarize", params, req_id=req_id, timeout=120.0)

            sections = result.get("sections") or []
            if not sections:
                self.logger.warning("LLM summarize returned no sections for slide %s", slide.slide_id)
                return None

            script = sections[0].get("script", "")
            if not script:
                self.logger.warning("LLM summarize provided empty script for slide %s", slide.slide_id)
                return None

            script = script.strip()
            if not script:
                return None

            tokens_used = result.get("meta", {}).get("token_count")
            return GeneratedNotes(text=script, tokens_used=tokens_used)

        except ToolError as e:
            self.logger.error("MCP tool error while generating notes: %s", e)
        except Exception as e:
            self.logger.error("Failed to generate notes for slide %s: %s", slide.slide_id, e)

        return None
