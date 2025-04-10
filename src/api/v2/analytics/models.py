from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class FeeMarketMetricType(str, Enum):
    """Types de métriques pour l'analyse du marché des frais"""
    AVERAGE_FEE = "average_fee"
    MEDIAN_FEE = "median_fee"
    FEE_PERCENTILE_95 = "fee_percentile_95"
    FEE_PERCENTILE_99 = "fee_percentile_99"
    FEE_VOLUME = "fee_volume"
    FEE_RATE = "fee_rate"
    FEE_TREND = "fee_trend"
    MARKET_SHARE = "market_share"
    COMPETITOR_FEE = "competitor_fee"

class FeeMarketTimeframe(str, Enum):
    """Périodes d'analyse du marché des frais"""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"

class FeeMarketSegment(str, Enum):
    """Segments du marché des frais"""
    RETAIL = "retail"
    WHOLESALE = "wholesale"
    INSTITUTIONAL = "institutional"
    HIGH_FREQUENCY = "high_frequency"
    CUSTOM = "custom"

class FeeMarketMetric(BaseModel):
    """Métrique du marché des frais"""
    id: str = Field(..., description="Identifiant unique de la métrique")
    type: FeeMarketMetricType = Field(..., description="Type de métrique")
    value: float = Field(..., description="Valeur de la métrique")
    timestamp: datetime = Field(..., description="Horodatage de la métrique")
    timeframe: FeeMarketTimeframe = Field(..., description="Période d'analyse")
    segment: FeeMarketSegment = Field(..., description="Segment de marché")
    channel_id: Optional[str] = Field(None, description="ID du canal concerné")
    node_id: Optional[str] = Field(None, description="ID du nœud concerné")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées supplémentaires")

    class Config:
        schema_extra = {
            "example": {
                "id": "metric-123",
                "type": "average_fee",
                "value": 0.0001,
                "timestamp": "2024-03-20T10:00:00Z",
                "timeframe": "day",
                "segment": "retail",
                "channel_id": "channel-456",
                "node_id": "node-789",
                "metadata": {
                    "source": "lightning_network",
                    "confidence": 0.95
                }
            }
        }

class FeeMarketAnalysis(BaseModel):
    """Analyse du marché des frais"""
    id: str = Field(..., description="Identifiant unique de l'analyse")
    timestamp: datetime = Field(..., description="Horodatage de l'analyse")
    timeframe: FeeMarketTimeframe = Field(..., description="Période d'analyse")
    segment: FeeMarketSegment = Field(..., description="Segment de marché")
    metrics: List[FeeMarketMetric] = Field(..., description="Métriques analysées")
    market_position: float = Field(..., description="Position sur le marché (0-1)")
    competitive_advantage: float = Field(..., description="Avantage concurrentiel (-1 à 1)")
    recommendations: List[str] = Field(..., description="Recommandations basées sur l'analyse")
    confidence_score: float = Field(..., ge=0, le=1, description="Score de confiance de l'analyse")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées supplémentaires")

    class Config:
        schema_extra = {
            "example": {
                "id": "analysis-123",
                "timestamp": "2024-03-20T10:00:00Z",
                "timeframe": "day",
                "segment": "retail",
                "metrics": [
                    {
                        "id": "metric-123",
                        "type": "average_fee",
                        "value": 0.0001,
                        "timestamp": "2024-03-20T10:00:00Z",
                        "timeframe": "day",
                        "segment": "retail",
                        "channel_id": "channel-456",
                        "node_id": "node-789",
                        "metadata": {
                            "source": "lightning_network",
                            "confidence": 0.95
                        }
                    }
                ],
                "market_position": 0.75,
                "competitive_advantage": 0.2,
                "recommendations": [
                    "Augmenter les frais de 10% pour le segment retail",
                    "Maintenir les frais actuels pour le segment wholesale"
                ],
                "confidence_score": 0.85,
                "metadata": {
                    "data_points": 1000,
                    "market_volatility": "low"
                }
            }
        }

class FeeMarketAnalysisRequest(BaseModel):
    """Requête d'analyse du marché des frais"""
    timeframe: FeeMarketTimeframe = Field(..., description="Période d'analyse")
    segment: FeeMarketSegment = Field(..., description="Segment de marché")
    channel_id: Optional[str] = Field(None, description="ID du canal à analyser")
    node_id: Optional[str] = Field(None, description="ID du nœud à analyser")
    include_competitors: bool = Field(True, description="Inclure l'analyse des concurrents")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées supplémentaires")

    class Config:
        schema_extra = {
            "example": {
                "timeframe": "day",
                "segment": "retail",
                "channel_id": "channel-456",
                "node_id": "node-789",
                "include_competitors": True,
                "metadata": {
                    "analysis_depth": "detailed",
                    "include_historical": True
                }
            }
        }

class FeeMarketFilter(BaseModel):
    """Filtres pour l'analyse du marché des frais"""
    timeframe: Optional[FeeMarketTimeframe] = Field(None, description="Période d'analyse")
    segment: Optional[FeeMarketSegment] = Field(None, description="Segment de marché")
    channel_id: Optional[str] = Field(None, description="ID du canal")
    node_id: Optional[str] = Field(None, description="ID du nœud")
    start_date: Optional[datetime] = Field(None, description="Date de début")
    end_date: Optional[datetime] = Field(None, description="Date de fin")
    limit: int = Field(100, ge=1, le=1000, description="Nombre maximum de résultats")

    @validator("limit")
    def validate_limit(cls, v):
        if v < 1 or v > 1000:
            raise ValueError("La limite doit être comprise entre 1 et 1000")
        return v

    class Config:
        schema_extra = {
            "example": {
                "timeframe": "day",
                "segment": "retail",
                "channel_id": "channel-456",
                "node_id": "node-789",
                "start_date": "2024-03-01T00:00:00Z",
                "end_date": "2024-03-20T23:59:59Z",
                "limit": 100
            }
        } 