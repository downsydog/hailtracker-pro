"""
Celery Application Configuration
================================
Background task processing for storm discovery and cleanup.
"""

from celery import Celery
from app.config import Config


def create_celery_app(app=None):
    """
    Create and configure Celery application.

    Args:
        app: Optional Flask app for context integration

    Returns:
        Configured Celery app
    """
    celery = Celery(
        'hailtracker',
        broker=Config.CELERY_BROKER_URL,
        backend=Config.CELERY_RESULT_BACKEND,
        include=[
            'backend.app.tasks.storm_tasks',
            'backend.app.tasks.cleanup_tasks',
            'backend.app.tasks.auto_nudges'
        ]
    )

    celery.conf.update(
        # Serialization
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',

        # Timezone
        timezone='UTC',
        enable_utc=True,

        # Task tracking
        task_track_started=True,
        task_time_limit=3600,  # 1 hour max per task

        # Worker settings
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        task_reject_on_worker_lost=True,

        # Scheduled tasks (Celery Beat)
        beat_schedule={
            'cleanup-expired-storms': {
                'task': 'backend.app.tasks.cleanup_tasks.cleanup_expired_storms',
                'schedule': 86400.0,  # Once per day
            },
            'process-auto-nudges': {
                'task': 'backend.app.tasks.auto_nudges.process_auto_nudges',
                'schedule': 900.0,  # Every 15 minutes
            },
        }
    )

    if app:
        celery.conf.update(app.config)

        class ContextTask(celery.Task):
            """Task class that runs within Flask app context."""
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask

    return celery


# Create the celery app instance
celery_app = create_celery_app()
