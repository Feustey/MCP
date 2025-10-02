from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Dict, List, Optional, Any
from app.services.lnbits import LNbitsService
from app.auth import verify_jwt_and_get_tenant

router = APIRouter(prefix="/channels", tags=["Channel Management"])

@router.get("/recommendations/amboss",
    summary="Recommandations Canaux Amboss",
    description="Récupère les suggestions de canaux depuis Amboss Space basées sur votre nœud",
    responses={
        200: {
            "description": "Recommandations Amboss récupérées",
            "content": {
                "application/json": {
                    "example": {
                        "recommendations": [
                            {
                                "node_pubkey": "02b1fe652cfc...",
                                "alias": "ACINQ",
                                "score": 95.5,
                                "capacity_suggested": 5000000,
                                "reasons": ["High centrality", "Good liquidity", "Low fees"]
                            }
                        ],
                        "count": 10,
                        "source": "amboss"
                    }
                }
            }
        },
        401: {"description": "Non authentifié"}
    }
)
async def get_amboss_recommendations(
    authorization: str = Header(..., alias="Authorization")
):
    """
    **🎯 Recommandations de Canaux Amboss**

    Récupère les suggestions intelligentes de partenaires pour nouveaux canaux
    depuis Amboss Space, basées sur:
    - Position de votre nœud dans le réseau
    - Liquidité et centralité des candidats
    - Historique de performance
    - Complémentarité avec vos canaux existants

    **Authentification:** JWT requis
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    lnbits_service = LNbitsService()
    return await lnbits_service.get_amboss_channel_recommendations()

@router.get("/recommendations/unified",
    summary="Recommandations Unifiées Multi-Sources",
    description="Agrège les recommandations de tous les fournisseurs (Amboss, 1ML, analyse interne)",
    responses={
        200: {
            "description": "Recommandations unifiées",
            "content": {
                "application/json": {
                    "example": {
                        "recommendations": [
                            {
                                "node_pubkey": "03a81c5aa298...",
                                "alias": "barcelona-big",
                                "composite_score": 92.3,
                                "sources": ["amboss", "internal_analysis"],
                                "suggested_capacity": 3000000,
                                "priority": "high",
                                "benefits": [
                                    "Améliore centralité de 15%",
                                    "Accès à cluster européen",
                                    "ROI estimé: 8.5%/an"
                                ]
                            }
                        ],
                        "total": 15,
                        "aggregation_strategy": "weighted_composite"
                    }
                }
            }
        }
    }
)
async def get_unified_recommendations(
    authorization: str = Header(..., alias="Authorization")
):
    """
    **🌐 Recommandations de Canaux Unifiées**

    Agrège et pondère les recommandations provenant de:
    - **Amboss Space**: Analyse réseau globale
    - **1ML (1 Million Lightning)**: Classements et statistiques
    - **Analyse Interne MCP**: DazFlow Index et Max-Flow

    **Avantages:**
    - Score composite multi-critères
    - Élimination des doublons
    - Priorisation intelligente
    - Estimation ROI personnalisée

    **Authentification:** JWT requis
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    lnbits_service = LNbitsService()
    return await lnbits_service.get_unified_channel_recommendations() 