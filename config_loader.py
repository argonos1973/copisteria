import json
import os
from pathlib import Path

# Ruta por defecto al archivo de configuración JSON
DEFAULT_CONFIG_PATH = Path(os.getenv("APP_CONFIG_PATH", "/var/www/html/config.json"))

# Cache interno para evitar leer múltiples veces
_CONFIG_CACHE = None


def _load_config_from_file(path: Path):
    try:
        if path.is_file():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        # Si hay error al leer o parsear, ignoramos y devolvemos dict vacío
        pass
    return {}


def get(key: str, default=None):
    """Obtiene un valor de configuración. Lee una sola vez y cachea."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        _CONFIG_CACHE = _load_config_from_file(DEFAULT_CONFIG_PATH)
    return _CONFIG_CACHE.get(key, default)
