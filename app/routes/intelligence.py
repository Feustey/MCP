"""
Endpoints d'intelligence MCP pour recommandations et analyse de nœuds
Version adaptée de mcp-light avec fonctionnalités étendues
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from typing import Optional, List
import logging
from datetime import datetime
import asyncio

from ..models.mcp_schemas import (
    NodeInfoResponse, 
    RecommendationsResponse, 
    PriorityActionsRequest,
    PriorityActionsResponse,
    HealthResponse,
    BulkAnalysisRequest,
    BulkAnalysisResponse,
    NodeAnalysisRequest,
    ErrorResponse,
    PerformanceMetrics
)
from src.clients.anthropic_client import AnthropicClient
from src.clients.sparkseer_client import SparkseerClient
from src.utils.cache_manager import cache_manager
from src.clients.lnbits_client import LNBitsClient

logger = logging.getLogger("mcp.intelligence")

router = APIRouter(prefix="/api/v1", tags=["Intelligence"])

# Clients globaux
anthropic_client = AnthropicClient()
sparkseer_client = SparkseerClient()
lnbits_client = LNBitsClient()

# Métriques de performance
performance_metrics = PerformanceMetrics()

async def update_metrics(endpoint: str, response_time: float, success: bool):
    """Met à jour les métriques de performance"""
    global performance_metrics
    performance_metrics.request_count += 1
    
    # Moyenne mobile simple
    performance_metrics.average_response_time = (
        (performance_metrics.average_response_time * (performance_metrics.request_count - 1) + response_time) 
        / performance_metrics.request_count
    )
    
    if not success:
        performance_metrics.error_rate = (
            (performance_metrics.error_rate * (performance_metrics.request_count - 1) + 1) 
            / performance_metrics.request_count
        )
    
    performance_metrics.last_updated = datetime.utcnow()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Vérification de l'état de santé de l'API et des services externes"""
    start_time = datetime.utcnow()
    
    services_status = {}
    
    # Test des services en parallèle
    tasks = [
        ("sparkseer_api", sparkseer_client.test_connection()),
        ("anthropic_api", anthropic_client.test_connection()),
        ("cache", _test_cache_connection()),
        ("lnbits_api", _test_lnbits_connection())
    ]
    
    try:
        results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
        
        for i, (service_name, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, Exception):
                services_status[service_name] = f"error: {str(result)}"
            else:
                services_status[service_name] = "connected" if result else "disconnected"
    
    except Exception as e:
        logger.error(f"Erreur lors du health check: {str(e)}")
    
    # Statut global
    connected_services = sum(1 for status in services_status.values() if "connected" in status)
    total_services = len(services_status)
    
    if connected_services == total_services:
        overall_status = "healthy"
    elif connected_services > total_services // 2:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    # Statistiques du cache
    cache_stats = await cache_manager.get_stats()
    
    response_time = (datetime.utcnow() - start_time).total_seconds()
    await update_metrics("health", response_time, overall_status != "unhealthy")
    
    return HealthResponse(
        status=overall_status,
        services=services_status,
        cache_stats=cache_stats,
        uptime_seconds=int((datetime.utcnow() - start_time).total_seconds())
    )

