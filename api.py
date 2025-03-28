from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from server import mcp
import asyncio
import json
from typing import Optional

app = FastAPI(
    title="MCP Lightning Node Optimizer API",
    description="API pour l'optimisation des nœuds Lightning via Sparkseer et OpenAI",
    version="1.0.0"
)

class NodeRequest(BaseModel):
    pubkey: str
    additional_params: Optional[dict] = None

class OptimizationResponse(BaseModel):
    performance_metrics: dict
    immediate_actions: list
    long_term_strategy: dict

class SparkseerDataResponse(BaseModel):
    node_stats: dict
    node_history: dict
    network_summary: dict
    centralities: dict
    recommendations: dict

@app.get("/sparkseer-data/{pubkey}", response_model=SparkseerDataResponse)
async def get_sparkseer_data(pubkey: str):
    """
    Récupère toutes les données brutes de Sparkseer pour un nœud donné.
    
    Args:
        pubkey: La clé publique du nœud Lightning
    
    Returns:
        SparkseerDataResponse: Contient toutes les données brutes de Sparkseer
    """
    try:
        # Récupération des données du nœud via Sparkseer
        node_stats = await mcp.get_node_stats(pubkey)
        node_history = await mcp.get_node_history(pubkey)
        
        # Récupération des données réseau
        network_summary = await mcp.get_network_summary()
        centralities = await mcp.get_centralities()
        
        # Récupération des recommandations
        channel_recommendations = await mcp.get_channel_recommendations()
        liquidity_value = await mcp.get_outbound_liquidity_value()
        suggested_fees = await mcp.get_suggested_fees()
        
        # Préparation de la réponse
        response = SparkseerDataResponse(
            node_stats=node_stats,
            node_history=node_history,
            network_summary=network_summary,
            centralities=centralities,
            recommendations={
                "channels": channel_recommendations,
                "liquidity": liquidity_value,
                "fees": suggested_fees
            }
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimize-node", response_model=OptimizationResponse)
async def optimize_node(request: NodeRequest):
    """
    Optimise un nœud Lightning en utilisant les données de Sparkseer et OpenAI.
    
    Args:
        request: Contient le pubkey du nœud et des paramètres additionnels optionnels
    
    Returns:
        OptimisationResponse: Contient les recommandations d'optimisation
    """
    try:
        # Récupération des données du nœud via Sparkseer
        node_stats = await mcp.get_node_stats(request.pubkey)
        node_history = await mcp.get_node_history(request.pubkey)
        
        # Récupération des données réseau
        network_summary = await mcp.get_network_summary()
        centralities = await mcp.get_centralities()
        
        # Récupération des recommandations
        channel_recommendations = await mcp.get_channel_recommendations()
        liquidity_value = await mcp.get_outbound_liquidity_value()
        suggested_fees = await mcp.get_suggested_fees()
        
        # Préparation des données pour OpenAI
        analysis_data = {
            "node_stats": node_stats,
            "node_history": node_history,
            "network_summary": network_summary,
            "centralities": centralities,
            "recommendations": {
                "channels": channel_recommendations,
                "liquidity": liquidity_value,
                "fees": suggested_fees
            }
        }
        
        # Utilisation du prompt OpenAI pour l'analyse
        rag_result = await mcp.rag(json.dumps(analysis_data))
        
        # Traitement et structuration de la réponse
        response = OptimizationResponse(
            performance_metrics=rag_result.get("performance_metrics", {}),
            immediate_actions=rag_result.get("immediate_actions", []),
            long_term_strategy=rag_result.get("long_term_strategy", {})
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    Vérifie l'état de l'API
    """
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 