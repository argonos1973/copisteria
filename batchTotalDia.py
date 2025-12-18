#!/usr/bin/env python3

import json
import os
import sqlite3
from datetime import datetime

from batch_utils import get_batch_db_path, load_batch_params
from email_utils import enviar_email_con_adjuntos
from logger_config import get_logger
from notificaciones_utils import guardar_notificacion

logger = get_logger(__name__)

DB_NAME = get_batch_db_path()


def _connect(db_path: str):
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA busy_timeout = 5000')
    except Exception:
        pass
    return conn


def _has_column(conn: sqlite3.Connection, table: str, col: str) -> bool:
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        for r in rows:
            name = r['name'] if isinstance(r, sqlite3.Row) else r[1]
            if str(name).lower() == col.lower():
                return True
    except Exception:
        return False
    return False


def _fmt_euro(n) -> str:
    try:
        x = float(n or 0)
    except Exception:
        x = 0.0
    s = f"{x:,.2f}"
    return s.replace(',', 'X').replace('.', ',').replace('X', '.')


def _map_forma_pago(code: str) -> str:
    c = (code or '').strip().upper()
    if c in ('T', 'TPV'):
        return 'Tarjeta'
    if c in ('E', 'EF', 'EFE'):
        return 'Efectivo'
    if c in ('B', 'R', 'TR'):
        return 'Banco/Transferencia'
    if not c:
        return 'Sin especificar'
    return c


def _query_totals(conn: sqlite3.Connection, table: str, date_col: str, date_str: str):
    estado_col = _has_column(conn, table, 'estado')
    cobrado_col = _has_column(conn, table, 'cobrado')

    total_col = 'total' if _has_column(conn, table, 'total') else None
    bruto_col = 'importe_bruto' if _has_column(conn, table, 'importe_bruto') else None
    iva_col = 'importe_impuestos' if _has_column(conn, table, 'importe_impuestos') else None

    if not total_col:
        raise RuntimeError(f"Tabla {table} no tiene columna total")

    filters = [f"{date_col} = ?"]
    params = [date_str]

    if estado_col:
        filters.append("estado = 'C'")
    elif cobrado_col:
        filters.append("cobrado = 1")

    where_sql = " AND ".join(filters)

    select_parts = [f"COUNT(*) as cnt", f"COALESCE(SUM({total_col}), 0) as total"]
    if bruto_col:
        select_parts.append(f"COALESCE(SUM({bruto_col}), 0) as base")
    else:
        select_parts.append("0 as base")
    if iva_col:
        select_parts.append(f"COALESCE(SUM({iva_col}), 0) as iva")
    else:
        select_parts.append("0 as iva")

    row = conn.execute(
        f"SELECT {', '.join(select_parts)} FROM {table} WHERE {where_sql}",
        tuple(params),
    ).fetchone()

    cnt = int(row['cnt'] or 0)
    total = float(row['total'] or 0)
    base = float(row['base'] or 0)
    iva = float(row['iva'] or 0)

    forma_col = 'formaPago' if _has_column(conn, table, 'formaPago') else None
    by_forma = []
    if forma_col:
        rows = conn.execute(
            f"""
            SELECT {forma_col} as forma, COUNT(*) as cnt, COALESCE(SUM({total_col}), 0) as total
            FROM {table}
            WHERE {where_sql}
            GROUP BY {forma_col}
            ORDER BY total DESC
            """,
            tuple(params),
        ).fetchall()
        for r in rows:
            by_forma.append({
                'forma': r['forma'],
                'cnt': int(r['cnt'] or 0),
                'total': float(r['total'] or 0),
            })

    return {
        'count': cnt,
        'total': total,
        'base': base,
        'iva': iva,
        'by_forma': by_forma,
        'date_col': date_col,
    }


def main():
    global DB_NAME
    params = load_batch_params()
    DB_NAME = get_batch_db_path(params=params, default_path=DB_NAME)

    correo = (params.get('correo') or params.get('email') or params.get('to') or '').strip()
    if not correo:
        raise RuntimeError('Parámetro "correo" requerido')

    if not os.path.exists(DB_NAME):
        raise RuntimeError(f"No existe la BD: {DB_NAME}")

    empresa_code = (os.getenv('EMPRESA_CODE') or '').strip()
    today = datetime.now().strftime('%Y-%m-%d')

    conn = _connect(DB_NAME)
    try:
        fecha_col_factura = 'fechaCobro' if _has_column(conn, 'factura', 'fechaCobro') else 'fecha'
        fecha_col_tickets = 'fecha'

        fact = _query_totals(conn, 'factura', fecha_col_factura, today)
        tix = _query_totals(conn, 'tickets', fecha_col_tickets, today)

        total = fact['total'] + tix['total']
        base = fact['base'] + tix['base']
        iva = fact['iva'] + tix['iva']

        lines = []
        lines.append(f"Resumen de ventas del día {today}")
        if empresa_code:
            lines.append(f"Empresa: {empresa_code}")
        lines.append("")
        lines.append("TOTALES")
        lines.append("-")
        lines.append(f"Total: { _fmt_euro(total) } €")
        lines.append(f"Base:  { _fmt_euro(base) } €")
        lines.append(f"IVA:   { _fmt_euro(iva) } €")
        lines.append("")

        lines.append("DETALLE")
        lines.append("-")
        lines.append(f"Tickets ({tix['count']}): { _fmt_euro(tix['total']) } €")
        lines.append(f"Facturas ({fact['count']}): { _fmt_euro(fact['total']) } €")
        lines.append("")

        def _append_forma(title: str, data: dict):
            if not data.get('by_forma'):
                return
            lines.append(title)
            for it in data['by_forma']:
                fp = _map_forma_pago(it.get('forma'))
                lines.append(f"- {fp}: {it.get('cnt', 0)} -> { _fmt_euro(it.get('total')) } €")
            lines.append("")

        _append_forma("Por forma de pago (tickets):", tix)
        _append_forma("Por forma de pago (facturas):", fact)

        cuerpo = "\n".join(lines).strip() + "\n"

        subject_empresa = f" [{empresa_code}]" if empresa_code else ''
        asunto = f"Total del día {today}{subject_empresa}"

        ok, msg = enviar_email_con_adjuntos(correo, asunto, cuerpo, [], [])
        if not ok:
            raise RuntimeError(msg or 'Error enviando el correo')
        guardar_notificacion(f"📧 Total del día enviado a {correo}", tipo='success', db_path=DB_NAME)
        return 0
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as e:
        logger.error(f"[BATCH_TOTAL_DIA] Error: {e}", exc_info=True)
        try:
            guardar_notificacion(f"❌ Error enviando total del día: {e}", tipo='error', db_path=DB_NAME)
        except Exception:
            pass
        raise SystemExit(2)
