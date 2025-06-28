import jwt
import os
from fastapi import HTTPException, status
from typing import Optional

# Utilisation de la variable d'environnement
SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET environment variable is required")
if len(SECRET_KEY) < 32:
    raise ValueError("JWT_SECRET must be at least 32 characters long")

ALGORITHM = "HS256"

def verify_jwt_and_get_tenant(authorization_header: str) -> Optional[str]:
    """
    Vérifie le JWT Bearer token et extrait le tenant_id.
    - Retourne le tenant_id si valide, None sinon.
    - Lève une HTTPException 401 si le token est invalide.
    """
    if not authorization_header or not authorization_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header Authorization manquant ou mal formé."
        )
    token = authorization_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Le token ne contient pas de tenant_id."
            )
        return tenant_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Le token JWT a expiré."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token JWT invalide."
        ) 