import json
import os


DEFAULT_DB_FALLBACK = "/var/www/html/db/aleph70.db"


def load_batch_params():
    raw = os.environ.get("BATCH_PARAMS_JSON")
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
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
