"""
API principale pour le système MCP (Moniteur et Contrôleur de Performance)

Cette API expose les endpoints pour le simulateur de nœuds Lightning, 
l'optimiseur de frais, et les rapports d'analyse.

Dernière mise à jour: 9 mai 2025
"""

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import logging
import asyncio
import json
import os
import random
from datetime import datetime
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-api")

# Importations internes (conditionnelles)
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from tools.node_simulator import NodeSimulator
    from optimizers.scoring_utils import evaluate_node, DecisionType
    from optimizers.fee_update_utils import get_fee_adjustment
    LEGACY_TOOLS_AVAILABLE = True
except ImportError as e:
    print(f"Legacy tools non disponibles: {e}")
    LEGACY_TOOLS_AVAILABLE = False

# Import du router Token4Good
from token4good_endpoints import router as token4good_router

# Import des routers existants (conditionnels)
try:
    from app.routes.lightning_scoring import router as lightning_scoring_router
    from app.routes.lightning import router as lightning_router  
    from app.routes.node import router as node_router
    from app.routes.channels import router as channels_router
    from app.routes.nodes import router as nodes_router
    from app.routes.admin import router as admin_router
    from app.routes.health import router as health_router
    from app.routes.fee_optimizer_api import router as fee_optimizer_router
    from app.routes.metrics import router as metrics_router
    from app.routes.intelligence import router as intelligence_router
    LEGACY_ROUTES_AVAILABLE = True
except ImportError as e:
    print(f"Legacy routes non disponibles: {e}")
    LEGACY_ROUTES_AVAILABLE = False

# Import du router RGB (conditionnel)
try:
    from rgb_endpoints import router as rgb_router
    RGB_ROUTES_AVAILABLE = True
except ImportError:
    RGB_ROUTES_AVAILABLE = False

