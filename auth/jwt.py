from datetime import datetime
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .models import User, TokenData, UserRole
from .lightning import LightningKeyValidator
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "votre_clé_secrète_très_longue_et_complexe")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Récupère l'utilisateur courant à partir du token JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les identifiants",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(
            username=username,
            role=UserRole(payload.get("role", "user")),
            exp=datetime.fromtimestamp(payload.get("exp"))
        )
    except JWTError:
        raise credentials_exception
    
    return User(
        username=token_data.username,
        role=token_data.role,
        lightning_pubkey=payload.get("lightning_pubkey")
    )

def check_permissions(required_role: UserRole):
    """Décorateur pour vérifier les permissions."""
    async def permission_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissions insuffisantes"
            )
        return current_user
    return permission_checker

def validate_lightning_pubkey(pubkey: str) -> bool:
    """Valide une clé publique Lightning."""
    return LightningKeyValidator.is_valid_pubkey(pubkey)

def validate_lightning_node_id(node_id: str) -> bool:
    """Valide un node_id Lightning."""
    return LightningKeyValidator.is_valid_node_id(node_id)

def convert_pubkey_to_node_id(pubkey: str) -> Optional[str]:
    """Convertit une clé publique en node_id."""
    return LightningKeyValidator.pubkey_to_node_id(pubkey)

def convert_node_id_to_pubkey(node_id: str) -> Optional[str]:
    """Convertit un node_id en clé publique."""
    return LightningKeyValidator.node_id_to_pubkey(node_id)

def create_permanent_token(username: str = "admin", role: str = "admin", expires_years: int = 10) -> str:
    """Crée un token JWT permanent pour Dazlng."""
    data = {
        "sub": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(days=365 * expires_years)
    }
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM) 