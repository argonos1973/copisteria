#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import sqlite3
from datetime import datetime

from batch_utils import get_batch_db_path, load_batch_params
from logger_config import get_logger
from notificaciones_utils import guardar_notificacion

logger = get_logger(__name__)

DB_NAME = get_batch_db_path()


def _notify(message: str, tipo: str = 'info'):
    try:
        guardar_notificacion(message, tipo=tipo, db_path=DB_NAME)
    except Exception:
        pass


def _run_sql(conn: sqlite3.Connection, sql: str):
    logger.info("Ejecutando SQL: %s", sql)
    conn.execute(sql)


def ejecutar_optimizacion(modo: str):
    """modo: 'optimizar' o 'reindex'"""

    global DB_NAME
    params = load_batch_params()
    DB_NAME = get_batch_db_path(params=params, default_path=DB_NAME)

    if not os.path.exists(DB_NAME):
        raise RuntimeError(f"No existe la BD: {DB_NAME}")

    # Permitir forzar modo por params
    modo_param = (params.get('modo') or params.get('accion') or '').strip().lower()
    if modo_param in ('optimizar', 'reindex'):
        modo = modo_param

    logger.info("[BATCH_OPTIMIZAR] Inicio modo=%s db=%s", modo, DB_NAME)

    start = datetime.now()

    # IMPORTANTE: VACUUM no puede ejecutarse dentro de una transacción
    conn = sqlite3.connect(DB_NAME)
    try:
        conn.execute('PRAGMA busy_timeout = 5000')

        if modo == 'reindex':
            # _notify('🧹 Reindexar BD: inicio', tipo='info')  # Notificación desactivada
            _run_sql(conn, 'REINDEX')
            _run_sql(conn, 'ANALYZE')
            try:
                _run_sql(conn, 'PRAGMA optimize')
            except Exception:
                pass
            # _notify('🧹 Reindexar BD: finalizado', tipo='success')  # Notificación desactivada
        else:
            # _notify('🧽 Optimizar BD: inicio', tipo='info')  # Notificación desactivada
            # ANALYZE recalcula estadísticas
            _run_sql(conn, 'ANALYZE')
            # PRAGMA optimize (si existe)
            try:
                _run_sql(conn, 'PRAGMA optimize')
            except Exception:
                pass
            # VACUUM compacta
            _run_sql(conn, 'VACUUM')
            # _notify('🧽 Optimizar BD: finalizado', tipo='success')  # Notificación desactivada

    finally:
        try:
            conn.close()
        except Exception:
            pass

    elapsed = (datetime.now() - start).total_seconds()
    logger.info("[BATCH_OPTIMIZAR] Fin modo=%s en %.2fs", modo, elapsed)


def main():
    # El worker pasa BATCH_JOB_CODE para distinguir definiciones sin params
    job_code = (os.getenv('BATCH_JOB_CODE') or '').strip().lower()
    modo = 'optimizar'
    if job_code == 'batchreindex':
        modo = 'reindex'

    try:
        ejecutar_optimizacion(modo)
        return 0
    except Exception as e:
        logger.error("[BATCH_OPTIMIZAR] Error: %s", e, exc_info=True)
        _notify(f'❌ Error en proceso BD ({modo}): {e}', tipo='error')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
