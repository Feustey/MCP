import asyncio
import aiohttp
from datetime import datetime
from mongo_operations import MongoOperations
from models import Recommendation, NodeData, NodePerformance, SecurityMetrics
import os
from typing import Dict, List, Tuple
import json

NODE_ID = "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"

def calculate_channel_score(node: Dict) -> float:
    """Calcule un score heuristique pour un nœud potentiel"""
    score = 0.0
    
    # Facteurs de score
    uptime_weight = 0.3
    capacity_weight = 0.25
    age_weight = 0.2
    fee_weight = 0.15
    connectivity_weight = 0.1
    
    # Calcul des composants du score
    uptime = node.get("uptime", 0)
    capacity = node.get("capacity", 0)
    age = node.get("age", 0)
    fee_rate = node.get("fee_rate", {}).get("base_fee", 1000)
    channel_count = node.get("channel_count", 0)
    
    # Normalisation et calcul du score
    score += (uptime / 100.0) * uptime_weight
    score += min(capacity / 10000000, 1.0) * capacity_weight  # Normalise par rapport à 10M sats
    score += min(age / 365, 1.0) * age_weight  # Normalise par rapport à 1 an
    score += (1 - min(fee_rate / 1000, 1.0)) * fee_weight  # Inverse pour que les frais bas donnent un meilleur score
    score += min(channel_count / 100, 1.0) * connectivity_weight
    
    return score

async def get_potential_channels(mongo: MongoOperations) -> List[Dict]:
    """Récupère et évalue les nœuds potentiels pour de nouveaux canaux"""
    nodes = await mongo.db.nodes.find({
        "node_id": {"$ne": NODE_ID},  # Exclut notre propre nœud
        "status": "active"
    }).to_list(length=None)
    
    scored_nodes = []
    for node in nodes:
        score = calculate_channel_score(node)
        node["heuristic_score"] = score
        scored_nodes.append(node)
    
    # Trie par score décroissant
    return sorted(scored_nodes, key=lambda x: x["heuristic_score"], reverse=True)

async def analyze_node_data(mongo: MongoOperations, node_data: NodeData) -> List[Dict]:
    """Analyse les données et génère des recommandations basées sur des heuristiques"""
    recommendations = []
    
    # Analyse du nombre de canaux
    if node_data.channel_count < 15:
        # Récupère les meilleurs nœuds potentiels
        potential_nodes = await get_potential_channels(mongo)
        top_nodes = potential_nodes[:5]  # Top 5 des meilleurs nœuds
        
        node_suggestions = [
            {
                "node_id": node["node_id"],
                "alias": node.get("alias", "Unknown"),
                "score": node["heuristic_score"],
                "capacity": node.get("capacity", 0),
                "fee_rate": node.get("fee_rate", {})
            }
            for node in top_nodes
        ]
        
        recommendations.append({
            "content": f"Nombre de canaux insuffisant ({node_data.channel_count}/15 minimum recommandé). "
                      f"Voici les 5 meilleurs nœuds potentiels pour ouvrir de nouveaux canaux :\n" +
                      "\n".join([
                          f"- {node['alias']} (score: {node['score']:.2f}, capacité: {node['capacity']} sats)"
                          for node in node_suggestions
                      ]),
            "context": {
                "metric": "channel_count",
                "current_value": node_data.channel_count,
                "threshold": 15,
                "potential_nodes": node_suggestions
            },
            "confidence_score": 0.95
        })
    
    # Analyse de la répartition de la liquidité
    total_capacity = node_data.capacity
    avg_channel_capacity = total_capacity / max(node_data.channel_count, 1)
    
    if avg_channel_capacity < 500000:  # Moins de 500k sats par canal en moyenne
        recommendations.append({
            "content": f"Capacité moyenne par canal faible ({avg_channel_capacity:.0f} sats). "
                      "Considérez d'augmenter la capacité de vos canaux pour améliorer l'efficacité du routage.",
            "context": {
                "metric": "avg_channel_capacity",
                "current_value": avg_channel_capacity,
                "threshold": 500000,
                "total_capacity": total_capacity
            },
            "confidence_score": 0.9
        })
    
    # Récupération des performances
    perf = await mongo.get_node_performance(NODE_ID)
    if perf:
        success_rate = perf.transaction_success_rate if hasattr(perf, 'transaction_success_rate') else 0
        if success_rate < 0.95:  # Moins de 95% de succès
            recommendations.append({
                "content": f"Taux de succès des transactions bas ({success_rate*100:.1f}%). "
                          "Optimisez vos paramètres de routage et la répartition de votre liquidité.",
                "context": {
                    "metric": "transaction_success_rate",
                    "current_value": success_rate,
                    "threshold": 0.95
                },
                "confidence_score": 0.85
            })
    
    return recommendations

async def main():
    try:
        # Initialisation de la connexion MongoDB
        mongo = MongoOperations()
        
        # Récupération des données du nœud
        print("Récupération des données réelles du nœud...")
        node_data = await mongo.get_node_data(NODE_ID)
        if not node_data:
            raise Exception(f"Aucune donnée trouvée pour le nœud {NODE_ID}")
        
        # Génération des recommandations
        print("Analyse des données et génération des recommandations...")
        recommendations = await analyze_node_data(mongo, node_data)
        
        # Sauvegarde des recommandations
        print("Sauvegarde des recommandations...")
        for rec in recommendations:
            recommendation = Recommendation(
                node_id=NODE_ID,
                content=rec["content"],
                context=rec["context"],
                confidence_score=rec["confidence_score"],
                status="active",
                created_at=datetime.now(),
                source="RAG System",
                metadata={
                    "analysis_timestamp": datetime.now().isoformat(),
                    "data_source": "mongodb_live",
                    "heuristic_version": "1.0"
                }
            )
            await mongo.save_recommendation(recommendation)
        
        print(f"✅ {len(recommendations)} recommandations générées et sauvegardées avec succès!")
        
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 