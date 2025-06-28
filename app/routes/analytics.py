#!/usr/bin/env python3
"""
Routes d'analytics pour l'API MCP
Endpoints pour l'analyse DazFlow Index et autres métriques avancées

Dernière mise à jour: 7 mai 2025
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from app.services.lnbits import LNBitsService
from src.analytics import DazFlowCalculator, DazFlowAnalysis, ReliabilityCurve

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/dazflow/node/{node_id}")
async def get_dazflow_analysis(
    node_id: str,
    lnbits_service: LNBitsService = Depends()
) -> Dict[str, Any]:
    """
    Analyse complète de l'indice DazFlow d'un nœud.
    
    Args:
        node_id: Identifiant du nœud à analyser
        
    Returns:
        Analyse DazFlow complète avec métriques et recommandations
    """
    try:
        logger.info(f"Analyse DazFlow Index demandée pour le nœud {node_id}")
        
        # Récupérer les données du nœud
        node_data = await lnbits_service.get_node_data(node_id)
        if not node_data:
            raise HTTPException(status_code=404, detail="Nœud non trouvé")
        
        # Calculer l'analyse DazFlow
        calculator = DazFlowCalculator()
        analysis = calculator.analyze_dazflow_index(node_data)
        
        if not analysis:
            raise HTTPException(status_code=500, detail="Erreur lors de l'analyse")
        
        return {
            "node_id": analysis.node_id,
            "timestamp": analysis.timestamp.isoformat(),
            "dazflow_index": round(analysis.dazflow_index, 4),
            "liquidity_efficiency": round(analysis.liquidity_efficiency, 4),
            "network_centrality": round(analysis.network_centrality, 4),
            "payment_analysis": {
                "amounts": analysis.payment_amounts,
                "success_probabilities": [round(p, 4) for p in analysis.success_probabilities]
            },
            "bottlenecks": {
                "count": len(analysis.bottleneck_channels),
                "channel_ids": analysis.bottleneck_channels
            },
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse DazFlow: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/dazflow/reliability-curve/{node_id}")
async def get_reliability_curve(
    node_id: str,
    amounts: Optional[str] = None,
    lnbits_service: LNBitsService = Depends()
) -> Dict[str, Any]:
    """
    Génère la courbe de fiabilité des paiements pour un nœud.
    
    Args:
        node_id: Identifiant du nœud
        amounts: Montants à tester (format: "1000,10000,100000")
        
    Returns:
        Courbe de fiabilité avec probabilités et recommandations
    """
    try:
        logger.info(f"Courbe de fiabilité demandée pour le nœud {node_id}")
        
        # Parser les montants
        if amounts:
            target_amounts = [int(x.strip()) for x in amounts.split(",")]
        else:
            target_amounts = [1000, 10000, 100000, 1000000, 10000000]
        
        # Récupérer les données du nœud
        node_data = await lnbits_service.get_node_data(node_id)
        if not node_data:
            raise HTTPException(status_code=404, detail="Nœud non trouvé")
        
        # Générer la courbe
        calculator = DazFlowCalculator()
        curve = calculator.generate_reliability_curve(node_data, target_amounts)
        
        return {
            "node_id": node_id,
            "amounts": curve.amounts,
            "probabilities": [round(p, 4) for p in curve.probabilities],
            "confidence_intervals": [
                [round(low, 4), round(high, 4)] 
                for low, high in curve.confidence_intervals
            ],
            "recommended_amounts": curve.recommended_amounts,
            "analysis": {
                "high_reliability_count": len(curve.recommended_amounts),
                "average_probability": round(sum(curve.probabilities) / len(curve.probabilities), 4),
                "max_reliable_amount": max(curve.recommended_amounts) if curve.recommended_amounts else 0
            },
            "status": "success"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Format de montants invalide")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur courbe fiabilité: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/dazflow/bottlenecks/{node_id}")
async def get_bottlenecks(
    node_id: str,
    lnbits_service: LNBitsService = Depends()
) -> Dict[str, Any]:
    """
    Identifie les goulots d'étranglement de liquidité d'un nœud.
    
    Args:
        node_id: Identifiant du nœud
        
    Returns:
        Liste des goulots d'étranglement avec analyses détaillées
    """
    try:
        logger.info(f"Analyse des goulots demandée pour le nœud {node_id}")
        
        # Récupérer les données du nœud
        node_data = await lnbits_service.get_node_data(node_id)
        if not node_data:
            raise HTTPException(status_code=404, detail="Nœud non trouvé")
        
        # Identifier les goulots
        calculator = DazFlowCalculator()
        bottlenecks = calculator.identify_bottlenecks(node_data)
        
        return {
            "node_id": node_id,
            "bottlenecks": bottlenecks,
            "summary": {
                "total_bottlenecks": len(bottlenecks),
                "high_severity": len([b for b in bottlenecks if b["severity"] == "high"]),
                "medium_severity": len([b for b in bottlenecks if b["severity"] == "medium"]),
                "most_common_issue": self._get_most_common_issue(bottlenecks)
            },
            "recommendations": self._generate_bottleneck_recommendations(bottlenecks),
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse goulots: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/dazflow/network-health")
async def get_network_health(
    lnbits_service: LNBitsService = Depends()
) -> Dict[str, Any]:
    """
    Évalue la santé globale du réseau Lightning.
    
    Returns:
        Métriques de santé du réseau basées sur l'analyse DazFlow
    """
    try:
        logger.info("Analyse de santé du réseau demandée")
        
        # Récupérer les données de plusieurs nœuds
        nodes_data = await lnbits_service.get_network_data()
        
        if not nodes_data:
            raise HTTPException(status_code=500, detail="Impossible de récupérer les données réseau")
        
        # Analyser chaque nœud
        calculator = DazFlowCalculator()
        analyses = []
        
        for node_data in nodes_data[:10]:  # Limiter à 10 nœuds pour les performances
            analysis = calculator.analyze_dazflow_index(node_data)
            if analysis:
                analyses.append(analysis)
        
        if not analyses:
            raise HTTPException(status_code=500, detail="Aucune analyse valide générée")
        
        # Calculer les métriques globales
        avg_dazflow = sum(a.dazflow_index for a in analyses) / len(analyses)
        avg_efficiency = sum(a.liquidity_efficiency for a in analyses) / len(analyses)
        avg_centrality = sum(a.network_centrality for a in analyses) / len(analyses)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "nodes_analyzed": len(analyses),
            "network_metrics": {
                "average_dazflow_index": round(avg_dazflow, 4),
                "average_liquidity_efficiency": round(avg_efficiency, 4),
                "average_network_centrality": round(avg_centrality, 4),
                "health_score": round((avg_dazflow + avg_efficiency + avg_centrality) / 3, 4)
            },
            "health_status": self._get_health_status(avg_dazflow),
            "recommendations": self._get_network_recommendations(analyses),
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse santé réseau: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.post("/dazflow/optimize-liquidity/{node_id}")
async def optimize_liquidity(
    node_id: str,
    target_amount: int,
    lnbits_service: LNBitsService = Depends()
) -> Dict[str, Any]:
    """
    Optimise la liquidité d'un nœud basée sur l'analyse DazFlow.
    
    Args:
        node_id: Identifiant du nœud
        target_amount: Montant cible pour l'optimisation
        
    Returns:
        Recommandations d'optimisation de liquidité
    """
    try:
        logger.info(f"Optimisation liquidité demandée pour le nœud {node_id}")
        
        # Récupérer les données du nœud
        node_data = await lnbits_service.get_node_data(node_id)
        if not node_data:
            raise HTTPException(status_code=404, detail="Nœud non trouvé")
        
        # Analyser la situation actuelle
        calculator = DazFlowCalculator()
        current_analysis = calculator.analyze_dazflow_index(node_data)
        
        if not current_analysis:
            raise HTTPException(status_code=500, detail="Erreur lors de l'analyse")
        
        # Générer les recommandations
        recommendations = self._generate_liquidity_recommendations(
            node_data, current_analysis, target_amount
        )
        
        return {
            "node_id": node_id,
            "target_amount": target_amount,
            "current_dazflow_index": round(current_analysis.dazflow_index, 4),
            "current_liquidity_efficiency": round(current_analysis.liquidity_efficiency, 4),
            "recommendations": recommendations,
            "estimated_improvement": self._estimate_improvement(current_analysis, recommendations),
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur optimisation liquidité: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

def _get_most_common_issue(bottlenecks: List[Dict[str, Any]]) -> str:
    """Trouve le problème le plus commun dans les goulots d'étranglement"""
    issue_counts = {}
    for bottleneck in bottlenecks:
        for issue in bottleneck.get("issues", []):
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
    
    if not issue_counts:
        return "aucun_problème"
    
    return max(issue_counts, key=issue_counts.get)

