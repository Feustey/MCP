from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from typing import Optional
from .models import User, Token, UserRole, UserUpdate
from .jwt import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    check_permissions,
    validate_lightning_pubkey,
    validate_lightning_node_id
)
from .database import db

router = APIRouter(prefix="/auth", tags=["authentication"])

# Configuration
ACCESS_TOKEN_EXPIRE_MINUTES = 30

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    current_user: Optional[User] = None
):
    """Authentifie un utilisateur et retourne un token JWT."""
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
        "user": User.from_orm(user)
    }

@router.put("/me", response_model=User)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """Met à jour les informations de l'utilisateur courant."""
    updated_user = await db.update_user(current_user.id, **user_update.dict(exclude_unset=True))
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    return User.from_orm(updated_user)

@router.post("/validate-lightning-key")
async def validate_lightning_key(
    pubkey: str,
    current_user: User = Depends(get_current_user)
):
    """Valide une clé publique Lightning."""
    if not validate_lightning_pubkey(pubkey):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clé publique Lightning invalide"
        )
    return {"message": "Clé publique Lightning valide"}

@router.post("/validate-lightning-node")
async def validate_lightning_node(
    node_id: str,
    current_user: User = Depends(get_current_user)
):
    """Valide un node_id Lightning."""
    if not validate_lightning_node_id(node_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Node ID Lightning invalide"
        )
    return {"message": "Node ID Lightning valide"}

@router.get("/admin")
async def admin_endpoint(
    current_user: User = Depends(check_permissions(UserRole.ADMIN))
):
    """Endpoint protégé accessible uniquement aux administrateurs."""
    return {"message": "Accès administrateur autorisé"} 