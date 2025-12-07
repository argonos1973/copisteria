#!/usr/bin/env python3
import os
import sqlite3
import re
from datetime import datetime

DB_ROOT = '/var/www/html/db'
ANIO_ACTUAL = datetime.now().year
EJERCICIO_CORTO = ANIO_ACTUAL % 100

CONFIG = {
    'F': {'table': 'factura', 'col': 'numero', 'prefix': f'F{EJERCICIO_CORTO:02}'},
    'T': {'table': 'tickets', 'col': 'numero', 'prefix': f'T{EJERCICIO_CORTO:02}'},
    'P': {'table': 'proforma', 'col': 'numero', 'prefix': f'P{EJERCICIO_CORTO:02}'},
}

def sync_numeradores():
    print(f"Sincronizando numeradores en {DB_ROOT} para ejercicio {ANIO_ACTUAL} (Prefijos *{EJERCICIO_CORTO:02}*)")
    
    if not os.path.exists(DB_ROOT):
        print(f"Directorio {DB_ROOT} no existe.")
        return

    for nombre_empresa in os.listdir(DB_ROOT):
        empresa_dir = os.path.join(DB_ROOT, nombre_empresa)
        if not os.path.isdir(empresa_dir): continue
            
        db_file = None
        for f in os.listdir(empresa_dir):
            if f.endswith('.db') and not f.endswith('plantilla.db'):
                db_file = os.path.join(empresa_dir, f)
                break
        
        if not db_file: continue
            
        print(f"[{nombre_empresa}] Procesando {db_file}...")
        
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            cambios = 0
            
            for tipo, conf in CONFIG.items():
                cursor.execute('SELECT numerador FROM numerador WHERE tipo = ? AND ejercicio = ?', (tipo, ANIO_ACTUAL))
                res = cursor.fetchone()
                if not res: continue
                
                num_actual_db = res[0]
                tabla = conf['table']
                col = conf['col']
                prefijo = conf['prefix']
                
                try:
                    # Verificar tabla
                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabla}'")
                    if not cursor.fetchone(): continue

                    # Obtener top 20 documentos para buscar el número más alto válido
                    cursor.execute(f"SELECT {col} FROM {tabla} WHERE {col} LIKE '{prefijo}%' ORDER BY {col} DESC LIMIT 20")
                    rows = cursor.fetchall()
                    
                    max_num_real = 0
                    
                    for row in rows:
                        doc_num = row[0]
                        # Intentar extraer número tras el prefijo
                        # T250001 -> 0001 -> 1
                        # T250001-R -> 0001 -> 1
                        parte_util = doc_num[len(prefijo):]
                        
                        # Buscar secuencia de dígitos inicial
                        match = re.match(r'^(\d+)', parte_util)
                        if match:
                            val = int(match.group(1))
                            if val > max_num_real:
                                max_num_real = val
                    
                    if max_num_real > num_actual_db:
                        print(f"  ⚠️ DESFASE {tipo}: BD={num_actual_db} vs REAL={max_num_real}")
                        cursor.execute('UPDATE numerador SET numerador = ? WHERE tipo = ? AND ejercicio = ?', 
                                      (max_num_real, tipo, ANIO_ACTUAL))
                        cambios += 1
                    
                except Exception as e_inner:
                    print(f"  - Error revisando {tipo}: {e_inner}")

            if cambios > 0:
                conn.commit()
                print(f"  ✓ Corregidos {cambios} numeradores.")
            else:
                print("  - OK.")
            
            conn.close()
            
        except Exception as e:
            print(f"  ERROR global en {nombre_empresa}: {e}")

if __name__ == '__main__':
    sync_numeradores()
