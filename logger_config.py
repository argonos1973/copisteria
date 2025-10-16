"""
Configuración centralizada de logging para Aleph70

Uso:
    from logger_config import get_logger
    
    logger = get_logger(__name__)
    logger.info("Mensaje informativo")
    logger.error("Error ocurrido", exc_info=True)
"""

import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime

# Directorios de logs
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Niveles de logging por entorno
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

# Formato de logs
DETAILED_FORMAT = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

SIMPLE_FORMAT = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Configuración de handlers
def setup_file_handler(name, level=logging.INFO, max_bytes=10*1024*1024, backup_count=5):
    """
    Crea un RotatingFileHandler para un módulo específico
    
    Args:
        name: Nombre del módulo/archivo de log
        level: Nivel de logging
        max_bytes: Tamaño máximo del archivo (default: 10MB)
        backup_count: Número de backups a mantener (default: 5)
    """
    log_file = LOGS_DIR / f'{name}.log'
    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    handler.setLevel(level)
    handler.setFormatter(DETAILED_FORMAT)
    return handler

def setup_console_handler(level=logging.WARNING):
    """
    Crea un StreamHandler para consola
    Solo muestra WARNING y ERROR en producción
    """
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(SIMPLE_FORMAT)
    return handler

def get_logger(name):
    """
    Obtiene o crea un logger configurado
    
    Args:
        name: Nombre del módulo (usar __name__)
    
    Returns:
        logging.Logger: Logger configurado
    """
    logger = logging.getLogger(name)
    
    # Evitar duplicar handlers si ya está configurado
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    
    # Handler de archivo general
    logger.addHandler(setup_file_handler('aleph70', logging.DEBUG))
    
    # Handler de consola (solo warnings y errores)
    logger.addHandler(setup_console_handler(logging.WARNING))
    
    # Handler específico para errores
    error_handler = setup_file_handler('errors', logging.ERROR)
    logger.addHandler(error_handler)
    
    # Evitar propagación al root logger
    logger.propagate = False
    
    return logger

def get_module_logger(module_name):
    """
    Obtiene un logger con archivo específico para un módulo
    
    Args:
        module_name: Nombre del módulo (ej: 'factura', 'conciliacion')
    
    Returns:
        logging.Logger: Logger con archivo dedicado
    """
    logger = get_logger(f'aleph70.{module_name}')
    
    # Añadir handler específico del módulo
    module_handler = setup_file_handler(module_name, logging.DEBUG)
    logger.addHandler(module_handler)
    
    return logger

# Loggers especializados por módulo
def get_factura_logger():
    """Logger para módulo de facturación"""
    return get_module_logger('factura')

def get_conciliacion_logger():
    """Logger para módulo de conciliación"""
    return get_module_logger('conciliacion')

def get_scraping_logger():
    """Logger para scraping bancario"""
    return get_module_logger('scraping')

def get_verifactu_logger():
    """Logger para VeriFactu"""
    return get_module_logger('verifactu')

def get_estadisticas_logger():
    """Logger para estadísticas"""
    return get_module_logger('estadisticas')

def get_productos_logger():
    """Logger para gestión de productos"""
    return get_module_logger('productos')

def get_tickets_logger():
    """Logger para sistema de tickets"""
    return get_module_logger('tickets')

# Logger para peticiones HTTP
def get_request_logger():
    """Logger para peticiones HTTP (API endpoints)"""
    logger = get_logger('aleph70.requests')
    request_handler = setup_file_handler('requests', logging.INFO)
    logger.addHandler(request_handler)
    return logger

# Limpieza de logs antiguos
def cleanup_old_logs(days=30):
    """
    Elimina archivos de log más antiguos que X días
    
    Args:
        days: Días de retención (default: 30)
    """
    import time
    cutoff = time.time() - (days * 86400)
    
    for log_file in LOGS_DIR.glob('*.log*'):
        if log_file.stat().st_mtime < cutoff:
            try:
                log_file.unlink()
                print(f"Deleted old log: {log_file.name}")
            except Exception as e:
                print(f"Error deleting {log_file.name}: {e}")

# Configuración inicial
if __name__ == '__main__':
    # Test del sistema de logging
    logger = get_logger('test')
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    print(f"\n✅ Logs creados en: {LOGS_DIR}")
    print(f"   LOG_LEVEL: {LOG_LEVEL}")
    print(f"   Archivos de log:")
    for log_file in sorted(LOGS_DIR.glob('*.log')):
        size = log_file.stat().st_size
        print(f"   - {log_file.name} ({size} bytes)")
