from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Dict, List, Optional, Any, Union, Tuple
from pydantic import BaseModel, Field, validator
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
import joblib
import os
import json
import pickle
from src.auth.jwt import get_current_user
from src.auth.models import User

# Créer le router
router = APIRouter(
    prefix="/predict",
    tags=["Machine Learning Predictions v2"],
    responses={
        401: {"description": "Non authentifié"},
        403: {"description": "Accès refusé"},
        429: {"description": "Trop de requêtes"},
        500: {"description": "Erreur serveur"}
    }
)

# Modèles de données
class FeeOptimizationRequest(BaseModel):
    """Paramètres pour l'optimisation des frais"""
    node_id: str = Field(..., description="Identifiant du nœud")
    channel_id: Optional[str] = Field(None, description="Identifiant du canal (si spécifié)")
    timeframe: str = Field("24h", description="Période d'analyse (1h, 6h, 24h, 7d, 30d)")
    target_metric: str = Field("revenue", description="Métrique à optimiser (revenue, volume, success_rate)")
    include_confidence: bool = Field(True, description="Inclure les intervalles de confiance")
    use_historical: bool = Field(True, description="Utiliser les données historiques")

class ChannelGrowthRequest(BaseModel):
    """Paramètres pour la prédiction de croissance des canaux"""
    node_id: str = Field(..., description="Identifiant du nœud")
    forecast_days: int = Field(30, description="Nombre de jours à prévoir", ge=1, le=365)
    channel_filter: Optional[List[str]] = Field(None, description="Liste de canaux à analyser")
    consider_network_growth: bool = Field(True, description="Prendre en compte la croissance du réseau")
    include_confidence: bool = Field(True, description="Inclure les intervalles de confiance")

class RoutingProbabilityRequest(BaseModel):
    """Paramètres pour la prédiction de probabilité de routage"""
    source_node: str = Field(..., description="Nœud source")
    destination_node: str = Field(..., description="Nœud destination")
    amount_sats: int = Field(..., description="Montant en satoshis", ge=1)
    max_fee_rate: Optional[int] = Field(None, description="Taux de frais maximum en ppm")
    max_paths: int = Field(3, description="Nombre maximum de chemins à considérer", ge=1, le=10)
    include_reliability: bool = Field(True, description="Inclure les métriques de fiabilité")

class PredictionInterval(BaseModel):
    """Intervalle de confiance pour une prédiction"""
    lower: float = Field(..., description="Borne inférieure de l'intervalle de confiance")
    upper: float = Field(..., description="Borne supérieure de l'intervalle de confiance")
    confidence_level: float = Field(0.95, description="Niveau de confiance (ex: 0.95 pour 95%)")

class FeeRecommendation(BaseModel):
    """Recommandation de frais pour un canal"""
    channel_id: str = Field(..., description="Identifiant du canal")
    current_fee_rate: int = Field(..., description="Taux de frais actuel en ppm")
    recommended_fee_rate: int = Field(..., description="Taux de frais recommandé en ppm")
    expected_revenue_change: float = Field(..., description="Changement attendu dans les revenus (%)")
    expected_volume_change: float = Field(..., description="Changement attendu dans le volume (%)")
    confidence_interval: Optional[PredictionInterval] = Field(None, description="Intervalle de confiance")
    explanation: str = Field(..., description="Explication de la recommandation")

class FeeOptimizationResponse(BaseModel):
    """Réponse pour l'optimisation des frais"""
    node_id: str = Field(..., description="Identifiant du nœud")
    recommendations: List[FeeRecommendation] = Field(..., description="Recommandations de frais")
    analysis_timeframe: str = Field(..., description="Période d'analyse utilisée")
    optimization_target: str = Field(..., description="Métrique optimisée")
    estimated_total_improvement: float = Field(..., description="Amélioration totale estimée (%)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Horodatage de l'analyse")

class GrowthPoint(BaseModel):
    """Point de données pour une prévision de croissance"""
    date: datetime = Field(..., description="Date de la prévision")
    value: float = Field(..., description="Valeur prévue")
    lower_bound: Optional[float] = Field(None, description="Borne inférieure de l'intervalle de confiance")
    upper_bound: Optional[float] = Field(None, description="Borne supérieure de l'intervalle de confiance")

