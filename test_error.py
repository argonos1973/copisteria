# Archivo de prueba CORREGIDO
from logger_config import get_logger

logger = get_logger(__name__)

def test_function():
    try:
        result = calculate_something()
        # CORREGIDO: f-string bien formateado
        logger.info(f"Resultado calculado: {result}")
        return result
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return None
