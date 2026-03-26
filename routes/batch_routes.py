# -*- coding: utf-8 -*-

import json
import sqlite3
from datetime import datetime

from flask import Blueprint, jsonify, request, session

from auth_middleware import require_admin
from logger_config import get_logger
from multiempresa_config import DB_USUARIOS_PATH

logger = get_logger(__name__)

batch_bp = Blueprint('batch', __name__, url_prefix='/api/batch')

_MISSING = object()  # sentinel para distinguir params ausentes de null explícito


def _sanitize_params(job_code: str, params):
    code = (job_code or '').strip()
    if params is None:
        return None
    if code == 'batchTotalDia':
        if not isinstance(params, dict):
            return {}
        out = {}
        if params.get('correo'):
            out['correo'] = str(params.get('correo')).strip()
        if params.get('db_path'):
            out['db_path'] = str(params.get('db_path')).strip()
        return out
    return params


def _get_conn():
    conn = sqlite3.connect(DB_USUARIOS_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _current_empresa_id():
    empresa_id = session.get('empresa_id')
    if not empresa_id:
        return None
    try:
        return int(empresa_id)
    except Exception:
        return None


def _ensure_admin_access_to_empresa(conn, empresa_id: int):
    if session.get('es_superadmin'):
        return True

    user_id = session.get('user_id')
    if not user_id:
        return False

    row = conn.execute(
        """
        SELECT es_admin_empresa
        FROM usuario_empresa
        WHERE usuario_id = ? AND empresa_id = ?
        """,
        (user_id, empresa_id),
    ).fetchone()

    return bool(row and (row['es_admin_empresa'] in (1, True, '1')))


def _ensure_batch_job_definitions(conn):
    """Inserta definiciones base si faltan (idempotente)."""
    items = [
        ('batchfacturasVencidas', 'Batch Facturas Vencidas (Emitidas)', 'batchFacturasVencidas', 900),
        ('batchPol', 'Batch POL (Proformas)', 'batchPol', 900),
        ('batchTotalDia', 'Total del día (Tickets + Facturas)', 'batchTotalDia', 300),
        ('batchScanFacturasRecibidas', 'Scanear Facturas Recibidas (OCR)', 'batchScanFacturasRecibidas', 1800),
        ('batchFacturasRecurrentes', 'Facturas Recurrentes (Proveedores)', 'batchFacturasRecurrentes', 600),
        ('batchOptimizar', 'Optimizar BD (VACUUM/ANALYZE)', 'batchOptimizar', 1800),
        ('batchReindex', 'Reindexar BD (REINDEX)', 'batchOptimizar', 1800),
    ]
    for code, name, handler, timeout_sec in items:
        conn.execute(
            """
            UPDATE batch_job_definitions
            SET name = ?,
                handler = ?,
                timeout_sec = ?,
                concurrency_mode = 'per_empresa_single',
                active = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE code = ?
            """,
            (name, handler, timeout_sec, code),
        )
        conn.execute(
            """
            INSERT INTO batch_job_definitions (code, name, handler, schema_json, timeout_sec, concurrency_mode, active)
            SELECT ?, ?, ?, NULL, ?, 'per_empresa_single', 1
            WHERE NOT EXISTS (SELECT 1 FROM batch_job_definitions WHERE code = ?)
            """,
            (code, name, handler, timeout_sec, code),
        )
    conn.commit()


def _strip_batch_prefix(name: str):
    if not name:
        return name
    n = str(name)
    return n[6:] if n.lower().startswith('batch ') else n


def _ensure_days_of_week_column(conn):
    """Añade la columna days_of_week si no existe (migración)."""
    try:
        conn.execute("SELECT days_of_week FROM batch_job_schedules LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE batch_job_schedules ADD COLUMN days_of_week TEXT DEFAULT '0,1,2,3,4,5,6'")
        conn.commit()
        logger.info("[BATCH] Añadida columna days_of_week a batch_job_schedules")


def _ensure_system_schedules(conn, empresa_id: int):
    """Garantiza que existan los schedules de sistema para la empresa (Reindex 02:00, Optimizar 03:00)."""
    system_jobs = [
        ('batchReindex', '0 2 * * *'),
        ('batchOptimizar', '0 3 * * *')
    ]

    for job_code, cron_expr in system_jobs:
        job_def = conn.execute("SELECT id FROM batch_job_definitions WHERE code = ?", (job_code,)).fetchone()
        if not job_def:
            continue

        exists = conn.execute(
            "SELECT 1 FROM batch_job_schedules WHERE empresa_id = ? AND job_definition_id = ?",
            (empresa_id, job_def['id'])
        ).fetchone()

        if not exists:
            conn.execute(
                """
                INSERT INTO batch_job_schedules
                (empresa_id, job_definition_id, enabled, cron_expr, created_by_usuario_id, updated_by_usuario_id)
                VALUES (?, ?, 1, ?, NULL, NULL)
                """,
                (empresa_id, job_def['id'], cron_expr)
            )
    conn.commit()


def _ensure_default_schedules(conn, empresa_id: int):
    exists_any = conn.execute(
        "SELECT 1 FROM batch_job_schedules WHERE empresa_id = ? LIMIT 1",
        (empresa_id,),
    ).fetchone()
    if exists_any:
        return

    defaults = [
        ('batchfacturasVencidas', '0 9 * * *', 0),
        ('batchPol', '*/15 * * * *', 0),
        ('batchTotalDia', '0 23 * * *', 0),
        ('batchScanFacturasRecibidas', '*/15 * * * *', 0),
    ]

    for job_code, cron_expr, enabled in defaults:
        job_def = conn.execute("SELECT id FROM batch_job_definitions WHERE code = ?", (job_code,)).fetchone()
        if not job_def:
            continue

        exists = conn.execute(
            "SELECT 1 FROM batch_job_schedules WHERE empresa_id = ? AND job_definition_id = ?",
            (empresa_id, job_def['id']),
        ).fetchone()
        if exists:
            continue

        conn.execute(
            """
            INSERT INTO batch_job_schedules
            (empresa_id, job_definition_id, enabled, cron_expr, created_by_usuario_id, updated_by_usuario_id)
            VALUES (?, ?, ?, ?, NULL, NULL)
            """,
            (empresa_id, job_def['id'], enabled, cron_expr),
        )

    conn.commit()


@batch_bp.route('/definitions', methods=['GET'])
@require_admin
def list_definitions():
    conn = _get_conn()
    try:
        _ensure_batch_job_definitions(conn)
        
        # Solo mostrar procesos que la empresa tiene asignados
        empresa_id = session.get('empresa_id')
        rows = conn.execute(
            """
            SELECT DISTINCT d.id, d.code, d.name, d.handler, d.schema_json, d.timeout_sec, d.concurrency_mode, d.active
            FROM batch_job_definitions d
            JOIN batch_job_schedules s ON s.job_definition_id = d.id
            WHERE d.active = 1
              AND s.empresa_id = ?
              AND d.code NOT IN ('batchOptimizar', 'batchReindex')
            ORDER BY d.name
            """,
            (empresa_id,)
        ).fetchall()

        out = []
        for r in rows:
            out.append({
                'id': r['id'],
                'code': r['code'],
                'name': _strip_batch_prefix(r['name']),
                'handler': r['handler'],
                'schema_json': r['schema_json'],
                'timeout_sec': r['timeout_sec'],
                'concurrency_mode': r['concurrency_mode'],
                'active': r['active'],
            })

        return jsonify({'success': True, 'definitions': out})
    finally:
        conn.close()


@batch_bp.route('/run', methods=['POST'])
@require_admin
def run_job_now():
    payload = request.json or {}
    job_code = (payload.get('job_code') or '').strip()
    params = payload.get('params')

    if not job_code:
        return jsonify({'success': False, 'error': 'job_code requerido'}), 400

    empresa_id = _current_empresa_id()
    if not empresa_id:
        return jsonify({'success': False, 'error': 'No hay empresa en sesión'}), 400

    conn = _get_conn()
    try:
        if not _ensure_admin_access_to_empresa(conn, empresa_id):
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

        job = conn.execute(
            "SELECT id FROM batch_job_definitions WHERE code = ? AND active = 1",
            (job_code,),
        ).fetchone()
        if not job:
            return jsonify({'success': False, 'error': 'Job no encontrado'}), 404

        params = _sanitize_params(job_code, params)
        if job_code == 'batchTotalDia':
            correo = (params or {}).get('correo') if isinstance(params, dict) else None
            if not correo or not str(correo).strip():
                return jsonify({'success': False, 'error': 'Parámetro "correo" requerido'}), 400

        params_snapshot = None
        if params is not None:
            params_snapshot = json.dumps(params, ensure_ascii=False)

        cur = conn.execute(
            """
            INSERT INTO batch_job_runs
            (empresa_id, schedule_id, job_definition_id, trigger, status, params_snapshot)
            VALUES (?, NULL, ?, 'manual', 'queued', ?)
            """,
            (empresa_id, job['id'], params_snapshot),
        )
        conn.commit()

        return jsonify({'success': True, 'run_id': cur.lastrowid})
    finally:
        conn.close()


@batch_bp.route('/schedules', methods=['GET'])
@require_admin
def list_schedules():
    conn = _get_conn()
    try:
        empresa_id = _current_empresa_id()
        if not empresa_id:
            return jsonify({'success': False, 'error': 'No hay empresa en sesión'}), 400

        if not _ensure_admin_access_to_empresa(conn, empresa_id):
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

        _ensure_batch_job_definitions(conn)
        _ensure_days_of_week_column(conn)
        _ensure_default_schedules(conn, empresa_id)
        _ensure_system_schedules(conn, empresa_id)

        rows = conn.execute(
            """
            SELECT s.id, s.empresa_id, s.enabled, s.cron_expr, s.timezone, s.params_json,
                   s.last_run_at, s.next_run_at, s.last_status, s.days_of_week,
                   d.code as job_code, d.name as job_name
            FROM batch_job_schedules s
            JOIN batch_job_definitions d ON d.id = s.job_definition_id
            WHERE s.empresa_id = ?
              AND d.code NOT IN ('batchOptimizar', 'batchReindex')
            ORDER BY d.name
            """,
            (empresa_id,),
        ).fetchall()

        out = []
        for r in rows:
            out.append({
                'id': r['id'],
                'empresa_id': r['empresa_id'],
                'enabled': r['enabled'],
                'cron_expr': r['cron_expr'],
                'timezone': r['timezone'],
                'params_json': r['params_json'],
                'last_run_at': r['last_run_at'],
                'next_run_at': r['next_run_at'],
                'last_status': r['last_status'],
                'days_of_week': r['days_of_week'] or '0,1,2,3,4,5,6',
                'job_code': r['job_code'],
                'job_name': _strip_batch_prefix(r['job_name']),
            })

        return jsonify({'success': True, 'schedules': out})
    finally:
        conn.close()


@batch_bp.route('/schedules', methods=['POST'])
@require_admin
def create_schedule():
    payload = request.json or {}
    job_code = (payload.get('job_code') or '').strip()
    cron_expr = (payload.get('cron_expr') or '').strip()
    enabled = 1 if payload.get('enabled', True) else 0
    timezone = payload.get('timezone')
    params = _sanitize_params(job_code, payload.get('params'))
    days_of_week = (payload.get('days_of_week') or '0,1,2,3,4,5,6').strip()

    if job_code in ('batchOptimizar', 'batchReindex'):
        return jsonify({'success': False, 'error': 'No se pueden crear procesos del sistema'}), 403

    if not job_code:
        return jsonify({'success': False, 'error': 'job_code requerido'}), 400
    if not cron_expr:
        return jsonify({'success': False, 'error': 'cron_expr requerido'}), 400

    empresa_id = _current_empresa_id()
    if not empresa_id:
        return jsonify({'success': False, 'error': 'No hay empresa en sesión'}), 400

    conn = _get_conn()
    try:
        if not _ensure_admin_access_to_empresa(conn, empresa_id):
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

        _ensure_days_of_week_column(conn)

        job = conn.execute(
            "SELECT id FROM batch_job_definitions WHERE code = ? AND active = 1",
            (job_code,),
        ).fetchone()
        if not job:
            return jsonify({'success': False, 'error': 'Job no encontrado'}), 404

        params_json = None
        if params is not None:
            params_json = json.dumps(params, ensure_ascii=False)

        user_id = session.get('user_id')

        cur = conn.execute(
            """
            INSERT INTO batch_job_schedules
            (empresa_id, job_definition_id, enabled, cron_expr, timezone, params_json, days_of_week, created_by_usuario_id, updated_by_usuario_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (empresa_id, job['id'], enabled, cron_expr, timezone, params_json, days_of_week, user_id, user_id),
        )
        conn.commit()

        return jsonify({'success': True, 'schedule_id': cur.lastrowid})
    finally:
        conn.close()


@batch_bp.route('/schedules/<int:schedule_id>', methods=['PUT'])
@require_admin
def update_schedule(schedule_id: int):
    payload = request.json or {}

    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT empresa_id FROM batch_job_schedules WHERE id = ?",
            (schedule_id,),
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'Schedule no encontrado'}), 404

        empresa_id = int(row['empresa_id'])
        if not _ensure_admin_access_to_empresa(conn, empresa_id):
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

        job_info = conn.execute(
            """
            SELECT d.code
            FROM batch_job_schedules s
            JOIN batch_job_definitions d ON d.id = s.job_definition_id
            WHERE s.id = ?
            """,
            (schedule_id,),
        ).fetchone()

        if job_info and job_info['code'] in ('batchOptimizar', 'batchReindex'):
            return jsonify({'success': False, 'error': 'No se pueden modificar procesos del sistema'}), 403

        fields = []
        values = []

        if 'enabled' in payload:
            fields.append('enabled = ?')
            values.append(1 if payload.get('enabled') else 0)

        if 'cron_expr' in payload:
            fields.append('cron_expr = ?')
            values.append((payload.get('cron_expr') or '').strip())

        if 'timezone' in payload:
            fields.append('timezone = ?')
            values.append(payload.get('timezone'))

        if 'params' in payload:
            job_code = None
            try:
                row = conn.execute(
                    """
                    SELECT d.code as job_code
                    FROM batch_job_schedules s
                    JOIN batch_job_definitions d ON d.id = s.job_definition_id
                    WHERE s.id = ?
                    """,
                    (schedule_id,),
                ).fetchone()
                job_code = row['job_code'] if row else None
            except Exception:
                job_code = None
            params_obj = _sanitize_params(job_code, payload.get('params'))
            fields.append('params_json = ?')
            values.append(json.dumps(params_obj, ensure_ascii=False) if params_obj is not None else None)

        if 'days_of_week' in payload:
            fields.append('days_of_week = ?')
            values.append((payload.get('days_of_week') or '0,1,2,3,4,5,6').strip())

        if not fields:
            return jsonify({'success': False, 'error': 'Sin cambios'}), 400

        user_id = session.get('user_id')
        fields.append('updated_by_usuario_id = ?')
        values.append(user_id)
        fields.append('updated_at = CURRENT_TIMESTAMP')

        values.append(schedule_id)
        conn.execute(
            f"UPDATE batch_job_schedules SET {', '.join(fields)} WHERE id = ?",
            tuple(values),
        )
        conn.commit()

        return jsonify({'success': True})
    finally:
        conn.close()


@batch_bp.route('/schedules/<int:schedule_id>/run', methods=['POST'])
@require_admin
def run_schedule_now(schedule_id: int):
    payload = request.json or {}
    conn = _get_conn()
    try:
        s = conn.execute(
            """
            SELECT s.empresa_id, s.job_definition_id, s.params_json
            FROM batch_job_schedules s
            WHERE s.id = ?
            """,
            (schedule_id,),
        ).fetchone()
        if not s:
            return jsonify({'success': False, 'error': 'Schedule no encontrado'}), 404

        empresa_id = int(s['empresa_id'])
        if not _ensure_admin_access_to_empresa(conn, empresa_id):
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

        # Sanitizar params para evitar que se hereden params antiguos (ej: batchTotalDia)
        params_snapshot = s['params_json']
        job_code = None
        try:
            job_row = conn.execute(
                """
                SELECT d.code as job_code
                FROM batch_job_definitions d
                WHERE d.id = ?
                """,
                (s['job_definition_id'],),
            ).fetchone()
            job_code = job_row['job_code'] if job_row else None
        except Exception:
            job_code = None

        incoming_params = payload.get('params') if 'params' in payload else _MISSING
        # Solo sobreescribir params del schedule si el frontend manda params con contenido real
        if incoming_params is not _MISSING and incoming_params:
            params_obj = _sanitize_params(job_code, incoming_params)
            params_snapshot = json.dumps(params_obj, ensure_ascii=False) if params_obj is not None else None
        else:
            # Usar params_json del schedule (sanitizando por si tiene campos viejos)
            if params_snapshot:
                try:
                    params_obj = _sanitize_params(job_code, json.loads(params_snapshot))
                    params_snapshot = json.dumps(params_obj, ensure_ascii=False) if params_obj is not None else None
                except Exception:
                    pass

        cur = conn.execute(
            """
            INSERT INTO batch_job_runs
            (empresa_id, schedule_id, job_definition_id, trigger, status, params_snapshot)
            VALUES (?, ?, ?, 'manual', 'queued', ?)
            """,
            (empresa_id, schedule_id, s['job_definition_id'], params_snapshot),
        )
        conn.commit()

        return jsonify({'success': True, 'run_id': cur.lastrowid})
    finally:
        conn.close()


@batch_bp.route('/runs', methods=['GET'])
@require_admin
def list_runs():
    conn = _get_conn()
    try:
        empresa_id = _current_empresa_id()
        if not empresa_id:
            return jsonify({'success': False, 'error': 'No hay empresa en sesión'}), 400

        if not _ensure_admin_access_to_empresa(conn, empresa_id):
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

        limit = request.args.get('limit', '50')
        try:
            limit = max(1, min(200, int(limit)))
        except Exception:
            limit = 50

        rows = conn.execute(
            """
            SELECT r.id, r.empresa_id, r.schedule_id, r.trigger, r.status, r.started_at, r.finished_at,
                   r.duration_ms, r.error_summary, r.result_summary, r.log_path,
                   d.code as job_code, d.name as job_name
            FROM batch_job_runs r
            JOIN batch_job_definitions d ON d.id = r.job_definition_id
            WHERE r.empresa_id = ?
            ORDER BY r.id DESC
            LIMIT ?
            """,
            (empresa_id, limit),
        ).fetchall()

        out = []
        for r in rows:
            out.append({
                'id': r['id'],
                'empresa_id': r['empresa_id'],
                'schedule_id': r['schedule_id'],
                'trigger': r['trigger'],
                'status': r['status'],
                'started_at': r['started_at'],
                'finished_at': r['finished_at'],
                'duration_ms': r['duration_ms'],
                'error_summary': r['error_summary'],
                'result_summary': r['result_summary'],
                'log_path': r['log_path'],
                'job_code': r['job_code'],
                'job_name': r['job_name'],
            })

        return jsonify({'success': True, 'runs': out})
    finally:
        conn.close()


@batch_bp.route('/runs/<int:run_id>', methods=['GET'])
@require_admin
def get_run(run_id: int):
    conn = _get_conn()
    try:
        row = conn.execute(
            """
            SELECT r.*, d.code as job_code, d.name as job_name
            FROM batch_job_runs r
            JOIN batch_job_definitions d ON d.id = r.job_definition_id
            WHERE r.id = ?
            """,
            (run_id,),
        ).fetchone()

        if not row:
            return jsonify({'success': False, 'error': 'Run no encontrado'}), 404

        empresa_id = int(row['empresa_id'])
        if not _ensure_admin_access_to_empresa(conn, empresa_id):
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

        out = dict(row)
        out['job_code'] = row['job_code']
        out['job_name'] = row['job_name']
        return jsonify({'success': True, 'run': out})
    finally:
        conn.close()


@batch_bp.route('/runs/<int:run_id>/logs', methods=['GET'])
@require_admin
def get_run_logs(run_id: int):
    conn = _get_conn()
    try:
        run = conn.execute("SELECT empresa_id FROM batch_job_runs WHERE id = ?", (run_id,)).fetchone()
        if not run:
            return jsonify({'success': False, 'error': 'Run no encontrado'}), 404

        empresa_id = int(run['empresa_id'])
        if not _ensure_admin_access_to_empresa(conn, empresa_id):
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

        limit = request.args.get('limit', '200')
        try:
            limit = max(1, min(2000, int(limit)))
        except Exception:
            limit = 200

        rows = conn.execute(
            """
            SELECT ts, level, message
            FROM batch_job_run_logs
            WHERE run_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (run_id, limit),
        ).fetchall()

        logs = []
        for r in reversed(rows):
            logs.append({'ts': r['ts'], 'level': r['level'], 'message': r['message']})

        return jsonify({'success': True, 'logs': logs})
    finally:
        conn.close()


@batch_bp.route('/runs/<int:run_id>/logs', methods=['DELETE'])
@require_admin
def delete_run_logs(run_id: int):
    conn = _get_conn()
    try:
        run = conn.execute(
            "SELECT empresa_id FROM batch_job_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if not run:
            return jsonify({'success': False, 'error': 'Run no encontrado'}), 404

        empresa_id = int(run['empresa_id'])
        if not _ensure_admin_access_to_empresa(conn, empresa_id):
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

        conn.execute("DELETE FROM batch_job_run_logs WHERE run_id = ?", (run_id,))
        conn.commit()
        return jsonify({'success': True})
    finally:
        conn.close()


@batch_bp.route('/logs', methods=['DELETE'])
@require_admin
def delete_all_logs_for_empresa():
    conn = _get_conn()
    try:
        empresa_id = _current_empresa_id()
        if not empresa_id:
            return jsonify({'success': False, 'error': 'No hay empresa en sesión'}), 400

        if not _ensure_admin_access_to_empresa(conn, empresa_id):
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

        run_rows = conn.execute(
            "SELECT id FROM batch_job_runs WHERE empresa_id = ?",
            (empresa_id,),
        ).fetchall()

        run_ids = [int(r['id']) for r in run_rows]
        for rid in run_ids:
            conn.execute("DELETE FROM batch_job_run_logs WHERE run_id = ?", (rid,))

        conn.commit()
        return jsonify({'success': True, 'runs': len(run_ids)})
    finally:
        conn.close()


@batch_bp.route('/runs', methods=['DELETE'])
@require_admin
def delete_all_runs_for_empresa():
    conn = _get_conn()
    try:
        empresa_id = _current_empresa_id()
        if not empresa_id:
            return jsonify({'success': False, 'error': 'No hay empresa en sesión'}), 400

        if not _ensure_admin_access_to_empresa(conn, empresa_id):
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

        run_rows = conn.execute(
            "SELECT id FROM batch_job_runs WHERE empresa_id = ?",
            (empresa_id,),
        ).fetchall()

        run_ids = [int(r['id']) for r in run_rows]
        for rid in run_ids:
            conn.execute("DELETE FROM batch_job_run_logs WHERE run_id = ?", (rid,))
            conn.execute("DELETE FROM batch_job_run_actions WHERE run_id = ?", (rid,))

        conn.execute("DELETE FROM batch_job_runs WHERE empresa_id = ?", (empresa_id,))
        conn.commit()
        return jsonify({'success': True, 'runs_deleted': len(run_ids)})
    finally:
        conn.close()

@batch_bp.route('/schedules/<int:schedule_id>', methods=['DELETE'])
@require_admin
def delete_schedule(schedule_id: int):
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT empresa_id FROM batch_job_schedules WHERE id = ?",
            (schedule_id,),
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'Schedule no encontrado'}), 404

        empresa_id = int(row['empresa_id'])
        if not _ensure_admin_access_to_empresa(conn, empresa_id):
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

        # Verificar si es proceso de sistema
        job_info = conn.execute(
            """
            SELECT d.code
            FROM batch_job_schedules s
            JOIN batch_job_definitions d ON d.id = s.job_definition_id
            WHERE s.id = ?
            """,
            (schedule_id,)
        ).fetchone()

        if job_info and job_info['code'] in ('batchOptimizar', 'batchReindex'):
            return jsonify({'success': False, 'error': 'No se pueden eliminar procesos del sistema'}), 403

        # Opcional: Verificar si hay runs en ejecución o algo así, pero por ahora permitimos borrar
        # Los runs históricos se quedan, pero el schedule desaparece.
        # Si quisieramos borrar runs asociados:
        # conn.execute("DELETE FROM batch_job_runs WHERE schedule_id = ?", (schedule_id,))

        conn.execute("DELETE FROM batch_job_schedules WHERE id = ?", (schedule_id,))
        conn.commit()

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"[BATCH] Error borrando schedule {schedule_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()
