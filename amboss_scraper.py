import aiohttp
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
from models import Document, NodeData, ChannelData
from mongo_operations import MongoOperations
from cache_manager import CacheManager
import os
from dotenv import load_dotenv

load_dotenv()

class AmbossScraper:
    def __init__(self):
        self.mongo_ops = MongoOperations()
        self.cache_manager = CacheManager()
        self.base_url = "https://amboss.space"
        self.session = None

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
        async with self.session.get(url) as response:
            if response.status == 200:
                html = await response.text()
                return await self.parse_node_page(html)
            return {}

    async def parse_node_page(self, html: str) -> Dict[str, Any]:
        """Parse la page HTML d'un nœud"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extraction des données de base
        node_data = {
            "node_id": "",
            "alias": "",
            "capacity": 0.0,
            "channel_count": 0,
            "last_update": datetime.now(),
            "reputation_score": 0.0,
            "metadata": {}
        }

        # TODO: Implémenter le parsing spécifique d'Amboss
        # Cette partie dépendra de la structure HTML exacte d'Amboss

        return node_data

    async def fetch_channel_data(self, channel_id: str) -> Dict[str, Any]:
        """Récupère les données d'un canal depuis Amboss"""
        await self.init_session()
        url = f"{self.base_url}/channel/{channel_id}"
        async with self.session.get(url) as response:
            if response.status == 200:
                html = await response.text()
                return await self.parse_channel_page(html)
            return {}

    async def parse_channel_page(self, html: str) -> Dict[str, Any]:
        """Parse la page HTML d'un canal"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extraction des données de base
        channel_data = {
            "channel_id": "",
            "capacity": 0.0,
            "fee_rate": {"base": 0, "rate": 0},
            "balance": {"local": 0, "remote": 0},
            "age": 0,
            "last_update": datetime.now(),
            "metadata": {}
        }

        # TODO: Implémenter le parsing spécifique d'Amboss
        # Cette partie dépendra de la structure HTML exacte d'Amboss

        return channel_data

    async def create_document(self, data: Any, source: str) -> Document:
        """Crée un document RAG à partir des données"""
        return Document(
            content=str(data),
            source=source,
            embedding=[],  # À remplir avec les embeddings
            metadata={"type": data.__class__.__name__}
        )

    async def scrape_data(self, node_ids: List[str], channel_ids: List[str]):
        """Fonction principale pour scraper les données"""
        try:
            await self.init_session()

            # Scraping des nœuds
            for node_id in node_ids:
                node_data = await self.fetch_node_data(node_id)
                if node_data:
                    node = NodeData(**node_data)
                    doc = await self.create_document(node, "amboss")
                    await self.mongo_ops.save_document(doc)

            # Scraping des canaux
            for channel_id in channel_ids:
                channel_data = await self.fetch_channel_data(channel_id)
                if channel_data:
                    channel = ChannelData(**channel_data)
                    doc = await self.create_document(channel, "amboss")
                    await self.mongo_ops.save_document(doc)

        finally:
            await self.close_session()

async def main():
    # Liste des nœuds et canaux à scraper
    node_ids = [
        "02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619",
        "03abf6f44c355dec0d5aa155bdbdd6e0c8fefe579eff5b380f9f1441e882f8582b"
    ]
    channel_ids = [
        "1234567890abcdef",
        "0987654321fedcba"
    ]

    scraper = AmbossScraper()
    await scraper.scrape_data(node_ids, channel_ids)

if __name__ == "__main__":
    asyncio.run(main()) 