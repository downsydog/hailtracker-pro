"""
Background Task Queue Abstraction

Two backends:
  1. ThreadTaskQueue  — in-process ThreadPoolExecutor (default, zero deps)
  2. CeleryTaskQueue  — Redis-backed Celery (production, opt-in via CELERY_BROKER_URL)

Environment:
    CELERY_BROKER_URL - If set, uses Celery backend. Otherwise ThreadTaskQueue.
    WORKER_POOL_SIZE  - Thread pool max workers (default: 4)
"""

import os
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Result of a submitted task."""
    task_name: str
    submitted_at: str
    completed_at: Optional[str] = None
    success: Optional[bool] = None
    error: Optional[str] = None


class ThreadTaskQueue:
    """
    In-process background task queue backed by ThreadPoolExecutor.

    Zero external dependencies. Suitable for single-process deployments
    and local development.

    Features:
      - Named tasks with deduplication (won't double-submit same name)
      - Status tracking per task
      - Configurable pool size via WORKER_POOL_SIZE
    """

    def __init__(self, max_workers: Optional[int] = None):
        self._max_workers = max_workers or int(os.environ.get('WORKER_POOL_SIZE', '4'))
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_workers,
            thread_name_prefix='hailworker',
        )
        self._lock = threading.Lock()
        self._tasks: Dict[str, Future] = {}
        self._results: Dict[str, TaskResult] = {}
        self._started = True
        logger.info("ThreadTaskQueue started: max_workers=%d", self._max_workers)

    def submit(self, task_name: str, fn: Callable, *args, **kwargs) -> bool:
        """
        Submit a task for background execution.

        Args:
            task_name: Unique name for deduplication (e.g. 'mrms_refresh')
            fn: Callable to execute
            *args, **kwargs: Arguments to fn

        Returns:
            True if submitted, False if already running with that name.
        """
        with self._lock:
            # Dedup: don't re-submit if already running
            existing = self._tasks.get(task_name)
            if existing is not None and not existing.done():
                logger.debug("Task '%s' already running, skipping", task_name)
                return False

            result = TaskResult(
                task_name=task_name,
                submitted_at=datetime.utcnow().isoformat() + 'Z',
            )
            self._results[task_name] = result

            future = self._executor.submit(self._run_task, task_name, fn, args, kwargs)
            self._tasks[task_name] = future
            logger.info("Task '%s' submitted", task_name)
            return True

    def _run_task(self, task_name: str, fn: Callable, args: tuple, kwargs: dict):
        """Execute task and record result."""
        try:
            fn(*args, **kwargs)
            with self._lock:
                r = self._results.get(task_name)
                if r:
                    r.success = True
                    r.completed_at = datetime.utcnow().isoformat() + 'Z'
            logger.info("Task '%s' completed OK", task_name)
        except Exception as e:
            with self._lock:
                r = self._results.get(task_name)
                if r:
                    r.success = False
                    r.error = str(e)
                    r.completed_at = datetime.utcnow().isoformat() + 'Z'
            logger.error("Task '%s' failed: %s", task_name, e)

    def is_running(self, task_name: str) -> bool:
        """Check if a task is currently running."""
        with self._lock:
            future = self._tasks.get(task_name)
            return future is not None and not future.done()

    def get_result(self, task_name: str) -> Optional[TaskResult]:
        """Get the last result for a task."""
        with self._lock:
            return self._results.get(task_name)

    def get_status(self) -> Dict[str, Any]:
        """Get queue status for health checks."""
        with self._lock:
            active = sum(1 for f in self._tasks.values() if not f.done())
            completed = sum(1 for f in self._tasks.values() if f.done())
            failed = sum(
                1 for r in self._results.values()
                if r.success is False
            )
        return {
            'backend': 'thread',
            'max_workers': self._max_workers,
            'active_tasks': active,
            'completed_tasks': completed,
            'failed_tasks': failed,
            'task_names': list(self._tasks.keys()),
        }

    def shutdown(self, wait: bool = True):
        """Shutdown the thread pool."""
        if self._started:
            self._executor.shutdown(wait=wait)
            self._started = False
            logger.info("ThreadTaskQueue shutdown (wait=%s)", wait)


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------
_instance: Optional[ThreadTaskQueue] = None
_instance_lock = threading.Lock()


def get_task_queue() -> ThreadTaskQueue:
    """
    Get the singleton task queue instance.

    Uses CELERY_BROKER_URL to decide backend. If not set, uses ThreadTaskQueue.
    (CeleryTaskQueue is a future extension point — for now, always ThreadTaskQueue.)
    """
    global _instance
    if _instance is not None:
        return _instance

    with _instance_lock:
        if _instance is not None:
            return _instance

        broker = os.environ.get('CELERY_BROKER_URL', '')
        if broker:
            # Future: CeleryTaskQueue integration point
            logger.info(
                "CELERY_BROKER_URL is set (%s), but Celery backend not yet "
                "implemented. Falling back to ThreadTaskQueue.", broker[:30]
            )

        _instance = ThreadTaskQueue()
        return _instance
