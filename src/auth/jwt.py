from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Optional
from datetime import datetime, timedelta
from .models import User

# Configuration pour les tests - normalement ce serait dans un fichier d'environnement
DISABLE_AUTH_FOR_TESTS = True

security = HTTPBearer(auto_error=not DISABLE_AUTH_FOR_TESTS)

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> User:
    """
    Fonction pour vérifier le JWT et récupérer l'utilisateur courant.
    Cette version est simplifiée et retourne un utilisateur de test.
    En production, cette fonction vérifierait la validité du token JWT.
    """
    # Si l'authentification est désactivée pour les tests, retourner un utilisateur fictif
    if DISABLE_AUTH_FOR_TESTS:
        return User(
            id="test_user_id",
            username="test_user",
            email="test@example.com",
            role="admin"
        )
        
    # En production, vérifier le token JWT
    if not credentials:
        raise HTTPException(status_code=401, detail="Non authentifié")
        
    # Vérification simplifiée pour les tests
    return User(
        id="test_user_id",
        username="test_user",
        email="test@example.com",
        role="admin"
    ) 