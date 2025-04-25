import aiohttp
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
from models import NodeData, ChannelData
from prisma_operations import MongoOperations
from cache_manager import CacheManager
import os
from dotenv import load_dotenv
import logging
import time
import uuid
import traceback

load_dotenv()

# Configuration du logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class AmbossScraper:
    def __init__(self):
        self.mongo_ops = MongoOperations()
        self.cache_manager = CacheManager()
        self.base_url = "https://amboss.space"
        self.session = None
        self.rate_limiter = RateLimiter(max_requests=10, time_window=60)  # 10 requêtes par minute
        self.error_handler = ErrorHandler()
        self.fallback_sources = {
            "mempool": "https://mempool.space/api/v1/lightning/nodes",
            "1ml": "https://1ml.com/node/{node_id}/json"
        }

    async def connect_db(self):
        """Établit la connexion à la base de données via MongoOperations."""
        await self.mongo_ops.connect()

    async def disconnect_db(self):
        """Ferme la connexion à la base de données via MongoOperations."""
        await self.mongo_ops.disconnect()

    async def init_session(self):
        """Initialise la session HTTP"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close_session(self):
        """Ferme la session HTTP"""
        if self.session:
            await self.session.close()
            self.session = None

    async def fetch_node_data(self, node_id: str) -> Dict[str, Any]:
        """Récupère les données d'un nœud depuis Amboss avec fallback"""
        await self.init_session()
        url = f"{self.base_url}/node/{node_id}"
        
        try:
            # Vérification du rate limit
            await self.rate_limiter.acquire()
            
            async with self.session.get(url) as response:
                if response.status == 429:  # Too Many Requests
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limit atteint, attente de {retry_after} secondes")
                    await asyncio.sleep(retry_after)
                    return await self.fetch_node_data(node_id)
                    
                response.raise_for_status()
                html = await response.text()
                return await self.parse_node_page(html, node_id)
                
        except aiohttp.ClientError as e:
            logger.error(f"Erreur HTTP lors de la récupération du nœud {node_id}: {e}")
            # Tentative de fallback
            return await self._try_fallback_sources(node_id)
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la récupération du nœud {node_id}: {e}")
            await self.error_handler.handle_error(e, {"node_id": node_id, "source": "amboss"})
            return {}

    async def _try_fallback_sources(self, node_id: str) -> Dict[str, Any]:
        """Tente de récupérer les données depuis des sources alternatives"""
        for source_name, url_template in self.fallback_sources.items():
            try:
                url = url_template.format(node_id=node_id)
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._normalize_fallback_data(data, source_name)
            except Exception as e:
                logger.warning(f"Échec de la source de fallback {source_name}: {e}")
        return {}

    def _normalize_fallback_data(self, data: Dict, source: str) -> Dict[str, Any]:
        """Normalise les données des différentes sources"""
        if source == "mempool":
            return {
                "pubkey": data.get("public_key"),
                "alias": data.get("alias", "Unknown"),
                "capacity": data.get("capacity", 0),
                "channels": data.get("channels", 0)
            }
        elif source == "1ml":
            return {
                "pubkey": data.get("pub_key"),
                "alias": data.get("alias", "Unknown"),
                "capacity": data.get("capacity", 0),
                "channels": data.get("channels", 0)
            }
        return {}

    async def parse_node_page(self, html: str, node_id: str) -> Dict[str, Any]:
        """Parse la page HTML d'un nœud"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extraction des données - À COMPLÉTER AVEC LES SÉLECTEURS AMBOSS
        # Exemple (purement illustratif):
        alias = soup.select_one('h1.node-alias')
        capacity_text = soup.select_one('.node-capacity span')
        channel_count_text = soup.select_one('.node-channels span')
        
        node_data = {
            "pubkey": node_id,
            "alias": alias.text.strip() if alias else f"AmbossNode-{node_id[:8]}",
            "capacity": float(capacity_text.text.replace(',', '')) if capacity_text else 0.0,
            "channels": int(channel_count_text.text) if channel_count_text else 0,
            "first_seen": datetime.now(),
            "last_updated": datetime.now()
        }
        logger.info(f"Parsing réussi pour le nœud {node_id}: Alias={node_data['alias']}")
        return node_data

    async def fetch_channel_data(self, channel_id: str) -> Dict[str, Any]:
        """Récupère les données d'un canal depuis Amboss"""
        await self.init_session()
        url = f"{self.base_url}/channel/{channel_id}"
        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
                return await self.parse_channel_page(html, channel_id)
        except aiohttp.ClientError as e:
            logger.error(f"Erreur HTTP lors de la récupération du canal {channel_id}: {e}")
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la récupération du canal {channel_id}: {e}")
        return {}

    async def parse_channel_page(self, html: str, channel_id: str) -> Dict[str, Any]:
        """Parse la page HTML d'un canal"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extraction des données - À COMPLÉTER AVEC LES SÉLECTEURS AMBOSS
        # Exemple (purement illustratif):
        capacity_text = soup.select_one('.channel-capacity span')
        node1_pubkey = soup.select_one('.node1-pubkey a')['href'].split('/')[-1]
        node2_pubkey = soup.select_one('.node2-pubkey a')['href'].split('/')[-1]
        fee_rate_text = soup.select_one('.fee-rate span')

        channel_data = {
            "channel_id": channel_id,
            "node1_pubkey": node1_pubkey if node1_pubkey else "",
            "node2_pubkey": node2_pubkey if node2_pubkey else "",
            "capacity": float(capacity_text.text.replace(',', '')) if capacity_text else 0.0,
            "fee_rate": float(fee_rate_text.text) if fee_rate_text else 0.0,
            "last_updated": datetime.now()
        }
        logger.info(f"Parsing réussi pour le canal {channel_id}")
        return channel_data

    async def scrape_data(self, node_ids: List[str], channel_ids: List[str]):
        """Fonction principale pour scraper et sauvegarder les données"""
        try:
            await self.connect_db()
            await self.init_session()

            # Scraping et sauvegarde des nœuds
            for node_id in node_ids:
                node_data = await self.fetch_node_data(node_id)
                if node_data:
                    try:
                        await self.mongo_ops.save_node(node_data)
                        logger.info(f"Données du nœud {node_id} sauvegardées via Mongo.")
                    except Exception as e:
                        logger.error(f"Erreur DB lors de la sauvegarde du nœud {node_id}: {e}")

            # Scraping et sauvegarde des canaux
            for channel_id in channel_ids:
                channel_data = await self.fetch_channel_data(channel_id)
                if channel_data:
                    try:
                        await self.mongo_ops.save_channel(channel_data)
                        logger.info(f"Données du canal {channel_id} sauvegardées via Mongo.")
                    except Exception as e:
                        logger.error(f"Erreur DB lors de la sauvegarde du canal {channel_id}: {e}")

        finally:
            await self.close_session()
            await self.disconnect_db()

class RateLimiter:
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            now = time.time()
            # Nettoyage des anciennes requêtes
            self.requests = [req for req in self.requests if now - req < self.time_window]
            
            if len(self.requests) >= self.max_requests:
                # Calcul du temps d'attente
                wait_time = self.requests[0] + self.time_window - now
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    return await self.acquire()
            
            self.requests.append(now)

class ErrorHandler:
    async def handle_error(self, error: Exception, context: dict):
        """Gère les erreurs de manière centralisée"""
        error_id = str(uuid.uuid4())
        error_data = {
            "id": error_id,
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "stack_trace": traceback.format_exc()
        }
        
        # Log détaillé
        logger.error(f"Error {error_id}: {error_data}")
        
        # Notification si critique
        if self._is_critical_error(error):
            await self._notify_admin(error_data)
            
        # Sauvegarde dans MongoDB pour analyse
        await self._save_error_log(error_data)
        
        # Retry strategy si applicable
        if self._can_retry(error):
            return await self._retry_operation(context)

    def _is_critical_error(self, error: Exception) -> bool:
        """Détermine si l'erreur est critique"""
        critical_errors = [
            aiohttp.ClientError,
            ConnectionError,
            TimeoutError
        ]
        return any(isinstance(error, err) for err in critical_errors)

    async def _notify_admin(self, error_data: dict):
        """Notifie l'administrateur en cas d'erreur critique"""
        # TODO: Implémenter la notification (email, Slack, etc.)
        pass

    async def _save_error_log(self, error_data: dict):
        """Sauvegarde l'erreur dans MongoDB"""
        try:
            await self.mongo_ops.save_error_log(error_data)
        except Exception as e:
            logger.error(f"Échec de la sauvegarde du log d'erreur: {e}")

    def _can_retry(self, error: Exception) -> bool:
        """Détermine si l'opération peut être réessayée"""
        retryable_errors = [
            aiohttp.ClientError,
            ConnectionError,
            TimeoutError
        ]
        return any(isinstance(error, err) for err in retryable_errors)

    async def _retry_operation(self, context: dict, max_retries: int = 3):
        """Tente de réexécuter l'opération"""
        for attempt in range(max_retries):
            try:
                # TODO: Implémenter la logique de retry spécifique
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                return await self._execute_operation(context)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Tentative {attempt + 1} échouée: {e}")

    async def _execute_operation(self, context: dict):
        """Exécute l'opération originale"""
        # TODO: Implémenter la logique d'exécution
        pass

async def main():
    node_ids = [
        "02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619",
        "03abf6f44c355dec0d5aa155bdbdd6e0c8fefe579eff5b380f9f1441e882f8582b"
    ]
    channel_ids = [
        "716930x170x1",
        "801175x1460x0"
    ]

    scraper = AmbossScraper()
    logger.info(f"Démarrage du scraping pour {len(node_ids)} nœuds et {len(channel_ids)} canaux.")
    await scraper.scrape_data(node_ids, channel_ids)
    logger.info("Scraping terminé.")

if __name__ == "__main__":
    asyncio.run(main()) 