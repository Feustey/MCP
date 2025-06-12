"""
Modèles Pydantic pour l'API MCP
Version adaptée de mcp-light avec extensions pour le système MCP complet
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum

# === Enums pour les types de données ===

class UserContext(str, Enum):
    """Niveau d'expertise de l'utilisateur"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"

class UserGoal(str, Enum):
    """Objectifs d'optimisation"""
    ROUTING_REVENUE = "routing_revenue"
    CONNECTIVITY = "connectivity"
    LIQUIDITY = "liquidity"
    RELIABILITY = "reliability"
    COST_OPTIMIZATION = "cost_optimization"

class RecommendationType(str, Enum):
    """Types de recommandations"""
    FEE_ADJUSTMENT = "fee_adjustment"
    CHANNEL_MANAGEMENT = "channel_management"
    LIQUIDITY_MANAGEMENT = "liquidity_management"
    NETWORK_TOPOLOGY = "network_topology"
    SECURITY = "security"

class ActionPriority(str, Enum):
    """Priorités des actions"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class ActionDifficulty(str, Enum):
    """Niveaux de difficulté"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class ActionTimeframe(str, Enum):
    """Délais d'exécution"""
    IMMEDIATE = "immediate"
    SHORT_TERM = "1-2 weeks"
    MEDIUM_TERM = "1 month"
    LONG_TERM = "3+ months"

# === Modèles de base ===

class NodeInfo(BaseModel):
    """Informations de base d'un nœud Lightning"""
    pubkey: str = Field(..., description="Clé publique du nœud")
    alias: Optional[str] = Field(None, description="Alias du nœud")
    color: Optional[str] = Field(None, description="Couleur du nœud")
    features: Optional[Dict[str, Any]] = Field(default_factory=dict)
    addresses: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    last_update: Optional[datetime] = None

class ChannelInfo(BaseModel):
    """Informations sur un canal"""
    channel_id: str
    capacity: int
    local_balance: Optional[int] = None
    remote_balance: Optional[int] = None
    fee_rate: Optional[int] = None
    base_fee: Optional[int] = None
    peer_pubkey: Optional[str] = None
    peer_alias: Optional[str] = None
    active: Optional[bool] = True

class NetworkMetrics(BaseModel):
    """Métriques réseau d'un nœud"""
    total_channels: int = 0
    total_capacity: int = 0
    average_channel_size: Optional[float] = None
    centrality_score: Optional[float] = None
    connectivity_score: Optional[float] = None
    routing_revenue_24h: Optional[int] = None
    routing_volume_24h: Optional[int] = None

# === Modèles de recommandations ===

class Recommendation(BaseModel):
    """Recommandation technique de base"""
    type: RecommendationType
    category: str = Field(..., description="Catégorie (connectivity, revenue, operational)")
    action: str = Field(..., description="Action recommandée")
    reason: str = Field(..., description="Justification de la recommandation")
    priority: ActionPriority = ActionPriority.MEDIUM
    estimated_impact: Optional[str] = None
    
    # Champs spécifiques selon le type
    channel_id: Optional[str] = None
    target_nodes: Optional[List[str]] = Field(default_factory=list)
    current_value: Optional[Union[int, float]] = None
    suggested_value: Optional[Union[int, float]] = None
    channels_affected: Optional[List[str]] = Field(default_factory=list)
    amount_suggestion: Optional[int] = None
    direction: Optional[str] = None  # inbound/outbound

class PriorityAction(BaseModel):
    """Action prioritaire générée par IA"""
    priority: int = Field(..., ge=1, le=10, description="Priorité (1=max)")
    action: str = Field(..., description="Action concrète à effectuer")
    reasoning: str = Field(..., description="Justification basée sur les données")
    impact: str = Field(..., description="Impact attendu quantifiable")
    difficulty: ActionDifficulty
    timeframe: ActionTimeframe
    command: Optional[str] = Field(None, description="Commande CLI/API si applicable")
    estimated_cost: Optional[float] = Field(None, description="Coût estimé en sats")
    success_metrics: Optional[List[str]] = Field(default_factory=list)

# === Modèles de requêtes ===

class NodeAnalysisRequest(BaseModel):
    """Requête d'analyse de nœud"""
    pubkey: str = Field(..., min_length=66, max_length=66)
    include_historical: bool = Field(default=True)
    include_recommendations: bool = Field(default=True)
    include_network_analysis: bool = Field(default=False)

