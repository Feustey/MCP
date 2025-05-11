#!/usr/bin/env python3
import os
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from src.integrations.amboss_integration import AmbossAPIIntegration
from src.integrations.lnrouter_integration import LNRouterAPIIntegration

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()

class ExternalDataAggregator:
    """
    Classe pour agréger les données de sources externes (Amboss, LNRouter)
    et les combiner avec les métriques internes.
    """
    
    def __init__(self):
        # Initialisation des connecteurs d'API
        self.amboss_api = AmbossAPIIntegration()
        self.lnrouter_api = LNRouterAPIIntegration()
        
        # Configuration des chemins de données
        self.data_dir = os.getenv("DATA_DIR", "data")
        self.raw_dir = f"{self.data_dir}/raw"
        self.metrics_dir = f"{self.data_dir}/metrics"
        
        # S'assurer que les répertoires existent
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(f"{self.raw_dir}/amboss", exist_ok=True)
        os.makedirs(f"{self.raw_dir}/lnrouter", exist_ok=True)
        os.makedirs(self.metrics_dir, exist_ok=True)
        
        # Intervalle de mise à jour (en secondes)
        self.update_interval = int(os.getenv("UPDATE_INTERVAL_SECONDS", "3600"))  # Par défaut, toutes les heures
        
        logger.info("Initialisation d'ExternalDataAggregator")
    
    async def initialize(self):
        """Initialise les connexions aux APIs externes."""
        amboss_initialized = await self.amboss_api.initialize()
        lnrouter_initialized = await self.lnrouter_api.initialize()
        
        if amboss_initialized and lnrouter_initialized:
            logger.info("Toutes les connexions aux APIs externes établies avec succès")
            return True
        else:
            logger.warning("Certaines connexions aux APIs externes n'ont pas pu être établies")
            return False
    
    async def collect_node_data(self, node_pubkeys: List[str]) -> Dict[str, Dict]:
        """
        Collecte les données des nœuds depuis toutes les sources disponibles.
        
        Args:
            node_pubkeys: Liste des clés publiques des nœuds
            
        Returns:
            Dict: Données combinées des nœuds
        """
        # Obtenir les données Amboss
        amboss_data = await self.amboss_api.fetch_and_store_nodes_data(node_pubkeys)
        
        # Obtenir les données LNRouter
        lnrouter_data = await self.lnrouter_api.fetch_topology_data(node_pubkeys)
        
        # Combiner les données
        combined_data = {}
        for pubkey in node_pubkeys:
            node_data = {
                "pubkey": pubkey,
                "amboss": amboss_data.get(pubkey, {}),
                "lnrouter": lnrouter_data.get(pubkey, {}),
                "timestamp": datetime.now().isoformat()
            }
            combined_data[pubkey] = node_data
        
        # Sauvegarde des données combinées
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_file = f"{self.raw_dir}/combined_node_data_{timestamp}.json"
        
        with open(combined_file, "w") as f:
            json.dump(combined_data, f, indent=2)
        
        logger.info(f"Données combinées sauvegardées dans {combined_file}")
        return combined_data
    
    def calculate_node_reliability_score(self, node_data: Dict[str, Any]) -> float:
        """
        Calcule un score de fiabilité pour un nœud en fonction des données disponibles.
        
        Args:
            node_data: Données du nœud
            
        Returns:
            float: Score de fiabilité (0-100)
        """
        # Initialiser le score
        reliability_score = 0.0
        weights = {
            "uptime": 0.4,            # Importance du temps de disponibilité
            "amboss_reputation": 0.3, # Importance de la réputation Amboss
            "centrality": 0.2,        # Importance de la centralité dans le réseau
            "channel_health": 0.1     # Importance de la santé des canaux
        }
        
        # Facteurs Amboss (uptime et réputation)
        amboss = node_data.get("amboss", {})
        if amboss:
            health = amboss.get("health", {})
            reputation = amboss.get("reputation", {})
            
            # Facteur d'uptime
            if "uptimePercent" in health:
                uptime_score = float(health["uptimePercent"]) if isinstance(health["uptimePercent"], (int, float)) else 0
                reliability_score += uptime_score * weights["uptime"]
            
            # Facteur de réputation
            if "reputationScore" in reputation:
                reputation_score = float(reputation["reputationScore"]) if isinstance(reputation["reputationScore"], (int, float)) else 0
                reliability_score += reputation_score * weights["amboss_reputation"]
        
        # Facteurs LNRouter (centralité)
        lnrouter = node_data.get("lnrouter", {})
        if lnrouter:
            centrality = lnrouter.get("centrality", {})
            if "betweenness" in centrality and "closeness" in centrality:
                betweenness = float(centrality["betweenness"]) if isinstance(centrality["betweenness"], (int, float)) else 0
                closeness = float(centrality["closeness"]) if isinstance(centrality["closeness"], (int, float)) else 0
                
                # Normaliser entre 0 et 100
                centrality_score = (betweenness * 0.6 + closeness * 0.4) * 100
                reliability_score += min(100, centrality_score) * weights["centrality"]
            
            # Facteur de santé des canaux
            channels = lnrouter.get("channels", [])
            if channels:
                active_channels = sum(1 for c in channels if c.get("active", False))
                channel_health_score = (active_channels / len(channels)) * 100 if channels else 0
                reliability_score += channel_health_score * weights["channel_health"]
        
        return round(min(100, reliability_score), 2)
    
    async def generate_node_metrics(self, combined_data: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Génère des métriques enrichies pour les nœuds à partir des données combinées.
        
        Args:
            combined_data: Données combinées des nœuds
            
        Returns:
            Dict: Métriques enrichies des nœuds
        """
        enriched_metrics = {}
        
        for pubkey, node_data in combined_data.items():
            # Calculer le score de fiabilité
            reliability_score = self.calculate_node_reliability_score(node_data)
            
            # Extraire les métriques clés d'Amboss
            amboss_metrics = {}
            if "amboss" in node_data and node_data["amboss"]:
                health = node_data["amboss"].get("health", {})
                reputation = node_data["amboss"].get("reputation", {})
                
                amboss_metrics = {
                    "health_score": health.get("healthScore", 0),
                    "uptime_percent": health.get("uptimePercent", 0),
                    "reputation_score": reputation.get("reputationScore", 0),
                }
            
            # Extraire les métriques clés de LNRouter
            lnrouter_metrics = {}
            if "lnrouter" in node_data and node_data["lnrouter"]:
                metrics = node_data["lnrouter"].get("metrics", {})
                centrality = node_data["lnrouter"].get("centrality", {})
                
                lnrouter_metrics = {
                    "betweenness": centrality.get("betweenness", 0),
                    "closeness": centrality.get("closeness", 0),
                    "avg_fee_rate": metrics.get("avg_fee_rate", 0),
                    "total_capacity": metrics.get("total_capacity", 0),
                }
            
            # Compiler les métriques enrichies
            enriched_metrics[pubkey] = {
                "pubkey": pubkey,
                "alias": node_data.get("amboss", {}).get("health", {}).get("alias", "Unknown"),
                "reliability_score": reliability_score,
                "amboss_metrics": amboss_metrics,
                "lnrouter_metrics": lnrouter_metrics,
                "timestamp": datetime.now().isoformat()
            }
        
        # Sauvegarde des métriques enrichies
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = f"{self.metrics_dir}/enriched_node_metrics_{timestamp}.json"
        
        with open(metrics_file, "w") as f:
            json.dump(enriched_metrics, f, indent=2)
        
        logger.info(f"Métriques enrichies sauvegardées dans {metrics_file}")
        return enriched_metrics
    
    async def run_periodic_update(self, node_pubkeys: List[str], run_once: bool = False):
        """
        Exécute des mises à jour périodiques des données.
        
        Args:
            node_pubkeys: Liste des clés publiques des nœuds à suivre
            run_once: Si True, exécute une seule mise à jour puis s'arrête
        """
        try:
            while True:
                logger.info("Début de la mise à jour périodique des données")
                
                # Collecte et agrégation des données
                combined_data = await self.collect_node_data(node_pubkeys)
                
                # Génération de métriques enrichies
                await self.generate_node_metrics(combined_data)
                
                if run_once:
                    logger.info("Mode run_once activé, arrêt après une mise à jour")
                    break
                
                logger.info(f"Mise à jour complète, prochaine mise à jour dans {self.update_interval} secondes")
                await asyncio.sleep(self.update_interval)
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour périodique: {str(e)}")
    
    async def close(self):
        """Ferme toutes les connexions."""
        await self.amboss_api.close()
        await self.lnrouter_api.close()
        logger.info("Toutes les connexions fermées")

async def main():
    """Fonction principale pour tester l'agrégateur de données."""
    # Liste des nœuds à surveiller (exemples avec des nœuds connus)
    test_nodes = [
        "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f", # ACINQ
        "02d96eadea3d780104449aca5c93461ce67c1564e2e1d73225fa67dd3b997a919b", # Bitfinex
        "02d4531a2f2e6e5a9033d37d548cff4834a3898e74c3abe1985b493c42ebbd707d"  # Kraken
    ]
    
    aggregator = ExternalDataAggregator()
    await aggregator.initialize()
    
    # Exécuter une seule mise à jour pour le test
    await aggregator.run_periodic_update(test_nodes, run_once=True)
    
    await aggregator.close()

if __name__ == "__main__":
    asyncio.run(main()) 