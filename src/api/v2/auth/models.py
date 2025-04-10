from pydantic import BaseModel, Field, validator, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid

class TokenType(str, Enum):
    """Types de jetons disponibles"""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"

class TokenStatus(str, Enum):
    """Statuts possibles d'un jeton"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"

class PermissionScope(str, Enum):
    """Scopes de permission disponibles"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    ANALYTICS = "analytics"
    PREDICTIONS = "predictions"
    SIMULATIONS = "simulations"
    MONITORING = "monitoring"
    BALANCING = "balancing"
    LIQUIDITY = "liquidity"

class User(BaseModel):
    """Modèle utilisateur"""
    id: str = Field(..., description="Identifiant unique de l'utilisateur")
    username: str = Field(..., description="Nom d'utilisateur")
    email: EmailStr = Field(..., description="Adresse email")
    full_name: Optional[str] = Field(None, description="Nom complet")
    is_active: bool = Field(True, description="Statut actif/inactif")
    is_admin: bool = Field(False, description="Statut administrateur")
    created_at: datetime = Field(..., description="Date de création")
    last_login: Optional[datetime] = Field(None, description="Dernière connexion")
    scopes: List[PermissionScope] = Field(default_factory=list, description="Scopes de permission")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées supplémentaires")

class UserCreate(BaseModel):
    """Modèle pour la création d'utilisateur"""
    username: str = Field(..., description="Nom d'utilisateur")
    email: EmailStr = Field(..., description="Adresse email")
    password: str = Field(..., description="Mot de passe")
    full_name: Optional[str] = Field(None, description="Nom complet")
    scopes: Optional[List[PermissionScope]] = Field(None, description="Scopes de permission")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Métadonnées supplémentaires")

class UserUpdate(BaseModel):
    """Modèle pour la mise à jour d'utilisateur"""
    username: Optional[str] = Field(None, description="Nom d'utilisateur")
    email: Optional[EmailStr] = Field(None, description="Adresse email")
    password: Optional[str] = Field(None, description="Mot de passe")
    full_name: Optional[str] = Field(None, description="Nom complet")
    is_active: Optional[bool] = Field(None, description="Statut actif/inactif")
    is_admin: Optional[bool] = Field(None, description="Statut administrateur")
    scopes: Optional[List[PermissionScope]] = Field(None, description="Scopes de permission")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Métadonnées supplémentaires")

class Token(BaseModel):
    """Modèle de jeton"""
    id: str = Field(..., description="Identifiant unique du jeton")
    user_id: str = Field(..., description="ID de l'utilisateur")
    type: TokenType = Field(..., description="Type de jeton")
    token: str = Field(..., description="Valeur du jeton")
    status: TokenStatus = Field(..., description="Statut du jeton")
    scopes: List[PermissionScope] = Field(..., description="Scopes de permission")
    created_at: datetime = Field(..., description="Date de création")
    expires_at: datetime = Field(..., description="Date d'expiration")
    last_used: Optional[datetime] = Field(None, description="Dernière utilisation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées supplémentaires")

class TokenCreate(BaseModel):
    """Modèle pour la création de jeton"""
    user_id: str = Field(..., description="ID de l'utilisateur")
    type: TokenType = Field(..., description="Type de jeton")
    scopes: List[PermissionScope] = Field(..., description="Scopes de permission")
    expires_in: Optional[int] = Field(None, description="Durée de validité en secondes")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Métadonnées supplémentaires")

class TokenResponse(BaseModel):
    """Modèle de réponse de jeton"""
    access_token: str = Field(..., description="Jeton d'accès")
    token_type: str = Field("bearer", description="Type de jeton")
    expires_in: int = Field(..., description="Durée de validité en secondes")
    refresh_token: Optional[str] = Field(None, description="Jeton de rafraîchissement")
    scopes: List[PermissionScope] = Field(..., description="Scopes de permission")

class LoginRequest(BaseModel):
    """Modèle de requête de connexion"""
    username: str = Field(..., description="Nom d'utilisateur")
    password: str = Field(..., description="Mot de passe")
    scopes: Optional[List[PermissionScope]] = Field(None, description="Scopes de permission demandés")

