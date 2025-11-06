# constantes.py
import socket

# Detectar IP automáticamente o usar localhost
from logger_config import get_logger

logger = get_logger(__name__)
def get_local_ip():
    try:
        # Obtener la IP local del servidor actual
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return "127.0.0.1"

IP_SERVIDOR = get_local_ip()

# Base de datos por defecto (solo para scripts sin contexto de sesión)
# En sistema multiempresa, SIEMPRE se debe usar session['empresa_db']
DB_NAME = None  # No hardcodear ninguna BD específica
