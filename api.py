from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
import asyncio
import json
from typing import Optional
from datetime import datetime
from server import (
    configure_cors,
    rag_workflow,
    cache_manager,
    rate_limiter,
    request_manager,
    get_headers,
    router as server_router,
    get_network_summary,
    retry_manager
)
from auth.routes import router as auth_router

app = FastAPI(
    title="MCP Lightning Node Optimizer API",
    description="API pour l'optimisation des nœuds Lightning via Sparkseer et OpenAI",
    version="1.0.0"
)

# Configuration CORS
configure_cors(app)

# Inclusion des routes d'authentification
app.include_router(auth_router)

# Inclusion des routes du serveur
app.include_router(server_router)

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
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>MCP Lightning Node Optimizer</h1>
        <p>Bienvenue sur l'API d'optimisation des nœuds Lightning.</p>
        <p>Consultez la documentation de l'API à <a href="/docs">/docs</a></p>
    </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HOME_PAGE_HTML

@app.get("/health")
async def health_check(request: Request):
    """Vérifie l'état de santé de l'API."""
    try:
        # Crée une requête mock pour le health check
        network_summary = await get_network_summary(request)
        sparkseer_status = "healthy"
    except Exception as e:
        sparkseer_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy",
        "sparkseer_status": sparkseer_status,
        "retry_stats": {
            endpoint: retry_manager.get_retry_stats(endpoint)
            for endpoint in ["network_summary", "centralities", "node_stats", "node_history", "optimize_node"]
        },
        "fallback_stats": {
            endpoint: retry_manager.get_fallback_stats(endpoint)
            for endpoint in ["network_summary", "node_stats"]
        },
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 