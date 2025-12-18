#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Optional

from logger_config import get_logger
from multiempresa_config import DB_USUARIOS_PATH

logger = get_logger(__name__)


def _now():
    return datetime.now()


def _parse_cron_simple(cron_expr: str):
    """Parsea un subconjunto simple de cron (min hora dom mes dow).

    Formatos soportados:
    - */N * * * *
    - */N H1-H2 * * *
    - M * * * *
    - M H * * *
    """
    if not cron_expr:
        return None

    expr = cron_expr.strip()

    m = re.fullmatch(r"\*/(\d+) \* \* \* \*", expr)
    if m:
        return {'kind': 'interval', 'minutes': max(1, int(m.group(1))), 'hour_range': None}

    m = re.fullmatch(r"\*/(\d+) (\d{1,2})-(\d{1,2}) \* \* \*", expr)
    if m:
        return {
            'kind': 'interval',
            'minutes': max(1, int(m.group(1))),
            'hour_range': (int(m.group(2)), int(m.group(3)))
        }

    m = re.fullmatch(r"(\d{1,2}) \* \* \* \*", expr)
    if m:
        minute = int(m.group(1))
        if 0 <= minute <= 59:
            return {'kind': 'hourly', 'minute': minute}

    m = re.fullmatch(r"(\d{1,2}) (\d{1,2}) \* \* \*", expr)
    if m:
        minute = int(m.group(1))
        hour = int(m.group(2))
        if 0 <= minute <= 59 and 0 <= hour <= 23:
            return {'kind': 'daily', 'hour': hour, 'minute': minute}

    return None


def _ceil_to_next_multiple(value: int, step: int):
    if step <= 1:
        return value
    return ((value + step - 1) // step) * step


def _next_run_from_cron(cron_expr: str, last: Optional[datetime]):
    cron_expr = (cron_expr or '').strip()
    now = _now()

    parsed = _parse_cron_simple(cron_expr)
    if not parsed:
        return (last or now) + timedelta(minutes=60)

    if parsed['kind'] == 'daily':
        hour = parsed['hour']
        minute = parsed['minute']
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate > now:
            return candidate
        return candidate + timedelta(days=1)

    if parsed['kind'] == 'hourly':
        minute = parsed['minute']
        candidate = now.replace(minute=minute, second=0, microsecond=0)
        if candidate > now:
            return candidate
        return candidate + timedelta(hours=1)

    if parsed['kind'] == 'interval':
        step = parsed['minutes']
        hour_range = parsed.get('hour_range')

        base = (now + timedelta(seconds=1))
        base = base.replace(second=0, microsecond=0)

        # Alinear al siguiente múltiplo del step desde medianoche
        minutes_since_midnight = base.hour * 60 + base.minute
        next_minutes = _ceil_to_next_multiple(minutes_since_midnight, step)
        candidate = base.replace(hour=0, minute=0) + timedelta(minutes=next_minutes)

        if hour_range:
            start_h, end_h = hour_range
            start_h = max(0, min(23, start_h))
            end_h = max(0, min(23, end_h))
            if end_h < start_h:
                start_h, end_h = end_h, start_h

            # Si cae fuera de la franja, saltar al inicio de la próxima franja
            if candidate.hour < start_h:
                candidate = candidate.replace(hour=start_h, minute=0)
                minutes_since_midnight = candidate.hour * 60 + candidate.minute
                next_minutes = _ceil_to_next_multiple(minutes_since_midnight, step)
                candidate = candidate.replace(hour=0, minute=0) + timedelta(minutes=next_minutes)
            elif candidate.hour > end_h:
                # siguiente día al inicio de la franja
                candidate = (candidate + timedelta(days=1)).replace(hour=start_h, minute=0, second=0, microsecond=0)
                minutes_since_midnight = candidate.hour * 60 + candidate.minute
                next_minutes = _ceil_to_next_multiple(minutes_since_midnight, step)
                candidate = candidate.replace(hour=0, minute=0) + timedelta(minutes=next_minutes)

            # Asegurar que seguimos dentro de la franja (puede saltar al final del día)
            if candidate.hour > end_h:
                candidate = (candidate + timedelta(days=1)).replace(hour=start_h, minute=0, second=0, microsecond=0)

        return candidate

    return (last or now) + timedelta(minutes=60)


def main():
    poll_seconds = int(os.getenv('BATCH_SCHEDULER_POLL', '30'))
    max_catchup_seconds = int(os.getenv('BATCH_MAX_CATCHUP_SECONDS', '120'))

    while True:
        try:
            conn = sqlite3.connect(DB_USUARIOS_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            schedules = cur.execute(
                """
                SELECT s.id, s.empresa_id, s.job_definition_id, s.enabled, s.cron_expr, s.params_json,
                       s.next_run_at, s.last_run_at
                FROM batch_job_schedules s
                WHERE s.enabled = 1
                """
            ).fetchall()

            now = _now()

            for s in schedules:
                next_run_at = None
                if s['next_run_at']:
                    try:
                        next_run_at = datetime.fromisoformat(str(s['next_run_at']))
                    except Exception:
                        next_run_at = None

                last_run_at = None
                if s['last_run_at']:
                    try:
                        last_run_at = datetime.fromisoformat(str(s['last_run_at']))
                    except Exception:
                        last_run_at = None

                if not next_run_at:
                    nxt = _next_run_from_cron(s['cron_expr'], last_run_at)
                    cur.execute(
                        """
                        UPDATE batch_job_schedules
                        SET next_run_at = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (nxt.isoformat(), s['id']),
                    )
                    continue

                if next_run_at and next_run_at > now:
                    continue

                if next_run_at and (now - next_run_at).total_seconds() > max_catchup_seconds:
                    nxt = _next_run_from_cron(s['cron_expr'], last_run_at)
                    cur.execute(
                        """
                        UPDATE batch_job_schedules
                        SET next_run_at = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (nxt.isoformat(), s['id']),
                    )
                    continue

                cur.execute(
                    """
                    INSERT INTO batch_job_runs (empresa_id, schedule_id, job_definition_id, trigger, status, params_snapshot)
                    VALUES (?, ?, ?, 'schedule', 'queued', ?)
                    """,
                    (s['empresa_id'], s['id'], s['job_definition_id'], s['params_json']),
                )

                nxt = _next_run_from_cron(s['cron_expr'], last_run_at)
                cur.execute(
                    """
                    UPDATE batch_job_schedules
                    SET last_run_at = ?, next_run_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (now.isoformat(), nxt.isoformat(), s['id']),
                )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"[BATCH_SCHEDULER] Error: {e}", exc_info=True)
            try:
                conn.close()
            except Exception:
                pass

        time.sleep(poll_seconds)


if __name__ == '__main__':
    raise SystemExit(main())
