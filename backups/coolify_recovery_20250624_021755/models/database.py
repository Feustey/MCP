"""
Modèles de base de données
Définition des modèles MongoDB pour api.dazno.de

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 27 mai 2025
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel, Field
from .base import UserBase, NodeBase, SimulationBase, OptimizationBase, AutomationBase, FileBase

class PyObjectId(ObjectId):
    """Classe pour gérer les ObjectId MongoDB"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("ObjectId invalide")
        return ObjectId(v)
    
    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class MongoBaseModel(BaseModel):
    """Modèle de base pour MongoDB"""
    
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    
    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
        allow_population_by_field_name = True

# Modèles MongoDB
class User(MongoBaseModel, UserBase):
    """Modèle utilisateur MongoDB"""
    
    password_hash: str = Field(..., description="Hash du mot de passe")
    last_login: Optional[datetime] = Field(None, description="Dernière connexion")
    failed_attempts: int = Field(default=0, description="Tentatives échouées")
    locked_until: Optional[datetime] = Field(None, description="Verrouillé jusqu'à")
    
    class Config:
        collection = "users"
        indexes = [
            {"fields": ["email"], "unique": True},
            {"fields": ["username"], "unique": True}
        ]

class Node(MongoBaseModel, NodeBase):
    """Modèle nœud MongoDB"""
    
    last_update: datetime = Field(default_factory=datetime.utcnow, description="Dernière mise à jour")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Métriques")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Paramètres")
    
    class Config:
        collection = "nodes"
        indexes = [
            {"fields": ["node_id"], "unique": True},
            {"fields": ["pubkey"], "unique": True},
            {"fields": ["status"]},
            {"fields": ["score"]}
        ]

class Simulation(MongoBaseModel, SimulationBase):
    """Modèle simulation MongoDB"""
    
    start_time: Optional[datetime] = Field(None, description="Heure de début")
    end_time: Optional[datetime] = Field(None, description="Heure de fin")
    duration: Optional[float] = Field(None, description="Durée en secondes")
    error: Optional[str] = Field(None, description="Message d'erreur")
    
    class Config:
        collection = "simulations"
        indexes = [
            {"fields": ["simulation_id"], "unique": True},
            {"fields": ["node_id"]},
            {"fields": ["status"]},
            {"fields": ["start_time"]}
        ]

class Optimization(MongoBaseModel, OptimizationBase):
    """Modèle optimisation MongoDB"""
    
    start_time: Optional[datetime] = Field(None, description="Heure de début")
    end_time: Optional[datetime] = Field(None, description="Heure de fin")
    duration: Optional[float] = Field(None, description="Durée en secondes")
    error: Optional[str] = Field(None, description="Message d'erreur")
    
    class Config:
        collection = "optimizations"
        indexes = [
            {"fields": ["optimization_id"], "unique": True},
            {"fields": ["node_id"]},
            {"fields": ["status"]},
            {"fields": ["start_time"]}
        ]

class Automation(MongoBaseModel, AutomationBase):
    """Modèle automatisation MongoDB"""
    
    next_run: Optional[datetime] = Field(None, description="Prochaine exécution")
    last_success: Optional[datetime] = Field(None, description="Dernier succès")
    last_error: Optional[str] = Field(None, description="Dernière erreur")
    error_count: int = Field(default=0, description="Nombre d'erreurs")
    
    class Config:
        collection = "automations"
        indexes = [
            {"fields": ["automation_id"], "unique": True},
            {"fields": ["type"]},
            {"fields": ["is_active"]},
            {"fields": ["next_run"]}
        ]

class File(MongoBaseModel, FileBase):
    """Modèle fichier MongoDB"""
    
    hash: str = Field(..., description="Hash du fichier")
    uploaded_by: str = Field(..., description="Uploadé par")
    download_count: int = Field(default=0, description="Nombre de téléchargements")
    last_download: Optional[datetime] = Field(None, description="Dernier téléchargement")
    
    class Config:
        collection = "files"
        indexes = [
            {"fields": ["file_id"], "unique": True},
            {"fields": ["hash"]},
            {"fields": ["type"]},
            {"fields": ["uploaded_by"]}
        ]

# Modèles de journalisation
class LogEntry(MongoBaseModel):
    """Modèle entrée de journal MongoDB"""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Horodatage")
    level: str = Field(..., description="Niveau de log")
    message: str = Field(..., description="Message")
    module: str = Field(..., description="Module")
    function: str = Field(..., description="Fonction")
    line: int = Field(..., description="Ligne")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Informations supplémentaires")
    
    class Config:
        collection = "logs"
        indexes = [
            {"fields": ["timestamp"]},
            {"fields": ["level"]},
            {"fields": ["module"]}
        ]

class AuditLog(MongoBaseModel):
    """Modèle journal d'audit MongoDB"""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Horodatage")
    user_id: str = Field(..., description="ID utilisateur")
    action: str = Field(..., description="Action")
    resource_type: str = Field(..., description="Type de ressource")
    resource_id: str = Field(..., description="ID ressource")
    details: Dict[str, Any] = Field(default_factory=dict, description="Détails")
    ip_address: str = Field(..., description="Adresse IP")
    
    class Config:
        collection = "audit_logs"
        indexes = [
            {"fields": ["timestamp"]},
            {"fields": ["user_id"]},
            {"fields": ["action"]},
            {"fields": ["resource_type", "resource_id"]}
        ]

# Modèles de métriques
class Metric(MongoBaseModel):
    """Modèle métrique MongoDB"""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Horodatage")
    name: str = Field(..., description="Nom")
    value: float = Field(..., description="Valeur")
    labels: Dict[str, str] = Field(default_factory=dict, description="Labels")
    
    class Config:
        collection = "metrics"
        indexes = [
            {"fields": ["timestamp"]},
            {"fields": ["name"]},
            {"fields": ["labels"]}
        ]

class SystemMetric(MongoBaseModel):
    """Modèle métrique système MongoDB"""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Horodatage")
    cpu_usage: float = Field(..., description="Utilisation CPU")
    memory_usage: float = Field(..., description="Utilisation mémoire")
    disk_usage: float = Field(..., description="Utilisation disque")
    network_in: float = Field(..., description="Trafic réseau entrant")
    network_out: float = Field(..., description="Trafic réseau sortant")
    
    class Config:
        collection = "system_metrics"
        indexes = [
            {"fields": ["timestamp"]}
        ] 