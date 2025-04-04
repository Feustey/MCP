from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime, timedelta
import asyncio
from src.models import NodeData, ChannelData, ChannelRecommendation, NetworkMetrics
from src.redis_operations import RedisOperations

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkOptimizer:
    """Classe pour optimiser le réseau Lightning avec des fonctionnalités avancées"""
    
    def __init__(self, redis_ops: RedisOperations):
        self.redis_ops = redis_ops
        self.routing_stats = {}  # Statistiques de routage par canal
        self.fee_adjustments = {}  # Ajustements de frais par canal
        self.bottleneck_channels = set()  # Canaux identifiés comme goulets d'étranglement
        
    async def monitor_routing_performance(self, channel_id: str, amount: int, success: bool, latency: float):
        """Surveille les performances de routage d'un canal"""
        try:
            if channel_id not in self.routing_stats:
                self.routing_stats[channel_id] = {
                    "total_attempts": 0,
                    "successful_routes": 0,
                    "total_latency": 0.0,
                    "last_update": datetime.now()
                }
                
            stats = self.routing_stats[channel_id]
            stats["total_attempts"] += 1
            
            if success:
                stats["successful_routes"] += 1
                stats["total_latency"] += latency
                
            # Mise à jour des statistiques dans Redis
            await self.redis_ops.update_channel_stats(
                channel_id,
                stats["successful_routes"] / stats["total_attempts"],
                stats["total_latency"] / stats["successful_routes"] if stats["successful_routes"] > 0 else 0
            )
            
            # Vérification des performances
            await self._check_channel_performance(channel_id)
            
        except Exception as e:
            logger.error(f"Erreur lors du monitoring des performances de routage: {str(e)}")
            
    async def _check_channel_performance(self, channel_id: str):
        """Vérifie les performances d'un canal et ajuste les frais si nécessaire"""
        try:
            stats = self.routing_stats.get(channel_id)
            if not stats:
                return
                
            # Calcul du taux de succès
            success_rate = stats["successful_routes"] / stats["total_attempts"]
            
            # Calcul de la latence moyenne
            avg_latency = stats["total_latency"] / stats["successful_routes"] if stats["successful_routes"] > 0 else float('inf')
            
            # Récupération du canal
            channel = await self.redis_ops.get_channel_data(channel_id)
            if not channel:
                return
                
            # Ajustement des frais en fonction des performances
            await self._adjust_channel_fees(channel, success_rate, avg_latency)
            
            # Vérification des goulets d'étranglement
            if success_rate < 0.7 or avg_latency > 1000:  # Seuils à ajuster
                self.bottleneck_channels.add(channel_id)
                await self._handle_bottleneck(channel)
            else:
                self.bottleneck_channels.discard(channel_id)
                
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des performances: {str(e)}")
            
    async def _adjust_channel_fees(self, channel: ChannelData, success_rate: float, avg_latency: float):
        """Ajuste les frais d'un canal en fonction de ses performances"""
        try:
            # Récupération des frais actuels
            current_fee_rate = channel.fee_rate["fee_rate"]
            
            # Calcul des ajustements
            if success_rate < 0.8:  # Faible taux de succès
                # Augmentation des frais pour réduire le trafic
                new_fee_rate = current_fee_rate * 1.2
            elif success_rate > 0.95 and avg_latency < 500:  # Excellentes performances
                # Réduction des frais pour attirer plus de trafic
                new_fee_rate = current_fee_rate * 0.9
            else:
                # Ajustement mineur basé sur la latence
                if avg_latency > 800:
                    new_fee_rate = current_fee_rate * 1.1
                elif avg_latency < 300:
                    new_fee_rate = current_fee_rate * 0.95
                else:
                    new_fee_rate = current_fee_rate
                    
            # Limites min et max pour les frais
            new_fee_rate = max(0.00001, min(0.001, new_fee_rate))
            
            # Mise à jour des frais si changement significatif
            if abs(new_fee_rate - current_fee_rate) / current_fee_rate > 0.05:
                await self.redis_ops.update_channel_fees(
                    channel.channel_id,
                    {"base_fee": channel.fee_rate["base_fee"], "fee_rate": new_fee_rate}
                )
                logger.info(f"Ajustement des frais pour le canal {channel.channel_id}: {current_fee_rate} -> {new_fee_rate}")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'ajustement des frais: {str(e)}")
            
    async def _handle_bottleneck(self, channel: ChannelData):
        """Gère un canal identifié comme goulet d'étranglement"""
        try:
            # Analyse de l'équilibre du canal
            balance_ratio = channel.balance["local"] / (channel.balance["local"] + channel.balance["remote"])
            
            if balance_ratio > 0.8 or balance_ratio < 0.2:
                # Canal déséquilibré, suggestion de rebalance
                await self._suggest_rebalance(channel)
            else:
                # Canal équilibré mais sous-performant, suggestion de fermeture
                await self._suggest_channel_closure(channel)
                
        except Exception as e:
            logger.error(f"Erreur lors de la gestion du goulet d'étranglement: {str(e)}")
            
    async def _suggest_rebalance(self, channel: ChannelData):
        """Suggère une opération de rebalance pour un canal"""
        try:
            # Calcul de la quantité à rebalancer
            total = channel.balance["local"] + channel.balance["remote"]
            target_ratio = 0.5
            
            if channel.balance["local"] / total > 0.8:
                # Trop de liquidité locale, suggérer un rebalance sortant
                amount = (channel.balance["local"] - total * target_ratio) * 0.8
                direction = "outgoing"
            else:
                # Trop de liquidité distante, suggérer un rebalance entrant
                amount = (total * target_ratio - channel.balance["local"]) * 0.8
                direction = "incoming"
                
            # Création de la suggestion
            suggestion = {
                "channel_id": channel.channel_id,
                "action": "rebalance",
                "amount": amount,
                "direction": direction,
                "priority": "high" if channel.channel_id in self.bottleneck_channels else "medium",
                "created_at": datetime.now()
            }
            
            # Enregistrement de la suggestion
            await this.redis_ops.save_rebalance_suggestion(suggestion)
            logger.info(f"Suggestion de rebalance pour le canal {channel.channel_id}: {amount} sats {direction}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la suggestion de rebalance: {str(e)}")
            
    async def _suggest_channel_closure(self, channel: ChannelData):
        """Suggère la fermeture d'un canal sous-performant"""
        try:
            # Vérification des performances
            stats = self.routing_stats.get(channel.channel_id, {})
            success_rate = stats.get("successful_routes", 0) / stats.get("total_attempts", 1)
            
            if success_rate < 0.5:  # Seuil à ajuster
                # Création de la suggestion
                suggestion = {
                    "channel_id": channel.channel_id,
                    "action": "close",
                    "reason": "low_success_rate",
                    "priority": "high" if channel.channel_id in self.bottleneck_channels else "medium",
                    "created_at": datetime.now()
                }
                
                # Enregistrement de la suggestion
                await this.redis_ops.save_channel_closure_suggestion(suggestion)
                logger.info(f"Suggestion de fermeture pour le canal {channel.channel_id}")
                
        except Exception as e:
            logger.error(f"Erreur lors de la suggestion de fermeture: {str(e)}")
            
    async def analyze_node_health(self, node_id: str) -> Dict:
        """Analyse la santé globale d'un nœud"""
        try:
            # Récupération des données du nœud
            node = await this.redis_ops.get_node_data(node_id)
            if not node:
                return {}
                
            # Récupération des canaux du nœud
            channels = await this.redis_ops.get_node_channels(node_id)
            if not channels:
                return {}
                
            # Calcul des métriques
            total_channels = len(channels)
            balanced_channels = sum(1 for c in channels if abs(c.balance["local"] / (c.balance["local"] + c.balance["remote"]) - 0.5) < 0.2)
            bottleneck_channels = sum(1 for c in channels if c.channel_id in self.bottleneck_channels)
            
            # Calcul des performances de routage
            routing_success = 0
            total_routes = 0
            total_latency = 0
            successful_routes = 0
            
            for channel in channels:
                stats = self.routing_stats.get(channel.channel_id, {})
                routing_success += stats.get("successful_routes", 0)
                total_routes += stats.get("total_attempts", 0)
                total_latency += stats.get("total_latency", 0)
                successful_routes += stats.get("successful_routes", 0)
                
            avg_success_rate = routing_success / total_routes if total_routes > 0 else 0
            avg_latency = total_latency / successful_routes if successful_routes > 0 else 0
            
            # Calcul du score de santé
            health_score = (
                (balanced_channels / total_channels) * 0.3 +
                (1 - bottleneck_channels / total_channels) * 0.3 +
                avg_success_rate * 0.2 +
                (1 - min(avg_latency / 1000, 1)) * 0.2
            )
            
            return {
                "node_id": node_id,
                "health_score": health_score,
                "total_channels": total_channels,
                "balanced_channels": balanced_channels,
                "bottleneck_channels": bottleneck_channels,
                "routing_success_rate": avg_success_rate,
                "average_latency": avg_latency,
                "last_update": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de la santé du nœud: {str(e)}")
            return {}
            
    async def get_optimization_suggestions(self, node_id: str) -> List[Dict]:
        """Génère des suggestions d'optimisation pour un nœud"""
        try:
            suggestions = []
            
            # Analyse de la santé du nœud
            health = await this.analyze_node_health(node_id)
            if not health:
                return []
                
            # Suggestions basées sur la santé
            if health["health_score"] < 0.7:
                if health["balanced_channels"] / health["total_channels"] < 0.6:
                    suggestions.append({
                        "type": "rebalance_strategy",
                        "priority": "high",
                        "message": "Stratégie de rebalance recommandée pour améliorer l'équilibre des canaux",
                        "created_at": datetime.now()
                    })
                    
                if health["bottleneck_channels"] > health["total_channels"] * 0.2:
                    suggestions.append({
                        "type": "channel_closure",
                        "priority": "medium",
                        "message": "Considérer la fermeture des canaux sous-performants",
                        "created_at": datetime.now()
                    })
                    
                if health["routing_success_rate"] < 0.8:
                    suggestions.append({
                        "type": "fee_adjustment",
                        "priority": "high",
                        "message": "Ajuster les frais pour améliorer les performances de routage",
                        "created_at": datetime.now()
                    })
                    
            # Suggestions de rebalance spécifiques
            rebalance_suggestions = await this.redis_ops.get_rebalance_suggestions(node_id)
            suggestions.extend(rebalance_suggestions)
            
            # Suggestions de fermeture de canaux
            closure_suggestions = await this.redis_ops.get_channel_closure_suggestions(node_id)
            suggestions.extend(closure_suggestions)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération des suggestions: {str(e)}")
            return [] 