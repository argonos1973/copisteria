import logging

# Logger compartido para la app. Si ya existe un logger "wsgi" (usado por la app), lo reutilizamos.
logger = logging.getLogger("wsgi")

# Si no tiene handlers configurados, añadimos uno a stderr (lo recogerá Apache/mod_wsgi en error.log)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(_handler)

__all__ = ["logger"]
