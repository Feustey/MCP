from pydantic import BaseModel, Field, validator
from typing import Optional, List, Any, Dict, Union, Literal
from enum import Enum
from bson import ObjectId
from datetime import datetime
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema, CoreSchema

# Classe utilitaire pour gérer les ObjectId de MongoDB dans Pydantic
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type,
        _handler,
    ):
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(cls.validate),
                ])
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )
                
    def __repr__(self):
        return f"PyObjectId({super().__repr__()})"
    
    def __str__(self):
        return str(super())

# Modèle Pydantic pour représenter un Node Lightning dans la base de données
# Ce modèle inclut l'_id généré par MongoDB
class NodeInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    alias: str = Field(..., min_length=1, max_length=50, description="Nom d'affichage du node")
    pubkey: str = Field(..., pattern=r"^[0-9a-fA-F]{66}$", description="Clé publique du node (hexadécimal, 66 caractères)")
    score: float = Field(..., ge=0, le=100, description="Score de qualité du node (0-100)")
    channels: int = Field(..., ge=0, description="Nombre de canaux ouverts")
    last_updated: Optional[datetime] = Field(None, description="Date de dernière mise à jour des informations")

    class Config:
        populate_by_name = True # Permet d'utiliser `_id` ou `id`
        arbitrary_types_allowed = True # Nécessaire pour PyObjectId
        json_encoders = {
            ObjectId: str, # Convertit ObjectId en string pour les réponses JSON
            datetime: lambda dt: dt.isoformat() # Formate les datetimes en ISO
        }
        json_schema_extra = {
            "example": {
                "_id": "60d5ecf1e4b0f8d9f3b1e3e1",
                "alias": "MonSuperNode",
                "pubkey": "02abcdef1234567890abcdef1234567890abcdef1234567890abcdef123456",
                "score": 95.7,
                "channels": 25,
                "last_updated": "2023-10-27T10:00:00Z"
            }
        }

# Modèle Pydantic pour la création d'un nouveau Node
# Pas besoin d'ID ici, car MongoDB le générera
# last_updated est aussi optionnel ou géré automatiquement
class NodeCreate(BaseModel):
    alias: str = Field(..., min_length=1, max_length=50, description="Nom d'affichage du node")
    pubkey: str = Field(..., pattern=r"^[0-9a-fA-F]{66}$", description="Clé publique du node (hexadécimal, 66 caractères)")
    score: float = Field(..., ge=0, le=100, description="Score de qualité du node (0-100)")
    channels: int = Field(..., ge=0, description="Nombre de canaux ouverts")

    class Config:
        json_schema_extra = {
            "example": {
                "alias": "NouveauNode",
                "pubkey": "03fedcba9876543210fedcba9876543210fedcba9876543210fedcba987654",
                "score": 88.2,
                "channels": 10
            }
        }

# Modèle Pydantic pour la mise à jour partielle d'un Node (PATCH)
# Tous les champs sont optionnels
class NodeUpdate(BaseModel):
    alias: Optional[str] = Field(None, min_length=1, max_length=50, description="Nouveau nom d'affichage (optionnel)")
    score: Optional[float] = Field(None, ge=0, le=100, description="Nouveau score (optionnel)")
    channels: Optional[int] = Field(None, ge=0, description="Nouveau nombre de canaux (optionnel)")
    last_updated: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Date de mise à jour")

    class Config:
        json_schema_extra = {
            "example": {
                "alias": "NodeRenommé",
                "score": 91.0
            }
        }

# Modèles pour le système de scoring Lightning Network

class LightningNodeBase(BaseModel):
    id: str = Field(..., description="Identifiant unique du nœud Lightning")
    alias: str = Field(..., description="Nom d'affichage du nœud")
    public_key: str = Field(..., description="Clé publique du nœud Lightning")
    last_update: datetime = Field(default_factory=datetime.utcnow, description="Date de dernière mise à jour")
    color: Optional[str] = Field(None, description="Couleur associée au nœud")
    
class LightningNodeFeature(BaseModel):
    name: str = Field(..., description="Nom de la fonctionnalité")
    is_required: bool = Field(..., description="Indique si la fonctionnalité est requise")
    is_supported: bool = Field(..., description="Indique si la fonctionnalité est supportée")

class LightningNodeAddress(BaseModel):
    network: str = Field(..., description="Type de réseau (tcp, tor, etc.)")
    addr: str = Field(..., description="Adresse du nœud")

class LightningNode(LightningNodeBase):
    features: Optional[List[LightningNodeFeature]] = Field(None, description="Fonctionnalités supportées par le nœud")
    addresses: Optional[List[LightningNodeAddress]] = Field(None, description="Adresses du nœud")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "123456",
                "alias": "ACINQ",
                "public_key": "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f",
                "last_update": "2023-10-27T10:00:00Z",
                "color": "#3399ff",
                "features": [
                    {"name": "option_static_remote_key", "is_required": True, "is_supported": True},
                    {"name": "option_anchor_outputs", "is_required": False, "is_supported": True}
                ],
                "addresses": [
                    {"network": "tcp", "addr": "34.239.230.56:9735"},
                    {"network": "tor", "addr": "vww6ybal4bd7szmgncyruucpgfkqahzddi37ktceo3ah7ngmcopnpyyd.onion:9735"}
                ]
            }
        }

