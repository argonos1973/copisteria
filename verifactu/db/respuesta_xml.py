#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guardar la respuesta completa (XML) de la AEAT en la base de datos.

Si la columna ``respuesta_xml`` no existe todavía en la tabla
``registro_facturacion`` se añadirá al vuelo (tipo TEXT).
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Optional

from .utils import get_db_connection  # type: ignore

logger = logging.getLogger("verifactu")

_TABLE = "registro_facturacion"
_COLUMN = "respuesta_xml"


def _ensure_column(conn: sqlite3.Connection) -> None:
    """Asegura que la columna ``respuesta_xml`` existe en la tabla."""
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({_TABLE})")
    cols = [row[1] for row in cur.fetchall()]
    if _COLUMN not in cols:
        logger.info("Añadiendo columna %s a %s", _COLUMN, _TABLE)
        cur.execute(f"ALTER TABLE {_TABLE} ADD COLUMN {_COLUMN} TEXT")
        conn.commit()


def guardar_respuesta_xml(factura_id: int, xml_text: Optional[str]) -> bool:
    """Guarda *xml_text* en la fila con *factura_id*.

    Args:
        factura_id: id interno factura/ticket.
        xml_text: texto XML a almacenar.
    Returns:
        True si se actualizó alguna fila.
    """
    if not xml_text:
        return False

    conn: Optional[sqlite3.Connection] = None
    try:
        conn = get_db_connection()
        _ensure_column(conn)
        cur = conn.cursor()
        cur.execute(
            f"UPDATE {_TABLE} SET {_COLUMN} = ? WHERE factura_id = ?",
            (xml_text, factura_id),
        )
        conn.commit()
        if cur.rowcount:
            logger.info("Respuesta XML guardada para factura/ticket %s", factura_id)
            return True
        logger.warning("No existe registro_facturacion para id %s", factura_id)
        return False
    except Exception as exc:
        logger.error("Error guardando respuesta XML (%s): %s", factura_id, exc)
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()
