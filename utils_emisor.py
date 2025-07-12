import json
import os


def cargar_datos_emisor(config_path=None):
    """
    Carga los datos del emisor desde un archivo JSON de configuración.
    Por defecto busca emisor_config.json en el mismo directorio que este archivo.
    """
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), 'emisor_config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)
