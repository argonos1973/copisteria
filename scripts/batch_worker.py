#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import socket
import sqlite3
import subprocess
import time
import json
import sys
import re
from datetime import datetime

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from logger_config import get_logger
from multiempresa_config import DB_USUARIOS_PATH
from notificaciones_utils import guardar_notificacion

logger = get_logger(__name__)


def _sanitize_params_for_job(job_code: str, params_obj):
    code = (job_code or '').strip()
    if code != 'batchTotalDia':
        return params_obj
    if not isinstance(params_obj, dict):
        return {}
    out = {}
    if params_obj.get('correo'):
        out['correo'] = str(params_obj.get('correo')).strip()
    if params_obj.get('db_path'):
        out['db_path'] = str(params_obj.get('db_path')).strip()
    return out


def _get_admin_emails(empresa_id: int):
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT DISTINCT u.email
            FROM usuarios u
            LEFT JOIN usuario_empresa ue ON ue.usuario_id = u.id AND ue.empresa_id = ?
            WHERE u.activo = 1
              AND u.email IS NOT NULL
              AND TRIM(u.email) != ''
              AND (
                    u.es_superadmin = 1
                    OR ue.es_admin_empresa = 1
                    OR ue.rol = 'admin'
                  )
            """,
            (empresa_id,),
        ).fetchall()
        try:
            return [str(r['email']).strip() for r in rows if r['email'] is not None and str(r['email']).strip()]
        finally:
            conn.close()
    except Exception:
        return []


def _tail_text_file(path: str, max_bytes: int = 80_000, max_lines: int = 80):
    try:
        if not path or not os.path.exists(path):
            return ''
        with open(path, 'rb') as f:
            try:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(0, size - max_bytes), os.SEEK_SET)
            except Exception:
                pass
            data = f.read()
        text = data.decode('utf-8', errors='ignore')
        lines = [ln.rstrip() for ln in text.splitlines()]
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
        return "\n".join(lines).strip()
    except Exception:
        return ''


def _fetch_run_log_lines(conn, run_id: int, limit: int = 60):
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT ts, level, message
            FROM batch_job_run_logs
            WHERE run_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (run_id, max(1, min(200, int(limit)))),
        ).fetchall()
        out = []
        for r in reversed(rows):
            out.append(f"[{r['ts']}] {r['level']}: {r['message']}")
        return out
    except Exception:
        return []


def _send_admin_email_for_run(conn, run: dict, empresa_codigo: str, status: str, duration_ms: int, error_summary: str, log_path: str):
    try:
        # No enviar emails para procesos de optimización de BD
        job_code = (run.get('job_code') or run.get('handler') or '').lower()
        handler = (run.get('handler') or '').lower()
        # Excluir cualquier proceso que contenga 'optim' o 'reindex'
        if any(x in job_code for x in ('optim', 'reindex', 'vacuum', 'analyze')):
            return
        if any(x in handler for x in ('optim', 'reindex', 'vacuum', 'analyze')):
            return
        
        empresa_id = int(run.get('empresa_id') or 0)
        if not empresa_id:
            return

        to_emails = _get_admin_emails(empresa_id)
        extra_to = (os.getenv('BATCH_NOTIFY_TO') or '').strip()
        if extra_to:
            to_emails.append(extra_to)

        to_emails = sorted(set([e for e in to_emails if e]))
        if not to_emails:
            return

        job_code = run.get('job_code') or run.get('handler') or 'batch'
        run_id = run.get('id')
        status_upper = str(status or '').upper()
        asunto = f"[{empresa_codigo}] Proceso {job_code} {status_upper} (run #{run_id})"

        lines = []
        lines.append(f"Empresa: {empresa_codigo} (ID {empresa_id})")
        lines.append(f"Proceso: {job_code}")
        lines.append(f"Run ID: {run_id}")
        lines.append(f"Estado: {status}")
        lines.append(f"Duración: {duration_ms} ms")
        if error_summary:
            lines.append(f"Error: {error_summary}")
        if log_path:
            lines.append(f"Log: {log_path}")
        lines.append("")

        db_logs = _fetch_run_log_lines(conn, int(run_id), limit=80)
        if db_logs:
            lines.append("LOG (DB)")
            lines.append("-")
            lines.extend(db_logs)
            lines.append("")

        tail = _tail_text_file(log_path, max_bytes=120_000, max_lines=120)
        if tail:
            lines.append("LOG (FICHERO - TAIL)")
            lines.append("-")
            lines.append(tail)
            lines.append("")

        cuerpo = "\n".join(lines).strip() + "\n"

        try:
            from email_utils import enviar_email_texto
            ok, msg = enviar_email_texto(to_emails, asunto, cuerpo)
        except Exception as e:
            ok, msg = False, str(e)

        if ok:
            _append_run_log(conn, int(run_id), 'info', f"Email de notificación enviado a admin: {', '.join(to_emails)}")
        else:
            _append_run_log(conn, int(run_id), 'warning', f"Error enviando email a admin: {msg}")
    except Exception:
        return


def _notify_run(run: dict, tipo: str, mensaje: str):
    """Notifica solo errores, no inicio/fin de procesos batch normales"""
    # Solo notificar errores, ignorar 'info' (inicio) y 'success' (finalizado OK)
    if tipo in ('info', 'success'):
        return
    try:
        db_path = None
        try:
            db_path = run.get('db_path')
        except Exception:
            db_path = None
        guardar_notificacion(mensaje, tipo=tipo, db_path=db_path)
    except Exception:
        pass


def _python_bin():
    venv_py = '/var/www/html/venv/bin/python3'
    return venv_py if os.path.exists(venv_py) else 'python3'


def _utc_now():
    return datetime.utcnow()


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _append_run_log(conn, run_id: int, level: str, message: str):
    conn.execute(
        "INSERT INTO batch_job_run_logs (run_id, level, message) VALUES (?, ?, ?)",
        (run_id, level, message),
    )


def _append_vencidas_updates_from_log(conn, run_id: int, log_path: str):
    try:
        if not log_path or not os.path.exists(log_path):
            return

        max_bytes = 200_000
        with open(log_path, 'rb') as f:
            try:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(0, size - max_bytes), os.SEEK_SET)
            except Exception:
                pass
            tail = f.read()

        text = tail.decode('utf-8', errors='ignore')
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        lines = lines[-800:]

        rx_v = re.compile(r"Factura\s+(?P<numero>[^\s]+)\s+\(ID:\s*(?P<id>\d+)\)\s+del\s+(?P<fecha>\d{4}-\d{2}-\d{2})\s+actualizada\s+a\s+estado\s+VENCIDA", re.IGNORECASE)
        rx_pdf = re.compile(r"Carta\s+de\s+reclamaci[óo]n\s+generada:\s+(?P<path>/[^\s]+\.pdf)", re.IGNORECASE)
        rx_email = re.compile(r"Enviando\s+email\s+a\s+(?P<to>[^\s]+)", re.IGNORECASE)
        rx_email_err = re.compile(r"Error\s+al\s+enviar\s+email\s+de\s+factura\s+(?P<num>[^\s]+)", re.IGNORECASE)

        matched_v = []
        matched_pdf = []
        matched_email = []
        matched_email_err = []
        for ln in lines:
            m = rx_v.search(ln)
            if m:
                matched_v.append(m)
                continue
            m = rx_pdf.search(ln)
            if m:
                matched_pdf.append(m)
                continue
            m = rx_email.search(ln)
            if m:
                matched_email.append(m)
                continue
            m = rx_email_err.search(ln)
            if m:
                matched_email_err.append(m)

        if matched_v:
            matched_v = matched_v[-50:]
            _append_run_log(conn, run_id, 'info', f"Facturas actualizadas a VENCIDA: {len(matched_v)}")
            for m in matched_v:
                msg = f"Factura actualizada a VENCIDA: numero={m.group('numero')} id={m.group('id')} fecha={m.group('fecha')}"
                _append_run_log(conn, run_id, 'info', msg)

        if matched_pdf:
            matched_pdf = matched_pdf[-50:]
            _append_run_log(conn, run_id, 'info', f"Cartas generadas: {len(matched_pdf)}")
            for m in matched_pdf:
                _append_run_log(conn, run_id, 'info', f"Carta generada: {m.group('path')}")

        if matched_email:
            matched_email = matched_email[-50:]
            _append_run_log(conn, run_id, 'info', f"Emails intentados: {len(matched_email)}")
            for m in matched_email:
                _append_run_log(conn, run_id, 'info', f"Enviando email a: {m.group('to')}")

        if matched_email_err:
            matched_email_err = matched_email_err[-50:]
            _append_run_log(conn, run_id, 'error', f"Errores email: {len(matched_email_err)}")
            for m in matched_email_err:
                _append_run_log(conn, run_id, 'error', f"Error al enviar email: factura={m.group('num')}")
    except Exception:
        return


def _claim_next_run(conn, worker_id: str):
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    row = cur.execute(
        """
        SELECT r.id, r.empresa_id, r.schedule_id, r.job_definition_id, r.params_snapshot,
               d.code as job_code, d.handler as handler, d.concurrency_mode,
               e.codigo as empresa_codigo, e.db_path as db_path
        FROM batch_job_runs r
        JOIN batch_job_definitions d ON d.id = r.job_definition_id
        JOIN empresas e ON e.id = r.empresa_id
        WHERE r.status = 'queued'
          AND d.active = 1
          AND (
                d.concurrency_mode != 'per_empresa_single'
                OR NOT EXISTS (
                    SELECT 1 FROM batch_job_runs rr
                    WHERE rr.empresa_id = r.empresa_id
                      AND rr.job_definition_id = r.job_definition_id
                      AND rr.status = 'running'
                )
          )
        ORDER BY r.id ASC
        LIMIT 1
        """
    ).fetchone()

    if not row:
        return None

    updated = cur.execute(
        """
        UPDATE batch_job_runs
        SET status = 'running', started_at = ?, worker_id = ?, host = ?
        WHERE id = ? AND status = 'queued'
        """,
        (_utc_now().isoformat(), worker_id, socket.gethostname(), row['id']),
    ).rowcount

    if updated != 1:
        return None

    return dict(row)


def _execute_handler(run: dict, log_path: str):
    handler = (run.get('handler') or '').strip()
    if handler.lower().endswith('.py'):
        handler = handler[:-3]

    handler_lc = handler.lower()
    if handler_lc == 'batchfacturasvencidas':
        handler = 'batchFacturasVencidas'
    elif handler_lc == 'batchpol':
        handler = 'batchPol'
    elif handler_lc == 'batchtotaldia':
        handler = 'batchTotalDia'
    elif handler_lc == 'batchscanfacturasrecibidas':
        handler = 'batchScanFacturasRecibidas'
    elif handler_lc == 'batchfacturasrecurrentes':
        handler = 'batchFacturasRecurrentes'
    elif handler_lc == 'batchoptimizar':
        handler = 'batchOptimizar'
    elif handler_lc == 'batchgenerico':
        handler = 'batchGenerico'

    py = _python_bin()
    if handler == 'batchFacturasVencidas':
        cmd = [py, '/var/www/html/batchFacturasVencidas.py']
    elif handler == 'batchPol':
        cmd = [py, '/var/www/html/batchPol.py']
    elif handler == 'batchTotalDia':
        cmd = [py, '/var/www/html/batchTotalDia.py']
    elif handler == 'batchScanFacturasRecibidas':
        cmd = [py, '/var/www/html/batchScanFacturasRecibidas.py']
    elif handler == 'batchFacturasRecurrentes':
        cmd = [py, '/var/www/html/scripts/batch_facturas_recurrentes.py']
    elif handler == 'batchOptimizar':
        cmd = [py, '/var/www/html/batchOptimizar.py']
    elif handler == 'batchGenerico':
        cmd = [py, '/var/www/html/batchGenerico.py']
    else:
        raise RuntimeError(f"Handler no soportado: {handler}")

    env = os.environ.copy()
    if run.get('db_path'):
        env['EMPRESA_DB_PATH'] = str(run['db_path'])

    if run.get('empresa_codigo'):
        env['EMPRESA_CODE'] = str(run['empresa_codigo'])
    if run.get('empresa_id') is not None:
        env['EMPRESA_ID'] = str(run['empresa_id'])

    if run.get('job_code'):
        env['BATCH_JOB_CODE'] = str(run['job_code'])

    params_snapshot = run.get('params_snapshot')
    # Si params vacío/nulo para batchTotalDia, recuperar del schedule asociado
    if not params_snapshot or params_snapshot.strip() in ('{}', 'null', ''):
        job_code_check = (run.get('job_code') or '').strip()
        schedule_id_check = run.get('schedule_id')
        if job_code_check == 'batchTotalDia' and schedule_id_check:
            try:
                conn_fallback = sqlite3.connect(DB_USUARIOS_PATH, timeout=10)
                conn_fallback.row_factory = sqlite3.Row
                row_fb = conn_fallback.execute(
                    "SELECT params_json FROM batch_job_schedules WHERE id=?",
                    (schedule_id_check,)
                ).fetchone()
                conn_fallback.close()
                if row_fb and row_fb['params_json']:
                    params_snapshot = row_fb['params_json']
            except Exception:
                pass
    if params_snapshot:
        try:
            params_obj = json.loads(str(params_snapshot))
            params_obj = _sanitize_params_for_job(run.get('job_code'), params_obj)
            env['BATCH_PARAMS_JSON'] = json.dumps(params_obj, ensure_ascii=False)
        except Exception:
            env['BATCH_PARAMS_JSON'] = str(params_snapshot)

    with open(log_path, 'wb') as f:
        proc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=env)
        return proc.returncode


def main():
    poll_seconds = int(os.getenv('BATCH_WORKER_POLL', '5'))
    worker_id = os.getenv('BATCH_WORKER_ID') or f"worker-{socket.gethostname()}-{os.getpid()}"
    
    # Solo ejecutar en el servidor .55 (hostname: sami-V-P8H67E)
    hostname = socket.gethostname()
    if hostname != 'sami-V-P8H67E':
        logger.info(f"[BATCH_WORKER] Worker iniciado en {hostname} - No ejecutará jobs (solo .55)")
        while True:
            time.sleep(60)  # Loop vacío, no ejecuta nada
    
    logger.info(f"[BATCH_WORKER] Worker iniciado en {hostname} - Ejecutando jobs")

    while True:
        run = None
        conn = None
        log_path = None
        try:
            conn = sqlite3.connect(DB_USUARIOS_PATH)
            conn.execute('PRAGMA busy_timeout = 5000')

            run = _claim_next_run(conn, worker_id)
            if not run:
                conn.commit()
                conn.close()
                time.sleep(poll_seconds)
                continue

            empresa_codigo = run.get('empresa_codigo') or 'empresa'
            base_dir = f"/var/www/html/logs/batch/{empresa_codigo}"
            _ensure_dir(base_dir)
            log_path = os.path.join(base_dir, f"run_{run['id']}.log")

            _append_run_log(conn, run['id'], 'info', f"Worker {worker_id} inicia {run.get('job_code')}")
            _notify_run(
                run,
                'info',
                f"Proceso {run.get('job_code')} ({empresa_codigo}) iniciado (run #{run.get('id')})",
            )
            if run.get('params_snapshot'):
                try:
                    params_obj = json.loads(run.get('params_snapshot'))
                    params_obj = _sanitize_params_for_job(run.get('job_code'), params_obj)
                    _append_run_log(conn, run['id'], 'info', f"Params: {json.dumps(params_obj, ensure_ascii=False)}")
                except Exception:
                    _append_run_log(conn, run['id'], 'info', f"Params(raw): {str(run.get('params_snapshot'))[:500]}")
            conn.execute("UPDATE batch_job_runs SET log_path = ? WHERE id = ?", (log_path, run['id']))
            conn.commit()

            start = _utc_now()
            rc = _execute_handler(run, log_path)
            end = _utc_now()
            duration_ms = int((end - start).total_seconds() * 1000)

            if run.get('handler') == 'batchFacturasVencidas':
                _append_vencidas_updates_from_log(conn, run['id'], log_path)

            if rc == 0:
                status = 'success'
                error_summary = None
                result_summary = f"{run.get('job_code')} finalizado"
                _append_run_log(conn, run['id'], 'success', f"Finalizado OK (rc=0) en {duration_ms}ms")
                _notify_run(
                    run,
                    'success',
                    f"Proceso {run.get('job_code')} ({empresa_codigo}) finalizado OK (run #{run.get('id')})",
                )
            else:
                status = 'error'
                error_summary = f"Proceso terminó con rc={rc}"
                result_summary = None
                _append_run_log(conn, run['id'], 'error', f"Finalizado ERROR (rc={rc}) en {duration_ms}ms")
                _notify_run(
                    run,
                    'error',
                    f"Proceso {run.get('job_code')} ({empresa_codigo}) ERROR rc={rc} (run #{run.get('id')})",
                )

            conn.execute(
                """
                UPDATE batch_job_runs
                SET status = ?, finished_at = ?, duration_ms = ?, error_summary = ?, result_summary = ?
                WHERE id = ?
                """,
                (status, end.isoformat(), duration_ms, error_summary, result_summary, run['id']),
            )
            conn.commit()

            try:
                _send_admin_email_for_run(conn, run, empresa_codigo, status, duration_ms, error_summary, log_path)
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

            conn.close()
            conn = None

        except Exception as e:
            logger.error(f"[BATCH_WORKER] Error: {e}", exc_info=True)
            try:
                if conn and run and run.get('id'):
                    _append_run_log(conn, run['id'], 'error', f"Excepción worker: {e}")
                    _notify_run(
                        run,
                        'error',
                        f"Proceso {run.get('job_code')} ({run.get('empresa_codigo') or 'empresa'}) ERROR: {str(e)[:200]} (run #{run.get('id')})",
                    )
                    conn.execute(
                        "UPDATE batch_job_runs SET status='error', finished_at=? , error_summary=? WHERE id=?",
                        (_utc_now().isoformat(), str(e)[:500], run['id']),
                    )
                    try:
                        empresa_codigo = run.get('empresa_codigo') or 'empresa'
                        _send_admin_email_for_run(conn, run, empresa_codigo, 'error', 0, str(e)[:500], log_path)
                    except Exception:
                        pass
                    conn.commit()
            except Exception:
                pass
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

        time.sleep(poll_seconds)


if __name__ == '__main__':
    raise SystemExit(main())
