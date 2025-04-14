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
        """Récupère les données d'un nœud depuis Amboss"""
        await self.init_session()
        url = f"{self.base_url}/node/{node_id}"
        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
                return await self.parse_node_page(html, node_id)
        except aiohttp.ClientError as e:
            logger.error(f"Erreur HTTP lors de la récupération du nœud {node_id}: {e}")
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la récupération du nœud {node_id}: {e}")
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