#!/usr/bin/env python3
"""
Script pour initialiser les collections MongoDB nécessaires au système RAG augmenté.
Ce script crée les collections et les index requis pour optimiser les performances.
"""

import os
import sys
# Ajouter le répertoire parent au sys.path pour trouver le module src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import logging
from argparse import ArgumentParser
from datetime import datetime

from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
from src.mongo_operations import MongoOperations

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Définitions des collections et index
COLLECTIONS_CONFIG = {
    "metrics_history": [
        IndexModel([("timestamp", DESCENDING)], name="timestamp_desc"),
        IndexModel([("node_id", ASCENDING), ("timestamp", DESCENDING)], name="node_id_timestamp"),
        IndexModel([("source", ASCENDING), ("timestamp", DESCENDING)], name="source_timestamp")
    ],
    "query_history": [
        IndexModel([("timestamp", DESCENDING)], name="timestamp_desc"),
        IndexModel([("query", TEXT)], name="query_text"),
        IndexModel([("query_type", ASCENDING), ("timestamp", DESCENDING)], name="type_timestamp")
    ],
    "hypothesis": [
        IndexModel([("timestamp", DESCENDING)], name="timestamp_desc"),
        IndexModel([("is_validated", ASCENDING)], name="is_validated"),
        IndexModel([("source", ASCENDING), ("topic", ASCENDING)], name="source_topic"),
        IndexModel([("description", TEXT)], name="description_text")
    ],
    "documentation": [
        IndexModel([("metadata.timestamp", DESCENDING)], name="timestamp_desc"),
        IndexModel([("metadata.type", ASCENDING)], name="doc_type"),
        IndexModel([("content", TEXT)], name="content_text")
    ],
    "logs": [
        IndexModel([("timestamp", DESCENDING)], name="timestamp_desc"),
        IndexModel([("level", ASCENDING), ("timestamp", DESCENDING)], name="level_timestamp"),
        IndexModel([("source", ASCENDING), ("timestamp", DESCENDING)], name="source_timestamp")
    ]
}

async def setup_collections(mongo_url, drop_existing=False):
    """
    Configure les collections MongoDB pour le système RAG augmenté.
    
    Args:
        mongo_url: URL de connexion MongoDB
        drop_existing: Supprimer les collections existantes avant la création
    """
    # Initialisation de la connexion MongoDB
    mongo_ops = MongoOperations(mongo_url)
    await mongo_ops.connect()
    
    db = mongo_ops.db
    
    # Configuration de chaque collection
    for collection_name, indexes in COLLECTIONS_CONFIG.items():
        logger.info(f"Configuration de la collection: {collection_name}")
        
        # Suppression de la collection si demandé
        if drop_existing and collection_name in await db.list_collection_names():
            logger.warning(f"Suppression de la collection existante: {collection_name}")
            await db.drop_collection(collection_name)
        
        # Création de la collection si elle n'existe pas
        if collection_name not in await db.list_collection_names():
            logger.info(f"Création de la collection: {collection_name}")
            await db.create_collection(collection_name)
        
        # Création des index
        collection = db[collection_name]
        existing_indexes = await collection.index_information()
        
        for index in indexes:
            index_name = index.document.get('name', '')
            if index_name not in existing_indexes:
                logger.info(f"Création de l'index {index_name} pour {collection_name}")
                await collection.create_indexes([index])
            else:
                logger.info(f"L'index {index_name} existe déjà pour {collection_name}")
    
    # Insérer des données de base pour la documentation
    if "documentation" in await db.list_collection_names():
        docs_count = await db.documentation.count_documents({})
        if docs_count == 0:
            await _insert_base_documentation(db)
    
    logger.info("Configuration des collections terminée")

async def _insert_base_documentation(db):
    """
    Insère la documentation de base dans la collection documentation.
    
    Args:
        db: Instance de la base de données MongoDB
    """
    logger.info("Insertion de la documentation de base")
    
    base_docs = [
        {
            "content": "# Documentation du Système RAG Augmenté\n\nLe système RAG Augmenté est une évolution du système RAG qui ajoute la pondération dynamique des sources et l'extraction avancée de contraintes.",
            "metadata": {
                "type": "system_overview",
                "title": "Vue d'ensemble du système RAG Augmenté",
                "timestamp": datetime.now(),
                "source": "documentation"
            }
        },
        {
            "content": "# Pondération Dynamique des Sources\n\nLa pondération dynamique des sources permet d'ajuster automatiquement l'importance relative des sources de données en fonction du contexte de la requête.",
            "metadata": {
                "type": "feature_guide",
                "title": "Guide de la pondération dynamique",
                "timestamp": datetime.now(),
                "source": "documentation"
            }
        },
        {
            "content": "# Extraction de Contraintes\n\nL'extraction avancée de contraintes permet d'identifier automatiquement des critères de filtrage implicites dans les requêtes en langage naturel.",
            "metadata": {
                "type": "feature_guide",
                "title": "Guide de l'extraction de contraintes",
                "timestamp": datetime.now(),
                "source": "documentation"
            }
        }
    ]
    
    await db.documentation.insert_many(base_docs)
    logger.info(f"Documentation de base insérée: {len(base_docs)} documents")

def main():
    """Fonction principale avec parsing des arguments"""
    parser = ArgumentParser(description="Configuration des collections MongoDB pour RAG augmenté")
    parser.add_argument("--mongo-url", required=True, help="URL de connexion MongoDB")
    parser.add_argument("--drop-existing", action="store_true", 
                      help="Supprimer les collections existantes avant la création")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(setup_collections(args.mongo_url, args.drop_existing))
        print("Configuration terminée avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de la configuration: {str(e)}")
        print(f"Erreur: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 