class LightningChannel(BaseModel):
    id: str = Field(..., description="Identifiant unique du canal")
    node1_pub: str = Field(..., description="Clé publique du premier nœud")
    node2_pub: str = Field(..., description="Clé publique du deuxième nœud")
    capacity: int = Field(..., description="Capacité du canal en satoshis")
    last_update: datetime = Field(default_factory=datetime.utcnow, description="Date de dernière mise à jour")
    status: Literal["active", "inactive"] = Field(..., description="État du canal")
    fee_rate: float = Field(..., description="Taux de frais en ppm")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "123456789:0:1",
                "node1_pub": "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f",
                "node2_pub": "02f6725f9c1c40333b67faea92fd211c183050f28df32cac3f9d69685fe9665432",
                "capacity": 16777215,
                "last_update": "2023-10-27T10:00:00Z",
                "status": "active",
                "fee_rate": 1.0
            }
        }

class ScoreMetrics(BaseModel):
    centrality: float = Field(..., ge=0, le=100, description="Score de centralité (0-100)")
    reliability: float = Field(..., ge=0, le=100, description="Score de fiabilité (0-100)")
    performance: float = Field(..., ge=0, le=100, description="Score de performance (0-100)")
    composite: float = Field(..., ge=0, le=100, description="Score composite global (0-100)")

class ScoreMetadata(BaseModel):
    calculation_version: str = Field(..., description="Version de l'algorithme de calcul")
    data_sources: List[str] = Field(..., description="Sources des données utilisées pour le calcul")

class DetailedScores(BaseModel):
    centrality: Dict[str, float] = Field(..., description="Détails des scores de centralité")
    performance: Dict[str, float] = Field(..., description="Détails des scores de performance")
    capacity: Dict[str, Union[float, int]] = Field(..., description="Détails des scores de capacité")

class HistoricalScorePoint(BaseModel):
    timestamp: datetime
    score: float

class LightningNodeScore(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    node_id: str = Field(..., description="Identifiant du nœud Lightning")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Date du calcul du score")
    metrics: ScoreMetrics
    metadata: Optional[ScoreMetadata] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat()
        }
        json_schema_extra = {
            "example": {
                "_id": "60d5ecf1e4b0f8d9f3b1e3e1",
                "node_id": "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f",
                "timestamp": "2023-10-27T10:00:00Z",
                "metrics": {
                    "centrality": 95.7,
                    "reliability": 87.3,
                    "performance": 92.1,
                    "composite": 91.7
                },
                "metadata": {
                    "calculation_version": "1.0.0",
                    "data_sources": ["lnd", "amboss", "1ml"]
                }
            }
        }

class NodeScoreResponse(BaseModel):
    node_id: str
    detailed_scores: DetailedScores
    historical_data: List[HistoricalScorePoint]

class ScoresListResponse(BaseModel):
    data: List[LightningNodeScore]
    metadata: Dict[str, Any]

class RecommendationPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Recommendation(BaseModel):
    type: str = Field(..., description="Type de recommandation")
    description: str = Field(..., description="Description détaillée de la recommandation")
    priority: RecommendationPriority = Field(..., description="Priorité de la recommandation")
    impact_score: float = Field(..., ge=0, le=100, description="Impact estimé sur le score global")
    implementation_difficulty: str = Field(..., description="Difficulté de mise en œuvre")

class NodeRecommendations(BaseModel):
    node_id: str
    recommendations: List[Recommendation]

class ScoringConfigWeights(BaseModel):
    centrality: float = Field(..., ge=0, le=1, description="Poids pour le score de centralité")
    reliability: float = Field(..., ge=0, le=1, description="Poids pour le score de fiabilité")
    performance: float = Field(..., ge=0, le=1, description="Poids pour le score de performance")

class ScoringConfigThresholds(BaseModel):
    minimum_score: float = Field(..., ge=0, le=100, description="Score minimum pour considérer un nœud")
    alert_threshold: float = Field(..., ge=0, le=100, description="Seuil d'alerte pour les scores faibles")

class ScoringConfig(BaseModel):
    weights: ScoringConfigWeights
    thresholds: ScoringConfigThresholds
    
    class Config:
        json_schema_extra = {
            "example": {
                "weights": {
                    "centrality": 0.4,
                    "reliability": 0.3,
                    "performance": 0.3
                },
                "thresholds": {
                    "minimum_score": 50.0,
                    "alert_threshold": 70.0
                }
            }
        }

class RecalculateScoresRequest(BaseModel):
    node_ids: Optional[List[str]] = None
    force: bool = False 