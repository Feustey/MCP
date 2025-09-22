"""
Service d'authentification pour l'API MCP
"""

from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import os
import logging

logger = logging.getLogger("mcp.auth")
security = HTTPBearer()

# Clés API valides (en production, utiliser une base de données ou gestionnaire de secrets)
VALID_API_KEYS = {
    "mcp_2f0d711f886ef6e2551397ba90b5152dfe6b23d4": {
        "name": "MCP Production Key",
        "permissions": ["read", "write", "admin"]
    },
    # Ajouter d'autres clés si nécessaire
    os.getenv("MCP_API_KEY", "test_key"): {
        "name": "Environment Key",
        "permissions": ["read", "write"]
    }
}

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Vérifie la validité de la clé API
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    api_key = credentials.credentials
    
    # Vérifier si la clé existe
    if api_key not in VALID_API_KEYS:
        logger.warning(f"Invalid API key attempted: {api_key[:16]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Retourner les informations de la clé
    key_info = VALID_API_KEYS[api_key]
    logger.info(f"Valid API key used: {key_info['name']}")
    
    return {
        "api_key": api_key,
        "name": key_info["name"],
        "permissions": key_info["permissions"]
    }

def verify_api_key_simple(api_key: str) -> bool:
    """
    Vérification simple de clé API (pour compatibilité)
    """
    return api_key in VALID_API_KEYS

def get_api_key_permissions(api_key: str) -> list:
    """
    Obtient les permissions d'une clé API
    """
    if api_key in VALID_API_KEYS:
        return VALID_API_KEYS[api_key]["permissions"]
    return []

def require_permission(required_permission: str):
    """
    Décorateur pour vérifier les permissions
    """
    def decorator(func):
        async def wrapper(credentials: HTTPAuthorizationCredentials = Security(security), *args, **kwargs):
            key_info = await verify_api_key(credentials)
            
            if required_permission not in key_info["permissions"]:
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission '{required_permission}' required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator