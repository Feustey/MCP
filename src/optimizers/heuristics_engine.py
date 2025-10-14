"""
Heuristics Engine - Moteur de scoring multicritère pour canaux Lightning
Dernière mise à jour: 12 octobre 2025
Version: 1.0.0

Combine toutes les heuristiques pour calculer un score global de performance.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import yaml

import structlog

from src.optimizers.heuristics.base import BaseHeuristic, HeuristicResult
from src.optimizers.heuristics.centrality import CentralityHeuristic
from src.optimizers.heuristics.liquidity import LiquidityHeuristic
from src.optimizers.heuristics.activity import ActivityHeuristic
from src.optimizers.heuristics.competitiveness import CompetitivenessHeuristic
from src.optimizers.heuristics.reliability import ReliabilityHeuristic
from src.optimizers.heuristics.age import AgeHeuristic
from src.optimizers.heuristics.peer_quality import PeerQualityHeuristic
from src.optimizers.heuristics.position import PositionHeuristic

logger = structlog.get_logger(__name__)


@dataclass
class ChannelScore:
    """Score complet d'un canal"""
    channel_id: str
    overall_score: float  # 0.0 - 1.0
    heuristic_scores: List[HeuristicResult]
    total_weight: float
    details: Dict[str, Any]
    calculated_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            "channel_id": self.channel_id,
            "overall_score": self.overall_score,
            "heuristic_scores": [h.to_dict() for h in self.heuristic_scores],
            "total_weight": self.total_weight,
            "details": self.details,
            "calculated_at": self.calculated_at
        }
    
    def get_recommendation(self) -> str:
        """Retourne une recommandation basée sur le score"""
        if self.overall_score >= 0.8:
            return "EXCELLENT - Keep as is"
        elif self.overall_score >= 0.7:
            return "GOOD - Minor optimization possible"
        elif self.overall_score >= 0.5:
            return "AVERAGE - Consider optimization"
        elif self.overall_score >= 0.3:
            return "POOR - Optimization recommended"
        else:
            return "CRITICAL - Urgent action needed"


