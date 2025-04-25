from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import re

class Document(BaseModel):
    """Modèle pour les documents du système RAG"""
    content: str = Field(..., description="Contenu du document")
    source: str
    embedding: List[float] = Field(None, description="Embedding du document")
    metadata: Dict[str, Any] = Field(..., description="Métadonnées du document")
    created_at: datetime = Field(default_factory=datetime.now, description="Horodatage")

class QueryHistory(BaseModel):
    """Modèle pour l'historique des requêtes"""
    query: str = Field(..., description="Texte de la requête")
    response: str
    context_docs: List[str]
    processing_time: float
    cache_hit: bool
    metadata: Dict = Field(default_factory=dict)
    timestamp: datetime = Field(..., description="Horodatage")

class SystemStats(BaseModel):
    """Modèle pour les statistiques du système"""
    total_documents: int = Field(..., description="Nombre total de documents")
    total_queries: int = Field(..., description="Nombre total de requêtes")
    average_processing_time: float
    cache_hit_rate: float
    last_update: datetime = Field(..., description="Date de dernière mise à jour")

class NodeData(BaseModel):
    """Modèle pour les données d'un nœud"""
    node_id: str = Field(..., description="Identifiant du nœud")
    pubkey: str = Field(..., description="Clé publique du nœud")
    alias: str = Field(..., description="Alias du nœud")
    capacity: int = Field(..., description="Capacité totale en sats")
    channels: int = Field(..., description="Nombre de canaux")
    first_seen: datetime = Field(..., description="Date de première apparition")
    last_updated: datetime = Field(..., description="Date de dernière mise à jour")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Métadonnées additionnelles")

    @validator('pubkey')
    def validate_pubkey(cls, v):
        if not re.match(r'^[0-9a-f]{66}$', v):
            raise ValueError('Format de pubkey invalide')
        return v

    @validator('capacity')
    def validate_capacity(cls, v):
        if v < 0:
            raise ValueError('La capacité ne peut pas être négative')
        return v

    @validator('channels')
    def validate_channels(cls, v):
        if v < 0:
            raise ValueError('Le nombre de canaux ne peut pas être négatif')
        return v

class ChannelData(BaseModel):
    """Modèle pour les données d'un canal"""
    channel_id: str = Field(..., description="Identifiant du canal")
    node1_pubkey: str = Field(..., description="Clé publique du nœud 1")
    node2_pubkey: str = Field(..., description="Clé publique du nœud 2")
    capacity: int = Field(..., description="Capacité du canal en sats")
    fee_rate: Dict[str, Any] = Field(..., description="Structure des frais")
    last_updated: datetime = Field(..., description="Date de dernière mise à jour")
    status: str = Field(..., description="Statut du canal")
    balance: Dict[str, int] = Field(..., description="Balance du canal")
    routing_stats: Dict[str, Any] = Field(
        default_factory=lambda: {
            "total_attempts": 0,
            "successful_routes": 0,
            "total_latency": 0.0,
            "last_30_days": {
                "attempts": 0,
                "successes": 0,
                "avg_latency": 0.0
            },
            "last_7_days": {
                "attempts": 0,
                "successes": 0,
                "avg_latency": 0.0
            }
        },
        description="Statistiques de routage"
    )
    performance_metrics: Dict[str, Any] = Field(
        default_factory=lambda: {
            "uptime": 1.0,
            "reliability_score": 1.0,
            "efficiency_score": 1.0,
            "last_performance_update": datetime.now()
        },
        description="Métriques de performance"
    )

    @validator('channel_id')
    def validate_channel_id(cls, v):
        if not re.match(r'^[0-9a-f]{64}$', v):
            raise ValueError('Format de channel_id invalide')
        return v

    @validator('capacity')
    def validate_capacity(cls, v):
        if v < 0:
            raise ValueError('La capacité ne peut pas être négative')
        return v

    @validator('fee_rate')
    def validate_fee_rate(cls, v):
        if not all(isinstance(rate, (int, float)) for rate in v.values()):
            raise ValueError('Les taux de frais doivent être numériques')
        if not all(rate >= 0 for rate in v.values()):
            raise ValueError('Les taux de frais ne peuvent pas être négatifs')
        return v

