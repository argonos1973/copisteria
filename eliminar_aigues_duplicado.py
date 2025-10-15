#!/usr/bin/env python3
"""
Eliminar el duplicado específico del recibo de Aigües en Septiembre 2025
"""
import sqlite3

DB_PATH = '/var/www/html/db/aleph70.db'

def eliminar_duplicado():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print('=' * 80)
    print('ELIMINAR DUPLICADO DE RECIBO AIGÜES SEPTIEMBRE 2025')
    print('=' * 80)
    print()
    
    # Mostrar el registro antes de eliminar
    cursor.execute('SELECT id, concepto, fecha_operacion, importe_eur FROM gastos WHERE id = 18162')
    row = cursor.fetchone()
    
    if row:
        print('Registro a eliminar:')
        print(f'  ID: {row[0]}')
        print(f'  Fecha: {row[2]}')
        print(f'  Importe: {row[3]}€')
        print(f'  Concepto: {row[1][:80]}')
        print()
        
        # Eliminar
        cursor.execute('DELETE FROM gastos WHERE id = 18162')
        conn.commit()
        
        print(f'✅ {cursor.rowcount} registro eliminado correctamente')
    else:
        print('❌ No se encontró el registro ID 18162 (puede que ya esté eliminado)')
    
    # Verificar
    cursor.execute('''
        SELECT COUNT(*) 
        FROM gastos 
        WHERE concepto LIKE '%Aigues%'
        AND substr(fecha_operacion, 4, 2) = '09'
        AND substr(fecha_operacion, 7, 4) = '2025'
        AND importe_eur < 0
    ''')
    
    count = cursor.fetchone()[0]
    print(f'\nVerificación: {count} recibo(s) de Aigües en Septiembre 2025 ✅')
    
    conn.close()

if __name__ == '__main__':
    eliminar_duplicado()
