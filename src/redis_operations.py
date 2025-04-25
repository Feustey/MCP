import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import redis.asyncio as redis
import logging
from models import (
    Document, QueryHistory, SystemStats,
    NodeData, ChannelData, NetworkMetrics,
    NodePerformance, SecurityMetrics, ChannelRecommendation
)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisOperations:
    """Classe pour gérer les opérations Redis"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis = redis.from_url(redis_url)
        self.ttl = 3600  # TTL par défaut en secondes
        self.logger = logging.getLogger(__name__)
        
    def _serialize_datetime(self, obj: Any) -> Any:
        """Convertit les objets datetime en chaînes ISO 8601"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj
        
    async def _init_redis(self):
        """Initialise la connexion Redis"""
        if not self.redis:
            self.redis = redis.from_url(self.redis_url)
            
    async def _close_redis(self):
        """Ferme la connexion Redis"""
        if self.redis:
            await self.redis.close()
            self.redis = None
            
    async def cache_document(self, doc: Document) -> bool:
        """Met en cache un document"""
        try:
            await self._init_redis()
            key = f"doc:{doc.source}"
            await self.redis.setex(
                key,
                self.ttl,
                json.dumps(doc.dict())
            )
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache du document: {str(e)}")
            return False
            
    async def get_cached_document(self, source: str) -> Optional[Document]:
        """Récupère un document du cache"""
        try:
            await self._init_redis()
            key = f"doc:{source}"
            data = await self.redis.get(key)
            if data:
                return Document(**json.loads(data))
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du document: {str(e)}")
            return None
            
    async def cache_query_history(self, query: QueryHistory) -> bool:
        """Met en cache l'historique d'une requête"""
        try:
            await self._init_redis()
            key = f"query:{query.timestamp.timestamp()}"
            await self.redis.setex(
                key,
                self.ttl,
                json.dumps(query.dict())
            )
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache de la requête: {str(e)}")
            return False
            
    async def get_recent_queries(self, limit: int = 10) -> List[QueryHistory]:
        """Récupère les requêtes récentes"""
        try:
            await self._init_redis()
            keys = await self.redis.keys("query:*")
            queries = []
            for key in sorted(keys, reverse=True)[:limit]:
                data = await self.redis.get(key)
                if data:
                    queries.append(QueryHistory(**json.loads(data)))
            return queries
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des requêtes: {str(e)}")
            return []
            
    async def update_system_stats(self, stats: SystemStats) -> bool:
        """Met à jour les statistiques système"""
        try:
            await self._init_redis()
            key = "system:stats"
            await self.redis.setex(
                key,
                self.ttl,
                json.dumps(stats.dict())
            )
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des stats: {str(e)}")
            return False
            
    async def get_system_stats(self) -> Optional[SystemStats]:
        """Récupère les statistiques système"""
        try:
            await self._init_redis()
            key = "system:stats"
            data = await self.redis.get(key)
            if data:
                return SystemStats(**json.loads(data))
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des stats: {str(e)}")
            return None
            
    # Méthodes pour les données Lightning Network
    
    async def cache_node_data(self, node_data: NodeData) -> bool:
        """Met en cache les données d'un nœud"""
        try:
            key = f"node:{node_data.node_id}"
            node_dict = node_data.dict()
            # Convertir les dates en chaînes ISO 8601
            node_dict["first_seen"] = self._serialize_datetime(node_dict["first_seen"])
            node_dict["last_updated"] = self._serialize_datetime(node_dict["last_updated"])
            await self.redis.setex(
                key,
                self.ttl,
                json.dumps(node_dict)
            )
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache des données du nœud: {str(e)}")
            return False
            
    async def get_node_data(self, node_id: str) -> Optional[NodeData]:
        """Récupère les données d'un nœud"""
        try:
            key = f"node:{node_id}"
            node_data = await self.redis.get(key)
            if node_data:
                node_dict = json.loads(node_data)
                # Convertir les chaînes ISO 8601 en datetime
                node_dict["first_seen"] = datetime.fromisoformat(node_dict["first_seen"])
                node_dict["last_updated"] = datetime.fromisoformat(node_dict["last_updated"])
                return NodeData(**node_dict)
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données du nœud: {str(e)}")
            return None
            
    async def cache_channel_data(self, channel_data: ChannelData) -> bool:
        """Met en cache les données d'un canal"""
        try:
            key = f"channel:{channel_data.channel_id}"
            channel_dict = channel_data.dict()
            # Convertir les dates en chaînes ISO 8601
            channel_dict["last_updated"] = self._serialize_datetime(channel_dict["last_updated"])
            await self.redis.setex(
                key,
                self.ttl,
                json.dumps(channel_dict)
            )
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache des données du canal: {str(e)}")
            return False
            
    async def get_channel_data(self, channel_id: str) -> Optional[ChannelData]:
        """Récupère les données d'un canal"""
        try:
            await self._init_redis()
            key = f"channel:{channel_id}"
            data = await self.redis.get(key)
            if data:
                return ChannelData(**json.loads(data))
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données du canal: {str(e)}")
            return None
            
    async def cache_network_metrics(self, metrics: NetworkMetrics) -> bool:
        """Met en cache les métriques réseau"""
        try:
            await self._init_redis()
            key = "network:metrics"
            await self.redis.setex(
                key,
                self.ttl,
                json.dumps(metrics.dict())
            )
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache des métriques réseau: {str(e)}")
            return False
            
    async def get_network_metrics(self) -> Optional[NetworkMetrics]:
        """Récupère les métriques réseau"""
        try:
            await self._init_redis()
            key = "network:metrics"
            data = await self.redis.get(key)
            if data:
                return NetworkMetrics(**json.loads(data))
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métriques réseau: {str(e)}")
            return None
            
    async def cache_node_performance(self, performance: NodePerformance) -> bool:
        """Met en cache les performances d'un nœud"""
        try:
            await self._init_redis()
            key = f"node:performance:{performance.node_id}"
            await self.redis.setex(
                key,
                self.ttl,
                json.dumps(performance.dict())
            )
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache des performances: {str(e)}")
            return False
            
    async def get_node_performance(self, node_id: str) -> Optional[NodePerformance]:
        """Récupère les performances d'un nœud"""
        try:
            await self._init_redis()
            key = f"node:performance:{node_id}"
            data = await self.redis.get(key)
            if data:
                return NodePerformance(**json.loads(data))
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des performances: {str(e)}")
            return None
            
    async def cache_security_metrics(self, metrics: SecurityMetrics) -> bool:
        """Met en cache les métriques de sécurité"""
        try:
            await self._init_redis()
            key = f"node:security:{metrics.node_id}"
            await self.redis.setex(
                key,
                self.ttl,
                json.dumps(metrics.dict())
            )
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache des métriques de sécurité: {str(e)}")
            return False
            
    async def get_security_metrics(self, node_id: str) -> Optional[SecurityMetrics]:
        """Récupère les métriques de sécurité"""
        try:
            await self._init_redis()
            key = f"node:security:{node_id}"
            data = await self.redis.get(key)
            if data:
                return SecurityMetrics(**json.loads(data))
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métriques de sécurité: {str(e)}")
            return None
            
    async def cache_channel_recommendation(self, recommendation: ChannelRecommendation) -> bool:
        """Met en cache une recommandation de canal"""
        try:
            await self._init_redis()
            key = f"channel:recommendation:{recommendation.target_node_id}"
            await self.redis.setex(
                key,
                self.ttl,
                json.dumps(recommendation.dict())
            )
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache de la recommandation: {str(e)}")
            return False
            
    async def get_channel_recommendation(self, target_node_id: str) -> Optional[ChannelRecommendation]:
        """Récupère une recommandation de canal"""
        try:
            await self._init_redis()
            key = f"channel:recommendation:{target_node_id}"
            data = await self.redis.get(key)
            if data:
                return ChannelRecommendation(**json.loads(data))
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la recommandation: {str(e)}")
            return None

    async def get_node_channels(self, node_id: str) -> List[ChannelData]:
        """Récupère tous les canaux d'un nœud"""
        try:
            # Récupérer tous les canaux
            keys = await self.redis.keys("channel:*")
            channels = []
            
            for key in keys:
                channel_data = await self.redis.get(key)
                if channel_data:
                    channel_dict = json.loads(channel_data)
                    # Convertir les chaînes ISO 8601 en datetime
                    channel_dict["last_updated"] = datetime.fromisoformat(channel_dict["last_updated"])
                    channel = ChannelData(**channel_dict)
                    
                    # Vérifier si le canal appartient au nœud
                    if channel.node1_pubkey == node_id or channel.node2_pubkey == node_id:
                        channels.append(channel)
            
            return channels
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des canaux du nœud: {str(e)}")
            return [] 