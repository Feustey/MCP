#!/usr/bin/env python3
import os
import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()

class LNRouterAPIIntegration:
    """
    Classe pour intégrer l'API LNRouter avec le système RAG.
    Permet d'utiliser les données de LNRouter comme source pour enrichir
    le RAG avec des données topologiques avancées et des métriques de centralité.
    """
    
    def __init__(self):
        # Configuration LNRouter API
        self.lnrouter_api_url = os.getenv("LNROUTER_API_URL", "https://api.lnrouter.app/v1")
        self.lnrouter_api_key = os.getenv("LNROUTER_API_KEY", "")
        
        logger.info(f"Initialisation de LNRouterAPIIntegration avec URL: {self.lnrouter_api_url}")
    
    async def initialize(self):
        """Initialise les connexions et vérifie l'accès à l'API LNRouter."""
        try:
            # Vérification de l'accès à l'API LNRouter
            if not self.lnrouter_api_key:
                logger.warning("Clé API LNRouter non configurée")
                return False
                
            # Test de connexion à l'API
            network_info = await self.get_network_info()
            if "error" not in network_info:
                logger.info("Connexion à l'API LNRouter établie avec succès")
                return True
            else:
                logger.warning(f"Impossible de se connecter à l'API LNRouter: {network_info.get('error')}")
                return False
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'API LNRouter: {str(e)}")
            return False
    
    async def call_lnrouter_api(self, endpoint: str, method: str = "GET", params: Dict = None, data: Dict = None) -> Dict[str, Any]:
        """
        Appelle l'API LNRouter.
        
        Args:
            endpoint: Point de terminaison de l'API
            method: Méthode HTTP à utiliser
            params: Paramètres de requête
            data: Données à envoyer (pour POST/PUT)
            
        Returns:
            Dict: Les données récupérées
        """
        headers = {
            "X-API-KEY": self.lnrouter_api_key,
            "Content-Type": "application/json"
        }
        
        url = f"{self.lnrouter_api_url}/{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                if method.upper() == "GET":
                    async with session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            error_text = await response.text()
                            logger.error(f"Erreur lors de l'appel à LNRouter API: {response.status} - {error_text}")
                            return {"error": f"Erreur HTTP {response.status}: {error_text}"}
                elif method.upper() == "POST":
                    async with session.post(url, headers=headers, json=data) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            error_text = await response.text()
                            logger.error(f"Erreur lors de l'appel à LNRouter API: {response.status} - {error_text}")
                            return {"error": f"Erreur HTTP {response.status}: {error_text}"}
        except Exception as e:
            logger.error(f"Exception lors de l'appel à LNRouter API: {str(e)}")
            return {"error": str(e)}
    
    async def get_network_info(self) -> Dict[str, Any]:
        """
        Récupère les informations générales sur le réseau Lightning.
        
        Returns:
            Dict: Informations sur le réseau
        """
        return await self.call_lnrouter_api("network/info")
    
    async def get_node_centrality(self, node_pubkey: str) -> Dict[str, Any]:
        """
        Récupère les métriques de centralité d'un nœud.
        
        Args:
            node_pubkey: Clé publique du nœud
            
        Returns:
            Dict: Métriques de centralité du nœud
        """
        return await self.call_lnrouter_api(f"node/{node_pubkey}/centrality")
    
    async def get_node_metrics(self, node_pubkey: str) -> Dict[str, Any]:
        """
        Récupère les métriques complètes d'un nœud.
        
        Args:
            node_pubkey: Clé publique du nœud
            
        Returns:
            Dict: Métriques du nœud
        """
        return await self.call_lnrouter_api(f"node/{node_pubkey}")
    
    async def get_path_finding(self, source_pubkey: str, target_pubkey: str, amount_sats: int = 100000) -> Dict[str, Any]:
        """
        Récupère les informations de routage entre deux nœuds.
        
        Args:
            source_pubkey: Clé publique du nœud source
            target_pubkey: Clé publique du nœud cible
            amount_sats: Montant en satoshis à router
            
        Returns:
            Dict: Informations de routage
        """
        data = {
            "source": source_pubkey,
            "target": target_pubkey,
            "amount_sats": amount_sats
        }
        return await self.call_lnrouter_api("path/find", method="POST", data=data)
    
    async def get_node_channels(self, node_pubkey: str) -> Dict[str, Any]:
        """
        Récupère la liste des canaux d'un nœud.
        
        Args:
            node_pubkey: Clé publique du nœud
            
        Returns:
            Dict: Liste des canaux du nœud
        """
        return await self.call_lnrouter_api(f"node/{node_pubkey}/channels")
    
    async def fetch_topology_data(self, node_pubkeys: List[str]) -> Dict[str, Dict]:
        """
        Récupère les données topologiques pour une liste de nœuds.
        
        Args:
            node_pubkeys: Liste des clés publiques des nœuds
            
        Returns:
            Dict: Données topologiques indexées par clé publique
        """
        result = {}
        for pubkey in node_pubkeys:
            metrics = await self.get_node_metrics(pubkey)
            centrality = await self.get_node_centrality(pubkey)
            channels = await self.get_node_channels(pubkey)
            
            result[pubkey] = {
                "metrics": metrics,
                "centrality": centrality,
                "channels": channels,
                "timestamp": datetime.now().isoformat()
            }
        
        # Sauvegarde des données dans un fichier
        output_dir = "data/raw/lnrouter"
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{output_dir}/topology_data_{timestamp}.json"
        
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Données topologiques LNRouter sauvegardées dans {output_file}")
        return result
    
    async def get_routing_suggestions(self, node_pubkey: str) -> Dict[str, Any]:
        """
        Récupère des suggestions de routage pour un nœud.
        
        Args:
            node_pubkey: Clé publique du nœud
            
        Returns:
            Dict: Suggestions de routage
        """
        return await self.call_lnrouter_api(f"node/{node_pubkey}/suggestions")
    
    async def close(self):
        """Ferme les connexions."""
        logger.info("Fermeture des connexions LNRouter")
        # Pas de connexion spécifique à fermer actuellement
        pass

async def main():
    """Fonction principale pour tester l'intégration LNRouter."""
    lnrouter_api = LNRouterAPIIntegration()
    await lnrouter_api.initialize()
    
    # Exemple de récupération des informations réseau
    network_info = await lnrouter_api.get_network_info()
    print(json.dumps(network_info, indent=2))
    
    # Exemple de récupération des métriques d'un nœud (ACINQ)
    node_pubkey = "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f"
    node_metrics = await lnrouter_api.get_node_metrics(node_pubkey)
    node_centrality = await lnrouter_api.get_node_centrality(node_pubkey)
    
    print(json.dumps(node_metrics, indent=2))
    print(json.dumps(node_centrality, indent=2))
    
    await lnrouter_api.close()

if __name__ == "__main__":
    asyncio.run(main()) 