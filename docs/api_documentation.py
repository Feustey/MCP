"""
Documentation API complète pour MCP Lightning Network 2.0.0
Configuration Swagger/OpenAPI avec tous les nouveaux endpoints avancés
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

# ============================================================================
# MODÈLES PYDANTIC POUR LA DOCUMENTATION
# ============================================================================

class NodePerformanceCategory(str, Enum):
    """Catégories de performance des nœuds"""
    elite_hub = "elite_hub"
    major_hub = "major_hub"
    active_router = "active_router"
    developing_node = "developing_node"
    emerging_node = "emerging_node"

class MaxFlowAnalysisRequest(BaseModel):
    """Requête d'analyse Max Flow"""
    source_node: str = Field(..., description="Public key du nœud source", min_length=66, max_length=66)
    target_node: str = Field(..., description="Public key du nœud cible", min_length=66, max_length=66)
    payment_amount: Optional[int] = Field(None, description="Montant du paiement en satoshis", gt=0)

class PaymentProbabilityRequest(BaseModel):
    """Requête d'analyse de probabilité de paiement"""
    source_node: str = Field(..., description="Public key du nœud source", min_length=66, max_length=66)
    target_node: str = Field(..., description="Public key du nœud cible", min_length=66, max_length=66)
    amounts: List[int] = Field(..., description="Liste des montants à tester en satoshis", min_items=1)

class FeeOptimizationTargets(BaseModel):
    """Métriques cibles pour l'optimisation des frais"""
    min_success_rate: float = Field(0.85, description="Taux de succès minimum souhaité", ge=0.0, le=1.0)
    target_volume_increase: float = Field(0.20, description="Augmentation de volume ciblée", ge=0.0, le=2.0)
    max_fee_increase: float = Field(0.50, description="Augmentation maximum des frais", ge=0.0, le=1.0)

class CentralityMetrics(BaseModel):
    """Métriques de centralité d'un nœud"""
    degree_centrality: float = Field(..., description="Centralité de degré (0-1)")
    betweenness_centrality: float = Field(..., description="Centralité d'intermédiarité (0-1)")
    closeness_centrality: float = Field(..., description="Centralité de proximité (0-1)")
    eigenvector_centrality: float = Field(..., description="Centralité de vecteur propre (0-1)")

class LiquidityMetrics(BaseModel):
    """Métriques de liquidité d'un nœud"""
    outbound_liquidity: int = Field(..., description="Liquidité sortante en satoshis")
    inbound_liquidity: int = Field(..., description="Liquidité entrante en satoshis")
    liquidity_ratio: float = Field(..., description="Ratio liquidité entrante/sortante")
    average_reachability: float = Field(..., description="Accessibilité moyenne vers les hubs")
    liquidity_distribution_score: float = Field(..., description="Score de distribution de liquidité (0-1)")

class FlowPath(BaseModel):
    """Chemin de flux dans l'analyse Max Flow"""
    path: List[str] = Field(..., description="Liste des nœuds dans le chemin")
    flow_amount: int = Field(..., description="Montant du flux sur ce chemin en satoshis")
    hop_count: int = Field(..., description="Nombre de sauts dans le chemin")

class MaxFlowResult(BaseModel):
    """Résultat d'analyse Max Flow"""
    max_flow_value: int = Field(..., description="Valeur du flux maximum en satoshis")
    success_probability: float = Field(..., description="Probabilité de succès du paiement (0-1)")
    flow_paths: List[FlowPath] = Field(..., description="Chemins de flux identifiés")
    bottleneck_analysis: Dict[str, Any] = Field(..., description="Analyse des goulots d'étranglement")
    liquidity_distribution: Dict[str, Any] = Field(..., description="Distribution de liquidité")

class RebalancingOperation(BaseModel):
    """Opération de rééquilibrage recommandée"""
    type: str = Field(..., description="Type d'opération (rebalance_inbound/outbound)")
    target_node: str = Field(..., description="Nœud cible pour l'opération")
    recommended_amount: int = Field(..., description="Montant recommandé en satoshis")
    current_ratio: float = Field(..., description="Ratio actuel de liquidité")
    priority: str = Field(..., description="Priorité de l'opération (high/medium/low)")

class ChannelOptimization(BaseModel):
    """Optimisation recommandée pour un canal"""
    channel_id: str = Field(..., description="ID du canal")
    current_fee_ppm: int = Field(..., description="Frais actuels en ppm")
    recommended_fee_ppm: int = Field(..., description="Frais recommandés en ppm")
    change_percent: float = Field(..., description="Changement en pourcentage")
    change_reason: str = Field(..., description="Raison du changement recommandé")
    expected_impact: Dict[str, Any] = Field(..., description="Impact attendu du changement")

