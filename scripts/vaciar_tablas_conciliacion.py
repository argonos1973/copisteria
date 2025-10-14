#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para vaciar las tablas de conciliación
Uso: python3 scripts/vaciar_tablas_conciliacion.py
"""

import sqlite3
import sys
import os

# Añadir directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_db_connection():
    """Conexión a la base de datos"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'aleph70.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def vaciar_tablas():
    """Vacía las tablas de conciliación"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("🗑️  Vaciando tablas de conciliación...")
        
        # 1. Contar registros antes de borrar
        cursor.execute("SELECT COUNT(*) as total FROM conciliacion_gastos")
        total_gastos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as total FROM conciliacion_documentos")
        total_documentos = cursor.fetchone()[0]
        
        print(f"   Registros en conciliacion_gastos: {total_gastos}")
        print(f"   Registros en conciliacion_documentos: {total_documentos}")
        
        if total_gastos == 0 and total_documentos == 0:
            print("✓ Las tablas ya están vacías")
            conn.close()
            return
        
        # 2. Vaciar tablas (sin confirmación)
        print("\n🔄 Borrando registros...")
        
        # Primero conciliacion_documentos (tiene FK a conciliacion_gastos)
        cursor.execute("DELETE FROM conciliacion_documentos")
        documentos_borrados = cursor.rowcount
        
        # Luego conciliacion_gastos
        cursor.execute("DELETE FROM conciliacion_gastos")
        gastos_borrados = cursor.rowcount
        
        # 4. Resetear autoincrement
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='conciliacion_gastos'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='conciliacion_documentos'")
        
        conn.commit()
        
        print(f"\n✅ Tablas vaciadas exitosamente:")
        print(f"   - conciliacion_gastos: {gastos_borrados} registros eliminados")
        print(f"   - conciliacion_documentos: {documentos_borrados} registros eliminados")
        print(f"   - IDs reiniciados a 1")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error al vaciar tablas: {e}")
        if conn:
            conn.rollback()
            conn.close()
        sys.exit(1)

if __name__ == '__main__':
    print("=" * 60)
    print("SCRIPT PARA VACIAR TABLAS DE CONCILIACIÓN")
    print("=" * 60)
    print("\n⚠️  ADVERTENCIA: Esta operación NO se puede deshacer\n")
    
    vaciar_tablas()
    
    print("\n" + "=" * 60)
