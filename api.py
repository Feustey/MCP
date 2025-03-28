from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
import asyncio
import json
from typing import Optional
from datetime import datetime
from server import app as server_app

app = FastAPI(
    title="MCP Lightning Node Optimizer API",
    description="API pour l'optimisation des nœuds Lightning via Sparkseer et OpenAI",
    version="1.0.0"
)

# Compteur d'appels
call_counter = {
    "total_calls": 0,
    "last_call": None,
    "sparkseer_calls": 0,
    "optimize_calls": 0
}

# Template HTML pour la page d'accueil
HOME_PAGE_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Lightning Node Optimizer</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
        }
        .status-section {
            margin: 20px 0;
            padding: 15px;
            border-radius: 5px;
        }
        .healthy {
            background-color: #d4edda;
            color: #155724;
        }
        .unhealthy {
            background-color: #f8d7da;
            color: #721c24;
        }
        .stats {
            background-color: #e9ecef;
            padding: 15px;
            border-radius: 5px;
            margin-top: 20px;
        }
        .stats h2 {
            color: #2c3e50;
            margin-top: 0;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .stat-item {
            background-color: white;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }
        .stat-label {
            color: #6c757d;
            font-size: 14px;
        }
        .api-docs {
            margin-top: 30px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .api-docs h2 {
            color: #2c3e50;
            margin-top: 0;
        }
        .endpoint {
            background-color: white;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid #2c3e50;
        }
        .endpoint h3 {
            margin: 0 0 10px 0;
            color: #2c3e50;
        }
        .endpoint pre {
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 3px;
            overflow-x: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>MCP Lightning Node Optimizer</h1>
        
        <div class="status-section {health_status_class}">
            <h2>État de l'Application</h2>
            <p>Status: {health_status}</p>
            <p>Version: {version}</p>
        </div>

        <div class="status-section {sparkseer_status_class}">
            <h2>État de l'API Sparkseer</h2>
            <p>Status: {sparkseer_status}</p>
        </div>

        <div class="stats">
            <h2>Statistiques d'Utilisation</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">{total_calls}</div>
                    <div class="stat-label">Appels Totaux</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{sparkseer_calls}</div>
                    <div class="stat-label">Appels Sparkseer</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{optimize_calls}</div>
                    <div class="stat-label">Appels Optimisation</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{last_call}</div>
                    <div class="stat-label">Dernier Appel</div>
                </div>
            </div>
        </div>

        <div class="api-docs">
            <h2>Documentation API</h2>
            
            <div class="endpoint">
                <h3>GET /sparkseer-data/{pubkey}</h3>
                <p>Récupère toutes les données brutes de Sparkseer pour un nœud donné.</p>
                <pre>curl https://mcp-c544a464bb52.herokuapp.com/sparkseer-data/02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b</pre>
            </div>

            <div class="endpoint">
                <h3>POST /optimize-node</h3>
                <p>Optimise un nœud Lightning en utilisant les données de Sparkseer et OpenAI.</p>
                <pre>curl -X POST https://mcp-c544a464bb52.herokuapp.com/optimize-node \
  -H "Content-Type: application/json" \
  -d '{"pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"}'</pre>
            </div>

            <div class="endpoint">
                <h3>GET /health</h3>
                <p>Vérifie l'état de l'API.</p>
                <pre>curl https://mcp-c544a464bb52.herokuapp.com/health</pre>
            </div>
        </div>
    </div>
</body>
</html>
"""

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

@app.get("/", response_class=HTMLResponse)
async def home():
    """
    Page d'accueil de l'application
    """
    # Vérification de l'état de l'API Sparkseer
    try:
        # Utilisation de l'endpoint health de server.py
        health_response = await server_app.get_network_summary()
        sparkseer_status = "Opérationnel"
        sparkseer_status_class = "healthy"
    except Exception as e:
        sparkseer_status = f"Erreur: {str(e)}"
        sparkseer_status_class = "unhealthy"

    # Formatage de la date du dernier appel
    last_call = call_counter["last_call"]
    if last_call:
        last_call = last_call.strftime("%d/%m/%Y %H:%M:%S")
    else:
        last_call = "Jamais"

    # Génération de la page HTML
    html_content = HOME_PAGE_HTML.format(
        health_status="Opérationnel",
        health_status_class="healthy",
        version="1.0.0",
        sparkseer_status=sparkseer_status,
        sparkseer_status_class=sparkseer_status_class,
        total_calls=call_counter["total_calls"],
        sparkseer_calls=call_counter["sparkseer_calls"],
        optimize_calls=call_counter["optimize_calls"],
        last_call=last_call
    )
    
    return HTMLResponse(content=html_content)

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
        # Mise à jour des compteurs
        call_counter["total_calls"] += 1
        call_counter["sparkseer_calls"] += 1
        call_counter["last_call"] = datetime.now()
        
        # Récupération des données via server.py
        node_stats = await server_app.get_node_stats(pubkey)
        node_history = await server_app.get_node_history(pubkey)
        network_summary = await server_app.get_network_summary()
        centralities = await server_app.get_centralities()
        
        # Préparation de la réponse
        response = SparkseerDataResponse(
            node_stats=node_stats,
            node_history=node_history,
            network_summary=network_summary,
            centralities=centralities,
            recommendations={}  # À implémenter plus tard
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
        # Mise à jour des compteurs
        call_counter["total_calls"] += 1
        call_counter["optimize_calls"] += 1
        call_counter["last_call"] = datetime.now()
        
        # Récupération des données via server.py
        node_stats = await server_app.get_node_stats(request.pubkey)
        node_history = await server_app.get_node_history(request.pubkey)
        network_summary = await server_app.get_network_summary()
        centralities = await server_app.get_centralities()
        
        # Préparation des données pour l'analyse
        analysis_data = {
            "node_stats": node_stats,
            "node_history": node_history,
            "network_summary": network_summary,
            "centralities": centralities
        }
        
        # Analyse avec RAG
        rag_result = await server_app.rag_workflow.analyze_node_data(analysis_data)
        
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
    try:
        health_status = await server_app.health_check()
        return health_status
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 