"""
PresGen-Training2 Presentation Module
Handles Google Slides integration, slides-to-video conversion, and presentation rendering
"""

from .slides.google_slides_processor import GoogleSlidesProcessor
from .renderer.slides_to_video import SlidesToVideoRenderer

__all__ = ['GoogleSlidesProcessor', 'SlidesToVideoRenderer']