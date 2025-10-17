"""
Cache Warmer pour MCP - Précalcule et met en cache les données fréquemment demandées
Améliore significativement les performances en anticipant les requêtes populaires
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.clients.sparkseer_client import SparkseerClient
from src.clients.anthropic_client import AnthropicClient
from src.utils.cache_manager import cache_manager
from src.clients.ollama_client import ollama_client
from config.rag_config import settings as rag_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CacheWarmer:
    """
    Précalcule et met en cache les données pour améliorer les performances
    """
    
    def __init__(self):
        self.sparkseer_client = SparkseerClient()
        self.anthropic_client = AnthropicClient()
        
        # Requêtes communes à précalculer
        self.common_queries = [
            "Comment optimiser mes frais de routage?",
            "Comment améliorer la liquidité de mes canaux?",
            "Quelles sont les meilleures pratiques pour un nœud Lightning?",
            "Comment augmenter mon uptime?",
            "Comment ouvrir de nouveaux canaux de manière stratégique?",
            "Comment équilibrer mes canaux?",
            "Quels sont les risques d'un nœud Lightning?",
            "Comment monitorer mon nœud efficacement?"
        ]
        
        self.stats = {
            'nodes_cached': 0,
            'recommendations_cached': 0,
            'embeddings_cached': 0,
            'queries_cached': 0,
            'errors': 0,
            'total_time_seconds': 0,
            'last_run': None
        }
    
    async def get_popular_nodes(self, limit: int = 100) -> List[Dict[str, str]]:
        """
        Récupère les nœuds les plus consultés
        
        Args:
            limit: Nombre de nœuds à récupérer
            
        Returns:
            Liste des nœuds populaires avec leur pubkey
        """
        # Pour l'instant, simuler avec des nœuds bien connus
        # TODO: Implémenter une vraie récupération depuis les analytics
        popular_nodes = [
            {"pubkey": "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f", "alias": "ACINQ"},
            {"pubkey": "035e4ff418fc8b5554c5d9eea66396c227bd429a3251c8cbc711002ba215bfc226", "alias": "WalletOfSatoshi.com"},
            {"pubkey": "03cde60a6323f7122d5178255766e38114b4722ede08f7c9e0c5df9b912cc201d6", "alias": "Bitrefill"},
            {"pubkey": "0260fab633066ed7b1d9b9b8a0fac87e1579d1709e874d28a0d171a1f5c43bb877", "alias": "Boltz"},
            {"pubkey": "03abf6f44c355dec0d5aa155bdbdd6e0c8fefe318eff402de65c6eb2e1be55dc3e", "alias": "River Financial 1"},
        ]
        
        # Charger depuis les analytics si disponible
        try:
            # TODO: Implémenter récupération depuis MongoDB analytics
            pass
        except Exception as e:
            logger.warning(f"Could not load popular nodes from analytics: {str(e)}")
        
        return popular_nodes[:limit]
    
    async def precompute_node_data(self, pubkey: str, alias: str = None) -> bool:
        """
        Précalcule toutes les données d'un nœud
        
        Args:
            pubkey: Public key du nœud
            alias: Alias du nœud (optionnel, pour logs)
            
        Returns:
            True si succès, False sinon
        """
        node_label = alias or pubkey[:16] + "..."
        
        try:
            logger.info(f"Warming cache for node: {node_label}")
            
            # 1. Informations de base du nœud
            try:
                node_info = await self.sparkseer_client.get_node_info(pubkey)
                if node_info:
                    cache_key = f"node_info:{pubkey}:True:False"
                    await cache_manager.set(
                        cache_key,
                        node_info,
                        data_type="node_info",
                        ttl=1800  # 30 minutes
                    )
                    logger.debug(f"Cached node_info for {node_label}")
            except Exception as e:
                logger.warning(f"Failed to cache node_info for {node_label}: {str(e)}")
            
            # 2. Recommandations techniques
            try:
                recommendations = await self.sparkseer_client.get_node_recommendations(pubkey)
                if recommendations:
                    cache_key = f"recommendations:{pubkey}:None:None"
                    await cache_manager.set(
                        cache_key,
                        {
                            'pubkey': pubkey,
                            'recommendations': recommendations.get('recommendations', []),
                            'total_count': len(recommendations.get('recommendations', [])),
                            'generated_at': datetime.utcnow()
                        },
                        data_type="recommendations",
                        ttl=900  # 15 minutes
                    )
                    logger.debug(f"Cached recommendations for {node_label}")
                    self.stats['recommendations_cached'] += 1
            except Exception as e:
                logger.warning(f"Failed to cache recommendations for {node_label}: {str(e)}")
            
            # 3. Embeddings pour requêtes communes sur ce nœud
            node_queries = [
                f"Analyse du nœud {pubkey}",
                f"Recommandations pour le nœud {pubkey}",
                f"État et performance du nœud {pubkey}"
            ]
            
            for query in node_queries:
                try:
                    embedding = await ollama_client.embed(query, rag_settings.EMBED_MODEL)
                    if embedding:
                        cache_key = f"embedding:{query}"
                        await cache_manager.set(
                            cache_key,
                            embedding,
                            data_type="embedding",
                            ttl=3600  # 1 heure
                        )
                        self.stats['embeddings_cached'] += 1
                except Exception as e:
                    logger.debug(f"Failed to cache embedding for query: {str(e)}")
            
            self.stats['nodes_cached'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to precompute data for {node_label}: {str(e)}")
            self.stats['errors'] += 1
            return False
    
    async def warm_common_queries(self):
        """
        Précalcule les embeddings pour les requêtes communes
        """
        logger.info(f"Warming cache for {len(self.common_queries)} common queries...")
        
        for query in self.common_queries:
            try:
                # Générer l'embedding
                embedding = await ollama_client.embed(query, rag_settings.EMBED_MODEL)
                
                if embedding:
                    cache_key = f"embedding:{query}"
                    await cache_manager.set(
                        cache_key,
                        embedding,
                        data_type="embedding",
                        ttl=3600  # 1 heure
                    )
                    self.stats['queries_cached'] += 1
                    logger.debug(f"Cached embedding for: {query[:50]}...")
                
                # Petit délai pour ne pas surcharger Ollama
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"Failed to cache query '{query[:50]}...': {str(e)}")
                self.stats['errors'] += 1
        
        logger.info(f"Cached {self.stats['queries_cached']} common query embeddings")
    
    async def warm_popular_nodes(self, limit: int = 100):
        """
        Chauffe le cache pour les nœuds les plus consultés
        
        Args:
            limit: Nombre de nœuds à traiter
        """
        logger.info(f"Starting cache warming for top {limit} popular nodes...")
        start_time = datetime.now()
        
        # Récupérer les nœuds populaires
        popular_nodes = await self.get_popular_nodes(limit=limit)
        logger.info(f"Found {len(popular_nodes)} popular nodes to cache")
        
        # Traiter les nœuds en parallèle par batches de 10
        batch_size = 10
        for i in range(0, len(popular_nodes), batch_size):
            batch = popular_nodes[i:i + batch_size]
            
            tasks = [
                self.precompute_node_data(node['pubkey'], node.get('alias'))
                for node in batch
            ]
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Petit délai entre les batches
            if i + batch_size < len(popular_nodes):
                await asyncio.sleep(1)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        self.stats['total_time_seconds'] = elapsed
        self.stats['last_run'] = datetime.now().isoformat()
        
        logger.info(
            f"Cache warming completed in {elapsed:.1f}s: "
            f"{self.stats['nodes_cached']} nodes, "
            f"{self.stats['recommendations_cached']} recommendations, "
            f"{self.stats['embeddings_cached']} embeddings, "
            f"{self.stats['errors']} errors"
        )
    
    async def schedule_cache_warming(
        self,
        interval_minutes: int = 60,
        nodes_per_run: int = 100
    ):
        """
        Exécute le cache warming périodiquement
        
        Args:
            interval_minutes: Intervalle entre les exécutions (minutes)
            nodes_per_run: Nombre de nœuds à traiter par exécution
        """
        logger.info(
            f"Cache warming scheduler started: "
            f"interval={interval_minutes}min, nodes_per_run={nodes_per_run}"
        )
        
        while True:
            try:
                # Réinitialiser les stats
                self.stats = {
                    'nodes_cached': 0,
                    'recommendations_cached': 0,
                    'embeddings_cached': 0,
                    'queries_cached': 0,
                    'errors': 0,
                    'total_time_seconds': 0,
                    'last_run': None
                }
                
                # Chauffer le cache
                await self.warm_popular_nodes(limit=nodes_per_run)
                await self.warm_common_queries()
                
                # Attendre avant la prochaine exécution
                next_run = datetime.now() + timedelta(minutes=interval_minutes)
                logger.info(f"Next cache warming scheduled at {next_run.strftime('%H:%M:%S')}")
                await asyncio.sleep(interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"Error in cache warming scheduler: {str(e)}")
                # Attendre 5 minutes avant de réessayer en cas d'erreur
                await asyncio.sleep(300)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du cache warmer"""
        return {
            **self.stats,
            'cache_stats': asyncio.run(cache_manager.get_stats()) if hasattr(cache_manager, 'get_stats') else {}
        }


