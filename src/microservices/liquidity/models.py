from pydantic import BaseModel, Field, validator, field_validator, model_validator
from typing import Dict, List, Optional, Any, Union, Annotated
from enum import Enum
from datetime import datetime, timedelta
import uuid
import re
from pydantic_extra_types.country import CountryAlpha2
from decimal import Decimal

# Types et enums
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

class ChannelDirection(str, Enum):
    """Direction des canaux"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"

# Type personnalisé pour les IDs des entités
EntityId = Annotated[str, Field(
    description="Identifiant unique au format UUID",
    examples=["550e8400-e29b-41d4-a716-446655440000"]
)]

# Valeurs constantes utilisées dans plusieurs modèles
MAX_LIMIT = 1000
MIN_LIMIT = 1
DEFAULT_LIMIT = 100

# Modèles principaux avec validation renforcée
class LiquidityMetric(BaseModel):
    """Modèle de métrique de liquidité"""
    id: Optional[EntityId] = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=3, max_length=100, description="Nom de la métrique")
    type: LiquidityMetricType = Field(..., description="Type de métrique")
    description: str = Field(..., min_length=10, max_length=500, description="Description détaillée")
    value: Decimal = Field(..., ge=0, description="Valeur de la métrique")
    unit: str = Field(..., min_length=1, max_length=20, description="Unité de mesure (sats, BTC, etc.)")
    timestamp: datetime = Field(default_factory=datetime.now, description="Horodatage")
    channel_id: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9-]+$", description="ID du canal")
    node_id: Optional[str] = Field(None, min_length=30, max_length=66, description="ID du nœud")
    tags: Dict[str, str] = Field(default_factory=dict, description="Tags personnalisés")
    location: Optional[CountryAlpha2] = Field(None, description="Localisation (code pays ISO)")
    created_at: datetime = Field(default_factory=datetime.now, description="Date de création")
    
    @field_validator('channel_id')
    def channel_id_format(cls, v):
        if v is not None and not re.match(r'^[a-zA-Z0-9-]+$', v):
            raise ValueError('Le channel_id doit contenir uniquement des lettres, chiffres et tirets')
        return v
    
    @field_validator('node_id')
    def node_id_format(cls, v):
        if v is not None and not re.match(r'^[a-fA-F0-9]{30,66}$', v):
            raise ValueError('Le node_id doit être une clé publique hexadécimale valide')
        return v
    
    @field_validator('value')
    def validate_value(cls, v, info):
        # Validation spécifique selon le type de métrique
        field_types = info.data.get('type')
        if field_types == LiquidityMetricType.PAYMENT_SUCCESS or field_types == LiquidityMetricType.ROUTING_SUCCESS:
            if v < 0 or v > 1:
                raise ValueError('Les taux de succès doivent être entre 0 et 1')
        return v
    
    @model_validator(mode='after')
    def validate_model(self):
        # Au moins un identifiant requis
        if not self.channel_id and not self.node_id:
            raise ValueError('Au moins un channel_id ou node_id doit être fourni')
        
        # Vérifier la cohérence des unités
        if self.type == LiquidityMetricType.CHANNEL_BALANCE and self.unit not in ['sats', 'BTC']:
            raise ValueError('L\'unité de balance doit être sats ou BTC')
        
        # Vérifier la cohérence des types et des identifiants
        if self.type in [LiquidityMetricType.CHANNEL_BALANCE, LiquidityMetricType.CHANNEL_HEALTH] and not self.channel_id:
            raise ValueError(f'Le channel_id est requis pour le type {self.type}')
        
        if self.type in [LiquidityMetricType.NODE_BALANCE, LiquidityMetricType.NETWORK_HEALTH] and not self.node_id:
            raise ValueError(f'Le node_id est requis pour le type {self.type}')
        
        # Interdire les dates futures
        if self.timestamp > datetime.now() + timedelta(minutes=5):
            raise ValueError("L'horodatage ne peut pas être dans le futur")
        
        return self

class LiquidityThreshold(BaseModel):
    """Modèle de seuil de liquidité avec validation renforcée"""
    id: Optional[EntityId] = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=3, max_length=100)
    type: LiquidityThresholdType
    metric_type: LiquidityMetricType
    value: Decimal = Field(..., ge=0)
    severity: LiquidityAlertSeverity
    description: str = Field(..., min_length=10, max_length=500)
    is_active: bool = True
    channel_id: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9-]+$")
    node_id: Optional[str] = Field(None, min_length=30, max_length=66)
    notification_enabled: bool = Field(True, description="Activer les notifications pour ce seuil")
    cooldown_period: int = Field(60, ge=0, le=86400, description="Période de refroidissement entre alertes en secondes")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    @model_validator(mode='after')
    def validate_model(self):
        # Validation de cohérence entre type de seuil et type de métrique
        valid_combinations = {
            (LiquidityThresholdType.MIN_BALANCE, LiquidityMetricType.CHANNEL_BALANCE),
            (LiquidityThresholdType.MAX_BALANCE, LiquidityMetricType.CHANNEL_BALANCE),
            (LiquidityThresholdType.MIN_BALANCE, LiquidityMetricType.NODE_BALANCE),
            (LiquidityThresholdType.MAX_BALANCE, LiquidityMetricType.NODE_BALANCE),
            (LiquidityThresholdType.MIN_RATIO, LiquidityMetricType.CAPACITY_UTILIZATION),
            (LiquidityThresholdType.MAX_RATIO, LiquidityMetricType.CAPACITY_UTILIZATION),
            (LiquidityThresholdType.MIN_SUCCESS_RATE, LiquidityMetricType.PAYMENT_SUCCESS),
            (LiquidityThresholdType.MIN_SUCCESS_RATE, LiquidityMetricType.ROUTING_SUCCESS),
            (LiquidityThresholdType.MAX_FEE_RATE, LiquidityMetricType.FEE_RATE),
            (LiquidityThresholdType.MIN_CAPACITY, LiquidityMetricType.CHANNEL_BALANCE),
            (LiquidityThresholdType.MAX_CAPACITY, LiquidityMetricType.CHANNEL_BALANCE),
        }
        
        if (self.type, self.metric_type) not in valid_combinations:
            raise ValueError(f"Combinaison invalide: type de seuil '{self.type}' avec métrique '{self.metric_type}'")
        
        # Valider les plages de valeurs selon le type
        if self.type in [LiquidityThresholdType.MIN_RATIO, LiquidityThresholdType.MAX_RATIO, 
                       LiquidityThresholdType.MIN_SUCCESS_RATE] and (self.value < 0 or self.value > 1):
            raise ValueError(f"La valeur pour {self.type} doit être entre 0 et 1")
        
        # Au moins un identifiant requis
        if not self.channel_id and not self.node_id:
            raise ValueError('Au moins un channel_id ou node_id doit être fourni')
        
        return self

class LiquidityAlert(BaseModel):
    """Modèle d'alerte de liquidité avec validation renforcée"""
    id: Optional[EntityId] = Field(default_factory=lambda: str(uuid.uuid4()))
    threshold_id: EntityId
    metric_id: EntityId
    severity: LiquidityAlertSeverity
    message: str = Field(..., min_length=10, max_length=500)
    value: Decimal
    threshold_value: Decimal
    timestamp: datetime = Field(default_factory=datetime.now)
    is_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    channel_id: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9-]+$")
    node_id: Optional[str] = Field(None, min_length=30, max_length=66)
    actions_taken: List[str] = Field(default_factory=list, description="Actions prises suite à l'alerte")
    resolution_status: Optional[str] = Field(None, description="Statut de résolution")
    
    @field_validator('actions_taken')
    def validate_actions(cls, v):
        if len(v) > 10:
            raise ValueError("Le nombre d'actions ne peut pas dépasser 10")
        return v
    
    @model_validator(mode='after')
    def validate_model(self):
        # Vérifier la cohérence des dates d'acquittement
        if self.is_acknowledged:
            if not self.acknowledged_by:
                raise ValueError("L'identifiant de l'acquéreur est requis pour une alerte acquittée")
            if not self.acknowledged_at:
                raise ValueError("La date d'acquittement est requise pour une alerte acquittée")
        else:
            if self.acknowledged_by or self.acknowledged_at:
                raise ValueError("Les champs d'acquittement doivent être null pour une alerte non acquittée")
        
        # Vérifier la relation entre valeur et seuil
        if self.severity == LiquidityAlertSeverity.CRITICAL and abs(self.value - self.threshold_value) < 0.1:
            raise ValueError("Pour une alerte critique, la différence doit être significative")
            
        return self

