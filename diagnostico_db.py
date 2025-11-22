import sqlite3
import os
import sys

dbs = [
    '/var/www/html/db/caca/caca.db',
    '/var/www/html/db/aleph70.db'
]

for db_path in dbs:
    if not os.path.exists(db_path):
        continue
        
    print(f"\n--- Verificando BD: {db_path} ---")
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        cursor = conn.cursor()
        
        # 1. Check integridad
        integrity = cursor.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"Integridad: {integrity}")
        
        # 2. Últimos tickets
        print("Últimos 3 tickets:")
        tickets = cursor.execute("SELECT id, fecha, numero, total, timestamp FROM tickets ORDER BY id DESC LIMIT 3").fetchall()
        for t in tickets:
            print(f"  ID: {t[0]}, Num: {t[2]}, Fecha: {t[1]}, Total: {t[3]}, TS: {t[4]}")
            
        # 3. Numerador
        num = cursor.execute("SELECT numerador FROM numerador WHERE tipo='T'").fetchone()
        print(f"Numerador T actual: {num[0] if num else 'No encontrado'}")
        
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")