async def run_cache_warming_once(nodes_limit: int = 100):
    """
    Exécute le cache warming une seule fois (pour tests ou cron)
    
    Args:
        nodes_limit: Nombre de nœuds à traiter
    """
    warmer = CacheWarmer()
    
    logger.info("=" * 80)
    logger.info("MCP CACHE WARMER - One-time execution")
    logger.info("=" * 80)
    
    await warmer.warm_popular_nodes(limit=nodes_limit)
    await warmer.warm_common_queries()
    
    stats = warmer.get_stats()
    
    logger.info("=" * 80)
    logger.info("CACHE WARMING SUMMARY:")
    logger.info(f"  Nodes cached: {stats['nodes_cached']}")
    logger.info(f"  Recommendations cached: {stats['recommendations_cached']}")
    logger.info(f"  Embeddings cached: {stats['embeddings_cached']}")
    logger.info(f"  Queries cached: {stats['queries_cached']}")
    logger.info(f"  Errors: {stats['errors']}")
    logger.info(f"  Total time: {stats['total_time_seconds']:.1f}s")
    logger.info("=" * 80)
    
    return stats


async def run_cache_warming_daemon(
    interval_minutes: int = 60,
    nodes_per_run: int = 100
):
    """
    Exécute le cache warming en mode daemon (continu)
    
    Args:
        interval_minutes: Intervalle entre les exécutions
        nodes_per_run: Nombre de nœuds par exécution
    """
    warmer = CacheWarmer()
    
    logger.info("=" * 80)
    logger.info("MCP CACHE WARMER - Daemon mode")
    logger.info(f"Interval: {interval_minutes} minutes")
    logger.info(f"Nodes per run: {nodes_per_run}")
    logger.info("=" * 80)
    
    await warmer.schedule_cache_warming(
        interval_minutes=interval_minutes,
        nodes_per_run=nodes_per_run
    )


# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Cache Warmer")
    parser.add_argument(
        '--mode',
        choices=['once', 'daemon'],
        default='once',
        help='Execution mode: once or daemon'
    )
    parser.add_argument(
        '--nodes',
        type=int,
        default=100,
        help='Number of nodes to cache (default: 100)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Interval in minutes for daemon mode (default: 60)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == 'once':
            asyncio.run(run_cache_warming_once(nodes_limit=args.nodes))
        else:
            asyncio.run(run_cache_warming_daemon(
                interval_minutes=args.interval,
                nodes_per_run=args.nodes
            ))
    except KeyboardInterrupt:
        logger.info("Cache warmer stopped by user")
    except Exception as e:
        logger.error(f"Cache warmer failed: {str(e)}")
        sys.exit(1)

