from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
import os
import logging
import asyncio

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import des services MCP
try:
    from app.services.ai_lightning_analysis import ai_analysis_service
    from app.services.redis_cache import cache_service
    AI_SERVICES_AVAILABLE = True
    logger.info("Services AI et cache chargés avec succès")
except ImportError as e:
    logger.warning(f"Services AI/cache non disponibles: {str(e)}")
    AI_SERVICES_AVAILABLE = False

app = FastAPI(
    title="MCP Lightning API",
    description="API pour le système MCP Lightning Network avec analyse de nœuds",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "status": "ok",
        "message": "MCP Lightning API is running",
        "version": "1.0.0",
        "mode": "production",
        "features": ["node_analysis", "recommendations", "scoring"]
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": "2025-01-07"}

@app.get("/api/v1/lightning/status")
def lightning_status():
    return {"lightning": "operational", "mock_mode": True}

# Nouveau endpoint pour analyse de nœud
@app.get("/api/v1/lightning/nodes/{node_id}/analysis")
async def analyze_node(
    node_id: str,
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """Analyse complète d'un nœud Lightning Network."""
    
    logger.info(f"Analyse demandée pour le nœud: {node_id}")
    
    # Validation de base de la clé publique
    if len(node_id) != 66 or not all(c in '0123456789abcdef' for c in node_id):
        raise HTTPException(status_code=400, detail="Format de node_id invalide")
    
    # Simulation d'analyse complète
    analysis_result = {
        "node_id": node_id,
        "analysis_timestamp": "2025-01-07T12:00:00Z",
        "basic_info": {
            "alias": f"Node_{node_id[:8]}",
            "color": "#3399ff",
            "public_key": node_id,
            "network": "mainnet"
        },
        "scores": {
            "overall_score": 7.2,
            "centrality_score": 6.8,
            "reliability_score": 8.1,
            "liquidity_score": 6.9,
            "connectivity_score": 7.5
        },
        "metrics": {
            "total_capacity": 150000000,  # 1.5 BTC en satoshis
            "channel_count": 12,
            "active_channels": 10,
            "avg_channel_size": 12500000,
            "uptime_percentage": 97.8,
            "success_rate": 94.2
        },
        "network_position": {
            "rank": 1247,
            "total_nodes": 15000,
            "percentile": 91.7,
            "degree_centrality": 0.00083,
            "betweenness_centrality": 0.00125
        },
        "recommendations": {
            "priority": "medium",
            "suggestions": [
                {
                    "type": "liquidity",
                    "title": "Améliorer la répartition de liquidité",
                    "description": "Rééquilibrer les canaux pour optimiser les capacités de routage",
                    "impact": "medium",
                    "difficulty": "low"
                },
                {
                    "type": "connectivity", 
                    "title": "Ouvrir des canaux avec des nœuds centraux",
                    "description": "Établir des connexions avec des nœuds à forte centralité",
                    "impact": "high",
                    "difficulty": "medium"
                },
                {
                    "type": "fees",
                    "title": "Optimiser la politique de frais",
                    "description": "Ajuster les frais pour améliorer le taux de routage",
                    "impact": "medium",
                    "difficulty": "low"
                }
            ]
        },
        "optimal_channels": [
            {
                "target_node": "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f",
                "target_alias": "ACINQ",
                "recommended_capacity": 5000000,
                "expected_centrality_gain": 0.15,
                "reasoning": "Nœud très central avec excellent uptime"
            },
            {
                "target_node": "025f1456582e70c4c06b61d5c8ed3ce229e6d0db538be337a2dc6d163b0ebc05a5", 
                "target_alias": "Bitrefill",
                "recommended_capacity": 3000000,
                "expected_centrality_gain": 0.08,
                "reasoning": "Forte activité commerciale, bon pour le routage"
            }
        ],
        "fee_recommendations": {
            "base_fee_msat": 1000,
            "fee_rate_ppm": 100,
            "reasoning": "Équilibre entre compétitivité et rentabilité"
        },
        "risks": [
            {
                "type": "concentration",
                "level": "low",
                "description": "Diversité des connexions acceptable"
            },
            {
                "type": "liquidity", 
                "level": "medium",
                "description": "Certains canaux déséquilibrés nécessitent attention"
            }
        ]
    }
    
    return analysis_result

@app.get("/api/v1/lightning/nodes/{node_id}/enhanced-analysis")
async def get_enhanced_node_analysis(
    node_id: str,
    include_ai_insights: bool = True,
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Analyse Lightning complète avec insights IA avancés.
    """
    try:
        # Vérification d'autorisation basique
        if authorization:
            from app.auth import verify_jwt_and_get_tenant
            tenant = verify_jwt_and_get_tenant(authorization)
            if not tenant:
                raise HTTPException(status_code=401, detail="Token invalide")
        
        # Obtenir l'analyse de base
        basic_analysis = await analyze_node(node_id, authorization)
        
        # Enrichir avec AI si disponible et demandé
        enhanced_result = {
            "node_id": node_id,
            "analysis_type": "enhanced",
            "timestamp": basic_analysis.get("analysis_timestamp"),
            "basic_analysis": basic_analysis
        }
        
        if include_ai_insights and AI_SERVICES_AVAILABLE:
            try:
                # Obtenir l'analyse AI
                ai_insights = await ai_analysis_service.analyze_node_with_ai(
                    node_id, basic_analysis
                )
                
                enhanced_result["ai_insights"] = ai_insights
                enhanced_result["analysis_type"] = "ai_enhanced"
                
                # Statistiques du cache
                cache_stats = await cache_service.get_cache_stats()
                enhanced_result["cache_info"] = {
                    "cache_mode": cache_stats.get("mode", "unknown"),
                    "cache_connected": cache_stats.get("connected", False)
                }
                
                logger.info(f"Analyse IA complète générée pour le nœud {node_id}")
                
            except Exception as ai_error:
                logger.error(f"Erreur lors de l'analyse AI: {str(ai_error)}")
                enhanced_result["ai_insights"] = {
                    "error": "Analyse AI temporairement indisponible",
                    "fallback": "Analyse de base fournie"
                }
        else:
            enhanced_result["ai_insights"] = {
                "available": False,
                "reason": "AI services non disponibles ou non demandés"
            }
        
        return enhanced_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse enhanced pour {node_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors de l'analyse enhanced: {str(e)}"
        )

@app.get("/api/v1/lightning/nodes/{node_id}/recommendations") 
async def get_node_recommendations(
    node_id: str,
    recommendation_type: Optional[str] = None,
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """Obtient des recommandations spécifiques pour un nœud."""
    
    logger.info(f"Recommandations demandées pour {node_id}, type: {recommendation_type}")
    
    # Filtrer par type si spécifié
    all_recommendations = {
        "connectivity": {
            "title": "Améliorer la connectivité",
            "priority": "high",
            "actions": [
                "Ouvrir des canaux avec des nœuds centraux",
                "Diversifier les connexions géographiques",
                "Cibler des nœuds avec forte activité de routage"
            ],
            "targets": [
                {"node": "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f", "alias": "ACINQ"},
                {"node": "025f1456582e70c4c06b61d5c8ed3ce229e6d0db538be337a2dc6d163b0ebc05a5", "alias": "Bitrefill"}
            ]
        },
        "liquidity": {
            "title": "Optimiser la liquidité",
            "priority": "medium", 
            "actions": [
                "Rééquilibrer les canaux existants",
                "Augmenter la capacité totale",
                "Optimiser la distribution locale/distante"
            ],
            "metrics": {
                "target_total_capacity": 200000000,
                "optimal_channel_size": 15000000,
                "rebalancing_frequency": "weekly"
            }
        },
        "fees": {
            "title": "Ajuster les frais",
            "priority": "low",
            "actions": [
                "Analyser la compétitivité des frais",
                "Ajuster selon l'activité de routage",
                "Optimiser par canal individuellement"
            ],
            "suggested_fees": {
                "base_fee_msat": 1000,
                "fee_rate_ppm": 100
            }
        }
    }
    
    if recommendation_type and recommendation_type in all_recommendations:
        return {
            "node_id": node_id,
            "recommendation_type": recommendation_type,
            "recommendation": all_recommendations[recommendation_type]
        }
    
    return {
        "node_id": node_id,
        "all_recommendations": all_recommendations
    }
