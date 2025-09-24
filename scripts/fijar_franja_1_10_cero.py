#!/usr/bin/env python3
"""
Fija la franja [1..10] con 0% de descuento para TODOS los productos.
- Si existe la franja (min_cantidad=1, max_cantidad=10), la actualiza a 0.
- Si no existe, la inserta.

Uso:
  python3 scripts/fijar_franja_1_10_cero.py            # aplica cambios
  python3 scripts/fijar_franja_1_10_cero.py --dry-run  # simula y muestra conteos
"""
from __future__ import annotations
import argparse
import sqlite3
from typing import Tuple

import sys
import os

# Asegurar que la raíz del proyecto esté en sys.path para imports directos
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from db_utils import get_db_connection
from productos import obtener_productos, ensure_tabla_descuentos_bandas


FR_MIN = 1
FR_MAX = 10
FR_DESC = 0.0


def fijar_franja_cero(dry_run: bool = False) -> Tuple[int, int, int]:
    """
    Retorna (total_productos, actualizadas, insertadas)
    """
    ensure_tabla_descuentos_bandas()
    productos = obtener_productos() or []

    actualizadas = 0
    insertadas = 0

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if not dry_run:
            conn.execute('BEGIN IMMEDIATE')

        for p in productos:
            pid = p.get('id') or p.get('producto_id')
            if not pid:
                continue

            # ¿Existe franja 1..10?
            cur.execute(
                """
                SELECT id FROM descuento_producto_franja
                WHERE producto_id = ? AND min_cantidad = ? AND max_cantidad = ?
                """,
                (pid, FR_MIN, FR_MAX),
            )
            row = cur.fetchone()
            if row:
                # Actualizar a 0%
                if dry_run:
                    actualizadas += 1
                else:
                    cur.execute(
                        """
                        UPDATE descuento_producto_franja
                        SET porcentaje_descuento = ?
                        WHERE id = ?
                        """,
                        (FR_DESC, row["id"] if isinstance(row, sqlite3.Row) else row[0]),
                    )
                    actualizadas += 1
            else:
                # Insertar franja 1..10 con 0%
                if dry_run:
                    insertadas += 1
                else:
                    cur.execute(
                        """
                        INSERT INTO descuento_producto_franja
                        (producto_id, min_cantidad, max_cantidad, porcentaje_descuento)
                        VALUES (?, ?, ?, ?)
                        """,
                        (pid, FR_MIN, FR_MAX, FR_DESC),
                    )
                    insertadas += 1

        if not dry_run:
            conn.commit()

        return (len(productos), actualizadas, insertadas)
    except Exception:
        if not dry_run:
            conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Fija franja 1..10 a 0% para todos los productos"
    )
    parser.add_argument("--dry-run", action="store_true", help="Simula sin escribir en BD")
    args = parser.parse_args()

    total, upd, ins = fijar_franja_cero(dry_run=args.dry_run)
    if args.dry_run:
        print(f"[DRY] Productos: {total} | actualizar: {upd} | insertar: {ins}")
    else:
        print(f"[OK] Procesados {total} productos. Actualizadas: {upd} | Insertadas: {ins}")


if __name__ == "__main__":
    main()