class PerformanceScore(BaseModel):
    """Score de performance d'un nœud"""
    overall_score: float = Field(..., description="Score global de performance (0-100)", ge=0, le=100)
    centrality_metrics: CentralityMetrics = Field(..., description="Métriques de centralité")
    liquidity_metrics: LiquidityMetrics = Field(..., description="Métriques de liquidité")
    score_breakdown: Dict[str, float] = Field(..., description="Détail des composants du score")
    ranking_category: NodePerformanceCategory = Field(..., description="Catégorie de performance")
    improvement_areas: List[str] = Field(..., description="Domaines d'amélioration prioritaires")

class NetworkTopology(BaseModel):
    """Métriques de topologie du réseau"""
    basic_metrics: Dict[str, Any] = Field(..., description="Métriques de base (nœuds, canaux, densité)")
    clustering_metrics: Dict[str, Any] = Field(..., description="Métriques de clustering")
    capacity_metrics: Dict[str, Any] = Field(..., description="Métriques de capacité")
    degree_distribution: Dict[str, Any] = Field(..., description="Distribution des degrés")
    critical_points: Dict[str, Any] = Field(..., description="Points critiques du réseau")

class HubNode(BaseModel):
    """Nœud hub identifié dans l'analyse"""
    hubness_score: float = Field(..., description="Score de hubness (0-1)")
    degree: int = Field(..., description="Nombre de connexions")
    weighted_degree: int = Field(..., description="Degré pondéré par capacité")
    betweenness: float = Field(..., description="Centralité d'intermédiarité")
    closeness: float = Field(..., description="Centralité de proximité")
    eigenvector: float = Field(..., description="Centralité de vecteur propre")
    alias: str = Field(..., description="Alias du nœud")

class EnhancedAnalysisResponse(BaseModel):
    """Réponse complète d'analyse avancée"""
    success: bool = Field(..., description="Succès de l'analyse")
    node_pubkey: str = Field(..., description="Public key du nœud analysé")
    enhanced_analysis: Dict[str, Any] = Field(..., description="Données d'analyse complètes")

class FinancialAnalysis(BaseModel):
    """Analyse financière d'un nœud"""
    node_financials: Dict[str, Any] = Field(..., description="État financier du nœud")
    revenue_analysis: Dict[str, Any] = Field(..., description="Analyse des revenus")
    fee_analysis: Dict[str, Any] = Field(..., description="Analyse de la structure tarifaire")
    roi_analysis: Dict[str, Any] = Field(..., description="Analyse du retour sur investissement")
    optimization_recommendations: List[Dict[str, Any]] = Field(..., description="Recommandations d'optimisation")

# ============================================================================
# CONFIGURATION SWAGGER/OPENAPI
# ============================================================================

API_TAGS_METADATA = [
    {
        "name": "System Health",
        "description": "Endpoints de santé système et monitoring"
    },
    {
        "name": "Lightning Network",
        "description": "Endpoints Lightning Network avec fonctionnalités avancées"
    },
    {
        "name": "Max Flow Analysis",
        "description": "Analyse Max Flow pour probabilité de succès des paiements"
    },
    {
        "name": "Graph Theory",
        "description": "Métriques de théorie des graphes et analyse de centralité"
    },
    {
        "name": "Financial Analysis",
        "description": "Analyse financière et optimisation des revenus"
    },
    {
        "name": "Network Topology",
        "description": "Analyse de la topologie du réseau Lightning"
    },
    {
        "name": "Performance Scoring",
        "description": "Scoring de performance composite des nœuds"
    }
]

