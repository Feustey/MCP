from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from dotenv import load_dotenv
import os

load_dotenv()

security = HTTPBearer()
SECRET_KEY = os.getenv("SECRET_KEY", "bydeKu3eAd8YFBZwQBYOuHXwUGAZurlX")

async def verify_jwt(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Vérifie le token JWT fourni dans l'en-tête Authorization.
    Retourne les données du token si valide, lève une exception sinon.
    """
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expiré"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token invalide"
        ) 