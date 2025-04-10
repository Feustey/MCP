from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime, timedelta
import uuid

class BalancingStrategy(str, Enum):
    """Stratégies d'équilibrage"""
    EQUAL = "equal"  # Équilibrage égal entre les canaux
    WEIGHTED = "weighted"  # Équilibrage pondéré selon les poids
    THRESHOLD = "threshold"  # Équilibrage basé sur des seuils
    ADAPTIVE = "adaptive"  # Équilibrage adaptatif selon l'utilisation
    CUSTOM = "custom"  # Stratégie personnalisée

class BalancingStatus(str, Enum):
    """Statuts d'équilibrage"""
    PENDING = "pending"  # En attente
    RUNNING = "running"  # En cours
    COMPLETED = "completed"  # Terminé avec succès
    FAILED = "failed"  # Échec
    CANCELLED = "cancelled"  # Annulé

class BalancingOperationType(str, Enum):
    """Types d'opérations d'équilibrage"""
    REBALANCE = "rebalance"  # Rééquilibrage entre canaux
    TOP_UP = "top_up"  # Ajout de liquidité
    DRAIN = "drain"  # Retrait de liquidité
    MERGE = "merge"  # Fusion de canaux
    SPLIT = "split"  # Division de canaux

class BalancingConfig(BaseModel):
    """Configuration d'équilibrage"""
    id: Optional[str] = None
    name: str
    strategy: BalancingStrategy
    description: str
    is_active: bool = True
    min_amount: int = 10000  # Montant minimum en satoshis
    max_amount: int = 1000000  # Montant maximum en satoshis
    max_fee_rate: int = 1000  # Taux de frais maximum en ppm
    target_ratio: Optional[float] = None  # Ratio cible pour l'équilibrage
    weights: Optional[Dict[str, float]] = None  # Poids pour l'équilibrage pondéré
    thresholds: Optional[Dict[str, int]] = None  # Seuils pour l'équilibrage par seuil
    schedule: Optional[str] = None  # Expression cron pour l'exécution planifiée
    channels: List[str] = []  # Liste des canaux à équilibrer
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "config-12345",
                "name": "Équilibrage quotidien",
                "strategy": "threshold",
                "description": "Équilibrage automatique quotidien des canaux principaux",
                "is_active": True,
                "min_amount": 100000,
                "max_amount": 1000000,
                "max_fee_rate": 500,
                "target_ratio": 0.5,
                "thresholds": {
                    "min_balance": 200000,
                    "max_balance": 800000
                },
                "schedule": "0 0 * * *",
                "channels": ["chan-12345", "chan-67890"],
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-07-01T12:34:56Z"
            }
        }

class BalancingConfigCreate(BaseModel):
    """Modèle pour la création d'une configuration d'équilibrage"""
    name: str
    strategy: BalancingStrategy
    description: str
    is_active: bool = True
    min_amount: int = 10000
    max_amount: int = 1000000
    max_fee_rate: int = 1000
    target_ratio: Optional[float] = None
    weights: Optional[Dict[str, float]] = None
    thresholds: Optional[Dict[str, int]] = None
    schedule: Optional[str] = None
    channels: List[str] = []

class BalancingConfigUpdate(BaseModel):
    """Modèle pour la mise à jour d'une configuration d'équilibrage"""
    name: Optional[str] = None
    strategy: Optional[BalancingStrategy] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    min_amount: Optional[int] = None
    max_amount: Optional[int] = None
    max_fee_rate: Optional[int] = None
    target_ratio: Optional[float] = None
    weights: Optional[Dict[str, float]] = None
    thresholds: Optional[Dict[str, int]] = None
    schedule: Optional[str] = None
    channels: Optional[List[str]] = None

class BalancingOperation(BaseModel):
    """Opération d'équilibrage"""
    id: Optional[str] = None
    config_id: str
    type: BalancingOperationType
    status: BalancingStatus
    source_channel: str
    target_channel: str
    amount: int
    fee_rate: int
    actual_fee: Optional[int] = None
    error_message: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "op-12345",
                "config_id": "config-12345",
                "type": "rebalance",
                "status": "completed",
                "source_channel": "chan-12345",
                "target_channel": "chan-67890",
                "amount": 500000,
                "fee_rate": 100,
                "actual_fee": 50,
                "start_time": "2023-07-01T12:34:56Z",
                "end_time": "2023-07-01T12:35:10Z",
                "created_at": "2023-07-01T12:34:56Z"
            }
        }

class BalancingOperationCreate(BaseModel):
    """Modèle pour la création d'une opération d'équilibrage"""
    config_id: str
    type: BalancingOperationType
    source_channel: str
    target_channel: str
    amount: int
    fee_rate: int

class BalancingOperationUpdate(BaseModel):
    """Modèle pour la mise à jour d'une opération d'équilibrage"""
    status: Optional[BalancingStatus] = None
    actual_fee: Optional[int] = None
    error_message: Optional[str] = None
    end_time: Optional[datetime] = None

class BalancingStats(BaseModel):
    """Statistiques d'équilibrage"""
    total_operations: int
    successful_operations: int
    failed_operations: int
    total_amount: int
    total_fees: int
    average_fee_rate: float
    start_date: datetime
    end_date: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "total_operations": 100,
                "successful_operations": 95,
                "failed_operations": 5,
                "total_amount": 50000000,
                "total_fees": 5000,
                "average_fee_rate": 100,
                "start_date": "2023-01-01T00:00:00Z",
                "end_date": "2023-07-01T12:34:56Z"
            }
        }

class BalancingStatsFilter(BaseModel):
    """Filtres pour les statistiques d'équilibrage"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    config_id: Optional[str] = None
    channel_id: Optional[str] = None
    status: Optional[BalancingStatus] = None

class BalancingOperationFilter(BaseModel):
    """Filtres pour les opérations d'équilibrage"""
    config_id: Optional[str] = None
    type: Optional[BalancingOperationType] = None
    status: Optional[BalancingStatus] = None
    source_channel: Optional[str] = None
    target_channel: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100
    
    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('La limite doit être entre 1 et 1000')
        return v 