API_DESCRIPTION = """
# MCP Lightning Network API 2.0.0

API complète pour l'analyse et la gestion professionnelle des nœuds Lightning Network.

## 🚀 Fonctionnalités avancées

### Max Flow Analysis
- **Probabilité de succès** des paiements entre nœuds
- **Analyse multi-montants** pour optimisation des transactions  
- **Recommandations de liquidité** basées sur les flux optimaux

### Graph Theory Metrics
- **Centralité** (degree, betweenness, closeness, eigenvector)
- **Hubness ranking** - identification des nœuds centraux
- **Positionnement stratégique** dans la topologie réseau

### Financial Analysis
- **ROI et revenus** avec projections temporelles
- **Optimisation tarifaire** automatique
- **Analyse concurrentielle** des frais de marché

### Network Intelligence
- **Topologie réseau** avec métriques critiques
- **Performance scoring** composite 0-100
- **Recommandations actionnables** pour améliorer les métriques

## 🔑 Authentification

Tous les endpoints nécessitent une clé API valide dans le header `Authorization: Bearer {your_api_key}`.

## 📊 Cas d'usage

- **Opérateurs de nœuds** : Optimisation performance et revenus
- **Développeurs** : Intégration analyse Lightning dans applications
- **Chercheurs** : Étude de la topologie et dynamique du réseau
- **Services financiers** : Analyse risque et routage optimal

## 🎯 Exemples d'analyse

### Nœud "barcelona-big"
```
GET /api/v1/lightning/nodes/{pubkey}/enhanced-analysis
```

### Max Flow entre deux nœuds
```  
GET /api/v1/lightning/max-flow/{source}/{target}?payment_amount=100000
```

### Optimisation des frais
```
POST /api/v1/lightning/nodes/{pubkey}/optimize-fees
```

---

*Système développé pour l'analyse professionnelle des nœuds Lightning Network*
"""

SWAGGER_CONFIG = {
    "title": "MCP Lightning Network API",
    "description": API_DESCRIPTION,
    "version": "2.0.0",
    "terms_of_service": "https://api.dazno.de/terms/",
    "contact": {
        "name": "MCP Lightning Support",
        "url": "https://api.dazno.de/support/",
        "email": "support@dazno.de"
    },
    "license_info": {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    "openapi_tags": API_TAGS_METADATA
}

# ============================================================================
# EXEMPLES DE RÉPONSES POUR LA DOCUMENTATION
# ============================================================================

EXAMPLE_RESPONSES = {
    "enhanced_analysis": {
        "success": True,
        "node_pubkey": "02b1fe652cfc61f1e5cef78c08d60918d9fad3f029808f995a959e0a9dcbd33bab",
        "enhanced_analysis": {
            "liquidity_analysis": {
                "outbound_liquidity": 399549854,
                "inbound_liquidity": 385420000,
                "liquidity_ratio": 0.965,
                "average_reachability": 1250000,
                "liquidity_distribution_score": 0.78
            },
            "network_positioning": {
                "centrality_metrics": {
                    "degree_centrality": 0.162,
                    "betweenness_centrality": 0.045,
                    "closeness_centrality": 0.23,
                    "eigenvector_centrality": 0.089
                },
                "ranking": {
                    "degree_rank": 248,
                    "degree_percentile": 97.5
                }
            },
            "financial_metrics": {
                "annual_roi_percent": 12.5,
                "monthly_revenue_btc": 0.00125,
                "monthly_revenue_usd": 55.75
            },
            "rebalancing_recommendations": [
                {
                    "type": "rebalance_outbound",
                    "target_node": "029ef6567a4be22b0387d63f721808dce5c0a13682dbd0d6efce820d3ec3c73991",
                    "recommended_amount": 5000000,
                    "priority": "high"
                }
            ]
        }
    },
    "max_flow_result": {
        "success": True,
        "max_flow_analysis": {
            "max_flow_value": 15000000,
            "success_probability": 0.95,
            "flow_paths": [
                {
                    "path": ["02b1fe652...", "029ef6567...", "target"],
                    "flow_amount": 8000000,
                    "hop_count": 2
                },
                {
                    "path": ["02b1fe652...", "alternate", "target"],
                    "flow_amount": 7000000,
                    "hop_count": 2
                }
            ]
        }
    },
    "performance_score": {
        "success": True,
        "performance_analysis": {
            "overall_score": 78.5,
            "ranking_category": "major_hub",
            "score_breakdown": {
                "connectivity_score": 82.0,
                "routing_efficiency": 75.0,
                "network_closeness": 85.0,
                "liquidity_management": 78.0
            },
            "improvement_areas": [
                "Améliorer le positionnement pour le routage",
                "Optimiser la distribution de liquidité"
            ]
        }
    }
}

# ============================================================================
# CONFIGURATION DES RÉPONSES D'ERREUR
# ============================================================================

ERROR_RESPONSES = {
    400: {
        "description": "Requête invalide",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Format du public key invalide"
                }
            }
        }
    },
    401: {
        "description": "Authentification requise",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Invalid API key"
                }
            }
        }
    },
    404: {
        "description": "Ressource non trouvée",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Nœud non trouvé dans le réseau"
                }
            }
        }
    },
    429: {
        "description": "Limite de taux atteinte",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Rate limit exceeded. Please try again later."
                }
            }
        }
    },
    500: {
        "description": "Erreur serveur interne",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Erreur lors de l'analyse du réseau"
                }
            }
        }
    }
}