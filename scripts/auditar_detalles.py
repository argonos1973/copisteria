#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sqlite3
import sys
import os

sys.path.insert(0, '/var/www/html')
from db_utils import get_db_connection

def table_exists(conn, name):
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None

def ensure_reports_dir():
    reports_dir = '/var/www/html/reports'
    try:
        os.makedirs(reports_dir, exist_ok=True)
    except Exception:
        pass
    return reports_dir


def write_json(path, payload):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        # Best effort logging
        try:
            with open('/var/www/html/reports/auditar_detalles_error.log', 'a', encoding='utf-8') as lf:
                lf.write(f"[WRITE_JSON_ERROR] {path}: {e}\n")
        except Exception:
            pass


def main():
    try:
        reports_dir = ensure_reports_dir()
        conn = get_db_connection()
        cur = conn.cursor()
        tablas = ['productos', 'detalle_tickets']
        existentes = {t: table_exists(conn, t) for t in tablas}
        write_json(os.path.join(reports_dir, 'auditar_detalles_tablas.json'), existentes)
        if not existentes.get('productos'):
            write_json(os.path.join(reports_dir, 'auditar_detalles_resumen.json'), {
                'error': 'Tabla productos no existe'
            })
            return 1
        if not existentes.get('detalle_tickets'):
            write_json(os.path.join(reports_dir, 'auditar_detalles_resumen.json'), {
                'warning': 'Tabla detalle_tickets no existe. No se puede auditar tickets.'
            })
            return 0

        # Totales
        cur.execute("SELECT COUNT(*) FROM detalle_tickets WHERE productoId IS NOT NULL")
        total_detalles = cur.fetchone()[0]

        # Enlaces rotos
        cur.execute("""
            SELECT COUNT(*)
            FROM detalle_tickets d
            LEFT JOIN productos p ON p.id = d.productoId
            WHERE d.productoId IS NOT NULL AND p.id IS NULL
        """)
        enlaces_rotos = cur.fetchone()[0]

        # Coincidencias exactas
        cur.execute("""
            SELECT COUNT(*)
            FROM detalle_tickets d
            JOIN productos p ON p.id = d.productoId
            WHERE COALESCE(TRIM(LOWER(d.concepto)),'') = COALESCE(TRIM(LOWER(p.nombre)),'')
        """)
        coincidencias = cur.fetchone()[0]

        # Mismatches
        cur.execute("""
            SELECT COUNT(*)
            FROM detalle_tickets d
            JOIN productos p ON p.id = d.productoId
            WHERE COALESCE(TRIM(LOWER(d.concepto)),'') <> COALESCE(TRIM(LOWER(p.nombre)),'')
        """)
        mismatches = cur.fetchone()[0]

        resumen = {
            'total_detalles_con_productoId': total_detalles,
            'enlaces_rotos': enlaces_rotos,
            'coincidencias_exactas': coincidencias,
            'mismatches_nombre': mismatches
        }
        write_json(os.path.join(reports_dir, 'auditar_detalles_resumen.json'), resumen)

        # Muestras
        def sample(q, params=(), limit=20):
            cur.execute(q + f" LIMIT {limit}", params)
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in rows]

        mismatches_rows = sample("""
            SELECT d.id_ticket, d.productoId, d.concepto AS concepto_detalle, p.nombre AS nombre_producto
            FROM detalle_tickets d
            JOIN productos p ON p.id = d.productoId
            WHERE COALESCE(TRIM(LOWER(d.concepto)),'') <> COALESCE(TRIM(LOWER(p.nombre)),'')
        """)
        write_json(os.path.join(reports_dir, 'auditar_detalles_mismatches.json'), mismatches_rows)

        rotos_rows = sample("""
            SELECT d.id_ticket, d.productoId, d.concepto AS concepto_detalle
            FROM detalle_tickets d
            LEFT JOIN productos p ON p.id = d.productoId
            WHERE d.productoId IS NOT NULL AND p.id IS NULL
        """)
        write_json(os.path.join(reports_dir, 'auditar_detalles_enlaces_rotos.json'), rotos_rows)

        # Top mismatches por producto (cuántos detalles por productoId no coinciden)
        cur.execute("""
            SELECT d.productoId,
                   p.nombre AS nombre_producto,
                   COUNT(*) AS cnt
            FROM detalle_tickets d
            JOIN productos p ON p.id = d.productoId
            WHERE COALESCE(TRIM(LOWER(d.concepto)),'') <> COALESCE(TRIM(LOWER(p.nombre)),'')
            GROUP BY d.productoId, p.nombre
            ORDER BY cnt DESC, d.productoId
        """)
        top_por_producto = [
            {
                'productoId': r[0],
                'nombre_producto': r[1],
                'mismatches': r[2]
            } for r in cur.fetchall()
        ]
        write_json(os.path.join(reports_dir, 'auditar_detalles_mismatch_top_producto.json'), top_por_producto)

        # Top pares (concepto_detalle vs nombre_producto) exactos (tras lower+trim)
        cur.execute("""
            SELECT TRIM(LOWER(d.concepto)) AS concepto_norm,
                   TRIM(LOWER(p.nombre))   AS nombre_norm,
                   COUNT(*) AS cnt
            FROM detalle_tickets d
            JOIN productos p ON p.id = d.productoId
            WHERE COALESCE(TRIM(LOWER(d.concepto)),'') <> COALESCE(TRIM(LOWER(p.nombre)),'')
            GROUP BY concepto_norm, nombre_norm
            ORDER BY cnt DESC
        """)
        top_parejas = [
            {
                'concepto_norm': r[0],
                'nombre_norm': r[1],
                'mismatches': r[2]
            } for r in cur.fetchall()
        ]
        write_json(os.path.join(reports_dir, 'auditar_detalles_mismatch_top_parejas.json'), top_parejas[:200])

        # Normalización agresiva para estimar qué se arregla con limpieza básica
        # Sustituir caracteres y símbolos comunes: espacios, '/', '-', '(', ')', '[', ']', ','
        # También normalizar variantes de mu: 'µ', 'Μ', 'u' antes de 'ms'
        def norm_agresiva(s: str) -> str:
            if s is None:
                return ''
            t = s.lower().strip()
            subs = {
                'b/n': 'bn',
                'μ': 'u',
                'µ': 'u',
                'Μ': 'u',
                'á':'a','é':'e','í':'i','ó':'o','ú':'u','à':'a','è':'e','ì':'i','ò':'o','ù':'u','ç':'c','ñ':'n','·':'.'
            }
            for k,v in subs.items():
                t = t.replace(k, v)
            quitar = set(" /-()[]{}.,;:¡!¿?\"'\t\n\r")
            t = ''.join(ch for ch in t if ch not in quitar)
            return t

        # Muestreo de qué porcentaje de mismatches pasarían a match con normalización agresiva
        cur.execute("""
            SELECT d.concepto, p.nombre
            FROM detalle_tickets d
            JOIN productos p ON p.id = d.productoId
            WHERE COALESCE(TRIM(LOWER(d.concepto)),'') <> COALESCE(TRIM(LOWER(p.nombre)),'')
            LIMIT 2000
        """)
        rows = cur.fetchall()
        resolubles = 0
        total = len(rows)
        muestras_norm = []
        for concepto, nombre in rows:
            if norm_agresiva(concepto) == norm_agresiva(nombre):
                resolubles += 1
                if len(muestras_norm) < 50:
                    muestras_norm.append({'concepto': concepto, 'nombre': nombre})
        write_json(os.path.join(reports_dir, 'auditar_detalles_mismatch_normalizable.json'), {
            'muestra_evaluada': total,
            'coinciden_con_normalizacion': resolubles,
            'porcentaje_resoluble_estimado': (resolubles/total*100.0) if total else 0.0,
            'muestras_que_se_resuelven': muestras_norm
        })
        return 0
    except Exception as e:
        try:
            with open('/var/www/html/reports/auditar_detalles_error.log', 'a', encoding='utf-8') as lf:
                lf.write(f"[ERROR] {e}\n")
        except Exception:
            pass
        return 1
    finally:
        try:
            conn.close()
        except:
            pass

if __name__ == '__main__':
    sys.exit(main())
