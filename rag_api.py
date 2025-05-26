#!/usr/bin/env python3
"""
API RAG simple pour MCP avec Ollama
Dernière mise à jour: 25 mai 2025
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import asyncio
import uvicorn
from datetime import datetime
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Modèles Pydantic
class QueryRequest(BaseModel):
    query: str
    model: str = "llama3"
    max_length: int = 500

class EmbeddingRequest(BaseModel):
    text: str
    model: str = "llama3"

class AnalysisRequest(BaseModel):
    node_data: dict
    analysis_type: str = "fee_optimization"

# Création de l'app FastAPI
app = FastAPI(
    title="MCP RAG API avec Ollama",
    description="API pour le système RAG Lightning Network avec Ollama",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OllamaClient:
    """Client simple pour Ollama."""
    
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
    
    async def test_connection(self):
        """Test la connexion à Ollama."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except:
            return False
    
    async def get_models(self):
        """Récupère la liste des modèles disponibles."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Erreur récupération modèles: {e}")
            return {"models": []}
    
    async def generate_response(self, prompt: str, model="llama3"):
        """Génère une réponse via Ollama."""
        try:
            url = f"{self.base_url}/api/generate"
            data = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=data)
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
        except Exception as e:
            logger.error(f"Erreur génération: {e}")
            raise HTTPException(status_code=500, detail=f"Erreur génération: {e}")
    
    async def get_embedding(self, text: str, model="llama3"):
        """Génère un embedding via Ollama."""
        try:
            url = f"{self.base_url}/api/embeddings"
            data = {
                "model": model,
                "prompt": text
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=data)
                response.raise_for_status()
                result = response.json()
                return result.get("embedding", [])
        except Exception as e:
            logger.error(f"Erreur embedding: {e}")
            raise HTTPException(status_code=500, detail=f"Erreur embedding: {e}")

# Instance globale du client Ollama
ollama_client = OllamaClient()

@app.get("/")
async def root():
    """Page d'accueil de l'API RAG."""
    return {
        "service": "MCP RAG API avec Ollama",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "endpoints": [
            "/health",
            "/models",
            "/query",
            "/embed",
            "/analyze",
            "/lightning/optimize",
            "/docs"
        ]
    }

@app.get("/health")
async def health_check():
    """Vérification de santé incluant Ollama."""
    ollama_status = await ollama_client.test_connection()
    
    return {
        "status": "healthy" if ollama_status else "degraded",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "running",
            "ollama": "connected" if ollama_status else "disconnected"
        },
        "ollama_url": ollama_client.base_url
    }

@app.get("/models")
async def get_available_models():
    """Récupère les modèles disponibles dans Ollama."""
    models = await ollama_client.get_models()
    return {
        "available_models": models.get("models", []),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/query")
async def rag_query(request: QueryRequest):
    """Effectue une requête RAG avec contexte Lightning Network."""
    
    # Construire le prompt avec contexte Lightning Network
    lightning_context = """
Tu es un expert en Lightning Network et en optimisation de nœuds. Tu dois répondre aux questions 
avec une expertise technique approfondie sur:
- Configuration des frais (base fee, fee rate)
- Gestion de la liquidité (inbound/outbound)
- Routing et pathfinding
- Monitoring et métriques
- Stratégies d'optimisation des revenus
- Sécurité et best practices

Contexte Lightning Network:
- Les nœuds génèrent des revenus en routant des paiements
- Les frais doivent être équilibrés (ni trop hauts, ni trop bas)
- La liquidité doit être bien répartie pour maximiser les opportunités de routing
- Le monitoring est crucial pour détecter les problèmes rapidement
"""
    
    full_prompt = f"{lightning_context}\n\nQuestion: {request.query}\n\nRéponse:"
    
    response = await ollama_client.generate_response(full_prompt, request.model)
    
    return {
        "query": request.query,
        "response": response,
        "model": request.model,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/embed")
async def generate_embedding(request: EmbeddingRequest):
    """Génère un embedding pour un texte."""
    embedding = await ollama_client.get_embedding(request.text, request.model)
    
    return {
        "text": request.text,
        "embedding": embedding,
        "dimension": len(embedding),
        "model": request.model,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/analyze")
async def analyze_data(request: AnalysisRequest):
    """Analyse des données Lightning Network."""
    
    node_data = request.node_data
    analysis_type = request.analysis_type
    
    # Construire le prompt d'analyse
    if analysis_type == "fee_optimization":
        prompt = f"""
Analyse les données suivantes d'un nœud Lightning Network et fournis des recommandations d'optimisation des frais:

Données du nœud:
{node_data}

Fournis une analyse structurée avec:
1. État actuel du nœud
2. Points d'amélioration identifiés  
3. Recommandations concrètes pour les frais
4. Stratégies de liquidité
5. Actions prioritaires

Sois précis et actionnable dans tes recommandations.
"""
    else:
        prompt = f"""
Analyse générale des données Lightning Network:

Données:
{node_data}

Fournis une analyse complète avec insights et recommandations.
"""
    
    analysis = await ollama_client.generate_response(prompt)
    
    return {
        "node_data": node_data,
        "analysis_type": analysis_type,
        "analysis": analysis,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/lightning/optimize")
async def optimize_lightning_node(node_data: dict):
    """Optimisation spécifique pour nœuds Lightning."""
    
    prompt = f"""
En tant qu'expert Lightning Network, analyse ce nœud et fournis des recommandations d'optimisation:

DONNÉES DU NŒUD:
{node_data}

ANALYSE DEMANDÉE:
1. Configuration des frais actuelle
2. État de la liquidité
3. Performance de routing
4. Recommandations d'amélioration
5. Actions immédiates à prendre

Fournis des recommandations CONCRÈTES et ACTIONNABLES avec des valeurs numériques précises.
"""
    
    optimization = await ollama_client.generate_response(prompt)
    
    return {
        "node_data": node_data,
        "optimization_recommendations": optimization,
        "timestamp": datetime.now().isoformat(),
        "expert_system": "MCP RAG Lightning Optimizer"
    }

@app.get("/lightning/health/{node_id}")
async def node_health_check(node_id: str):
    """Vérification de santé d'un nœud Lightning."""
    
    # Simuler une vérification de santé
    prompt = f"""
Effectue une vérification de santé pour le nœud Lightning {node_id}.

Vérifie:
1. Connectivité réseau
2. État des channels
3. Liquidité disponible
4. Performance récente
5. Alertes potentielles

Fournis un rapport de santé structuré.
"""
    
    health_report = await ollama_client.generate_response(prompt)
    
    return {
        "node_id": node_id,
        "health_status": "checked",
        "report": health_report,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("🚀 Lancement de l'API RAG MCP avec Ollama...")
    print("📍 Disponible sur: http://localhost:8001")
    print("📖 Documentation: http://localhost:8001/docs")
    print("🔍 Santé: http://localhost:8001/health")
    print("🧠 Modèles: http://localhost:8001/models")
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info") 