class HeuristicsEngine:
    """
    Moteur d'heuristiques pour scoring de canaux
    
    Combine 8 heuristiques pondérées:
    1. Centrality (20%) - Position dans le réseau
    2. Liquidity (25%) - Balance local/remote
    3. Activity (20%) - Forwarding performance
    4. Competitiveness (15%) - Fees vs réseau
    5. Reliability (10%) - Uptime et stabilité
    6. Age (5%) - Maturité du canal
    7. Peer Quality (3%) - Qualité du peer
    8. Position (2%) - Position stratégique
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        custom_weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialise le moteur d'heuristiques
        
        Args:
            config_path: Chemin vers fichier de config (YAML)
            custom_weights: Poids personnalisés pour override
        """
        # Charger la configuration
        if config_path:
            self.config = self._load_config(config_path)
        else:
            self.config = self._default_config()
        
        # Override avec poids personnalisés si fournis
        if custom_weights:
            weights = self.config.get("weights", {})
            weights.update(custom_weights)
            self.config["weights"] = weights
        
        # Initialiser les heuristiques
        self.heuristics = self._initialize_heuristics()
        
        # Vérifier que les poids totalisent ~1.0
        total_weight = sum(h.weight for h in self.heuristics if h.enabled)
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(
                "weights_not_normalized",
                total=total_weight,
                expected=1.0
            )
        
        logger.info(
            "heuristics_engine_initialized",
            heuristics_count=len(self.heuristics),
            total_weight=total_weight
        )
    
    def _default_config(self) -> Dict[str, Any]:
        """Configuration par défaut"""
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
            "enabled": {
                "centrality": True,
                "liquidity": True,
                "activity": True,
                "competitiveness": True,
                "reliability": True,
                "age": True,
                "peer_quality": True,
                "position": True
            }
        }
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Charge la configuration depuis un fichier YAML"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info("config_loaded", path=config_path)
            return config
        except Exception as e:
            logger.error("config_load_failed", error=str(e))
            return self._default_config()
    
    def _initialize_heuristics(self) -> List[BaseHeuristic]:
        """Initialise toutes les heuristiques"""
        weights = self.config.get("weights", {})
        enabled = self.config.get("enabled", {})
        
        return [
            CentralityHeuristic(
                weight=weights.get("centrality", 0.20),
                enabled=enabled.get("centrality", True)
            ),
            LiquidityHeuristic(
                weight=weights.get("liquidity", 0.25),
                enabled=enabled.get("liquidity", True)
            ),
            ActivityHeuristic(
                weight=weights.get("activity", 0.20),
                enabled=enabled.get("activity", True)
            ),
            CompetitivenessHeuristic(
                weight=weights.get("competitiveness", 0.15),
                enabled=enabled.get("competitiveness", True)
            ),
            ReliabilityHeuristic(
                weight=weights.get("reliability", 0.10),
                enabled=enabled.get("reliability", True)
            ),
            AgeHeuristic(
                weight=weights.get("age", 0.05),
                enabled=enabled.get("age", True)
            ),
            PeerQualityHeuristic(
                weight=weights.get("peer_quality", 0.03),
                enabled=enabled.get("peer_quality", True)
            ),
            PositionHeuristic(
                weight=weights.get("position", 0.02),
                enabled=enabled.get("position", True)
            )
        ]
    
    async def calculate_score(
        self,
        channel_data: Dict[str, Any],
        node_data: Optional[Dict[str, Any]] = None,
        network_data: Optional[Dict[str, Any]] = None
    ) -> ChannelScore:
        """
        Calcule le score complet d'un canal
        
        Args:
            channel_data: Données du canal
            node_data: Données du nœud peer
            network_data: Données du réseau/topologie
            
        Returns:
            Score complet avec détails
        """
        channel_id = channel_data.get("channel_id", "unknown")
        
        logger.info(
            "calculating_channel_score",
            channel_id=channel_id
        )
        
        # Calculer chaque heuristique
        heuristic_results = []
        for heuristic in self.heuristics:
            if not heuristic.enabled:
                continue
            
            try:
                result = await heuristic.calculate(
                    channel_data=channel_data,
                    node_data=node_data,
                    network_data=network_data
                )
                heuristic_results.append(result)
                
                logger.debug(
                    "heuristic_calculated",
                    channel_id=channel_id,
                    heuristic=result.name,
                    score=result.score,
                    weighted=result.weighted_score
                )
                
            except Exception as e:
                logger.error(
                    "heuristic_calculation_failed",
                    channel_id=channel_id,
                    heuristic=heuristic.name,
                    error=str(e)
                )
        
        # Calculer le score global
        total_weight = sum(h.weight for h in heuristic_results)
        overall_score = sum(h.weighted_score for h in heuristic_results)
        
        # Normaliser si nécessaire
        if total_weight != 1.0 and total_weight > 0:
            overall_score = overall_score / total_weight
        
        # Clamp entre 0 et 1
        overall_score = max(0.0, min(1.0, overall_score))
        
        # Détails supplémentaires
        details = {
            "heuristics_used": len(heuristic_results),
            "total_weight": total_weight,
            "score_distribution": {
                h.name: h.score for h in heuristic_results
            }
        }
        
        from datetime import datetime
        channel_score = ChannelScore(
            channel_id=channel_id,
            overall_score=overall_score,
            heuristic_scores=heuristic_results,
            total_weight=total_weight,
            details=details,
            calculated_at=datetime.now().isoformat()
        )
        
        logger.info(
            "channel_score_calculated",
            channel_id=channel_id,
            overall_score=overall_score,
            recommendation=channel_score.get_recommendation()
        )
        
        return channel_score
    
    async def calculate_batch_scores(
        self,
        channels: List[Dict[str, Any]],
        node_data: Optional[Dict[str, Dict[str, Any]]] = None,
        network_data: Optional[Dict[str, Any]] = None
    ) -> List[ChannelScore]:
        """
        Calcule les scores pour plusieurs canaux
        
        Args:
            channels: Liste de données de canaux
            node_data: Dict de données de nœuds (key = node_id)
            network_data: Données réseau communes
            
        Returns:
            Liste de scores
        """
        import asyncio
        
        logger.info("calculating_batch_scores", count=len(channels))
        
        tasks = []
        for channel in channels:
            peer_id = channel.get("peer_id") or channel.get("remote_pubkey")
            peer_data = node_data.get(peer_id) if node_data and peer_id else None
            
            task = self.calculate_score(channel, peer_data, network_data)
            tasks.append(task)
        
        scores = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtrer les exceptions
        valid_scores = [s for s in scores if isinstance(s, ChannelScore)]
        
        logger.info(
            "batch_scores_calculated",
            total=len(channels),
            successful=len(valid_scores),
            failed=len(channels) - len(valid_scores)
        )
        
        return valid_scores