@router.get("/node/{pubkey}/info", response_model=NodeInfoResponse)
async def get_node_info(
    pubkey: str,
    include_historical: bool = Query(default=True),
    include_network_analysis: bool = Query(default=False),
    use_cache: bool = Query(default=True)
):
    """Récupère toutes les informations disponibles sur un nœud"""
    start_time = datetime.utcnow()
    
    # Validation de la pubkey
    if len(pubkey) != 66:
        raise HTTPException(status_code=400, detail="Pubkey invalide (doit faire 66 caractères)")
    
    # Clé de cache
    cache_key = f"node_info:{pubkey}:{include_historical}:{include_network_analysis}"
    
    try:
        # Vérifier le cache d'abord si demandé
        if use_cache:
            cached_data = await cache_manager.get(cache_key, "node_info")
            if cached_data:
                logger.debug(f"Cache hit pour {pubkey[:16]}...")
                cached_data["cache_hit"] = True
                return NodeInfoResponse(**cached_data)
        
        # Récupération des données depuis les sources
        tasks = []
        
        # Données Sparkseer
        if sparkseer_client.enabled:
            tasks.append(("sparkseer", sparkseer_client.get_node_info(pubkey)))
        
        # Données LNBits locales si disponibles
        tasks.append(("lnbits", _get_local_node_data(pubkey)))
        
        # Exécution parallèle
        results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
        
        # Agrégation des données
        node_data = {"pubkey": pubkey}
        sources = []
        
        for i, (source_name, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, dict) and result:
                node_data.update(result)
                sources.append(source_name)
            elif isinstance(result, Exception):
                logger.warning(f"Erreur source {source_name}: {str(result)}")
        
        if not sources:
            raise HTTPException(status_code=404, detail=f"Nœud {pubkey} non trouvé")
        
        # Construction de la réponse
        response_data = {
            "pubkey": pubkey,
            "node_info": node_data.get("node_info", {}),
            "metrics": node_data.get("metrics", {}),
            "channels": node_data.get("channels", []),
            "network_position": node_data.get("network_position", {}),
            "timestamp": datetime.utcnow(),
            "source": "+".join(sources),
            "cache_hit": False
        }
        
        # Mise en cache
        if use_cache:
            await cache_manager.set(cache_key, response_data, data_type="node_info")
        
        response_time = (datetime.utcnow() - start_time).total_seconds()
        await update_metrics("node_info", response_time, True)
        
        return NodeInfoResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des infos pour {pubkey}: {str(e)}")
        response_time = (datetime.utcnow() - start_time).total_seconds()
        await update_metrics("node_info", response_time, False)
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@router.get("/node/{pubkey}/recommendations", response_model=RecommendationsResponse)
async def get_recommendations(
    pubkey: str,
    category: Optional[str] = Query(None, description="Filtrer par catégorie"),
    priority: Optional[str] = Query(None, description="Filtrer par priorité"),
    use_cache: bool = Query(default=True)
):
    """Récupère les recommandations techniques basées sur les métriques"""
    start_time = datetime.utcnow()
    
    cache_key = f"recommendations:{pubkey}:{category}:{priority}"
    
    try:
        # Cache check
        if use_cache:
            cached_data = await cache_manager.get(cache_key, "recommendations")
            if cached_data:
                return RecommendationsResponse(**cached_data)
        
        # Récupération des recommandations
        recommendations_data = await sparkseer_client.get_node_recommendations(pubkey)
        recommendations = recommendations_data.get("recommendations", [])
        
        # Filtrage
        if category:
            recommendations = [r for r in recommendations if r.get("category") == category]
        if priority:
            recommendations = [r for r in recommendations if r.get("priority") == priority]
        
        # Statistiques
        by_category = {}
        by_priority = {}
        
        for rec in recommendations:
            cat = rec.get("category", "unknown")
            prio = rec.get("priority", "medium")
            by_category[cat] = by_category.get(cat, 0) + 1
            by_priority[prio] = by_priority.get(prio, 0) + 1
        
        response_data = {
            "pubkey": pubkey,
            "recommendations": recommendations,
            "total_count": len(recommendations),
            "by_category": by_category,
            "by_priority": by_priority,
            "generated_at": datetime.utcnow()
        }
        
        # Cache
        if use_cache:
            await cache_manager.set(cache_key, response_data, data_type="recommendations")
        
        response_time = (datetime.utcnow() - start_time).total_seconds()
        await update_metrics("recommendations", response_time, True)
        
        return RecommendationsResponse(**response_data)
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des recommandations pour {pubkey}: {str(e)}")
        response_time = (datetime.utcnow() - start_time).total_seconds()
        await update_metrics("recommendations", response_time, False)
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@router.post("/node/{pubkey}/priorities", response_model=PriorityActionsResponse)
async def get_priority_actions(
    pubkey: str, 
    request: PriorityActionsRequest,
    background_tasks: BackgroundTasks
):
    """Génère les actions prioritaires via Anthropic basées sur les données du nœud"""
    start_time = datetime.utcnow()
    
    try:
        # Récupération des données complètes en parallèle
        tasks = [
            sparkseer_client.get_node_info(pubkey),
            sparkseer_client.get_node_recommendations(pubkey),
            _get_local_node_data(pubkey)
        ]
        
        node_info, recommendations, local_data = await asyncio.gather(
            *tasks, return_exceptions=True
        )
        
        # Gestion des erreurs
        if isinstance(node_info, Exception) or not node_info:
            raise HTTPException(status_code=404, detail=f"Nœud {pubkey} non trouvé")
        
        if isinstance(recommendations, Exception):
            recommendations = {"recommendations": []}
        
        if isinstance(local_data, Exception):
            local_data = {}
        
        # Enrichissement des données
        enriched_node_info = {**node_info, **local_data}
        
        # Génération des actions prioritaires via Anthropic
        priority_response = await anthropic_client.generate_priority_actions(
            pubkey=pubkey,
            node_info=enriched_node_info,
            recommendations=recommendations,
            context=request.context.value,
            goals=[goal.value for goal in request.goals],
            max_actions=request.max_actions
        )
        
        if priority_response.get("error"):
            raise HTTPException(status_code=503, detail="Service Anthropic temporairement indisponible")
        
        # Filtrage par budget si spécifié
        actions = priority_response.get("actions", [])
        if request.budget_limit:
            actions = [
                action for action in actions 
                if not action.get("estimated_cost") or action["estimated_cost"] <= request.budget_limit
            ]
        
        # Filtrage par délai si spécifié
        if request.timeframe_preference:
            actions = [
                action for action in actions 
                if action.get("timeframe") == request.timeframe_preference.value
            ]
        
        response_data = {
            "pubkey": pubkey,
            "priority_actions": actions,
            "openai_analysis": priority_response.get("analysis", ""),
            "key_metrics": priority_response.get("key_metrics", []),
            "generated_at": datetime.utcnow(),
            "model_used": anthropic_client.model
        }
        
        # Tâche en arrière-plan pour logging
        background_tasks.add_task(
            _log_priority_request, 
            pubkey, 
            request.dict(), 
            len(actions)
        )
        
        response_time = (datetime.utcnow() - start_time).total_seconds()
        await update_metrics("priorities", response_time, True)
        
        return PriorityActionsResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la génération des priorités pour {pubkey}: {str(e)}")
        response_time = (datetime.utcnow() - start_time).total_seconds()
        await update_metrics("priorities", response_time, False)
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@router.post("/nodes/bulk-analysis", response_model=BulkAnalysisResponse)
async def bulk_node_analysis(request: BulkAnalysisRequest):
    """Analyse en masse de plusieurs nœuds"""
    start_time = datetime.utcnow()
    
    try:
        results = []
        errors = []
        
        # Traitement en parallèle par batches de 10
        batch_size = 10
        for i in range(0, len(request.pubkeys), batch_size):
            batch = request.pubkeys[i:i+batch_size]
            
            # Création des tâches pour le batch
            tasks = []
            for pubkey in batch:
                if request.use_cache:
                    task = _get_cached_or_fetch_node_info(pubkey)
                else:
                    task = sparkseer_client.get_node_info(pubkey)
                tasks.append((pubkey, task))
            
            # Exécution du batch
            batch_results = await asyncio.gather(
                *[task[1] for task in tasks], 
                return_exceptions=True
            )
            
            # Traitement des résultats
            for j, (pubkey, _) in enumerate(tasks):
                result = batch_results[j]
                
                if isinstance(result, Exception):
                    errors.append({
                        "pubkey": pubkey,
                        "error": str(result)
                    })
                elif result:
                    try:
                        response_data = {
                            "pubkey": pubkey,
                            "node_info": result.get("node_info", {}),
                            "metrics": result.get("metrics", {}),
                            "channels": result.get("channels", []),
                            "network_position": result.get("network_position", {}),
                            "timestamp": datetime.utcnow(),
                            "source": result.get("source", "sparkseer"),
                            "cache_hit": result.get("cache_hit", False)
                        }
                        results.append(NodeInfoResponse(**response_data))
                    except Exception as e:
                        errors.append({
                            "pubkey": pubkey,
                            "error": f"Erreur de traitement: {str(e)}"
                        })
                else:
                    errors.append({
                        "pubkey": pubkey,
                        "error": "Nœud non trouvé"
                    })
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return BulkAnalysisResponse(
            total_analyzed=len(request.pubkeys),
            successful=len(results),
            failed=len(errors),
            results=results,
            errors=errors,
            processing_time_seconds=processing_time
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse en masse: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@router.get("/metrics", response_model=PerformanceMetrics)
async def get_performance_metrics():
    """Retourne les métriques de performance de l'API"""
    # Mise à jour du cache hit ratio
    cache_stats = await cache_manager.get_stats()
    if isinstance(cache_stats, dict) and "redis_info" in cache_stats:
        performance_metrics.cache_hit_ratio = cache_stats["redis_info"].get("hit_ratio", 0.0)
    
    return performance_metrics

# === Fonctions utilitaires ===

async def _test_cache_connection() -> bool:
    """Test de connexion au cache Redis"""
    try:
        test_key = "health_check_test"
        await cache_manager.set(test_key, {"test": True}, ttl=10)
        result = await cache_manager.get(test_key)
        await cache_manager.delete(test_key)
        return result is not None
    except:
        return False

async def _test_lnbits_connection() -> bool:
    """Test de connexion à LNBits"""
    try:
        wallet_info = await lnbits_client.get_wallet_info()
        return wallet_info is not None
    except:
        return False

async def _get_local_node_data(pubkey: str) -> dict:
    """Récupère les données locales du nœud depuis LNBits"""
    try:
        # Vérifier si c'est notre nœud local
        wallet_info = await lnbits_client.get_wallet_info()
        if wallet_info and wallet_info.get("node_pubkey") == pubkey:
            return {
                "local_node": True,
                "wallet_balance": wallet_info.get("balance", 0),
                "local_channels": await lnbits_client.get_channels()
            }
    except Exception as e:
        logger.debug(f"Impossible de récupérer les données locales pour {pubkey}: {str(e)}")
    
    return {}

async def _get_cached_or_fetch_node_info(pubkey: str) -> dict:
    """Récupère les infos du nœud depuis le cache ou les sources"""
    cache_key = f"node_info:{pubkey}:True:False"
    
    cached_data = await cache_manager.get(cache_key, "node_info")
    if cached_data:
        cached_data["cache_hit"] = True
        return cached_data
    
    # Fallback vers Sparkseer
    node_data = await sparkseer_client.get_node_info(pubkey)
    if node_data:
        node_data["cache_hit"] = False
        await cache_manager.set(cache_key, node_data, data_type="node_info")
    
    return node_data or {}

async def _log_priority_request(pubkey: str, request_data: dict, actions_count: int):
    """Log les requêtes de priorités pour analytics"""
    try:
        log_data = {
            "pubkey": pubkey[:16] + "...",
            "context": request_data.get("context"),
            "goals": request_data.get("goals"),
            "actions_generated": actions_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        logger.info(f"Priority request: {log_data}")
    except Exception as e:
        logger.warning(f"Erreur lors du logging: {str(e)}") 