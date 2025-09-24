#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
import sys
import os
import json

sys.path.insert(0, '/var/www/html')
from db_utils import get_db_connection

REPORTS_DIR = '/var/www/html/reports'


def ensure_reports():
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
    except Exception:
        pass


def main():
    ensure_reports()
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Preview: cuántos se van a actualizar
        cur.execute(
            """
            SELECT COUNT(*)
            FROM detalle_tickets d
            WHERE d.productoId IS NOT NULL
              AND EXISTS (SELECT 1 FROM productos p WHERE p.id = d.productoId)
              AND COALESCE(TRIM(LOWER(d.concepto)),'') <> COALESCE(TRIM(LOWER((SELECT p2.nombre FROM productos p2 WHERE p2.id = d.productoId))),'')
            """
        )
        to_update = cur.fetchone()[0]

        # Hacer backup previo opcional en JSON (muestra limitada)
        cur.execute(
            """
            SELECT d.id_ticket, d.productoId, d.concepto AS concepto_old,
                   (SELECT p2.nombre FROM productos p2 WHERE p2.id = d.productoId) AS concepto_new
            FROM detalle_tickets d
            WHERE d.productoId IS NOT NULL
              AND EXISTS (SELECT 1 FROM productos p WHERE p.id = d.productoId)
              AND COALESCE(TRIM(LOWER(d.concepto)),'') <> COALESCE(TRIM(LOWER((SELECT p2.nombre FROM productos p2 WHERE p2.id = d.productoId))),'')
            LIMIT 200
            """
        )
        sample = [
            {
                'id_ticket': r[0],
                'productoId': r[1],
                'concepto_old': r[2],
                'concepto_new': r[3],
            }
            for r in cur.fetchall()
        ]
        with open(os.path.join(REPORTS_DIR, 'fixar_detalle_conceptos_preview.json'), 'w', encoding='utf-8') as f:
            json.dump({'to_update': to_update, 'sample': sample}, f, ensure_ascii=False, indent=2)

        # Ejecutar UPDATE
        cur.execute(
            """
            UPDATE detalle_tickets
               SET concepto = (
                   SELECT p.nombre FROM productos p WHERE p.id = detalle_tickets.productoId
               )
             WHERE productoId IS NOT NULL
               AND EXISTS (SELECT 1 FROM productos p WHERE p.id = detalle_tickets.productoId)
               AND COALESCE(TRIM(LOWER(concepto)),'') <> COALESCE(TRIM(LOWER((SELECT nombre FROM productos p2 WHERE p2.id = detalle_tickets.productoId))),'')
            """
        )
        conn.commit()
        updated = conn.total_changes
        with open(os.path.join(REPORTS_DIR, 'fixar_detalle_conceptos_result.json'), 'w', encoding='utf-8') as f:
            json.dump({'updated_rows_total_changes': updated, 'planned_to_update': to_update}, f, ensure_ascii=False, indent=2)
        print(json.dumps({'updated': updated, 'planned': to_update}))
        return 0
    except Exception as e:
        try:
            with open(os.path.join(REPORTS_DIR, 'fixar_detalle_conceptos_error.log'), 'a', encoding='utf-8') as f:
                f.write(str(e) + "\n")
        except Exception:
            pass
        print('[ERROR]', str(e))
        return 1
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    sys.exit(main())
