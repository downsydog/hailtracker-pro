"""
Celery periodic task: radar pipeline watchdog.

Runs every 60 seconds and evaluates the SLA state of the radar pipeline.
If the state transitions to degraded or down, sends a deduped notification.
If it recovers to ok, sends a "recovered" notification (also deduped).

Notification channels:
  1. Webhook (WATCHDOG_WEBHOOK_URL)
  2. Log file (always, via structured logger)
  3. Redis pub/sub channel (radar:watchdog:events)

Redis keys:
    radar:watchdog:last_state       STRING  ok|degraded|down
    radar:watchdog:last_alert:down  STRING  '1', TTL 30 min (dedupe)
    radar:watchdog:last_alert:degraded  STRING  '1', TTL 30 min
    radar:watchdog:last_alert:recovered STRING  '1', TTL 30 min
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import redis as redis_lib
from celery import shared_task

logger = logging.getLogger(__name__)

# Redis key constants
_STATE_KEY = 'radar:watchdog:last_state'
_ALERT_PREFIX = 'radar:watchdog:last_alert:'
_EVENTS_CHANNEL = 'radar:watchdog:events'

# Dedupe TTL: 30 minutes (don't repeat same alert within this window)
_ALERT_DEDUPE_TTL = 1800


def _get_redis() -> redis_lib.Redis:
    url = os.environ.get(
        'REDIS_URL',
        os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    )
    return redis_lib.Redis.from_url(url, decode_responses=True)


@shared_task(
    name='src.workers.radar_watchdog.radar_watchdog',
    bind=True,
    max_retries=1,
    acks_late=True,
    time_limit=30,
    soft_time_limit=25,
)
def radar_watchdog(self):
    """
    Evaluate radar pipeline SLA state and send notifications on transitions.
    """
    r = _get_redis()

    try:
        return _run_watchdog(r)
    except Exception as exc:
        logger.warning("Watchdog failed: %s", exc)
        return {'error': str(exc)}


def _run_watchdog(r: redis_lib.Redis) -> dict:
    """Core watchdog logic."""
    from src.observability.health import compute_sla_state_from_redis

    # Compute current SLA state
    sla = compute_sla_state_from_redis(r)
    current_state = sla['state']

    # Read previous state
    previous_state = r.get(_STATE_KEY) or 'unknown'

    # Update stored state
    r.set(_STATE_KEY, current_state, ex=3600)

    # Update Prometheus gauge
    try:
        from src.observability.metrics import WATCHDOG_SLA_STATE
        state_map = {'ok': 2, 'degraded': 1, 'down': 0, 'unknown': 0}
        WATCHDOG_SLA_STATE.set(state_map.get(current_state, 0))
    except Exception:
        pass

    # Update storage + DB metrics (cheap, every 60s)
    try:
        from src.observability.metrics import (
            refresh_mrms_age_gauge,
            refresh_storage_gauges,
            refresh_db_table_gauges,
        )
        refresh_mrms_age_gauge(r)
        refresh_storage_gauges()
        refresh_db_table_gauges()
    except Exception:
        pass

    # --- Transition detection ---
    now_iso = datetime.now(timezone.utc).isoformat()

    if current_state in ('degraded', 'down') and previous_state != current_state:
        # State worsened or newly bad
        _send_alert(r, current_state, sla, now_iso)

    elif current_state == 'ok' and previous_state in ('degraded', 'down'):
        # Recovered
        _send_recovery(r, sla, now_iso)

    result = {
        'state': current_state,
        'previous_state': previous_state,
        'tick_age_seconds': sla.get('tick_age_seconds'),
        'mrms_age_seconds': sla.get('mrms_age_seconds'),
    }

    logger.info(
        "Watchdog: state=%s previous=%s tick_age=%s mrms_age=%s",
        current_state, previous_state,
        sla.get('tick_age_seconds'), sla.get('mrms_age_seconds'),
    )

    return result


def _send_alert(r: redis_lib.Redis, state: str, sla: dict, now_iso: str) -> None:
    """Send a degraded/down alert (deduped)."""
    dedupe_key = f'{_ALERT_PREFIX}{state}'
    if r.exists(dedupe_key):
        logger.debug("Watchdog alert for %s deduped (already sent recently)", state)
        return

    # Mark as sent
    r.set(dedupe_key, '1', ex=_ALERT_DEDUPE_TTL)

    message = {
        'type': 'alert',
        'state': state,
        'timestamp': now_iso,
        'tick_age_seconds': sla.get('tick_age_seconds'),
        'mrms_age_seconds': sla.get('mrms_age_seconds'),
        'message': f'Radar pipeline SLA state: {state.upper()}',
    }

    logger.warning(
        "WATCHDOG ALERT: pipeline %s | tick_age=%s mrms_age=%s",
        state.upper(), sla.get('tick_age_seconds'), sla.get('mrms_age_seconds'),
    )

    # Publish to Redis channel
    try:
        r.publish(_EVENTS_CHANNEL, json.dumps(message))
    except Exception:
        pass

    # Webhook notification
    _post_webhook(message)


def _send_recovery(r: redis_lib.Redis, sla: dict, now_iso: str) -> None:
    """Send a recovery notification (deduped)."""
    dedupe_key = f'{_ALERT_PREFIX}recovered'
    if r.exists(dedupe_key):
        return

    r.set(dedupe_key, '1', ex=_ALERT_DEDUPE_TTL)

    # Do NOT clear degraded/down dedupe keys on recovery — let them
    # expire naturally via TTL to prevent flap spam (rapid re-alerting
    # if the pipeline briefly dips and recovers).

    message = {
        'type': 'recovery',
        'state': 'ok',
        'timestamp': now_iso,
        'tick_age_seconds': sla.get('tick_age_seconds'),
        'mrms_age_seconds': sla.get('mrms_age_seconds'),
        'message': 'Radar pipeline recovered to OK',
    }

    logger.info(
        "WATCHDOG RECOVERY: pipeline ok | tick_age=%s mrms_age=%s",
        sla.get('tick_age_seconds'), sla.get('mrms_age_seconds'),
    )

    try:
        r.publish(_EVENTS_CHANNEL, json.dumps(message))
    except Exception:
        pass

    _post_webhook(message)


def _post_webhook(payload: dict) -> None:
    """POST to WATCHDOG_WEBHOOK_URL if configured."""
    url = os.environ.get('WATCHDOG_WEBHOOK_URL', '')
    if not url:
        return

    try:
        import requests
        resp = requests.post(
            url,
            json=payload,
            timeout=10,
            headers={'Content-Type': 'application/json'},
        )
        logger.info("Watchdog webhook → %d", resp.status_code)
    except Exception as e:
        logger.warning("Watchdog webhook failed: %s", e)
