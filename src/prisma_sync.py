import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional
from prisma import Prisma

# Ajouter le répertoire parent au chemin Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.redis_operations import RedisOperations
from src.models import (
    NodeData, ChannelData, NetworkMetrics,
    NodePerformance, SecurityMetrics, ChannelRecommendation
)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PrismaSynchronizer:
    """Classe pour synchroniser les données de Redis vers Prisma"""
    
    def __init__(self, redis_ops: RedisOperations):
        self.redis_ops = redis_ops
        self.prisma = Prisma()
        
    async def connect(self):
        """Établit la connexion à Prisma"""
        await self.prisma.connect()
        
    async def disconnect(self):
        """Ferme la connexion à Prisma"""
        await self.prisma.disconnect()
        
    async def sync_all_data(self):
        """Synchronise toutes les données de Redis vers Prisma"""
        try:
            # 1. Synchronisation des nœuds
            logger.info("Synchronisation des nœuds...")
            nodes = await self.redis_ops.get_all_nodes()
            for node in nodes:
                await self._sync_node(node)
                
            # 2. Synchronisation des canaux
            logger.info("Synchronisation des canaux...")
            for node in nodes:
                channels = await self.redis_ops.get_node_channels(node.node_id)
                for channel in channels:
                    await self._sync_channel(channel)
                    
            # 3. Synchronisation des métriques réseau
            logger.info("Synchronisation des métriques réseau...")
            metrics = await self.redis_ops.get_network_metrics()
            if metrics:
                await self._sync_network_metrics(metrics)
                
            # 4. Synchronisation des performances des nœuds
            logger.info("Synchronisation des performances des nœuds...")
            for node in nodes:
                performance = await self.redis_ops.get_node_performance(node.node_id)
                if performance:
                    await self._sync_node_performance(performance)
                    
            # 5. Synchronisation des recommandations de canaux
            logger.info("Synchronisation des recommandations de canaux...")
            for node in nodes:
                recommendations = await self.redis_ops.get_channel_recommendations(node.node_id)
                for rec in recommendations:
                    await self._sync_channel_recommendation(rec)
                    
            logger.info("Synchronisation Prisma terminée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation Prisma: {str(e)}")
            
    async def _sync_node(self, node: NodeData):
        """Synchronise les données d'un nœud"""
        try:
            await self.prisma.node.upsert(
                where={
                    'node_id': node.node_id
                },
                data={
                    'create': {
                        'node_id': node.node_id,
                        'alias': node.alias,
                        'capacity': node.capacity,
                        'channel_count': node.channel_count,
                        'reputation_score': node.reputation_score,
                        'last_update': node.last_update
                    },
                    'update': {
                        'alias': node.alias,
                        'capacity': node.capacity,
                        'channel_count': node.channel_count,
                        'reputation_score': node.reputation_score,
                        'last_update': node.last_update
                    }
                }
            )
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation du nœud {node.node_id}: {str(e)}")
            
    async def _sync_channel(self, channel: ChannelData):
        """Synchronise les données d'un canal"""
        try:
            await self.prisma.channel.upsert(
                where={
                    'channel_id': channel.channel_id
                },
                data={
                    'create': {
                        'channel_id': channel.channel_id,
                        'capacity': channel.capacity,
                        'fee_rate': channel.fee_rate,
                        'balance': channel.balance,
                        'age': channel.age,
                        'last_update': channel.last_update
                    },
                    'update': {
                        'capacity': channel.capacity,
                        'fee_rate': channel.fee_rate,
                        'balance': channel.balance,
                        'age': channel.age,
                        'last_update': channel.last_update
                    }
                }
            )
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation du canal {channel.channel_id}: {str(e)}")
            
    async def _sync_network_metrics(self, metrics: NetworkMetrics):
        """Synchronise les métriques réseau"""
        try:
            await self.prisma.networkMetrics.upsert(
                where={
                    'id': 1  # Une seule entrée de métriques réseau
                },
                data={
                    'create': {
                        'total_capacity': metrics.total_capacity,
                        'total_channels': metrics.total_channels,
                        'total_nodes': metrics.total_nodes,
                        'average_fee_rate': metrics.average_fee_rate,
                        'last_update': metrics.last_update
                    },
                    'update': {
                        'total_capacity': metrics.total_capacity,
                        'total_channels': metrics.total_channels,
                        'total_nodes': metrics.total_nodes,
                        'average_fee_rate': metrics.average_fee_rate,
                        'last_update': metrics.last_update
                    }
                }
            )
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation des métriques réseau: {str(e)}")
            
    async def _sync_node_performance(self, performance: NodePerformance):
        """Synchronise les performances d'un nœud"""
        try:
            await self.prisma.nodePerformance.upsert(
                where={
                    'node_id': performance.node_id
                },
                data={
                    'create': {
                        'node_id': performance.node_id,
                        'uptime': performance.uptime,
                        'success_rate': performance.success_rate,
                        'average_fee_rate': performance.average_fee_rate,
                        'total_capacity': performance.total_capacity,
                        'channel_count': performance.channel_count,
                        'last_update': performance.last_update
                    },
                    'update': {
                        'uptime': performance.uptime,
                        'success_rate': performance.success_rate,
                        'average_fee_rate': performance.average_fee_rate,
                        'total_capacity': performance.total_capacity,
                        'channel_count': performance.channel_count,
                        'last_update': performance.last_update
                    }
                }
            )
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation des performances du nœud {performance.node_id}: {str(e)}")
            
    async def _sync_channel_recommendation(self, recommendation: ChannelRecommendation):
        """Synchronise une recommandation de canal"""
        try:
            await self.prisma.channelRecommendation.upsert(
                where={
                    'id': f"{recommendation.source_node_id}_{recommendation.target_node_id}"
                },
                data={
                    'create': {
                        'source_node_id': recommendation.source_node_id,
                        'target_node_id': recommendation.target_node_id,
                        'score': recommendation.score,
                        'capacity_recommendation': recommendation.capacity_recommendation,
                        'fee_recommendation': recommendation.fee_recommendation,
                        'created_at': recommendation.created_at
                    },
                    'update': {
                        'score': recommendation.score,
                        'capacity_recommendation': recommendation.capacity_recommendation,
                        'fee_recommendation': recommendation.fee_recommendation,
                        'created_at': recommendation.created_at
                    }
                }
            )
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation de la recommandation: {str(e)}")
            
    async def start_periodic_sync(self, interval: int = 3600):
        """Démarre la synchronisation périodique des données"""
        await self.connect()
        try:
            while True:
                await self.sync_all_data()
                await asyncio.sleep(interval)
        finally:
            await self.disconnect()

async def main():
    # Configuration
    redis_url = "redis://localhost:6379"  # À adapter selon votre configuration
    
    # Création des opérations Redis
    redis_ops = RedisOperations(redis_url)
    
    # Création du synchroniseur Prisma
    synchronizer = PrismaSynchronizer(redis_ops)
    
    # Démarrage de la synchronisation périodique
    await synchronizer.start_periodic_sync()

if __name__ == "__main__":
    asyncio.run(main()) 