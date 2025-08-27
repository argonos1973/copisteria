#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import json
from collections import defaultdict

sys.path.insert(0, '/var/www/html')
from db_utils import get_db_connection

REPORTS_DIR = '/var/www/html/reports'


def ensure_reports():
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
    except Exception:
        pass


def norm_text(s: str) -> str:
    if s is None:
        return ''
    t = s.lower().strip()
    # Sustituciones habituales
    subs = {
        'b/n': 'bn',
        'μ': 'u', 'µ': 'u', 'Μ': 'u',
        'á': 'a','é': 'e','í': 'i','ó': 'o','ú': 'u',
        'à': 'a','è': 'e','ì': 'i','ò': 'o','ù': 'u',
        'ç': 'c','ñ': 'n','·': '.',
    }
    for k, v in subs.items():
        t = t.replace(k, v)
    # Quitar signos y espacios
    quitar = set(" /-()[]{}.,;:¡!¿?\"'\t\n\r")
    t = ''.join(ch for ch in t if ch not in quitar)
    return t


essential_skip = {
    '',
    'seleccioneunproducto',
}


def main():
    ensure_reports()
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Mapa de nombres normalizados de productos -> lista de ids (para detectar ambigüedad)
        cur.execute("SELECT id, nombre FROM productos")
        prod_rows = cur.fetchall()
        name_map = defaultdict(list)
        for pid, nombre in prod_rows:
            name_map[norm_text(nombre)].append((pid, nombre))

        # Enlaces rotos: productoId no existe o vacío pero concepto utilizable
        cur.execute(
            """
            SELECT d.id_ticket, d.productoId, d.concepto
            FROM detalle_tickets d
            LEFT JOIN productos p ON p.id = d.productoId
            WHERE (d.productoId IS NOT NULL AND p.id IS NULL)
               OR (d.productoId IS NULL OR TRIM(CAST(d.productoId AS TEXT))='')
            """
        )
        broken = cur.fetchall()

        to_fix = []  # (new_productoId, id_ticket)
        to_fix_full = []  # dicts for preview
        ambiguous = []
        skipped = []

        for id_ticket, prod_id, concepto in broken:
            key = norm_text(concepto)
            if key in essential_skip:
                skipped.append({
                    'id_ticket': id_ticket,
                    'productoId_actual': prod_id,
                    'concepto': concepto,
                    'reason': 'concepto no utilizable'
                })
                continue
            candidates = name_map.get(key, [])
            if len(candidates) == 1:
                new_id, nombre = candidates[0]
                to_fix.append((new_id, id_ticket))
                to_fix_full.append({
                    'id_ticket': id_ticket,
                    'productoId_actual': prod_id,
                    'concepto': concepto,
                    'match_nombre': nombre,
                    'new_productoId': new_id
                })
            elif len(candidates) == 0:
                skipped.append({
                    'id_ticket': id_ticket,
                    'productoId_actual': prod_id,
                    'concepto': concepto,
                    'reason': 'sin coincidencias'
                })
            else:
                ambiguous.append({
                    'id_ticket': id_ticket,
                    'productoId_actual': prod_id,
                    'concepto': concepto,
                    'candidates': [{'id': pid, 'nombre': nomb} for pid, nomb in candidates]
                })

        # Preview
        with open(os.path.join(REPORTS_DIR, 'fixar_enlaces_rotos_preview.json'), 'w', encoding='utf-8') as f:
            json.dump({
                'total_rotos_detectados': len(broken),
                'soluciones_unicas': len(to_fix),
                'ambiguos': len(ambiguous),
                'omitidos': len(skipped),
                'muestra_soluciones': to_fix_full[:200],
                'muestra_ambiguos': ambiguous[:100],
                'muestra_omitidos': skipped[:100],
            }, f, ensure_ascii=False, indent=2)

        # Aplicar fixes solo para coincidencia única
        updated = 0
        if to_fix:
            # Actualizamos productoId y alineamos concepto al nombre del producto
            # Usamos subquery para concepto
            q = (
                "UPDATE detalle_tickets "
                "SET productoId = ?, "
                "    concepto = (SELECT nombre FROM productos WHERE id = ?) "
                "WHERE id_ticket = ?"
            )
            data = []
            for new_id, id_ticket in to_fix:
                data.append((new_id, new_id, id_ticket))
            cur.executemany(q, data)
            conn.commit()
            updated = conn.total_changes

        with open(os.path.join(REPORTS_DIR, 'fixar_enlaces_rotos_result.json'), 'w', encoding='utf-8') as f:
            json.dump({
                'updated_rows_total_changes': updated,
                'planned_unique_fixes': len(to_fix),
                'ambiguous': len(ambiguous),
                'skipped': len(skipped)
            }, f, ensure_ascii=False, indent=2)

        print(json.dumps({'updated': updated, 'planned_unique_fixes': len(to_fix)}))
        return 0
    except Exception as e:
        try:
            with open(os.path.join(REPORTS_DIR, 'fixar_enlaces_rotos_error.log'), 'a', encoding='utf-8') as f:
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
