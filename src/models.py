from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Document(BaseModel):
    """Modèle pour les documents du système RAG"""
    content: str
    source: str
    embedding: List[float]
    metadata: Dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)

class QueryHistory(BaseModel):
    """Modèle pour l'historique des requêtes"""
    query: str
    response: str
    context_docs: List[str]
    processing_time: float
    cache_hit: bool
    metadata: Dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

class SystemStats(BaseModel):
    """Modèle pour les statistiques du système"""
    total_documents: int
    total_queries: int
    average_processing_time: float
    cache_hit_rate: float
    last_update: datetime = Field(default_factory=datetime.now)

class NodeData(BaseModel):
    """Modèle pour les données d'un nœud Lightning"""
    node_id: str
    alias: str
    capacity: float  # en sats
    channel_count: int
    last_update: datetime
    reputation_score: float
    metadata: Dict = Field(default_factory=dict)

class ChannelData(BaseModel):
    """Modèle pour les données d'un canal Lightning"""
    channel_id: str
    capacity: float  # en sats
    fee_rate: Dict[str, float]  # base_fee et fee_rate
    balance: Dict[str, float]  # local et remote
    age: int  # en jours
    last_update: datetime
    metadata: Dict = Field(default_factory=dict)

class NetworkMetrics(BaseModel):
    """Modèle pour les métriques globales du réseau"""
    total_capacity: float  # en sats
    total_channels: int
    total_nodes: int
    average_fee_rate: float
    last_update: datetime
    metadata: Dict = Field(default_factory=dict)

class NodePerformance(BaseModel):
    """Modèle pour les performances d'un nœud"""
    node_id: str
    uptime: float  # pourcentage
    transaction_count: int
    average_processing_time: float
    last_update: datetime
    metadata: Dict = Field(default_factory=dict)

class SecurityMetrics(BaseModel):
    """Modèle pour les métriques de sécurité"""
    node_id: str
    risk_score: float
    suspicious_activity: List[str]
    last_update: datetime
    metadata: Dict = Field(default_factory=dict)

class ChannelRecommendation(BaseModel):
    """Modèle pour les recommandations de canaux"""
    target_node_id: str
    suggested_capacity: float
    suggested_fee_rate: Dict[str, float]
    confidence_score: float
    last_update: datetime
    metadata: Dict = Field(default_factory=dict) 