class LiquidityAnalysis(BaseModel):
    """Modèle d'analyse de liquidité avec validation renforcée"""
    id: Optional[EntityId] = Field(default_factory=lambda: str(uuid.uuid4()))
    channel_id: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9-]+$")
    node_id: Optional[str] = Field(None, min_length=30, max_length=66)
    timestamp: datetime = Field(default_factory=datetime.now)
    metrics: Dict[str, Decimal] = Field(..., min_length=1)
    score: Decimal = Field(..., ge=0, le=100)
    recommendations: List[str] = Field(..., min_length=1)
    issues: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    analysis_version: str = Field("1.0", description="Version de l'algorithme d'analyse")
    data_completeness: Decimal = Field(1.0, ge=0, le=1.0, description="Complétude des données")
    
    @field_validator('recommendations')
    def validate_recommendations(cls, v):
        if len(v) > 10:
            raise ValueError("Le nombre de recommandations ne peut pas dépasser 10")
        for rec in v:
            if len(rec) < 10 or len(rec) > 500:
                raise ValueError("Chaque recommandation doit avoir entre 10 et 500 caractères")
        return v
    
    @field_validator('metrics')
    def validate_metrics(cls, v):
        required_metrics = ["balance_ratio", "payment_success_rate"]
        missing = [m for m in required_metrics if m not in v]
        if missing:
            raise ValueError(f"Métriques requises manquantes: {', '.join(missing)}")
        return v
    
    @model_validator(mode='after')
    def validate_model(self):
        # Vérifier cohérence score vs métriques
        if 'payment_success_rate' in self.metrics and self.metrics['payment_success_rate'] < 0.5 and self.score > 70:
            raise ValueError("Incohérence: score élevé avec taux de succès faible")
        
        # Au moins un identifiant requis
        if not self.channel_id and not self.node_id:
            raise ValueError('Au moins un channel_id ou node_id doit être fourni')
            
        # Vérifier cohérence score vs issues
        if len(self.issues) == 0 and self.score < 80:
            raise ValueError("Incohérence: score faible sans problèmes identifiés")
            
        # Vérifier la complétude des données
        if self.data_completeness < 0.7 and not any("données incomplètes" in issue.lower() for issue in self.issues):
            self.issues.append("Analyse basée sur des données incomplètes")
            
        return self