class ChannelGrowthResponse(BaseModel):
    """Réponse pour la prévision de croissance des canaux"""
    node_id: str = Field(..., description="Identifiant du nœud")
    forecast_days: int = Field(..., description="Nombre de jours prévus")
    capacity_forecast: List[GrowthPoint] = Field(..., description="Prévision de capacité totale")
    channels_forecast: List[GrowthPoint] = Field(..., description="Prévision du nombre de canaux")
    transactions_forecast: Optional[List[GrowthPoint]] = Field(None, description="Prévision du nombre de transactions")
    volume_forecast: Optional[List[GrowthPoint]] = Field(None, description="Prévision du volume de transactions")
    confidence_level: Optional[float] = Field(None, description="Niveau de confiance des prévisions")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Horodatage de l'analyse")

class RoutingPath(BaseModel):
    """Chemin de routage pour un paiement"""
    path: List[str] = Field(..., description="Liste des nœuds dans le chemin")
    total_fee: int = Field(..., description="Frais totaux en satoshis")
    fee_rate: float = Field(..., description="Taux de frais effectif en ppm")
    probability: float = Field(..., description="Probabilité de succès estimée")
    avg_delay_ms: Optional[int] = Field(None, description="Délai moyen estimé en millisecondes")
    reliability_score: Optional[float] = Field(None, description="Score de fiabilité (0-1)")

class RoutingProbabilityResponse(BaseModel):
    """Réponse pour la prédiction de probabilité de routage"""
    source_node: str = Field(..., description="Nœud source")
    destination_node: str = Field(..., description="Nœud destination")
    amount_sats: int = Field(..., description="Montant en satoshis")
    overall_success_probability: float = Field(..., description="Probabilité globale de succès")
    recommended_paths: List[RoutingPath] = Field(..., description="Chemins recommandés")
    alternative_amount_suggestions: Optional[List[int]] = Field(None, description="Suggestions de montants alternatifs")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Horodatage de l'analyse")

