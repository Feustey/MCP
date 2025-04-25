#!/usr/bin/env python3
"""
Script d'archivage automatique des données historiques
Ce script peut être exécuté quotidiennement via cron ou un autre planificateur
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Ajout du répertoire parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mongo_operations import MongoOperations
from src.models import ArchiveSettings

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/archiving.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("archiving")

# Collections à archiver avec leurs paramètres par défaut
DEFAULT_ARCHIVE_SETTINGS = [
    {
        "collection_name": "metrics_history",
        "retention_days": 90,
        "archive_after_days": 365,
        "compression_enabled": True,
        "archiving_frequency": "daily"
    },
    {
        "collection_name": "query_history",
        "retention_days": 30,
        "archive_after_days": 180,
        "compression_enabled": True,
        "archiving_frequency": "daily"
    }
]

async def ensure_archive_settings(mongo_ops: MongoOperations) -> None:
    """
    S'assure que les paramètres d'archivage sont configurés pour chaque collection
    """
    for settings in DEFAULT_ARCHIVE_SETTINGS:
        # Vérification si les paramètres existent déjà
        existing_settings = await mongo_ops.get_archive_settings(settings["collection_name"])
        
        if not existing_settings:
            # Création des paramètres par défaut
            logger.info(f"Création des paramètres d'archivage pour {settings['collection_name']}")
            await mongo_ops.save_archive_settings(ArchiveSettings(**settings))
        else:
            logger.info(f"Paramètres d'archivage existants pour {settings['collection_name']}")

async def run_archiving() -> None:
    """
    Exécute le processus d'archivage pour toutes les collections configurées
    """
    try:
        # Initialisation des opérations MongoDB
        mongo_ops = MongoOperations()
        await mongo_ops.initialize()
        
        # Vérification des paramètres d'archivage
        await ensure_archive_settings(mongo_ops)
        
        # Récupération de toutes les collections à archiver
        all_collections = []
        for settings in DEFAULT_ARCHIVE_SETTINGS:
            all_collections.append(settings["collection_name"])
        
        # Exécution de l'archivage pour chaque collection
        results = []
        for collection_name in all_collections:
            try:
                logger.info(f"Archivage de la collection {collection_name}")
                stats = await mongo_ops.archive_old_data(collection_name)
                results.append(stats)
                logger.info(f"Archivage terminé: {stats['archived_count']} documents archivés, {stats['deleted_count']} documents supprimés")
            except Exception as e:
                logger.error(f"Erreur lors de l'archivage de {collection_name}: {str(e)}")
        
        # Résumé de l'opération
        total_archived = sum(stats.get("archived_count", 0) for stats in results)
        total_deleted = sum(stats.get("deleted_count", 0) for stats in results)
        
        logger.info(f"Archivage terminé: {total_archived} documents archivés, {total_deleted} documents supprimés")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'archivage: {str(e)}")
    finally:
        # Fermeture de la connexion
        await mongo_ops.close()

if __name__ == "__main__":
    # Exécution du processus d'archivage
    asyncio.run(run_archiving()) 