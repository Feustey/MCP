#!/usr/bin/env python3
"""
Script de rafraîchissement de l'index unifié du système RAG.
Ce script est conçu pour être exécuté régulièrement (par exemple, via cron)
afin de maintenir l'index unifié à jour avec les dernières données.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# Ajout du répertoire parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.enhanced_rag import EnhancedRAGWorkflow
from src.redis_operations import RedisOperations

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/refresh_index.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("refresh_index")

async def refresh_index():
    """Rafraîchit l'index unifié"""
    try:
        # Initialisation du Redis si disponible
        redis_ops = None
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            redis_ops = RedisOperations(redis_url)
        
        # Initialisation du RAG amélioré
        rag = EnhancedRAGWorkflow(redis_ops=redis_ops)
        await rag.initialize()
        
        # Rafraîchissement de l'index
        logger.info("Rafraîchissement de l'index unifié...")
        start_time = datetime.now()
        
        result = await rag.refresh_unified_index()
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Rafraîchissement terminé en {duration:.2f} secondes")
        
        if not result:
            logger.error("Échec du rafraîchissement de l'index")
            return False
            
        # Invalidation du cache pour forcer l'utilisation des nouvelles données
        if redis_ops:
            logger.info("Invalidation du cache pour les réponses enrichies...")
            await redis_ops.redis.delete("enhanced_responses")
            logger.info("Cache invalidé")
        
        logger.info("Opération terminée avec succès")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors du rafraîchissement de l'index: {str(e)}")
        return False
    finally:
        # Fermeture des connexions
        if 'rag' in locals():
            await rag.close()

async def main():
    """Fonction principale"""
    logger.info("Démarrage du rafraîchissement de l'index unifié...")
    success = await refresh_index()
    if success:
        logger.info("✓ Opération réussie")
        sys.exit(0)
    else:
        logger.error("✗ Opération échouée")
        sys.exit(1)

if __name__ == "__main__":
    # Exécution du rafraîchissement
    asyncio.run(main()) 