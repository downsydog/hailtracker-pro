#!/usr/bin/env python3
"""
Offline test for the background task queue (HARDEN-2).

Verifies:
  - Import succeeds
  - ThreadTaskQueue submit/dedup/status works
  - Error handling records failures
  - Singleton factory works
  - Shutdown is safe

Usage:
    python scripts/test_task_queue.py
"""

import sys
import os
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 60)
    print("TASK QUEUE OFFLINE TEST (HARDEN-2)")
    print("=" * 60)

    # --- 1) Import ---
    print("\n[1] Import check...")
    from src.workers.task_queue import ThreadTaskQueue, get_task_queue
    print("    OK: Imported ThreadTaskQueue, get_task_queue")

    # --- 2) Basic submit ---
    print("\n[2] Basic submit + completion...")
    q = ThreadTaskQueue(max_workers=2)
    results = []

    def worker(val):
        time.sleep(0.1)
        results.append(val)

    ok = q.submit('test_basic', worker, 42)
    assert ok is True, "First submit should return True"
    print("    Submitted 'test_basic'")

    # Wait for completion
    time.sleep(0.5)
    assert 42 in results, f"Expected 42 in results, got {results}"
    r = q.get_result('test_basic')
    assert r is not None
    assert r.success is True
    assert r.completed_at is not None
    print(f"    OK: task completed, success={r.success}")

    # --- 3) Dedup ---
    print("\n[3] Dedup (re-submit while running)...")
    barrier = threading.Event()

    def slow_worker():
        barrier.wait(timeout=5)

    ok1 = q.submit('test_dedup', slow_worker)
    assert ok1 is True
    assert q.is_running('test_dedup')

    ok2 = q.submit('test_dedup', slow_worker)
    assert ok2 is False, "Second submit should be deduplicated"
    print("    OK: duplicate submission rejected")

    barrier.set()  # Release
    time.sleep(0.3)
    assert not q.is_running('test_dedup')
    print("    OK: task completed after barrier release")

    # --- 4) Error handling ---
    print("\n[4] Error handling...")

    def failing_worker():
        raise RuntimeError("intentional failure")

    q.submit('test_fail', failing_worker)
    time.sleep(0.3)
    r = q.get_result('test_fail')
    assert r is not None
    assert r.success is False
    assert 'intentional failure' in r.error
    print(f"    OK: failure recorded: {r.error}")

    # --- 5) Status ---
    print("\n[5] Queue status...")
    status = q.get_status()
    assert status['backend'] == 'thread'
    assert status['max_workers'] == 2
    assert 'test_basic' in status['task_names']
    assert status['failed_tasks'] >= 1
    print(f"    OK: {status}")

    # --- 6) Shutdown ---
    print("\n[6] Shutdown...")
    q.shutdown(wait=True)
    q.shutdown(wait=True)  # Double shutdown should be safe
    print("    OK: shutdown safe")

    # --- 7) Singleton factory ---
    print("\n[7] Singleton factory...")
    # Reset singleton for test
    import src.workers.task_queue as tq_mod
    tq_mod._instance = None

    q1 = get_task_queue()
    q2 = get_task_queue()
    assert q1 is q2, "Singleton should return same instance"
    print("    OK: get_task_queue() is singleton")
    q1.shutdown()
    tq_mod._instance = None  # Clean up

    print("\n" + "=" * 60)
    print("ALL TASK QUEUE TESTS PASSED (HARDEN-2)")
    print("=" * 60)


if __name__ == '__main__':
    main()