class NetworkMetrics(BaseModel):
    """Modèle pour les métriques réseau"""
    total_capacity: int = Field(..., description="Capacité totale du réseau")
    total_channels: int = Field(..., description="Nombre total de canaux")
    avg_channel_capacity: float = Field(..., description="Capacité moyenne par canal")
    median_channel_capacity: float = Field(..., description="Capacité médiane par canal")
    last_update: datetime = Field(..., description="Date de dernière mise à jour")

    @validator('total_capacity')
    def validate_total_capacity(cls, v):
        if v < 0:
            raise ValueError('La capacité totale ne peut pas être négative')
        return v

    @validator('total_channels')
    def validate_total_channels(cls, v):
        if v < 0:
            raise ValueError('Le nombre total de canaux ne peut pas être négatif')
        return v

    @validator('avg_channel_capacity', 'median_channel_capacity')
    def validate_capacity_values(cls, v):
        if v < 0:
            raise ValueError('Les valeurs de capacité ne peuvent pas être négatives')
        return v

class NodePerformance(BaseModel):
    """Modèle pour les performances d'un nœud"""
    node_id: str = Field(..., description="Identifiant du nœud")
    success_rate: float = Field(..., description="Taux de succès des paiements")
    avg_fee_rate: float = Field(..., description="Taux de frais moyen")
    total_forwarded: int = Field(..., description="Montant total transféré")
    last_update: datetime = Field(..., description="Date de dernière mise à jour")

class SecurityMetrics(BaseModel):
    """Modèle pour les métriques de sécurité"""
    node_id: str = Field(..., description="Identifiant du nœud")
    uptime: float = Field(..., description="Temps de fonctionnement")
    tor_node: bool = Field(..., description="Nœud Tor")
    watchtower: bool = Field(..., description="Utilisation d'un watchtower")
    last_update: datetime = Field(..., description="Date de dernière mise à jour")

class ChannelRecommendation(BaseModel):
    """Modèle pour les recommandations de canaux"""
    source_node: str = Field(..., description="Nœud source")
    target_node: str = Field(..., description="Nœud cible")
    capacity: int = Field(..., description="Capacité recommandée")
    fee_rate: Dict[str, Any] = Field(..., description="Structure des frais recommandée")
    score: float = Field(..., description="Score de la recommandation")

class LightningMetricsHistory(BaseModel):
    """Modèle pour l'historique des métriques Lightning"""
    node_id: str = Field(..., description="Identifiant du nœud")
    timestamp: datetime = Field(default_factory=datetime.now, description="Horodatage")
    
    # Métriques du nœud
    capacity: int = Field(..., description="Capacité totale en sats")
    channels_count: int = Field(..., description="Nombre de canaux")
    avg_channel_size: float = Field(..., description="Taille moyenne des canaux en sats")
    
    # Métriques de frais
    base_fee_rate: float = Field(..., description="Taux de frais de base moyen en msats")
    fee_rate_ppm: float = Field(..., description="Taux de frais proportionnel moyen en ppm")
    
    # Métriques de performance
    successful_forwards: int = Field(0, description="Nombre de transmissions réussies")
    failed_forwards: int = Field(0, description="Nombre de transmissions échouées")
    total_fees_earned: int = Field(0, description="Total des frais gagnés en msats")
    
    # Balance
    local_balance_ratio: float = Field(..., description="Ratio de la balance locale sur la capacité totale")
    
    # Contexte réseau
    network_position: Optional[Dict[str, float]] = Field(None, description="Position dans le réseau (centralité)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "node_id": "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f",
                "timestamp": "2023-06-01T12:00:00",
                "capacity": 50000000,
                "channels_count": 15,
                "avg_channel_size": 3333333.33,
                "base_fee_rate": 1000,
                "fee_rate_ppm": 500,
                "successful_forwards": 120,
                "failed_forwards": 5,
                "total_fees_earned": 5000000,
                "local_balance_ratio": 0.65,
                "network_position": {"betweenness": 0.025, "degree": 0.018}
            }
        }