def _generate_bottleneck_recommendations(bottlenecks: List[Dict[str, Any]]) -> List[str]:
    """Génère des recommandations basées sur les goulots d'étranglement"""
    recommendations = []
    
    high_severity = [b for b in bottlenecks if b["severity"] == "high"]
    if high_severity:
        recommendations.append("Priorité haute: Rééquilibrer les canaux avec déséquilibre > 80%")
    
    imbalance_issues = [b for b in bottlenecks if "déséquilibre_liquidité" in b.get("issues", [])]
    if len(imbalance_issues) > len(bottlenecks) * 0.5:
        recommendations.append("Stratégie globale: Rééquilibrer l'ensemble des canaux")
    
    low_liquidity = [b for b in bottlenecks if "liquidité_sortante_faible" in b.get("issues", [])]
    if low_liquidity:
        recommendations.append("Augmenter la liquidité sortante sur les canaux identifiés")
    
    return recommendations

def _get_health_status(avg_dazflow: float) -> str:
    """Détermine le statut de santé basé sur l'indice DazFlow moyen"""
    if avg_dazflow >= 0.8:
        return "excellent"
    elif avg_dazflow >= 0.6:
        return "bon"
    elif avg_dazflow >= 0.4:
        return "modéré"
    else:
        return "critique"

