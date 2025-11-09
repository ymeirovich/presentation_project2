"""Background tasks for async processing.

Phase 3: Architectural Improvements - Background Job Queue
"""

from src.tasks.course_generation import generate_course_async

__all__ = ['generate_course_async']
