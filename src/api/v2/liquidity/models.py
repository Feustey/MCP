from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime, timedelta
import uuid

class LiquidityMetricType(str, Enum):
    """Types de métriques de liquidité"""
    CHANNEL_BALANCE = "channel_balance"
    NODE_BALANCE = "node_balance"
    PAYMENT_SUCCESS = "payment_success"
    ROUTING_SUCCESS = "routing_success"
    FEE_RATE = "fee_rate"
    CAPACITY_UTILIZATION = "capacity_utilization"
    CHANNEL_HEALTH = "channel_health"
    NETWORK_HEALTH = "network_health"

class LiquidityThresholdType(str, Enum):
    """Types de seuils de liquidité"""
    MIN_BALANCE = "min_balance"
    MAX_BALANCE = "max_balance"
    MIN_RATIO = "min_ratio"
    MAX_RATIO = "max_ratio"
    MIN_SUCCESS_RATE = "min_success_rate"
    MAX_FEE_RATE = "max_fee_rate"
    MIN_CAPACITY = "min_capacity"
    MAX_CAPACITY = "max_capacity"

class LiquidityAlertSeverity(str, Enum):
    """Niveaux de sévérité des alertes de liquidité"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class LiquidityMetric(BaseModel):
    """Modèle de métrique de liquidité"""
    id: Optional[str] = None
    name: str
    type: LiquidityMetricType
    description: str
    value: float
    unit: str
    timestamp: datetime
    channel_id: Optional[str] = None
    node_id: Optional[str] = None
    tags: Dict[str, str] = {}
    
    class Config:
        schema_extra = {
            "example": {
                "id": "metric-12345",
                "name": "Balance du canal",
                "type": "channel_balance",
                "description": "Balance actuelle du canal en satoshis",
                "value": 1000000,
                "unit": "sats",
                "timestamp": "2023-07-01T12:34:56Z",
                "channel_id": "chan-12345",
                "tags": {
                    "direction": "outbound",
                    "peer": "node-67890"
                }
            }
        }

class LiquidityThreshold(BaseModel):
    """Modèle de seuil de liquidité"""
    id: Optional[str] = None
    name: str
    type: LiquidityThresholdType
    metric_type: LiquidityMetricType
    value: float
    severity: LiquidityAlertSeverity
    description: str
    is_active: bool = True
    channel_id: Optional[str] = None
    node_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "threshold-12345",
                "name": "Seuil minimum de balance",
                "type": "min_balance",
                "metric_type": "channel_balance",
                "value": 500000,
                "severity": "warning",
                "description": "Alerte si la balance du canal descend en dessous de 500,000 sats",
                "is_active": True,
                "channel_id": "chan-12345",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-07-01T12:34:56Z"
            }
        }

class LiquidityThresholdCreate(BaseModel):
    """Modèle pour la création d'un seuil de liquidité"""
    name: str
    type: LiquidityThresholdType
    metric_type: LiquidityMetricType
    value: float
    severity: LiquidityAlertSeverity
    description: str
    is_active: bool = True
    channel_id: Optional[str] = None
    node_id: Optional[str] = None

class LiquidityThresholdUpdate(BaseModel):
    """Modèle pour la mise à jour d'un seuil de liquidité"""
    name: Optional[str] = None
    value: Optional[float] = None
    severity: Optional[LiquidityAlertSeverity] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class LiquidityAlert(BaseModel):
    """Modèle d'alerte de liquidité"""
    id: Optional[str] = None
    threshold_id: str
    metric_id: str
    severity: LiquidityAlertSeverity
    message: str
    value: float
    threshold_value: float
    timestamp: datetime
    is_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    channel_id: Optional[str] = None
    node_id: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "alert-12345",
                "threshold_id": "threshold-12345",
                "metric_id": "metric-12345",
                "severity": "warning",
                "message": "La balance du canal est inférieure au seuil minimum",
                "value": 450000,
                "threshold_value": 500000,
                "timestamp": "2023-07-01T12:34:56Z",
                "is_acknowledged": False,
                "channel_id": "chan-12345"
            }
        }

class LiquidityAnalysis(BaseModel):
    """Modèle d'analyse de liquidité"""
    id: Optional[str] = None
    channel_id: Optional[str] = None
    node_id: Optional[str] = None
    timestamp: datetime
    metrics: Dict[str, float]
    score: float
    recommendations: List[str]
    issues: List[str]
    created_at: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "analysis-12345",
                "channel_id": "chan-12345",
                "timestamp": "2023-07-01T12:34:56Z",
                "metrics": {
                    "balance_ratio": 0.75,
                    "payment_success_rate": 0.98,
                    "fee_rate": 0.0001
                },
                "score": 85.5,
                "recommendations": [
                    "Augmenter la balance du canal de 200,000 sats",
                    "Optimiser les frais de routage"
                ],
                "issues": [
                    "Balance déséquilibrée",
                    "Taux de succès des paiements légèrement bas"
                ],
                "created_at": "2023-07-01T12:34:56Z"
            }
        }

class LiquidityAnalysisRequest(BaseModel):
    """Modèle pour la demande d'analyse de liquidité"""
    channel_id: Optional[str] = None
    node_id: Optional[str] = None
    include_recommendations: bool = True
    include_issues: bool = True

class LiquidityMetricFilter(BaseModel):
    """Filtres pour les métriques de liquidité"""
    type: Optional[LiquidityMetricType] = None
    channel_id: Optional[str] = None
    node_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100
    
    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('La limite doit être entre 1 et 1000')
        return v

class LiquidityAlertFilter(BaseModel):
    """Filtres pour les alertes de liquidité"""
    severity: Optional[LiquidityAlertSeverity] = None
    is_acknowledged: Optional[bool] = None
    channel_id: Optional[str] = None
    node_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100
    
    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('La limite doit être entre 1 et 1000')
        return v 