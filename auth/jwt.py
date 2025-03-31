from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
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
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Génère un hash de mot de passe."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crée un token JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Récupère l'utilisateur courant à partir du token."""
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
        
    # Ici, vous devriez récupérer l'utilisateur depuis votre base de données
    # Pour l'exemple, nous créons un utilisateur factice
    user = User(
        id="1",
        username=token_data.username,
        email="user@example.com",
        role=token_data.role,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    if user is None:
        raise credentials_exception
    return user

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