def _get_network_recommendations(analyses: List[DazFlowAnalysis]) -> List[str]:
    """Génère des recommandations pour le réseau global"""
    recommendations = []
    
    low_efficiency_nodes = [a for a in analyses if a.liquidity_efficiency < 0.5]
    if low_efficiency_nodes:
        recommendations.append(f"Optimiser l'efficacité de {len(low_efficiency_nodes)} nœuds")
    
    low_centrality_nodes = [a for a in analyses if a.network_centrality < 0.3]
    if low_centrality_nodes:
        recommendations.append("Améliorer la connectivité des nœuds périphériques")
    
    return recommendations

def _generate_liquidity_recommendations(
    node_data: Dict[str, Any], 
    analysis: DazFlowAnalysis, 
    target_amount: int
) -> List[Dict[str, Any]]:
    """Génère des recommandations d'optimisation de liquidité"""
    recommendations = []
    channels = node_data.get("channels", [])
    
    # Analyser chaque canal
    for channel in channels:
        capacity = channel.get("capacity", 0)
        local_balance = channel.get("local_balance", 0)
        remote_balance = channel.get("remote_balance", 0)
        
        if capacity == 0:
            continue
        
        imbalance = abs(local_balance - remote_balance) / capacity
        
        if imbalance > 0.3:
            action = "réduire" if local_balance > remote_balance else "augmenter"
            amount = int(abs(local_balance - remote_balance) * 0.5)
            
            recommendations.append({
                "channel_id": channel.get("channel_id"),
                "peer_alias": channel.get("peer_alias"),
                "action": f"{action}_liquidité",
                "amount": amount,
                "priority": "high" if imbalance > 0.5 else "medium",
                "reason": f"Déséquilibre de {imbalance:.1%}"
            })
    
    return recommendations

def _estimate_improvement(
    current_analysis: DazFlowAnalysis, 
    recommendations: List[Dict[str, Any]]
) -> Dict[str, float]:
    """Estime l'amélioration attendue après optimisation"""
    high_priority = len([r for r in recommendations if r["priority"] == "high"])
    medium_priority = len([r for r in recommendations if r["priority"] == "medium"])
    
    estimated_dazflow_improvement = min(0.2, (high_priority * 0.05 + medium_priority * 0.02))
    estimated_efficiency_improvement = min(0.15, (high_priority * 0.04 + medium_priority * 0.015))
    
    return {
        "dazflow_index_improvement": round(estimated_dazflow_improvement, 4),
        "liquidity_efficiency_improvement": round(estimated_efficiency_improvement, 4),
        "confidence": "high" if high_priority > 0 else "medium"
    } 