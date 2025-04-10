from fastapi import APIRouter, HTTPException, Depends, Query, Path, status, Header
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import logging
import jwt
from .models import (
    User, UserCreate, UserUpdate,
    Token, TokenCreate, TokenResponse, TokenFilter,
    LoginRequest, RefreshRequest,
    APIKey, APIKeyCreate, APIKeyResponse,
    TokenType, TokenStatus, PermissionScope
)

# Configuration du logging
logger = logging.getLogger(__name__)

# Configuration JWT
JWT_SECRET = "your-secret-key"  # À remplacer par une vraie clé secrète
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Création du router
router = APIRouter(
    prefix="/auth",
    tags=["authentification"],
    responses={
        401: {"description": "Non autorisé"},
        403: {"description": "Accès interdit"},
        404: {"description": "Ressource non trouvée"},
        500: {"description": "Erreur interne du serveur"}
    }
)

# Base de données temporaire en mémoire (à remplacer par une vraie base de données)
class AuthDB:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.tokens: Dict[str, Token] = {}
        self.api_keys: Dict[str, APIKey] = {}

# Instance de la base de données
db = AuthDB()

# Fonctions utilitaires
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Créer un jeton d'accès JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Créer un jeton de rafraîchissement JWT"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """Vérifier un jeton JWT"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton expiré"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton invalide"
        )

# Middleware d'authentification
async def get_current_user(authorization: str = Header(...)) -> User:
    """Middleware pour obtenir l'utilisateur courant"""
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Schéma d'authentification invalide"
            )
        payload = verify_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Jeton invalide"
            )
        if user_id not in db.users:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )
        return db.users[user_id]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Format d'authentification invalide"
        )

# Routes pour les utilisateurs
@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """Créer un nouvel utilisateur"""
    # Vérifier si l'utilisateur existe déjà
    for existing_user in db.users.values():
        if existing_user.username == user.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nom d'utilisateur déjà utilisé"
            )
        if existing_user.email == user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email déjà utilisé"
            )
    
    # Créer l'utilisateur
    user_id = f"user-{uuid.uuid4().hex[:8]}"
    new_user = User(
        id=user_id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        created_at=datetime.utcnow(),
        scopes=user.scopes or [PermissionScope.READ],
        metadata=user.metadata or {}
    )
    db.users[user_id] = new_user
    return new_user

@router.get("/users/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Obtenir les informations de l'utilisateur courant"""
    return current_user

@router.put("/users/me", response_model=User)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """Mettre à jour les informations de l'utilisateur courant"""
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    return current_user

# Routes pour l'authentification
@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Se connecter et obtenir un jeton"""
    # Vérifier les identifiants (à remplacer par une vraie vérification)
    user = None
    for u in db.users.values():
        if u.username == request.username:
            user = u
            break
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides"
        )
    
    # Créer les jetons
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "scopes": [s.value for s in request.scopes or user.scopes]},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id, "scopes": [s.value for s in request.scopes or user.scopes]}
    )
    
    # Enregistrer les jetons
    token_id = f"token-{uuid.uuid4().hex[:8]}"
    db.tokens[token_id] = Token(
        id=token_id,
        user_id=user.id,
        type=TokenType.ACCESS,
        token=access_token,
        status=TokenStatus.ACTIVE,
        scopes=request.scopes or user.scopes,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + access_token_expires,
        last_used=datetime.utcnow()
    )
    
    refresh_token_id = f"token-{uuid.uuid4().hex[:8]}"
    db.tokens[refresh_token_id] = Token(
        id=refresh_token_id,
        user_id=user.id,
        type=TokenType.REFRESH,
        token=refresh_token,
        status=TokenStatus.ACTIVE,
        scopes=request.scopes or user.scopes,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        last_used=datetime.utcnow()
    )
    
    # Mettre à jour la dernière connexion
    user.last_login = datetime.utcnow()
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token,
        scopes=request.scopes or user.scopes
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """Rafraîchir un jeton"""
    # Vérifier le jeton de rafraîchissement
    payload = verify_token(request.refresh_token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton invalide"
        )
    
    # Vérifier si l'utilisateur existe
    if user_id not in db.users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    user = db.users[user_id]
    
    # Créer un nouveau jeton d'accès
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "scopes": [s.value for s in request.scopes or user.scopes]},
        expires_delta=access_token_expires
    )
    
    # Enregistrer le nouveau jeton
    token_id = f"token-{uuid.uuid4().hex[:8]}"
    db.tokens[token_id] = Token(
        id=token_id,
        user_id=user.id,
        type=TokenType.ACCESS,
        token=access_token,
        status=TokenStatus.ACTIVE,
        scopes=request.scopes or user.scopes,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + access_token_expires,
        last_used=datetime.utcnow()
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=request.refresh_token,
        scopes=request.scopes or user.scopes
    )

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Se déconnecter"""
    # Révoquer tous les jetons de l'utilisateur
    for token in db.tokens.values():
        if token.user_id == current_user.id:
            token.status = TokenStatus.REVOKED
    return {"message": "Déconnexion réussie"}

# Routes pour les clés API
@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    api_key: APIKeyCreate,
    current_user: User = Depends(get_current_user)
):
    """Créer une nouvelle clé API"""
    # Générer une clé API unique
    api_key_value = f"lk_{uuid.uuid4().hex}"
    
    # Créer la clé API
    key_id = f"apikey-{uuid.uuid4().hex[:8]}"
    new_api_key = APIKey(
        id=key_id,
        user_id=current_user.id,
        name=api_key.name,
        key=api_key_value,
        status=TokenStatus.ACTIVE,
        scopes=api_key.scopes,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(seconds=api_key.expires_in) if api_key.expires_in else None,
        last_used=None,
        metadata=api_key.metadata or {}
    )
    db.api_keys[key_id] = new_api_key
    
    return APIKeyResponse(
        id=new_api_key.id,
        name=new_api_key.name,
        key=new_api_key.key,
        scopes=new_api_key.scopes,
        created_at=new_api_key.created_at,
        expires_at=new_api_key.expires_at
    )

@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(current_user: User = Depends(get_current_user)):
    """Lister les clés API de l'utilisateur"""
    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            key=key.key,
            scopes=key.scopes,
            created_at=key.created_at,
            expires_at=key.expires_at
        )
        for key in db.api_keys.values()
        if key.user_id == current_user.id
    ]

@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str = Path(..., description="ID de la clé API"),
    current_user: User = Depends(get_current_user)
):
    """Supprimer une clé API"""
    if key_id not in db.api_keys:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clé API non trouvée"
        )
    
    api_key = db.api_keys[key_id]
    if api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès interdit"
        )
    
    del db.api_keys[key_id]
    return None 