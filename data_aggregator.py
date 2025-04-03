import os
import aiohttp
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from models import (
    Document, NodeData, ChannelData, NetworkMetrics,
    NodePerformance, SecurityMetrics, ChannelRecommendation
)
from mongo_operations import MongoOperations
from cache_manager import CacheManager
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class DataAggregator:
    def __init__(self):
        self.mongo_ops = MongoOperations()
        self.cache_manager = CacheManager()
        self.sparkseer_api_key = os.getenv("SPARKSEER_API_KEY")
        self.lnbits_url = os.getenv("LNBITS_URL")
        self.lnbits_admin_key = os.getenv("LNBITS_ADMIN_KEY")
        self.lnbits_invoice_key = os.getenv("LNBITS_INVOICE_KEY")
        self.sparkseer_base_url = "https://api.sparkseer.io/v1"  # URL corrigée

    async def make_request(self, url: str, headers: Dict[str, str], params: Dict[str, Any] = None) -> Any:
        """Fait une requête HTTP avec gestion d'erreur"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Erreur HTTP {response.status} pour {url}")
                        return None
        except aiohttp.ClientError as e:
            logger.error(f"Erreur de connexion pour {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Erreur inattendue pour {url}: {str(e)}")
            return None

    async def fetch_sparkseer_network_metrics(self) -> Dict[str, Any]:
        """Récupère les métriques globales du réseau"""
        headers = {"api-key": self.sparkseer_api_key}
        return await self.make_request(
            f"{self.sparkseer_base_url}/network/metrics",
            headers=headers
        ) or {}

    async def fetch_sparkseer_top_nodes(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Récupère les nœuds les plus importants"""
        headers = {"api-key": self.sparkseer_api_key}
        params = {"limit": limit}
        return await self.make_request(
            f"{self.sparkseer_base_url}/network/top-nodes",
            headers=headers,
            params=params
        ) or []

    async def fetch_sparkseer_node_details(self, node_id: str) -> Dict[str, Any]:
        """Récupère les détails d'un nœud spécifique"""
        headers = {"api-key": self.sparkseer_api_key}
        return await self.make_request(
            f"{self.sparkseer_base_url}/network/nodes/{node_id}",
            headers=headers
        ) or {}

    async def fetch_sparkseer_channel_metrics(self) -> List[Dict[str, Any]]:
        """Récupère les métriques des canaux"""
        headers = {"api-key": self.sparkseer_api_key}
        return await self.make_request(
            f"{self.sparkseer_base_url}/network/channels/metrics",
            headers=headers
        ) or []

    async def fetch_sparkseer_fee_analysis(self) -> Dict[str, Any]:
        """Récupère l'analyse des frais"""
        headers = {"api-key": self.sparkseer_api_key}
        return await self.make_request(
            f"{self.sparkseer_base_url}/network/fee-analysis",
            headers=headers
        ) or {}

    async def fetch_sparkseer_network_health(self) -> Dict[str, Any]:
        """Récupère la santé du réseau"""
        headers = {"api-key": self.sparkseer_api_key}
        return await self.make_request(
            f"{self.sparkseer_base_url}/network/health",
            headers=headers
        ) or {}

    async def fetch_lnbits_wallets(self) -> List[Dict[str, Any]]:
        """Récupère la liste des wallets LNBits"""
        headers = {"X-Api-Key": self.lnbits_admin_key}
        return await self.make_request(
            f"{self.lnbits_url}/api/v1/wallet",
            headers=headers
        ) or []

    async def fetch_lnbits_payments(self, wallet_id: str) -> List[Dict[str, Any]]:
        """Récupère l'historique des paiements d'un wallet"""
        headers = {"X-Api-Key": self.lnbits_admin_key}
        params = {"wallet_id": wallet_id}
        return await self.make_request(
            f"{self.lnbits_url}/api/v1/payments",
            headers=headers,
            params=params
        ) or []

    async def fetch_lnbits_invoices(self, wallet_id: str) -> List[Dict[str, Any]]:
        """Récupère les factures d'un wallet"""
        headers = {"X-Api-Key": self.lnbits_invoice_key}
        params = {"wallet_id": wallet_id}
        return await self.make_request(
            f"{self.lnbits_url}/api/v1/invoices",
            headers=headers,
            params=params
        ) or []

    async def process_node_data(self, raw_data: Dict[str, Any]) -> NodeData:
        """Traite les données brutes d'un nœud"""
        return NodeData(
            node_id=raw_data.get("node_id", ""),
            alias=raw_data.get("alias", ""),
            capacity=float(raw_data.get("capacity", 0)),
            channel_count=int(raw_data.get("channel_count", 0)),
            last_update=datetime.now(),
            reputation_score=float(raw_data.get("reputation_score", 0)),
            metadata=raw_data.get("metadata", {})
        )

    async def process_channel_data(self, raw_data: Dict[str, Any]) -> ChannelData:
        """Traite les données brutes d'un canal"""
        return ChannelData(
            channel_id=raw_data.get("channel_id", ""),
            capacity=float(raw_data.get("capacity", 0)),
            fee_rate=raw_data.get("fee_rate", {"base": 0, "rate": 0}),
            balance=raw_data.get("balance", {"local": 0, "remote": 0}),
            age=int(raw_data.get("age", 0)),
            last_update=datetime.now(),
            metadata=raw_data.get("metadata", {})
        )

    async def create_document(self, data: Any, source: str) -> Document:
        """Crée un document RAG à partir des données"""
        # TODO: Implémenter la génération d'embeddings
        return Document(
            content=str(data),
            source=source,
            embedding=[],  # À remplir avec les embeddings
            metadata={"type": data.__class__.__name__}
        )

    async def aggregate_data(self):
        """Fonction principale pour agréger les données"""
        try:
            # Récupération des données Sparkseer
            logger.info("Récupération des métriques réseau Sparkseer...")
            network_metrics = await self.fetch_sparkseer_network_metrics()
            if network_metrics:
                doc = await self.create_document(network_metrics, "sparkseer_network_metrics")
                await self.mongo_ops.save_document(doc)
                logger.info("Métriques réseau sauvegardées")

            logger.info("Récupération des nœuds top Sparkseer...")
            top_nodes = await self.fetch_sparkseer_top_nodes(limit=100)
            for node_data in top_nodes:
                # Récupération des détails du nœud
                node_details = await self.fetch_sparkseer_node_details(node_data.get("node_id", ""))
                if node_details:
                    node_data.update(node_details)
                
                node = await self.process_node_data(node_data)
                doc = await self.create_document(node, "sparkseer_node")
                await self.mongo_ops.save_document(doc)
            logger.info(f"{len(top_nodes)} nœuds sauvegardés")

            logger.info("Récupération des métriques de canaux Sparkseer...")
            channel_metrics = await self.fetch_sparkseer_channel_metrics()
            for channel_data in channel_metrics:
                channel = await self.process_channel_data(channel_data)
                doc = await self.create_document(channel, "sparkseer_channel")
                await self.mongo_ops.save_document(doc)
            logger.info(f"{len(channel_metrics)} canaux sauvegardés")

            logger.info("Récupération de l'analyse des frais Sparkseer...")
            fee_analysis = await self.fetch_sparkseer_fee_analysis()
            if fee_analysis:
                doc = await self.create_document(fee_analysis, "sparkseer_fee_analysis")
                await self.mongo_ops.save_document(doc)
                logger.info("Analyse des frais sauvegardée")

            logger.info("Récupération de la santé du réseau Sparkseer...")
            network_health = await self.fetch_sparkseer_network_health()
            if network_health:
                doc = await self.create_document(network_health, "sparkseer_network_health")
                await self.mongo_ops.save_document(doc)
                logger.info("Santé du réseau sauvegardée")

            # Récupération des données LNBits
            logger.info("Récupération des wallets LNBits...")
            lnbits_wallets = await self.fetch_lnbits_wallets()
            for wallet in lnbits_wallets:
                # Récupération des paiements
                payments = await self.fetch_lnbits_payments(wallet["id"])
                wallet["payments"] = payments

                # Récupération des factures
                invoices = await self.fetch_lnbits_invoices(wallet["id"])
                wallet["invoices"] = invoices

                # Création du document
                doc = await self.create_document(wallet, "lnbits")
                await self.mongo_ops.save_document(doc)
            logger.info(f"{len(lnbits_wallets)} wallets sauvegardés")

            # Mise à jour des statistiques
            stats = {
                "total_documents": len(top_nodes) + len(channel_metrics) + len(lnbits_wallets) + 3,  # +3 pour les métriques globales
                "total_queries": 0,
                "average_processing_time": 0.0,
                "cache_hit_rate": 0.0,
                "last_update": datetime.now()
            }
            await self.mongo_ops.update_system_stats(stats)
            logger.info("Statistiques mises à jour")

        except Exception as e:
            logger.error(f"Erreur lors de l'agrégation des données: {str(e)}")
            raise

async def main():
    aggregator = DataAggregator()
    await aggregator.aggregate_data()

if __name__ == "__main__":
    asyncio.run(main()) 