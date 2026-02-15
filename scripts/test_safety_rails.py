#!/usr/bin/env python3
"""
Offline test for safety rails (HARDEN-4).

Verifies:
  - CircuitBreaker state transitions (closed -> open -> half_open -> closed)
  - CircuitBreakerOpen exception
  - Guard context manager
  - Shutdown flag and callbacks
  - Status reporting

Usage:
    python scripts/test_safety_rails.py
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 60)
    print("SAFETY RAILS OFFLINE TEST (HARDEN-4)")
    print("=" * 60)

    # --- 1) Import ---
    print("\n[1] Import check...")
    from src.safety.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
    from src.safety.shutdown import (
        is_shutting_down, register_shutdown_callback,
        _shutdown_flag, _callbacks,
    )
    print("    OK: All safety modules imported")

    # --- 2) Circuit breaker — closed state ---
    print("\n[2] Circuit breaker — closed state...")
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.5, success_threshold=1)

    assert cb.allow('KTLX') is True
    assert cb.get_state('KTLX') == 'closed'
    cb.record_success('KTLX')
    assert cb.get_state('KTLX') == 'closed'
    print("    OK: starts closed, success keeps it closed")

    # --- 3) Trip to OPEN ---
    print("\n[3] Trip to OPEN...")
    for i in range(3):
        cb.record_failure('KTLX')

    assert cb.get_state('KTLX') == 'open'
    assert cb.allow('KTLX') is False
    print("    OK: 3 failures -> open, requests blocked")

    # --- 4) Cooldown to HALF_OPEN ---
    print("\n[4] Cooldown to HALF_OPEN...")
    time.sleep(0.6)  # Wait past cooldown
    assert cb.allow('KTLX') is True  # Transitions to half_open
    assert cb.get_state('KTLX') == 'half_open'
    print("    OK: after cooldown -> half_open, probe allowed")

    # --- 5) Recovery to CLOSED ---
    print("\n[5] Recovery to CLOSED...")
    cb.record_success('KTLX')  # success_threshold=1
    assert cb.get_state('KTLX') == 'closed'
    print("    OK: success in half_open -> closed")

    # --- 6) Half-open failure -> OPEN again ---
    print("\n[6] Half-open failure -> OPEN...")
    cb2 = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.3, success_threshold=2)
    cb2.record_failure('KFWS')
    cb2.record_failure('KFWS')
    assert cb2.get_state('KFWS') == 'open'

    time.sleep(0.4)
    cb2.allow('KFWS')  # -> half_open
    cb2.record_failure('KFWS')  # Fail probe
    assert cb2.get_state('KFWS') == 'open'
    print("    OK: failed probe in half_open -> open again")

    # --- 7) Guard context manager ---
    print("\n[7] Guard context manager...")
    cb3 = CircuitBreaker(failure_threshold=2, cooldown_seconds=60)

    with cb3.guard('TEST'):
        pass  # Success
    assert cb3.get_state('TEST') == 'closed'

    try:
        with cb3.guard('TEST'):
            raise RuntimeError("oops")
    except RuntimeError:
        pass

    try:
        with cb3.guard('TEST'):
            raise RuntimeError("oops2")
    except RuntimeError:
        pass

    assert cb3.get_state('TEST') == 'open'

    # Now guard should raise CircuitBreakerOpen
    try:
        with cb3.guard('TEST'):
            assert False, "Should not reach here"
    except CircuitBreakerOpen as e:
        assert e.key == 'TEST'
        assert e.retry_after > 0
        print(f"    OK: CircuitBreakerOpen raised: {e}")

    # --- 8) Status ---
    print("\n[8] Status...")
    status = cb.get_status()
    assert 'KTLX' in status
    assert status['KTLX']['state'] == 'closed'
    print(f"    OK: {status}")

    # --- 9) Reset ---
    print("\n[9] Reset...")
    cb.reset('KTLX')
    assert cb.get_state('KTLX') == 'closed'
    cb.reset()  # Reset all
    assert len(cb.get_status()) == 0
    print("    OK: reset works")

    # --- 10) Shutdown flag ---
    print("\n[10] Shutdown flag...")
    _shutdown_flag.clear()
    _callbacks.clear()

    assert is_shutting_down() is False

    callback_called = []
    register_shutdown_callback(lambda: callback_called.append(True))

    _shutdown_flag.set()
    assert is_shutting_down() is True
    print("    OK: shutdown flag works")

    # Clean up
    _shutdown_flag.clear()
    _callbacks.clear()

    print("\n" + "=" * 60)
    print("ALL SAFETY RAILS TESTS PASSED (HARDEN-4)")
    print("=" * 60)


if __name__ == '__main__':
    main()
