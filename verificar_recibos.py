#!/usr/bin/env python3
"""
Verificar duplicados específicamente en recibos
"""
import sqlite3
import re
from collections import defaultdict

DB_PATH = '/var/www/html/db/aleph70.db'

def verificar_recibos_duplicados():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Obtener todos los recibos de 2025
    cursor.execute('''
        SELECT id, concepto, fecha_operacion, importe_eur 
        FROM gastos 
        WHERE concepto LIKE 'Recibo%'
        AND substr(fecha_operacion, 7, 4) = '2025'
        AND importe_eur < 0
        ORDER BY id
    ''')
    
    recibos = cursor.fetchall()
    print(f"Total recibos en 2025: {len(recibos)}\n")
    
    # Agrupar por fecha + importe exacto para encontrar duplicados
    por_fecha_importe = defaultdict(list)
    
    for row in recibos:
        clave = (row['fecha_operacion'], row['importe_eur'])
        por_fecha_importe[clave].append(dict(row))
    
    # Buscar duplicados exactos
    duplicados_exactos = []
    for clave, registros in por_fecha_importe.items():
        if len(registros) > 1:
            duplicados_exactos.append({'clave': clave, 'registros': registros})
    
    if duplicados_exactos:
        print("=" * 80)
        print(f"❌ DUPLICADOS EXACTOS ENCONTRADOS: {len(duplicados_exactos)} grupos")
        print("=" * 80)
        print()
        
        for i, dup in enumerate(duplicados_exactos, 1):
            registros = dup['registros']
            print(f"Grupo {i}: {len(registros)} registros")
            print(f"  Fecha: {dup['clave'][0]}")
            print(f"  Importe: {dup['clave'][1]}€")
            for reg in registros:
                print(f"    ID {reg['id']}: {reg['concepto'][:70]}")
            print()
    else:
        print("✅ NO SE ENCONTRARON DUPLICADOS EXACTOS EN RECIBOS")
    
    # Mostrar recibos de Aigües como ejemplo
    print("\n" + "=" * 80)
    print("EJEMPLO: Recibos Aigües de Barcelona 2025")
    print("=" * 80)
    
    cursor.execute('''
        SELECT id, concepto, fecha_operacion, ABS(importe_eur) as importe
        FROM gastos
        WHERE concepto LIKE '%Aigues%'
        AND substr(fecha_operacion, 7, 4) = '2025'
        AND importe_eur < 0
        ORDER BY fecha_operacion
    ''')
    
    aigues = cursor.fetchall()
    print(f"\nTotal recibos Aigües: {len(aigues)}")
    print()
    
    for row in aigues:
        print(f"  {row['fecha_operacion']}: {row['importe']:>8.2f}€ - ID {row['id']}")
        print(f"    {row['concepto'][:75]}")
    
    # Verificar Union Papelera
    print("\n" + "=" * 80)
    print("EJEMPLO: Recibos Union Papelera 2025")
    print("=" * 80)
    
    cursor.execute('''
        SELECT id, concepto, fecha_operacion, ABS(importe_eur) as importe
        FROM gastos
        WHERE concepto LIKE '%Union Papelera%'
        AND substr(fecha_operacion, 7, 4) = '2025'
        AND importe_eur < 0
        ORDER BY fecha_operacion
    ''')
    
    papelera = cursor.fetchall()
    print(f"\nTotal recibos Union Papelera: {len(papelera)}")
    print()
    
    for row in papelera:
        print(f"  {row['fecha_operacion']}: {row['importe']:>8.2f}€ - ID {row['id']}")
    
    conn.close()

if __name__ == '__main__':
    verificar_recibos_duplicados()
