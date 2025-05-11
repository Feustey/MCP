import sys
import os
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import asyncio
from src.data_aggregator import DataAggregator
# Commenté car nécessite redis_ops
# from src.amboss_scraper import AmbossScraper 
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    start_time = datetime.now()
    logger.info("Début de l'agrégation des données")

    try:
        # Agrégation des données Sparkseer et LNBits
        logger.info("Début de l'agrégation des données Sparkseer et LNBits")
        aggregator = DataAggregator()
        await aggregator.aggregate_data()
        logger.info("Fin de l'agrégation des données Sparkseer et LNBits")

        # Partie Amboss commentée car elle nécessite redis_ops
        """
        # Scraping des données Amboss
        logger.info("Début du scraping des données Amboss")
        scraper = AmbossScraper()
        node_ids = [
            "02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619",
            "03abf6f44c355dec0d5aa155bdbdd6e0c8fefe579eff5b380f9f1441e882f8582b"
        ]
        channel_ids = [
            "1234567890abcdef",
            "0987654321fedcba"
        ]
        await scraper.scrape_data(node_ids, channel_ids)
        logger.info("Fin du scraping des données Amboss")
        """
        logger.info("Partie Amboss désactivée car elle nécessite redis_ops")

    except Exception as e:
        logger.error(f"Erreur lors de l'agrégation des données: {str(e)}")
        raise

    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"Fin de l'agrégation des données. Durée: {duration}")

if __name__ == "__main__":
    asyncio.run(main()) 