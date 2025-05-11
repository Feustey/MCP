#!/usr/bin/env python3
import asyncio
import argparse
import logging
import os
from dotenv import load_dotenv
from rag.rag import RAGWorkflow

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def init_rag_system(data_dir, debug=False):
    """Initialise le système RAG avec chunking sémantique."""
    try:
        logger.info(f"Initialisation du système RAG avec les données de {data_dir}")
        
        # Créer une instance du RAGWorkflow
        rag = RAGWorkflow()
        
        # Activer le mode debug si demandé
        if debug:
            rag.debug_mode = True
            logger.info("Mode debug activé")
        
        # Ingérer les documents
        result = await rag.ingest_documents(data_dir)
        
        logger.info(f"Ingestion terminée: {result['documents_processed']} documents traités, "
                   f"{result['chunks_created']} chunks créés en {result['processing_time']:.2f} secondes")
        
        if result['errors'] > 0:
            logger.warning(f"{result['errors']} erreurs lors de l'ingestion")
        
        # Test simple avec une requête
        if debug:
            logger.info("Test du système RAG avec une requête simple...")
            query = "Quelles sont les recommandations pour optimiser les frais du nœud Feustey?"
            response = await rag.query(query)
            logger.info(f"Requête: {query}")
            logger.info(f"Réponse: {response[:300]}...")
        
        logger.info("Système RAG initialisé avec succès")
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du système RAG: {str(e)}")
        return False

def main():
    # Charger les variables d'environnement
    load_dotenv()
    
    # Parser les arguments de ligne de commande
    parser = argparse.ArgumentParser(description="Initialisation du système RAG avec chunking sémantique")
    parser.add_argument('--data-dir', type=str, default='data/scrapping', 
                        help='Répertoire contenant les données à ingérer')
    parser.add_argument('--debug', action='store_true', 
                        help='Activer le mode debug')
    args = parser.parse_args()
    
    # Vérifier que le répertoire existe
    if not os.path.isdir(args.data_dir):
        logger.error(f"Le répertoire {args.data_dir} n'existe pas")
        return 1
    
    # Exécuter l'initialisation
    success = asyncio.run(init_rag_system(args.data_dir, args.debug))
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main()) 