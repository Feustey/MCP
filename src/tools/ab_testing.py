#!/usr/bin/env python3
"""
Tests A/B avancés pour MCP - Analyse statistique et apprentissage
Dernière mise à jour: 7 mai 2025
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import scipy.stats as stats
from scipy.optimize import minimize
import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

@dataclass
class TestVariant:
    """Variante de test A/B"""
    variant_id: str
    base_fee: int
    fee_rate: int
    start_time: datetime
    end_time: Optional[datetime] = None
    metrics: Optional[Dict[str, float]] = None

@dataclass
class TestResult:
    """Résultat d'un test A/B"""
    winner_id: Optional[str]
    confidence: float
    improvement: float
    p_value: float
    metrics_comparison: Dict[str, Dict[str, float]]
    recommendations: List[str]

class ABTesting:
    """
    Système de tests A/B avancé avec analyse statistique
    et apprentissage pour l'optimisation des frais.
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        min_sample_size: int = 100,
        confidence_threshold: float = 0.95,
        effect_size_threshold: float = 0.1
    ):
        """
        Initialise le système de tests A/B
        
        Args:
            redis_url: URL de connexion Redis
            min_sample_size: Taille minimale d'échantillon
            confidence_threshold: Seuil de confiance (alpha)
            effect_size_threshold: Taille d'effet minimale
        """
        self.redis = redis.from_url(redis_url)
        self.min_sample_size = min_sample_size
        self.confidence_threshold = confidence_threshold
        self.effect_size_threshold = effect_size_threshold
        
        # Métriques à suivre
        self.metrics = {
            "revenue": {"weight": 0.4, "higher_better": True},
            "volume": {"weight": 0.3, "higher_better": True},
            "success_rate": {"weight": 0.2, "higher_better": True},
            "latency": {"weight": 0.1, "higher_better": False}
        }
        
    def create_test(
        self,
        channel_id: str,
        variants: List[Dict[str, Any]],
        duration: timedelta
    ) -> str:
        """
        Crée un nouveau test A/B
        
        Args:
            channel_id: ID du canal
            variants: Liste des variantes à tester
            duration: Durée du test
            
        Returns:
            str: ID du test
        """
        try:
            # 1. Générer l'ID du test
            test_id = f"test_{channel_id}_{int(datetime.now().timestamp())}"
            
            # 2. Créer les variantes
            test_variants = []
            start_time = datetime.now()
            
            for v in variants:
                variant = TestVariant(
                    variant_id=f"{test_id}_v{len(test_variants)}",
                    base_fee=v["base_fee"],
                    fee_rate=v["fee_rate"],
                    start_time=start_time,
                    end_time=start_time + duration
                )
                test_variants.append(variant)
                
            # 3. Sauvegarder le test
            test_data = {
                "channel_id": channel_id,
                "variants": [vars(v) for v in test_variants],
                "status": "running",
                "created_at": start_time.isoformat(),
                "end_time": (start_time + duration).isoformat()
            }
            
            key = f"ab_test:{test_id}"
            self.redis.setex(
                key,
                int(duration.total_seconds()) + 7 * 24 * 3600,  # TTL = durée + 7 jours
                str(test_data)
            )
            
            logger.info(f"Test A/B créé: {test_id}")
            return test_id
            
        except Exception as e:
            logger.error(f"Erreur création test A/B: {e}")
            raise
            
    def update_metrics(
        self,
        test_id: str,
        variant_id: str,
        metrics: Dict[str, float]
    ) -> None:
        """
        Met à jour les métriques d'une variante
        
        Args:
            test_id: ID du test
            variant_id: ID de la variante
            metrics: Nouvelles métriques
        """
        try:
            # 1. Récupérer le test
            key = f"ab_test:{test_id}"
            test_data = eval(self.redis.get(key))  # Pour demo uniquement
            
            # 2. Mettre à jour les métriques
            for variant in test_data["variants"]:
                if variant["variant_id"] == variant_id:
                    if not variant.get("metrics"):
                        variant["metrics"] = {}
                    variant["metrics"].update(metrics)
                    break
                    
            # 3. Sauvegarder
            self.redis.setex(
                key,
                7 * 24 * 3600,  # TTL 7 jours
                str(test_data)
            )
            
        except Exception as e:
            logger.error(f"Erreur mise à jour métriques: {e}")
            
    def analyze_test(self, test_id: str) -> TestResult:
        """
        Analyse les résultats d'un test A/B
        
        Args:
            test_id: ID du test
            
        Returns:
            TestResult avec l'analyse complète
        """
        try:
            # 1. Récupérer les données
            key = f"ab_test:{test_id}"
            test_data = eval(self.redis.get(key))
            
            # 2. Vérifier la taille d'échantillon
            if not self._check_sample_size(test_data["variants"]):
                return TestResult(
                    winner_id=None,
                    confidence=0.0,
                    improvement=0.0,
                    p_value=1.0,
                    metrics_comparison={},
                    recommendations=["Échantillon insuffisant"]
                )
                
            # 3. Analyser les métriques
            metrics_comparison = self._compare_metrics(test_data["variants"])
            
            # 4. Calculer les scores globaux
            scores = self._calculate_scores(metrics_comparison)
            
            # 5. Identifier le gagnant
            winner_id, confidence = self._identify_winner(
                scores,
                test_data["variants"]
            )
            
            # 6. Calculer l'amélioration
            improvement = self._calculate_improvement(
                metrics_comparison,
                winner_id
            ) if winner_id else 0.0
            
            # 7. Test statistique
            p_value = self._calculate_p_value(
                metrics_comparison,
                winner_id
            ) if winner_id else 1.0
            
            # 8. Générer les recommandations
            recommendations = self._generate_recommendations(
                metrics_comparison,
                winner_id,
                confidence,
                p_value
            )
            
            return TestResult(
                winner_id=winner_id,
                confidence=confidence,
                improvement=improvement,
                p_value=p_value,
                metrics_comparison=metrics_comparison,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Erreur analyse test: {e}")
            raise
            
    def _check_sample_size(self, variants: List[Dict[str, Any]]) -> bool:
        """
        Vérifie si la taille d'échantillon est suffisante
        
        Args:
            variants: Liste des variantes
            
        Returns:
            bool: True si échantillon suffisant
        """
        for variant in variants:
            if not variant.get("metrics"):
                return False
            
            # Vérifier chaque métrique
            for metric in self.metrics:
                if metric not in variant["metrics"]:
                    return False
                    
                # Simplification: utiliser le volume comme proxy
                if variant["metrics"].get("volume", 0) < self.min_sample_size:
                    return False
                    
        return True
        
    def _compare_metrics(
        self,
        variants: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        """
        Compare les métriques entre variantes
        
        Args:
            variants: Liste des variantes
            
        Returns:
            Dict avec comparaison des métriques
        """
        comparison = {}
        
        # Pour chaque métrique
        for metric_name in self.metrics:
            comparison[metric_name] = {}
            
            # Pour chaque variante
            for variant in variants:
                variant_id = variant["variant_id"]
                metric_value = variant["metrics"].get(metric_name, 0)
                comparison[metric_name][variant_id] = metric_value
                
        return comparison
        
    def _calculate_scores(
        self,
        metrics_comparison: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """
        Calcule les scores globaux des variantes
        
        Args:
            metrics_comparison: Comparaison des métriques
            
        Returns:
            Dict avec scores par variante
        """
        scores = {}
        
        # Pour chaque variante
        for variant_id in metrics_comparison["revenue"].keys():
            score = 0.0
            
            # Pour chaque métrique
            for metric_name, metric_config in self.metrics.items():
                metric_value = metrics_comparison[metric_name][variant_id]
                
                # Normaliser et pondérer
                normalized = self._normalize_metric(
                    metric_value,
                    metric_name,
                    metrics_comparison[metric_name].values()
                )
                
                if not metric_config["higher_better"]:
                    normalized = 1 - normalized
                    
                score += normalized * metric_config["weight"]
                
            scores[variant_id] = score
            
        return scores
        
    def _normalize_metric(
        self,
        value: float,
        metric_name: str,
        all_values: List[float]
    ) -> float:
        """
        Normalise une valeur de métrique
        
        Args:
            value: Valeur à normaliser
            metric_name: Nom de la métrique
            all_values: Toutes les valeurs de la métrique
            
        Returns:
            float: Valeur normalisée
        """
        min_val = min(all_values)
        max_val = max(all_values)
        
        if max_val == min_val:
            return 0.5
            
        return (value - min_val) / (max_val - min_val)
        
    def _identify_winner(
        self,
        scores: Dict[str, float],
        variants: List[Dict[str, Any]]
    ) -> Tuple[Optional[str], float]:
        """
        Identifie la variante gagnante
        
        Args:
            scores: Scores des variantes
            variants: Liste des variantes
            
        Returns:
            Tuple (ID gagnant, confiance)
        """
        if not scores:
            return None, 0.0
            
        # Trouver le meilleur score
        best_variant = max(scores.items(), key=lambda x: x[1])
        
        # Calculer la confiance
        confidence = self._calculate_confidence(
            best_variant[0],
            scores,
            variants
        )
        
        # Vérifier le seuil
        if confidence >= self.confidence_threshold:
            return best_variant[0], confidence
            
        return None, confidence
        
    def _calculate_confidence(
        self,
        winner_id: str,
        scores: Dict[str, float],
        variants: List[Dict[str, Any]]
    ) -> float:
        """
        Calcule la confiance dans le gagnant
        
        Args:
            winner_id: ID du gagnant
            scores: Scores des variantes
            variants: Liste des variantes
            
        Returns:
            float: Score de confiance
        """
        winner_score = scores[winner_id]
        other_scores = [s for vid, s in scores.items() if vid != winner_id]
        
        if not other_scores:
            return 1.0
            
        # Écart relatif avec le second
        best_challenger = max(other_scores)
        relative_improvement = (winner_score - best_challenger) / best_challenger
        
        # Ajuster par la taille d'échantillon
        for variant in variants:
            if variant["variant_id"] == winner_id:
                sample_size = variant["metrics"].get("volume", 0)
                sample_factor = min(1.0, sample_size / (2 * self.min_sample_size))
                break
                
        return min(1.0, relative_improvement * sample_factor)
        
    def _calculate_improvement(
        self,
        metrics_comparison: Dict[str, Dict[str, float]],
        winner_id: Optional[str]
    ) -> float:
        """
        Calcule l'amélioration apportée par le gagnant
        
        Args:
            metrics_comparison: Comparaison des métriques
            winner_id: ID du gagnant
            
        Returns:
            float: Pourcentage d'amélioration
        """
        if not winner_id:
            return 0.0
            
        improvements = []
        
        # Pour chaque métrique
        for metric_name, metric_config in self.metrics.items():
            winner_value = metrics_comparison[metric_name][winner_id]
            other_values = [
                v for k, v in metrics_comparison[metric_name].items()
                if k != winner_id
            ]
            
            if not other_values:
                continue
                
            baseline = np.mean(other_values)
            if baseline == 0:
                continue
                
            improvement = (winner_value - baseline) / baseline
            if not metric_config["higher_better"]:
                improvement = -improvement
                
            improvements.append(improvement * metric_config["weight"])
            
        return np.mean(improvements) if improvements else 0.0
        
    def _calculate_p_value(
        self,
        metrics_comparison: Dict[str, Dict[str, float]],
        winner_id: Optional[str]
    ) -> float:
        """
        Calcule la p-value du test
        
        Args:
            metrics_comparison: Comparaison des métriques
            winner_id: ID du gagnant
            
        Returns:
            float: P-value du test
        """
        if not winner_id:
            return 1.0
            
        p_values = []
        
        # Pour chaque métrique
        for metric_name in self.metrics:
            winner_value = metrics_comparison[metric_name][winner_id]
            other_values = [
                v for k, v in metrics_comparison[metric_name].items()
                if k != winner_id
            ]
            
            if not other_values:
                continue
                
            # T-test
            t_stat, p_value = stats.ttest_1samp(
                other_values,
                winner_value
            )
            p_values.append(p_value)
            
        return np.mean(p_values) if p_values else 1.0
        
    def _generate_recommendations(
        self,
        metrics_comparison: Dict[str, Dict[str, float]],
        winner_id: Optional[str],
        confidence: float,
        p_value: float
    ) -> List[str]:
        """
        Génère des recommandations basées sur l'analyse
        
        Args:
            metrics_comparison: Comparaison des métriques
            winner_id: ID du gagnant
            confidence: Score de confiance
            p_value: P-value du test
            
        Returns:
            Liste de recommandations
        """
        recommendations = []
        
        # 1. Pas de gagnant clair
        if not winner_id:
            recommendations.append(
                "Pas de gagnant clair - Continuer le test"
            )
            
            if confidence < self.confidence_threshold:
                recommendations.append(
                    f"Confiance insuffisante ({confidence:.1%}) - "
                    f"Augmenter la taille d'échantillon"
                )
                
        # 2. Gagnant avec haute confiance
        elif confidence > 0.9:
            recommendations.append(
                f"Adopter la configuration de {winner_id}"
            )
            
        # 3. Gagnant avec confiance moyenne
        else:
            recommendations.append(
                f"Gagnant provisoire {winner_id} - "
                f"Confiance: {confidence:.1%}"
            )
            
        # 4. Analyse par métrique
        for metric_name, metric_config in self.metrics.items():
            values = metrics_comparison[metric_name]
            best_id = max(values.items(), key=lambda x: x[1])[0]
            
            if best_id != winner_id:
                recommendations.append(
                    f"Note: {best_id} meilleur pour {metric_name}"
                )
                
        # 5. Significativité statistique
        if p_value > 0.05:
            recommendations.append(
                f"Différence non statistiquement significative "
                f"(p={p_value:.3f})"
            )
            
        return recommendations 