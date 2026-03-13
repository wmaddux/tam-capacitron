"""
Load input defaults and slider specs from config/inputs.json.

Edit config/inputs.json to change default values and slider min/max/step
without touching Python or the frontend. Restart the app after editing.
"""

import json
from pathlib import Path
from typing import Any

_CONFIG: dict[str, Any] | None = None


def _config_path() -> Path:
    """Path to config/inputs.json (repo root / config / inputs.json)."""
    return Path(__file__).resolve().parent.parent / "config" / "inputs.json"


def _load_config() -> dict[str, Any]:
    """Load config once; return cached dict."""
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG
    path = _config_path()
    if not path.is_file():
        _CONFIG = {"defaults": {}, "sliders": {}}
        return _CONFIG
    with open(path, encoding="utf-8") as f:
        _CONFIG = json.load(f)
    return _CONFIG


def get_defaults() -> dict[str, Any]:
    """Return default input values (flat, CapacityInputs-shaped)."""
    cfg = _load_config()
    return cfg.get("defaults", {}).copy()


def get_slider_specs() -> dict[str, dict[str, float]]:
    """Return slider metadata: { key: { min, max, step }, ... }."""
    cfg = _load_config()
    return cfg.get("sliders", {}).copy()
