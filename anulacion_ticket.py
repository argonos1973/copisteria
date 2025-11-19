#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Módulo de soporte para anular tickets (facturas simplificadas).

Al igual que con las facturas completas, la normativa indica que no se puede
eliminar un ticket ya emitido; debe emitirse un ticket rectificativo con
importes en negativo y referencia al original.

La lógica es muy similar a la utilizada para `anulacion.py` (facturas):
1. El ticket original pasa a estado 'A' (anulado).
2. Se genera un nuevo ticket rectificativo (estado 'RF', tipo 'R') con números
   negativos y sufijo "-R" en el número.
3. Se copian los detalles en negativo.
4. (Opcional) Integración VERI*FACTU si el módulo soporte provee función para
   tickets. Si no, solo se registra internamente.
"""
import traceback
from datetime import datetime

from flask import jsonify

from db_utils import get_db_connection


def _ensure_column(table: str, col_name: str, col_type: str = "TEXT") -> None:
    """Asegura que la columna existe en la tabla indicada."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        existing = [row[1] for row in cur.fetchall()]
        if col_name not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
            conn.commit()
    finally:
        if conn:
            conn.close()


def _copiar_detalles_negativos(cur, id_original: int, id_rect: int):
    """Copia detalles del ticket original invirtiendo cantidad, impuestos y total."""
    cur.execute(
        """SELECT concepto, descripcion, cantidad, precio, impuestos, total, productoId
           FROM detalle_tickets WHERE id_ticket = ?""",
        (id_original,),
    )
    for row in cur.fetchall():
        concepto, descripcion, cantidad, precio, impuestos, total, productoId = row
        cur.execute(
            """INSERT INTO detalle_tickets (
                    id_ticket, concepto, descripcion, cantidad, precio, impuestos, total, productoId)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                id_rect,
                concepto,
                descripcion,
                -cantidad if cantidad else None,
                precio,
                -impuestos if impuestos else None,
                -total if total else None,
                productoId,
            ),
        )


def anular_ticket(id_ticket: int):
    _ensure_column("tickets", "id_ticket_rectificado", "INTEGER")
    _ensure_column("tickets", "tipo", "TEXT")  # 'N' normal, 'R' rectificativo

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Obtener datos del ticket original
        cur.execute("SELECT * FROM tickets WHERE id = ?", (id_ticket,))
        row_orig = cur.fetchone()
        if not row_orig:
            return jsonify({"error": "Ticket no encontrado"}), 404

        colnames = [d[0] for d in cur.description]
        original = dict(zip(colnames, row_orig))

        if original.get("estado") == "A":
            return jsonify({"error": "El ticket ya está anulado"}), 400

        # Iniciar transacción
        cur.execute("BEGIN IMMEDIATE")

        # 1) Marcar original como anulada
        cur.execute("UPDATE tickets SET estado = 'A' WHERE id = ?", (id_ticket,))

        # 2) Calcular nuevo número y fecha
        numero_rect = f"{original['numero']}-R"
        hoy = datetime.now().strftime("%Y-%m-%d")
        now_iso = datetime.now().isoformat()

        # 3) Insertar ticket rectificativo
        cur.execute(
            """INSERT INTO tickets (
                    fecha, numero, importe_bruto, importe_impuestos, importe_cobrado, total,
                    timestamp, estado, formaPago, tipo, id_ticket_rectificado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                hoy,
                numero_rect,
                -float(original.get("importe_bruto") or 0),
                -float(original.get("importe_impuestos") or 0),
                0.0,
                -float(original.get("total") or 0),
                now_iso,
                "RF",
                original.get("formaPago", "E"),
                "R",
                id_ticket,
            ),
        )
        id_rect = cur.lastrowid

        # 4) Copiar detalles en negativo
        _copiar_detalles_negativos(cur, id_ticket, id_rect)

        conn.commit()

        # 5) VERI*FACTU (opcional)
        resultado_envio = None
        try:
            from verifactu.core import generar_datos_verifactu_para_ticket
            import re
            db_path = conn.execute('PRAGMA database_list').fetchone()[2]
            match = re.search(r'/db/([^/]+)/\1\.db', db_path)
            if match:
                empresa_codigo = match.group(1)
            else:
                import os
                db_name = os.path.basename(db_path)
                empresa_codigo = db_name.replace('.db', '')
            
            resultado_envio = generar_datos_verifactu_para_ticket(id_rect, empresa_codigo=empresa_codigo)
        except Exception:
            traceback.print_exc()

        return jsonify({
            "exito": True,
            "id_rectificativo": id_rect,
            "envio_aeat": resultado_envio,
        }), 200

    except Exception as exc:
        if conn:
            conn.rollback()
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500
    finally:
        if conn:
            conn.close()
