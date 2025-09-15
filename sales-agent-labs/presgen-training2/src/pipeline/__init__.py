"""
PresGen-Training2 Pipeline Module
Handles video appending, format normalization, and transitions
"""

from .appender.video_appender import VideoAppendingEngine

__all__ = ['VideoAppendingEngine']