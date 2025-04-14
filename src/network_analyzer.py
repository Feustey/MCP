from typing import List, Dict, Optional
import logging
from datetime import datetime
from src.models import NodeData, ChannelData, ChannelRecommendation
from src.redis_operations import RedisOperations

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkAnalyzer:
    """Classe pour analyser le réseau Lightning et recommander les meilleures connexions"""
    
    def __init__(self, redis_ops: RedisOperations):
        self.redis_ops = redis_ops
        
    async def analyze_node_connections(self, source_node_id: str) -> List[ChannelRecommendation]:
        """Analyse et recommande les meilleures connexions pour un nœud source"""
        try:
            # Récupération des données du nœud source
            source_node = await self.redis_ops.get_node_data(source_node_id)
            if not source_node:
                logger.error(f"Nœud source {source_node_id} non trouvé")
                return []
                
            # Récupération de tous les nœuds disponibles
            all_nodes = await self.redis_ops.get_all_nodes()
            if not all_nodes:
                logger.error("Aucun nœud disponible pour l'analyse")
                return []
                
            recommendations = []
            for target_node in all_nodes:
                if target_node.node_id == source_node_id:
                    continue
                    
                # Analyse de la connexion potentielle
                recommendation = await self._analyze_potential_connection(
                    source_node,
                    target_node
                )
                if recommendation:
                    recommendations.append(recommendation)
                    
            # Tri des recommandations par score
            recommendations.sort(key=lambda x: x.score, reverse=True)
            return recommendations[:10]  # Retourne les 10 meilleures recommandations
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des connexions: {str(e)}")
            return []
            
    async def _analyze_potential_connection(
        self,
        source_node: NodeData,
        target_node: NodeData
    ) -> Optional[ChannelRecommendation]:
        """Analyse une connexion potentielle entre deux nœuds"""
        try:
            # Calcul du score de base
            base_score = 0.0
            
            # 1. Capacité du nœud cible (30% du score)
            target_capacity_score = min(target_node.capacity / 1_000_000_000, 1.0) * 0.3
            
            # 2. Nombre de canaux du nœud cible (20% du score)
            target_channels_score = min(target_node.channel_count / 100, 1.0) * 0.2
            
            # 3. Score de réputation du nœud cible (20% du score)
            reputation_score = (target_node.reputation_score / 100) * 0.2
            
            # 4. Diversité géographique (15% du score)
            # À implémenter si les données de localisation sont disponibles
            geographic_score = 0.15
            
            # 5. Équilibre des canaux (15% du score)
            balance_score = await self._calculate_balance_score(target_node) * 0.15
            
            # Calcul du score final
            final_score = (
                target_capacity_score +
                target_channels_score +
                reputation_score +
                geographic_score +
                balance_score
            )
            
            # Création de la recommandation
            capacity_rec = await self._calculate_recommended_capacity(
                source_node,
                target_node
            )
            fee_rec = await self._calculate_recommended_fees(
                source_node,
                target_node
            )
            
            recommendation = ChannelRecommendation(
                source_node_id=source_node.node_id,
                target_node_id=target_node.node_id,
                score=final_score,
                capacity_recommendation=capacity_rec,
                fee_recommendation=fee_rec,
                created_at=datetime.now()
            )
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de la connexion: {str(e)}")
            return None
            
    async def _calculate_balance_score(self, node: NodeData) -> float:
        """Calcule le score d'équilibre des canaux d'un nœud"""
        try:
            # Récupération des canaux du nœud
            channels = await self.redis_ops.get_node_channels(node.node_id)
            if not channels:
                return 0.0
                
            balanced_channels = 0
            for channel in channels:
                # Un canal est considéré équilibré si la différence entre local et remote
                # est inférieure à 20% de la capacité totale
                total = channel.balance["local"] + channel.balance["remote"]
                if total > 0:
                    diff = abs(channel.balance["local"] - channel.balance["remote"])
                    if diff / total < 0.2:
                        balanced_channels += 1
                        
            return balanced_channels / len(channels)
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul du score d'équilibre: {str(e)}")
            return 0.0
            
    async def _calculate_recommended_capacity(
        self,
        source_node: NodeData,
        target_node: NodeData
    ) -> Dict[str, float]:
        """
        Calcule la capacité recommandée pour un nouveau canal.
        
        Args:
            source_node: Données du nœud source
            target_node: Données du nœud cible
            
        Returns:
            Dict contenant les capacités min et max recommandées en BTC
        """
        try:
            # La capacité recommandée est basée sur :
            # 1. La capacité moyenne des canaux existants du nœud cible
            # 2. La capacité disponible du nœud source
            # 3. Un facteur de réduction pour éviter les canaux trop grands
            
            target_channels = await self.redis_ops.get_node_channels(target_node.node_id)
            if not target_channels:
                return {"min": 0.01, "max": 0.1}  # Valeurs par défaut en BTC
                
            # Calcul de la capacité moyenne des canaux existants en BTC
            total_capacity = sum(channel.capacity for channel in target_channels)
            avg_capacity = (total_capacity / len(target_channels)) / 100_000_000  # Conversion en BTC
            
            # Facteur de réduction pour éviter les canaux trop grands
            reduction_factor = 0.8
            
            # Calcul des capacités min et max recommandées en BTC
            min_capacity = max(0.01, min(0.05, avg_capacity * 0.5 * reduction_factor))
            max_capacity = min(0.1, avg_capacity * 1.5 * reduction_factor)
            
            # S'assurer que min <= max
            if min_capacity > max_capacity:
                min_capacity = max_capacity * 0.5
            
            return {
                "min": min_capacity,
                "max": max_capacity
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul de la capacité recommandée: {str(e)}")
            return {"min": 0.01, "max": 0.1}  # Valeurs par défaut en BTC
            
    async def _calculate_recommended_fees(
        self,
        source_node: NodeData,
        target_node: NodeData
    ) -> Dict[str, float]:
        """
        Calcule les frais recommandés pour un nouveau canal.
        
        Args:
            source_node: Données du nœud source
            target_node: Données du nœud cible
            
        Returns:
            Dict contenant les frais de base et le taux recommandés
        """
        try:
            # Les frais recommandés sont basés sur :
            # 1. Les frais moyens des canaux existants du nœud cible
            # 2. La position du nœud dans le réseau
            # 3. Un facteur d'ajustement basé sur la liquidité
            
            target_channels = await self.redis_ops.get_node_channels(target_node.node_id)
            if not target_channels:
                return {"base_fee": 1000, "fee_rate": 0.00008}  # Valeurs par défaut
                
            # Calcul des frais moyens
            total_base_fee = sum(channel.fee_rate["base_fee"] for channel in target_channels)
            total_fee_rate = sum(channel.fee_rate["fee_rate"] for channel in target_channels)
            
            avg_base_fee = total_base_fee / len(target_channels)
            avg_fee_rate = total_fee_rate / len(target_channels)
            
            # Facteur d'ajustement basé sur la liquidité
            liquidity_factor = 0.8  # Réduction des frais pour les nœuds liquides
            
            return {
                "base_fee": int(avg_base_fee * liquidity_factor),
                "fee_rate": avg_fee_rate * liquidity_factor
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des frais recommandés: {str(e)}")
            return {"base_fee": 1000, "fee_rate": 0.00008}  # Valeurs par défaut
            
    async def get_network_insights(self) -> Dict:
        """Génère des insights sur l'état du réseau"""
        try:
            # Récupération des métriques réseau
            metrics = await self.redis_ops.get_network_metrics()
            if not metrics:
                return {}
                
            # Récupération des nœuds
            nodes = await self.redis_ops.get_all_nodes()
            if not nodes:
                return {}
                
            # Calcul des statistiques
            total_nodes = len(nodes)
            total_channels = sum(node.channel_count for node in nodes)
            total_capacity = sum(node.capacity for node in nodes)
            
            # Calcul des moyennes
            avg_capacity = total_capacity / total_nodes if total_nodes > 0 else 0
            avg_channels = total_channels / total_nodes if total_nodes > 0 else 0
            avg_reputation = sum(node.reputation_score for node in nodes) / total_nodes if total_nodes > 0 else 0
            
            return {
                "total_nodes": total_nodes,
                "total_channels": total_channels,
                "total_capacity": total_capacity,
                "average_capacity": avg_capacity,
                "average_channels": avg_channels,
                "average_reputation": avg_reputation,
                "network_fee_rate": metrics.average_fee_rate,
                "last_update": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération des insights: {str(e)}")
            return {} 