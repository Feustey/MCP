"""
Module d'authentification pour MCP.

Ce module fournit des fonctionnalités d'authentification et d'autorisation
pour l'API MCP.
"""

from .jwt import get_current_user
from .models import User

__all__ = [
    'get_current_user', 
    'User'
] 