#!/usr/bin/env python3
"""
Migración: Mover plantilla de tabla empresas a usuario_empresa

Objetivo:
- Agregar columna 'plantilla' a tabla usuario_empresa
- Copiar valor de empresas.plantilla a usuario_empresa.plantilla para cada usuario
- Mantener empresas.plantilla por compatibilidad (se puede eliminar después)

Fecha: 2025-11-06
"""

import sqlite3
import os
import sys

DB_PATH = '/var/www/html/db/usuarios_sistema.db'

def log(msg):
    """Simple print logger"""
    print(msg)

def migrar():
    """Ejecuta la migración"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        log("="*60)
        log("INICIANDO MIGRACIÓN: add_plantilla_to_usuario_empresa")
        log("="*60)
        
        # 1. Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(usuario_empresa)")
        columnas = [col[1] for col in cursor.fetchall()]
        
        if 'plantilla' in columnas:
            log("⚠️ La columna 'plantilla' ya existe en usuario_empresa")
            log("Saltando creación de columna...")
        else:
            # 2. Agregar columna plantilla a usuario_empresa
            log("📝 Agregando columna 'plantilla' a usuario_empresa...")
            cursor.execute("""
                ALTER TABLE usuario_empresa 
                ADD COLUMN plantilla TEXT DEFAULT 'dark'
            """)
            log("✅ Columna agregada correctamente")
        
        # 3. Copiar datos de empresas.plantilla a usuario_empresa.plantilla
        log("📋 Copiando datos de empresas.plantilla a usuario_empresa.plantilla...")
        
        cursor.execute("""
            UPDATE usuario_empresa
            SET plantilla = (
                SELECT e.plantilla 
                FROM empresas e 
                WHERE e.id = usuario_empresa.empresa_id
            )
            WHERE plantilla IS NULL OR plantilla = 'dark'
        """)
        
        filas_actualizadas = cursor.rowcount
        log(f"✅ {filas_actualizadas} filas actualizadas con plantilla de su empresa")
        
        # 4. Verificar datos
        cursor.execute("""
            SELECT u.username, e.nombre, ue.plantilla
            FROM usuario_empresa ue
            JOIN usuarios u ON ue.usuario_id = u.id
            JOIN empresas e ON ue.empresa_id = e.id
            ORDER BY e.nombre, u.username
        """)
        
        log("\n📊 Estado después de migración:")
        log("-" * 60)
        for row in cursor.fetchall():
            username, empresa, plantilla = row
            log(f"  Usuario: {username:20} | Empresa: {empresa:15} | Plantilla: {plantilla}")
        log("-" * 60)
        
        # 5. Commit
        conn.commit()
        log("\n✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        log("="*60)
        
        conn.close()
        return True
        
    except Exception as e:
        log(f"❌ Error en migración: {e}", exc_info=True)
        if conn:
            conn.rollback()
            conn.close()
        return False

def rollback():
    """Revierte la migración (elimina columna)"""
    try:
        log("⚠️ ROLLBACK no soportado directamente en SQLite")
        log("Para revertir, necesitas:")
        log("1. Hacer backup de la tabla")
        log("2. Recrear tabla sin la columna")
        log("3. Copiar datos del backup")
        return False
    except Exception as e:
        log(f"Error en rollback: {e}")
        return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Migración: plantilla a usuario_empresa')
    parser.add_argument('--rollback', action='store_true', help='Revertir migración')
    args = parser.parse_args()
    
    if args.rollback:
        success = rollback()
    else:
        success = migrar()
    
    sys.exit(0 if success else 1)
