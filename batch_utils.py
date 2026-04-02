import json
import os


DEFAULT_DB_FALLBACK = "/var/www/html/db/aleph70.db"


def load_batch_params():
    # Primero intentar desde variable de entorno
    raw = os.environ.get("BATCH_PARAMS_JSON")
    if raw:
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            pass
    
    # Luego intentar desde archivo batch_params.json
    try:
        params_path = "/var/www/html/batch_params.json"
        if os.path.exists(params_path):
            with open(params_path, 'r', encoding='utf-8') as f:
                obj = json.load(f)
                return obj if isinstance(obj, dict) else {}
    except Exception:
        pass
    
    return {}


def get_batch_db_path(params=None, default_path=None):
    if default_path is None:
        default_path = DEFAULT_DB_FALLBACK

    db_path = os.getenv("EMPRESA_DB_PATH") or default_path

    if params and isinstance(params, dict) and params.get("db_path"):
        try:
            db_path = str(params.get("db_path"))
        except Exception:
            pass

    return db_path
