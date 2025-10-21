"""
Config package initializer.

- Expose submodules like `config.rag_config`
- Preserve backward compatibility for `from config import settings`
  by dynamically loading the legacy root-level `config.py` (module)
  and re-exporting its `settings` symbol here.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from types import ModuleType

__all__ = [
    "settings",
    "MONGO_URL",
    "MONGO_DB_NAME",
    "DRY_RUN",
    "DEBUG_MODE",
]


def _load_legacy_root_config() -> ModuleType | None:
    """Load the legacy root-level config.py as a separate module name.

    This allows existing imports `from config import settings` to continue
    working even though `config` is now a package.
    """
    # Locate /app/config.py (root-level module copied into the image)
    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.py"))
    if not os.path.exists(root_path):
        return None
    module_name = "_root_config_compat"
    spec = importlib.util.spec_from_file_location(module_name, root_path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]
        return mod
    return None


# Try to expose `settings` from the legacy root config.py
_legacy = _load_legacy_root_config()
if _legacy is not None:
    # Re-export legacy symbols if present
    if hasattr(_legacy, "settings"):
        settings = getattr(_legacy, "settings")  # type: ignore[assignment]
    if hasattr(_legacy, "MONGO_URL"):
        MONGO_URL = getattr(_legacy, "MONGO_URL")  # type: ignore[assignment]
    if hasattr(_legacy, "MONGO_DB_NAME"):
        MONGO_DB_NAME = getattr(_legacy, "MONGO_DB_NAME")  # type: ignore[assignment]
    if hasattr(_legacy, "DRY_RUN"):
        DRY_RUN = getattr(_legacy, "DRY_RUN")  # type: ignore[assignment]
    if hasattr(_legacy, "DEBUG_MODE"):
        DEBUG_MODE = getattr(_legacy, "DEBUG_MODE")  # type: ignore[assignment]

# Fallbacks from environment if legacy symbols are absent
if 'MONGO_URL' not in globals():
    MONGO_URL = os.environ.get('MONGO_URL') or os.environ.get('MONGODB_URL') or 'mongodb://localhost:27017/mcp'
if 'MONGO_DB_NAME' not in globals():
    MONGO_DB_NAME = os.environ.get('MONGO_NAME') or os.environ.get('MONGODB_DATABASE') or 'mcp'
if 'DRY_RUN' not in globals():
    DRY_RUN = os.environ.get('DRY_RUN', 'true').lower() == 'true'
if 'DEBUG_MODE' not in globals():
    DEBUG_MODE = os.environ.get('DEBUG', 'false').lower() == 'true'



