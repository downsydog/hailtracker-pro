"""
Background Workers Module

Provides a lightweight task queue abstraction:
  - ThreadTaskQueue (default): in-process thread pool, zero infrastructure
  - CeleryTaskQueue (opt-in): Redis-backed Celery, via CELERY_BROKER_URL

Usage:
    from src.workers import get_task_queue

    q = get_task_queue()
    q.submit('mrms_refresh', my_func, arg1, arg2)
    print(q.get_status())
"""

from .task_queue import get_task_queue, ThreadTaskQueue

__all__ = ['get_task_queue', 'ThreadTaskQueue']
