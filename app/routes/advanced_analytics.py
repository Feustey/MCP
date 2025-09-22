"""
Routes API pour les analyses avancées Lightning Network
Max Flow, Graph Theory, Financial Analysis
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from app.services.auth import verify_api_key
from src.lightning.max_flow_analysis import LightningMaxFlowAnalyzer
from src.lightning.graph_theory_metrics import LightningGraphAnalyzer
from src.lightning.financial_analysis import LightningFinancialAnalyzer
from src.data.graph_data_manager import GraphDataManager

logger = logging.getLogger("mcp.advanced_analytics")
router = APIRouter()

# Instances globales des analyseurs
max_flow_analyzer = LightningMaxFlowAnalyzer()
graph_analyzer = LightningGraphAnalyzer()
financial_analyzer = LightningFinancialAnalyzer()
data_manager = GraphDataManager()

@router.get("/network-topology")
async def get_network_topology_analysis(api_key: str = Depends(verify_api_key)):
    """
    Analyse complète de la topologie du réseau Lightning
    """
    try:
        # Charger les données du réseau
        nodes, channels = await data_manager.get_network_data()
        
        # Construire le graphe
        graph_analyzer.build_graph(nodes, channels)
        max_flow_analyzer.build_network_graph(nodes, channels)
        
        # Calculer les métriques
        topology_metrics = graph_analyzer.calculate_network_topology_metrics()
        
        return {
            "success": True,
            "data": topology_metrics,
            "network_size": {
                "nodes": len(nodes),
                "channels": len(channels)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur analyse topologie réseau: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/max-flow-analysis/{source_node}/{target_node}")
async def analyze_max_flow(
    source_node: str,
    target_node: str,
    payment_amount: Optional[int] = Query(None, description="Montant du paiement en satoshis"),
    api_key: str = Depends(verify_api_key)
):
    """
    Analyse Max Flow entre deux nœuds pour probabilité de succès des paiements
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
            "data": flow_result,
            "source_node": source_node[:16] + "...",
            "target_node": target_node[:16] + "...",
            "payment_amount": payment_amount
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse max flow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payment-probability/{source_node}/{target_node}")
async def analyze_payment_probability(
    source_node: str,
    target_node: str,
    amounts: str = Query(..., description="Montants séparés par des virgules (ex: 1000,5000,10000)"),
    api_key: str = Depends(verify_api_key)
):
    """
    Analyse de probabilité de succès pour différents montants de paiement
    """
    try:
        # Parser les montants
        amount_list = [int(x.strip()) for x in amounts.split(",")]
        
        # Charger les données et construire le graphe
        nodes, channels = await data_manager.get_network_data()
        max_flow_analyzer.build_network_graph(nodes, channels)
        
        # Analyser les probabilités
        probability_result = max_flow_analyzer.analyze_payment_probability(
            source_node, target_node, amount_list
        )
        
        return {
            "success": True,
            "data": probability_result,
            "source_node": source_node[:16] + "...",
            "target_node": target_node[:16] + "...",
            "tested_amounts": amount_list
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Format des montants invalide: {str(e)}")
    except Exception as e:
        logger.error(f"Erreur analyse probabilité paiement: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/centrality-metrics")
async def get_centrality_metrics(
    node_pubkey: Optional[str] = Query(None, description="Analyse pour un nœud spécifique"),
    api_key: str = Depends(verify_api_key)
):
    """
    Calcule les métriques de centralité (degree, betweenness, closeness, eigenvector)
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
            "data": centrality_result,
            "analysis_scope": "single_node" if node_pubkey else "full_network",
            "node_analyzed": node_pubkey[:16] + "..." if node_pubkey else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur métriques centralité: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hubness-analysis")
async def get_hubness_analysis(
    top_n: int = Query(50, description="Nombre de top hubs à retourner"),
    api_key: str = Depends(verify_api_key)
):
    """
    Analyse des hubs du réseau - identification des nœuds centraux
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
            "data": hubness_result,
            "top_hubs_count": top_n
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse hubness: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hopness-analysis")
async def get_hopness_analysis(
    sample_size: int = Query(1000, description="Taille de l'échantillon pour l'analyse"),
    source_nodes: Optional[str] = Query(None, description="Nœuds sources spécifiques (séparés par des virgules)"),
    api_key: str = Depends(verify_api_key)
):
    """
    Analyse hopness - efficacité de routage par distance
    """
    try:
        # Parser les nœuds sources si fournis
        source_list = None
        if source_nodes:
            source_list = [x.strip() for x in source_nodes.split(",")]
        
        # Charger les données du réseau
        nodes, channels = await data_manager.get_network_data()
        graph_analyzer.build_graph(nodes, channels)
        
        # Calculer les métriques de hopness
        hopness_result = graph_analyzer.calculate_hopness_metrics(source_list, sample_size)
        
        if "error" in hopness_result:
            raise HTTPException(status_code=400, detail=hopness_result["error"])
        
        return {
            "success": True,
            "data": hopness_result,
            "sample_size_used": sample_size
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse hopness: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/node-positioning/{node_pubkey}")
async def analyze_node_positioning(
    node_pubkey: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Analyse complète de la position d'un nœud dans le réseau
    """
    try:
        # Charger les données du réseau
        nodes, channels = await data_manager.get_network_data()
        graph_analyzer.build_graph(nodes, channels)
        
        # Analyser le positionnement
        positioning_result = graph_analyzer.analyze_node_positioning(node_pubkey)
        
        if "error" in positioning_result:
            raise HTTPException(status_code=400, detail=positioning_result["error"])
        
        return {
            "success": True,
            "data": positioning_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse positionnement: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/liquidity-analysis/{node_pubkey}")
async def analyze_node_liquidity(
    node_pubkey: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Analyse de liquidité et recommandations de rééquilibrage
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
        
        return {
            "success": True,
            "data": {
                "liquidity_analysis": liquidity_analysis,
                "rebalancing_recommendations": rebalancing_recs
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse liquidité: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/financial-analysis/{node_pubkey}")
async def analyze_node_financials(
    node_pubkey: str,
    timeframe_days: int = Query(30, description="Période d'analyse en jours"),
    btc_price_usd: Optional[float] = Query(None, description="Prix BTC en USD pour conversions"),
    api_key: str = Depends(verify_api_key)
):
    """
    Analyse financière complète d'un nœud
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
            "data": financial_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse financière: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fee-optimization/{node_pubkey}")
async def optimize_node_fees(
    node_pubkey: str,
    target_metrics: Optional[Dict[str, float]] = None,
    api_key: str = Depends(verify_api_key)
):
    """
    Optimisation de la structure tarifaire d'un nœud
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
            "data": optimization_result,
            "node_pubkey": node_pubkey[:16] + "..."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur optimisation frais: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/liquidity-efficiency/{node_pubkey}")
async def analyze_liquidity_efficiency(
    node_pubkey: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Analyse de l'efficacité de la liquidité d'un nœud
    """
    try:
        # Obtenir les canaux du nœud
        node_channels = await data_manager.get_node_channels(node_pubkey)
        if not node_channels:
            raise HTTPException(status_code=404, detail="Nœud non trouvé ou sans canaux")
        
        # Analyser l'efficacité
        efficiency_result = financial_analyzer.analyze_liquidity_efficiency(node_channels)
        
        if "error" in efficiency_result:
            raise HTTPException(status_code=400, detail=efficiency_result["error"])
        
        return {
            "success": True,
            "data": efficiency_result,
            "node_pubkey": node_pubkey[:16] + "..."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse efficacité liquidité: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/revenue-projections/{node_pubkey}")
async def project_revenue_scenarios(
    node_pubkey: str,
    scenarios: List[Dict[str, Any]],
    api_key: str = Depends(verify_api_key)
):
    """
    Projections de revenus selon différents scénarios
    """
    try:
        # Obtenir les métriques actuelles du nœud
        node_channels = await data_manager.get_node_channels(node_pubkey)
        payment_history = await data_manager.get_payment_history(node_pubkey, 30)
        
        current_metrics = financial_analyzer.analyze_node_financials(
            node_pubkey, node_channels, payment_history, 30
        )
        
        if "error" in current_metrics:
            raise HTTPException(status_code=400, detail=current_metrics["error"])
        
        # Calculer les projections
        projections = financial_analyzer.project_revenue_scenarios(
            current_metrics, scenarios
        )
        
        if "error" in projections:
            raise HTTPException(status_code=400, detail=projections["error"])
        
        return {
            "success": True,
            "data": projections,
            "node_pubkey": node_pubkey[:16] + "...",
            "scenarios_analyzed": len(scenarios)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur projections revenus: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/competitive-analysis/{node_pubkey}")
async def analyze_competitive_position(
    node_pubkey: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Analyse concurrentielle des frais et performance
    """
    try:
        # Obtenir les canaux du nœud
        node_channels = await data_manager.get_node_channels(node_pubkey)
        if not node_channels:
            raise HTTPException(status_code=404, detail="Nœud non trouvé ou sans canaux")
        
        # Obtenir les données du marché pour comparaison
        market_data = await data_manager.get_market_fee_data()
        
        # Analyser la position concurrentielle
        competitive_result = financial_analyzer.calculate_competitive_analysis(
            node_channels, market_data
        )
        
        if "error" in competitive_result:
            raise HTTPException(status_code=400, detail=competitive_result["error"])
        
        return {
            "success": True,
            "data": competitive_result,
            "node_pubkey": node_pubkey[:16] + "..."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse concurrentielle: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))