#!/usr/bin/env python3
import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Optional, List

import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SparkSeerMetrics:
    """Structure des métriques Sparkseer"""
    def __init__(self, data: dict):
        self.timestamp = datetime.utcnow()
        self.node_info = {
            "pubkey": data.get("pubkey", ""),
            "alias": data.get("alias", ""),
            "total_capacity": data.get("total_capacity", 0),
            "num_channels": data.get("num_channels", 0),
        }
        
        self.channel_metrics = {
            "avg_capacity": data.get("avg_channel_capacity", 0),
            "median_capacity": data.get("median_channel_capacity", 0),
        }
        
        self.fee_metrics = {
            "outbound": {
                "mean_base": data.get("mean_outbound_base_fee", 0),
                "median_base": data.get("median_outbound_base_fee", 0),
                "mean_rate": data.get("mean_outbound_fee_rate", 0),
                "median_rate": data.get("median_outbound_fee_rate", 0),
            },
            "inbound": {
                "mean_base": data.get("mean_inbound_base_fee", 0),
                "median_base": data.get("median_inbound_base_fee", 0),
                "mean_rate": data.get("mean_inbound_fee_rate", 0),
                "median_rate": data.get("median_inbound_fee_rate", 0),
            }
        }
        
        self.liquidity_metrics = {
            "flexibility_score": data.get("liquidity_flexibility_score", 0),
            "effective_outbound": data.get("effective_outbound_balance", 0),
            "effective_inbound": data.get("effective_inbound_balance", 0),
        }
        
        self.network_metrics = {
            "htlc_response_time": data.get("mean_htlc_response_time", 0),
            "ranks": {
                "betweenness": {
                    "rank": data.get("betweenness_rank", 0),
                    "weighted_rank": data.get("weighted_betweenness_rank", 0)
                },
                "closeness": {
                    "rank": data.get("closeness_rank", 0),
                    "weighted_rank": data.get("weighted_closeness_rank", 0)
                },
                "hubness": {
                    "rank": data.get("hubness_rank", 0),
                    "weighted_rank": data.get("weighted_hubness_rank", 0)
                }
            }
        }
        
        self.peer_metrics = {
            "shared_peers": data.get("shared_peers", []),
            "local_network": data.get("local_network", {}),
            "triangles": data.get("triangles", [])
        }

    def to_dict(self) -> dict:
        """Convertit les métriques en dictionnaire pour stockage"""
        return {
            "timestamp": self.timestamp,
            "node_info": self.node_info,
            "channel_metrics": self.channel_metrics,
            "fee_metrics": self.fee_metrics,
            "liquidity_metrics": self.liquidity_metrics,
            "network_metrics": self.network_metrics,
            "peer_metrics": self.peer_metrics
        }

class NodeAnalyzer:
    def __init__(self):
        self.mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
        self.db_name = os.getenv('MONGODB_DB_NAME', 'dazlng')
        self.client = AsyncIOMotorClient(self.mongodb_uri)
        self.db = self.client[self.db_name]
        
    async def get_node_data_from_sparkseer(self, session: aiohttp.ClientSession, node_id: str) -> dict:
        """Récupère les données complètes depuis l'API Sparkseer"""
        api_key = os.getenv("SPARKSEER_API_KEY")
        if not api_key:
            raise ValueError("SPARKSEER_API_KEY non définie dans les variables d'environnement")
            
        url = f"https://api.sparkseer.space/v1/nodes/{node_id}"
        headers = {'Authorization': f'Bearer {api_key}'}
        
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                raise Exception(f"Erreur API Sparkseer: {response.status}")
            return await response.json()

    async def store_metrics(self, node_id: str, metrics: SparkSeerMetrics):
        """Stocke les métriques dans MongoDB"""
        collection = self.db.node_metrics
        document = metrics.to_dict()
        document['node_id'] = node_id
        await collection.insert_one(document)
        
        # Stockage des métriques agrégées pour l'historique
        agg_collection = self.db.node_metrics_history
        agg_data = {
            "node_id": node_id,
            "timestamp": metrics.timestamp,
            "total_capacity": metrics.node_info["total_capacity"],
            "num_channels": metrics.node_info["num_channels"],
            "liquidity_score": metrics.liquidity_metrics["flexibility_score"],
            "effective_outbound": metrics.liquidity_metrics["effective_outbound"],
            "effective_inbound": metrics.liquidity_metrics["effective_inbound"]
        }
        await agg_collection.insert_one(agg_data)

    async def get_historical_metrics(self, node_id: str, limit: int = 30) -> List[dict]:
        """Récupère l'historique des métriques"""
        collection = self.db.node_metrics_history
        cursor = collection.find(
            {'node_id': node_id},
            {'_id': 0}
        ).sort('timestamp', -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_latest_metrics(self, node_id: str) -> Optional[dict]:
        """Récupère les dernières métriques complètes"""
        collection = self.db.node_metrics
        return await collection.find_one(
            {'node_id': node_id},
            {'_id': 0},
            sort=[('timestamp', -1)]
        )

async def main():
    analyzer = NodeAnalyzer()
    node_id = "02aced13b08adcbe1e0897ad3b26e4525e1a9cdb76c86ed4aa42a518045bcb7e9f"
    
    async with aiohttp.ClientSession() as session:
        try:
            # Récupération des données Sparkseer
            raw_data = await analyzer.get_node_data_from_sparkseer(session, node_id)
            
            # Conversion en métriques structurées
            metrics = SparkSeerMetrics(raw_data)
            
            # Stockage des métriques
            await analyzer.store_metrics(node_id, metrics)
            
            # Récupération de l'historique
            history = await analyzer.get_historical_metrics(node_id)
            
            print("\n=== MÉTRIQUES DU NŒUD STOCKÉES ===")
            print(json.dumps(metrics.to_dict(), indent=2, ensure_ascii=False))
            
            print("\n=== HISTORIQUE DES MÉTRIQUES ===")
            print(json.dumps(history, indent=2, ensure_ascii=False))
            
        except Exception as e:
            print(f"Erreur: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 