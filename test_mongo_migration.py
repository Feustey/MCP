#!/usr/bin/env python3
import asyncio
import logging
import os
import json
from mongo_operations import MongoOperations

# Configuration du logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_mongo_connection():
    """Teste la connexion à MongoDB"""
    logger.info("Test de connexion à MongoDB...")
    mongo_ops = MongoOperations()
    
    try:
        # Simple test de connexion
        await mongo_ops.db.command("ping")
        logger.info("✅ Connexion à MongoDB réussie")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur de connexion à MongoDB: {str(e)}")
        return False

async def count_json_files():
    """Compte les fichiers JSON dans le répertoire de données"""
    data_dir = "collected_data"
    if not os.path.exists(data_dir):
        logger.warning(f"Le répertoire {data_dir} n'existe pas")
        return 0
        
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    logger.info(f"Nombre de fichiers JSON trouvés: {len(json_files)}")
    
    # Calcul de la taille totale
    total_size = 0
    for file in json_files:
        file_path = os.path.join(data_dir, file)
        size = os.path.getsize(file_path)
        total_size += size
        logger.info(f"  - {file}: {size / 1024:.2f} KB")
    
    logger.info(f"Taille totale des fichiers JSON: {total_size / (1024*1024):.2f} MB")
    return len(json_files)

async def test_mongo_storage():
    """Teste le stockage et la récupération depuis MongoDB"""
    logger.info("Test de stockage/récupération MongoDB...")
    mongo_ops = MongoOperations()
    
    # Test avec un petit jeu de données
    test_data = {
        "name": "test_migration",
        "timestamp": "2023-04-24T12:00:00",
        "nodes": [
            {"id": 1, "name": "node1"},
            {"id": 2, "name": "node2"}
        ]
    }
    
    # Test de sauvegarde
    try:
        result = await mongo_ops.db.test_migration.insert_one(test_data)
        if result.inserted_id:
            logger.info(f"✅ Données de test insérées avec succès, ID: {result.inserted_id}")
        else:
            logger.error("❌ Échec de l'insertion des données de test")
            return False
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'insertion des données de test: {str(e)}")
        return False
    
    # Test de récupération
    try:
        retrieved_data = await mongo_ops.db.test_migration.find_one({"name": "test_migration"})
        if retrieved_data:
            logger.info("✅ Données de test récupérées avec succès")
            return True
        else:
            logger.error("❌ Données de test non trouvées")
            return False
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des données de test: {str(e)}")
        return False

async def test_network_summary_migration():
    """Teste la migration des données de résumé réseau"""
    logger.info("Test de migration des données de résumé réseau...")
    mongo_ops = MongoOperations()
    
    # Chemin du fichier JSON
    file_path = os.path.join("collected_data", "sparkseer_ln_summary_ts.json")
    if not os.path.exists(file_path):
        logger.warning(f"❓ Le fichier {file_path} n'existe pas, test ignoré")
        return None
    
    # Charger les données
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        logger.info(f"Données chargées depuis {file_path}")
        
        # Sauvegarder dans MongoDB
        result = await mongo_ops.save_network_summary(data)
        if result:
            logger.info("✅ Données de résumé réseau migrées avec succès")
            
            # Vérifier la récupération
            retrieved_data = await mongo_ops.get_latest_network_summary()
            if retrieved_data:
                logger.info("✅ Données de résumé réseau récupérées avec succès")
                return True
            else:
                logger.error("❌ Données de résumé réseau non récupérées")
                return False
        else:
            logger.error("❌ Échec de la migration des données de résumé réseau")
            return False
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration des données de résumé réseau: {str(e)}")
        return False

async def test_centralities_migration():
    """Teste la migration des données de centralités"""
    logger.info("Test de migration des données de centralités...")
    mongo_ops = MongoOperations()
    
    # Chemin du fichier JSON
    file_path = os.path.join("collected_data", "sparkseer_centralities.json")
    if not os.path.exists(file_path):
        logger.warning(f"❓ Le fichier {file_path} n'existe pas, test ignoré")
        return None
    
    # Charger les données
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        logger.info(f"Données chargées depuis {file_path}")
        
        # Sauvegarder dans MongoDB
        result = await mongo_ops.save_centralities(data)
        if result:
            logger.info("✅ Données de centralités migrées avec succès")
            
            # Vérifier la récupération
            retrieved_data = await mongo_ops.get_latest_centralities()
            if retrieved_data:
                logger.info("✅ Données de centralités récupérées avec succès")
                return True
            else:
                logger.error("❌ Données de centralités non récupérées")
                return False
        else:
            logger.error("❌ Échec de la migration des données de centralités")
            return False
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration des données de centralités: {str(e)}")
        return False

async def main():
    logger.info("=== Test de migration JSON vers MongoDB ===")
    
    # Test de connexion MongoDB
    mongo_connection = await test_mongo_connection()
    if not mongo_connection:
        logger.error("Impossible de se connecter à MongoDB, tests abandonnés")
        return
    
    # Compte des fichiers JSON
    await count_json_files()
    
    # Test de stockage MongoDB
    mongo_storage = await test_mongo_storage()
    if not mongo_storage:
        logger.error("Problème de stockage MongoDB, tests de migration ignorés")
        return
    
    # Tests de migration
    network_result = await test_network_summary_migration()
    centralities_result = await test_centralities_migration()
    
    # Résumé des tests
    logger.info("\n=== Résumé des tests ===")
    logger.info(f"Connexion MongoDB: {'✅ Réussi' if mongo_connection else '❌ Échec'}")
    logger.info(f"Stockage MongoDB: {'✅ Réussi' if mongo_storage else '❌ Échec'}")
    logger.info(f"Migration résumé réseau: {'✅ Réussi' if network_result is True else '❌ Échec' if network_result is False else '❓ Ignoré'}")
    logger.info(f"Migration centralités: {'✅ Réussi' if centralities_result is True else '❌ Échec' if centralities_result is False else '❓ Ignoré'}")
    
    logger.info("\nPour effectuer la migration complète, exécutez: python migrate_json_to_mongo.py")

if __name__ == "__main__":
    asyncio.run(main()) 