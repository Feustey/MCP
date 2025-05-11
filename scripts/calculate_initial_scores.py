#!/usr/bin/env python3
# scripts/calculate_initial_scores.py

import asyncio
import logging
import os
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Importer le service de scoring
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.services.lightning_scoring import LightningScoreService

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

# Configuration MongoDB
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "daznode")

# Collections
NODES_COLLECTION = "lightning_nodes"
SCORES_COLLECTION = "lightning_scores"

async def main():
    try:
        # Se connecter à MongoDB
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[MONGO_DB]
        
        # Vérifier si la collection de scores existe déjà et la supprimer
        collections = await db.list_collection_names()
        if SCORES_COLLECTION in collections:
            await db[SCORES_COLLECTION].drop()
            logger.info(f"Collection {SCORES_COLLECTION} supprimée")
        
        # Créer le service de scoring
        scoring_service = LightningScoreService(db)
        
        # Récupérer tous les nœuds
        nodes = await db[NODES_COLLECTION].find().to_list(length=None)
        
        if not nodes:
            logger.error(f"Aucun nœud trouvé dans la collection {NODES_COLLECTION}")
            return
        
        logger.info(f"Calcul des scores pour {len(nodes)} nœuds...")
        
        # Calculer les scores pour tous les nœuds
        start_time = datetime.now()
        count = 0
        
        for node in nodes:
            try:
                node_id = node["public_key"]
                score = await scoring_service.calculate_node_score(node_id)
                if score:
                    count += 1
                    logger.debug(f"Score calculé pour {node['alias']} ({node_id}): {score.metrics.composite:.2f}")
            except Exception as e:
                logger.error(f"Erreur lors du calcul du score pour {node.get('alias', 'inconnu')}: {e}")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Calcul des scores terminé: {count}/{len(nodes)} scores calculés en {duration:.2f} secondes")
        
        # Créer les indices pour la collection des scores
        await db[SCORES_COLLECTION].create_index("node_id")
        await db[SCORES_COLLECTION].create_index([("node_id", 1), ("timestamp", -1)])
        await db[SCORES_COLLECTION].create_index("metrics.composite")
        
        logger.info("Indices créés pour la collection des scores")
    
    except Exception as e:
        logger.error(f"Erreur lors du calcul des scores: {e}")
    finally:
        # Fermer la connexion
        client.close()

if __name__ == "__main__":
    logger.info("Démarrage du calcul des scores initiaux")
    asyncio.run(main()) 