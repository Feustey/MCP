from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Document(BaseModel):
    """Modèle pour les documents source"""
    content: str
    source: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: List[float]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class QueryHistory(BaseModel):
    """Modèle pour l'historique des requêtes"""
    query: str
    response: str
    context_docs: List[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time: float
    cache_hit: bool = False

class SystemStats(BaseModel):
    """Modèle pour les statistiques du système"""
    total_documents: int = 0
    total_queries: int = 0
    average_processing_time: float = 0.0
    cache_hit_rate: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow) 