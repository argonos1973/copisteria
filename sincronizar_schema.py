#!/usr/bin/env python3
"""
Script para sincronizar esquema de base de datos SQLite.
Compara la estructura de la BD origen (.18) con la destino (.55)
y añade tablas/columnas faltantes.

Uso: python3 sincronizar_schema.py <bd_destino>
"""

import sqlite3
import sys
import os
import subprocess
from datetime import datetime

# Configuración
SSH_KEY = "/home/sami/.ssh/id_rsa"
SRC_HOST = "192.168.1.18"
SRC_DB = "/var/www/html/db/aleph70.db"
LOG_FILE = "/var/www/html/logs/schema_sync.log"

def log(msg):
    """Log con timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + "\n")
    except:
        pass

def ejecutar_ssh(comando):
    """Ejecuta comando en servidor origen via SSH"""
    cmd = f'ssh -i {SSH_KEY} -o BatchMode=yes -o ConnectTimeout=10 sami@{SRC_HOST} "{comando}"'
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception as e:
        log(f"Error SSH: {e}")
        return None

def obtener_tablas_origen():
    """Obtiene lista de tablas del servidor origen"""
    resultado = ejecutar_ssh(f"sqlite3 '{SRC_DB}' \".tables\"")
    if resultado:
        # .tables devuelve tablas en múltiples columnas, las parseamos
        tablas = []
        for linea in resultado.split('\n'):
            tablas.extend(linea.split())
        return [t.strip() for t in tablas if t.strip()]
    return []

def obtener_schema_tabla_origen(tabla):
    """Obtiene el schema CREATE de una tabla del origen"""
    resultado = ejecutar_ssh(f"sqlite3 '{SRC_DB}' \".schema {tabla}\"")
    return resultado if resultado else None

def obtener_columnas_origen(tabla):
    """Obtiene columnas de una tabla del origen"""
    resultado = ejecutar_ssh(f"sqlite3 '{SRC_DB}' \"PRAGMA table_info({tabla});\"")
    if resultado:
        columnas = {}
        for linea in resultado.split('\n'):
            if linea.strip():
                partes = linea.split('|')
                if len(partes) >= 3:
                    col_name = partes[1]
                    col_type = partes[2]
                    col_notnull = partes[3] if len(partes) > 3 else '0'
                    col_default = partes[4] if len(partes) > 4 else None
                    columnas[col_name] = {
                        'type': col_type,
                        'notnull': col_notnull == '1',
                        'default': col_default
                    }
        return columnas
    return {}

def obtener_tablas_destino(conn):
    """Obtiene lista de tablas de la BD destino"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return [row[0] for row in cursor.fetchall()]

def obtener_columnas_destino(conn, tabla):
    """Obtiene columnas de una tabla destino"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({tabla})")
    columnas = {}
    for row in cursor.fetchall():
        columnas[row[1]] = {
            'type': row[2],
            'notnull': row[3] == 1,
            'default': row[4]
        }
    return columnas

def sincronizar_schema(db_destino):
    """Sincroniza el schema de la BD destino con el origen"""
    
    if not os.path.exists(db_destino):
        log(f"Error: No existe {db_destino}")
        return False
    
    log(f"=== Iniciando sincronización de schema ===")
    log(f"Origen: {SRC_HOST}:{SRC_DB}")
    log(f"Destino: {db_destino}")
    
    # Conectar a destino
    conn = sqlite3.connect(db_destino)
    cursor = conn.cursor()
    
    cambios = 0
    errores = 0
    
    try:
        # 1. Obtener tablas de ambos lados
        tablas_origen = obtener_tablas_origen()
        tablas_destino = obtener_tablas_destino(conn)
        
        if not tablas_origen:
            log("Error: No se pudieron obtener tablas del origen")
            return False
        
        log(f"Tablas origen: {len(tablas_origen)}")
        log(f"Tablas destino: {len(tablas_destino)}")
        
        # 2. Crear tablas faltantes
        tablas_faltantes = set(tablas_origen) - set(tablas_destino)
        for tabla in tablas_faltantes:
            log(f"  + Creando tabla faltante: {tabla}")
            schema = obtener_schema_tabla_origen(tabla)
            if schema:
                try:
                    # Puede haber múltiples statements (CREATE TABLE + CREATE INDEX)
                    for stmt in schema.split(';'):
                        stmt = stmt.strip()
                        if stmt:
                            cursor.execute(stmt)
                    cambios += 1
                    log(f"    ✓ Tabla {tabla} creada")
                except Exception as e:
                    log(f"    ✗ Error creando {tabla}: {e}")
                    errores += 1
        
        # 3. Sincronizar columnas de tablas existentes
        tablas_comunes = set(tablas_origen) & set(tablas_destino)
        for tabla in tablas_comunes:
            cols_origen = obtener_columnas_origen(tabla)
            cols_destino = obtener_columnas_destino(conn, tabla)
            
            if not cols_origen:
                continue
            
            # Columnas faltantes
            cols_faltantes = set(cols_origen.keys()) - set(cols_destino.keys())
            for col in cols_faltantes:
                info = cols_origen[col]
                col_type = info['type'] or 'TEXT'
                default = f"DEFAULT {info['default']}" if info['default'] else ""
                
                log(f"  + Añadiendo columna {tabla}.{col} ({col_type} {default})")
                try:
                    sql = f"ALTER TABLE {tabla} ADD COLUMN {col} {col_type} {default}"
                    cursor.execute(sql)
                    cambios += 1
                    log(f"    ✓ Columna añadida")
                except Exception as e:
                    log(f"    ✗ Error: {e}")
                    errores += 1
        
        # 4. Crear índices faltantes
        log("Verificando índices...")
        indices_origen = ejecutar_ssh(f"sqlite3 '{SRC_DB}' \"SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL;\"")
        if indices_origen:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indices_destino = set(row[0] for row in cursor.fetchall())
            
            for linea in indices_origen.split('\n'):
                if '|' in linea:
                    partes = linea.split('|', 1)
                    idx_name = partes[0]
                    idx_sql = partes[1] if len(partes) > 1 else None
                    
                    if idx_name not in indices_destino and idx_sql:
                        log(f"  + Creando índice: {idx_name}")
                        try:
                            cursor.execute(idx_sql)
                            cambios += 1
                        except Exception as e:
                            if "already exists" not in str(e).lower():
                                log(f"    ✗ Error: {e}")
                                errores += 1
        
        conn.commit()
        log(f"=== Sincronización completada: {cambios} cambios, {errores} errores ===")
        return errores == 0
        
    except Exception as e:
        log(f"Error general: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 sincronizar_schema.py <ruta_bd_destino>")
        sys.exit(1)
    
    exito = sincronizar_schema(sys.argv[1])
    sys.exit(0 if exito else 1)
