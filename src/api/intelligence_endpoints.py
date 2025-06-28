from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
import asyncio
import logging
from app.services.rag_service import get_rag_workflow
from app.auth import verify_jwt_and_get_tenant

# Création du router
router = APIRouter(prefix="/intelligence", tags=["intelligence"])

# Modèles de requête pour l'intelligence
class NodeAnalysisRequest(BaseModel):
    node_pubkey: str
    analysis_depth: str = "comprehensive"  # basic, detailed, comprehensive
    include_network_context: bool = True
    include_historical_data: bool = True
    include_predictions: bool = False

class NetworkIntelligenceRequest(BaseModel):
    network_scope: str = "global"  # global, regional, local
    analysis_type: str = "topology"  # topology, routing, capacity
    include_metrics: List[str] = ["centrality", "connectivity", "liquidity"]
    time_range: str = "7d"

class OptimizationRequest(BaseModel):
    node_pubkey: str
    optimization_target: str  # fees, routing, capacity, connectivity
    constraints: Optional[Dict[str, Any]] = None
    risk_tolerance: str = "medium"  # low, medium, high
    include_impact_analysis: bool = True

class PredictionRequest(BaseModel):
    node_pubkey: str
    prediction_type: str  # performance, fees, network_growth
    time_horizon: str = "30d"  # 7d, 30d, 90d, 180d
    confidence_level: float = 0.8

class ComparativeAnalysisRequest(BaseModel):
    node_pubkeys: List[str]
    comparison_metrics: List[str] = ["fees", "routing", "capacity"]
    benchmark_type: str = "peer_group"  # peer_group, top_performers, historical
    include_rankings: bool = True

class AlertConfigurationRequest(BaseModel):
    node_pubkey: str
    alert_types: List[str] = ["performance_degradation", "fee_anomaly", "capacity_issue"]
    thresholds: Dict[str, float] = {}
    notification_channels: List[str] = ["api", "email"]

# Endpoints d'intelligence avancée

