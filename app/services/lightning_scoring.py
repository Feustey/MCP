# app/services/lightning_scoring.py
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any

import numpy as np
from motor.core import AgnosticCollection, AgnosticDatabase
from bson import ObjectId

from app.models import (
    LightningNode, LightningChannel, LightningNodeScore, ScoreMetrics,
    ScoreMetadata, DetailedScores, HistoricalScorePoint, Recommendation,
    RecommendationPriority, NodeRecommendations, ScoringConfig
)

logger = logging.getLogger(__name__)

# Collections MongoDB
NODES_COLLECTION = "lightning_nodes"
CHANNELS_COLLECTION = "lightning_channels"
SCORES_COLLECTION = "lightning_scores"
CONFIG_COLLECTION = "lightning_config"

# Configuration par défaut
DEFAULT_CONFIG = {
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

class LightningScoreService:
    """Service responsable du calcul et de la gestion des scores des nœuds Lightning."""
    
    def __init__(self, db: AgnosticDatabase):
        """Initialise le service avec une instance de base de données."""
        self.db = db
        self.nodes_collection = db[NODES_COLLECTION]
        self.channels_collection = db[CHANNELS_COLLECTION]
        self.scores_collection = db[SCORES_COLLECTION]
        self.config_collection = db[CONFIG_COLLECTION]
        self._config = None
    
    async def get_config(self) -> Dict[str, Any]:
        """Récupère la configuration actuelle ou utilise la configuration par défaut."""
        if self._config is None:
            config_doc = await self.config_collection.find_one({"_id": "scoring_config"})
            if config_doc:
                self._config = config_doc
            else:
                # Initialiser avec la configuration par défaut
                self._config = DEFAULT_CONFIG
                await self.config_collection.insert_one({"_id": "scoring_config", **self._config})
        
        return self._config
    
    async def update_config(self, config: ScoringConfig, tenant_id: str) -> Dict[str, Any]:
        """Met à jour la configuration de scoring."""
        config_dict = config.dict()
        result = await self.config_collection.update_one(
            {"_id": "scoring_config", "tenant_id": tenant_id},
            {"$set": config_dict},
            upsert=True
        )
        
        # Mettre à jour le cache
        self._config = config_dict
        
        # Si la config a été modifiée, recalculer tous les scores
        if result.modified_count > 0 or result.upserted_id:
            # Lancer le recalcul en arrière-plan
            asyncio.create_task(self.recalculate_all_scores(force=True, tenant_id=tenant_id))
        
        return self._config
    
    async def get_node_score(self, node_id: str, tenant_id: str) -> Optional[LightningNodeScore]:
        """Récupère le score d'un nœud par son ID."""
        score = await self.scores_collection.find_one({"node_id": node_id, "tenant_id": tenant_id})
        return score
    
    async def get_all_scores(self, page: int = 1, limit: int = 100, 
                           sort_field: str = "metrics.composite", 
                           sort_order: int = -1,
                           tenant_id: str = None,
                           filter_query: Dict = None) -> Dict[str, Any]:
        """
        Récupère les scores de tous les nœuds avec pagination, tri et filtrage.
        
        Args:
            page: Numéro de page (commence à 1)
            limit: Nombre d'éléments par page
            sort_field: Champ de tri
            sort_order: Ordre de tri (1 pour ascendant, -1 pour descendant)
            tenant_id: ID du locataire
            filter_query: Requête de filtrage MongoDB
        
        Returns:
            Dict contenant les scores et les métadonnées de pagination
        """
        if filter_query is None:
            filter_query = {}
        if tenant_id:
            filter_query["tenant_id"] = tenant_id
        
        skip = (page - 1) * limit
        
        # Construire le pipeline d'agrégation
        pipeline = [
            {"$match": filter_query},
            {"$sort": {sort_field: sort_order}},
            {"$skip": skip},
            {"$limit": limit}
        ]
        
        # Exécuter la requête
        cursor = self.scores_collection.aggregate(pipeline)
        scores = await cursor.to_list(length=limit)
        
        # Compter le nombre total d'éléments filtrés
        total = await self.scores_collection.count_documents(filter_query)
        
        return {
            "data": scores,
            "metadata": {
                "total": total,
                "page": page,
                "limit": limit
            }
        }
    
    async def get_detailed_node_score(self, node_id: str, tenant_id: str) -> Dict[str, Any]:
        """
        Récupère les informations détaillées de score pour un nœud.
        
        Args:
            node_id: ID du nœud
            tenant_id: ID du locataire
        
        Returns:
            Dict contenant les scores détaillés et l'historique
        """
        # Récupérer le score actuel
        current_score = await self.scores_collection.find_one({"node_id": node_id, "tenant_id": tenant_id})
        if not current_score:
            return None
        
        # Récupérer les détails du nœud
        node = await self.nodes_collection.find_one({"public_key": node_id})
        
        # Calculer les scores détaillés
        detailed_scores = await self._calculate_detailed_scores(node_id)
        
        # Récupérer l'historique des scores
        history_cursor = self.scores_collection.find(
            {"node_id": node_id, "tenant_id": tenant_id},
            {"timestamp": 1, "metrics.composite": 1}
        ).sort("timestamp", -1).limit(30)
        
        history = await history_cursor.to_list(length=30)
        historical_data = [
            {"timestamp": h["timestamp"], "score": h["metrics"]["composite"]}
            for h in history
        ]
        
        return {
            "node_id": node_id,
            "detailed_scores": detailed_scores,
            "historical_data": historical_data
        }
    
    async def _calculate_detailed_scores(self, node_id: str) -> DetailedScores:
        """Calcule les scores détaillés pour un nœud."""
        # Récupérer les canaux du nœud
        channels = await self.channels_collection.find(
            {"$or": [{"node1_pub": node_id}, {"node2_pub": node_id}]}
        ).to_list(length=None)
        
        # Récupérer tous les nœuds pour les calculs de centralité
        all_nodes = await self.nodes_collection.find().to_list(length=None)
        
        # Calculer les métriques de centralité
        degree_centrality = len(channels)
        betweenness = await self._calculate_betweenness(node_id, all_nodes, channels)
        
        # Calculer les métriques de performance
        uptime = await self._calculate_uptime(node_id)
        success_rate = await self._calculate_success_rate(node_id)
        
        # Calculer les métriques de capacité
        total_capacity = sum(channel["capacity"] for channel in channels)
        avg_capacity = total_capacity / max(1, degree_centrality)
        
        return {
            "centrality": {
                "degree": degree_centrality,
                "betweenness": betweenness
            },
            "performance": {
                "uptime": uptime,
                "success_rate": success_rate
            },
            "capacity": {
                "total": total_capacity,
                "average_per_channel": avg_capacity
            }
        }
    
    async def _calculate_betweenness(
        self, node_id: str, all_nodes: List[dict], channels: List[dict]
    ) -> float:
        """
        Calcule la centralité d'intermédiarité approximative du nœud.
        Cette implémentation est une approximation simplifiée.
        """
        # Dans une implémentation réelle, on utiliserait un algorithme de graphe complet.
        # Pour cette démonstration, nous utilisons une approximation.
        num_nodes = len(all_nodes)
        if num_nodes <= 2:
            return 0
        
        # Extraire le graphe des canaux
        edges = {}
        for channel in channels:
            node1 = channel["node1_pub"]
            node2 = channel["node2_pub"]
            if node1 not in edges:
                edges[node1] = []
            if node2 not in edges:
                edges[node2] = []
            edges[node1].append(node2)
            edges[node2].append(node1)
        
        # Calculer le nombre de chemins passant par ce nœud
        # Dans une implémentation réelle, on calculerait tous les plus courts chemins
        num_paths_through_node = 0
        sampled_nodes = min(100, num_nodes)  # Limiter l'échantillon pour des raisons de performance
        
        for _ in range(sampled_nodes):
            # Prendre 2 nœuds aléatoires
            source = all_nodes[np.random.randint(0, num_nodes)]["public_key"]
            target = all_nodes[np.random.randint(0, num_nodes)]["public_key"]
            
            if source == target or source == node_id or target == node_id:
                continue
            
            # Vérifier si un chemin existe entre source et target passant par node_id
            # C'est une simplification - en réalité, on vérifierait tous les plus courts chemins
            if source in edges and node_id in edges[source] and target in edges and node_id in edges[target]:
                num_paths_through_node += 1
        
        # Normaliser
        max_possible_paths = sampled_nodes * (sampled_nodes - 1) / 2
        betweenness = num_paths_through_node / max(1, max_possible_paths)
        
        return betweenness * 100  # Convertir en pourcentage
    
    async def _calculate_uptime(self, node_id: str) -> float:
        """
        Calcule le taux de disponibilité du nœud.
        Dans une implémentation réelle, on utiliserait des données historiques.
        """
        # Simulation pour la démonstration
        # On suppose que nous avons une collection d'événements de nœuds qui enregistre l'uptime
        return np.random.uniform(90, 100)  # Valeur entre 90% et 100% pour la démo
    
    async def _calculate_success_rate(self, node_id: str) -> float:
        """
        Calcule le taux de réussite des transactions.
        Dans une implémentation réelle, on utiliserait des données de transactions.
        """
        # Simulation pour la démonstration
        return np.random.uniform(85, 100)  # Valeur entre 85% et 100% pour la démo
    
    async def calculate_node_score(self, node_id: str, tenant_id: str) -> LightningNodeScore:
        """
        Calcule le score complet d'un nœud Lightning.
        
        Args:
            node_id: ID du nœud
            tenant_id: ID du locataire
        
        Returns:
            LightningNodeScore contenant toutes les métriques
        """
        # Récupérer le nœud
        node = await self.nodes_collection.find_one({"public_key": node_id})
        if not node:
            return None
        
        # Récupérer la configuration
        config = await self.get_config()
        weights = config["weights"]
        
        # Calculer les scores détaillés
        detailed = await self._calculate_detailed_scores(node_id)
        
        # Normaliser les scores (sur 100)
        # Ces facteurs de normalisation devraient être ajustés en fonction des données réelles
        degree_norm = min(100, detailed["centrality"]["degree"] / 2)
        betweenness_norm = detailed["centrality"]["betweenness"]
        uptime_norm = detailed["performance"]["uptime"]
        success_rate_norm = detailed["performance"]["success_rate"]
        capacity_norm = min(100, np.log10(max(1, detailed["capacity"]["total"])) / 10 * 100)
        
        # Calculer les scores composants
        centrality_score = (degree_norm + betweenness_norm) / 2
        reliability_score = (uptime_norm + success_rate_norm) / 2
        performance_score = capacity_norm
        
        # Calculer le score composite
        composite_score = (
            weights["centrality"] * centrality_score +
            weights["reliability"] * reliability_score +
            weights["performance"] * performance_score
        )
        
        # Créer les métriques
        metrics = ScoreMetrics(
            centrality=centrality_score,
            reliability=reliability_score,
            performance=performance_score,
            composite=composite_score
        )
        
        # Créer les métadonnées
        metadata = ScoreMetadata(
            calculation_version="1.0.0",
            data_sources=["simulation", "lnd_grpc"]  # Dans une implémentation réelle, on indiquerait les sources réelles
        )
        
        # Créer et retourner le score
        score = LightningNodeScore(
            node_id=node_id,
            timestamp=datetime.utcnow(),
            metrics=metrics,
            metadata=metadata
        )
        
        # Sauvegarder le score dans la base de données
        score_dict = {k: v for k, v in score.dict(exclude={"id"}).items()}
        score_dict["tenant_id"] = tenant_id
        await self.scores_collection.insert_one(score_dict)
        
        return score
    
    async def recalculate_all_scores(self, force: bool = False, tenant_id: str = None) -> int:
        """
        Recalcule les scores pour tous les nœuds.
        
        Args:
            force: Si True, recalcule même les scores récents
            tenant_id: ID du locataire
        
        Returns:
            Nombre de scores recalculés
        """
        logger.info("Démarrage du recalcul de tous les scores")
        
        # Récupérer tous les nœuds
        nodes = await self.nodes_collection.find().to_list(length=None)
        count = 0
        
        for node in nodes:
            node_id = node["public_key"]
            
            # Vérifier si un recalcul est nécessaire
            if not force:
                # Vérifier si un score récent existe
                recent_score = await self.scores_collection.find_one(
                    {"node_id": node_id, "timestamp": {"$gt": datetime.utcnow() - timedelta(days=1)}}
                )
                if recent_score:
                    logger.debug(f"Score récent trouvé pour {node_id}, pas de recalcul nécessaire")
                    continue
            
            # Recalculer le score
            try:
                await self.calculate_node_score(node_id, tenant_id)
                count += 1
                logger.debug(f"Score recalculé pour {node_id}")
            except Exception as e:
                logger.error(f"Erreur lors du calcul du score pour {node_id}: {e}")
        
        logger.info(f"Recalcul des scores terminé: {count} scores mis à jour")
        return count
    
    async def recalculate_scores(self, node_ids: Optional[List[str]], force: bool, tenant_id: str) -> int:
        """
        Recalcule les scores pour les nœuds spécifiés.
        
        Args:
            node_ids: Liste des IDs de nœuds à recalculer (tous si None)
            force: Si True, recalcule même les scores récents
            tenant_id: ID du locataire
        
        Returns:
            Nombre de scores recalculés
        """
        if node_ids is None:
            return await self.recalculate_all_scores(force, tenant_id)
        
        # Filtrer les scores à recalculer par tenant_id
        query = {"tenant_id": tenant_id}
        if node_ids:
            query["node_id"] = {"$in": node_ids}
        
        count = 0
        for node_id in node_ids:
            # Vérifier si le nœud existe
            node = await self.nodes_collection.find_one({"public_key": node_id})
            if not node:
                logger.warning(f"Nœud {node_id} non trouvé, ignoré")
                continue
            
            # Vérifier si un recalcul est nécessaire
            if not force:
                recent_score = await self.scores_collection.find_one(
                    {"node_id": node_id, "timestamp": {"$gt": datetime.utcnow() - timedelta(days=1)}}
                )
                if recent_score:
                    logger.debug(f"Score récent trouvé pour {node_id}, pas de recalcul nécessaire")
                    continue
            
            # Recalculer le score
            try:
                await self.calculate_node_score(node_id, tenant_id)
                count += 1
                logger.debug(f"Score recalculé pour {node_id}")
            except Exception as e:
                logger.error(f"Erreur lors du calcul du score pour {node_id}: {e}")
        
        return count
    
    async def generate_recommendations(self, node_id: str, tenant_id: str) -> NodeRecommendations:
        """
        Génère des recommandations pour améliorer le score d'un nœud.
        
        Args:
            node_id: ID du nœud
            tenant_id: ID du locataire
        
        Returns:
            NodeRecommendations contenant une liste de recommandations
        """
        # Récupérer les scores détaillés
        detailed_scores = await self._calculate_detailed_scores(node_id)
        
        # Récupérer le score global
        node_score = await self.get_node_score(node_id, tenant_id)
        if not node_score:
            return None
        
        # Liste pour stocker les recommandations
        recommendations = []
        
        # Recommandations basées sur la centralité
        degree = detailed_scores["centrality"]["degree"]
        if degree < 10:
            recommendations.append(Recommendation(
                type="connectivity",
                description="Augmentez le nombre de canaux pour améliorer la connectivité du réseau",
                priority=RecommendationPriority.HIGH,
                impact_score=30.0,
                implementation_difficulty="Moyenne"
            ))
        
        # Recommandations basées sur la capacité
        avg_capacity = detailed_scores["capacity"]["average_per_channel"]
        if avg_capacity < 1_000_000:  # 1M sats
            recommendations.append(Recommendation(
                type="liquidity",
                description="Augmentez la capacité moyenne de vos canaux pour améliorer la liquidité",
                priority=RecommendationPriority.MEDIUM,
                impact_score=25.0,
                implementation_difficulty="Difficile"
            ))
        
        # Recommandations basées sur la performance
        uptime = detailed_scores["performance"]["uptime"]
        if uptime < 95:
            recommendations.append(Recommendation(
                type="reliability",
                description="Améliorez la disponibilité de votre nœud pour augmenter sa fiabilité",
                priority=RecommendationPriority.HIGH,
                impact_score=35.0,
                implementation_difficulty="Moyenne"
            ))
        
        success_rate = detailed_scores["performance"]["success_rate"]
        if success_rate < 90:
            recommendations.append(Recommendation(
                type="routing",
                description="Optimisez vos paramètres de routage pour améliorer le taux de succès des paiements",
                priority=RecommendationPriority.MEDIUM,
                impact_score=20.0,
                implementation_difficulty="Facile"
            ))
        
        return NodeRecommendations(
            node_id=node_id,
            recommendations=recommendations
        ) 