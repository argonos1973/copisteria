import sqlite3
from datetime import datetime

from constantes import DB_NAME


def guardar_notificacion(mensaje, tipo='info', db_path=DB_NAME):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
# Crear tabla si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notificaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                mensaje TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
# Insertar notificación
        cursor.execute(
            "INSERT INTO notificaciones (tipo, mensaje, timestamp) VALUES (?, ?, ?)",
            (tipo, mensaje, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error al guardar notificación: {e}")