# Classes pour les requêtes et filtres
class LiquidityAnalysisRequest(BaseModel):
    """Modèle pour la demande d'analyse de liquidité"""
    channel_id: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9-]+$")
    node_id: Optional[str] = Field(None, min_length=30, max_length=66)
    include_recommendations: bool = True
    include_issues: bool = True
    analysis_depth: str = Field("standard", pattern=r"^(light|standard|deep)$")
    
    @model_validator(mode='after')
    def validate_model(self):
        if not self.channel_id and not self.node_id:
            raise ValueError('Au moins un channel_id ou node_id doit être fourni')
        return self

class LiquidityMetricFilter(BaseModel):
    """Filtres pour les métriques de liquidité"""
    type: Optional[LiquidityMetricType] = None
    channel_id: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9-]+$")
    node_id: Optional[str] = Field(None, min_length=30, max_length=66)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(DEFAULT_LIMIT, ge=MIN_LIMIT, le=MAX_LIMIT)
    
    @model_validator(mode='after')
    def validate_model(self):
        # Validation de la plage de dates
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValueError('La date de début doit être antérieure à la date de fin')
        
        # Limitation de la plage à 30 jours
        if self.start_time and self.end_time and (self.end_time - self.start_time).days > 30:
            raise ValueError('La plage de dates ne peut pas dépasser 30 jours')
            
        return self

class LiquidityAlertFilter(BaseModel):
    """Filtres pour les alertes de liquidité"""
    severity: Optional[LiquidityAlertSeverity] = None
    is_acknowledged: Optional[bool] = None
    channel_id: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9-]+$")
    node_id: Optional[str] = Field(None, min_length=30, max_length=66)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(DEFAULT_LIMIT, ge=MIN_LIMIT, le=MAX_LIMIT)
    
    @model_validator(mode='after')
    def validate_model(self):
        # Validation de la plage de dates
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValueError('La date de début doit être antérieure à la date de fin')
        
        # Vérifier la présence de critères de filtrage
        if not any([self.severity, self.is_acknowledged is not None, 
                   self.channel_id, self.node_id, self.start_time, self.end_time]):
            raise ValueError('Au moins un critère de filtrage doit être spécifié')
            
        return self 