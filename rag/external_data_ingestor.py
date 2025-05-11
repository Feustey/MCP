#!/usr/bin/env python3
import os
import sys
import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
import glob

# Ajouter le répertoire parent au chemin Python pour les imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/rag_ingestion_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()

class ExternalDataIngestor:
    """
    Classe pour ingérer les données externes dans le système RAG.
    """
    
    def __init__(self):
        self.data_dir = os.getenv("DATA_DIR", "data")
        self.raw_dir = f"{self.data_dir}/raw"
        self.metrics_dir = f"{self.data_dir}/metrics"
        self.rag_assets_dir = "rag/RAG_assets/documents/external_data"
        
        # Créer les répertoires nécessaires s'ils n'existent pas
        os.makedirs(self.rag_assets_dir, exist_ok=True)
        
        logger.info(f"Initialisation de ExternalDataIngestor")
    
    async def collect_latest_data_files(self) -> Dict[str, List[str]]:
        """
        Collecte les chemins des fichiers de données les plus récents.
        
        Returns:
            Dict[str, List[str]]: Dictionnaire des chemins de fichiers par source
        """
        data_files = {
            "amboss": [],
            "lnrouter": [],
            "combined": [],
            "metrics": []
        }
        
        # Rechercher les fichiers Amboss
        amboss_files = glob.glob(f"{self.raw_dir}/amboss/nodes_data_*.json")
        if amboss_files:
            data_files["amboss"] = sorted(amboss_files, reverse=True)[:3]  # 3 fichiers les plus récents
        
        # Rechercher les fichiers LNRouter
        lnrouter_files = glob.glob(f"{self.raw_dir}/lnrouter/topology_data_*.json")
        if lnrouter_files:
            data_files["lnrouter"] = sorted(lnrouter_files, reverse=True)[:3]
        
        # Rechercher les fichiers combinés
        combined_files = glob.glob(f"{self.raw_dir}/combined_node_data_*.json")
        if combined_files:
            data_files["combined"] = sorted(combined_files, reverse=True)[:3]
        
        # Rechercher les fichiers de métriques
        metrics_files = glob.glob(f"{self.metrics_dir}/enriched_node_metrics_*.json")
        if metrics_files:
            data_files["metrics"] = sorted(metrics_files, reverse=True)[:3]
        
        return data_files
    
    async def format_data_for_rag(self, data_files: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """
        Formate les données pour l'ingestion dans le RAG.
        
        Args:
            data_files: Dictionnaire des chemins de fichiers par source
            
        Returns:
            List[Dict[str, Any]]: Documents formatés pour le RAG
        """
        rag_documents = []
        
        # Traiter les fichiers Amboss
        for file_path in data_files["amboss"]:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                    # Créer un document pour chaque nœud
                    for pubkey, node_data in data.items():
                        doc = {
                            "title": f"Amboss Data - {pubkey}",
                            "content": json.dumps(node_data, indent=2),
                            "metadata": {
                                "source": "amboss",
                                "pubkey": pubkey,
                                "timestamp": datetime.now().isoformat(),
                                "original_file": os.path.basename(file_path)
                            }
                        }
                        rag_documents.append(doc)
            except Exception as e:
                logger.error(f"Erreur lors du traitement du fichier Amboss {file_path}: {str(e)}")
        
        # Traiter les fichiers LNRouter
        for file_path in data_files["lnrouter"]:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                    # Créer un document pour chaque nœud
                    for pubkey, node_data in data.items():
                        doc = {
                            "title": f"LNRouter Topology - {pubkey}",
                            "content": json.dumps(node_data, indent=2),
                            "metadata": {
                                "source": "lnrouter",
                                "pubkey": pubkey,
                                "timestamp": datetime.now().isoformat(),
                                "original_file": os.path.basename(file_path)
                            }
                        }
                        rag_documents.append(doc)
            except Exception as e:
                logger.error(f"Erreur lors du traitement du fichier LNRouter {file_path}: {str(e)}")
        
        # Traiter les fichiers de métriques
        for file_path in data_files["metrics"]:
            try:
                with open(file_path, 'r') as f:
                    metrics = json.load(f)
                    
                    # Créer un document résumé avec toutes les métriques
                    doc = {
                        "title": "Node Reliability Metrics",
                        "content": f"""
Métriques de fiabilité des nœuds Lightning Network:
{json.dumps(metrics, indent=2)}

Ces métriques combinent les données d'Amboss et LNRouter pour fournir un score de fiabilité composite
pour chaque nœud, ce qui permet d'optimiser les décisions de routage et la gestion des canaux.
                        """.strip(),
                        "metadata": {
                            "source": "metrics",
                            "timestamp": datetime.now().isoformat(),
                            "original_file": os.path.basename(file_path)
                        }
                    }
                    rag_documents.append(doc)
                    
                    # Créer un document pour chaque nœud
                    for pubkey, node_metrics in metrics.items():
                        doc = {
                            "title": f"Node Metrics - {pubkey}",
                            "content": json.dumps(node_metrics, indent=2),
                            "metadata": {
                                "source": "metrics",
                                "pubkey": pubkey,
                                "timestamp": datetime.now().isoformat(),
                                "original_file": os.path.basename(file_path)
                            }
                        }
                        rag_documents.append(doc)
            except Exception as e:
                logger.error(f"Erreur lors du traitement du fichier de métriques {file_path}: {str(e)}")
        
        return rag_documents
    
    async def save_documents_for_rag(self, documents: List[Dict[str, Any]]) -> bool:
        """
        Sauvegarde les documents formatés pour l'ingestion RAG.
        
        Args:
            documents: Liste des documents formatés
            
        Returns:
            bool: True si la sauvegarde a réussi
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{self.rag_assets_dir}/external_data_{timestamp}.json"
            
            with open(output_file, 'w') as f:
                json.dump(documents, f, indent=2)
                
            logger.info(f"Documents RAG sauvegardés dans {output_file} ({len(documents)} documents)")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des documents RAG: {str(e)}")
            return False
    
    async def run(self):
        """Exécute le processus d'ingestion complet."""
        try:
            # Collecte des fichiers de données
            data_files = await self.collect_latest_data_files()
            
            # Formatage des données pour le RAG
            rag_documents = await self.format_data_for_rag(data_files)
            
            # Sauvegarde des documents
            if rag_documents:
                await self.save_documents_for_rag(rag_documents)
                logger.info(f"Ingestion réussie: {len(rag_documents)} documents préparés pour le RAG")
            else:
                logger.warning("Aucun document généré pour l'ingestion RAG")
        except Exception as e:
            logger.error(f"Erreur lors de l'ingestion des données externes: {str(e)}")

async def main():
    """Fonction principale."""
    # Création du répertoire de logs s'il n'existe pas
    os.makedirs("logs", exist_ok=True)
    
    logger.info("Démarrage de l'ingestion des données externes pour le RAG")
    
    ingestor = ExternalDataIngestor()
    await ingestor.run()
    
    logger.info("Processus d'ingestion terminé")

if __name__ == "__main__":
    asyncio.run(main()) 