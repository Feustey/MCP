#!/usr/bin/env python3
"""
Optimiseur avancé de frais pour MCP - Apprentissage et adaptation dynamique
Dernière mise à jour: 7 mai 2025
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

@dataclass
class ChannelState:
    """État d'un canal Lightning"""
    channel_id: str
    local_balance: int
    remote_balance: int
    base_fee: int
    fee_rate: int
    last_update: datetime
    forward_history: List[Dict[str, Any]]
    revenue_history: List[Dict[str, Any]]

@dataclass
class OptimizationResult:
    """Résultat d'une optimisation de frais"""
    new_base_fee: int
    new_fee_rate: int
    expected_improvement: float
    confidence: float
    reasoning: List[str]

class AdvancedFeeOptimizer:
    """
    Optimiseur avancé de frais avec apprentissage par renforcement
    et adaptation dynamique basée sur les métriques historiques.
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        learning_rate: float = 0.1,
        exploration_rate: float = 0.2
    ):
        """
        Initialise l'optimiseur de frais
        
        Args:
            redis_url: URL de connexion Redis
            learning_rate: Taux d'apprentissage (alpha)
            exploration_rate: Taux d'exploration (epsilon)
        """
        self.redis = redis.from_url(redis_url)
        self.learning_rate = learning_rate
        self.exploration_rate = exploration_rate
        
        # Paramètres d'optimisation
        self.fee_bounds = {
            "base_fee": {"min": 0, "max": 10000},
            "fee_rate": {"min": 0, "max": 100000}
        }
        
        # Fenêtres d'analyse
        self.analysis_windows = {
            "short_term": timedelta(hours=24),
            "medium_term": timedelta(days=7),
            "long_term": timedelta(days=30)
        }
        
    def optimize_fees(self, channel_state: ChannelState) -> OptimizationResult:
        """
        Optimise les frais d'un canal en utilisant l'apprentissage
        
        Args:
            channel_state: État actuel du canal
            
        Returns:
            OptimizationResult avec les nouveaux frais recommandés
        """
        try:
            # 1. Analyser l'historique
            metrics = self._analyze_history(channel_state)
            
            # 2. Calculer l'état du marché
            market_state = self._analyze_market_conditions(channel_state)
            
            # 3. Générer les recommandations
            base_fee, fee_rate = self._generate_fee_recommendation(
                channel_state,
                metrics,
                market_state
            )
            
            # 4. Calculer la confiance et l'amélioration attendue
            confidence, improvement = self._evaluate_recommendation(
                channel_state,
                base_fee,
                fee_rate,
                metrics
            )
            
            # 5. Générer le raisonnement
            reasoning = self._generate_reasoning(
                channel_state,
                metrics,
                market_state,
                base_fee,
                fee_rate
            )
            
            # 6. Sauvegarder pour apprentissage
            self._save_recommendation(
                channel_state.channel_id,
                base_fee,
                fee_rate,
                confidence,
                improvement
            )
            
            return OptimizationResult(
                new_base_fee=base_fee,
                new_fee_rate=fee_rate,
                expected_improvement=improvement,
                confidence=confidence,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation: {e}")
            raise
            
    def _analyze_history(
        self,
        channel_state: ChannelState
    ) -> Dict[str, Any]:
        """
        Analyse l'historique du canal pour extraire des métriques
        
        Args:
            channel_state: État du canal
            
        Returns:
            Dict contenant les métriques d'analyse
        """
        metrics = {
            "short_term": self._compute_window_metrics(
                channel_state,
                self.analysis_windows["short_term"]
            ),
            "medium_term": self._compute_window_metrics(
                channel_state,
                self.analysis_windows["medium_term"]
            ),
            "long_term": self._compute_window_metrics(
                channel_state,
                self.analysis_windows["long_term"]
            )
        }
        
        # Calculer les tendances
        metrics["trends"] = {
            "revenue": self._calculate_trend(
                [m["avg_revenue"] for m in metrics.values()]
            ),
            "volume": self._calculate_trend(
                [m["avg_volume"] for m in metrics.values()]
            ),
            "success_rate": self._calculate_trend(
                [m["success_rate"] for m in metrics.values()]
            )
        }
        
        return metrics
        
    def _analyze_market_conditions(
        self,
        channel_state: ChannelState
    ) -> Dict[str, Any]:
        """
        Analyse les conditions du marché
        
        Args:
            channel_state: État du canal
            
        Returns:
            Dict contenant l'analyse du marché
        """
        try:
            # 1. Récupérer les données du marché
            market_key = f"market:global:{datetime.now().date().isoformat()}"
            market_data = self.redis.get(market_key)
            
            if market_data:
                market_stats = eval(market_data)  # Pour demo uniquement
            else:
                market_stats = self._compute_market_stats()
                self.redis.setex(
                    market_key,
                    24 * 3600,
                    str(market_stats)
                )
                
            # 2. Analyser la position relative
            relative_position = self._analyze_relative_position(
                channel_state,
                market_stats
            )
            
            return {
                "stats": market_stats,
                "relative_position": relative_position,
                "competition_level": self._estimate_competition(
                    channel_state,
                    market_stats
                )
            }
            
        except Exception as e:
            logger.error(f"Erreur analyse marché: {e}")
            return {}
            
    def _generate_fee_recommendation(
        self,
        channel_state: ChannelState,
        metrics: Dict[str, Any],
        market_state: Dict[str, Any]
    ) -> Tuple[int, int]:
        """
        Génère une recommandation de frais
        
        Args:
            channel_state: État du canal
            metrics: Métriques d'analyse
            market_state: État du marché
            
        Returns:
            Tuple (base_fee, fee_rate) recommandé
        """
        # 1. Calculer les facteurs d'ajustement
        volume_factor = self._calculate_volume_factor(metrics)
        competition_factor = self._calculate_competition_factor(market_state)
        success_factor = self._calculate_success_factor(metrics)
        
        # 2. Appliquer l'exploration si nécessaire
        if np.random.random() < self.exploration_rate:
            return self._explore_fees()
            
        # 3. Calculer les nouveaux frais
        base_fee = int(
            channel_state.base_fee *
            (1 + self.learning_rate * (
                volume_factor +
                competition_factor +
                success_factor
            ))
        )
        
        fee_rate = int(
            channel_state.fee_rate *
            (1 + self.learning_rate * (
                volume_factor +
                competition_factor +
                success_factor
            ))
        )
        
        # 4. Appliquer les limites
        base_fee = max(
            self.fee_bounds["base_fee"]["min"],
            min(base_fee, self.fee_bounds["base_fee"]["max"])
        )
        
        fee_rate = max(
            self.fee_bounds["fee_rate"]["min"],
            min(fee_rate, self.fee_bounds["fee_rate"]["max"])
        )
        
        return base_fee, fee_rate
        
    def _evaluate_recommendation(
        self,
        channel_state: ChannelState,
        base_fee: int,
        fee_rate: int,
        metrics: Dict[str, Any]
    ) -> Tuple[float, float]:
        """
        Évalue une recommandation de frais
        
        Args:
            channel_state: État du canal
            base_fee: Base fee recommandée
            fee_rate: Fee rate recommandé
            metrics: Métriques d'analyse
            
        Returns:
            Tuple (confidence, expected_improvement)
        """
        # 1. Calculer la différence relative
        base_fee_change = abs(base_fee - channel_state.base_fee) / channel_state.base_fee
        fee_rate_change = abs(fee_rate - channel_state.fee_rate) / channel_state.fee_rate
        
        # 2. Évaluer la stabilité historique
        stability = self._calculate_stability(metrics)
        
        # 3. Calculer la confiance
        confidence = max(0.0, min(1.0, 1.0 - (
            0.3 * base_fee_change +
            0.3 * fee_rate_change +
            0.4 * (1 - stability)
        )))
        
        # 4. Estimer l'amélioration
        current_revenue = metrics["short_term"]["avg_revenue"]
        expected_revenue = current_revenue * (1 + self._estimate_improvement_factor(
            channel_state,
            base_fee,
            fee_rate,
            metrics
        ))
        
        improvement = (expected_revenue - current_revenue) / current_revenue
        
        return confidence, improvement
        
    def _generate_reasoning(
        self,
        channel_state: ChannelState,
        metrics: Dict[str, Any],
        market_state: Dict[str, Any],
        base_fee: int,
        fee_rate: int
    ) -> List[str]:
        """
        Génère le raisonnement derrière une recommandation
        
        Args:
            channel_state: État du canal
            metrics: Métriques d'analyse
            market_state: État du marché
            base_fee: Base fee recommandée
            fee_rate: Fee rate recommandé
            
        Returns:
            Liste de raisons
        """
        reasons = []
        
        # 1. Analyser les changements
        if base_fee > channel_state.base_fee:
            reasons.append(
                "Augmentation base_fee suggérée par tendance positive du volume"
            )
        elif base_fee < channel_state.base_fee:
            reasons.append(
                "Réduction base_fee suggérée pour stimuler le volume"
            )
            
        if fee_rate > channel_state.fee_rate:
            reasons.append(
                "Augmentation fee_rate basée sur forte demande"
            )
        elif fee_rate < channel_state.fee_rate:
            reasons.append(
                "Réduction fee_rate pour rester compétitif"
            )
            
        # 2. Analyser les métriques
        if metrics["trends"]["revenue"] > 0:
            reasons.append(
                "Tendance positive des revenus supporte l'ajustement"
            )
            
        if metrics["trends"]["success_rate"] < 0:
            reasons.append(
                "Baisse du taux de succès suggère ajustement nécessaire"
            )
            
        # 3. Analyser le marché
        if market_state.get("competition_level", 0) > 0.7:
            reasons.append(
                "Forte compétition influence la recommandation"
            )
            
        return reasons
        
    def _compute_window_metrics(
        self,
        channel_state: ChannelState,
        window: timedelta
    ) -> Dict[str, float]:
        """
        Calcule les métriques pour une fenêtre temporelle
        
        Args:
            channel_state: État du canal
            window: Fenêtre d'analyse
            
        Returns:
            Dict contenant les métriques calculées
        """
        start_time = datetime.now() - window
        
        # Filtrer l'historique
        forwards = [
            f for f in channel_state.forward_history
            if datetime.fromisoformat(f["timestamp"]) > start_time
        ]
        
        revenues = [
            r for r in channel_state.revenue_history
            if datetime.fromisoformat(r["timestamp"]) > start_time
        ]
        
        # Calculer les métriques
        return {
            "avg_volume": np.mean([f["amount"] for f in forwards]) if forwards else 0,
            "avg_revenue": np.mean([r["amount"] for r in revenues]) if revenues else 0,
            "success_rate": len(forwards) / (len(forwards) + len(revenues)) if forwards or revenues else 0,
            "volatility": np.std([f["amount"] for f in forwards]) if forwards else 0
        }
        
    def _calculate_trend(self, values: List[float]) -> float:
        """
        Calcule la tendance d'une série de valeurs
        
        Args:
            values: Liste de valeurs
            
        Returns:
            float: Coefficient de tendance
        """
        if not values:
            return 0.0
            
        x = np.arange(len(values))
        y = np.array(values)
        
        # Régression linéaire simple
        slope = np.polyfit(x, y, 1)[0]
        
        # Normaliser entre -1 et 1
        return max(-1.0, min(1.0, slope))
        
    def _compute_market_stats(self) -> Dict[str, Any]:
        """
        Calcule les statistiques globales du marché
        
        Returns:
            Dict contenant les stats du marché
        """
        # Pour demo, retourner des valeurs par défaut
        return {
            "avg_base_fee": 1000,
            "avg_fee_rate": 500,
            "market_volume": 1000000,
            "active_channels": 100
        }
        
    def _analyze_relative_position(
        self,
        channel_state: ChannelState,
        market_stats: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Analyse la position relative du canal
        
        Args:
            channel_state: État du canal
            market_stats: Statistiques du marché
            
        Returns:
            Dict contenant l'analyse relative
        """
        return {
            "base_fee_percentile": channel_state.base_fee / market_stats["avg_base_fee"],
            "fee_rate_percentile": channel_state.fee_rate / market_stats["avg_fee_rate"]
        }
        
    def _estimate_competition(
        self,
        channel_state: ChannelState,
        market_stats: Dict[str, Any]
    ) -> float:
        """
        Estime le niveau de compétition
        
        Args:
            channel_state: État du canal
            market_stats: Statistiques du marché
            
        Returns:
            float: Niveau de compétition (0-1)
        """
        # Simplification pour demo
        return 0.5
        
    def _explore_fees(self) -> Tuple[int, int]:
        """
        Génère des frais exploratoires
        
        Returns:
            Tuple (base_fee, fee_rate) exploratoire
        """
        base_fee = np.random.randint(
            self.fee_bounds["base_fee"]["min"],
            self.fee_bounds["base_fee"]["max"]
        )
        
        fee_rate = np.random.randint(
            self.fee_bounds["fee_rate"]["min"],
            self.fee_bounds["fee_rate"]["max"]
        )
        
        return base_fee, fee_rate
        
    def _calculate_volume_factor(self, metrics: Dict[str, Any]) -> float:
        """
        Calcule le facteur d'ajustement basé sur le volume
        
        Args:
            metrics: Métriques d'analyse
            
        Returns:
            float: Facteur d'ajustement (-1 à 1)
        """
        return metrics["trends"]["volume"]
        
    def _calculate_competition_factor(
        self,
        market_state: Dict[str, Any]
    ) -> float:
        """
        Calcule le facteur d'ajustement basé sur la compétition
        
        Args:
            market_state: État du marché
            
        Returns:
            float: Facteur d'ajustement (-1 à 1)
        """
        competition = market_state.get("competition_level", 0.5)
        return -0.5 * (competition - 0.5)
        
    def _calculate_success_factor(self, metrics: Dict[str, Any]) -> float:
        """
        Calcule le facteur d'ajustement basé sur le taux de succès
        
        Args:
            metrics: Métriques d'analyse
            
        Returns:
            float: Facteur d'ajustement (-1 à 1)
        """
        return metrics["trends"]["success_rate"]
        
    def _calculate_stability(self, metrics: Dict[str, Any]) -> float:
        """
        Calcule la stabilité des métriques
        
        Args:
            metrics: Métriques d'analyse
            
        Returns:
            float: Score de stabilité (0-1)
        """
        volatilities = [
            m.get("volatility", 0)
            for m in metrics.values()
            if isinstance(m, dict)
        ]
        
        if not volatilities:
            return 1.0
            
        # Normaliser et inverser (plus volatile = moins stable)
        max_vol = max(volatilities)
        if max_vol == 0:
            return 1.0
            
        return 1.0 - (np.mean(volatilities) / max_vol)
        
    def _estimate_improvement_factor(
        self,
        channel_state: ChannelState,
        base_fee: int,
        fee_rate: int,
        metrics: Dict[str, Any]
    ) -> float:
        """
        Estime le facteur d'amélioration attendu
        
        Args:
            channel_state: État du canal
            base_fee: Nouveau base fee
            fee_rate: Nouveau fee rate
            metrics: Métriques d'analyse
            
        Returns:
            float: Facteur d'amélioration estimé
        """
        # Simplification pour demo
        base_fee_change = abs(base_fee - channel_state.base_fee) / channel_state.base_fee
        fee_rate_change = abs(fee_rate - channel_state.fee_rate) / channel_state.fee_rate
        
        return max(
            -0.5,
            min(
                0.5,
                0.1 * (metrics["trends"]["revenue"] - 0.2 * (base_fee_change + fee_rate_change))
            )
        )
        
    def _save_recommendation(
        self,
        channel_id: str,
        base_fee: int,
        fee_rate: int,
        confidence: float,
        improvement: float
    ) -> None:
        """
        Sauvegarde une recommandation pour apprentissage
        
        Args:
            channel_id: ID du canal
            base_fee: Base fee recommandé
            fee_rate: Fee rate recommandé
            confidence: Score de confiance
            improvement: Amélioration attendue
        """
        try:
            key = f"recommendation:{channel_id}:{int(time.time())}"
            data = {
                "base_fee": base_fee,
                "fee_rate": fee_rate,
                "confidence": confidence,
                "expected_improvement": improvement,
                "timestamp": datetime.now().isoformat()
            }
            
            self.redis.setex(key, 30 * 24 * 3600, str(data))
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde recommandation: {e}")