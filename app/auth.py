import jwt
import os
from fastapi import HTTPException, status
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Configuration sécurisée du JWT - Pas de fallback en production
SECRET_KEY = os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")

# Bloquer le démarrage si aucune clé valide n'est fournie
if not SECRET_KEY:
    error_msg = "CRITICAL: JWT_SECRET environment variable is required. Application cannot start without it."
    logger.critical(error_msg)
    raise RuntimeError(error_msg)

if len(SECRET_KEY) < 32:
    error_msg = f"CRITICAL: JWT_SECRET too short ({len(SECRET_KEY)} chars). Minimum 32 characters required for security."
    logger.critical(error_msg)
    raise RuntimeError(error_msg)

ALGORITHM = "HS256"

def verify_jwt_and_get_tenant(authorization_header: str) -> Optional[str]:
    """
    Vérifie le JWT Bearer token et extrait le tenant_id.
    - Retourne le tenant_id si valide, None sinon.
    - Lève une HTTPException 401 si le token est invalide.
    """
    # Mode développement - désactivé en production
    # Ne jamais activer DEVELOPMENT_MODE sur un serveur exposé
    if os.getenv("ENVIRONMENT") == "development" and os.getenv("DEVELOPMENT_MODE") == "true":
        logger.warning("Development mode active - authentication bypassed. DO NOT USE IN PRODUCTION.")
        return "development_tenant"
    
    # Vérification du header
    if not authorization_header:
        logger.warning("Authorization header missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header Authorization manquant."
        )
    
    # Support pour différents formats
    if not isinstance(authorization_header, str):
        logger.error(f"Authorization header is not a string: {type(authorization_header)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header Authorization mal formé."
        )
    
    # Extraction du token
    if authorization_header.startswith("Bearer "):
        token = authorization_header.split(" ", 1)[1]
    else:
        # Accepter le token directement s'il n'y a pas de préfixe Bearer
        token = authorization_header
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        tenant_id = payload.get("tenant_id") or payload.get("sub") or "default_tenant"
        logger.debug(f"Token decoded successfully, tenant_id: {tenant_id}")
        return tenant_id
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Le token JWT a expiré."
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid JWT token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token JWT invalide."
        )
    except Exception as e:
        logger.error(f"Unexpected error in JWT verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Erreur lors de la vérification du token."
        ) 