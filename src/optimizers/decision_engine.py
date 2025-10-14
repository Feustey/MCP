"""
Decision Engine - Moteur de décision pour optimisation des canaux
Dernière mise à jour: 12 octobre 2025
Version: 1.0.0

Prend des décisions basées sur:
- Scores des heuristiques
- Thresholds configurables
- Règles business
- Contraintes de sécurité

Types de décisions:
- NO_ACTION
- INCREASE_FEES
- DECREASE_FEES
- REBALANCE
- CLOSE_CHANNEL
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import yaml

import structlog

from src.optimizers.heuristics_engine import ChannelScore

logger = structlog.get_logger(__name__)


class DecisionType(Enum):
    """Types de décisions possibles"""
    NO_ACTION = "no_action"
    INCREASE_FEES = "increase_fees"
    DECREASE_FEES = "decrease_fees"
    REBALANCE = "rebalance"
    CLOSE_CHANNEL = "close_channel"


class DecisionConfidence(Enum):
    """Niveau de confiance dans la décision"""
    HIGH = "high"  # >0.8
    MEDIUM = "medium"  # 0.5-0.8
    LOW = "low"  # <0.5


@dataclass
class Decision:
    """Décision d'optimisation pour un canal"""
    channel_id: str
    decision_type: DecisionType
    confidence: DecisionConfidence
    confidence_score: float  # 0.0 - 1.0
    reasoning: str
    recommended_changes: Dict[str, Any]
    current_state: Dict[str, Any]
    expected_impact: str
    score_details: ChannelScore
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            "channel_id": self.channel_id,
            "decision_type": self.decision_type.value,
            "confidence": self.confidence.value,
            "confidence_score": self.confidence_score,
            "reasoning": self.reasoning,
            "recommended_changes": self.recommended_changes,
            "current_state": self.current_state,
            "expected_impact": self.expected_impact,
            "score": self.score_details.overall_score,
            "score_details": self.score_details.to_dict(),
            "timestamp": self.timestamp
        }


