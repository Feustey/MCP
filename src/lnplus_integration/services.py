from typing import List, Dict, Any, Optional
from datetime import datetime
from .client import LNPlusClient
from .models import (
    LightningSwap,
    SwapCreationRequest,
    NodeMetrics,
    Rating,
    RatingCreate
)

class SwapService:
    def __init__(self, lnplus_client: LNPlusClient):
        self.client = lnplus_client

    async def get_available_swaps(
        self,
        min_capacity: Optional[int] = None,
        max_participants: Optional[int] = None
    ) -> List[LightningSwap]:
        """Récupère les swaps disponibles avec filtres"""
        filters = {}
        if min_capacity:
            filters["min_capacity"] = min_capacity
        if max_participants:
            filters["max_participants"] = max_participants
        return await self.client.get_swaps(filters)

    async def create_swap(self, swap_request: SwapCreationRequest) -> LightningSwap:
        """Crée un nouveau swap"""
        return await self.client.create_swap(swap_request)

class NodeMetricsService:
    def __init__(self, lnplus_client: LNPlusClient):
        self.client = lnplus_client

    async def get_enhanced_metrics(self, node_id: str) -> NodeMetrics:
        """Récupère les métriques enrichies d'un nœud"""
        return await self.client.get_node(node_id)

    async def get_node_reputation(self, node_id: str) -> Dict[str, Any]:
        """Récupère la réputation complète d'un nœud"""
        return await self.client.get_node_reputation(node_id)

class RatingService:
    def __init__(self, lnplus_client: LNPlusClient):
        self.client = lnplus_client

    async def create_rating(
        self,
        target_node_id: str,
        is_positive: bool,
        comment: str,
        from_node_id: str
    ) -> Rating:
        """Crée une nouvelle notation"""
        rating = await self.client.create_rating(target_node_id, is_positive, comment)
        rating.from_node_id = from_node_id
        return rating

    async def get_node_ratings(self, node_id: str) -> Dict[str, Any]:
        """Récupère toutes les notations d'un nœud"""
        return await self.client.get_node_reputation(node_id)

class RecommendationService:
    def __init__(self, lnplus_client: LNPlusClient):
        self.client = lnplus_client

    async def get_enhanced_recommendations(
        self,
        node_id: str,
        min_capacity: int = 100000
    ) -> List[Dict[str, Any]]:
        """Génère des recommandations enrichies pour un nœud"""
        # Récupérer les métriques du nœud
        node_metrics = await self.client.get_node(node_id)
        
        # Récupérer les swaps disponibles
        swaps = await self.client.get_swaps({
            "min_capacity": min_capacity
        })
        
        # Générer les recommandations
        recommendations = []
        for swap in swaps:
            if len(swap.participants) < swap.participant_max_count:
                recommendations.append({
                    "type": "swap",
                    "swap_id": swap.id,
                    "capacity": swap.capacity_sats,
                    "participants": len(swap.participants),
                    "max_participants": swap.participant_max_count,
                    "score": self._calculate_swap_score(swap, node_metrics)
                })
        
        return sorted(recommendations, key=lambda x: x["score"], reverse=True)

    def _calculate_swap_score(self, swap: LightningSwap, node_metrics: NodeMetrics) -> float:
        """Calcule un score pour un swap potentiel"""
        score = 0.0
        
        # Facteur de capacité
        capacity_factor = min(swap.capacity_sats / node_metrics.capacity, 1.0)
        score += capacity_factor * 0.4
        
        # Facteur de réputation
        reputation_factor = (
            node_metrics.positive_ratings /
            (node_metrics.positive_ratings + node_metrics.negative_ratings + 1)
        )
        score += reputation_factor * 0.3
        
        # Facteur de participation
        participation_factor = 1 - (len(swap.participants) / swap.participant_max_count)
        score += participation_factor * 0.3
        
        return score 