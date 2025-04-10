from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials
from typing import Dict

async def verify_jwt(credentials: HTTPAuthorizationCredentials = Security(HTTPAuthorizationCredentials)) -> Dict:
    # Implémentation de base - à remplacer par une vraie vérification JWT
    return {"user_id": "test_user", "role": "user"} 