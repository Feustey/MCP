from prisma import Prisma
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PrismaOperations:
    def __init__(self):
        self.prisma = Prisma(
            datasource={
                "url": os.getenv("DATABASE_URL"),
                "direct_url": os.getenv("DIRECT_DATABASE_URL")
            }
        )
        
    async def connect(self):
        """Établit la connexion avec la base de données."""
        await self.prisma.connect()
        
    async def disconnect(self):
        """Ferme la connexion avec la base de données."""
        await self.prisma.disconnect()
        
    async def get_node_data(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les données d'un nœud."""
        try:
            node = await self.prisma.node.find_unique(
                where={'node_id': node_id},
                include={
                    'channels': True,
                    'performances': True
                }
            )
            return node
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données du nœud: {str(e)}")
            return None
            
    async def get_network_metrics(self) -> Optional[Dict[str, Any]]:
        """Récupère les métriques globales du réseau."""
        try:
            metrics = await self.prisma.networkmetrics.find_first()
            return metrics
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métriques réseau: {str(e)}")
            return None
            
    async def get_channel_recommendations(self, node_id: str) -> List[Dict[str, Any]]:
        """Récupère les recommandations de canaux pour un nœud."""
        try:
            recommendations = await self.prisma.channelrecommendation.find_many(
                where={
                    'OR': [
                        {'source_node_id': node_id},
                        {'target_node_id': node_id}
                    ]
                },
                include={
                    'source_node': True,
                    'target_node': True
                }
            )
            return recommendations
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des recommandations: {str(e)}")
            return []
            
    async def get_node_performance(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les performances d'un nœud."""
        try:
            performance = await self.prisma.nodeperformance.find_first(
                where={'node_id': node_id},
                order={'last_update': 'desc'}
            )
            return performance
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des performances: {str(e)}")
            return None 