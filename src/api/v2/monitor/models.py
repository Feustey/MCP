from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional, Any, Union, Set
from enum import Enum
from datetime import datetime, timedelta

class AlertSeverity(str, Enum):
    """Niveau de sévérité d'une alerte"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertType(str, Enum):
    """Type d'alerte"""
    CHANNEL_BALANCE = "channel_balance"
    NODE_BALANCE = "node_balance"
    PAYMENT_FAILURE = "payment_failure"
    PAYMENT_SUCCESS = "payment_success"
    ROUTING_FAILURE = "routing_failure"
    PEER_CONNECTION = "peer_connection"
    BLOCKCHAIN_SYNC = "blockchain_sync"
    CUSTOM = "custom"

class NotificationChannel(str, Enum):
    """Canal de notification"""
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    WEBHOOK = "webhook"
    IN_APP = "in_app"
    TELEGRAM = "telegram"

class MetricType(str, Enum):
    """Type de métrique"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"

class MetricScope(str, Enum):
    """Portée de la métrique"""
    NODE = "node"
    CHANNEL = "channel"
    NETWORK = "network"
    PAYMENT = "payment"
    SYSTEM = "system"

class TimeRange(str, Enum):
    LAST_HOUR = "1h"
    LAST_DAY = "24h"
    LAST_WEEK = "1w"
    LAST_MONTH = "1m"
    CUSTOM = "custom"

class Condition(BaseModel):
    """Condition pour déclencher une alerte"""
    metric: str
    operator: str
    threshold: float
    duration: Optional[str] = None

class AlertConfig(BaseModel):
    """Configuration d'une alerte"""
    id: Optional[str] = None
    name: str
    description: str
    enabled: bool = True
    type: AlertType
    severity: AlertSeverity
    conditions: List[Condition]
    notification_channels: List[NotificationChannel]
    template: Dict[str, str]
    tags: List[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user_id: Optional[str] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Déséquilibre de canal",
                "description": "Alerte sur déséquilibre des canaux",
                "enabled": True,
                "type": "channel_balance",
                "severity": "warning",
                "conditions": [
                    {
                        "metric": "channel_balance_ratio",
                        "operator": "<",
                        "threshold": 0.2,
                        "duration": "1h"
                    }
                ],
                "notification_channels": ["email", "in_app"],
                "template": {
                    "title": "Déséquilibre de canal détecté",
                    "message": "Le canal {channel_id} avec {peer_alias} est déséquilibré (ratio: {balance_ratio})"
                },
                "tags": ["balance", "channel"]
            }
        }
    }

class NotificationConfig(BaseModel):
    """Configuration d'un canal de notification"""
    id: Optional[str] = None
    name: str
    channel: NotificationChannel
    type: NotificationChannel
    config: Dict[str, Any]
    enabled: bool = True
    user_id: Optional[str] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Email Pro",
                "channel": "email",
                "type": "email",
                "config": {
                    "email": "admin@example.com",
                    "include_details": True
                },
                "enabled": True
            }
        }
    }

class EventFilter(BaseModel):
    """Filtres pour les événements"""
    type: Optional[str] = None
    severity: Optional[AlertSeverity] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    acknowledged: Optional[bool] = None
    limit: int = 50
    
    @field_validator('limit')
    @classmethod
    def validate_limit(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('La limite doit être entre 1 et 1000')
        return v

class EventData(BaseModel):
    """Données d'un événement"""
    id: str
    type: str
    source: str
    source_id: Optional[str] = None
    timestamp: datetime
    severity: AlertSeverity
    title: str
    message: str
    details: Dict[str, Any] = {}
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "evt-12345",
                "type": "alert_triggered",
                "source": "alert",
                "source_id": "alert-123",
                "timestamp": "2023-07-01T12:34:56Z",
                "severity": "warning",
                "title": "Déséquilibre de canal détecté",
                "message": "Le canal 12345 avec peer123 est déséquilibré (ratio: 0.15)",
                "details": {
                    "channel_id": "12345",
                    "peer_id": "peer123",
                    "balance_ratio": 0.15,
                    "local_balance": 1000000,
                    "remote_balance": 5666667
                },
                "acknowledged": False
            }
        }
    }

