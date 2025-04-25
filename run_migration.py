#!/usr/bin/env python3
import os
import asyncio
import logging
import shutil
import sys
from migrate_json_to_mongo import JsonToMongoMigrator
from data_aggregator import DataAggregator

# Configuration du logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SLUGIGNORE_PATH = ".slugignore"
BACKUP_DIR = "json_backup"

async def update_slugignore():
    """Met à jour le fichier .slugignore pour exclure les fichiers JSON"""
    logger.info("Mise à jour du fichier .slugignore")
    
    # S'assurer que collected_data est dans .slugignore
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

async def backup_json_files():
    """Crée une sauvegarde des fichiers JSON"""
    data_dir = "collected_data"
    if not os.path.exists(data_dir):
        logger.warning(f"Le répertoire {data_dir} n'existe pas, pas de sauvegarde à faire")
        return False
        
    # Créer le répertoire de sauvegarde
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        logger.info(f"Répertoire de sauvegarde {BACKUP_DIR} créé")
    
    # Copier tous les fichiers JSON
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    if not json_files:
        logger.warning("Aucun fichier JSON à sauvegarder")
        return False
        
    for file in json_files:
        source = os.path.join(data_dir, file)
        destination = os.path.join(BACKUP_DIR, file)
        shutil.copy2(source, destination)
        logger.info(f"Sauvegarde de {source} vers {destination}")
    
    logger.info(f"{len(json_files)} fichiers JSON sauvegardés dans {BACKUP_DIR}")
    return True

async def test_data_aggregator_with_mongodb():
    """Teste l'agrégateur de données avec MongoDB"""
    logger.info("Test de l'agrégateur de données avec MongoDB...")
    
    # Exécuter l'agrégateur avec MongoDB
    aggregator = DataAggregator()
    try:
        result = await aggregator.aggregate_data()
        if result:
            logger.info("✅ Agrégateur de données fonctionnel avec MongoDB")
            return True
        else:
            logger.error("❌ Problème avec l'agrégateur de données")
            return False
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exécution de l'agrégateur: {str(e)}")
        return False

async def main():
    logger.info("=== Migration des données JSON vers MongoDB ===")
    
    # Confirmation de l'utilisateur
    if len(sys.argv) <= 1 or sys.argv[1] != "--confirm":
        print("\n⚠️  ATTENTION: Cette opération va migrer toutes les données JSON vers MongoDB et peut supprimer les fichiers originaux.")
        print("Assurez-vous d'avoir une connexion MongoDB active et correctement configurée.")
        print("\nOptions:")
        print("  --confirm       Exécuter la migration sans demander confirmation")
        print("  --test-only     Exécuter uniquement les tests de migration sans modifier les fichiers")
        print("  --no-backup     Ne pas créer de sauvegarde des fichiers JSON")
        print("  --keep-json     Conserver les fichiers JSON originaux après migration")
        print("\nExemple: python run_migration.py --confirm --keep-json\n")
        
        user_input = input("Voulez-vous continuer? (oui/non): ")
        if user_input.lower() not in ['oui', 'o', 'yes', 'y']:
            logger.info("Migration annulée")
            return
    
    # Options
    test_only = "--test-only" in sys.argv
    no_backup = "--no-backup" in sys.argv
    keep_json = "--keep-json" in sys.argv
    
    # Sauvegarde des fichiers JSON
    if not no_backup and not test_only:
        await backup_json_files()
    
    # Mise à jour du fichier .slugignore
    if not test_only:
        await update_slugignore()
    
    if test_only:
        logger.info("Mode test uniquement - exécution des tests de migration")
        # Exécuter le script de test
        import test_mongo_migration
        await test_mongo_migration.main()
        return
    
    # Migrer les données
    logger.info("Démarrage de la migration des données...")
    migrator = JsonToMongoMigrator()
    results = await migrator.migrate_all()
    
    # Statistiques de migration
    success_count = sum(1 for result in results.values() if result)
    total_count = len(results)
    logger.info(f"Migration terminée: {success_count}/{total_count} fichiers migrés avec succès")
    
    # Suppression des fichiers JSON après migration
    if not keep_json and success_count > 0:
        logger.info("Suppression des fichiers JSON originaux...")
        removed_files = await migrator.remove_migrated_files(results)
        logger.info(f"{len(removed_files)} fichiers supprimés")
    
    # Test de l'agrégateur de données
    logger.info("Test de l'agrégateur de données avec MongoDB...")
    aggregator_test = await test_data_aggregator_with_mongodb()
    
    # Résumé
    logger.info("\n=== Résumé de la migration ===")
    logger.info(f"Fichiers migrés: {success_count}/{total_count}")
    logger.info(f"Agrégateur avec MongoDB: {'✅ Fonctionnel' if aggregator_test else '❌ Problèmes détectés'}")
    if not keep_json:
        logger.info(f"Fichiers JSON supprimés: {len(removed_files) if 'removed_files' in locals() else 0}")
    else:
        logger.info("Les fichiers JSON originaux ont été conservés")
    
    logger.info("\nPour revenir à la version JSON, vous pouvez restaurer les fichiers depuis:")
    logger.info(f"  - Le répertoire de sauvegarde: {BACKUP_DIR}")
    logger.info(f"  - Les fichiers .bak dans {migrator.data_dir}")
    
    logger.info("\nMigration terminée avec succès")

if __name__ == "__main__":
    asyncio.run(main()) 