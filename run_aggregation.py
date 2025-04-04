import asyncio
import logging
from data_aggregator import DataAggregator
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    try:
        logger.info("Démarrage de l'agrégation des données et génération des recommandations...")
        start_time = datetime.now()
        
        # Initialisation de l'agrégateur
        aggregator = DataAggregator()
        await aggregator.initialize()
        
        # Exécution de l'agrégation
        await aggregator.aggregate_data()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Agrégation terminée en {duration:.2f} secondes")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'agrégation : {str(e)}")
        raise
    finally:
        # Fermeture des connexions
        if 'aggregator' in locals() and aggregator.mongo_ops:
            await aggregator.mongo_ops.close()

if __name__ == "__main__":
    asyncio.run(main()) 