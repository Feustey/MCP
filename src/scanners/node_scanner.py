#!/usr/bin/env python3
# node_scanner.py - Scanner et stockage des informations des nœuds Lightning

import os
import sys
import asyncio
import logging
import json
import httpx
from datetime import datetime
from typing import Dict, Any, List, Optional
from pymongo import MongoClient, UpdateOne
from pymongo.errors import ServerSelectionTimeoutError, PyMongoError
import argparse
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv(override=True)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/node_scanner.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ajouter le répertoire racine au path pour les imports
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Importer la configuration
from config import MONGO_URL, MONGO_DB_NAME

# Configuration des sources de données
SPARKSEER_API_KEY = os.getenv("SPARKSEER_API_KEY", "")
SPARKSEER_BASE_URL = os.getenv("SPARKSEER_BASE_URL", "https://api.sparkseer.space")

class NodeScanner:
    """Classe pour scanner et stocker les informations des nœuds Lightning"""
    
    def __init__(self):
        """Initialisation du scanner"""
        self.mongo_client = None
        self.db = None
        self.httpx_client = httpx.AsyncClient(timeout=30.0)
        
    async def initialize(self):
        """Initialisation des connexions"""
        try:
            # Connexion MongoDB
            self.mongo_client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            self.db = self.mongo_client[MONGO_DB_NAME]
            
            # Vérification de la connexion
            self.mongo_client.server_info()
            logger.info(f"Connexion à MongoDB établie: {MONGO_URL}")
            
            # Création des index si nécessaire
            self.db.nodes.create_index("pubkey", unique=True)
            self.db.nodes.create_index("alias")
            self.db.nodes.create_index("last_check")
            
            return True
        except ServerSelectionTimeoutError:
            logger.error(f"Impossible de se connecter à MongoDB: {MONGO_URL}")
            return False
        except Exception as e:
            logger.error(f"Erreur d'initialisation: {str(e)}")
            return False
    
    async def close(self):
        """Fermeture des connexions"""
        if self.httpx_client:
            await self.httpx_client.aclose()
        if self.mongo_client:
            self.mongo_client.close()
    
    async def get_node_from_sparkseer(self, pubkey: str) -> Optional[Dict[str, Any]]:
        """Récupère les informations d'un nœud depuis Sparkseer"""
        if not SPARKSEER_API_KEY:
            logger.warning("Clé API Sparkseer non configurée")
            return None
        try:
            headers = {"x-api-key": SPARKSEER_API_KEY}
            # Endpoint pour les infos d'un nœud
            url = f"{SPARKSEER_BASE_URL}/v1/node/{pubkey}"
            response = await self.httpx_client.get(url, headers=headers)
            response.raise_for_status()
            node_data = response.json()
            if not node_data or "pubkey" not in node_data:
                logger.warning(f"Nœud {pubkey} non trouvé sur Sparkseer")
                return None
            # Transformation des données
            result = {
                "pubkey": node_data.get("pubkey", ""),
                "alias": node_data.get("alias", ""),
                "node_capacity": node_data.get("capacity", 0),
                "channels_count": node_data.get("channels_count", 0),
                "channels": node_data.get("channels", []),
                "median_fee": node_data.get("fee_rate_median", 0),
                "base_fee": node_data.get("base_fee_median", 0),
                "last_check": datetime.now().isoformat(),
                "source": "sparkseer",
                "updated_at": node_data.get("updated_at", "")
            }
            # Ajout ping/uptime si dispo
            if "ping" in node_data:
                result["ping"] = node_data["ping"]
            if "uptime" in node_data:
                result["uptime"] = node_data["uptime"]
            return result
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des infos Sparkseer pour {pubkey}: {str(e)}")
            return None
    
    async def scan_node(self, pubkey: str) -> bool:
        """Scan un nœud spécifique et stocke les données (Sparkseer)"""
        try:
            node_info = await self.get_node_from_sparkseer(pubkey)
            if node_info is None:
                logger.warning(f"Impossible d'obtenir des informations pour le nœud {pubkey}")
                return False
            # Stocker dans MongoDB avec upsert
            result = self.db.nodes.update_one(
                {"pubkey": pubkey},
                {"$set": node_info},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"Nœud {pubkey} mis à jour avec succès (Sparkseer)")
            elif result.upserted_id:
                logger.info(f"Nœud {pubkey} ajouté avec succès (Sparkseer)")
            else:
                logger.info(f"Aucune modification pour le nœud {pubkey}")
            return True
        except PyMongoError as e:
            logger.error(f"Erreur MongoDB lors du scan du nœud {pubkey}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue lors du scan du nœud {pubkey}: {str(e)}")
            return False
    
    async def batch_scan_nodes(self, pubkeys: List[str]) -> Dict[str, bool]:
        """Scan un lot de nœuds et retourne les résultats"""
        results = {}
        for pubkey in pubkeys:
            results[pubkey] = await self.scan_node(pubkey)
        return results
    
    def get_node_info(self, pubkey: str) -> Optional[Dict[str, Any]]:
        """Récupère les informations d'un nœud depuis la BDD"""
        try:
            if not self.db:
                logger.error("MongoDB non initialisé")
                return None
                
            node = self.db.nodes.find_one({"pubkey": pubkey})
            return node
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du nœud {pubkey}: {str(e)}")
            return None
    
    async def update_outdated_nodes(self, max_age_days: int = 7) -> int:
        """Met à jour les nœuds dont les informations sont périmées"""
        try:
            # Calculer la date limite
            from datetime import timedelta
            limit_date = (datetime.now() - timedelta(days=max_age_days)).isoformat()
            
            # Trouver les nœuds à mettre à jour
            outdated_nodes = list(self.db.nodes.find(
                {"last_check": {"$lt": limit_date}},
                {"pubkey": 1}
            ))
            
            pubkeys = [node["pubkey"] for node in outdated_nodes]
            
            if not pubkeys:
                logger.info("Aucun nœud à mettre à jour")
                return 0
                
            logger.info(f"{len(pubkeys)} nœuds à mettre à jour")
            
            # Mettre à jour par lots
            batch_size = 10
            updated_count = 0
            
            for i in range(0, len(pubkeys), batch_size):
                batch = pubkeys[i:i+batch_size]
                results = await self.batch_scan_nodes(batch)
                updated_count += sum(1 for success in results.values() if success)
            
            logger.info(f"{updated_count} nœuds mis à jour avec succès")
            return updated_count
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des nœuds périmés: {str(e)}")
            return 0

