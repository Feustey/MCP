from fastapi import APIRouter, HTTPException, Depends, Header, Query
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from pydantic import BaseModel, Field

from app.services.lnbits import LNbitsService
from app.auth import verify_jwt_and_get_tenant
from app.services.auth import verify_api_key
from src.lightning.max_flow_analysis import LightningMaxFlowAnalyzer
from src.lightning.graph_theory_metrics import LightningGraphAnalyzer
from src.lightning.financial_analysis import LightningFinancialAnalyzer
from src.data.graph_data_manager import GraphDataManager

logger = logging.getLogger("mcp.lightning_routes")
router = APIRouter(prefix="/lightning", tags=["Lightning Network"])

# Initialize analyzers
max_flow_analyzer = LightningMaxFlowAnalyzer()
graph_analyzer = LightningGraphAnalyzer()
financial_analyzer = LightningFinancialAnalyzer()
data_manager = GraphDataManager()

@router.get("/explorer/nodes")
async def get_explorer_nodes(
    authorization: str = Header(..., alias="Authorization")
):
    """Récupère la liste des nœuds du réseau Lightning."""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    lnbits_service = LNbitsService()
    return await lnbits_service.get_network_nodes()

@router.get("/rankings")
async def get_rankings(
    authorization: str = Header(..., alias="Authorization")
):
    """Récupère les classements des nœuds Lightning."""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    lnbits_service = LNbitsService()
    return await lnbits_service.get_node_rankings()

@router.get("/network/global-stats")
async def get_global_stats(
    authorization: str = Header(..., alias="Authorization")
):
    """Récupère les statistiques globales du réseau Lightning."""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    lnbits_service = LNbitsService()
    return await lnbits_service.get_network_stats()

@router.get("/calculator")
async def get_calculator(
    authorization: str = Header(..., alias="Authorization")
):
    """Calculateur de frais Lightning."""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    lnbits_service = LNbitsService()
    return await lnbits_service.get_fee_calculator()

@router.get("/decoder")
async def get_decoder(
    authorization: str = Header(..., alias="Authorization")
):
    """Décodeur d'objets Lightning (factures, etc.)."""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    lnbits_service = LNbitsService()
    return await lnbits_service.get_decoder()

# ============================================================================
# NOUVEAUX ENDPOINTS AVEC FONCTIONNALITÉS AVANCÉES
# ============================================================================

