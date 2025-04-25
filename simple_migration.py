#!/usr/bin/env python3
import os
import json
import asyncio
import logging
import shutil
from datetime import datetime
from pymongo import MongoClient

# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DATA_DIR = "collected_data"
BACKUP_DIR = "json_backup"
SLUGIGNORE_PATH = ".slugignore"
MONGO_URI = os.getenv("DATABASE_URL", "mongodb+srv://feustey:VwSrcnNI8i5m2sim@dazlng.ug0aiaw.mongodb.net/?retryWrites=true&w=majority&appName=DazLng")
DB_NAME = "dazlng"

def backup_json_files():
    """Crée une sauvegarde des fichiers JSON"""
    if not os.path.exists(DATA_DIR):
        logger.warning(f"Le répertoire {DATA_DIR} n'existe pas")
        return False
        
    # Créer le répertoire de sauvegarde
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        logger.info(f"Répertoire de sauvegarde {BACKUP_DIR} créé")
    
    # Copier tous les fichiers JSON
    json_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
    if not json_files:
        logger.warning("Aucun fichier JSON à sauvegarder")
        return False
        
    for file in json_files:
        source = os.path.join(DATA_DIR, file)
        destination = os.path.join(BACKUP_DIR, file)
        shutil.copy2(source, destination)
        logger.info(f"Sauvegarde de {source} vers {destination}")
    
    logger.info(f"{len(json_files)} fichiers JSON sauvegardés dans {BACKUP_DIR}")
    return True

def update_slugignore():
    """Met à jour le fichier .slugignore pour exclure les fichiers JSON"""
    if os.path.exists(SLUGIGNORE_PATH):
        with open(SLUGIGNORE_PATH, 'r') as f:
            content = f.read()
            
        # Vérifier si collected_data est déjà exclu
        if "collected_data/" in content:
            logger.info("Le répertoire collected_data est déjà exclu dans .slugignore")
        else:
            # Ajouter collected_data à .slugignore
            with open(SLUGIGNORE_PATH, 'a') as f:
                f.write("\n# Exclusion des données JSON (migrées vers MongoDB)\ncollected_data/\n")
            logger.info("collected_data/ ajouté à .slugignore")
            
        return True
    else:
        logger.error(f"Le fichier {SLUGIGNORE_PATH} n'existe pas")
        return False

def migrate_json_to_mongo():
    """Migre les fichiers JSON vers MongoDB"""
    # Connexion à MongoDB
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        logger.info(f"Connexion à MongoDB établie sur {DB_NAME}")
    except Exception as e:
        logger.error(f"Erreur de connexion à MongoDB: {str(e)}")
        return False
    
    # Mapping des fichiers JSON vers les collections MongoDB
    collection_mapping = {
        "sparkseer_centralities.json": "centralities",
        "sparkseer_ln_summary_ts.json": "network_summaries",
        "sparkseer_outbound_liquidity_value.json": "outbound_liquidity",
        "sparkseer_suggested_fees.json": "suggested_fees",
        "sparkseer_channel_recommendations.json": "channel_recommendations",
        "network_metrics.json": "network_metrics",
        "lnbits_wallets.json": "lnbits_wallets",
        "sparkseer_channels.json": "channels",
        "sparkseer_nodes.json": "nodes"
    }
    
    # Migrer chaque fichier JSON
    results = {}
    if not os.path.exists(DATA_DIR):
        logger.warning(f"Le répertoire {DATA_DIR} n'existe pas")
        return results
        
    json_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
    logger.info(f"{len(json_files)} fichiers JSON trouvés dans {DATA_DIR}")
    
    for file_name in json_files:
        file_path = os.path.join(DATA_DIR, file_name)
        
        # Déterminer la collection cible
        collection_name = collection_mapping.get(file_name)
        if not collection_name:
            # Utiliser le nom du fichier sans extension comme nom de collection
            collection_name = os.path.splitext(file_name)[0]
        
        logger.info(f"Migration de {file_name} vers la collection {collection_name}")
        
        try:
            # Lire le fichier JSON
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Ajouter un timestamp
            if isinstance(data, dict):
                data['timestamp'] = datetime.now()
                # Insérer le document
                result = db[collection_name].insert_one(data)
                
                # Sauvegarder aussi dans latest_data pour accès rapide
                db.latest_data.update_one(
                    {"data_type": collection_name},
                    {"$set": {"data": data, "updated_at": datetime.now()}},
                    upsert=True
                )
                
                logger.info(f"Document inséré, ID: {result.inserted_id}")
                results[file_name] = True
            elif isinstance(data, list):
                # Ajouter un timestamp à chaque élément
                for item in data:
                    if isinstance(item, dict):
                        item['timestamp'] = datetime.now()
                
                # Insérer les documents
                result = db[collection_name].insert_many(data)
                logger.info(f"{len(result.inserted_ids)} documents insérés")
                results[file_name] = True
            else:
                logger.error(f"Format de données non supporté dans {file_name}")
                results[file_name] = False
                
        except Exception as e:
            logger.error(f"Erreur lors de la migration de {file_name}: {str(e)}")
            results[file_name] = False
    
    # Statistiques
    success_count = sum(1 for result in results.values() if result)
    logger.info(f"Migration terminée: {success_count}/{len(json_files)} fichiers migrés avec succès")
    
    return results

