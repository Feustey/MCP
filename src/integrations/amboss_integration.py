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

class AmbossAPIIntegration:
    """
    Classe pour intégrer l'API Amboss avec le système RAG.
    Permet d'utiliser les données d'Amboss comme source pour enrichir
    le RAG avec des données de topologie et de réputation.
    """
    
    def __init__(self):
        # Configuration Amboss API
        self.amboss_api_url = os.getenv("AMBOSS_API_URL", "https://api.amboss.space/graphql")
        # Pas besoin de clé API pour l'accès public
        
        logger.info(f"Initialisation de AmbossAPIIntegration avec URL: {self.amboss_api_url}")
    
    async def initialize(self):
        """Initialise les connexions et vérifie l'accès à l'API Amboss."""
        try:
            # Test simple de connexion à l'API GraphQL
            query = """
            query {
                health {
                    status
                }
            }
            """
            result = await self.query_amboss_api(query)
            if result and "data" in result and "health" in result["data"]:
                logger.info("Connexion à l'API Amboss établie avec succès")
                return True
            else:
                logger.warning("Impossible de se connecter à l'API Amboss")
                return False
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'API Amboss: {str(e)}")
            return False
    
    async def query_amboss_api(self, query: str, variables: Dict = None) -> Dict[str, Any]:
        """
        Exécute une requête GraphQL sur l'API Amboss.
        
        Args:
            query: Requête GraphQL
            variables: Variables pour la requête GraphQL
            
        Returns:
            Dict: Les données récupérées
        """
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.amboss_api_url,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f"Erreur lors de la requête Amboss API: {response.status} - {error_text}")
                        return {"error": f"Erreur HTTP {response.status}: {error_text}"}
        except Exception as e:
            logger.error(f"Exception lors de la requête Amboss API: {str(e)}")
            return {"error": str(e)}
    
    async def get_node_health_data(self, node_pubkey: str) -> Dict[str, Any]:
        """
        Récupère les données de santé d'un nœud depuis Amboss.
        
        Args:
            node_pubkey: Clé publique du nœud
            
        Returns:
            Dict: Les données de santé du nœud
        """
        query = """
        query GetNodeHealth($pubkey: String!) {
            getNode(pubkey: $pubkey) {
                pubkey
                alias
                health {
                    healthScore
                    uptime
                    lastUpdate
                }
                monitoringStatus
                uptimePercent
            }
        }
        """
        
        variables = {"pubkey": node_pubkey}
        return await self.query_amboss_api(query, variables)
    
    async def get_network_insights(self) -> Dict[str, Any]:
        """
        Récupère des statistiques sur le réseau Lightning depuis Amboss.
        
        Returns:
            Dict: Les statistiques du réseau
        """
        query = """
        query {
            getNetworkStats {
                nodeCount
                channelCount
                totalCapacity
                avgCapacity
                avgNodeCapacity
                avgChannelsPerNode
                medianChannelsPerNode
                avgFeerate
                medianFeerate
            }
        }
        """
        
        return await self.query_amboss_api(query)
    
    async def get_node_reputation(self, node_pubkey: str) -> Dict[str, Any]:
        """
        Récupère les données de réputation d'un nœud depuis Amboss.
        
        Args:
            node_pubkey: Clé publique du nœud
            
        Returns:
            Dict: Les données de réputation du nœud
        """
        query = """
        query GetNodeReputation($pubkey: String!) {
            getNode(pubkey: $pubkey) {
                pubkey
                alias
                reputationScore
                reputationFactors {
                    age
                    capacity
                    uptime
                    community
                    channels
                }
            }
        }
        """
        
        variables = {"pubkey": node_pubkey}
        return await self.query_amboss_api(query, variables)
    
    async def fetch_and_store_nodes_data(self, node_pubkeys: List[str]) -> Dict[str, Dict]:
        """
        Récupère et stocke les données de plusieurs nœuds.
        
        Args:
            node_pubkeys: Liste des clés publiques des nœuds
            
        Returns:
            Dict: Dictionnaire avec les données de chaque nœud
        """
        result = {}
        for pubkey in node_pubkeys:
            health_data = await self.get_node_health_data(pubkey)
            reputation_data = await self.get_node_reputation(pubkey)
            
            if "data" in health_data and "data" in reputation_data:
                result[pubkey] = {
                    "health": health_data["data"]["getNode"],
                    "reputation": reputation_data["data"]["getNode"],
                    "timestamp": datetime.now().isoformat()
                }
                
        # Fichier de sortie pour les données
        output_dir = "data/raw/amboss"
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{output_dir}/nodes_data_{timestamp}.json"
        
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Données Amboss sauvegardées dans {output_file}")
        return result
    
    async def close(self):
        """Ferme les connexions."""
        logger.info("Fermeture des connexions Amboss")
        # Pas de connexion spécifique à fermer actuellement
        pass

async def main():
    """Fonction principale pour tester l'intégration Amboss."""
    amboss_api = AmbossAPIIntegration()
    await amboss_api.initialize()
    
    # Exemple de récupération des statistiques réseau
    network_stats = await amboss_api.get_network_insights()
    print(json.dumps(network_stats, indent=2))
    
    # Exemple de récupération des données d'un nœud spécifique (ACINQ)
    node_pubkey = "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f"
    node_health = await amboss_api.get_node_health_data(node_pubkey)
    node_reputation = await amboss_api.get_node_reputation(node_pubkey)
    
    print(json.dumps(node_health, indent=2))
    print(json.dumps(node_reputation, indent=2))
    
    await amboss_api.close()

if __name__ == "__main__":
    asyncio.run(main()) 