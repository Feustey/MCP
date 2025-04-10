from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class User(BaseModel):
    """Modèle d'utilisateur pour l'authentification"""
    id: str
    username: str
    email: str
    role: str = "user"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True
    permissions: List[str] = []
    settings: Dict[str, Any] = Field(default_factory=dict)

class TokenResponse(BaseModel):
    """Modèle de réponse pour l'authentification JWT"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User

class LoginRequest(BaseModel):
    """Modèle de requête pour la connexion"""
    username: str
    password: str 