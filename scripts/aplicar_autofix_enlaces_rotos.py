#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import json

sys.path.insert(0, '/var/www/html')
from db_utils import get_db_connection

REPORTS_DIR = '/var/www/html/reports'
SUG_FILE = os.path.join(REPORTS_DIR, 'sugerencias_enlaces_rotos.json')

THRESH_BEST = 0.85
THRESH_SECOND = 0.80


def ensure_reports():
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
    except Exception:
        pass


def main():
    ensure_reports()
    if not os.path.exists(SUG_FILE):
        print('[ERROR] No existe sugerencias_enlaces_rotros.json')
        return 1
    with open(SUG_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    sugerencias = data.get('muestra', [])

    # Filtrar según umbrales
    candidatos = []
    for s in sugerencias:
        best = s.get('best_match')
        cands = s.get('candidatos') or []
        if not best:
            continue
        score_best = best.get('score') or 0
        score_second = cands[1]['score'] if len(cands) > 1 else 0.0
        if score_best >= THRESH_BEST and score_second < THRESH_SECOND:
            candidatos.append({
                'id_ticket': s['id_ticket'],
                'new_productoId': best['productoId']
            })

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        updated = 0
        # Ejecutar updates uno a uno (pocos casos)
        for item in candidatos:
            new_id = item['new_productoId']
            id_ticket = item['id_ticket']
            # Actualizar productoId y alinear concepto al nombre del producto
            cur.execute(
                """
                UPDATE detalle_tickets
                   SET productoId = ?,
                       concepto = (SELECT nombre FROM productos WHERE id = ?)
                 WHERE id_ticket = ?
                """,
                (new_id, new_id, id_ticket)
            )
        conn.commit()
        updated = conn.total_changes
        out = {
            'planned': len(candidatos),
            'updated_rows_total_changes': updated
        }
        with open(os.path.join(REPORTS_DIR, 'aplicar_autofix_enlaces_rotos_result.json'), 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(json.dumps(out))
        return 0
    except Exception as e:
        try:
            with open(os.path.join(REPORTS_DIR, 'aplicar_autofix_enlaces_rotos_error.log'), 'a', encoding='utf-8') as f:
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