class MetricDefinition(BaseModel):
    """Définition d'une métrique"""
    name: str
    description: str
    type: str
    scope: str
    unit: str
    labels: List[str] = []
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "channel_balance_ratio",
                "description": "Ratio de balance dans un canal (0-1)",
                "type": "gauge",
                "scope": "channel",
                "unit": "ratio",
                "labels": ["channel_id", "node_id", "peer_id"]
            }
        }
    }

class MetricQuery(BaseModel):
    """Requête pour les métriques"""
    metrics: List[str]
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    step: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
    aggregation: Optional[str] = None
    
    @field_validator('start_time', 'end_time')
    @classmethod
    def validate_time_range(cls, v, info):
        data = info.data
        if 'start_time' in data and data['start_time'] and v:
            if v < data['start_time']:
                raise ValueError('end_time doit être postérieur à start_time')
        return v

class MetricDataPoint(BaseModel):
    """Point de données d'une métrique"""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = {}

class MetricSeries(BaseModel):
    """Série de données de métriques"""
    metric: str
    labels: Dict[str, str] = {}
    datapoints: List[MetricDataPoint] = []

class MetricQueryResult(BaseModel):
    """Résultat d'une requête de métriques"""
    series: List[MetricSeries]
    query: MetricQuery

class SubscriptionRequest(BaseModel):
    """Demande d'abonnement aux événements"""
    event_types: List[str] = []
    event_sources: List[str] = []
    severity_levels: List[AlertSeverity] = []
    filters: Dict[str, Any] = {}
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "event_types": ["alert_triggered", "alert_resolved"],
                "event_sources": ["alert"],
                "severity_levels": ["critical", "error"],
                "filters": {
                    "tags": ["balance", "payment"]
                }
            }
        }
    }

class SubscriptionResponse(BaseModel):
    """Réponse à une demande d'abonnement"""
    subscription_id: str
    status: str
    message: str
    expires_at: datetime

class DashboardWidgetType(str, Enum):
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    GAUGE = "gauge"
    TABLE = "table"
    STATUS = "status"
    TEXT = "text"

class DashboardWidget(BaseModel):
    """Widget d'un tableau de bord"""
    id: Optional[str] = None
    title: str
    type: DashboardWidgetType
    description: Optional[str] = None
    metrics: List[str] = []
    query: Optional[MetricQuery] = None
    options: Dict[str, Any] = {}
    size: Dict[str, int] = {"width": 1, "height": 1}
    position: Dict[str, int] = {"x": 0, "y": 0}

class MonitoringDashboard(BaseModel):
    """Tableau de bord de monitoring"""
    id: Optional[str] = None
    name: str
    description: str
    is_default: bool = False
    time_range: TimeRange = TimeRange.LAST_DAY
    custom_time_range: Optional[Dict[str, datetime]] = None
    refresh_interval: int = 60
    widgets: List[DashboardWidget] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user_id: Optional[str] = None
    
    @field_validator('custom_time_range')
    @classmethod
    def validate_custom_time(cls, v, info):
        data = info.data
        if 'time_range' in data and data['time_range'] == TimeRange.CUSTOM:
            if not v or 'start' not in v or 'end' not in v:
                raise ValueError('Pour un intervalle personnalisé, start et end sont requis')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Vue d'ensemble des canaux",
                "description": "Tableau de bord principal pour surveiller les canaux",
                "is_default": True,
                "time_range": "24h",
                "refresh_interval": 60,
                "widgets": [
                    {
                        "title": "Balance des canaux",
                        "type": "line_chart",
                        "description": "Évolution des balances par canal",
                        "metrics": ["channel_balance_sats"],
                        "options": {
                            "stacked": False,
                            "fill": True
                        },
                        "size": {"width": 2, "height": 1},
                        "position": {"x": 0, "y": 0}
                    }
                ]
            }
        }
    } 