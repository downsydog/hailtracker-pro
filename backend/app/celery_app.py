"""
Celery Application Configuration
================================
Background task processing for storm discovery and cleanup.
"""

from celery import Celery
from .config import Config


def create_celery_app(app=None):
    """
    Create and configure Celery application.

    Args:
        app: Optional Flask app for context integration

    Returns:
        Configured Celery app
    """
    # Weather-core task modules (always available)
    _include = [
        'src.workers.radar_tick',
        'src.workers.radar_backfill',
        'src.workers.radar_watchdog',
    ]

    # CRM task modules are optional (require SQLAlchemy + full Flask stack)
    try:
        import backend.app.tasks.storm_tasks  # noqa: F401
        _include += [
            'backend.app.tasks.storm_tasks',
            'backend.app.tasks.cleanup_tasks',
            'backend.app.tasks.auto_nudges',
        ]
        _crm_tasks_available = True
    except Exception:
        _crm_tasks_available = False

    celery = Celery(
        'hailtracker',
        broker=Config.CELERY_BROKER_URL,
        backend=Config.CELERY_RESULT_BACKEND,
        include=_include,
    )

    # Scheduled tasks (Celery Beat)
    _beat_schedule = {
        'radar-tick': {
            'task': 'src.workers.radar_tick.radar_tick',
            'schedule': 120.0,  # Every 2 minutes
        },
        'radar-watchdog': {
            'task': 'src.workers.radar_watchdog.radar_watchdog',
            'schedule': 60.0,  # Every 1 minute
        },
    }

    if _crm_tasks_available:
        _beat_schedule.update({
            'cleanup-expired-storms': {
                'task': 'backend.app.tasks.cleanup_tasks.cleanup_expired_storms',
                'schedule': 86400.0,  # Once per day
            },
            'process-auto-nudges': {
                'task': 'backend.app.tasks.auto_nudges.process_auto_nudges',
                'schedule': 900.0,  # Every 15 minutes
            },
        })

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
        beat_schedule=_beat_schedule,

        # Task routing
        task_routes={
            'src.workers.radar_tick.*': {'queue': 'radar'},
            'src.workers.radar_backfill.*': {'queue': 'radar_backfill'},
            'src.workers.radar_watchdog.*': {'queue': 'radar_ops'},
            'backend.app.tasks.*': {'queue': 'radar_ops'},
        },
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
