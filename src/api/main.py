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

# Importations internes avec gestion d'erreur
try:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tools.node_simulator import NodeSimulator
    from optimizers.scoring_utils import evaluate_node, DecisionType
    from optimizers.fee_update_utils import get_fee_adjustment
except ImportError as e:
    logger.warning(f"Imports optionnels non disponibles: {e}")
    NodeSimulator = None
    evaluate_node = None
    DecisionType = None
    get_fee_adjustment = None

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
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "dry_run": DRY_RUN
    }

# Route racine
@app.get("/")
async def root():
    """Page d'accueil de l'API"""
    return {
        "message": "MCP - Moniteur et Contrôleur de Performance",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health"
    }

# Endpoints pour la simulation de nœuds (si disponible)
@app.get("/api/v1/simulate/profiles")
async def get_simulation_profiles():
    """Récupère la liste des profils de simulation disponibles"""
    if NodeSimulator is None:
        raise HTTPException(
            status_code=503, 
            detail="Service de simulation non disponible"
        )
    
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
    if NodeSimulator is None:
        raise HTTPException(
            status_code=503, 
            detail="Service de simulation non disponible"
        )
    
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
        if generate_report and evaluate_node is not None:
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
        
    if evaluate_node is None:
        raise HTTPException(
            status_code=503, 
            detail="Service d'optimisation non disponible"
        )
        
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
                current_fees = channel_score.get("current_fees", 1000)
                adjustment = get_fee_adjustment(channel_score["recommendation"], current_fees)
                
                updates.append({
                    "channel_id": channel_id,
                    "current_fees": current_fees,
                    "new_fees": adjustment,
                    "recommendation": channel_score["recommendation"].value,
                    "reason": channel_score.get("reason", "Optimisation automatique")
                })
        
        result = {
            "node_id": node_id,
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "evaluation": {
                "node_score": evaluation["node_score"],
                "global_recommendation": evaluation["global_recommendation"],
                "channel_count": len(evaluation["channel_scores"])
            },
            "updates": updates,
            "update_count": len(updates)
        }
        
        # Si ce n'est pas un dry run, appliquer les changements
        if not dry_run:
            logger.info(f"Application des mises à jour pour le nœud {node_id}")
            # Ici, vous ajouteriez le code pour appliquer réellement les changements
            result["applied"] = True
        else:
            result["applied"] = False
            result["message"] = "Mode dry-run activé - aucun changement appliqué"
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'optimisation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

# Endpoints pour le tableau de bord
@app.get("/api/v1/dashboard/metrics")
async def get_dashboard_metrics():
    """Récupère les métriques pour le tableau de bord"""
    try:
        # Métriques de base du système
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "status": "operational",
                "version": "1.0.0",
                "environment": os.getenv("ENVIRONMENT", "development"),
                "dry_run": DRY_RUN
            },
            "api": {
                "endpoints_available": len(app.routes),
                "health_status": "healthy"
            }
        }
        
        # Ajouter des métriques de simulation si disponible
        if NodeSimulator is not None:
            try:
                simulator = NodeSimulator()
                metrics["simulation"] = {
                    "profiles_available": len(simulator.NODE_BEHAVIORS),
                    "profiles": list(simulator.NODE_BEHAVIORS.keys())
                }
            except Exception as e:
                logger.warning(f"Impossible de récupérer les métriques de simulation: {e}")
                metrics["simulation"] = {
                    "status": "unavailable",
                    "error": str(e)
                }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des métriques: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

# Endpoint pour la configuration
@app.get("/api/v1/config")
async def get_config():
    """Récupère la configuration actuelle de l'application"""
    return {
        "environment": os.getenv("ENVIRONMENT", "development"),
        "dry_run": DRY_RUN,
        "version": "1.0.0",
        "features": {
            "simulation": NodeSimulator is not None,
            "optimization": evaluate_node is not None,
            "database": False,  # Pas de base de données en mode simple
            "redis": False      # Pas de Redis en mode simple
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 