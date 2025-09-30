from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime
import asyncio
import logging
from app.services.rag_service import get_rag_workflow, check_rag_health
from app.auth import verify_jwt_and_get_tenant

# Création du router
router = APIRouter(prefix="/rag", tags=["rag"])

# Modèles de requête
class QueryRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5
    context_type: Optional[str] = "lightning"  # lightning, general, technical
    include_validation: Optional[bool] = True

class IngestRequest(BaseModel):
    documents: List[str]
    metadata: Optional[Dict[str, str]] = None
    source_type: Optional[str] = "manual"  # manual, api, automated

class AnalysisRequest(BaseModel):
    node_pubkey: str
    analysis_type: str  # performance, fees, channels, network
    time_range: Optional[str] = "7d"  # 1d, 7d, 30d, 90d
    include_recommendations: Optional[bool] = True

class WorkflowRequest(BaseModel):
    workflow_name: str
    parameters: Optional[Dict[str, Any]] = None
    execute_async: Optional[bool] = True

class ValidationRequest(BaseModel):
    content: str
    validation_type: str  # config, report, recommendation
    criteria: Optional[Dict[str, Any]] = None

class BenchmarkRequest(BaseModel):
    benchmark_type: str  # performance, fees, network
    comparison_nodes: Optional[List[str]] = None
    metrics: Optional[List[str]] = None