class RefreshRequest(BaseModel):
    """Modèle de requête de rafraîchissement"""
    refresh_token: str = Field(..., description="Jeton de rafraîchissement")
    scopes: Optional[List[PermissionScope]] = Field(None, description="Scopes de permission demandés")

class APIKey(BaseModel):
    """Modèle de clé API"""
    id: str = Field(..., description="Identifiant unique de la clé API")
    user_id: str = Field(..., description="ID de l'utilisateur")
    name: str = Field(..., description="Nom de la clé")
    key: str = Field(..., description="Valeur de la clé")
    status: TokenStatus = Field(..., description="Statut de la clé")
    scopes: List[PermissionScope] = Field(..., description="Scopes de permission")
    created_at: datetime = Field(..., description="Date de création")
    expires_at: Optional[datetime] = Field(None, description="Date d'expiration")
    last_used: Optional[datetime] = Field(None, description="Dernière utilisation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées supplémentaires")

class APIKeyCreate(BaseModel):
    """Modèle pour la création de clé API"""
    name: str = Field(..., description="Nom de la clé")
    scopes: List[PermissionScope] = Field(..., description="Scopes de permission")
    expires_in: Optional[int] = Field(None, description="Durée de validité en secondes")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Métadonnées supplémentaires")

class APIKeyResponse(BaseModel):
    """Modèle de réponse de clé API"""
    id: str = Field(..., description="Identifiant unique de la clé API")
    name: str = Field(..., description="Nom de la clé")
    key: str = Field(..., description="Valeur de la clé")
    scopes: List[PermissionScope] = Field(..., description="Scopes de permission")
    created_at: datetime = Field(..., description="Date de création")
    expires_at: Optional[datetime] = Field(None, description="Date d'expiration")

class TokenFilter(BaseModel):
    """Filtres pour les jetons"""
    user_id: Optional[str] = Field(None, description="ID de l'utilisateur")
    type: Optional[TokenType] = Field(None, description="Type de jeton")
    status: Optional[TokenStatus] = Field(None, description="Statut du jeton")
    scope: Optional[PermissionScope] = Field(None, description="Scope de permission")
    limit: int = Field(100, ge=1, le=1000, description="Nombre maximum de résultats")

    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('La limite doit être comprise entre 1 et 1000')
        return v

# Exemples de configuration
User.schema_extra = {
    "example": {
        "id": "user-123",
        "username": "johndoe",
        "email": "john.doe@example.com",
        "full_name": "John Doe",
        "is_active": True,
        "is_admin": False,
        "created_at": "2024-02-20T10:00:00Z",
        "last_login": "2024-02-21T15:30:00Z",
        "scopes": [PermissionScope.READ, PermissionScope.WRITE],
        "metadata": {
            "department": "Engineering",
            "role": "Developer"
        }
    }
}

Token.schema_extra = {
    "example": {
        "id": "token-123",
        "user_id": "user-123",
        "type": TokenType.ACCESS,
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "status": TokenStatus.ACTIVE,
        "scopes": [PermissionScope.READ, PermissionScope.WRITE],
        "created_at": "2024-02-21T15:30:00Z",
        "expires_at": "2024-02-21T16:30:00Z",
        "last_used": "2024-02-21T15:45:00Z",
        "metadata": {
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0..."
        }
    }
}

APIKey.schema_extra = {
    "example": {
        "id": "apikey-123",
        "user_id": "user-123",
        "name": "Production API Key",
        "key": "lk_1234567890abcdef",
        "status": TokenStatus.ACTIVE,
        "scopes": [PermissionScope.READ, PermissionScope.WRITE, PermissionScope.ANALYTICS],
        "created_at": "2024-02-20T10:00:00Z",
        "expires_at": "2025-02-20T10:00:00Z",
        "last_used": "2024-02-21T15:30:00Z",
        "metadata": {
            "environment": "production",
            "description": "API key for production environment"
        }
    }
} 