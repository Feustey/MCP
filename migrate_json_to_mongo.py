#!/usr/bin/env python3
import os
import asyncio
import logging
import glob
from typing import List, Dict, Any
from mongo_operations import MongoOperations

# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JsonToMongoMigrator:
    def __init__(self):
        self.mongo_ops = MongoOperations()
        self.data_dir = "collected_data"
        self.migration_map = {
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
        
    def get_json_files(self) -> List[str]:
        """Récupère tous les fichiers JSON dans le répertoire de données"""
        json_pattern = os.path.join(self.data_dir, "*.json")
        return glob.glob(json_pattern)
        
    async def migrate_file(self, file_path: str) -> bool:
        """Migre un fichier JSON vers MongoDB"""
        file_name = os.path.basename(file_path)
        logger.info(f"Migration du fichier: {file_name}")
        
        # Déterminer la collection cible
        collection_name = self.migration_map.get(file_name)
        if not collection_name:
            logger.warning(f"Collection non spécifiée pour {file_name}, utilisation du nom de fichier comme nom de collection")
            collection_name = os.path.splitext(file_name)[0]  # Nom du fichier sans extension
            
        # Migrer les données
        result = await self.mongo_ops.save_json_to_collection(file_path, collection_name)
        
        # Si c'est l'un des fichiers volumineux principaux, utiliser également les méthodes spécifiques
        if file_name == "sparkseer_centralities.json" and result:
            # Charger les données pour les enregistrer via la méthode spécifique
            import json
            with open(file_path, 'r') as f:
                centralities_data = json.load(f)
            await self.mongo_ops.save_centralities(centralities_data)
            logger.info(f"Données de centralités également sauvegardées via méthode spécifique")
            
        elif file_name == "sparkseer_ln_summary_ts.json" and result:
            # Charger les données pour les enregistrer via la méthode spécifique
            import json
            with open(file_path, 'r') as f:
                network_summary = json.load(f)
            await self.mongo_ops.save_network_summary(network_summary)
            logger.info(f"Données de résumé réseau également sauvegardées via méthode spécifique")
            
        return result
        
    async def migrate_all(self) -> Dict[str, Any]:
        """Migre tous les fichiers JSON vers MongoDB"""
        json_files = self.get_json_files()
        logger.info(f"Fichiers JSON trouvés: {len(json_files)}")
        
        results = {}
        for file_path in json_files:
            file_name = os.path.basename(file_path)
            result = await self.migrate_file(file_path)
            results[file_name] = result
            
        return results
        
    async def remove_migrated_files(self, results: Dict[str, bool]) -> List[str]:
        """Supprime les fichiers JSON après migration réussie"""
        removed_files = []
        
        for file_name, success in results.items():
            if success:
                file_path = os.path.join(self.data_dir, file_name)
                try:
                    # Créer une sauvegarde avant suppression
                    backup_path = f"{file_path}.bak"
                    if os.path.exists(file_path):
                        import shutil
                        shutil.copy2(file_path, backup_path)
                        logger.info(f"Sauvegarde créée: {backup_path}")
                        
                        # Supprimer le fichier original
                        os.remove(file_path)
                        logger.info(f"Fichier supprimé: {file_path}")
                        removed_files.append(file_name)
                except Exception as e:
                    logger.error(f"Erreur lors de la suppression de {file_path}: {str(e)}")
                    
        return removed_files

async def main():
    logger.info("Début de la migration JSON vers MongoDB")
    migrator = JsonToMongoMigrator()
    
    # Migrer les données
    results = await migrator.migrate_all()
    
    # Statistiques de migration
    success_count = sum(1 for result in results.values() if result)
    total_count = len(results)
    logger.info(f"Migration terminée: {success_count}/{total_count} fichiers migrés avec succès")
    
    # Demander confirmation avant suppression
    user_input = input("Voulez-vous supprimer les fichiers JSON originaux? (oui/non): ")
    if user_input.lower() in ['oui', 'o', 'yes', 'y']:
        removed_files = await migrator.remove_migrated_files(results)
        logger.info(f"Fichiers supprimés: {len(removed_files)}")
    else:
        logger.info("Les fichiers JSON originaux ont été conservés")
    
    logger.info("Migration terminée avec succès")

if __name__ == "__main__":
    asyncio.run(main()) 