class PriorityActionsRequest(BaseModel):
    """Requête d'actions prioritaires"""
    context: UserContext = UserContext.INTERMEDIATE
    goals: List[UserGoal] = Field(default_factory=lambda: [UserGoal.ROUTING_REVENUE])
    max_actions: int = Field(default=5, ge=1, le=10)
    budget_limit: Optional[int] = Field(None, description="Budget max en sats")
    timeframe_preference: Optional[ActionTimeframe] = None

class BulkAnalysisRequest(BaseModel):
    """Requête d'analyse en masse"""
    pubkeys: List[str] = Field(..., max_items=50)
    analysis_types: List[str] = Field(default_factory=lambda: ["basic"])
    use_cache: bool = Field(default=True)

# === Modèles de réponses ===

class NodeInfoResponse(BaseModel):
    """Réponse d'informations de nœud"""
    pubkey: str
    node_info: NodeInfo
    metrics: NetworkMetrics
    channels: Optional[List[ChannelInfo]] = Field(default_factory=list)
    network_position: Optional[Dict[str, Any]] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = "mcp_enhanced"
    cache_hit: bool = False

class RecommendationsResponse(BaseModel):
    """Réponse de recommandations"""
    pubkey: str
    recommendations: List[Recommendation]
    total_count: int = Field(..., description="Nombre total de recommandations")
    by_category: Dict[str, int] = Field(default_factory=dict)
    by_priority: Dict[str, int] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = "mcp_analyzer"

class PriorityActionsResponse(BaseModel):
    """Réponse d'actions prioritaires"""
    pubkey: str
    priority_actions: List[PriorityAction]
    openai_analysis: str
    key_metrics: List[str] = Field(default_factory=list)
    total_estimated_cost: Optional[float] = None
    expected_roi: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    model_used: str = "gpt-4o-mini"
    
    @validator('total_estimated_cost', pre=True, always=True)
    def calculate_total_cost(cls, v, values):
        """Calcule le coût total des actions"""
        if 'priority_actions' in values:
            total = sum(
                action.estimated_cost or 0 
                for action in values['priority_actions']
            )
            return total if total > 0 else None
        return v

class HealthResponse(BaseModel):
    """Réponse de health check"""
    status: str = Field(..., description="healthy/degraded/unhealthy")
    services: Dict[str, str] = Field(default_factory=dict)
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    uptime_seconds: Optional[int] = None
    cache_stats: Optional[Dict[str, Any]] = Field(default_factory=dict)

class BulkAnalysisResponse(BaseModel):
    """Réponse d'analyse en masse"""
    total_analyzed: int
    successful: int
    failed: int
    results: List[NodeInfoResponse]
    errors: List[Dict[str, str]] = Field(default_factory=list)
    processing_time_seconds: float
    generated_at: datetime = Field(default_factory=datetime.utcnow)

# === Modèles d'erreur ===

class ErrorResponse(BaseModel):
    """Réponse d'erreur standardisée"""
    error: str
    error_code: str
    details: Optional[Dict[str, Any]] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None

class ValidationError(BaseModel):
    """Erreur de validation"""
    field: str
    message: str
    invalid_value: Any

# === Modèles de configuration ===

class OptimizationConfig(BaseModel):
    """Configuration d'optimisation"""
    enabled_strategies: List[str] = Field(default_factory=list)
    risk_tolerance: str = Field(default="medium")  # low/medium/high
    target_revenue_increase: Optional[float] = None  # pourcentage
    max_fee_adjustment: Optional[float] = Field(default=50.0)  # pourcentage
    min_channel_size: Optional[int] = Field(default=1000000)  # sats
    exclude_nodes: List[str] = Field(default_factory=list)

class CacheConfig(BaseModel):
    """Configuration du cache"""
    ttl_node_info: int = 300
    ttl_recommendations: int = 600
    ttl_openai_responses: int = 1800
    namespace: str = "mcp"
    max_keys: int = 10000

# === Modèles de métriques et monitoring ===

class PerformanceMetrics(BaseModel):
    """Métriques de performance de l'API"""
    request_count: int = 0
    average_response_time: float = 0.0
    cache_hit_ratio: float = 0.0
    error_rate: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class SystemStatus(BaseModel):
    """État du système"""
    api_status: str
    database_status: str
    cache_status: str
    external_apis: Dict[str, str] = Field(default_factory=dict)
    resource_usage: Dict[str, float] = Field(default_factory=dict)
    last_check: datetime = Field(default_factory=datetime.utcnow) 