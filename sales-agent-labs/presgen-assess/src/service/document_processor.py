"""
Document Processor for PresGen-Assess

Handles processing of various document types (PDF, DOCX, TXT)
and extracts structured content for ChromaDB storage.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import aiofiles
from io import BytesIO

# Optional imports for different file types
try:
    import pypdf
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False


logger = logging.getLogger(__name__)


class DocumentChunk:
    """Represents a processed document chunk"""

    def __init__(
        self,
        content: str,
        section: str = "",
        page: Optional[int] = None,
        chunk_index: int = 0,
        keywords: Optional[List[str]] = None,
        concepts: Optional[List[str]] = None,
        subdomain: str = ""
    ):
        self.content = content
        self.section = section
        self.page = page
        self.chunk_index = chunk_index
        self.keywords = keywords or []
        self.concepts = concepts or []
        self.subdomain = subdomain

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'content': self.content,
            'section': self.section,
            'page': self.page,
            'chunk_index': self.chunk_index,
            'keywords': self.keywords,
            'concepts': self.concepts,
            'subdomain': self.subdomain
        }


class DocumentProcessor:
    """Processor for different document types"""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.setup_nltk()

    def setup_nltk(self):
        """Setup NLTK resources if available"""
        if not NLTK_AVAILABLE:
            logger.warning("NLTK not available, text analysis will be limited")
            return

        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            logger.info("Downloading NLTK resources...")
            try:
                nltk.download('punkt', quiet=True)
                nltk.download('stopwords', quiet=True)
            except Exception as e:
                logger.warning(f"Failed to download NLTK resources: {e}")

    async def process_file(self, file_path: Path, mime_type: str) -> List[Dict[str, Any]]:
        """Process file based on MIME type"""

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Processing file: {file_path} (type: {mime_type})")

        if mime_type == 'application/pdf':
            return await self.process_pdf(file_path)
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            return await self.process_docx(file_path)
        elif mime_type in ['text/plain', 'text/markdown']:
            return await self.process_text(file_path)
        else:
            # Try to process as text
            logger.warning(f"Unknown MIME type {mime_type}, attempting text processing")
            return await self.process_text(file_path)

    async def process_pdf(self, file_path: Path) -> List[Dict[str, Any]]:
        """Process PDF file"""
        if not PDF_AVAILABLE:
            raise ImportError("pypdf library not installed. Install with: pip install pypdf")

        chunks = []
        current_section = ""

        try:
            with open(file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)

                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        text = page.extract_text()
                        if not text or len(text.strip()) < self.min_chunk_size:
                            continue

                        # Try to extract section headers
                        section = self.extract_section_header(text)
                        if section:
                            current_section = section

                        # Clean and chunk the text
                        cleaned_text = self.clean_text(text)
                        page_chunks = self.create_chunks(
                            text=cleaned_text,
                            section=current_section,
                            page=page_num
                        )

                        chunks.extend([chunk.to_dict() for chunk in page_chunks])

                    except Exception as e:
                        logger.warning(f"Error processing page {page_num}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
            raise

        logger.info(f"Extracted {len(chunks)} chunks from PDF")
        return chunks

    async def process_docx(self, file_path: Path) -> List[Dict[str, Any]]:
        """Process DOCX file"""
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx library not installed. Install with: pip install python-docx")

        chunks = []
        current_section = ""

        try:
            doc = DocxDocument(file_path)
            full_text = []
            page_num = 1  # DOCX doesn't have explicit pages

            for paragraph in doc.paragraphs:
                if not paragraph.text.strip():
                    continue

                # Check if paragraph is a heading
                if paragraph.style.name.startswith('Heading'):
                    current_section = paragraph.text.strip()
                    full_text.append(f"\n\n{paragraph.text}\n")
                else:
                    full_text.append(paragraph.text)

            # Combine text and create chunks
            combined_text = " ".join(full_text)
            cleaned_text = self.clean_text(combined_text)

            if len(cleaned_text.strip()) >= self.min_chunk_size:
                doc_chunks = self.create_chunks(
                    text=cleaned_text,
                    section=current_section,
                    page=page_num
                )
                chunks.extend([chunk.to_dict() for chunk in doc_chunks])

        except Exception as e:
            logger.error(f"Error processing DOCX {file_path}: {e}")
            raise

        logger.info(f"Extracted {len(chunks)} chunks from DOCX")
        return chunks

    async def process_text(self, file_path: Path) -> List[Dict[str, Any]]:
        """Process plain text file"""
        chunks = []

        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                content = await file.read()

            if len(content.strip()) < self.min_chunk_size:
                logger.warning(f"Text file {file_path} too short to process")
                return chunks

            # Try to detect sections
            current_section = self.extract_section_header(content)

            # Clean and chunk the text
            cleaned_text = self.clean_text(content)
            text_chunks = self.create_chunks(
                text=cleaned_text,
                section=current_section,
                page=1
            )

            chunks.extend([chunk.to_dict() for chunk in text_chunks])

        except Exception as e:
            logger.error(f"Error processing text file {file_path}: {e}")
            raise

        logger.info(f"Extracted {len(chunks)} chunks from text file")
        return chunks

    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.,!?;:()\-]', ' ', text)

        # Remove multiple periods/dots
        text = re.sub(r'\.{3,}', '...', text)

        # Normalize quotes
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r'['']', "'", text)

        return text.strip()

    def extract_section_header(self, text: str) -> str:
        """Extract section header from text"""
        lines = text.split('\n')

        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if not line:
                continue

            # Common patterns for section headers
            if (len(line) < 100 and  # Not too long
                (line.isupper() or  # All caps
                 re.match(r'^[A-Z][^.]*$', line) or  # Starts with capital, no period
                 re.match(r'^\d+\.?\s+[A-Z]', line) or  # Numbered section
                 re.match(r'^Chapter\s+\d+', line, re.IGNORECASE) or  # Chapter X
                 re.match(r'^Section\s+\d+', line, re.IGNORECASE))):  # Section X
                return line

        return ""

    def create_chunks(
        self,
        text: str,
        section: str = "",
        page: Optional[int] = None
    ) -> List[DocumentChunk]:
        """Create chunks from text with overlap"""
        if len(text) <= self.chunk_size:
            # Text is small enough to be one chunk
            chunk = DocumentChunk(
                content=text,
                section=section,
                page=page,
                chunk_index=0,
                keywords=self.extract_keywords(text),
                concepts=self.extract_concepts(text)
            )
            return [chunk]

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + self.chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending within overlap distance
                for i in range(min(self.chunk_overlap, len(text) - end)):
                    if text[end + i] in '.!?':
                        end = end + i + 1
                        break

            chunk_text = text[start:end].strip()

            if len(chunk_text) >= self.min_chunk_size:
                chunk = DocumentChunk(
                    content=chunk_text,
                    section=section,
                    page=page,
                    chunk_index=chunk_index,
                    keywords=self.extract_keywords(chunk_text),
                    concepts=self.extract_concepts(chunk_text)
                )
                chunks.append(chunk)
                chunk_index += 1

            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break

        return chunks

    def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        if not NLTK_AVAILABLE:
            # Simple keyword extraction without NLTK
            words = re.findall(r'\b[A-Z][a-z]+\b', text)  # Capitalized words
            return list(set(words))[:10]

        try:
            # Tokenize and filter
            words = word_tokenize(text.lower())
            stop_words = set(stopwords.words('english'))

            # Filter out stopwords and short words
            keywords = [
                word for word in words
                if (word.isalpha() and
                    len(word) > 3 and
                    word not in stop_words)
            ]

            # Get unique keywords, limit to top 10
            return list(set(keywords))[:10]

        except Exception:
            # Fallback to simple extraction
            words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
            return list(set(words))[:10]

    def extract_concepts(self, text: str) -> List[str]:
        """Extract key concepts from text"""
        concepts = []

        # Technical terms (capitalized phrases)
        tech_terms = re.findall(r'\b[A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)*\b', text)
        concepts.extend([term for term in tech_terms if len(term) > 3])

        # Acronyms
        acronyms = re.findall(r'\b[A-Z]{2,}\b', text)
        concepts.extend(acronyms)

        # Common patterns for important concepts
        concept_patterns = [
            r'\b(?:AWS|Azure|Google Cloud|GCP)\s+[A-Z][a-zA-Z\s]*\b',
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Service|Platform|Protocol|Algorithm))\b',
            r'\b(?:best practices?|design patterns?|architectures?|methodologies?)\b',
        ]

        for pattern in concept_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            concepts.extend(matches)

        # Remove duplicates and limit
        unique_concepts = list(set([c.strip() for c in concepts if len(c.strip()) > 2]))
        return unique_concepts[:15]

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'min_chunk_size': self.min_chunk_size,
            'pdf_support': PDF_AVAILABLE,
            'docx_support': DOCX_AVAILABLE,
            'nltk_support': NLTK_AVAILABLE
        }


# Example usage
async def main():
    """Example usage of DocumentProcessor"""
    processor = DocumentProcessor()

    # Example with a text file
    content = """
    Chapter 1: Introduction to Cloud Computing

    Cloud computing is a model for enabling ubiquitous, convenient, on-demand network access
    to a shared pool of configurable computing resources (e.g., networks, servers, storage,
    applications, and services) that can be rapidly provisioned and released with minimal
    management effort or service provider interaction.

    Amazon Web Services (AWS) provides a comprehensive cloud computing platform that includes
    Infrastructure as a Service (IaaS), Platform as a Service (PaaS), and Software as a Service (SaaS).
    """

    # Create a temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
        temp_file.write(content)
        temp_file_path = Path(temp_file.name)

    try:
        # Process the file
        chunks = await processor.process_file(temp_file_path, 'text/plain')
        print(f"Processed {len(chunks)} chunks:")
        for i, chunk in enumerate(chunks):
            print(f"\nChunk {i}:")
            print(f"Content: {chunk['content'][:100]}...")
            print(f"Keywords: {chunk['keywords']}")
            print(f"Concepts: {chunk['concepts']}")
    finally:
        # Clean up
        temp_file_path.unlink()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())