import sqlite3
from datetime import datetime
import os

from constantes import DB_NAME
from logger_config import get_logger

# Inicializar logger
logger = get_logger(__name__)


def guardar_notificacion(mensaje, tipo='info', db_path=DB_NAME):
    try:
        resolved_db_path = db_path
        try:
            env_db = os.getenv('EMPRESA_DB_PATH')
            if env_db and os.path.exists(env_db) and (db_path == DB_NAME or not db_path):
                resolved_db_path = env_db
        except Exception:
            resolved_db_path = db_path

        conn = sqlite3.connect(resolved_db_path)
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
        logger.error(f"Error al guardar notificación: {e}", exc_info=True)
