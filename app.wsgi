import sys
import os
import site
import logging

# Configurar logging para depuración
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('wsgi')

# Manejar el módulo requests antes de que se importe en otras partes
try:
    import requests
    logger.info("Módulo requests importado correctamente en app.wsgi")
except ImportError:
    logger.warning("No se pudo importar requests. Creando módulo mock para evitar errores.")
    # Crear un módulo mock para requests si no está disponible
    import types
    requests = types.ModuleType('requests')
    requests.get = lambda *args, **kwargs: None
    requests.post = lambda *args, **kwargs: None
    requests.put = lambda *args, **kwargs: None
    requests.delete = lambda *args, **kwargs: None
    sys.modules['requests'] = requests
    logger.info("Módulo mock de requests creado satisfactoriamente")

# Ya no intentamos activar un entorno virtual que no existe
logger.info("Usando la instalación de Python del sistema")

# Asegurarse de que /var/www/html esté en el path
if '/var/www/html' not in sys.path:
    sys.path.insert(0, '/var/www/html')
    logger.info("Directorio /var/www/html añadido al path")

# Verificar que los módulos necesarios estén disponibles
try:
    import flask
    logger.info("Flask está instalado y disponible")
except ImportError:
    logger.error("Flask no está disponible - la aplicación podría fallar")

# Añadir la ruta del proyecto
sys.path.insert(0, '/var/www/html')
logger.info("Directorio del proyecto añadido al path")

# Asegurar que se pueda importar verifactu sin problemas con requests
try:
    import verifactu
    logger.info("Módulo verifactu importado correctamente")
except Exception as e:
    logger.error(f"Error al importar verifactu: {e}")

# Importar la aplicación Flask
try:
    from app import app as application  # 'application' debe apuntar a tu app Flask
    logger.info("Aplicación Flask cargada correctamente")
    try:
        for rule in application.url_map.iter_rules():
            logger.error(f"Ruta registrada: {rule}")
    except Exception as e:
        logger.error(f"Error listando rutas: {e}")
except Exception as e:
    logger.error(f"Error al cargar la aplicación Flask: {e}")
    raise
