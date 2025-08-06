"""
CRUD operations for user management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime
from .models import User, UserCreate, UserUpdate, UserRole
from .jwt import get_current_user, check_permissions
from .database import db

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=User)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(check_permissions([UserRole.ADMIN]))
):
    """Créer un nouvel utilisateur (admin uniquement)"""
    # Vérifier si l'utilisateur existe déjà
    existing_user = await db.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec ce nom existe déjà"
        )
    
    existing_email = await db.get_user_by_email(user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec cet email existe déjà"
        )
    
    # Créer l'utilisateur
    user = await db.create_user(user_data)
    return User.from_orm(user)

@router.get("/", response_model=List[User])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(check_permissions([UserRole.ADMIN]))
):
    """Lister tous les utilisateurs (admin uniquement)"""
    users = await db.list_users(skip=skip, limit=limit)
    return [User.from_orm(user) for user in users]

@router.get("/me", response_model=User)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Récupérer le profil de l'utilisateur courant"""
    return current_user

@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """Récupérer un utilisateur par ID"""
    # Vérifier les permissions
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission insuffisante"
        )
    
    user = await db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    return User.from_orm(user)

@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """Mettre à jour un utilisateur"""
    # Vérifier les permissions
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission insuffisante"
        )
    
    # Les utilisateurs non-admin ne peuvent pas changer leur rôle
    if current_user.role != UserRole.ADMIN and user_update.role is not None:
        user_update.role = None
    
    updated_user = await db.update_user(user_id, **user_update.dict(exclude_unset=True))
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    return User.from_orm(updated_user)

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(check_permissions([UserRole.ADMIN]))
):
    """Supprimer un utilisateur (admin uniquement)"""
    # Empêcher la suppression de son propre compte
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de supprimer son propre compte"
        )
    
    success = await db.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    return {"message": "Utilisateur supprimé avec succès"}

@router.post("/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: User = Depends(check_permissions([UserRole.ADMIN]))
):
    """Activer un utilisateur (admin uniquement)"""
    user = await db.update_user(user_id, is_active=True)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    return {"message": "Utilisateur activé avec succès"}

@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(check_permissions([UserRole.ADMIN]))
):
    """Désactiver un utilisateur (admin uniquement)"""
    # Empêcher la désactivation de son propre compte
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de désactiver son propre compte"
        )
    
    user = await db.update_user(user_id, is_active=False)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    return {"message": "Utilisateur désactivé avec succès"}

@router.post("/{user_id}/change-password")
async def change_user_password(
    user_id: str,
    new_password: str,
    current_user: User = Depends(get_current_user)
):
    """Changer le mot de passe d'un utilisateur"""
    # Vérifier les permissions
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission insuffisante"
        )
    
    success = await db.change_password(user_id, new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    return {"message": "Mot de passe modifié avec succès"}