class ArchiveSettings(BaseModel):
    """Modèle pour les paramètres d'archivage"""
    collection_name: str = Field(..., description="Nom de la collection à archiver")
    retention_days: int = Field(90, description="Nombre de jours de rétention dans la collection principale")
    archive_after_days: int = Field(365, description="Nombre de jours après lesquels les données sont supprimées de l'archive")
    compression_enabled: bool = Field(True, description="Activer la compression pour les données archivées")
    archiving_frequency: str = Field("daily", description="Fréquence d'archivage ('hourly', 'daily', 'weekly', 'monthly')")
    
    @validator('retention_days')
    def validate_retention_days(cls, v):
        if v < 1:
            raise ValueError("La période de rétention doit être d'au moins 1 jour")
        return v
    
    @validator('archive_after_days')
    def validate_archive_after_days(cls, v, values):
        if 'retention_days' in values and v <= values['retention_days']:
            raise ValueError('La période d\'archive doit être supérieure à la période de rétention')
        return v
    
    @validator('archiving_frequency')
    def validate_archiving_frequency(cls, v):
        valid_frequencies = ['hourly', 'daily', 'weekly', 'monthly']
        if v not in valid_frequencies:
            raise ValueError(f'La fréquence d\'archivage doit être l\'une des suivantes: {", ".join(valid_frequencies)}')
        return v

class FeeChangeHypothesis(BaseModel):
    """Modèle pour les hypothèses de changement de frais"""
    hypothesis_id: str = Field(None, description="Identifiant unique de l'hypothèse")
    node_id: str = Field(..., description="Identifiant du nœud")
    channel_id: str = Field(..., description="Identifiant du canal")
    created_at: datetime = Field(default_factory=datetime.now, description="Date de création")
    
    # État avant le changement
    before_base_fee: int = Field(..., description="Frais de base avant le changement (msats)")
    before_fee_rate: int = Field(..., description="Taux de frais avant le changement (ppm)")
    before_stats: Dict[str, Any] = Field(..., description="Statistiques avant le changement")
    
    # Changement proposé
    new_base_fee: int = Field(..., description="Nouveaux frais de base proposés (msats)")
    new_fee_rate: int = Field(..., description="Nouveau taux de frais proposé (ppm)")
    
    # État après le changement (à remplir une fois le changement appliqué et mesuré)
    change_applied_at: Optional[datetime] = Field(None, description="Date d'application du changement")
    after_stats: Optional[Dict[str, Any]] = Field(None, description="Statistiques après le changement")
    
    # Résultats et conclusions
    evaluation_period_days: int = Field(7, description="Période d'évaluation en jours")
    is_validated: Optional[bool] = Field(None, description="L'hypothèse est-elle validée?")
    conclusion: Optional[str] = Field(None, description="Conclusion de l'hypothèse")
    impact_metrics: Optional[Dict[str, float]] = Field(None, description="Métriques d'impact")
    
    class Config:
        json_schema_extra = {
            "example": {
                "node_id": "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f",
                "channel_id": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                "before_base_fee": 1000,
                "before_fee_rate": 100,
                "before_stats": {
                    "successful_forwards": 120,
                    "failed_forwards": 5,
                    "total_fees_earned": 5000000,
                    "avg_daily_forwards": 18.5
                },
                "new_base_fee": 500,
                "new_fee_rate": 200,
                "evaluation_period_days": 7
            }
        }

