import os
import re
import requests
import time
import logging
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Use simple logging for now - can integrate with parent project later
def jlog(logger, level, event, **kwargs):
    """Simple logging wrapper"""
    logger.log(level, f"Event: {event}, Data: {kwargs}")

@dataclass
class SlideData:
    """Individual slide data with notes and timing"""
    slide_id: str
    slide_order: int
    title: str
    slide_image_url: str
    notes_text: str
    estimated_duration: float  # seconds based on notes length
    local_image_path: Optional[str] = None

@dataclass
class GoogleSlidesResult:
    """Result of Google Slides processing"""
    success: bool
    slides: List[SlideData] = None
    presentation_title: str = ""
    total_duration: float = 0.0
    error: Optional[str] = None

class GoogleSlidesProcessor:
    """
    Google Slides URL processing and Notes extraction
    Handles authentication, slide export, and notes parsing
    """

    # OAuth 2.0 scopes for Google Slides API
    SCOPES = [
        "https://www.googleapis.com/auth/presentations",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/script.projects",
        "https://www.googleapis.com/auth/spreadsheets"
    ]

    def __init__(self, logger: Optional[logging.Logger] = None, skip_auth: bool = False):
        self.logger = logger or logging.getLogger("presgen_training2.slides")
        self.service = None
        self.drive_service = None

        if not skip_auth:
            try:
                self._authenticate()
            except Exception as e:
                self.logger.warning(f"Google Slides authentication failed: {e}. Some features may not work.")
        else:
            self.logger.info("Skipping Google Slides authentication for testing")

    def _authenticate(self):
        """Authenticate with Google APIs using OAuth or service account"""
        try:
            creds = None
            token_file = Path(
                os.getenv("OAUTH_TOKEN_PATH", "token.json")
            )
            credentials_file = Path(
                os.getenv(
                    "OAUTH_CLIENT_SECRET_PATH",
                    "config/google_slides_credentials.json"
                )
            )

            # Load existing token
            if token_file.exists():
                creds = Credentials.from_authorized_user_file(str(token_file), self.SCOPES)

            # If no valid credentials, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not credentials_file.exists():
                        self.logger.error("Google Slides credentials file not found. Please set up OAuth credentials.")
                        raise FileNotFoundError(f"Credentials file not found: {credentials_file}")

                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(credentials_file), self.SCOPES)
                    creds = flow.run_local_server(port=0)

                # Save credentials for next run
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())

            # Build services
            self.service = build('slides', 'v1', credentials=creds)
            self.drive_service = build('drive', 'v3', credentials=creds)
            self.logger.info("Google Slides API authentication successful")

        except Exception as e:
            self.logger.error(f"Google Slides authentication failed: {e}")
            raise

    def extract_presentation_id(self, url: str) -> Optional[str]:
        """Extract presentation ID from Google Slides URL"""
        try:
            # Handle various Google Slides URL formats
            patterns = [
                r'/presentation/d/([a-zA-Z0-9-_]+)',
                r'id=([a-zA-Z0-9-_]+)',
                r'/d/([a-zA-Z0-9-_]+)'
            ]

            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)

            self.logger.error(f"Could not extract presentation ID from URL: {url}")
            return None

        except Exception as e:
            self.logger.error(f"Error extracting presentation ID: {e}")
            return None

    def process_google_slides_url(self,
                                url: str,
                                output_dir: str = "temp",
                                default_slide_duration: float = 3.0) -> GoogleSlidesResult:
        """
        Process Google Slides URL and extract slides with notes

        Args:
            url: Google Slides presentation URL
            output_dir: Directory to save slide images
            default_slide_duration: Default duration for slides without notes

        Returns:
            GoogleSlidesResult with slides data and metadata
        """

        start_time = time.time()

        try:
            # Extract presentation ID
            presentation_id = self.extract_presentation_id(url)
            if not presentation_id:
                return GoogleSlidesResult(
                    success=False,
                    error="Invalid Google Slides URL or could not extract presentation ID"
                )

            self.logger.info(f"Processing Google Slides presentation: {presentation_id}")
            jlog(self.logger, logging.INFO,
                event="google_slides_processing_started",
                presentation_id=presentation_id,
                url=url)

            # Get presentation data
            presentation = self.service.presentations().get(
                presentationId=presentation_id
            ).execute()

            presentation_title = presentation.get('title', 'Untitled Presentation')
            slides_data = presentation.get('slides', [])

            self.logger.info(f"Found {len(slides_data)} slides in presentation: {presentation_title}")

            # Process each slide
            processed_slides = []
            total_duration = 0.0

            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            for i, slide in enumerate(slides_data):
                slide_data = self._process_individual_slide(
                    slide=slide,
                    slide_order=i + 1,
                    presentation_id=presentation_id,
                    output_dir=output_dir,
                    default_duration=default_slide_duration
                )

                if slide_data:
                    processed_slides.append(slide_data)
                    total_duration += slide_data.estimated_duration

            processing_time = time.time() - start_time

            self.logger.info(f"Google Slides processing completed in {processing_time:.2f}s")
            jlog(self.logger, logging.INFO,
                event="google_slides_processing_completed",
                processing_time=processing_time,
                slides_count=len(processed_slides),
                total_duration=total_duration,
                presentation_title=presentation_title)

            return GoogleSlidesResult(
                success=True,
                slides=processed_slides,
                presentation_title=presentation_title,
                total_duration=total_duration
            )

        except Exception as e:
            error_msg = f"Google Slides processing failed: {str(e)}"
            self.logger.error(error_msg)
            return GoogleSlidesResult(
                success=False,
                error=error_msg
            )

    def _process_individual_slide(self,
                                slide: Dict[str, Any],
                                slide_order: int,
                                presentation_id: str,
                                output_dir: str,
                                default_duration: float) -> Optional[SlideData]:
        """Process individual slide and extract notes"""

        try:
            slide_id = slide.get('objectId', f'slide_{slide_order}')

            # Extract slide title
            title = self._extract_slide_title(slide)

            # Extract notes text
            notes_text = self._extract_slide_notes(slide)

            # Calculate duration based on notes length
            duration = self._calculate_narration_duration(notes_text, default_duration)

            # Export slide as image
            image_url = self._get_slide_image_url(presentation_id, slide_id)
            local_image_path = self._download_slide_image(
                image_url,
                slide_id,
                output_dir
            )

            return SlideData(
                slide_id=slide_id,
                slide_order=slide_order,
                title=title,
                slide_image_url=image_url,
                notes_text=notes_text,
                estimated_duration=duration,
                local_image_path=local_image_path
            )

        except Exception as e:
            self.logger.error(f"Error processing slide {slide_order}: {e}")
            return None

    def _extract_slide_title(self, slide: Dict[str, Any]) -> str:
        """Extract title from slide"""
        try:
            for element in slide.get('pageElements', []):
                shape = element.get('shape', {})
                if shape.get('shapeType') == 'TEXT_BOX':
                    text_content = shape.get('text', {})
                    for text_element in text_content.get('textElements', []):
                        text_run = text_element.get('textRun', {})
                        content = text_run.get('content', '').strip()
                        if content and len(content) > 5:  # Likely a title
                            return content[:100]  # Truncate long titles

            return f"Slide {slide.get('objectId', 'Unknown')}"

        except Exception:
            return "Untitled Slide"

    def _extract_slide_notes(self, slide: Dict[str, Any]) -> str:
        """Extract notes from slide"""
        try:
            notes_page = slide.get('slideProperties', {}).get('notesPage')
            if not notes_page:
                return ""

            notes_text = ""
            for element in notes_page.get('pageElements', []):
                shape = element.get('shape', {})
                if shape.get('shapeType') == 'TEXT_BOX':
                    text_content = shape.get('text', {})
                    for text_element in text_content.get('textElements', []):
                        text_run = text_element.get('textRun', {})
                        content = text_run.get('content', '')
                        notes_text += content

            return notes_text.strip()

        except Exception as e:
            self.logger.warning(f"Could not extract notes: {e}")
            return ""

    def _calculate_narration_duration(self, notes_text: str, default_duration: float) -> float:
        """Calculate narration duration based on text length"""
        if not notes_text.strip():
            return default_duration

        # Estimate reading time: ~150 words per minute
        words = len(notes_text.split())
        estimated_seconds = (words / 150.0) * 60.0

        # Minimum duration of 2 seconds, maximum of 60 seconds per slide
        return max(2.0, min(60.0, estimated_seconds))

    def _get_slide_image_url(self, presentation_id: str, slide_id: str) -> str:
        """Get download URL for slide as image"""
        # Export slide as PNG image
        return f"https://docs.google.com/presentation/d/{presentation_id}/export/png?id={presentation_id}&pageid={slide_id}"

    def _download_slide_image(self, image_url: str, slide_id: str, output_dir: str) -> Optional[str]:
        """Download slide image to local directory"""
        try:
            output_path = Path(output_dir) / f"slide_{slide_id}.png"

            # Use authenticated session for download
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            with open(output_path, 'wb') as f:
                f.write(response.content)

            self.logger.debug(f"Downloaded slide image: {output_path}")
            return str(output_path)

        except Exception as e:
            self.logger.error(f"Failed to download slide image: {e}")
            return None

    def validate_slides_access(self, url: str) -> bool:
        """Validate that we can access the Google Slides presentation"""
        try:
            presentation_id = self.extract_presentation_id(url)
            if not presentation_id:
                return False

            # Try to get basic presentation info
            presentation = self.service.presentations().get(
                presentationId=presentation_id,
                fields="title"
            ).execute()

            return bool(presentation.get('title'))

        except Exception as e:
            self.logger.error(f"Cannot access presentation: {e}")
            return False