# Classe de service pour les prédictions
class PredictionService:
    """Service pour effectuer des prédictions d'apprentissage automatique"""
    
    def __init__(self):
        """Initialise le service de prédiction"""
        self.models = {}
        self.load_models()
    
    def load_models(self):
        """Charge les modèles ML préentraînés"""
        # Dans une implémentation réelle, ces modèles seraient chargés depuis des fichiers
        # Pour cet exemple, nous utiliserons des modèles créés à la volée
        
        # Modèle pour l'optimisation des frais
        fee_model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        # Modèle pour la croissance des canaux
        growth_model = RandomForestRegressor(n_estimators=100, random_state=42)
        # Modèle pour la probabilité de routage
        routing_model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        
        self.models = {
            "fee_optimization": fee_model,
            "channel_growth": growth_model,
            "routing_probability": routing_model
        }
    
    def predict_optimal_fees(self, request: FeeOptimizationRequest) -> FeeOptimizationResponse:
        """
        Prédit les frais optimaux pour les canaux d'un nœud
        
        Args:
            request: Les paramètres de la requête
            
        Returns:
            Recommandations de frais optimaux
        """
        # Dans une implémentation réelle, nous récupérerions les données historiques
        # et alimenterions le modèle avec ces données
        
        # Simuler quelques canaux pour le nœud
        channels = [f"{request.node_id[:8]}-{i}" for i in range(5)]
        
        # Générer des recommandations simulées
        recommendations = []
        total_improvement = 0.0
        
        for channel_id in channels:
            # Si un canal spécifique est demandé, filtrer
            if request.channel_id and channel_id != request.channel_id:
                continue
                
            # Simuler des valeurs actuelles
            current_fee = np.random.randint(100, 1000)
            
            # Simuler une prédiction
            if request.target_metric == "revenue":
                recommended_fee = max(int(current_fee * (1 + np.random.uniform(-0.3, 0.5))), 1)
                revenue_change = np.random.uniform(-5, 25)
                volume_change = np.random.uniform(-15, 10)
                explanation = "Basé sur les tendances du marché et l'historique de ce canal"
            elif request.target_metric == "volume":
                recommended_fee = max(int(current_fee * (1 - np.random.uniform(0.1, 0.4))), 1)
                revenue_change = np.random.uniform(-15, 10)
                volume_change = np.random.uniform(5, 30)
                explanation = "Réduction des frais pour augmenter le volume de transactions"
            else:  # success_rate
                recommended_fee = max(int(current_fee * (1 - np.random.uniform(0.05, 0.2))), 1)
                revenue_change = np.random.uniform(-10, 5)
                volume_change = np.random.uniform(0, 15)
                explanation = "Équilibre entre taux de réussite et revenus"
            
            # Créer un intervalle de confiance si demandé
            confidence_interval = None
            if request.include_confidence:
                # Simuler un intervalle de confiance
                margin = recommended_fee * 0.2
                confidence_interval = PredictionInterval(
                    lower=max(recommended_fee - margin, 1),
                    upper=recommended_fee + margin,
                    confidence_level=0.95
                )
            
            # Créer la recommandation
            recommendation = FeeRecommendation(
                channel_id=channel_id,
                current_fee_rate=current_fee,
                recommended_fee_rate=recommended_fee,
                expected_revenue_change=revenue_change,
                expected_volume_change=volume_change,
                confidence_interval=confidence_interval,
                explanation=explanation
            )
            
            recommendations.append(recommendation)
            total_improvement += revenue_change if request.target_metric == "revenue" else volume_change
        
        # Calculer l'amélioration moyenne
        avg_improvement = total_improvement / len(recommendations) if recommendations else 0
        
        return FeeOptimizationResponse(
            node_id=request.node_id,
            recommendations=recommendations,
            analysis_timeframe=request.timeframe,
            optimization_target=request.target_metric,
            estimated_total_improvement=avg_improvement
        )
    
    def predict_channel_growth(self, request: ChannelGrowthRequest) -> ChannelGrowthResponse:
        """
        Prédit la croissance des canaux d'un nœud
        
        Args:
            request: Les paramètres de la requête
            
        Returns:
            Prévisions de croissance
        """
        # Dans une implémentation réelle, nous récupérerions les données historiques
        # et alimenterions le modèle avec ces données
        
        # Générer des dates pour la prévision
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        dates = [today + timedelta(days=i) for i in range(1, request.forecast_days + 1)]
        
        # Simuler une croissance de capacité
        capacity_base = 10000000  # 10M sats
        capacity_forecast = []
        
        # Simuler une croissance du nombre de canaux
        channels_base = 15
        channels_forecast = []
        
        # Simuler une croissance du nombre de transactions
        transactions_base = 100
        transactions_forecast = []
        
        # Simuler une croissance du volume de transactions
        volume_base = 1000000  # 1M sats
        volume_forecast = []
        
        for i, date in enumerate(dates):
            # Capacité : croissance légèrement exponentielle
            growth_factor = 1 + (0.01 * (i / 30))  # 1% de croissance par mois
            capacity = capacity_base * (growth_factor ** (i / 30))
            
            # Nombre de canaux : croissance linéaire
            channels = channels_base + (i / 10)
            
            # Nombre de transactions : croissance variable
            transactions = transactions_base * (1 + (0.015 * i))
            
            # Volume : suit la capacité avec des variations
            volume = volume_base * (growth_factor ** (i / 30)) * (1 + np.random.uniform(-0.1, 0.1))
            
            # Créer les intervalles de confiance si demandés
            capacity_lower = None
            capacity_upper = None
            channels_lower = None
            channels_upper = None
            transactions_lower = None
            transactions_upper = None
            volume_lower = None
            volume_upper = None
            
            if request.include_confidence:
                # Les intervalles s'élargissent avec le temps
                uncertainty_factor = 1 + (i / request.forecast_days)
                
                capacity_margin = capacity * 0.05 * uncertainty_factor
                capacity_lower = capacity - capacity_margin
                capacity_upper = capacity + capacity_margin
                
                channels_margin = channels * 0.03 * uncertainty_factor
                channels_lower = max(channels - channels_margin, channels_base)
                channels_upper = channels + channels_margin
                
                transactions_margin = transactions * 0.1 * uncertainty_factor
                transactions_lower = transactions - transactions_margin
                transactions_upper = transactions + transactions_margin
                
                volume_margin = volume * 0.15 * uncertainty_factor
                volume_lower = volume - volume_margin
                volume_upper = volume + volume_margin
            
            # Ajouter les points de données
            capacity_forecast.append(GrowthPoint(
                date=date,
                value=capacity,
                lower_bound=capacity_lower,
                upper_bound=capacity_upper
            ))
            
            channels_forecast.append(GrowthPoint(
                date=date,
                value=channels,
                lower_bound=channels_lower,
                upper_bound=channels_upper
            ))
            
            transactions_forecast.append(GrowthPoint(
                date=date,
                value=transactions,
                lower_bound=transactions_lower,
                upper_bound=transactions_upper
            ))
            
            volume_forecast.append(GrowthPoint(
                date=date,
                value=volume,
                lower_bound=volume_lower,
                upper_bound=volume_upper
            ))
        
        return ChannelGrowthResponse(
            node_id=request.node_id,
            forecast_days=request.forecast_days,
            capacity_forecast=capacity_forecast,
            channels_forecast=channels_forecast,
            transactions_forecast=transactions_forecast,
            volume_forecast=volume_forecast,
            confidence_level=0.95 if request.include_confidence else None
        )
    
    def predict_routing_probability(self, request: RoutingProbabilityRequest) -> RoutingProbabilityResponse:
        """
        Prédit la probabilité de routage entre deux nœuds
        
        Args:
            request: Les paramètres de la requête
            
        Returns:
            Probabilités de routage et chemins recommandés
        """
        # Dans une implémentation réelle, nous récupérerions la topologie du réseau
        # et alimenterions le modèle avec ces données
        
        # Simuler plusieurs chemins possibles
        paths = []
        
        # Plus le montant est élevé, plus la probabilité globale diminue
        amount_factor = max(0.1, 1 - (request.amount_sats / 10000000))  # 10M sats max
        overall_probability = min(0.98, amount_factor * np.random.uniform(0.7, 1.0))
        
        # Générer des chemins alternatifs
        for i in range(min(request.max_paths, 5)):
            # Plus le chemin est long, moins il est fiable
            path_length = np.random.randint(2, 6)
            path_nodes = [request.source_node]
            
            # Générer des nœuds intermédiaires aléatoires
            for j in range(path_length - 2):
                intermediate_node = f"node_{np.random.randint(1000, 9999)}"
                path_nodes.append(intermediate_node)
            
            path_nodes.append(request.destination_node)
            
            # Calculer les frais et la probabilité de ce chemin
            base_fee = request.amount_sats * np.random.uniform(0.0001, 0.003)  # 0.01% to 0.3%
            fee_rate = base_fee * 1000000 / request.amount_sats  # en ppm
            
            path_probability = overall_probability * (1 - (i * 0.15))  # Le premier chemin est le plus probable
            
            # Ajouter des métriques supplémentaires si demandées
            avg_delay = None
            reliability_score = None
            
            if request.include_reliability:
                avg_delay = np.random.randint(50, 2000)  # 50ms to 2s
                reliability_score = path_probability * np.random.uniform(0.8, 1.0)
            
            paths.append(RoutingPath(
                path=path_nodes,
                total_fee=int(base_fee),
                fee_rate=fee_rate,
                probability=path_probability,
                avg_delay_ms=avg_delay,
                reliability_score=reliability_score
            ))
        
        # Générer des suggestions de montants alternatifs
        alternative_amounts = None
        if request.amount_sats > 1000000:  # 1M sats
            smaller_amount1 = request.amount_sats // 2
            smaller_amount2 = request.amount_sats // 3
            alternative_amounts = [smaller_amount1, smaller_amount2]
        
        return RoutingProbabilityResponse(
            source_node=request.source_node,
            destination_node=request.destination_node,
            amount_sats=request.amount_sats,
            overall_success_probability=overall_probability,
            recommended_paths=paths,
            alternative_amount_suggestions=alternative_amounts
        )

