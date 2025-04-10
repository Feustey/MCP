from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

class PredictionType(str, Enum):
    """Types de prédictions disponibles"""
    CHANNEL_BALANCE = "channel_balance"
    PAYMENT_SUCCESS = "payment_success"
    NETWORK_CONGESTION = "network_congestion"
    FEE_RATE = "fee_rate"
    NODE_RELIABILITY = "node_reliability"
    CHANNEL_HEALTH = "channel_health"

class ModelType(str, Enum):
    """Types de modèles disponibles"""
    TIME_SERIES = "time_series"
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    ANOMALY_DETECTION = "anomaly_detection"

class PredictionModel(BaseModel):
    """Modèle de prédiction"""
    id: str = Field(..., description="Identifiant unique du modèle")
    name: str = Field(..., description="Nom du modèle")
    type: ModelType = Field(..., description="Type de modèle")
    prediction_type: PredictionType = Field(..., description="Type de prédiction")
    version: str = Field(..., description="Version du modèle")
    description: str = Field(..., description="Description du modèle")
    features: List[str] = Field(..., description="Liste des features utilisées")
    accuracy: float = Field(..., description="Précision du modèle (0-1)")
    last_trained: datetime = Field(..., description="Date de dernière entraînement")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Paramètres du modèle")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées supplémentaires")

class PredictionRequest(BaseModel):
    """Requête de prédiction"""
    model_id: str = Field(..., description="ID du modèle à utiliser")
    features: Dict[str, Any] = Field(..., description="Features pour la prédiction")
    timestamp: Optional[datetime] = Field(None, description="Timestamp pour la prédiction")
    confidence_threshold: Optional[float] = Field(0.95, description="Seuil de confiance minimum")

class PredictionResult(BaseModel):
    """Résultat de prédiction"""
    model_id: str = Field(..., description="ID du modèle utilisé")
    prediction_type: PredictionType = Field(..., description="Type de prédiction")
    value: Union[float, bool, str] = Field(..., description="Valeur prédite")
    confidence: float = Field(..., description="Niveau de confiance (0-1)")
    timestamp: datetime = Field(..., description="Timestamp de la prédiction")
    features_used: Dict[str, Any] = Field(..., description="Features utilisées")
    explanation: Optional[str] = Field(None, description="Explication de la prédiction")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées supplémentaires")

class ModelTrainingRequest(BaseModel):
    """Requête d'entraînement de modèle"""
    model_id: str = Field(..., description="ID du modèle à entraîner")
    training_data: List[Dict[str, Any]] = Field(..., description="Données d'entraînement")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Paramètres d'entraînement")
    validation_split: Optional[float] = Field(0.2, description="Proportion des données de validation")

class ModelEvaluationResult(BaseModel):
    """Résultat d'évaluation de modèle"""
    model_id: str = Field(..., description="ID du modèle évalué")
    accuracy: float = Field(..., description="Précision globale")
    precision: float = Field(..., description="Précision par classe")
    recall: float = Field(..., description="Rappel par classe")
    f1_score: float = Field(..., description="Score F1")
    confusion_matrix: Optional[List[List[int]]] = Field(None, description="Matrice de confusion")
    feature_importance: Dict[str, float] = Field(..., description="Importance des features")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées supplémentaires")

class PredictionFilter(BaseModel):
    """Filtres pour les prédictions"""
    model_id: Optional[str] = Field(None, description="ID du modèle")
    prediction_type: Optional[PredictionType] = Field(None, description="Type de prédiction")
    start_time: Optional[datetime] = Field(None, description="Début de la période")
    end_time: Optional[datetime] = Field(None, description="Fin de la période")
    min_confidence: Optional[float] = Field(None, description="Confiance minimum")
    limit: int = Field(100, ge=1, le=1000, description="Nombre maximum de résultats")

    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('La limite doit être comprise entre 1 et 1000')
        return v

# Exemples de configuration
PredictionModel.schema_extra = {
    "example": {
        "id": "model-123",
        "name": "Channel Balance Predictor",
        "type": ModelType.TIME_SERIES,
        "prediction_type": PredictionType.CHANNEL_BALANCE,
        "version": "1.0.0",
        "description": "Prédiction de l'équilibre des canaux",
        "features": ["channel_capacity", "payment_volume", "fee_rate"],
        "accuracy": 0.95,
        "last_trained": "2024-02-20T10:00:00Z",
        "parameters": {
            "window_size": 24,
            "forecast_horizon": 12
        },
        "metadata": {
            "training_samples": 10000,
            "training_duration": "2h"
        }
    }
}

PredictionRequest.schema_extra = {
    "example": {
        "model_id": "model-123",
        "features": {
            "channel_capacity": 1000000,
            "payment_volume": 50000,
            "fee_rate": 0.0001
        },
        "timestamp": "2024-02-20T10:00:00Z",
        "confidence_threshold": 0.95
    }
}

PredictionResult.schema_extra = {
    "example": {
        "model_id": "model-123",
        "prediction_type": PredictionType.CHANNEL_BALANCE,
        "value": 750000,
        "confidence": 0.98,
        "timestamp": "2024-02-20T10:00:00Z",
        "features_used": {
            "channel_capacity": 1000000,
            "payment_volume": 50000,
            "fee_rate": 0.0001
        },
        "explanation": "Prédiction basée sur l'historique des paiements et les taux de frais",
        "metadata": {
            "prediction_time_ms": 150
        }
    }
} 