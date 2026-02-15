#!/usr/bin/env python3
"""
Offline test for observability stack (HARDEN-3).

Verifies:
  - Structured JSON logging works
  - HealthCheck register/check_all works
  - Metrics include expected fields
  - Singleton factory works

Usage:
    python scripts/test_observability.py
"""

import sys
import os
import json
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 60)
    print("OBSERVABILITY OFFLINE TEST (HARDEN-3)")
    print("=" * 60)

    # --- 1) Import ---
    print("\n[1] Import check...")
    from src.observability.logging_config import configure_logging, JSONFormatter
    from src.observability.health import HealthCheck, get_health_check
    print("    OK: All observability modules imported")

    # --- 2) JSON formatter ---
    print("\n[2] JSON formatter...")
    fmt = JSONFormatter()
    record = logging.LogRecord(
        name='test', level=logging.INFO, pathname='', lineno=0,
        msg='hello %s', args=('world',), exc_info=None,
    )
    output = fmt.format(record)
    parsed = json.loads(output)
    assert parsed['level'] == 'INFO'
    assert parsed['message'] == 'hello world'
    assert 'timestamp' in parsed
    assert parsed['logger'] == 'test'
    print(f"    OK: {output}")

    # --- 3) configure_logging (text) ---
    print("\n[3] configure_logging(text)...")
    configure_logging(log_format='text', log_level='WARNING')
    root = logging.getLogger()
    assert root.level == logging.WARNING
    print("    OK: text logging configured at WARNING")

    # Reset for remaining tests
    configure_logging(log_format='text', log_level='INFO')

    # --- 4) HealthCheck ---
    print("\n[4] HealthCheck...")
    hc = HealthCheck()

    def check_ok():
        return {'ok': True, 'detail': 'fine'}

    def check_fail():
        return {'ok': False, 'detail': 'broken'}

    hc.register('good', check_ok)
    result = hc.check_all()
    assert result['healthy'] is True
    assert result['checks']['good']['ok'] is True
    assert 'ms' in result['checks']['good']
    print(f"    OK: all healthy: {result}")

    hc.register('bad', check_fail)
    result2 = hc.check_all()
    assert result2['healthy'] is False
    assert result2['checks']['bad']['ok'] is False
    print(f"    OK: unhealthy detected: {result2}")

    # --- 5) Exception in check ---
    print("\n[5] Exception in health check...")

    def check_crash():
        raise RuntimeError("boom")

    hc.register('crasher', check_crash)
    result3 = hc.check_all()
    assert result3['healthy'] is False
    assert 'boom' in result3['checks']['crasher']['error']
    print(f"    OK: exception caught: {result3['checks']['crasher']}")

    # --- 6) Liveness ---
    print("\n[6] Liveness probe...")
    health = hc.get_health()
    assert health['status'] == 'ok'
    assert 'uptime_seconds' in health
    assert 'pid' in health
    print(f"    OK: {health}")

    # --- 7) Metrics ---
    print("\n[7] Metrics...")
    hc.increment_requests()
    hc.increment_requests()
    hc.increment_errors()
    metrics = hc.get_metrics()
    assert metrics['requests_total'] == 2
    assert metrics['errors_total'] == 1
    assert 'python_version' in metrics
    assert 'thread_count' in metrics
    print(f"    OK: {metrics}")

    # --- 8) Singleton ---
    print("\n[8] Singleton...")
    import src.observability.health as h_mod
    h_mod._instance = None  # Reset
    hc1 = get_health_check()
    hc2 = get_health_check()
    assert hc1 is hc2
    print("    OK: get_health_check() is singleton")
    h_mod._instance = None  # Clean up

    print("\n" + "=" * 60)
    print("ALL OBSERVABILITY TESTS PASSED (HARDEN-3)")
    print("=" * 60)


if __name__ == '__main__':
    main()