async def main():
    """Fonction principale"""
    try:
        parser = argparse.ArgumentParser(description="Scan de nœuds Lightning")
        parser.add_argument('--pubkeys', nargs='*', help='Liste de pubkeys à scanner (séparées par des espaces)')
        args = parser.parse_args()

        # Initialiser le scanner
        logger.info("Initialisation du scanner de nœuds Lightning")
        scanner = NodeScanner()
        
        if not await scanner.initialize():
            logger.error("Erreur d'initialisation, impossible de continuer")
            return 1
        
        if args.pubkeys:
            pubkeys = args.pubkeys
            logger.info(f"Scan de {len(pubkeys)} nœuds Lightning (pubkeys passées en argument)...")
            for pubkey in pubkeys:
                logger.info(f"Scan du nœud {pubkey}...")
                success = await scanner.scan_node(pubkey)
                if success:
                    node_info = scanner.get_node_info(pubkey)
                    if node_info:
                        logger.info(f"Nœud récupéré: {node_info.get('alias','?')} {pubkey} - {node_info.get('channels_count', 0)} canaux, {node_info.get('node_capacity', 0):,} sats de capacité")
        else:
            # Tester avec quelques nœuds connus
            test_nodes = [
                # Format : (Alias, Pubkey)
                ("Podcast Index", "03ae9f91a0cb8ff43840e3c322c4c61f019d8c1c3cea15a25cfc425ac605e61a4a"),
                ("ACINQ", "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f"),
                ("Breez", "02d96eadea3d780104449aca5c93461ce67c1564e2e1d73225fa67dd3b997a919f"),
                ("BTCPay Server", "0357712cde38c9e82044ce5070473585e35dcb6069014a7e31a28909a1f1ed0d9c"),
                ("Wallet of Satoshi", "035e4ff418fc8b5554c5d9eea66396c227bd429a3251c8cbc711002ba215bfc226"),
                ("feustey", "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"),
                ("barcelona", "03ea0975a7136641752f657f618c8b4c1ee70e03c0baa3c2c6ecfff628cf9d5cb9"),
            ]
            logger.info(f"Scan de {len(test_nodes)} nœuds Lightning...")
            for alias, pubkey in test_nodes:
                logger.info(f"Scan du nœud {alias} ({pubkey})...")
                success = await scanner.scan_node(pubkey)
                if success:
                    node_info = scanner.get_node_info(pubkey)
                    if node_info:
                        logger.info(f"Nœud {alias} récupéré: {node_info.get('channels_count', 0)} canaux, "
                                   f"{node_info.get('node_capacity', 0):,} sats de capacité")
        # Fermeture des connexions
        await scanner.close()
        logger.info("Scan des nœuds terminé avec succès")
        return 0
    except KeyboardInterrupt:
        logger.info("Processus interrompu par l'utilisateur")
        return 0
    except Exception as e:
        logger.critical(f"Erreur critique: {str(e)}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Processus interrompu par l'utilisateur")
    except Exception as e:
        logger.critical(f"Erreur fatale: {str(e)}")
        sys.exit(1) 