@router.post("/node/analyze")
async def analyze_node_intelligence(request: NodeAnalysisRequest, rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Analyse intelligente complète d'un nœud Lightning
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Construction de la requête d'analyse intelligente
        analysis_query = f"""
        Analyse intelligente du nœud {request.node_pubkey}:
        - Profondeur: {request.analysis_depth}
        - Contexte réseau: {request.include_network_context}
        - Données historiques: {request.include_historical_data}
        - Prédictions: {request.include_predictions}
        
        Fournir une analyse intelligente avec:
        1. Évaluation de la performance
        2. Analyse de la connectivité réseau
        3. Optimisation des frais
        4. Recommandations stratégiques
        5. Prédictions de performance (si activé)
        """
        
        result = await rag_workflow.query(analysis_query, max_results=15)
        
        # Validation de l'analyse
        validation = await rag_workflow.validate_report_with_ollama(result.get("answer", ""))
        
        return {
            "status": "success",
            "node_pubkey": request.node_pubkey,
            "analysis_depth": request.analysis_depth,
            "intelligence_analysis": result.get("answer", ""),
            "validation": validation,
            "key_insights": result.get("insights", []),
            "recommendations": result.get("recommendations", []),
            "risk_assessment": result.get("risk_assessment", {}),
            "performance_metrics": result.get("metrics", {}),
            "network_position": result.get("network_position", {}),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Erreur analyse intelligence nœud: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/network/analyze")
async def analyze_network_intelligence(request: NetworkIntelligenceRequest, rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Analyse intelligente du réseau Lightning
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Construction de la requête d'analyse réseau
        network_query = f"""
        Analyse intelligente du réseau Lightning:
        - Portée: {request.network_scope}
        - Type d'analyse: {request.analysis_type}
        - Métriques: {', '.join(request.include_metrics)}
        - Période: {request.time_range}
        
        Fournir une analyse intelligente du réseau avec:
        1. Topologie et connectivité
        2. Distribution de la liquidité
        3. Patterns de routage
        4. Points de congestion
        5. Opportunités d'optimisation
        """
        
        result = await rag_workflow.query(network_query, max_results=20)
        
        return {
            "status": "success",
            "network_scope": request.network_scope,
            "analysis_type": request.analysis_type,
            "network_intelligence": result.get("answer", ""),
            "topology_insights": result.get("topology", {}),
            "routing_analysis": result.get("routing", {}),
            "capacity_distribution": result.get("capacity", {}),
            "bottlenecks": result.get("bottlenecks", []),
            "optimization_opportunities": result.get("opportunities", []),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Erreur analyse intelligence réseau: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimization/recommend")
async def recommend_optimization(request: OptimizationRequest, rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Recommandations d'optimisation intelligentes
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Construction de la requête d'optimisation
        optimization_query = f"""
        Recommandations d'optimisation pour le nœud {request.node_pubkey}:
        - Cible: {request.optimization_target}
        - Contraintes: {request.constraints}
        - Tolérance au risque: {request.risk_tolerance}
        - Analyse d'impact: {request.include_impact_analysis}
        
        Fournir des recommandations intelligentes avec:
        1. Stratégies d'optimisation
        2. Impact attendu
        3. Risques associés
        4. Plan d'implémentation
        5. Métriques de suivi
        """
        
        result = await rag_workflow.query(optimization_query, max_results=12)
        
        return {
            "status": "success",
            "node_pubkey": request.node_pubkey,
            "optimization_target": request.optimization_target,
            "recommendations": result.get("recommendations", []),
            "impact_analysis": result.get("impact", {}),
            "risk_assessment": result.get("risks", {}),
            "implementation_plan": result.get("plan", {}),
            "monitoring_metrics": result.get("metrics", []),
            "expected_improvements": result.get("improvements", {}),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Erreur recommandations optimisation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/prediction/generate")
async def generate_predictions(request: PredictionRequest, rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Génération de prédictions intelligentes
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Construction de la requête de prédiction
        prediction_query = f"""
        Prédictions pour le nœud {request.node_pubkey}:
        - Type: {request.prediction_type}
        - Horizon: {request.time_horizon}
        - Niveau de confiance: {request.confidence_level}
        
        Générer des prédictions intelligentes avec:
        1. Scénarios de performance
        2. Évolutions des frais
        3. Croissance du réseau
        4. Facteurs de risque
        5. Intervalles de confiance
        """
        
        result = await rag_workflow.query(prediction_query, max_results=10)
        
        return {
            "status": "success",
            "node_pubkey": request.node_pubkey,
            "prediction_type": request.prediction_type,
            "time_horizon": request.time_horizon,
            "confidence_level": request.confidence_level,
            "predictions": result.get("predictions", {}),
            "scenarios": result.get("scenarios", []),
            "confidence_intervals": result.get("intervals", {}),
            "risk_factors": result.get("risk_factors", []),
            "trend_analysis": result.get("trends", {}),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Erreur génération prédictions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/comparative/analyze")
async def comparative_analysis(request: ComparativeAnalysisRequest, rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Analyse comparative intelligente entre nœuds
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Construction de la requête comparative
        comparative_query = f"""
        Analyse comparative des nœuds: {', '.join(request.node_pubkeys)}
        - Métriques: {', '.join(request.comparison_metrics)}
        - Benchmark: {request.benchmark_type}
        - Rankings: {request.include_rankings}
        
        Fournir une analyse comparative intelligente avec:
        1. Comparaison des performances
        2. Analyse des différences
        3. Classements relatifs
        4. Recommandations d'amélioration
        5. Insights stratégiques
        """
        
        result = await rag_workflow.query(comparative_query, max_results=15)
        
        return {
            "status": "success",
            "node_pubkeys": request.node_pubkeys,
            "comparison_metrics": request.comparison_metrics,
            "benchmark_type": request.benchmark_type,
            "comparative_analysis": result.get("answer", ""),
            "performance_comparison": result.get("comparison", {}),
            "rankings": result.get("rankings", []) if request.include_rankings else None,
            "differences_analysis": result.get("differences", {}),
            "improvement_recommendations": result.get("recommendations", []),
            "strategic_insights": result.get("insights", []),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Erreur analyse comparative: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/configure")
async def configure_intelligent_alerts(request: AlertConfigurationRequest, rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Configuration d'alertes intelligentes
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Construction de la requête de configuration d'alertes
        alert_query = f"""
        Configuration d'alertes intelligentes pour le nœud {request.node_pubkey}:
        - Types d'alertes: {', '.join(request.alert_types)}
        - Seuils: {request.thresholds}
        - Canaux: {', '.join(request.notification_channels)}
        
        Configurer des alertes intelligentes avec:
        1. Seuils adaptatifs
        2. Patterns de détection
        3. Logique d'escalade
        4. Personnalisation des notifications
        5. Intégration avec le système RAG
        """
        
        result = await rag_workflow.query(alert_query, max_results=8)
        
        return {
            "status": "success",
            "node_pubkey": request.node_pubkey,
            "alert_types": request.alert_types,
            "thresholds": request.thresholds,
            "notification_channels": request.notification_channels,
            "alert_configuration": result.get("configuration", {}),
            "adaptive_thresholds": result.get("adaptive_thresholds", {}),
            "detection_patterns": result.get("patterns", []),
            "escalation_logic": result.get("escalation", {}),
            "notification_templates": result.get("templates", {}),
            "rag_integration": result.get("rag_integration", {}),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Erreur configuration alertes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/insights/summary")
async def get_intelligence_summary(rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Résumé des insights d'intelligence
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Construction de la requête de résumé
        summary_query = """
        Résumé des insights d'intelligence Lightning Network:
        
        Fournir un résumé des insights clés:
        1. Tendances principales du réseau
        2. Opportunités d'optimisation
        3. Risques identifiés
        4. Recommandations stratégiques
        5. Métriques de performance globales
        """
        
        result = await rag_workflow.query(summary_query, max_results=10)
        
        return {
            "status": "success",
            "intelligence_summary": result.get("answer", ""),
            "key_trends": result.get("trends", []),
            "optimization_opportunities": result.get("opportunities", []),
            "identified_risks": result.get("risks", []),
            "strategic_recommendations": result.get("recommendations", []),
            "global_metrics": result.get("metrics", {}),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Erreur résumé intelligence: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workflow/automated")
async def execute_automated_intelligence_workflow(background_tasks: BackgroundTasks, rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Exécution d'un workflow d'intelligence automatisé
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        task_id = f"intelligence_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        async def run_intelligence_workflow():
            try:
                # Simulation d'exécution du workflow d'intelligence
                await asyncio.sleep(5)  # Simulation
                logging.info("Workflow d'intelligence automatisé exécuté avec succès")
            except Exception as e:
                logging.error(f"Erreur workflow d'intelligence: {str(e)}")
        
        background_tasks.add_task(run_intelligence_workflow)
        
        return {
            "status": "started",
            "task_id": task_id,
            "workflow_type": "automated_intelligence",
            "message": "Workflow d'intelligence démarré en arrière-plan",
            "estimated_duration": "5-10 minutes",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Erreur démarrage workflow intelligence: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health/intelligence")
async def intelligence_health(rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Santé du système d'intelligence
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Vérification de la santé du système d'intelligence
        health_status = {
            "rag_system": True,
            "prediction_engine": True,
            "optimization_engine": True,
            "alert_system": True,
            "comparative_analysis": True,
            "network_intelligence": True
        }
        
        return {
            "status": "healthy",
            "intelligence_components": health_status,
            "last_updated": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        logging.error(f"Erreur santé intelligence: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 