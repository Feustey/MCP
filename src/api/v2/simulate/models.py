from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

class SimulationType(str, Enum):
    """Types de simulations disponibles"""
    NETWORK_LOAD = "network_load"
    PAYMENT_ROUTE = "payment_route"
    CHANNEL_BALANCE = "channel_balance"
    NODE_FAILURE = "node_failure"
    NETWORK_CONGESTION = "network_congestion"
    FEE_RATE = "fee_rate"

class SimulationStatus(str, Enum):
    """Statuts possibles d'une simulation"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class SimulationScenario(BaseModel):
    """Scénario de simulation"""
    id: str = Field(..., description="Identifiant unique du scénario")
    name: str = Field(..., description="Nom du scénario")
    type: SimulationType = Field(..., description="Type de simulation")
    description: str = Field(..., description="Description du scénario")
    parameters: Dict[str, Any] = Field(..., description="Paramètres du scénario")
    created_at: datetime = Field(..., description="Date de création")
    updated_at: datetime = Field(..., description="Date de dernière mise à jour")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées supplémentaires")

class SimulationRequest(BaseModel):
    """Requête de simulation"""
    scenario_id: str = Field(..., description="ID du scénario à simuler")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Paramètres de simulation")
    duration: Optional[int] = Field(3600, description="Durée de la simulation en secondes")
    real_time: Optional[bool] = Field(True, description="Simulation en temps réel")

class SimulationResult(BaseModel):
    """Résultat de simulation"""
    id: str = Field(..., description="Identifiant unique de la simulation")
    scenario_id: str = Field(..., description="ID du scénario simulé")
    status: SimulationStatus = Field(..., description="Statut de la simulation")
    start_time: datetime = Field(..., description="Début de la simulation")
    end_time: Optional[datetime] = Field(None, description="Fin de la simulation")
    results: Dict[str, Any] = Field(..., description="Résultats de la simulation")
    metrics: Dict[str, float] = Field(..., description="Métriques calculées")
    events: List[Dict[str, Any]] = Field(..., description="Événements simulés")
    error_message: Optional[str] = Field(None, description="Message d'erreur en cas d'échec")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées supplémentaires")

class SimulationFilter(BaseModel):
    """Filtres pour les simulations"""
    scenario_id: Optional[str] = Field(None, description="ID du scénario")
    type: Optional[SimulationType] = Field(None, description="Type de simulation")
    status: Optional[SimulationStatus] = Field(None, description="Statut de la simulation")
    start_time: Optional[datetime] = Field(None, description="Début de la période")
    end_time: Optional[datetime] = Field(None, description="Fin de la période")
    limit: int = Field(100, ge=1, le=1000, description="Nombre maximum de résultats")

    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('La limite doit être comprise entre 1 et 1000')
        return v

# Exemples de configuration
SimulationScenario.schema_extra = {
    "example": {
        "id": "scenario-123",
        "name": "Test de charge réseau",
        "type": SimulationType.NETWORK_LOAD,
        "description": "Simulation de charge réseau avec 1000 paiements simultanés",
        "parameters": {
            "num_payments": 1000,
            "payment_amount": 100000,
            "duration_minutes": 60
        },
        "created_at": "2024-02-20T10:00:00Z",
        "updated_at": "2024-02-20T10:00:00Z",
        "metadata": {
            "author": "admin",
            "version": "1.0"
        }
    }
}

SimulationRequest.schema_extra = {
    "example": {
        "scenario_id": "scenario-123",
        "parameters": {
            "num_payments": 500,
            "payment_amount": 50000
        },
        "duration": 1800,
        "real_time": True
    }
}

SimulationResult.schema_extra = {
    "example": {
        "id": "sim-123",
        "scenario_id": "scenario-123",
        "status": SimulationStatus.COMPLETED,
        "start_time": "2024-02-20T10:00:00Z",
        "end_time": "2024-02-20T10:30:00Z",
        "results": {
            "successful_payments": 485,
            "failed_payments": 15,
            "average_route_length": 3.2
        },
        "metrics": {
            "success_rate": 0.97,
            "average_fee": 100,
            "max_route_length": 5
        },
        "events": [
            {
                "timestamp": "2024-02-20T10:05:00Z",
                "type": "payment_success",
                "details": {"payment_id": "pay-123", "amount": 50000}
            }
        ],
        "metadata": {
            "simulation_duration": "30m",
            "cpu_usage": "45%"
        }
    }
} 