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

# Activar el entorno virtual usando el método más compatible
activate_this = '/var/www/html/venv/bin/activate_this.py'

try:
    with open(activate_this) as file_:
        exec(file_.read(), dict(__file__=activate_this))
    logger.info("Entorno virtual activado mediante activate_this.py")
except FileNotFoundError:
    # Alternativa si activate_this.py no existe
    logger.info("activate_this.py no encontrado, usando método alternativo")
    site_packages = '/var/www/html/venv/lib/python3.12/site-packages'
    prev_sys_path = list(sys.path)
    site.addsitedir(site_packages)
    sys.real_prefix = sys.prefix
    sys.prefix = '/var/www/html/venv'
    new_sys_path = []
    for item in list(sys.path):
        if item not in prev_sys_path:
            new_sys_path.append(item)
            sys.path.remove(item)
    sys.path[:0] = new_sys_path
    logger.info(f"site-packages añadido: {site_packages}")

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
