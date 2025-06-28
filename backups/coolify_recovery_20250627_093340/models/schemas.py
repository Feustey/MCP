"""
Schémas de requêtes et réponses
Définition des modèles Pydantic pour les entrées/sorties d'API

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 27 mai 2025
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from .base import UserBase, NodeBase, SimulationBase, OptimizationBase, AutomationBase, FileBase

# Schémas de requêtes
class UserCreate(BaseModel):
    """Schéma de création d'utilisateur"""
    
    email: str = Field(..., description="Email de l'utilisateur")
    username: str = Field(..., description="Nom d'utilisateur")
    password: str = Field(..., description="Mot de passe")
    full_name: Optional[str] = Field(None, description="Nom complet")
    
    @validator("password")
    def validate_password(cls, v):
        """Valide le mot de passe"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

class UserUpdate(BaseModel):
    """Schéma de mise à jour d'utilisateur"""
    
    email: Optional[str] = Field(None, description="Email de l'utilisateur")
    username: Optional[str] = Field(None, description="Nom d'utilisateur")
    full_name: Optional[str] = Field(None, description="Nom complet")
    is_active: Optional[bool] = Field(None, description="Statut actif")
    is_admin: Optional[bool] = Field(None, description="Statut administrateur")
    permissions: Optional[List[str]] = Field(None, description="Liste des permissions")

class NodeCreate(BaseModel):
    """Schéma de création de nœud"""
    
    node_id: str = Field(..., description="Identifiant du nœud")
    alias: str = Field(..., description="Alias du nœud")
    pubkey: str = Field(..., description="Clé publique")
    capacity: int = Field(..., description="Capacité en satoshis")
    channels: int = Field(..., description="Nombre de canaux")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Métadonnées")

class NodeUpdate(BaseModel):
    """Schéma de mise à jour de nœud"""
    
    alias: Optional[str] = Field(None, description="Alias du nœud")
    status: Optional[str] = Field(None, description="Statut du nœud")
    capacity: Optional[int] = Field(None, description="Capacité en satoshis")
    channels: Optional[int] = Field(None, description="Nombre de canaux")
    score: Optional[float] = Field(None, description="Score d'optimisation")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Métadonnées")

class SimulationCreate(BaseModel):
    """Schéma de création de simulation"""
    
    node_id: str = Field(..., description="Identifiant du nœud")
    profile: str = Field(..., description="Profil de simulation")
    parameters: Dict[str, Any] = Field(..., description="Paramètres de simulation")

class SimulationUpdate(BaseModel):
    """Schéma de mise à jour de simulation"""
    
    status: Optional[str] = Field(None, description="Statut de la simulation")
    results: Optional[Dict[str, Any]] = Field(None, description="Résultats")

class OptimizationCreate(BaseModel):
    """Schéma de création d'optimisation"""
    
    node_id: str = Field(..., description="Identifiant du nœud")
    strategy: str = Field(..., description="Stratégie d'optimisation")
    parameters: Dict[str, Any] = Field(..., description="Paramètres d'optimisation")

class OptimizationUpdate(BaseModel):
    """Schéma de mise à jour d'optimisation"""
    
    status: Optional[str] = Field(None, description="Statut de l'optimisation")
    results: Optional[Dict[str, Any]] = Field(None, description="Résultats")

class AutomationCreate(BaseModel):
    """Schéma de création d'automatisation"""
    
    name: str = Field(..., description="Nom de l'automatisation")
    type: str = Field(..., description="Type d'automatisation")
    schedule: str = Field(..., description="Planning (cron)")
    parameters: Dict[str, Any] = Field(..., description="Paramètres")

class AutomationUpdate(BaseModel):
    """Schéma de mise à jour d'automatisation"""
    
    name: Optional[str] = Field(None, description="Nom de l'automatisation")
    schedule: Optional[str] = Field(None, description="Planning (cron)")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Paramètres")
    is_active: Optional[bool] = Field(None, description="Statut actif")

# Schémas de réponses
class UserResponse(UserBase):
    """Schéma de réponse utilisateur"""
    pass

class NodeResponse(NodeBase):
    """Schéma de réponse nœud"""
    pass

class SimulationResponse(SimulationBase):
    """Schéma de réponse simulation"""
    pass

class OptimizationResponse(OptimizationBase):
    """Schéma de réponse optimisation"""
    pass

class AutomationResponse(AutomationBase):
    """Schéma de réponse automatisation"""
    pass

class FileResponse(FileBase):
    """Schéma de réponse fichier"""
    pass

# Schémas de pagination
class PaginationParams(BaseModel):
    """Paramètres de pagination"""
    
    page: int = Field(default=1, ge=1, description="Numéro de page")
    size: int = Field(default=10, ge=1, le=100, description="Taille de page")
    sort_by: Optional[str] = Field(None, description="Champ de tri")
    sort_order: Optional[str] = Field(None, description="Ordre de tri (asc/desc)")

class PaginatedResponse(BaseModel):
    """Réponse paginée"""
    
    items: List[Any] = Field(..., description="Liste des éléments")
    total: int = Field(..., description="Nombre total d'éléments")
    page: int = Field(..., description="Page courante")
    size: int = Field(..., description="Taille de page")
    pages: int = Field(..., description="Nombre total de pages")

# Schémas d'authentification
class Token(BaseModel):
    """Schéma de token"""
    
    access_token: str = Field(..., description="Token d'accès")
    token_type: str = Field(default="bearer", description="Type de token")
    expires_at: datetime = Field(..., description="Date d'expiration")

class TokenData(BaseModel):
    """Données du token"""
    
    username: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)

# Schémas d'erreur
class ErrorResponse(BaseModel):
    """Schéma de réponse d'erreur"""
    
    code: str = Field(..., description="Code d'erreur")
    message: str = Field(..., description="Message d'erreur")
    details: Optional[Dict[str, Any]] = Field(None, description="Détails de l'erreur") 