"""
PresGen-Training2 Core Module
Handles LivePortrait integration, voice cloning, and content processing
"""

from .liveportrait.avatar_engine import LivePortraitEngine
from .voice.voice_manager import VoiceProfileManager
from .content.processor import ContentProcessor

__all__ = ['LivePortraitEngine', 'VoiceProfileManager', 'ContentProcessor']