class DecisionEngine:
    """
    Moteur de décision pour optimisation
    
    Workflow:
    1. Analyse du score global
    2. Analyse des heuristiques individuelles
    3. Application des règles business
    4. Génération de la recommandation
    5. Calcul de la confiance
    """
    
    def __init__(
        self,
        config_path: str = "config/decision_thresholds.yaml",
        custom_thresholds: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise le moteur de décision
        
        Args:
            config_path: Chemin vers config des thresholds
            custom_thresholds: Thresholds personnalisés
        """
        # Charger la configuration
        self.config = self._load_config(config_path)
        
        # Override avec thresholds personnalisés
        if custom_thresholds:
            self.config["thresholds"].update(custom_thresholds)
        
        self.thresholds = self.config.get("thresholds", {})
        self.weights = self.config.get("weights", {})
        self.fee_adjustments = self.config.get("fee_adjustments", {})
        self.safety = self.config.get("safety", {})
        
        logger.info(
            "decision_engine_initialized",
            thresholds=list(self.thresholds.keys())
        )
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Charge la configuration depuis YAML"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info("decision_config_loaded", path=config_path)
            return config
        except Exception as e:
            logger.error("config_load_failed", error=str(e))
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Configuration par défaut si fichier absent"""
        return {
            "thresholds": {
                "optimal_min": 0.7,
                "increase_threshold": 0.3,
                "decrease_threshold": 0.5,
                "rebalance_ratio_high": 0.8,
                "rebalance_ratio_low": 0.2,
                "close_threshold": 0.1,
                "close_inactivity_days": 30
            },
            "fee_adjustments": {
                "max_increase_percent": 50,
                "max_decrease_percent": 30,
                "small_adjustment": 5,
                "medium_adjustment": 15,
                "large_adjustment": 30
            }
        }
    
    async def make_decision(
        self,
        score: ChannelScore,
        channel_data: Dict[str, Any]
    ) -> Decision:
        """
        Prend une décision basée sur le score
        
        Args:
            score: Score calculé du canal
            channel_data: Données actuelles du canal
            
        Returns:
            Décision avec recommandations
        """
        channel_id = score.channel_id
        overall_score = score.overall_score
        
        logger.info(
            "making_decision",
            channel_id=channel_id,
            score=overall_score
        )
        
        # 1. Score optimal → NO_ACTION
        if overall_score >= self.thresholds["optimal_min"]:
            return self._decision_no_action(score, channel_data)
        
        # 2. Score très bas → envisager fermeture
        if overall_score <= self.thresholds["close_threshold"]:
            # Vérifier inactivité
            inactivity_days = channel_data.get("days_since_last_forward", 0)
            if inactivity_days >= self.thresholds["close_inactivity_days"]:
                return self._decision_close_channel(score, channel_data)
        
        # 3. Vérifier déséquilibre liquidité → REBALANCE
        local_balance = channel_data.get("local_balance", 0)
        capacity = channel_data.get("capacity", 1)
        local_ratio = local_balance / capacity if capacity > 0 else 0.5
        
        if local_ratio >= self.thresholds["rebalance_ratio_high"]:
            return self._decision_rebalance(score, channel_data, "high_local")
        elif local_ratio <= self.thresholds["rebalance_ratio_low"]:
            return self._decision_rebalance(score, channel_data, "high_remote")
        
        # 4. Score bas et faible activité → INCREASE_FEES
        if overall_score <= self.thresholds["increase_threshold"]:
            activity_score = self._get_heuristic_score(score, "Activity")
            if activity_score and activity_score < 0.4:
                return self._decision_increase_fees(score, channel_data)
        
        # 5. Score moyen et fees trop élevés → DECREASE_FEES
        if overall_score <= self.thresholds["decrease_threshold"]:
            competitiveness_score = self._get_heuristic_score(score, "Competitiveness")
            if competitiveness_score and competitiveness_score < 0.5:
                return self._decision_decrease_fees(score, channel_data)
        
        # 6. Par défaut → NO_ACTION (avec warning)
        return self._decision_no_action(score, channel_data, warning=True)
    
    def _get_heuristic_score(self, channel_score: ChannelScore, heuristic_name: str) -> Optional[float]:
        """Récupère le score d'une heuristique spécifique"""
        for h in channel_score.heuristic_scores:
            if h.name == heuristic_name:
                return h.score
        return None
    
    def _decision_no_action(
        self,
        score: ChannelScore,
        channel_data: Dict[str, Any],
        warning: bool = False
    ) -> Decision:
        """Décision: Aucune action requise"""
        reasoning = f"Channel score is optimal ({score.overall_score:.2f})"
        if warning:
            reasoning += " but some metrics could be improved"
        
        confidence_score = score.overall_score
        confidence = self._calculate_confidence(confidence_score)
        
        return Decision(
            channel_id=score.channel_id,
            decision_type=DecisionType.NO_ACTION,
            confidence=confidence,
            confidence_score=confidence_score,
            reasoning=reasoning,
            recommended_changes={},
            current_state=self._extract_current_state(channel_data),
            expected_impact="No changes expected",
            score_details=score,
            timestamp=datetime.now().isoformat()
        )
    
    def _decision_increase_fees(
        self,
        score: ChannelScore,
        channel_data: Dict[str, Any]
    ) -> Decision:
        """Décision: Augmenter les fees"""
        current_base_fee = channel_data.get("base_fee_msat", 1000)
        current_fee_rate = channel_data.get("fee_rate_ppm", 100)
        
        # Calculer l'augmentation (basée sur le score)
        # Score très bas → grande augmentation
        if score.overall_score < 0.2:
            increase_percent = self.fee_adjustments["large_adjustment"]
        elif score.overall_score < 0.3:
            increase_percent = self.fee_adjustments["medium_adjustment"]
        else:
            increase_percent = self.fee_adjustments["small_adjustment"]
        
        # Appliquer l'augmentation
        new_base_fee = int(current_base_fee * (1 + increase_percent / 100))
        new_fee_rate = int(current_fee_rate * (1 + increase_percent / 100))
        
        # Respecter les limites max
        new_base_fee = min(new_base_fee, self.fee_adjustments.get("max_base_fee_msat", 10000))
        new_fee_rate = min(new_fee_rate, self.fee_adjustments.get("max_fee_rate_ppm", 10000))
        
        reasoning = (
            f"Channel underperforming (score={score.overall_score:.2f}). "
            f"Low activity suggests fees may be too low. "
            f"Increasing fees by {increase_percent}% to test demand."
        )
        
        confidence_score = 0.7  # Moyenne car basé sur peu d'activité
        confidence = self._calculate_confidence(confidence_score)
        
        return Decision(
            channel_id=score.channel_id,
            decision_type=DecisionType.INCREASE_FEES,
            confidence=confidence,
            confidence_score=confidence_score,
            reasoning=reasoning,
            recommended_changes={
                "base_fee_msat": new_base_fee,
                "fee_rate_ppm": new_fee_rate,
                "change_percent": increase_percent
            },
            current_state=self._extract_current_state(channel_data),
            expected_impact=f"May reduce volume but increase revenue per forward",
            score_details=score,
            timestamp=datetime.now().isoformat()
        )
    
    def _decision_decrease_fees(
        self,
        score: ChannelScore,
        channel_data: Dict[str, Any]
    ) -> Decision:
        """Décision: Diminuer les fees"""
        current_base_fee = channel_data.get("base_fee_msat", 1000)
        current_fee_rate = channel_data.get("fee_rate_ppm", 100)
        
        # Calculer la diminution
        decrease_percent = self.fee_adjustments["medium_adjustment"]
        
        # Appliquer la diminution
        new_base_fee = int(current_base_fee * (1 - decrease_percent / 100))
        new_fee_rate = int(current_fee_rate * (1 - decrease_percent / 100))
        
        # Respecter les limites min
        new_base_fee = max(new_base_fee, self.fee_adjustments.get("min_base_fee_msat", 0))
        new_fee_rate = max(new_fee_rate, self.fee_adjustments.get("min_fee_rate_ppm", 1))
        
        reasoning = (
            f"Channel score moderate (score={score.overall_score:.2f}). "
            f"Fees appear non-competitive vs network. "
            f"Decreasing fees by {decrease_percent}% to stimulate activity."
        )
        
        confidence_score = 0.75
        confidence = self._calculate_confidence(confidence_score)
        
        return Decision(
            channel_id=score.channel_id,
            decision_type=DecisionType.DECREASE_FEES,
            confidence=confidence,
            confidence_score=confidence_score,
            reasoning=reasoning,
            recommended_changes={
                "base_fee_msat": new_base_fee,
                "fee_rate_ppm": new_fee_rate,
                "change_percent": -decrease_percent
            },
            current_state=self._extract_current_state(channel_data),
            expected_impact=f"May increase volume and total fees earned",
            score_details=score,
            timestamp=datetime.now().isoformat()
        )
    
    def _decision_rebalance(
        self,
        score: ChannelScore,
        channel_data: Dict[str, Any],
        reason: str
    ) -> Decision:
        """Décision: Rééquilibrer le canal"""
        local_balance = channel_data.get("local_balance", 0)
        remote_balance = channel_data.get("remote_balance", 0)
        capacity = local_balance + remote_balance
        
        local_ratio = local_balance / capacity if capacity > 0 else 0.5
        
        if reason == "high_local":
            reasoning = (
                f"Channel has too much local balance ({local_ratio * 100:.1f}%). "
                f"Rebalancing recommended to enable outbound routing."
            )
            target_amount = int((local_ratio - 0.5) * capacity)
        else:  # high_remote
            reasoning = (
                f"Channel has too much remote balance ({(1-local_ratio) * 100:.1f}%). "
                f"Rebalancing recommended to enable inbound routing."
            )
            target_amount = int((0.5 - local_ratio) * capacity)
        
        confidence_score = 0.8
        confidence = self._calculate_confidence(confidence_score)
        
        return Decision(
            channel_id=score.channel_id,
            decision_type=DecisionType.REBALANCE,
            confidence=confidence,
            confidence_score=confidence_score,
            reasoning=reasoning,
            recommended_changes={
                "rebalance_amount_sats": abs(target_amount),
                "direction": "outbound" if reason == "high_local" else "inbound",
                "target_ratio": 0.5
            },
            current_state=self._extract_current_state(channel_data),
            expected_impact="Improved bidirectional routing capability",
            score_details=score,
            timestamp=datetime.now().isoformat()
        )
    
    def _decision_close_channel(
        self,
        score: ChannelScore,
        channel_data: Dict[str, Any]
    ) -> Decision:
        """Décision: Fermer le canal"""
        inactivity_days = channel_data.get("days_since_last_forward", 0)
        
        reasoning = (
            f"Channel critically underperforming (score={score.overall_score:.2f}). "
            f"Inactive for {inactivity_days} days. "
            f"Consider closing to free up capital."
        )
        
        # Estimer les coûts de fermeture
        onchain_fee_estimate = channel_data.get("estimated_close_fee_sats", 1000)
        
        confidence_score = 0.6  # Modérée car fermeture est définitive
        confidence = self._calculate_confidence(confidence_score)
        
        return Decision(
            channel_id=score.channel_id,
            decision_type=DecisionType.CLOSE_CHANNEL,
            confidence=confidence,
            confidence_score=confidence_score,
            reasoning=reasoning,
            recommended_changes={
                "action": "close",
                "estimated_onchain_fee": onchain_fee_estimate,
                "force_close": False  # Cooperative close préféré
            },
            current_state=self._extract_current_state(channel_data),
            expected_impact=f"Free up {channel_data.get('capacity', 0):,} sats for better channels",
            score_details=score,
            timestamp=datetime.now().isoformat()
        )
    
    def _calculate_confidence(self, score: float) -> DecisionConfidence:
        """Calcule le niveau de confiance"""
        if score >= 0.8:
            return DecisionConfidence.HIGH
        elif score >= 0.5:
            return DecisionConfidence.MEDIUM
        else:
            return DecisionConfidence.LOW
    
    def _extract_current_state(self, channel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrait l'état actuel du canal"""
        return {
            "base_fee_msat": channel_data.get("base_fee_msat", 0),
            "fee_rate_ppm": channel_data.get("fee_rate_ppm", 0),
            "local_balance": channel_data.get("local_balance", 0),
            "remote_balance": channel_data.get("remote_balance", 0),
            "capacity": channel_data.get("capacity", 0)
        }
    
    async def batch_decisions(
        self,
        scores: List[ChannelScore],
        channels_data: Dict[str, Dict[str, Any]]
    ) -> List[Decision]:
        """
        Prend des décisions pour plusieurs canaux
        
        Args:
            scores: Liste des scores calculés
            channels_data: Dict des données canaux (key = channel_id)
            
        Returns:
            Liste des décisions
        """
        import asyncio
        
        logger.info("making_batch_decisions", count=len(scores))
        
        tasks = []
        for score in scores:
            channel_data = channels_data.get(score.channel_id, {})
            task = self.make_decision(score, channel_data)
            tasks.append(task)
        
        decisions = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtrer les exceptions
        valid_decisions = [d for d in decisions if isinstance(d, Decision)]
        
        # Statistiques
        decision_stats = {
            DecisionType.NO_ACTION: 0,
            DecisionType.INCREASE_FEES: 0,
            DecisionType.DECREASE_FEES: 0,
            DecisionType.REBALANCE: 0,
            DecisionType.CLOSE_CHANNEL: 0
        }
        
        for decision in valid_decisions:
            decision_stats[decision.decision_type] += 1
        
        logger.info(
            "batch_decisions_completed",
            total=len(scores),
            successful=len(valid_decisions),
            stats={k.value: v for k, v in decision_stats.items()}
        )
        
        return valid_decisions

