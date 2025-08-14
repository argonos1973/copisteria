#!/usr/bin/env python3
import sqlite3
from datetime import datetime


def get_db_connection():
    db_path = '/var/www/html/aleph70.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Actualizar los timestamps en la base de datos
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Usar un timestamp actual
    ahora = datetime.now()
    nuevo_timestamp = ahora.isoformat()
    print(f"Actualizando registros con nuevo timestamp: {nuevo_timestamp}")
    
    # Actualizar todos los registros del mes actual
    mes_actual = ahora.month
    anio_actual = ahora.year
    patron = f"%/{mes_actual:02d}/{anio_actual}"
    
    # Verificar cuántos registros hay para actualizar
    cursor.execute("SELECT COUNT(*) FROM gastos WHERE fecha_operacion LIKE ?", (patron,))
    total_registros = cursor.fetchone()[0]
    print(f"Encontrados {total_registros} registros para actualizar")
    
    # Actualizar los timestamps
    cursor.execute("UPDATE gastos SET ts = ? WHERE fecha_operacion LIKE ?", 
                  (nuevo_timestamp, patron))
    conn.commit()
    
    # Verificar que se hayan actualizado
    print(f"Registros actualizados: {cursor.rowcount}")
    
    # Mostrar algunos registros actualizados
    cursor.execute("SELECT ts, fecha_operacion FROM gastos ORDER BY rowid DESC LIMIT 5")
    for row in cursor.fetchall():
        print(f"TS: {row[0]}, Fecha: {row[1]}")
    
    conn.close()
    print("Actualización completada con éxito")
    
except Exception as e:
    print(f"Error al actualizar los timestamps: {e}")
