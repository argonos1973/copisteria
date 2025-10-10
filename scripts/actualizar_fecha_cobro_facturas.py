#!/usr/bin/env python3
"""
Script para actualizar el campo fechaCobro en facturas cobradas antiguas.

Este script:
1. Busca facturas con estado 'C' (Cobrada) sin fechaCobro
2. Establece fechaCobro = fecha (fecha de emisión) como aproximación
3. Muestra estadísticas de facturas actualizadas

Uso:
    python3 actualizar_fecha_cobro_facturas.py
"""

import sqlite3
import sys
import os

# Añadir el directorio padre al path para importar constantes
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constantes import DB_NAME


def actualizar_fecha_cobro():
    """Actualiza fechaCobro en facturas cobradas que no lo tienen"""
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Estadísticas antes de actualizar
        cursor.execute('''
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN formaPago = 'T' THEN 1 END) as tpv,
                   COUNT(CASE WHEN formaPago = 'E' THEN 1 END) as efectivo,
                   COUNT(CASE WHEN formaPago = 'B' THEN 1 END) as banco
            FROM factura
            WHERE estado = 'C'
            AND (fechaCobro IS NULL OR fechaCobro = '')
        ''')
        
        stats = cursor.fetchone()
        total_sin_fecha = stats[0]
        
        if total_sin_fecha == 0:
            print("✅ No hay facturas cobradas sin fechaCobro")
            return
        
        print(f"Facturas cobradas sin fechaCobro encontradas:")
        print(f"  Total: {stats[0]}")
        print(f"  TPV: {stats[1]}")
        print(f"  Efectivo: {stats[2]}")
        print(f"  Banco: {stats[3]}")
        
        # Actualizar facturas
        print(f"\nActualizando {total_sin_fecha} facturas...")
        cursor.execute('''
            UPDATE factura
            SET fechaCobro = fecha
            WHERE estado = 'C'
            AND (fechaCobro IS NULL OR fechaCobro = '')
        ''')
        
        filas_actualizadas = cursor.rowcount
        conn.commit()
        
        print(f"\n✅ {filas_actualizadas} facturas actualizadas correctamente")
        print(f"   fechaCobro establecido = fecha de emisión")
        
        # Verificar
        cursor.execute('''
            SELECT COUNT(*)
            FROM factura
            WHERE estado = 'C'
            AND (fechaCobro IS NULL OR fechaCobro = '')
        ''')
        
        pendientes = cursor.fetchone()[0]
        
        if pendientes == 0:
            print(f"\n✅ Todas las facturas cobradas tienen fechaCobro")
        else:
            print(f"\n⚠️ Facturas cobradas sin fechaCobro restantes: {pendientes}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    print("=" * 60)
    print("ACTUALIZAR FECHA DE COBRO EN FACTURAS")
    print("=" * 60)
    print()
    
    actualizar_fecha_cobro()
    
    print()
    print("=" * 60)
