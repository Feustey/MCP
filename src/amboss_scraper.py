import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
import logging
from bs4 import BeautifulSoup
import json
import re
from src.models import NodeData, ChannelData, NetworkMetrics
from src.redis_operations import RedisOperations

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AmbossScraper:
    """Classe pour scraper les données d'Amboss.Space"""
    
    def __init__(self, redis_ops: RedisOperations):
        self.base_url = "https://amboss.space"
        self.redis_ops = redis_ops
        self.session = None
        
    async def _init_session(self):
        """Initialise la session aiohttp"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
    async def _close_session(self):
        """Ferme la session aiohttp"""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def _get_page(self, url: str) -> Optional[str]:
        """Récupère une page HTML"""
        try:
            await self._init_session()
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                logger.error(f"Erreur lors de la récupération de {url}: {response.status}")
                return None
        except Exception as e:
            logger.error(f"Erreur lors de la requête {url}: {str(e)}")
            return None
            
    async def scrape_node_data(self, node_id: str) -> Optional[NodeData]:
        """Scrape les données d'un nœud spécifique"""
        url = f"{self.base_url}/node/{node_id}"
        html = await self._get_page(url)
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Extraction des données du nœud
            node_data = NodeData(
                node_id=node_id,
                alias=self._extract_alias(soup),
                capacity=self._extract_capacity(soup),
                channel_count=self._extract_channel_count(soup),
                last_update=datetime.now(),
                reputation_score=self._extract_reputation(soup)
            )
            
            # Mise en cache dans Redis
            await self.redis_ops.cache_node_data(node_data)
            return node_data
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing des données du nœud {node_id}: {str(e)}")
            return None
            
    async def scrape_channel_data(self, channel_id: str) -> Optional[ChannelData]:
        """Scrape les données d'un canal spécifique"""
        url = f"{self.base_url}/channel/{channel_id}"
        html = await self._get_page(url)
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Extraction des données du canal
            channel_data = ChannelData(
                channel_id=channel_id,
                capacity=self._extract_channel_capacity(soup),
                fee_rate=self._extract_fee_rate(soup),
                balance=self._extract_balance(soup),
                age=self._extract_channel_age(soup),
                last_update=datetime.now()
            )
            
            # Mise en cache dans Redis
            await self.redis_ops.cache_channel_data(channel_data)
            return channel_data
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing des données du canal {channel_id}: {str(e)}")
            return None
            
    async def scrape_network_metrics(self) -> Optional[NetworkMetrics]:
        """Scrape les métriques globales du réseau"""
        url = f"{self.base_url}/network"
        html = await self._get_page(url)
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Extraction des métriques réseau
            metrics = NetworkMetrics(
                total_capacity=self._extract_total_capacity(soup),
                total_channels=self._extract_total_channels(soup),
                total_nodes=self._extract_total_nodes(soup),
                average_fee_rate=self._extract_average_fee_rate(soup),
                last_update=datetime.now()
            )
            
            # Mise en cache dans Redis
            await self.redis_ops.cache_network_metrics(metrics)
            return metrics
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing des métriques réseau: {str(e)}")
            return None
            
    def _extract_alias(self, soup: BeautifulSoup) -> str:
        """Extrait l'alias du nœud"""
        try:
            alias_elem = soup.find('h1', class_='node-alias')
            return alias_elem.text.strip() if alias_elem else "Unknown"
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de l'alias: {str(e)}")
            return "Unknown"
        
    def _extract_capacity(self, soup: BeautifulSoup) -> float:
        """Extrait la capacité totale du nœud"""
        try:
            capacity_elem = soup.find('div', class_='node-capacity')
            if capacity_elem:
                capacity_text = capacity_elem.text.strip()
                # Conversion de BTC en sats (1 BTC = 100,000,000 sats)
                capacity_btc = float(re.search(r'(\d+\.?\d*)', capacity_text).group(1))
                return capacity_btc * 100_000_000
            return 0.0
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de la capacité: {str(e)}")
            return 0.0
        
    def _extract_channel_count(self, soup: BeautifulSoup) -> int:
        """Extrait le nombre de canaux"""
        try:
            channels_elem = soup.find('div', class_='node-channels')
            if channels_elem:
                count_text = channels_elem.text.strip()
                return int(re.search(r'(\d+)', count_text).group(1))
            return 0
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction du nombre de canaux: {str(e)}")
            return 0
        
    def _extract_reputation(self, soup: BeautifulSoup) -> float:
        """Extrait le score de réputation"""
        try:
            reputation_elem = soup.find('div', class_='node-reputation')
            if reputation_elem:
                score_text = reputation_elem.text.strip()
                return float(re.search(r'(\d+\.?\d*)', score_text).group(1))
            return 0.0
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de la réputation: {str(e)}")
            return 0.0
        
    def _extract_channel_capacity(self, soup: BeautifulSoup) -> float:
        """Extrait la capacité d'un canal"""
        try:
            capacity_elem = soup.find('div', class_='channel-capacity')
            if capacity_elem:
                capacity_text = capacity_elem.text.strip()
                capacity_btc = float(re.search(r'(\d+\.?\d*)', capacity_text).group(1))
                return capacity_btc * 100_000_000
            return 0.0
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de la capacité du canal: {str(e)}")
            return 0.0
        
    def _extract_fee_rate(self, soup: BeautifulSoup) -> Dict[str, float]:
        """Extrait les frais d'un canal"""
        try:
            fee_elem = soup.find('div', class_='channel-fees')
            if fee_elem:
                base_fee = float(re.search(r'Base: (\d+)', fee_elem.text).group(1))
                fee_rate = float(re.search(r'Rate: (\d+)', fee_elem.text).group(1))
                return {
                    "base_fee": base_fee,
                    "fee_rate": fee_rate
                }
            return {"base_fee": 0.0, "fee_rate": 0.0}
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des frais: {str(e)}")
            return {"base_fee": 0.0, "fee_rate": 0.0}
        
    def _extract_balance(self, soup: BeautifulSoup) -> Dict[str, float]:
        """Extrait l'équilibre d'un canal"""
        try:
            balance_elem = soup.find('div', class_='channel-balance')
            if balance_elem:
                local = float(re.search(r'Local: (\d+\.?\d*)', balance_elem.text).group(1))
                remote = float(re.search(r'Remote: (\d+\.?\d*)', balance_elem.text).group(1))
                return {
                    "local": local,
                    "remote": remote
                }
            return {"local": 0.0, "remote": 0.0}
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de l'équilibre: {str(e)}")
            return {"local": 0.0, "remote": 0.0}
        
    def _extract_channel_age(self, soup: BeautifulSoup) -> int:
        """Extrait l'âge d'un canal"""
        try:
            age_elem = soup.find('div', class_='channel-age')
            if age_elem:
                age_text = age_elem.text.strip()
                days = int(re.search(r'(\d+)', age_text).group(1))
                return days
            return 0
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de l'âge du canal: {str(e)}")
            return 0
        
    def _extract_total_capacity(self, soup: BeautifulSoup) -> float:
        """Extrait la capacité totale du réseau"""
        try:
            capacity_elem = soup.find('div', class_='network-capacity')
            if capacity_elem:
                capacity_text = capacity_elem.text.strip()
                capacity_btc = float(re.search(r'(\d+\.?\d*)', capacity_text).group(1))
                return capacity_btc * 100_000_000
            return 0.0
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de la capacité totale: {str(e)}")
            return 0.0
        
    def _extract_total_channels(self, soup: BeautifulSoup) -> int:
        """Extrait le nombre total de canaux"""
        try:
            channels_elem = soup.find('div', class_='network-channels')
            if channels_elem:
                count_text = channels_elem.text.strip()
                return int(re.search(r'(\d+)', count_text).group(1))
            return 0
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction du nombre total de canaux: {str(e)}")
            return 0
        
    def _extract_total_nodes(self, soup: BeautifulSoup) -> int:
        """Extrait le nombre total de nœuds"""
        try:
            nodes_elem = soup.find('div', class_='network-nodes')
            if nodes_elem:
                count_text = nodes_elem.text.strip()
                return int(re.search(r'(\d+)', count_text).group(1))
            return 0
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction du nombre total de nœuds: {str(e)}")
            return 0
        
    def _extract_average_fee_rate(self, soup: BeautifulSoup) -> float:
        """Extrait le taux de frais moyen"""
        try:
            fee_elem = soup.find('div', class_='network-fees')
            if fee_elem:
                fee_text = fee_elem.text.strip()
                return float(re.search(r'(\d+\.?\d*)', fee_text).group(1))
            return 0.0
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction du taux de frais moyen: {str(e)}")
            return 0.0
        
    async def update_all_data(self):
        """Met à jour toutes les données du réseau"""
        try:
            # Récupération des métriques réseau
            network_metrics = await self.scrape_network_metrics()
            if network_metrics:
                logger.info("Métriques réseau mises à jour avec succès")
            
            # Récupération des nœuds principaux
            main_nodes = await self._get_main_nodes()
            for node_id in main_nodes:
                node_data = await self.scrape_node_data(node_id)
                if node_data:
                    logger.info(f"Données du nœud {node_id} mises à jour avec succès")
                    
                # Récupération des canaux du nœud
                channels = await self._get_node_channels(node_id)
                for channel_id in channels:
                    channel_data = await self.scrape_channel_data(channel_id)
                    if channel_data:
                        logger.info(f"Données du canal {channel_id} mises à jour avec succès")
                        
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des données: {str(e)}")
            
    async def _get_main_nodes(self) -> List[str]:
        """Récupère la liste des nœuds principaux"""
        try:
            url = f"{self.base_url}/nodes"
            html = await self._get_page(url)
            if not html:
                return []
                
            soup = BeautifulSoup(html, 'html.parser')
            nodes = []
            for node_elem in soup.find_all('div', class_='node-item'):
                node_id = node_elem.get('data-node-id')
                if node_id:
                    nodes.append(node_id)
            return nodes
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des nœuds principaux: {str(e)}")
            return []
            
    async def _get_node_channels(self, node_id: str) -> List[str]:
        """Récupère la liste des canaux d'un nœud"""
        try:
            url = f"{self.base_url}/node/{node_id}/channels"
            html = await self._get_page(url)
            if not html:
                return []
                
            soup = BeautifulSoup(html, 'html.parser')
            channels = []
            for channel_elem in soup.find_all('div', class_='channel-item'):
                channel_id = channel_elem.get('data-channel-id')
                if channel_id:
                    channels.append(channel_id)
            return channels
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des canaux du nœud {node_id}: {str(e)}")
            return []
            
    async def start_periodic_update(self, interval: int = 3600):
        """Démarre la mise à jour périodique des données"""
        while True:
            try:
                await self.update_all_data()
                logger.info(f"Mise à jour des données terminée. Prochaine mise à jour dans {interval} secondes")
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour périodique: {str(e)}")
                await asyncio.sleep(60)  # Attente d'une minute en cas d'erreur 