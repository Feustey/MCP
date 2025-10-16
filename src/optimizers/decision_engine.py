#!/usr/bin/env python3
"""
Decision Engine - Moteur de décision pour l'optimisation des canaux Lightning

Ce module centralise la logique de décision pour déterminer les actions à prendre
sur chaque canal basé sur les 8 heuristiques et les thresholds configurables.

Décisions possibles:
- NO_ACTION: Canal optimal, rien à faire
- INCREASE_FEES: Augmenter les frais (canal sous-utilisé)
- DECREASE_FEES: Baisser les frais (canal sur-pricé)
- REBALANCE: Rééquilibrer le canal (déséquilibre liquidité)
- CLOSE_CHANNEL: Fermer le canal (performance très faible)

Dernière mise à jour: 15 octobre 2025
"""

import logging
import yaml
from enum import Enum
from typing import Dict, Any, Tuple
from pathlib import Path

# Importer toutes les heuristiques
from src.optimizers.heuristics import (
    calculate_centrality_score,
    calculate_liquidity_score,
    calculate_activity_score,
    calculate_competitiveness_score,
    calculate_reliability_score,
    calculate_age_stability_score,
    calculate_peer_quality_score,
    calculate_network_position_score
)

logger = logging.getLogger(__name__)

# Charger configuration
CONFIG_FILE = Path("config/decision_thresholds.yaml")


class DecisionType(Enum):
    """Types de décisions possibles."""
    NO_ACTION = "no_action"
    INCREASE_FEES = "increase_fees"
    DECREASE_FEES = "decrease_fees"
    REBALANCE = "rebalance"
    CLOSE_CHANNEL = "close_channel"


