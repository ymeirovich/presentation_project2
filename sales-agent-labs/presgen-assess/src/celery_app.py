"""Celery application configuration for async task processing.

Phase 3: Architectural Improvements - Background Job Queue
"""

from celery import Celery
from src.common.config import settings

# Create Celery app instance
celery_app = Celery(
    'presgen_assess',
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Configure Celery
celery_app.conf.update(
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # Timezone
    timezone='UTC',
    enable_utc=True,

    # Task tracking
    task_track_started=True,
    task_send_sent_event=True,

    # Time limits (generous for video generation)
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit

    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours
    result_persistent=True,  # Persist results to disk

    # Worker settings
    worker_prefetch_multiplier=1,  # Only fetch one task at a time (tasks are long)
    worker_max_tasks_per_child=10,  # Restart worker after 10 tasks (prevent memory leaks)

    # Retry settings
    task_acks_late=True,  # Acknowledge task after completion (not after pickup)
    task_reject_on_worker_lost=True,  # Requeue tasks if worker dies

    # Task routes (can be extended for different queues)
    task_routes={
        'src.tasks.course_generation.*': {'queue': 'course_generation'},
    },

    # Rate limits
    task_default_rate_limit='10/m',  # Max 10 tasks per minute
)

# Auto-discover tasks from tasks module
celery_app.autodiscover_tasks(['src.tasks'])
