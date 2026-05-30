"""Gestion de configuracion y rutas de datos del usuario."""
from __future__ import annotations

import json
import os
from pathlib import Path

APP_NAME = "Vita"

# Modelo de Gemini por defecto (capa gratuita real en 2026, rapido)
DEFAULT_MODEL = "gemini-2.5-flash-lite"

# Manifiesto de versiones para auto-actualizacion (JSON: version/url/notes).
# Vacio = sin comprobacion de actualizaciones.
UPDATE_URL = "https://raw.githubusercontent.com/DavidRdgzz/vita/main/version.json"

# Modelos que perdieron la capa gratuita: se migran al default al arrancar.
_DEPRECATED_MODELS = {
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "claude-haiku-4-5-20251001",
}

_DEFAULT_CONFIG = {
    "api_key": "",
    "model": DEFAULT_MODEL,
    "water_goal_ml": 2500,
}


def data_dir() -> Path:
    """Carpeta persistente del usuario (%APPDATA%\\Vita en Windows)."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = Path(base) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    return data_dir() / "vita.db"


def _config_path() -> Path:
    return data_dir() / "config.json"


def load_config() -> dict:
    path = _config_path()
    cfg = dict(_DEFAULT_CONFIG)
    if path.exists():
        try:
            cfg.update(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg: dict) -> None:
    _config_path().write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def get(key: str, default=None):
    return load_config().get(key, default)


def set_value(key: str, value) -> None:
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)


def migrate() -> None:
    """Repara configuraciones antiguas (p. ej. modelos sin capa gratuita)."""
    cfg = load_config()
    if cfg.get("model") in _DEPRECATED_MODELS:
        cfg["model"] = DEFAULT_MODEL
        save_config(cfg)


def get_api_key() -> str:
    """API key desde config o variable de entorno GEMINI_API_KEY."""
    key = load_config().get("api_key", "").strip()
    if key:
        return key
    return os.environ.get("GEMINI_API_KEY", "").strip()