class ChannelConfigHypothesis(BaseModel):
    """Modèle pour les hypothèses de configuration de canaux"""
    hypothesis_id: str = Field(None, description="Identifiant unique de l'hypothèse")
    node_id: str = Field(..., description="Identifiant du nœud")
    created_at: datetime = Field(default_factory=datetime.now, description="Date de création")
    
    # État initial
    initial_config: Dict[str, Any] = Field(..., description="Configuration initiale des canaux")
    initial_performance: Dict[str, Any] = Field(..., description="Performance initiale")
    
    # Changements proposés
    proposed_changes: Dict[str, Any] = Field(..., description="Changements proposés")
    
    # État après les changements
    changes_applied_at: Optional[datetime] = Field(None, description="Date d'application des changements")
    after_config: Optional[Dict[str, Any]] = Field(None, description="Configuration après les changements")
    after_performance: Optional[Dict[str, Any]] = Field(None, description="Performance après les changements")
    
    # Résultats et conclusions
    evaluation_period_days: int = Field(30, description="Période d'évaluation en jours")
    is_validated: Optional[bool] = Field(None, description="L'hypothèse est-elle validée?")
    conclusion: Optional[str] = Field(None, description="Conclusion de l'hypothèse")
    impact_metrics: Optional[Dict[str, float]] = Field(None, description="Métriques d'impact")
    
    class Config:
        json_schema_extra = {
            "example": {
                "node_id": "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f",
                "initial_config": {
                    "channel_count": 15,
                    "total_capacity": 50000000,
                    "avg_channel_size": 3333333.33,
                    "channel_distribution": {"small": 5, "medium": 8, "large": 2}
                },
                "initial_performance": {
                    "total_forwards": 120,
                    "success_rate": 0.95,
                    "total_fees_earned": 5000000,
                    "avg_daily_forwards": 18.5
                },
                "proposed_changes": {
                    "add_channels": [
                        {"target_node": "02fc8e97419338c9475c6c06bd8f3ee5c917352809a4024db350a48497036eec86", "capacity": 5000000},
                        {"target_node": "0260fab633066d6f9a0ce7c942cb8edf72c254e491232c48867518f8b8a5a559ec", "capacity": 3000000}
                    ],
                    "close_channels": [
                        {"channel_id": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"}
                    ],
                    "rebalance": True
                },
                "evaluation_period_days": 30
            }
        }

class DataValidationError(Exception):
    """Exception pour les erreurs de validation de données"""
    def __init__(self, message: str, errors: Dict[str, Any]):
        super().__init__(message)
        self.errors = errors

class DataValidator:
    """Classe utilitaire pour la validation des données"""
    
    @staticmethod
    async def validate_node_data(data: Dict[str, Any]) -> NodeData:
        """Valide les données d'un nœud"""
        try:
            return NodeData(**data)
        except Exception as e:
            raise DataValidationError("Erreur de validation des données du nœud", {"error": str(e)})

    @staticmethod
    async def validate_channel_data(data: Dict[str, Any]) -> ChannelData:
        """Valide les données d'un canal"""
        try:
            return ChannelData(**data)
        except Exception as e:
            raise DataValidationError("Erreur de validation des données du canal", {"error": str(e)})

    @staticmethod
    async def validate_network_metrics(data: Dict[str, Any]) -> NetworkMetrics:
        """Valide les métriques du réseau"""
        try:
            return NetworkMetrics(**data)
        except Exception as e:
            raise DataValidationError("Erreur de validation des métriques du réseau", {"error": str(e)})

    @staticmethod
    async def validate_batch_data(data_list: List[Dict[str, Any]], data_type: str) -> List[Any]:
        """Valide un lot de données"""
        validated_data = []
        errors = []
        
        for idx, data in enumerate(data_list):
            try:
                if data_type == "node":
                    validated_data.append(await DataValidator.validate_node_data(data))
                elif data_type == "channel":
                    validated_data.append(await DataValidator.validate_channel_data(data))
                elif data_type == "metrics":
                    validated_data.append(await DataValidator.validate_network_metrics(data))
            except DataValidationError as e:
                errors.append({"index": idx, "error": str(e)})
        
        if errors:
            raise DataValidationError(
                f"Erreurs de validation dans le lot de données {data_type}",
                {"errors": errors}
            )
        
        return validated_data 