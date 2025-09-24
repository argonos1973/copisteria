#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import json
from difflib import SequenceMatcher

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
    subs = {
        'b/n': 'bn',
        'μ': 'u', 'µ': 'u', 'Μ': 'u',
        'á': 'a','é': 'e','í': 'i','ó': 'o','ú': 'u',
        'à': 'a','è': 'e','ì': 'i','ò': 'o','ù': 'u',
        'ç': 'c','ñ': 'n','·': '.',
    }
    for k, v in subs.items():
        t = t.replace(k, v)
    quitar = set(" /-()[]{}.,;:¡!¿?\"'\t\n\r")
    t = ''.join(ch for ch in t if ch not in quitar)
    return t


def main():
    ensure_reports()
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Cargar productos
        cur.execute("SELECT id, nombre FROM productos")
        productos = cur.fetchall()
        prods = [{'id': r[0], 'nombre': r[1], 'norm': norm_text(r[1])} for r in productos]

        # Cargar rotos
        cur.execute(
            """
            SELECT d.id_ticket, d.productoId, d.concepto
            FROM detalle_tickets d
            LEFT JOIN productos p ON p.id = d.productoId
            WHERE (d.productoId IS NOT NULL AND p.id IS NULL)
               OR (d.productoId IS NULL OR TRIM(CAST(d.productoId AS TEXT))='')
            """
        )
        broken = [{'id_ticket': r[0], 'productoId_actual': r[1], 'concepto': r[2]} for r in cur.fetchall()]

        sugerencias = []
        for b in broken:
            concepto = b['concepto'] or ''
            norm_c = norm_text(concepto)
            if norm_c in {'', 'seleccioneunproducto'}:
                continue
            # Puntuar contra todos los productos
            scores = []
            for p in prods:
                # mezcla de similarity normal y similarity de formas normalizadas
                s1 = SequenceMatcher(None, concepto.lower().strip(), p['nombre'].lower().strip()).ratio()
                s2 = SequenceMatcher(None, norm_c, p['norm']).ratio()
                score = max(s1, s2)
                if score >= 0.6:  # umbral mínimo para listar
                    scores.append({'productoId': p['id'], 'nombre': p['nombre'], 'score': round(score, 4)})
            scores.sort(key=lambda x: x['score'], reverse=True)
            top = scores[:5]
            best = top[0] if top else None
            sugerencias.append({
                'id_ticket': b['id_ticket'],
                'productoId_actual': b['productoId_actual'],
                'concepto': concepto,
                'best_match': best,
                'candidatos': top
            })

        out = {
            'total_broken': len(broken),
            'sugerencias_generadas': len(sugerencias),
            'muestra': sugerencias[:200]
        }
        with open(os.path.join(REPORTS_DIR, 'sugerencias_enlaces_rotos.json'), 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(json.dumps({'suggestions': len(sugerencias)}))
        return 0
    except Exception as e:
        try:
            with open(os.path.join(REPORTS_DIR, 'sugerir_match_enlaces_rotos_error.log'), 'a', encoding='utf-8') as f:
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
