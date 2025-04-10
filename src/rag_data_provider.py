from data_aggregator import DataAggregator
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RAGDataProvider:
    def __init__(self):
        self.data_aggregator = DataAggregator()
        self.cache_ttl = timedelta(hours=4)
        self._cache = {}
        self._cache_timestamps = {}
        
    async def get_context_data(self, query: str) -> Dict[str, Any]:
        """Récupère les données contextuelles pour le RAG"""
        try:
            # Vérifier le cache
            cache_key = f"context:{hash(query)}"
            if self._is_cache_valid(cache_key):
                logger.info("Utilisation des données en cache")
                return self._cache[cache_key]
            
            # Récupérer les données agrégées
            aggregated_data = await self.data_aggregator.aggregate_data()
            
            # Formater pour le RAG
            context = {
                "network_metrics": aggregated_data.get("network_summary", {}),
                "node_data": aggregated_data.get("centralities", {}).get("nodes", []),
                "wallet_data": aggregated_data.get("lnbits_wallets", []),
                "timestamp": datetime.now().isoformat()
            }
            
            # Mettre en cache
            self._cache[cache_key] = context
            self._cache_timestamps[cache_key] = datetime.now()
            
            return context
            
        except Exception as e:
            logger.error(f"Erreur de récupération du contexte: {str(e)}")
            return {}
            
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Vérifie si les données en cache sont toujours valides"""
        if cache_key not in self._cache_timestamps:
            return False
            
        cache_age = datetime.now() - self._cache_timestamps[cache_key]
        return cache_age < self.cache_ttl
        
    async def clear_expired_cache(self):
        """Nettoie les entrées de cache expirées"""
        current_time = datetime.now()
        expired_keys = [
            key for key, timestamp in self._cache_timestamps.items()
            if current_time - timestamp > self.cache_ttl
        ]
        
        for key in expired_keys:
            del self._cache[key]
            del self._cache_timestamps[key]
            
        logger.info(f"Nettoyage du cache: {len(expired_keys)} entrées supprimées") 