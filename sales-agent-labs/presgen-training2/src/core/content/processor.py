import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import logging
# Use simple logging for now - can integrate with parent project later
def jlog(logger, level, event, **kwargs):
    """Simple logging wrapper"""
    logger.log(level, f"Event: {event}, Data: {kwargs}")

@dataclass
class ProcessedContent:
    title: str
    summary: str
    script: str
    slides_content: Optional[List[Dict[str, Any]]] = None
    processing_time: Optional[float] = None

class ContentProcessor:
    """
    Process uploaded content files into presentation scripts
    Handles PDF, DOCX, TXT, and MD files
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("presgen_training2.content")

    def process_content_file(self,
                           file_path: str,
                           instructions: str = None) -> Optional[ProcessedContent]:
        """
        Process uploaded content file into presentation script

        Args:
            file_path: Path to content file (PDF, DOCX, TXT, MD)
            instructions: Custom instructions for script generation

        Returns:
            ProcessedContent with generated script and metadata
        """

        try:
            file_path_obj = Path(file_path)

            if not file_path_obj.exists():
                self.logger.error(f"Content file not found: {file_path}")
                return None

            # Extract text based on file type
            text_content = self._extract_text_from_file(file_path_obj)
            if not text_content:
                return None

            # Generate presentation script
            script = self._generate_presentation_script(
                content=text_content,
                instructions=instructions
            )

            # Extract title from content
            title = self._extract_title(text_content)

            # Generate summary
            summary = self._generate_summary(text_content)

            jlog(self.logger, logging.INFO,
                event="content_processed",
                file_path=file_path,
                file_type=file_path_obj.suffix,
                content_length=len(text_content),
                script_length=len(script))

            return ProcessedContent(
                title=title,
                summary=summary,
                script=script
            )

        except Exception as e:
            self.logger.error(f"Error processing content file: {e}")
            return None

    def _extract_text_from_file(self, file_path: Path) -> Optional[str]:
        """Extract text content from various file formats"""

        try:
            suffix = file_path.suffix.lower()

            if suffix == '.txt':
                return self._extract_from_txt(file_path)
            elif suffix == '.md':
                return self._extract_from_markdown(file_path)
            elif suffix == '.pdf':
                return self._extract_from_pdf(file_path)
            elif suffix in ['.docx', '.doc']:
                return self._extract_from_docx(file_path)
            else:
                self.logger.error(f"Unsupported file format: {suffix}")
                return None

        except Exception as e:
            self.logger.error(f"Error extracting text from {file_path}: {e}")
            return None

    def _extract_from_txt(self, file_path: Path) -> str:
        """Extract text from TXT file"""
        return file_path.read_text(encoding='utf-8')

    def _extract_from_markdown(self, file_path: Path) -> str:
        """Extract text from Markdown file"""
        return file_path.read_text(encoding='utf-8')

    def _extract_from_pdf(self, file_path: Path) -> Optional[str]:
        """Extract text from PDF file"""

        try:
            import PyPDF2

            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""

                for page in reader.pages:
                    text += page.extract_text() + "\n"

                return text.strip()

        except ImportError:
            self.logger.error("PyPDF2 not installed. Cannot process PDF files.")
            return None
        except Exception as e:
            self.logger.error(f"Error extracting PDF text: {e}")
            return None

    def _extract_from_docx(self, file_path: Path) -> Optional[str]:
        """Extract text from DOCX file"""

        try:
            from docx import Document

            doc = Document(file_path)
            text = []

            for paragraph in doc.paragraphs:
                text.append(paragraph.text)

            return "\n".join(text)

        except ImportError:
            self.logger.error("python-docx not installed. Cannot process DOCX files.")
            return None
        except Exception as e:
            self.logger.error(f"Error extracting DOCX text: {e}")
            return None

    def _extract_title(self, content: str) -> str:
        """Extract title from content"""

        lines = content.split('\n')

        # Look for markdown headers
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()

        # Look for the first non-empty line
        for line in lines:
            line = line.strip()
            if line:
                # Take first 50 characters as title
                return line[:50] + "..." if len(line) > 50 else line

        return "Untitled Document"

    def _generate_summary(self, content: str) -> str:
        """Generate a summary of the content"""

        # Simple extractive summary (first few sentences)
        sentences = content.split('.')

        summary_sentences = []
        char_count = 0
        max_chars = 300

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if char_count + len(sentence) > max_chars:
                break

            summary_sentences.append(sentence)
            char_count += len(sentence)

            if len(summary_sentences) >= 3:  # Max 3 sentences
                break

        return '. '.join(summary_sentences) + '.' if summary_sentences else content[:300] + "..."

    def _generate_presentation_script(self, content: str, instructions: str = None) -> str:
        """
        Generate presentation script from content

        This is a simplified implementation. In a full version, this would:
        1. Use LLM integration (Gemini) to convert content to script
        2. Apply custom instructions
        3. Structure for voice narration

        For now, we'll create a structured script format.
        """

        # For MVP, create a simple structured script
        script_parts = []

        # Introduction
        script_parts.append("Welcome to this presentation.")

        # Main content (simplified processing)
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

        for i, paragraph in enumerate(paragraphs[:5]):  # Limit to 5 paragraphs
            if len(paragraph) > 50:  # Only include substantial paragraphs
                # Simplify paragraph for narration
                simplified = self._simplify_for_narration(paragraph)
                script_parts.append(simplified)

        # Apply custom instructions if provided
        if instructions:
            script_parts.insert(1, f"As requested: {instructions}")

        # Conclusion
        script_parts.append("Thank you for your attention.")

        return " ".join(script_parts)

    def _simplify_for_narration(self, text: str) -> str:
        """Simplify text for better voice narration"""

        # Remove special characters that don't read well
        simplified = text.replace('&', 'and')
        simplified = simplified.replace('@', 'at')
        simplified = simplified.replace('#', 'number')

        # Ensure sentences end properly
        if not simplified.endswith('.'):
            simplified += '.'

        return simplified

    def process_text_input(self, text: str, instructions: str = None) -> ProcessedContent:
        """Process direct text input into presentation script"""

        try:
            # Generate script from text
            script = self._generate_presentation_script(
                content=text,
                instructions=instructions
            )

            # Extract title and summary
            title = self._extract_title(text)
            summary = self._generate_summary(text)

            jlog(self.logger, logging.INFO,
                event="text_content_processed",
                content_length=len(text),
                script_length=len(script))

            return ProcessedContent(
                title=title,
                summary=summary,
                script=script
            )

        except Exception as e:
            self.logger.error(f"Error processing text input: {e}")
            return ProcessedContent(
                title="Error",
                summary="Processing failed",
                script="Sorry, there was an error processing your content."
            )