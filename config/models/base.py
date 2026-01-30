"""
Modèles de données de base
Définition des modèles Pydantic pour api.dazno.de

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 27 mai 2025
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid

class BaseSchema(BaseModel):
    """Schéma de base pour tous les modèles"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: Optional[str] = None
    
    class Config:
        """Configuration Pydantic"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        validate_by_name = True  # Pydantic v2 (ex allow_population_by_field_name)

class UserBase(BaseSchema):
    """Modèle de base pour les utilisateurs"""
    
    email: str = Field(..., description="Email de l'utilisateur")
    username: str = Field(..., description="Nom d'utilisateur")
    full_name: Optional[str] = Field(None, description="Nom complet")
    is_active: bool = Field(default=True, description="Statut actif")
    is_admin: bool = Field(default=False, description="Statut administrateur")
    permissions: List[str] = Field(default_factory=list, description="Liste des permissions")
    
    @validator("email")
    def validate_email(cls, v):
        """Valide le format de l'email"""
        if not "@" in v:
            raise ValueError("Invalid email format")
        return v.lower()
    
    @validator("username")
    def validate_username(cls, v):
        """Valide le format du nom d'utilisateur"""
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        return v.lower()

class NodeBase(BaseSchema):
    """Modèle de base pour les nœuds Lightning"""
    
    node_id: str = Field(..., description="Identifiant du nœud")
    alias: str = Field(..., description="Alias du nœud")
    pubkey: str = Field(..., description="Clé publique")
    status: str = Field(default="active", description="Statut du nœud")
    capacity: int = Field(..., description="Capacité en satoshis")
    channels: int = Field(..., description="Nombre de canaux")
    score: float = Field(default=0.0, description="Score d'optimisation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées")
    
    @validator("node_id")
    def validate_node_id(cls, v):
        """Valide le format de l'identifiant du nœud"""
        if len(v) < 3:
            raise ValueError("Node ID must be at least 3 characters")
        return v
    
    @validator("pubkey")
    def validate_pubkey(cls, v):
        """Valide le format de la clé publique"""
        if len(v) != 66:
            raise ValueError("Invalid public key format")
        return v
    
    @validator("capacity")
    def validate_capacity(cls, v):
        """Valide la capacité"""
        if v < 0:
            raise ValueError("Capacity must be positive")
        return v
    
    @validator("channels")
    def validate_channels(cls, v):
        """Valide le nombre de canaux"""
        if v < 0:
            raise ValueError("Number of channels must be positive")
        return v
    
    @validator("score")
    def validate_score(cls, v):
        """Valide le score"""
        if not 0 <= v <= 1:
            raise ValueError("Score must be between 0 and 1")
        return v

class SimulationBase(BaseSchema):
    """Modèle de base pour les simulations"""
    
    simulation_id: str = Field(..., description="Identifiant de la simulation")
    node_id: str = Field(..., description="Identifiant du nœud")
    profile: str = Field(..., description="Profil de simulation")
    parameters: Dict[str, Any] = Field(..., description="Paramètres de simulation")
    results: Dict[str, Any] = Field(default_factory=dict, description="Résultats")
    status: str = Field(default="pending", description="Statut de la simulation")
    
    @validator("simulation_id")
    def validate_simulation_id(cls, v):
        """Valide le format de l'identifiant de simulation"""
        if len(v) < 3:
            raise ValueError("Simulation ID must be at least 3 characters")
        return v
    
    @validator("status")
    def validate_status(cls, v):
        """Valide le statut"""
        valid_statuses = ["pending", "running", "completed", "failed"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return v

class OptimizationBase(BaseSchema):
    """Modèle de base pour les optimisations"""
    
    optimization_id: str = Field(..., description="Identifiant de l'optimisation")
    node_id: str = Field(..., description="Identifiant du nœud")
    strategy: str = Field(..., description="Stratégie d'optimisation")
    parameters: Dict[str, Any] = Field(..., description="Paramètres d'optimisation")
    results: Dict[str, Any] = Field(default_factory=dict, description="Résultats")
    status: str = Field(default="pending", description="Statut de l'optimisation")
    
    @validator("optimization_id")
    def validate_optimization_id(cls, v):
        """Valide le format de l'identifiant d'optimisation"""
        if len(v) < 3:
            raise ValueError("Optimization ID must be at least 3 characters")
        return v
    
    @validator("status")
    def validate_status(cls, v):
        """Valide le statut"""
        valid_statuses = ["pending", "running", "completed", "failed"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return v

class AutomationBase(BaseSchema):
    """Modèle de base pour les automations"""
    
    automation_id: str = Field(..., description="Identifiant de l'automatisation")
    name: str = Field(..., description="Nom de l'automatisation")
    type: str = Field(..., description="Type d'automatisation")
    schedule: str = Field(..., description="Planning (cron)")
    parameters: Dict[str, Any] = Field(..., description="Paramètres")
    is_active: bool = Field(default=True, description="Statut actif")
    last_run: Optional[datetime] = Field(None, description="Dernière exécution")
    
    @validator("automation_id")
    def validate_automation_id(cls, v):
        """Valide le format de l'identifiant d'automatisation"""
        if len(v) < 3:
            raise ValueError("Automation ID must be at least 3 characters")
        return v
    
    @validator("schedule")
    def validate_schedule(cls, v):
        """Valide le format du planning cron"""
        # Validation basique du format cron
        parts = v.split()
        if len(parts) != 5:
            raise ValueError("Invalid cron schedule format")
        return v

class FileBase(BaseSchema):
    """Modèle de base pour les fichiers"""
    
    file_id: str = Field(..., description="Identifiant du fichier")
    name: str = Field(..., description="Nom du fichier")
    type: str = Field(..., description="Type MIME")
    size: int = Field(..., description="Taille en bytes")
    path: str = Field(..., description="Chemin du fichier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées")
    
    @validator("file_id")
    def validate_file_id(cls, v):
        """Valide le format de l'identifiant de fichier"""
        if len(v) < 3:
            raise ValueError("File ID must be at least 3 characters")
        return v
    
    @validator("size")
    def validate_size(cls, v):
        """Valide la taille"""
        if v < 0:
            raise ValueError("Size must be positive")
        return v 