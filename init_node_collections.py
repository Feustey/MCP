import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os
import logging
from models import NodeData, NodePerformance, SecurityMetrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NODE_ID = "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"

async def init_collections():
    mongo_url = os.getenv("DATABASE_URL", "mongodb+srv://feustey:VwSrcnNI8i5m2sim@dazlng.ug0aiaw.mongodb.net/?retryWrites=true&w=majority&appName=DazLng")
    client = AsyncIOMotorClient(mongo_url)
    db = client.dazlng
    
    try:
        # Nettoyage des collections existantes
        await db.nodes.delete_many({})
        await db.node_performance.delete_many({})
        await db.security_metrics.delete_many({})
        logger.info("🗑️ Collections nettoyées")
        
        # Création des index
        await db.nodes.create_index("node_id", unique=True)
        await db.node_performance.create_index("node_id", unique=True)
        await db.security_metrics.create_index("node_id", unique=True)
        logger.info("✅ Index créés")
        
        # Création des données du nœud
        node_data = NodeData(
            node_id=NODE_ID,
            alias="DazLng Node",
            capacity=1000000,  # 1M sats
            channel_count=3,
            last_update=datetime.now(),
            reputation_score=0.85,
            metadata={
                "network": "mainnet",
                "implementation": "lnd",
                "version": "0.16.4"
            }
        )
        
        # Création des données de performance
        performance_data = NodePerformance(
            node_id=NODE_ID,
            uptime=99.5,
            transaction_count=150,
            average_processing_time=0.5,
            last_update=datetime.now(),
            metadata={
                "cpu_usage": 45,
                "memory_usage": 60,
                "disk_usage": 55
            }
        )
        
        # Création des données de sécurité
        security_data = SecurityMetrics(
            node_id=NODE_ID,
            risk_score=0.15,
            suspicious_activity=[],
            last_update=datetime.now(),
            metadata={
                "tor_node": True,
                "watchtower_enabled": True,
                "channel_backup_enabled": True
            }
        )
        
        # Insertion des données
        await db.nodes.insert_one(node_data.model_dump())
        logger.info("✅ Données du nœud insérées")
        
        await db.node_performance.insert_one(performance_data.model_dump())
        logger.info("✅ Données de performance insérées")
        
        await db.security_metrics.insert_one(security_data.model_dump())
        logger.info("✅ Données de sécurité insérées")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation des collections: {str(e)}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(init_collections()) 