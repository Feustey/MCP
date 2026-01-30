# -*- coding: utf-8 -*-
"""
Database package initialization.
Réexporte get_database depuis config.database.mongodb pour compatibilité.
"""

try:
    from config.database.mongodb import get_database
except ImportError as e:
    import sys
    raise ImportError(
        f"Cannot import get_database from config.database.mongodb: {e}. "
        "Ensure config.database.mongodb is on PYTHONPATH and motor/pymongo are installed."
    ) from e

__all__ = ["get_database"]

