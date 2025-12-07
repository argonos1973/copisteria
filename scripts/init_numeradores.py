#!/usr/bin/env python3
import os
import sqlite3
from datetime import datetime

DB_ROOT = '/var/www/html/db'
TIPOS_DOC = ['F', 'P', 'T', 'O', 'R']
ANIO_ACTUAL = datetime.now().year

def init_numeradores():
    print(f"Iniciando revisión de numeradores en {DB_ROOT} para el año {ANIO_ACTUAL}")
    
    if not os.path.exists(DB_ROOT):
        print(f"Directorio {DB_ROOT} no existe.")
        return

    # Recorrer subdirectorios (empresas)
    for nombre_empresa in os.listdir(DB_ROOT):
        empresa_dir = os.path.join(DB_ROOT, nombre_empresa)
        
        if not os.path.isdir(empresa_dir):
            continue
            
        # Buscar archivo .db
        db_file = None
        for f in os.listdir(empresa_dir):
            if f.endswith('.db') and not f.endswith('plantilla.db'):
                db_file = os.path.join(empresa_dir, f)
                break
        
        if not db_file:
            print(f"Saltando {nombre_empresa}: No se encontró .db")
            continue
            
        print(f"Procesando BD: {db_file}")
        
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # 1. Asegurar tabla
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS "numerador" (
                    "id"    INTEGER PRIMARY KEY AUTOINCREMENT,
                    "tipo"  TEXT,
                    "numerador"     INTEGER,
                    "ejercicio"     INTEGER,
                    UNIQUE("ejercicio","tipo")
                )
            ''')
            
            cambios = 0
            for tipo in TIPOS_DOC:
                cursor.execute('SELECT 1 FROM numerador WHERE tipo = ? AND ejercicio = ?', (tipo, ANIO_ACTUAL))
                if not cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO numerador (tipo, numerador, ejercicio) 
                        VALUES (?, 0, ?)
                    ''', (tipo, ANIO_ACTUAL))
                    print(f"  -> Insertado numerador {tipo}/{ANIO_ACTUAL} = 0")
                    cambios += 1
            
            if cambios > 0:
                conn.commit()
                print(f"  ✓ Se inicializaron {cambios} numeradores.")
            else:
                print("  - Numeradores ya inicializados.")
                
            conn.close()
            
        except Exception as e:
            print(f"  ERROR procesando {db_file}: {e}")

if __name__ == '__main__':
    init_numeradores()