@router.get("/nodes/{node_pubkey}/enhanced-analysis",
    summary="Analyse complète d'un nœud",
    description="Analyse avancée incluant Max Flow, centralité, finances et recommandations",
    tags=["Lightning Network", "Max Flow Analysis", "Financial Analysis"],
    response_model=dict,
    responses={
        200: {
            "description": "Analyse complète réussie",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "node_pubkey": "02b1fe652cfc...",
                        "enhanced_analysis": {
                            "liquidity_analysis": {"outbound_liquidity": 399549854},
                            "network_positioning": {"centrality_metrics": {"degree_centrality": 0.162}},
                            "financial_metrics": {"annual_roi_percent": 12.5}
                        }
                    }
                }
            }
        },
        404: {"description": "Nœud non trouvé"},
        500: {"description": "Erreur d'analyse"}
    }
)
async def get_node_enhanced_analysis(
    node_pubkey: str,
    api_key: str = Depends(verify_api_key)
):
    """
    **Analyse complète et avancée d'un nœud Lightning Network**
    
    Cette endpoint fournit une analyse 360° d'un nœud incluant :
    - **Max Flow Analysis** : Liquidité et capacité de routage
    - **Centralité** : Position dans la topologie réseau  
    - **Finances** : ROI, revenus et optimisation tarifaire
    - **Recommandations** : Actions prioritaires d'amélioration
    
    Idéal pour les opérateurs souhaitant une vue d'ensemble des performances de leur nœud.
    """
    try:
        logger.info(f"Analyse avancée demandée pour le nœud: {node_pubkey}")
        
        # Charger les données du réseau
        nodes, channels = await data_manager.get_network_data()
        
        # Construire les graphes
        max_flow_analyzer.build_network_graph(nodes, channels)
        graph_analyzer.build_graph(nodes, channels)
        
        # Obtenir les canaux du nœud
        node_channels = await data_manager.get_node_channels(node_pubkey)
        
        # Analyse Max Flow - liquidité réseau
        liquidity_analysis = max_flow_analyzer.analyze_network_liquidity(node_pubkey)
        
        # Analyse positionnement dans le graphe
        positioning_analysis = graph_analyzer.analyze_node_positioning(node_pubkey)
        
        # Analyse financière si données disponibles
        financial_analysis = {}
        if node_channels:
            payment_history = await data_manager.get_payment_history(node_pubkey, 30)
            financial_analysis = financial_analyzer.analyze_node_financials(
                node_pubkey, node_channels, payment_history, 30
            )
        
        # Recommandations de rééquilibrage
        rebalancing_recs = max_flow_analyzer.recommend_liquidity_rebalancing(node_pubkey)
        
        return {
            "success": True,
            "node_pubkey": node_pubkey,
            "enhanced_analysis": {
                "liquidity_analysis": liquidity_analysis,
                "network_positioning": positioning_analysis,
                "financial_metrics": financial_analysis,
                "rebalancing_recommendations": rebalancing_recs,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Erreur analyse avancée pour {node_pubkey}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/max-flow/{source_node}/{target_node}",
    summary="Analyse Max Flow entre nœuds",
    description="Calcule la probabilité de succès d'un paiement entre deux nœuds",
    tags=["Max Flow Analysis"],
    response_model=dict,
    responses={
        200: {
            "description": "Analyse Max Flow réussie",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "max_flow_analysis": {
                            "max_flow_value": 15000000,
                            "success_probability": 0.95,
                            "flow_paths": [{"path": ["source", "intermediate", "target"], "flow_amount": 8000000, "hop_count": 2}]
                        }
                    }
                }
            }
        },
        400: {"description": "Paramètres invalides"},
        500: {"description": "Erreur de calcul"}
    }
)
async def calculate_max_flow_between_nodes(
    source_node: str,
    target_node: str,
    payment_amount: Optional[int] = Query(None, description="Montant du paiement en satoshis", gt=0),
    api_key: str = Depends(verify_api_key)
):
    """
    **Analyse Max Flow pour probabilité de succès des paiements**
    
    Calcule le flux maximum possible entre deux nœuds Lightning Network pour :
    - **Évaluer la probabilité** de succès d'un paiement
    - **Identifier les chemins** de routage optimaux
    - **Détecter les goulots** d'étranglement de liquidité
    
    Essentiel pour l'optimisation des paiements et la planification de liquidité.
    """
    try:
        # Charger les données du réseau
        nodes, channels = await data_manager.get_network_data()
        max_flow_analyzer.build_network_graph(nodes, channels)
        
        # Calculer le max flow
        flow_result = max_flow_analyzer.calculate_max_flow(source_node, target_node, payment_amount)
        
        if "error" in flow_result:
            raise HTTPException(status_code=400, detail=flow_result["error"])
        
        return {
            "success": True,
            "max_flow_analysis": flow_result,
            "source_node": source_node[:16] + "...",
            "target_node": target_node[:16] + "...",
            "payment_amount_tested": payment_amount
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur calcul max flow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payment-probability/{source_node}/{target_node}")
async def analyze_payment_success_probability(
    source_node: str,
    target_node: str,
    amounts: str = Query(..., description="Montants à tester séparés par des virgules (ex: 1000,5000,10000)"),
    api_key: str = Depends(verify_api_key)
):
    """
    Analyse la probabilité de succès des paiements pour différents montants
    """
    try:
        # Parser les montants
        amount_list = [int(x.strip()) for x in amounts.split(",")]
        
        # Charger les données du réseau
        nodes, channels = await data_manager.get_network_data()
        max_flow_analyzer.build_network_graph(nodes, channels)
        
        # Analyser les probabilités
        probability_result = max_flow_analyzer.analyze_payment_probability(
            source_node, target_node, amount_list
        )
        
        return {
            "success": True,
            "payment_probability_analysis": probability_result,
            "tested_amounts": amount_list,
            "source_node": source_node[:16] + "...",
            "target_node": target_node[:16] + "..."
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Format des montants invalide: {str(e)}")
    except Exception as e:
        logger.error(f"Erreur analyse probabilité: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/nodes/{node_pubkey}/centrality-metrics")
async def get_node_centrality_metrics(
    node_pubkey: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Calcule les métriques de centralité d'un nœud (degree, betweenness, closeness, eigenvector)
    """
    try:
        # Charger les données du réseau
        nodes, channels = await data_manager.get_network_data()
        graph_analyzer.build_graph(nodes, channels)
        
        # Calculer les métriques de centralité
        centrality_result = graph_analyzer.calculate_centrality_metrics(node_pubkey)
        
        if "error" in centrality_result:
            raise HTTPException(status_code=400, detail=centrality_result["error"])
        
        return {
            "success": True,
            "node_pubkey": node_pubkey,
            "centrality_metrics": centrality_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur métriques centralité: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/nodes/{node_pubkey}/financial-analysis")
async def get_node_financial_analysis(
    node_pubkey: str,
    timeframe_days: int = Query(30, description="Période d'analyse en jours"),
    btc_price_usd: Optional[float] = Query(None, description="Prix BTC en USD pour conversions"),
    api_key: str = Depends(verify_api_key)
):
    """
    Analyse financière complète d'un nœud Lightning
    """
    try:
        # Mettre à jour le prix BTC si fourni
        if btc_price_usd:
            financial_analyzer.set_btc_price(btc_price_usd)
        
        # Obtenir les données des canaux du nœud
        node_channels = await data_manager.get_node_channels(node_pubkey)
        if not node_channels:
            raise HTTPException(status_code=404, detail="Nœud non trouvé ou sans canaux")
        
        # Obtenir l'historique des paiements si disponible
        payment_history = await data_manager.get_payment_history(node_pubkey, timeframe_days)
        
        # Analyser les finances
        financial_result = financial_analyzer.analyze_node_financials(
            node_pubkey, node_channels, payment_history, timeframe_days
        )
        
        if "error" in financial_result:
            raise HTTPException(status_code=400, detail=financial_result["error"])
        
        return {
            "success": True,
            "financial_analysis": financial_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse financière: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/nodes/{node_pubkey}/optimize-fees")
async def optimize_node_fee_structure(
    node_pubkey: str,
    target_metrics: Optional[Dict[str, float]] = None,
    api_key: str = Depends(verify_api_key)
):
    """
    Optimise la structure tarifaire d'un nœud pour maximiser les revenus
    """
    try:
        # Obtenir les canaux du nœud
        node_channels = await data_manager.get_node_channels(node_pubkey)
        if not node_channels:
            raise HTTPException(status_code=404, detail="Nœud non trouvé ou sans canaux")
        
        # Optimiser la structure tarifaire
        optimization_result = financial_analyzer.optimize_fee_structure(node_channels, target_metrics)
        
        if "error" in optimization_result:
            raise HTTPException(status_code=400, detail=optimization_result["error"])
        
        return {
            "success": True,
            "node_pubkey": node_pubkey[:16] + "...",
            "fee_optimization": optimization_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur optimisation frais: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/nodes/{node_pubkey}/liquidity-recommendations")
async def get_liquidity_recommendations(
    node_pubkey: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Recommandations de gestion de liquidité et rééquilibrage
    """
    try:
        # Charger les données du réseau
        nodes, channels = await data_manager.get_network_data()
        max_flow_analyzer.build_network_graph(nodes, channels)
        
        # Analyser la liquidité
        liquidity_analysis = max_flow_analyzer.analyze_network_liquidity(node_pubkey)
        
        if "error" in liquidity_analysis:
            raise HTTPException(status_code=400, detail=liquidity_analysis["error"])
        
        # Recommandations de rééquilibrage
        rebalancing_recs = max_flow_analyzer.recommend_liquidity_rebalancing(node_pubkey)
        
        # Analyse d'efficacité des canaux
        node_channels = await data_manager.get_node_channels(node_pubkey)
        efficiency_analysis = {}
        if node_channels:
            efficiency_analysis = financial_analyzer.analyze_liquidity_efficiency(node_channels)
        
        return {
            "success": True,
            "node_pubkey": node_pubkey[:16] + "...",
            "liquidity_analysis": liquidity_analysis,
            "rebalancing_recommendations": rebalancing_recs,
            "efficiency_analysis": efficiency_analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur recommandations liquidité: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/network/topology-analysis")
async def get_network_topology_analysis(
    api_key: str = Depends(verify_api_key)
):
    """
    Analyse complète de la topologie du réseau Lightning Network
    """
    try:
        # Charger les données du réseau
        nodes, channels = await data_manager.get_network_data()
        graph_analyzer.build_graph(nodes, channels)
        
        # Calculer les métriques de topologie
        topology_metrics = graph_analyzer.calculate_network_topology_metrics()
        
        return {
            "success": True,
            "network_topology": topology_metrics,
            "network_size": {
                "nodes": len(nodes),
                "channels": len(channels)
            }
        }
        
    except Exception as e:
        logger.error(f"Erreur analyse topologie: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/network/hub-analysis")
async def get_network_hub_analysis(
    top_n: int = Query(50, description="Nombre de top hubs à analyser"),
    api_key: str = Depends(verify_api_key)
):
    """
    Analyse des hubs du réseau Lightning - identification des nœuds centraux
    """
    try:
        # Charger les données du réseau
        nodes, channels = await data_manager.get_network_data()
        graph_analyzer.build_graph(nodes, channels)
        
        # Calculer les métriques de hubness
        hubness_result = graph_analyzer.calculate_hubness_metrics(top_n)
        
        if "error" in hubness_result:
            raise HTTPException(status_code=400, detail=hubness_result["error"])
        
        return {
            "success": True,
            "hub_analysis": hubness_result,
            "analysis_scope": f"Top {top_n} hubs"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse hubs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/nodes/{node_pubkey}/performance-score",
    summary="Score de performance composite",
    description="Score 0-100 basé sur centralité, liquidité et performance financière",
    tags=["Performance Scoring"],
    response_model=dict,
    responses={
        200: {
            "description": "Score de performance calculé",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "performance_analysis": {
                            "overall_score": 78.5,
                            "ranking_category": "major_hub",
                            "score_breakdown": {
                                "connectivity_score": 82.0,
                                "routing_efficiency": 75.0,
                                "liquidity_management": 78.0
                            },
                            "improvement_areas": ["Améliorer le positionnement pour le routage"]
                        }
                    }
                }
            }
        }
    }
)
async def get_node_performance_score(
    node_pubkey: str,
    api_key: str = Depends(verify_api_key)
):
    """
    **Score de performance composite d'un nœud Lightning**
    
    Génère un score 0-100 basé sur :
    - **Connectivité** : Position dans la topologie réseau
    - **Efficacité de routage** : Capacité à router des paiements
    - **Gestion de liquidité** : Optimisation de la distribution des fonds
    - **Performance financière** : ROI et génération de revenus
    
    Permet de comparer objectivement les performances entre nœuds.
    """
    try:
        # Charger les données du réseau
        nodes, channels = await data_manager.get_network_data()
        
        # Construire les graphes
        max_flow_analyzer.build_network_graph(nodes, channels)
        graph_analyzer.build_graph(nodes, channels)
        
        # Métriques de centralité
        centrality = graph_analyzer.calculate_centrality_metrics(node_pubkey)
        if "error" in centrality:
            raise HTTPException(status_code=400, detail=centrality["error"])
        
        # Métriques de liquidité
        liquidity = max_flow_analyzer.analyze_network_liquidity(node_pubkey)
        if "error" in liquidity:
            raise HTTPException(status_code=400, detail=liquidity["error"])
        
        # Score composite
        performance_score = {
            "overall_score": _calculate_composite_score(centrality, liquidity),
            "centrality_metrics": centrality,
            "liquidity_metrics": liquidity,
            "score_breakdown": _breakdown_performance_score(centrality, liquidity),
            "ranking_category": _categorize_node_performance(centrality, liquidity),
            "improvement_areas": _identify_improvement_areas(centrality, liquidity)
        }
        
        return {
            "success": True,
            "node_pubkey": node_pubkey[:16] + "...",
            "performance_analysis": performance_score
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur score performance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# FONCTIONS UTILITAIRES POUR L'ANALYSE DE PERFORMANCE
# ============================================================================

def _calculate_composite_score(centrality_metrics: Dict, liquidity_metrics: Dict) -> float:
    """Calcule un score composite de performance 0-100"""
    try:
        # Normaliser les métriques de centralité
        centrality_score = (
            centrality_metrics.get("degree_centrality", 0) * 0.3 +
            centrality_metrics.get("betweenness_centrality", 0) * 0.4 +
            centrality_metrics.get("closeness_centrality", 0) * 0.2 +
            centrality_metrics.get("eigenvector_centrality", 0) * 0.1
        )
        
        # Score de liquidité basé sur la distribution et l'efficacité
        liquidity_score = liquidity_metrics.get("liquidity_distribution_score", 0)
        
        # Score composite pondéré
        composite = (centrality_score * 0.6 + liquidity_score * 0.4) * 100
        return min(100.0, max(0.0, composite))
        
    except Exception:
        return 0.0

def _breakdown_performance_score(centrality_metrics: Dict, liquidity_metrics: Dict) -> Dict:
    """Détaille les composants du score de performance"""
    return {
        "connectivity_score": centrality_metrics.get("degree_centrality", 0) * 100,
        "routing_efficiency": centrality_metrics.get("betweenness_centrality", 0) * 100,  
        "network_closeness": centrality_metrics.get("closeness_centrality", 0) * 100,
        "liquidity_management": liquidity_metrics.get("liquidity_distribution_score", 0) * 100,
        "capital_efficiency": liquidity_metrics.get("average_reachability", 0) / 1000000 * 100  # Normalisation
    }

def _categorize_node_performance(centrality_metrics: Dict, liquidity_metrics: Dict) -> str:
    """Catégorise la performance du nœud"""
    composite_score = _calculate_composite_score(centrality_metrics, liquidity_metrics)
    
    if composite_score >= 80:
        return "elite_hub"
    elif composite_score >= 60:
        return "major_hub"
    elif composite_score >= 40:
        return "active_router"
    elif composite_score >= 20:
        return "developing_node"
    else:
        return "emerging_node"

def _identify_improvement_areas(centrality_metrics: Dict, liquidity_metrics: Dict) -> List[str]:
    """Identifie les domaines d'amélioration prioritaires"""
    improvements = []
    
    if centrality_metrics.get("degree_centrality", 0) < 0.1:
        improvements.append("Augmenter le nombre de connexions")
    
    if centrality_metrics.get("betweenness_centrality", 0) < 0.05:
        improvements.append("Améliorer le positionnement pour le routage")
    
    if liquidity_metrics.get("liquidity_distribution_score", 0) < 0.5:
        improvements.append("Optimiser la distribution de liquidité")
    
    if liquidity_metrics.get("average_reachability", 0) < 100000:
        improvements.append("Améliorer la connectivité vers les hubs majeurs")
    
    return improvements if improvements else ["Performance optimale dans toutes les catégories"] 