class DecisionEngine:
    """
    Moteur de décision pur et déterministe pour l'optimisation des canaux.
    
    Fonction pure: mêmes inputs → même output
    Pas d'effets de bord
    Facilement testable
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialise le moteur avec la configuration.
        
        Args:
            config_path: Chemin vers fichier de configuration (optionnel)
        """
        self.config = self._load_config(config_path or str(CONFIG_FILE))
        self.weights = self.config.get("weights", {})
        self.thresholds = self.config.get("thresholds", {})
        self.decision_rules = self.config.get("decision_rules", {})
        
        logger.info(f"DecisionEngine initialisé avec config: {config_path or CONFIG_FILE}")
    
    def _load_config(self, config_path: str) -> Dict:
        """Charge la configuration depuis le fichier YAML."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            logger.warning(f"Impossible de charger la config {config_path}: {e}. Utilisation des valeurs par défaut.")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Configuration par défaut si fichier non disponible."""
        return {
            "weights": {
                "centrality": 0.20,
                "liquidity": 0.25,
                "activity": 0.20,
                "competitiveness": 0.15,
                "reliability": 0.10,
                "age": 0.05,
                "peer_quality": 0.03,
                "position": 0.02
            },
            "thresholds": {
                "optimal_min": 0.7,
                "increase_threshold": 0.3,
                "decrease_threshold": 0.5,
                "rebalance_ratio_max": 0.8,
                "rebalance_ratio_min": 0.2,
                "close_threshold": 0.1,
                "close_inactivity_days": 30
            },
            "decision_rules": {
                "min_confidence": 0.6,
                "max_fee_increase_ppm": 1000,
                "max_fee_decrease_pct": 0.5,
                "rebalance_target_ratio": 0.5
            }
        }
    
    def evaluate_channel(
        self,
        channel: Dict[str, Any],
        node_data: Dict[str, Any],
        network_graph: Dict[str, Any] = None,
        network_stats: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Évalue un canal et retourne une décision.
        
        Fonction PURE: pas d'effets de bord.
        
        Args:
            channel: Données du canal
            node_data: Données du nœud
            network_graph: Graphe du réseau (optionnel)
            network_stats: Stats du réseau (optionnel)
        
        Returns:
            Dict contenant:
                - decision: DecisionType
                - confidence: float (0-1)
                - total_score: float (0-1)
                - scores: Dict des scores individuels
                - reasoning: str expliquant la décision
                - params: Dict des paramètres suggérés
        """
        # 1. Calculer tous les scores
        scores = self._calculate_all_scores(channel, node_data, network_graph, network_stats)
        
        # 2. Calculer le score composite
        total_score = self._calculate_composite_score(scores)
        
        # 3. Déterminer la décision
        decision, confidence, reasoning, params = self._determine_decision(
            total_score, scores, channel, node_data
        )
        
        return {
            "decision": decision,
            "confidence": confidence,
            "total_score": total_score,
            "scores": scores,
            "reasoning": reasoning,
            "params": params,
            "channel_id": channel.get("channel_id"),
            "timestamp": channel.get("timestamp")
        }
    
    def _calculate_all_scores(
        self,
        channel: Dict[str, Any],
        node_data: Dict[str, Any],
        network_graph: Dict[str, Any] = None,
        network_stats: Dict[str, Any] = None
    ) -> Dict[str, float]:
        """
        Calcule tous les scores d'heuristiques.
        
        Returns:
            Dict avec tous les scores normalisés (0-1)
        """
        return {
            "centrality": calculate_centrality_score(channel, node_data, network_graph) / 100,
            "liquidity": calculate_liquidity_score(channel, node_data) / 100,
            "activity": calculate_activity_score(channel, node_data) / 100,
            "competitiveness": calculate_competitiveness_score(channel, node_data, network_stats) / 100,
            "reliability": calculate_reliability_score(channel, node_data) / 100,
            "age": calculate_age_stability_score(channel, node_data) / 100,
            "peer_quality": calculate_peer_quality_score(channel, node_data) / 100,
            "position": calculate_network_position_score(channel, node_data, network_graph) / 100
        }
    
    def _calculate_composite_score(self, scores: Dict[str, float]) -> float:
        """
        Calcule le score composite pondéré.
        
        Returns:
            Score entre 0 et 1
        """
        total = 0.0
        for heuristic, score in scores.items():
            weight = self.weights.get(heuristic, 0.0)
            total += score * weight
        
        return min(1.0, max(0.0, total))
    
    def _determine_decision(
        self,
        total_score: float,
        scores: Dict[str, float],
        channel: Dict[str, Any],
        node_data: Dict[str, Any]
    ) -> Tuple[DecisionType, float, str, Dict]:
        """
        Détermine la décision à prendre basée sur les scores.
        
        Returns:
            (decision, confidence, reasoning, params)
        """
        # Récupérer les thresholds
        optimal_min = self.thresholds.get("optimal_min", 0.7)
        increase_threshold = self.thresholds.get("increase_threshold", 0.3)
        decrease_threshold = self.thresholds.get("decrease_threshold", 0.5)
        close_threshold = self.thresholds.get("close_threshold", 0.1)
        
        # Analyser les scores individuels
        liquidity_score = scores.get("liquidity", 0.5)
        activity_score = scores.get("activity", 0.5)
        competitiveness_score = scores.get("competitiveness", 0.5)
        
        # Calculer liquidité ratio
        local = int(channel.get("local_balance", 0))
        remote = int(channel.get("remote_balance", 0))
        total_balance = local + remote
        liquidity_ratio = local / total_balance if total_balance > 0 else 0.5
        
        # Décision 1: CLOSE_CHANNEL (prioritaire)
        if total_score < close_threshold and activity_score < 0.15:
            return (
                DecisionType.CLOSE_CHANNEL,
                0.95,  # Haute confiance pour fermeture
                f"Score très faible ({total_score:.2f}) et inactivité prolongée. Canal non performant.",
                {"close_type": "cooperative", "reason": "low_performance"}
            )
        
        # Décision 2: REBALANCE
        rebalance_max = self.thresholds.get("rebalance_ratio_max", 0.8)
        rebalance_min = self.thresholds.get("rebalance_ratio_min", 0.2)
        
        if liquidity_ratio > rebalance_max or liquidity_ratio < rebalance_min:
            target_ratio = self.decision_rules.get("rebalance_target_ratio", 0.5)
            amount_to_move = abs((liquidity_ratio - target_ratio) * total_balance)
            
            return (
                DecisionType.REBALANCE,
                0.85,
                f"Déséquilibre de liquidité important (ratio: {liquidity_ratio:.2f}). Rééquilibrage nécessaire.",
                {
                    "target_ratio": target_ratio,
                    "amount_sats": int(amount_to_move),
                    "direction": "outbound" if liquidity_ratio > 0.5 else "inbound"
                }
            )
        
        # Décision 3: INCREASE_FEES
        if (activity_score > 0.7 and liquidity_ratio > 0.65) or \
           (total_score > optimal_min and liquidity_ratio > 0.7):
            current_policy = channel.get("policy", {})
            current_rate = int(current_policy.get("fee_rate_ppm", 500))
            max_increase = self.decision_rules.get("max_fee_increase_ppm", 1000)
            suggested_rate = min(current_rate + 200, current_rate + max_increase)
            
            return (
                DecisionType.INCREASE_FEES,
                0.75,
                f"Canal très actif avec excès de liquidité locale. Augmenter les frais pour optimiser revenue.",
                {
                    "current_fee_rate": current_rate,
                    "suggested_fee_rate": suggested_rate,
                    "increase_ppm": suggested_rate - current_rate
                }
            )
        
        # Décision 4: DECREASE_FEES
        if (competitiveness_score < 0.4 and activity_score < 0.4) or \
           (total_score < decrease_threshold and total_score >= increase_threshold):
            current_policy = channel.get("policy", {})
            current_rate = int(current_policy.get("fee_rate_ppm", 500))
            max_decrease_pct = self.decision_rules.get("max_fee_decrease_pct", 0.5)
            suggested_rate = max(1, int(current_rate * (1 - 0.2)))  # -20%
            suggested_rate = max(suggested_rate, int(current_rate * max_decrease_pct))
            
            return (
                DecisionType.DECREASE_FEES,
                0.70,
                f"Frais peu compétitifs avec faible activité. Baisse recommandée pour attirer du routing.",
                {
                    "current_fee_rate": current_rate,
                    "suggested_fee_rate": suggested_rate,
                    "decrease_pct": ((current_rate - suggested_rate) / current_rate) * 100
                }
            )
        
        # Décision 5: NO_ACTION (défaut)
        return (
            DecisionType.NO_ACTION,
            0.80,
            f"Canal performant (score: {total_score:.2f}). Paramètres actuels optimaux.",
            {}
        )
    
    def batch_evaluate_channels(
        self,
        channels: list,
        node_data: Dict[str, Any],
        network_graph: Dict[str, Any] = None,
        network_stats: Dict[str, Any] = None
    ) -> list:
        """
        Évalue un batch de canaux.
        
        Returns:
            Liste des évaluations triées par confiance décroissante
        """
        evaluations = []
        
        for channel in channels:
            try:
                eval_result = self.evaluate_channel(
                    channel, node_data, network_graph, network_stats
                )
                evaluations.append(eval_result)
            except Exception as e:
                logger.error(f"Erreur évaluation canal {channel.get('channel_id')}: {e}")
                continue
        
        # Trier par confiance décroissante
        evaluations.sort(key=lambda x: x["confidence"], reverse=True)
        
        return evaluations
    
    def get_actionable_decisions(
        self,
        evaluations: list,
        min_confidence: float = None
    ) -> list:
        """
        Filtre les décisions actionnables (non NO_ACTION) avec confiance suffisante.
        
        Args:
            evaluations: Liste des évaluations
            min_confidence: Confiance minimale (utilise config si None)
        
        Returns:
            Liste des décisions actionnables
        """
        min_conf = min_confidence or self.decision_rules.get("min_confidence", 0.6)
        
        actionable = [
            e for e in evaluations
            if e["decision"] != DecisionType.NO_ACTION and e["confidence"] >= min_conf
        ]
        
        return actionable


# Fonction utilitaire pour usage direct
def evaluate_channel_simple(
    channel: Dict[str, Any],
    node_data: Dict[str, Any],
    config_path: str = None
) -> Dict[str, Any]:
    """
    Fonction utilitaire pour évaluer un canal rapidement.
    
    Args:
        channel: Données du canal
        node_data: Données du nœud
        config_path: Chemin config (optionnel)
    
    Returns:
        Résultat de l'évaluation
    """
    engine = DecisionEngine(config_path)
    return engine.evaluate_channel(channel, node_data)


# CLI pour tests
if __name__ == "__main__":
    import json
    import sys
    
    # Exemple d'utilisation
    if len(sys.argv) < 2:
        print("Usage: python decision_engine.py <channel_data.json>")
        sys.exit(1)
    
    with open(sys.argv[1], 'r') as f:
        data = json.load(f)
    
    channel = data.get("channel", {})
    node_data = data.get("node_data", {})
    
    result = evaluate_channel_simple(channel, node_data)
    
    print(json.dumps(result, indent=2, default=str))
