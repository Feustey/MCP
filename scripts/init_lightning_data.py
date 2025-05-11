#!/usr/bin/env python3
# scripts/init_lightning_data.py

import asyncio
import json
import logging
import os
import random
from datetime import datetime, timedelta

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

# Configuration MongoDB
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "daznode")

# Collections
NODES_COLLECTION = "lightning_nodes"
CHANNELS_COLLECTION = "lightning_channels"

# Fonction pour générer une clé publique hexadécimale aléatoire
def generate_pubkey():
    return ''.join(random.choice('0123456789abcdef') for _ in range(66))

# Fonction pour générer des nœuds Lightning aléatoires
def generate_nodes(count=30):
    nodes = []
    colors = ["#3399ff", "#cc0000", "#00cc00", "#ff9900", "#9900cc", "#ff66cc", "#00cccc"]
    aliases = ["Alice", "Bob", "Charlie", "Dave", "Eve", "Frank", "Grace", "Heidi", 
               "Ivan", "Judy", "Mallory", "Niaj", "Oscar", "Peggy", "Rupert", "Sybil",
               "Trent", "Umay", "Victor", "Walter", "Xavier", "Yasmine", "Zara"]
    
    # Completer la liste d'alias si nécessaire
    while len(aliases) < count:
        aliases.append(f"Node{len(aliases)+1}")
    
    for i in range(count):
        node = {
            "public_key": generate_pubkey(),
            "alias": aliases[i],
            "color": random.choice(colors),
            "last_update": datetime.utcnow() - timedelta(days=random.randint(0, 30)),
            "features": [
                {"name": "option_static_remote_key", "is_required": True, "is_supported": True},
                {"name": "option_anchor_outputs", "is_required": False, "is_supported": random.choice([True, False])},
                {"name": "option_upfront_shutdown_script", "is_required": False, "is_supported": random.choice([True, False])}
            ],
            "addresses": [
                {"network": "tcp", "addr": f"192.168.1.{random.randint(2, 254)}:9735"},
                {"network": "tor", "addr": f"{generate_pubkey()[:16]}.onion:9735"} if random.random() > 0.3 else None
            ]
        }
        # Supprimer les adresses None
        node["addresses"] = [addr for addr in node["addresses"] if addr]
        nodes.append(node)
    
    return nodes

# Fonction pour générer des canaux aléatoires entre les nœuds
def generate_channels(nodes, avg_channels_per_node=5):
    channels = []
    node_keys = [node["public_key"] for node in nodes]
    
    # Assurer un minimum de connexions pour chaque nœud
    for i, node1_pub in enumerate(node_keys):
        # Créer au moins un canal pour chaque nœud
        for _ in range(random.randint(1, avg_channels_per_node * 2)):
            # Choisir un autre nœud au hasard
            node2_pub = random.choice([n for n in node_keys if n != node1_pub])
            
            # Vérifier si le canal existe déjà
            existing = any(
                (ch["node1_pub"] == node1_pub and ch["node2_pub"] == node2_pub) or
                (ch["node1_pub"] == node2_pub and ch["node2_pub"] == node1_pub)
                for ch in channels
            )
            
            if not existing:
                channel = {
                    "id": f"{random.randint(100000, 999999)}:{random.randint(0, 5)}:{random.randint(0, 5)}",
                    "node1_pub": node1_pub,
                    "node2_pub": node2_pub,
                    "capacity": random.randint(1000000, 50000000),  # 0.01 à 0.5 BTC en sats
                    "last_update": datetime.utcnow() - timedelta(days=random.randint(0, 30)),
                    "status": random.choices(["active", "inactive"], weights=[0.9, 0.1])[0],
                    "fee_rate": random.uniform(0, 10)  # ppm
                }
                channels.append(channel)
    
    return channels

# Fonction principale asynchrone
async def main():
    try:
        # Se connecter à MongoDB
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[MONGO_DB]
        
        # Vérifier si les collections existent déjà et les supprimer
        collections = await db.list_collection_names()
        if NODES_COLLECTION in collections:
            await db[NODES_COLLECTION].drop()
        if CHANNELS_COLLECTION in collections:
            await db[CHANNELS_COLLECTION].drop()
        
        # Générer des données aléatoires
        nodes = generate_nodes(50)  # 50 nœuds
        channels = generate_channels(nodes, 8)  # ~8 canaux par nœud en moyenne
        
        # Insérer les données
        if nodes:
            await db[NODES_COLLECTION].insert_many(nodes)
            logger.info(f"Inséré {len(nodes)} nœuds dans {NODES_COLLECTION}")
        
        if channels:
            await db[CHANNELS_COLLECTION].insert_many(channels)
            logger.info(f"Inséré {len(channels)} canaux dans {CHANNELS_COLLECTION}")
        
        # Créer les indices
        await db[NODES_COLLECTION].create_index("public_key", unique=True)
        await db[CHANNELS_COLLECTION].create_index("id", unique=True)
        await db[CHANNELS_COLLECTION].create_index("node1_pub")
        await db[CHANNELS_COLLECTION].create_index("node2_pub")
        
        logger.info("Initialisation des données Lightning terminée avec succès")
    
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation des données: {e}")
    finally:
        # Fermer la connexion
        client.close()

# Point d'entrée pour exécuter le script
if __name__ == "__main__":
    logger.info("Démarrage de l'initialisation des données Lightning")
    asyncio.run(main()) 