# Initialiser le service
prediction_service = PredictionService()

@router.post("/fee-optimization", response_model=FeeOptimizationResponse)
async def optimize_fees(
    request: FeeOptimizationRequest = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Optimise les frais des canaux d'un nœud Lightning.
    
    Cette endpoint utilise l'apprentissage automatique pour recommander
    des ajustements de frais qui maximisent les revenus, le volume ou
    le taux de réussite des transactions.
    
    Les recommandations sont basées sur les tendances historiques et
    les conditions actuelles du réseau Lightning.
    """
    try:
        result = prediction_service.predict_optimal_fees(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'optimisation des frais: {str(e)}")

@router.post("/channel-growth", response_model=ChannelGrowthResponse)
async def predict_channel_growth(
    request: ChannelGrowthRequest = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Prédit la croissance future des canaux d'un nœud Lightning.
    
    Cette endpoint utilise des modèles de série temporelle pour prévoir
    l'évolution de la capacité, du nombre de canaux, du volume et
    des transactions d'un nœud Lightning.
    
    Les prévisions peuvent être utilisées pour planifier la stratégie
    de croissance et d'allocation de liquidité.
    """
    try:
        result = prediction_service.predict_channel_growth(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la prédiction de croissance: {str(e)}")

@router.post("/routing-probability", response_model=RoutingProbabilityResponse)
async def predict_routing_probability(
    request: RoutingProbabilityRequest = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Prédit la probabilité de routage d'un paiement entre deux nœuds.
    
    Cette endpoint analyse la topologie du réseau Lightning pour estimer
    les chances de succès d'un paiement entre deux nœuds et recommande
    les chemins optimaux.
    
    Les prédictions tiennent compte de la capacité des canaux, de
    leur fiabilité historique et des frais associés.
    """
    try:
        result = prediction_service.predict_routing_probability(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la prédiction de routage: {str(e)}") 