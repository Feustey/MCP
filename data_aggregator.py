import os
import aiohttp
import asyncio
import logging
import json
import ssl
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional
from cache_manager import CacheManager
from src.data_augmentation import DataAugmentor
from src.data_batcher import DataBatcher
from dotenv import load_dotenv
from mongo_operations import MongoOperations

# Chargement des variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Nombre maximum de nœuds individuels à interroger pour les statistiques détaillées
MAX_NODES_TO_QUERY = 10 

class DataAggregator:
    def __init__(self):
        self.cache_manager = CacheManager()
        self.data_augmentor = DataAugmentor()
        self.data_batcher = DataBatcher(batch_size=32)
        self.mongo_ops = MongoOperations()
        self.sparkseer_api_key = os.getenv("SPARKSEER_API_KEY")
        self.lnbits_url = os.getenv("LNBITS_URL")
        self.lnbits_admin_key = os.getenv("LNBITS_ADMIN_KEY", "")
        self.lnbits_invoice_key = os.getenv("LNBITS_INVOICE_KEY", "")
        self.lnbits_user_id = os.getenv("LNBITS_USER_ID", "")
        self.sparkseer_base_url = "https://api.sparkseer.space"
        self.data_dir = "collected_data"
        
        # Configuration SSL pour LNBits
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # Création du répertoire de données s'il n'existe pas
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        # Log des configurations
        logger.info(f"Configuration initiale:")
        logger.info(f"- Sparkseer Base URL: {self.sparkseer_base_url}")
        logger.info(f"- LNBits URL: {self.lnbits_url}")
        logger.info(f"- Sparkseer API Key présente: {'Oui' if self.sparkseer_api_key else 'Non'}")
        logger.info(f"- LNBits Admin Key présente: {'Oui' if self.lnbits_admin_key and len(self.lnbits_admin_key) > 10 else 'Non'}")
        logger.info(f"- LNBits Invoice Key présente: {'Oui' if self.lnbits_invoice_key and len(self.lnbits_invoice_key) > 10 else 'Non'}")
        logger.info(f"- LNBits User ID présent: {'Oui' if self.lnbits_user_id else 'Non'}")

    async def initialize(self):
        """Initialise les connexions et les ressources nécessaires"""
        logger.info("Initialisation du DataAggregator")
        return self

    async def _make_sparkseer_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, needs_auth: bool = False) -> Optional[Dict[str, Any]]:
        """Fonction utilitaire pour les requêtes Sparkseer"""
        url = f"{self.sparkseer_base_url}{endpoint}"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        if needs_auth:
            if not self.sparkseer_api_key:
                logger.warning(f"Clé API Sparkseer requise pour {endpoint} mais non fournie.")
                return None
            headers["api-key"] = self.sparkseer_api_key
        
        logger.info(f"Requête Sparkseer - URL: {url}")
        logger.info(f"Params: {params}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    response_text = await response.text()
                    logger.info(f"Réponse brute pour {endpoint}: {response_text[:200]}...")
                    
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 401:
                         logger.error(f"Erreur d'authentification (401) pour {endpoint}. Vérifiez votre clé API.")
                         return None
                    else:
                        logger.error(f"Erreur lors de la récupération depuis {endpoint}: {response.status}")
                        logger.error(f"Corps de la réponse: {response_text}")
                        return None
        except Exception as e:
            logger.error(f"Exception lors de la requête vers {endpoint}: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    async def save_to_json(self, data: Any, filename: str) -> None:
        """Sauvegarde les données dans un fichier JSON (gardé pour compatibilité)"""
        if data is None:
            logger.warning(f"Aucune donnée à sauvegarder pour {filename}.")
            return
            
        filepath = os.path.join(self.data_dir, filename)
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Données sauvegardées dans {filepath}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde dans {filepath}: {str(e)}")
            logger.warning(f"Migration vers MongoDB recommandée.")
            raise

    async def aggregate_data(self):
        """Fonction principale pour agréger les données"""
        try:
            await self.initialize()
            
            # Vérifier le cache pour les données réseau
            cached_network_data = await self.cache_manager.get('network_summary', 'network_metrics')
            if cached_network_data:
                logger.info("Utilisation des données réseau en cache")
                network_summary_ts = cached_network_data
            else:
                # Récupération du résumé temporel du réseau
                logger.info("Récupération du résumé temporel du réseau...")
                network_summary_ts = await self.fetch_sparkseer_network_summary_ts()
                await self.cache_manager.set('network_summary', network_summary_ts, 'network_metrics')
            
            # Récupération et augmentation des données des nœuds
            logger.info("Récupération des centralités...")
            centralities = await self.fetch_sparkseer_centralities()
            
            if centralities and 'nodes' in centralities:
                # Augmentation des données
                augmented_nodes = [
                    self.data_augmentor.augment_node_data(node)
                    for node in centralities['nodes']
                ]
                
                # Traitement par batchs
                processed_nodes = []
                for batch in self.data_batcher.shuffle_and_batch(augmented_nodes):
                    # Traitement du batch
                    processed_batch = await self._process_node_batch(batch)
                    processed_nodes.extend(processed_batch)
                
                # Mise à jour des centralités avec les données augmentées
                centralities['nodes'] = processed_nodes
                
                # Mise en cache des données augmentées
                await self.cache_manager.set('centralities', centralities, 'node_data')
            
            # Sauvegarde des données dans MongoDB
            if network_summary_ts:
                logger.info("Sauvegarde du résumé réseau dans MongoDB...")
                await self.mongo_ops.save_network_summary(network_summary_ts)
                
            if centralities:
                logger.info("Sauvegarde des centralités dans MongoDB...")
                await self.mongo_ops.save_centralities(centralities)
            
            # Sauvegarde en JSON maintenue pour compatibilité (peut être désactivée après migration complète)
            # await self.save_to_json(network_summary_ts, "sparkseer_ln_summary_ts.json")
            # await self.save_to_json(centralities, "sparkseer_centralities.json")
            
            # Récupération des données LNBits si disponibles
            if self.lnbits_admin_key and len(self.lnbits_admin_key) > 10:
                cached_wallets = await self.cache_manager.get('lnbits_wallets', 'wallet_data')
                if cached_wallets:
                    logger.info("Utilisation des wallets LNBits en cache")
                    lnbits_wallets = cached_wallets
                else:
                    logger.info("Récupération des wallets LNBits...")
                    lnbits_wallets = await self.fetch_lnbits_wallets()
                    if lnbits_wallets:
                        await self.cache_manager.set('lnbits_wallets', lnbits_wallets, 'wallet_data')
                        # Sauvegarde dans MongoDB au lieu de JSON
                        collection_name = "lnbits_wallets"
                        logger.info(f"Sauvegarde des wallets LNBits dans la collection MongoDB {collection_name}...")
                        await self.mongo_ops.db[collection_name].insert_one({
                            "data": lnbits_wallets,
                            "timestamp": datetime.now()
                        })
                        # await self.save_to_json(lnbits_wallets, "lnbits_wallets.json")
            
            return {
                'network_summary': network_summary_ts,
                'centralities': centralities,
                'lnbits_wallets': lnbits_wallets if 'lnbits_wallets' in locals() else None
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'agrégation des données: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    async def _process_node_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Traite un batch de nœuds"""
        processed_nodes = []
        for node in batch:
            try:
                # Ajout de métadonnées de traitement
                node['processed_at'] = datetime.now().isoformat()
                node['batch_size'] = len(batch)
                processed_nodes.append(node)
            except Exception as e:
                logger.error(f"Erreur lors du traitement du nœud {node.get('pubkey', 'unknown')}: {str(e)}")
        return processed_nodes

    async def fetch_sparkseer_top_nodes(self, limit: int = 100) -> Optional[Dict[str, Any]]:
        """Récupère les nœuds top depuis Sparkseer"""
        endpoint = "/v1/nodes" 
        params = {
            "limit": limit,
            "sort": "capacity",
            "order": "desc"
        }
        return await self._make_sparkseer_request(endpoint, params=params, needs_auth=False)

    async def fetch_sparkseer_channel_metrics(self) -> Optional[Dict[str, Any]]:
        """Récupère les métriques des canaux depuis Sparkseer"""
        endpoint = "/v1/channels"
        params = {
            "metrics": "true"
        }
        return await self._make_sparkseer_request(endpoint, params=params, needs_auth=False)

    async def fetch_lnbits_wallets(self) -> Optional[List[Dict[str, Any]]]:
        """Récupère les wallets depuis LNBits."""
        if not self.lnbits_url:
             logger.warning("URL LNBits manquante.")
             return None
             
        url = f"{self.lnbits_url}/api/v1/wallets"
        headers = {
            "Content-type": "application/json",
            "X-Api-Key": self.lnbits_admin_key
        }
        params = None # Pas de params par défaut
        
        if self.lnbits_admin_key:
            headers["X-Api-Key"] = self.lnbits_admin_key
            logger.info("Utilisation de la clé Admin LNBits.")
        else:
             logger.warning("Clé Admin LNBits non trouvée. Impossible de récupérer les wallets via cet endpoint.")
             return None 
        
        logger.info(f"Requête LNBits wallets - URL: {url}")
        logger.info(f"Params LNBits: {params}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params, ssl=self.ssl_context) as response:
                    response_text = await response.text()
                    logger.info(f"Réponse brute LNBits wallets: {response_text[:500]}...") # Augmenté la taille loggée
                    
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 401:
                        logger.error(f"Erreur d\'authentification LNBits (401): Clé API invalide? {response_text}")
                        return None
                    elif response.status == 403: # Gérer l'erreur 403 vue précédemment
                         logger.error(f"Erreur d\'autorisation LNBits (403): {response_text}")
                         return None
                    else:
                        logger.error(f"Erreur lors de la récupération des wallets LNBits: {response.status}")
                        logger.error(f"Corps de la réponse: {response_text}")
                        return None
        except Exception as e:
            logger.error(f"Exception lors de la récupération des wallets LNBits: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    async def fetch_sparkseer_network_summary_ts(self) -> Optional[Dict[str, Any]]:
        """Récupère le résumé temporel du réseau depuis Sparkseer"""
        # Essayer d'abord de récupérer depuis MongoDB
        logger.info("Tentative de récupération du résumé réseau depuis MongoDB...")
        mongo_data = await self.mongo_ops.get_latest_network_summary()
        
        if mongo_data:
            logger.info("Résumé réseau récupéré depuis MongoDB")
            return mongo_data
            
        # Si non trouvé, faire la requête API
        logger.info("Résumé réseau non trouvé dans MongoDB, récupération depuis l'API...")
        endpoint = "/v1/stats/ln-summary-ts"
        return await self._make_sparkseer_request(endpoint, needs_auth=False)

    async def fetch_sparkseer_centralities(self) -> Optional[Dict[str, Any]]:
        """Récupère les centralités depuis Sparkseer"""
        # Essayer d'abord de récupérer depuis MongoDB
        logger.info("Tentative de récupération des centralités depuis MongoDB...")
        mongo_data = await self.mongo_ops.get_latest_centralities()
        
        if mongo_data:
            logger.info("Centralités récupérées depuis MongoDB")
            return mongo_data
            
        # Si non trouvé, faire la requête API
        logger.info("Centralités non trouvées dans MongoDB, récupération depuis l'API...")
        endpoint = "/v1/stats/centralities"
        return await self._make_sparkseer_request(endpoint, needs_auth=False)
        
    async def fetch_sparkseer_node_current_stats(self, pubkey: str) -> Optional[Dict[str, Any]]:
        """Récupère les stats actuelles pour un nœud spécifique"""
        if not pubkey: return None
        endpoint = f"/v1/node/current-stats/{pubkey}"
        return await self._make_sparkseer_request(endpoint, needs_auth=True)

    async def fetch_sparkseer_node_historical_stats(self, pubkey: str) -> Optional[Dict[str, Any]]:
        """Récupère les stats historiques pour un nœud spécifique"""
        if not pubkey: return None
        endpoint = f"/v1/node/historical/{pubkey}"
        return await self._make_sparkseer_request(endpoint, needs_auth=True)

    async def fetch_sparkseer_channel_recommendations(self) -> Optional[Dict[str, Any]]:
        """Récupère les recommandations de canaux (Service)"""
        endpoint = "/v1/services/channel-recommendations"
        data = await self._make_sparkseer_request(endpoint, needs_auth=True)
        
        if data:
            # Sauvegarder dans MongoDB
            collection_name = "channel_recommendations"
            logger.info(f"Sauvegarde des recommandations de canaux dans MongoDB...")
            await self.mongo_ops.db[collection_name].insert_one({
                "data": data,
                "timestamp": datetime.now()
            })
        
        return data

    async def fetch_sparkseer_suggested_fees(self) -> Optional[Dict[str, Any]]:
        """Récupère les suggestions de frais (Service)"""
        endpoint = "/v1/services/suggested-fees"
        data = await self._make_sparkseer_request(endpoint, needs_auth=True)
        
        if data:
            # Sauvegarder dans MongoDB
            collection_name = "suggested_fees"
            logger.info(f"Sauvegarde des suggestions de frais dans MongoDB...")
            await self.mongo_ops.db[collection_name].insert_one({
                "data": data,
                "timestamp": datetime.now()
            })
        
        return data

    async def fetch_sparkseer_outbound_liquidity_value(self) -> Optional[Dict[str, Any]]:
        """Récupère la valeur de liquidité sortante (Service)"""
        endpoint = "/v1/services/outbound-liquidity-value"
        data = await self._make_sparkseer_request(endpoint, needs_auth=True)
        
        if data:
            # Sauvegarder dans MongoDB
            collection_name = "outbound_liquidity"
            logger.info(f"Sauvegarde des données de liquidité sortante dans MongoDB...")
            await self.mongo_ops.db[collection_name].insert_one({
                "data": data,
                "timestamp": datetime.now()
            })
        
        return data

async def main():
    aggregator = DataAggregator()
    await aggregator.aggregate_data()

if __name__ == "__main__":
    asyncio.run(main()) 