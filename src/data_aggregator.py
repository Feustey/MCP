import sys
import os
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
import aiohttp
import asyncio
import logging
import json
import ssl
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional
from rag.cache_manager import CacheManager
from dotenv import load_dotenv

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
        self.sparkseer_api_key = os.getenv("SPARKSEER_API_KEY")
        self.lnbits_url = os.getenv("LNBITS_URL")
        self.lnbits_admin_key = os.getenv("LNBITS_ADMIN_KEY", "")
        self.lnbits_invoice_key = os.getenv("LNBITS_INVOICE_KEY", "")
        self.lnbits_user_id = os.getenv("LNBITS_USER_ID", "")
        self.sparkseer_base_url = "https://api.sparkseer.space"  # Retrait de /api/v1
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
        """Sauvegarde les données dans un fichier JSON"""
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
            raise

    async def aggregate_data(self):
        """Fonction principale pour agréger les données"""
        try:
            await self.initialize()
            
            # --- Récupération des données Sparkseer ---
            logger.info("--- Début récupération données Sparkseer ---")
            
            # 1. Liste des noeuds top (Commenté - Endpoint invalide?)
            # logger.info("Récupération des nœuds top...")
            # top_nodes_data = await self.fetch_sparkseer_top_nodes()
            # top_nodes = top_nodes_data.get("nodes", []) if top_nodes_data else []
            # await self.save_to_json(top_nodes_data, "sparkseer_top_nodes.json")
            # logger.info(f"Nombre de nœuds top récupérés : {len(top_nodes)}")
            top_nodes = [] # Initialiser comme vide car non récupéré

            # 2. Métriques des canaux (Commenté - Endpoint invalide?)
            # logger.info("Récupération des métriques de canaux...")
            # channel_metrics_data = await self.fetch_sparkseer_channel_metrics()
            # await self.save_to_json(channel_metrics_data, "sparkseer_channel_metrics.json")
            # if channel_metrics_data and "channels" in channel_metrics_data:
            #      logger.info(f"Nombre de métriques de canaux récupérées : {len(channel_metrics_data['channels'])}")
            channel_metrics_data = None # Initialiser comme None car non récupéré
            
            # 3. Résumé temporel du réseau (Nouveau)
            logger.info("Récupération du résumé temporel du réseau...")
            network_summary_ts = await self.fetch_sparkseer_network_summary_ts()
            await self.save_to_json(network_summary_ts, "sparkseer_ln_summary_ts.json")

            # 4. Centralités (Nouveau)
            logger.info("Récupération des centralités...")
            centralities = await self.fetch_sparkseer_centralities()
            await self.save_to_json(centralities, "sparkseer_centralities.json")
            
            # 5. Statistiques individuelles des N premiers nœuds (Commenté - Dépend de top_nodes)
            # individual_node_stats = {}
            # historical_node_stats = {}
            # if top_nodes:
            #     logger.info(f"Récupération des stats individuelles pour les {min(len(top_nodes), MAX_NODES_TO_QUERY)} premiers nœuds...")
            #     nodes_to_query = top_nodes[:MAX_NODES_TO_QUERY]
            #     tasks_current = [self.fetch_sparkseer_node_current_stats(node.get("pubkey")) for node in nodes_to_query if node.get("pubkey")]
            #     tasks_historical = [self.fetch_sparkseer_node_historical_stats(node.get("pubkey")) for node in nodes_to_query if node.get("pubkey")]
            #     
            #     results_current = await asyncio.gather(*tasks_current)
            #     results_historical = await asyncio.gather(*tasks_historical)

            #     for i, node in enumerate(nodes_to_query):
            #         pubkey = node.get("pubkey")
            #         if pubkey:
            #             if results_current[i]:
            #                 individual_node_stats[pubkey] = results_current[i]
            #             if results_historical[i]:
            #                  historical_node_stats[pubkey] = results_historical[i]

            #     await self.save_to_json(individual_node_stats, "sparkseer_individual_node_stats.json")
            #     await self.save_to_json(historical_node_stats, "sparkseer_historical_node_stats.json")
            # else:
            #     logger.warning("Aucun nœud top récupéré, impossible de récupérer les stats individuelles.")
            logger.warning("Récupération des stats individuelles désactivée (dépend de top_nodes).")

            # 6. Services (Nouveau - Nécessite API Key)
            if self.sparkseer_api_key:
                logger.info("Récupération des recommandations de canaux (Service)...")
                channel_recs = await self.fetch_sparkseer_channel_recommendations()
                await self.save_to_json(channel_recs, "sparkseer_channel_recommendations.json")

                logger.info("Récupération des suggestions de frais (Service)...")
                suggested_fees = await self.fetch_sparkseer_suggested_fees()
                await self.save_to_json(suggested_fees, "sparkseer_suggested_fees.json")
                
                logger.info("Récupération de la valeur de liquidité sortante (Service)...")
                outbound_value = await self.fetch_sparkseer_outbound_liquidity_value()
                await self.save_to_json(outbound_value, "sparkseer_outbound_liquidity_value.json")
            else:
                 logger.warning("Clé API Sparkseer non fournie, services non interrogés.")

            logger.info("--- Fin récupération données Sparkseer ---")

            # Récupération des données LNBits
            if self.lnbits_admin_key and len(self.lnbits_admin_key) > 10:
                logger.info("Récupération des wallets LNBits...")
                lnbits_wallets = await self.fetch_lnbits_wallets()
                await self.save_to_json(lnbits_wallets, "lnbits_wallets.json")
                if lnbits_wallets:
                    logger.info(f"Nombre de wallets récupérés : {len(lnbits_wallets)}")
                else:
                    logger.warning("Aucun wallet récupéré de LNBits")
            else:
                logger.warning("Clé admin LNBits non configurée ou invalide, récupération des wallets ignorée.")
            
            # --- Calcul Métriques réseau (Commenté - Dépend de top_nodes et channel_metrics)
            # if top_nodes and channel_metrics_data and "channels" in channel_metrics_data:
            #      channels = channel_metrics_data["channels"]
            #      network_metrics = {
            #          \'total_capacity\': sum(node.get(\'capacity\', 0) for node in top_nodes), # Peut être redondant avec ln_summary_ts
            #          \'total_channels\': len(channels), # Peut être redondant avec ln_summary_ts
            #          \'total_nodes\': len(top_nodes), # Peut être redondant avec ln_summary_ts
            #          \'average_fee_rate\': sum(channel.get(\'fee_rate\', {}).get(\'rate\', 0) for channel in channels) / len(channels) if channels else 0,
            #          \'timestamp\': datetime.now().isoformat()
            #      }
            #      await self.save_to_json(network_metrics, "network_metrics.json")
            #      logger.info("Métriques réseau calculées et sauvegardées")
            # else:
            #      logger.warning("Impossible de calculer les métriques réseau (manque top_nodes ou channel_metrics).")
            logger.warning("Calcul des métriques réseau désactivé (dépend de top_nodes/channel_metrics).")

        except Exception as e:
            logger.error(f"Erreur majeure lors de l'agrégation des données: {str(e)}")
            logger.error(f"Détails de l'erreur: {traceback.format_exc()}")
            raise

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
        headers = {"Content-type": "application/json"}
        params = None # Pas de params par défaut

        # Déterminer la clé à utiliser et si on doit envoyer 'usr'
        # Règle : Si on a la clé ADMIN, on l'utilise et on n'envoie PAS usr.
        # Si on n'a PAS la clé ADMIN mais on a la clé INVOICE/READ et USER_ID, 
        # on utilise la clé INVOICE/READ et on envoie usr.
        # Ici, on simplifie : si LNBITS_ADMIN_KEY est là, on l'utilise sans usr.
        # (La logique pour clé non-admin nécessiterait d'autres endpoints ou ajustements)
        
        if self.lnbits_admin_key:
            headers["X-Api-Key"] = self.lnbits_admin_key
            logger.info("Utilisation de la clé Admin LNBits.")
        # elif self.lnbits_invoice_key and self.lnbits_user_id: # Logique alternative si pas de clé admin
        #     headers["X-Api-Key"] = self.lnbits_invoice_key
        #     params = {'usr': self.lnbits_user_id}
        #     logger.info(f"Utilisation de la clé Invoice LNBits et User ID: {self.lnbits_user_id}")
        else:
             logger.warning("Clé Admin LNBits non trouvée. Impossible de récupérer les wallets via cet endpoint.")
             # Peut-être tenter avec invoice key si la logique est différente?
             # Pour l'instant, on retourne None si pas de clé admin.
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
        endpoint = "/v1/stats/ln-summary-ts"
        return await self._make_sparkseer_request(endpoint, needs_auth=False)

    async def fetch_sparkseer_centralities(self) -> Optional[Dict[str, Any]]:
        """Récupère les centralités depuis Sparkseer"""
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
        return await self._make_sparkseer_request(endpoint, needs_auth=True)

    async def fetch_sparkseer_suggested_fees(self) -> Optional[Dict[str, Any]]:
        """Récupère les suggestions de frais (Service)"""
        endpoint = "/v1/services/suggested-fees"
        return await self._make_sparkseer_request(endpoint, needs_auth=True)

    async def fetch_sparkseer_outbound_liquidity_value(self) -> Optional[Dict[str, Any]]:
        """Récupère la valeur de liquidité sortante (Service)"""
        endpoint = "/v1/services/outbound-liquidity-value"
        return await self._make_sparkseer_request(endpoint, needs_auth=True)

async def main():
    aggregator = DataAggregator()
    await aggregator.aggregate_data()

if __name__ == "__main__":
    asyncio.run(main()) 