# Initialisation de l'application FastAPI
app = FastAPI(
    title="MCP - Moniteur et Contrôleur de Performance pour Lightning Network",
    description="API pour l'optimisation et la simulation de nœuds Lightning Network",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À ajuster en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion du router Token4Good
app.include_router(token4good_router)

# Inclusion des routers existants (conditionnel)
if LEGACY_ROUTES_AVAILABLE:
    app.include_router(lightning_scoring_router)
    app.include_router(lightning_router)
    app.include_router(node_router)
    app.include_router(channels_router)
    app.include_router(nodes_router)
    app.include_router(admin_router)
    app.include_router(health_router)
    app.include_router(fee_optimizer_router)
    app.include_router(metrics_router)
    app.include_router(intelligence_router)

# Inclusion du router RGB (conditionnel)
if RGB_ROUTES_AVAILABLE:
    app.include_router(rgb_router)

# Variables globales
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
SIMULATOR_OUTPUT_PATH = Path("rag/RAG_assets/nodes/simulations")

# Middleware pour le logging des requêtes
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware pour enregistrer les requêtes entrantes"""
    start_time = datetime.now()
    response = await call_next(request)
    process_time = datetime.now() - start_time
    logger.info(f"[{request.method}] {request.url.path} - {response.status_code} - {process_time.total_seconds():.3f}s")
    return response

# Route de santé
@app.get("/health")
async def health_check():
    """Vérifie l'état de santé de l'API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Endpoints pour la simulation de nœuds
@app.get("/api/v1/simulate/profiles")
async def get_simulation_profiles():
    """Récupère la liste des profils de simulation disponibles"""
    try:
        simulator = NodeSimulator()
        profiles = list(simulator.NODE_BEHAVIORS.keys())
        return {
            "profiles": profiles,
            "count": len(profiles)
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des profils: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@app.post("/api/v1/simulate/node")
async def simulate_node(profile: str, generate_report: bool = True):
    """
    Génère une simulation de nœud avec le profil spécifié
    
    Args:
        profile: Profil de comportement du nœud
        generate_report: Si True, génère un rapport d'évaluation
    """
    try:
        # Initialiser le simulateur
        simulator = NodeSimulator()
        
        # Vérifier si le profil existe
        if profile not in simulator.NODE_BEHAVIORS:
            raise HTTPException(
                status_code=400, 
                detail=f"Profil inconnu: {profile}. Profils disponibles: {list(simulator.NODE_BEHAVIORS.keys())}"
            )
        
        # Générer la simulation
        logger.info(f"Génération d'une simulation pour le profil '{profile}'")
        simulated_data = simulator.generate_simulation(profile)
        
        # Sauvegarder les données simulées
        filepath = simulator.save_simulation(simulated_data)
        
        result = {
            "profile": profile,
            "timestamp": datetime.now().isoformat(),
            "filepath": str(filepath),
            "node_metrics": {
                "success_rate": simulated_data["metrics"]["activity"]["success_rate"],
                "forwards_count": simulated_data["metrics"]["activity"]["forwards_count"],
                "cumul_fees": simulated_data["cumul_fees"]
            }
        }
        
        # Générer un rapport d'évaluation si demandé
        if generate_report:
            # Évaluer le nœud avec le système de scoring
            evaluation = evaluate_node(simulated_data)
            
            if evaluation["status"] == "success":
                result["evaluation"] = {
                    "node_score": evaluation["node_score"],
                    "recommendation": evaluation["global_recommendation"],
                    "channel_count": len(evaluation["channel_scores"])
                }
            else:
                result["evaluation"] = {
                    "status": "error",
                    "reason": evaluation.get("reason", "Erreur inconnue")
                }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la simulation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

# Endpoints pour l'optimisation et les décisions
@app.post("/api/v1/optimize/node/{node_id}")
async def optimize_node(node_id: str, dry_run: bool = None):
    """
    Optimise un nœud Lightning en fonction des métriques
    
    Args:
        node_id: Identifiant du nœud à optimiser
        dry_run: Si True, simule l'optimisation sans l'appliquer
    """
    # Utiliser la valeur par défaut si non spécifiée
    if dry_run is None:
        dry_run = DRY_RUN
        
    try:
        # Charger les données du nœud
        node_file = next(SIMULATOR_OUTPUT_PATH.glob(f"*{node_id}*.json"), None)
        
        if not node_file:
            raise HTTPException(
                status_code=404, 
                detail=f"Nœud non trouvé: {node_id}"
            )
        
        with open(node_file, "r") as f:
            node_data = json.load(f)
            
        # Évaluer le nœud
        logger.info(f"Évaluation du nœud {node_id}")
        evaluation = evaluate_node(node_data)
        
        if evaluation["status"] != "success":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "reason": evaluation.get("reason", "Erreur inconnue"),
                    "node_id": node_id
                }
            )
            
        # Préparer les mises à jour de frais en fonction des recommandations
        updates = []
        
        for channel_score in evaluation["channel_scores"]:
            # Ne mettre à jour que les canaux avec une recommandation de changement de frais
            if channel_score["recommendation"] in [DecisionType.INCREASE_FEES, DecisionType.LOWER_FEES]:
                channel_id = channel_score["channel_id"]
                
                # Simuler des valeurs de frais pour le test
                current_base_fee = 1000
                current_fee_rate = 500
                
                # Calculer les nouveaux frais
                new_base_fee, new_fee_rate = get_fee_adjustment(
                    current_base_fee=current_base_fee,
                    current_fee_rate=current_fee_rate,
                    forward_success_rate=channel_score["scores"]["success_rate"],
                    channel_activity=int(node_data["metrics"]["activity"]["forwards_count"] * random.uniform(0.7, 1.3))
                )
                
                updates.append({
                    "channel_id": channel_id,
                    "old_base_fee": current_base_fee,
                    "old_fee_rate": current_fee_rate,
                    "new_base_fee": new_base_fee,
                    "new_fee_rate": new_fee_rate,
                    "recommendation": channel_score["recommendation"]
                })
        
        # Retourner les résultats
        return {
            "status": "success",
            "node_id": node_id,
            "evaluation": {
                "node_score": evaluation["node_score"],
                "global_recommendation": evaluation["global_recommendation"]
            },
            "updates": updates,
            "dry_run": dry_run
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'optimisation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

# Endpoint pour les métriques du tableau de bord
@app.get("/api/v1/dashboard/metrics")
async def get_dashboard_metrics():
    """Récupère les métriques globales pour le tableau de bord"""
    try:
        # Simuler des métriques pour le test
        return {
            "nodes_count": 25,
            "total_forwards": 12500,
            "total_fees_earned": 150000,
            "avg_success_rate": 0.92,
            "channels_count": 420,
            "avg_channel_capacity": 5000000,
            "total_capacity": 2100000000,
            "updated_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des métriques: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

# Point d'entrée principal
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    ) 