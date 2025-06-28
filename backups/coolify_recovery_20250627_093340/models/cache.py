"""
Modèles de cache
Définition des modèles Redis pour api.dazno.de

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 27 mai 2025
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class CacheKey:
    """Classe pour gérer les clés de cache"""
    
    @staticmethod
    def user(user_id: str) -> str:
        """Génère une clé de cache pour un utilisateur"""
        return f"user:{user_id}"
    
    @staticmethod
    def node(node_id: str) -> str:
        """Génère une clé de cache pour un nœud"""
        return f"node:{node_id}"
    
    @staticmethod
    def simulation(simulation_id: str) -> str:
        """Génère une clé de cache pour une simulation"""
        return f"simulation:{simulation_id}"
    
    @staticmethod
    def optimization(optimization_id: str) -> str:
        """Génère une clé de cache pour une optimisation"""
        return f"optimization:{optimization_id}"
    
    @staticmethod
    def automation(automation_id: str) -> str:
        """Génère une clé de cache pour une automatisation"""
        return f"automation:{automation_id}"
    
    @staticmethod
    def file(file_id: str) -> str:
        """Génère une clé de cache pour un fichier"""
        return f"file:{file_id}"
    
    @staticmethod
    def session(session_id: str) -> str:
        """Génère une clé de cache pour une session"""
        return f"session:{session_id}"
    
    @staticmethod
    def rate_limit(ip: str) -> str:
        """Génère une clé de cache pour la limitation de débit"""
        return f"rate_limit:{ip}"
    
    @staticmethod
    def metrics(name: str, labels: Dict[str, str]) -> str:
        """Génère une clé de cache pour une métrique"""
        label_str = ":".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"metric:{name}:{label_str}"

class CacheTTL:
    """Classe pour gérer les durées de vie du cache"""
    
    # Durées de vie par défaut (en secondes)
    USER = 3600  # 1 heure
    NODE = 300  # 5 minutes
    SIMULATION = 1800  # 30 minutes
    OPTIMIZATION = 1800  # 30 minutes
    AUTOMATION = 3600  # 1 heure
    FILE = 86400  # 24 heures
    SESSION = 7200  # 2 heures
    RATE_LIMIT = 60  # 1 minute
    METRICS = 300  # 5 minutes

class CacheModel(BaseModel):
    """Modèle de base pour le cache"""
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserCache(CacheModel):
    """Modèle de cache utilisateur"""
    
    user_id: str
    email: str
    username: str
    permissions: List[str]
    is_active: bool
    is_admin: bool

class NodeCache(CacheModel):
    """Modèle de cache nœud"""
    
    node_id: str
    alias: str
    pubkey: str
    status: str
    capacity: int
    channels: int
    score: float
    metrics: Dict[str, Any]

class SimulationCache(CacheModel):
    """Modèle de cache simulation"""
    
    simulation_id: str
    node_id: str
    status: str
    results: Dict[str, Any]

class OptimizationCache(CacheModel):
    """Modèle de cache optimisation"""
    
    optimization_id: str
    node_id: str
    status: str
    results: Dict[str, Any]

class AutomationCache(CacheModel):
    """Modèle de cache automatisation"""
    
    automation_id: str
    name: str
    type: str
    is_active: bool
    next_run: Optional[datetime]

class FileCache(CacheModel):
    """Modèle de cache fichier"""
    
    file_id: str
    name: str
    type: str
    size: int
    path: str

class SessionCache(CacheModel):
    """Modèle de cache session"""
    
    session_id: str
    user_id: str
    permissions: List[str]
    ip_address: str
    user_agent: str

class RateLimitCache(CacheModel):
    """Modèle de cache limitation de débit"""
    
    ip: str
    count: int
    window_start: datetime
    window_end: datetime

class MetricsCache(CacheModel):
    """Modèle de cache métriques"""
    
    name: str
    value: float
    labels: Dict[str, str]
    timestamp: datetime 