def remove_migrated_files(results):
    """Supprime les fichiers JSON après migration réussie"""
    removed_files = []
    
    for file_name, success in results.items():
        if success:
            file_path = os.path.join(DATA_DIR, file_name)
            try:
                # Créer une sauvegarde avant suppression
                backup_path = f"{file_path}.bak"
                if os.path.exists(file_path):
                    shutil.copy2(file_path, backup_path)
                    logger.info(f"Sauvegarde créée: {backup_path}")
                    
                    # Supprimer le fichier original
                    os.remove(file_path)
                    logger.info(f"Fichier supprimé: {file_path}")
                    removed_files.append(file_name)
            except Exception as e:
                logger.error(f"Erreur lors de la suppression de {file_path}: {str(e)}")
                
    return removed_files

def main():
    print("\n=== Migration des données JSON vers MongoDB ===")
    print("\nCette opération va:")
    print("1. Sauvegarder vos fichiers JSON dans un dossier de backup")
    print("2. Migrer les données vers MongoDB")
    print("3. Mettre à jour .slugignore pour exclure le dossier collected_data")
    print("4. Supprimer les fichiers JSON originaux (avec sauvegarde .bak)")
    
    user_input = input("\nVoulez-vous continuer? (oui/non): ")
    if user_input.lower() not in ['oui', 'o', 'yes', 'y']:
        print("Migration annulée")
        return
    
    # Option de conservation des fichiers JSON
    keep_json = input("Conserver les fichiers JSON originaux? (oui/non, défaut: non): ")
    keep_json = keep_json.lower() in ['oui', 'o', 'yes', 'y']
    
    # Sauvegarde des fichiers
    print("\nSauvegarde des fichiers JSON...")
    backup_json_files()
    
    # Mise à jour de .slugignore
    print("\nMise à jour de .slugignore...")
    update_slugignore()
    
    # Migration des données
    print("\nMigration des données vers MongoDB...")
    results = migrate_json_to_mongo()
    
    # Suppression des fichiers
    if not keep_json:
        print("\nSuppression des fichiers JSON originaux...")
        removed_files = remove_migrated_files(results)
        print(f"{len(removed_files)} fichiers supprimés")
    else:
        print("\nLes fichiers JSON originaux ont été conservés")
    
    print("\nMigration terminée!")
    print(f"\nPour restaurer les fichiers, utilisez les sauvegardes dans:")
    print(f"- Le répertoire {BACKUP_DIR}")
    print(f"- Les fichiers .bak dans {DATA_DIR}")

if __name__ == "__main__":
    main() 