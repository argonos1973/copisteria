import sys
import os
import site
import logging

# Configurar logging para depuración
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('wsgi')

# Asegurar UTF-8 en stdout/stderr bajo mod_wsgi para evitar errores de codificación ASCII
try:
    import sys as _sys
    if hasattr(_sys.stdout, 'reconfigure'):
        _sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(_sys.stderr, 'reconfigure'):
        _sys.stderr.reconfigure(encoding='utf-8')
    logger.info("stdout/stderr reconfigurados a UTF-8")
except Exception as _e:
    try:
        logger.warning(f"No se pudo reconfigurar stdout/stderr a UTF-8: {_e}")
    except Exception:
        pass

# Activar el entorno virtual
venv_path = '/var/www/html/venv'
activate_this = os.path.join(venv_path, 'bin/activate_this.py')

if os.path.exists(activate_this):
    with open(activate_this) as f:
        code = compile(f.read(), activate_this, 'exec')
        exec(code, dict(__file__=activate_this))
    logger.info("Entorno virtual activado correctamente")
else:
    # Configurar manualmente el entorno virtual
    site_packages = os.path.join(venv_path, 'lib/python3.*/site-packages')
    import glob
    site_packages_dirs = glob.glob(site_packages)
    if site_packages_dirs:
        site.addsitedir(site_packages_dirs[0])
        logger.info(f"Directorio site-packages añadido: {site_packages_dirs[0]}")
    else:
        logger.warning("No se encontró el directorio site-packages del venv")

logger.info("Usando entorno virtual de /var/www/html/venv")

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
        franjas_routes = []
        for rule in application.url_map.iter_rules():
            if 'franjas_config' in str(rule):
                franjas_routes.append(str(rule))
            logger.error(f"Ruta registrada: {rule}")
        logger.error(f"Rutas franjas_config encontradas: {franjas_routes}")

        # Middleware de prefijo /api para compatibilidad con WSGIScriptAlias /api
        def _add_prefix_middleware(app, prefix='/api'):
            def wrapper(environ, start_response):
                path = environ.get('PATH_INFO', '')
                # WSGIScriptAlias /api elimina /api del PATH_INFO, lo restauramos
                if not path.startswith(prefix):
                    environ['PATH_INFO'] = prefix + path
                return app(environ, start_response)
            return wrapper

        application = _add_prefix_middleware(application, '/api')
        logger.info("Middleware de prefijo '/api' activado en WSGI")
    except Exception as e:
        logger.error(f"Error listando rutas: {e}")
except Exception as e:
    logger.error(f"Error al cargar la aplicación Flask: {e}")
    raise
# Force reload mié 22 oct 2025 22:40:43 CEST