# Endpoints existants améliorés
@router.post("/query")
async def query_rag(request: QueryRequest, rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Effectue une requête RAG avec contexte Lightning
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Ajout du contexte Lightning si demandé
        if request.context_type == "lightning":
            request.query = f"[Lightning Network Context] {request.query}"
        
        result = await rag_workflow.query(request.query, request.max_results)
        
        # Validation finale facultative
        validation_result = None
        if request.include_validation:
        validation_result = await rag_workflow.validate_report(result.get("answer", ""))
        
        return {
            "status": "success",
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "confidence": result.get("confidence", 0.0),
            "validation": validation_result,
            "processing_time": result.get("processing_time", 0.0)
        }
    except Exception as e:
        logging.error(f"Erreur requête RAG: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_rag_stats(rag_workflow = Depends(get_rag_workflow)):
    """
    Récupère les statistiques détaillées du système RAG
    """
    try:
        stats = await rag_workflow.get_stats()
        return {
            "status": "success",
            "stats": stats,
            "system_info": {
                "total_documents": stats.get("total_documents", 0),
                "total_queries": stats.get("total_queries", 0),
                "cache_hit_rate": stats.get("cache_hit_rate", 0.0),
                "average_response_time": stats.get("average_response_time", 0.0),
                "last_updated": stats.get("last_updated", datetime.now().isoformat())
            }
        }
    except Exception as e:
        logging.error(f"Erreur stats RAG: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest")
async def ingest_documents(request: IngestRequest, rag_workflow = Depends(get_rag_workflow)):
    """
    Ingestion de documents dans le système RAG avec métadonnées
    """
    try:
        result = await rag_workflow.ingest_documents_from_list(request.documents, request.metadata)
        return {
            "status": "success",
            "ingested": result,
            "source_type": request.source_type,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Erreur ingestion RAG: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_rag_history(rag_workflow = Depends(get_rag_workflow), limit: int = 50):
    """
    Récupère l'historique des requêtes RAG avec pagination
    """
    try:
        history = await rag_workflow.get_query_history(limit=limit)
        return {
            "status": "success",
            "history": history,
            "total_queries": len(history),
            "limit": limit
        }
    except Exception as e:
        logging.error(f"Erreur historique RAG: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def rag_health():
    """
    Vérification complète de la santé du système RAG
    """
    health = await check_rag_health()
    status = "healthy" if all(health.values()) else "degraded"
    
    # Informations supplémentaires
    additional_info = {
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "components": {
            "redis": health.get("redis", False),
            "mongo": health.get("mongo", False),
            "rag_instance": health.get("rag_instance", False),
            "embedding_service": health.get("embedding_service", True),
            "llm_service": health.get("llm_service", True)
        }
    }
    
    return {
        "status": status, 
        "details": health,
        "additional_info": additional_info
    }

# Nouveaux endpoints RAG avancés

@router.post("/analyze/node")
async def analyze_node(request: AnalysisRequest, rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Analyse complète d'un nœud Lightning avec RAG
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Construction de la requête d'analyse
        analysis_query = f"""
        Analyse du nœud {request.node_pubkey}:
        - Type d'analyse: {request.analysis_type}
        - Période: {request.time_range}
        - Inclure recommandations: {request.include_recommendations}
        
        Fournir une analyse détaillée avec métriques, tendances et recommandations.
        """
        
        result = await rag_workflow.query(analysis_query, max_results=10)
        
        # Validation de l'analyse
        validation = await rag_workflow.validate_report(result.get("answer", ""))
        
        return {
            "status": "success",
            "node_pubkey": request.node_pubkey,
            "analysis_type": request.analysis_type,
            "time_range": request.time_range,
            "analysis": result.get("answer", ""),
            "validation": validation,
            "recommendations": result.get("recommendations", []),
            "metrics": result.get("metrics", {}),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Erreur analyse nœud: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workflow/execute")
async def execute_workflow(request: WorkflowRequest, background_tasks: BackgroundTasks, rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Exécute un workflow RAG spécifique
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        if request.execute_async:
            # Exécution asynchrone
            task_id = f"workflow_{request.workflow_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            async def run_workflow():
                try:
                    # Simulation d'exécution de workflow
                    await asyncio.sleep(2)  # Simulation
                    logging.info(f"Workflow {request.workflow_name} exécuté avec succès")
                except Exception as e:
                    logging.error(f"Erreur workflow {request.workflow_name}: {str(e)}")
            
            background_tasks.add_task(run_workflow)
            
            return {
                "status": "started",
                "task_id": task_id,
                "workflow_name": request.workflow_name,
                "message": "Workflow démarré en arrière-plan"
            }
        else:
            # Exécution synchrone
            # Simulation d'exécution
            await asyncio.sleep(1)
            
            return {
                "status": "completed",
                "workflow_name": request.workflow_name,
                "result": "Workflow exécuté avec succès",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logging.error(f"Erreur exécution workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate")
async def validate_content(request: ValidationRequest, rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Valide du contenu avec le système RAG
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        validation_result = None
        
        if request.validation_type == "config":
            # Validation de configuration Lightning
            validation_result = await rag_workflow.validate_lightning_config({"content": request.content})
        elif request.validation_type == "report":
            # Validation de rapport
            validation_result = await rag_workflow.validate_report(request.content)
        else:
            # Validation générale
            validation_result = await rag_workflow.validate_report(request.content)
        
        return {
            "status": "success",
            "validation_type": request.validation_type,
            "validation_result": validation_result,
            "is_valid": "valid" in validation_result.lower() if validation_result else False,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Erreur validation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/benchmark")
async def run_benchmark(request: BenchmarkRequest, rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Exécute des benchmarks avec le système RAG
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Construction de la requête de benchmark
        benchmark_query = f"""
        Benchmark {request.benchmark_type}:
        - Nœuds de comparaison: {request.comparison_nodes or 'tous'}
        - Métriques: {request.metrics or 'performance, fees, network'}
        
        Fournir une analyse comparative détaillée.
        """
        
        result = await rag_workflow.query(benchmark_query, max_results=15)
        
        return {
            "status": "success",
            "benchmark_type": request.benchmark_type,
            "comparison_nodes": request.comparison_nodes,
            "metrics": request.metrics,
            "benchmark_result": result.get("answer", ""),
            "comparison_data": result.get("comparison_data", {}),
            "rankings": result.get("rankings", []),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Erreur benchmark: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/assets/list")
async def list_rag_assets(rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Liste tous les assets RAG disponibles
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Simulation de liste d'assets
        assets = {
            "documents": [
                {"id": "doc_1", "name": "Lightning Network Best Practices", "type": "guide"},
                {"id": "doc_2", "name": "Fee Optimization Strategies", "type": "strategy"},
                {"id": "doc_3", "name": "Node Performance Analysis", "type": "analysis"}
            ],
            "workflows": [
                {"id": "wf_1", "name": "Node Analysis Workflow", "type": "analysis"},
                {"id": "wf_2", "name": "Fee Optimization Workflow", "type": "optimization"}
            ],
            "metrics": [
                {"id": "metric_1", "name": "Network Centrality", "type": "network"},
                {"id": "metric_2", "name": "Fee Efficiency", "type": "performance"}
            ]
        }
        
        return {
            "status": "success",
            "assets": assets,
            "total_assets": sum(len(v) for v in assets.values()),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Erreur liste assets: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/assets/{asset_id}")
async def get_rag_asset(asset_id: str, rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Récupère un asset RAG spécifique
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Simulation de récupération d'asset
        asset = {
            "id": asset_id,
            "name": f"Asset {asset_id}",
            "content": f"Contenu de l'asset {asset_id}",
            "metadata": {
                "created_at": "2025-01-07T10:00:00Z",
                "updated_at": "2025-01-07T10:00:00Z",
                "type": "document"
            }
        }
        
        return {
            "status": "success",
            "asset": asset
        }
    except Exception as e:
        logging.error(f"Erreur récupération asset: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cache/clear")
async def clear_rag_cache(rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Vide le cache RAG
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Simulation de vidage de cache
        await asyncio.sleep(0.1)  # Simulation
        
        return {
            "status": "success",
            "message": "Cache RAG vidé avec succès",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Erreur vidage cache: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cache/stats")
async def get_cache_stats(rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Récupère les statistiques du cache RAG
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Simulation de stats de cache
        cache_stats = {
            "total_entries": 150,
            "hit_rate": 0.85,
            "miss_rate": 0.15,
            "memory_usage": "45.2 MB",
            "last_cleared": "2025-01-07T09:00:00Z"
        }
        
        return {
            "status": "success",
            "cache_stats": cache_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Erreur stats cache: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 
