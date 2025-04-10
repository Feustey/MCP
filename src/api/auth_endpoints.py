from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from typing import Optional
from pydantic import BaseModel, Field
from src.auth.jwt import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    check_permissions
)
from src.auth.models import User, Token, UserRole, UserUpdate
from src.auth.database import db

# Création du router
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        401: {"description": "Non authentifié"},
        403: {"description": "Accès refusé"},
        429: {"description": "Trop de requêtes"},
        500: {"description": "Erreur serveur"}
    }
)

# Configuration
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class TokenResponse(BaseModel):
    """
    Modèle de réponse pour l'authentification
    """
    access_token: str = Field(..., description="Token JWT d'accès")
    token_type: str = Field(..., description="Type de token (bearer)")
    expires_in: int = Field(..., description="Durée de validité en secondes")
    user: User = Field(..., description="Informations de l'utilisateur")

@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    current_user: Optional[User] = None
):
    """
    Authentifie un utilisateur et retourne un token JWT.
    
    Cette endpoint permet à un utilisateur de s'authentifier et de recevoir
    un token JWT pour accéder aux endpoints protégés.
    """
    user = await db.verify_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Mise à jour de la dernière connexion
    await db.update_last_login(user.id)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user
    }

@router.post("/register", response_model=User)
async def register_user(user: UserUpdate):
    """
    Enregistre un nouvel utilisateur.
    
    Cette endpoint permet de créer un nouveau compte utilisateur
    avec les informations fournies.
    """
    # Vérifier si l'utilisateur existe déjà
    existing_user = await db.get_user_by_username(user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nom d'utilisateur déjà utilisé"
        )
    
    # Créer le nouvel utilisateur
    hashed_password = get_password_hash(user.password)
    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=UserRole.USER,
        created_at=datetime.utcnow()
    )
    
    # Sauvegarder l'utilisateur
    created_user = await db.create_user(new_user)
    return created_user

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Récupère les informations de l'utilisateur connecté.
    
    Cette endpoint retourne les informations de l'utilisateur
    actuellement authentifié.
    """
    return current_user

@router.put("/me", response_model=User)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Met à jour les informations de l'utilisateur connecté.
    
    Cette endpoint permet à un utilisateur de mettre à jour
    ses informations personnelles.
    """
    updated_user = await db.update_user(current_user.id, user_update)
    return updated_user

@router.get("/admin")
async def admin_endpoint(
    current_user: User = Depends(check_permissions(UserRole.ADMIN))
):
    """
    Endpoint protégé accessible uniquement aux administrateurs.
    
    Cette endpoint sert à vérifier les droits d'administration
    d'un utilisateur.
    """
    return {
        "message": "Accès administrateur autorisé",
        "user": current_user
    } 