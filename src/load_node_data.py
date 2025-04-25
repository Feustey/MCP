import asyncio
import os
import requests
from dotenv import load_dotenv
from src.redis_operations import RedisOperations
from src.models import NodeData, ChannelData
from datetime import datetime

# Chargement des variables d'environnement
load_dotenv(".env.local")

async def fetch_node_channels(node_pubkey: str) -> list:
    """Récupère tous les canaux d'un nœud depuis l'API 1ML"""
    try:
        # URL de l'API 1ML pour récupérer les canaux d'un nœud
        url = f"https://1ml.com/node/{node_pubkey}/json"
        response = requests.get(url)
        data = response.json()
        
        channels = []
        for channel in data.get("channels", []):
            # Création d'un identifiant unique pour le canal
            channel_id = channel.get("channel_id", "0" * 64)
            
            # Récupération des statistiques de routage depuis l'API
            routing_url = f"https://1ml.com/channel/{channel_id}/json"
            routing_response = requests.get(routing_url)
            routing_data = routing_response.json()
            
            # Calcul des métriques de performance
            total_attempts = routing_data.get("total_attempts", 0)
            successful_routes = routing_data.get("successful_routes", 0)
            total_latency = routing_data.get("total_latency", 0.0)
            
            # Calcul des scores de performance
            reliability_score = successful_routes / total_attempts if total_attempts > 0 else 1.0
            efficiency_score = 1.0 - (total_latency / (total_attempts * 1000)) if total_attempts > 0 else 1.0
            
            # Création de l'objet ChannelData
            channel_data = ChannelData(
                channel_id=channel_id,
                node1_pubkey=node_pubkey,
                node2_pubkey=channel.get("remote_pubkey", ""),
                capacity=channel.get("capacity", 0),
                fee_rate={
                    "base_fee": channel.get("base_fee", 0),
                    "fee_rate": channel.get("fee_rate", 0),
                    "min_htlc": channel.get("min_htlc", 1000),
                    "max_htlc": channel.get("max_htlc", 1000000),
                    "local": channel.get("local_fee_rate", 0),
                    "remote": channel.get("remote_fee_rate", 0)
                },
                last_updated=datetime.now(),
                status=channel.get("status", "active"),
                balance={
                    "local": channel.get("local_balance", 0),
                    "remote": channel.get("remote_balance", 0)
                },
                routing_stats={
                    "total_attempts": total_attempts,
                    "successful_routes": successful_routes,
                    "total_latency": total_latency,
                    "last_30_days": routing_data.get("last_30_days", {
                        "attempts": 0,
                        "successes": 0,
                        "avg_latency": 0.0
                    }),
                    "last_7_days": routing_data.get("last_7_days", {
                        "attempts": 0,
                        "successes": 0,
                        "avg_latency": 0.0
                    })
                },
                performance_metrics={
                    "uptime": channel.get("uptime", 1.0),
                    "reliability_score": reliability_score,
                    "efficiency_score": efficiency_score,
                    "last_performance_update": datetime.now()
                }
            )
            channels.append(channel_data)
            
        return channels
        
    except Exception as e:
        print(f"Erreur lors de la récupération des canaux : {str(e)}")
        return []

async def load_test_data():
    """Charge des données de test dans Redis"""
    try:
        # Initialisation de Redis
        redis_ops = RedisOperations(redis_url=os.getenv("REDIS_URL"))
        
        # Clé publique du nœud à analyser
        node_pubkey = "02aced13b08adcbe1e0897ad3b26e4525e1a9cdb76c86ed4aa42a518045bcb7e9f"
        
        # Récupération de tous les canaux du nœud
        channels = await fetch_node_channels(node_pubkey)
        
        if not channels:
            print("Aucun canal trouvé pour le nœud")
            return
            
        # Création des données du nœud avec les vraies données
        node = NodeData(
            node_id=node_pubkey,
            pubkey=node_pubkey,
            alias="w4ge",
            capacity=sum(channel.capacity for channel in channels),
            channels=len(channels),
            first_seen=datetime.now(),
            last_updated=datetime.now(),
            metadata={
                "platform": "LND",
                "version": "0.15.5-beta"
            }
        )
        
        # Sauvegarde des données dans Redis
        await redis_ops.cache_node_data(node)
        for channel in channels:
            await redis_ops.cache_channel_data(channel)
            
        print(f"Données chargées avec succès dans Redis : {len(channels)} canaux")
        
    except Exception as e:
        print(f"Erreur lors du chargement des données : {str(e)}")
        
if __name__ == "__main__":
    asyncio.run(load_test_data()) 