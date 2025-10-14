"""
Competitiveness Heuristic - Heuristique de compétitivité des fees

Évalue la compétitivité des fees d'un canal par rapport au réseau
et aux canaux similaires.

Métriques:
- Position par rapport à la médiane réseau
- Comparaison avec peers similaires
- Écart-type du pricing
- Attractivité pour le routage

Auteur: MCP Team
Date: 13 octobre 2025
"""

from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class CompetitivenessHeuristic:
    """
    Calcule le score de compétitivité des fees.
    
    Score élevé = fees compétitifs et attractifs
    """
    
    def __init__(self, weight: float = 0.15):
        """
        Initialise l'heuristique.
        
        Args:
            weight: Poids de cette heuristique (défaut: 15%)
        """
        self.weight = weight
        self.name = "Competitiveness"
        
        # Statistiques réseau typiques (mise à jour périodique)
        self.network_median_base_fee = 1000  # msat
        self.network_median_fee_rate = 100  # ppm
        
        logger.info("competitiveness_heuristic_initialized", weight=weight)
    
    def calculate(self,
                 channel_data: Dict[str, Any],
                 network_stats: Optional[Dict[str, Any]] = None) -> float:
        """
        Calcule le score de compétitivité.
        
        Args:
            channel_data: Données du canal
            network_stats: Statistiques réseau (optionnel)
            
        Returns:
            Score 0.0 - 1.0
        """
        # Récupérer les fees actuels
        base_fee = channel_data.get("base_fee_msat", 0)
        fee_rate = channel_data.get("fee_rate_ppm", 0)
        
        # Mise à jour stats réseau si disponibles
        if network_stats:
            self.network_median_base_fee = network_stats.get("median_base_fee", self.network_median_base_fee)
            self.network_median_fee_rate = network_stats.get("median_fee_rate", self.network_median_fee_rate)
        
        # Calculer les ratios par rapport à la médiane
        base_fee_ratio = self._calculate_fee_ratio(base_fee, self.network_median_base_fee)
        fee_rate_ratio = self._calculate_fee_ratio(fee_rate, self.network_median_fee_rate)
        
        # Score basé sur la proximité à la médiane
        # Fees trop élevés = moins compétitif
        # Fees trop bas = peut-être sous-optimisé
        base_score = self._score_from_ratio(base_fee_ratio)
        rate_score = self._score_from_ratio(fee_rate_ratio)
        
        # Score composite (fee_rate plus important)
        competitiveness_score = (
            base_score * 0.30 +
            rate_score * 0.70
        )
        
        logger.debug("competitiveness_calculated",
                    channel_id=channel_data.get("channel_id"),
                    base_fee=base_fee,
                    fee_rate=fee_rate,
                    base_ratio=base_fee_ratio,
                    rate_ratio=fee_rate_ratio,
                    score=competitiveness_score)
        
        return max(0.0, min(1.0, competitiveness_score))
    
    def _calculate_fee_ratio(self, actual_fee: int, median_fee: int) -> float:
        """
        Calcule le ratio actuel/médiane.
        
        Args:
            actual_fee: Fee actuel
            median_fee: Fee médian du réseau
            
        Returns:
            Ratio
        """
        if median_fee == 0:
            return 1.0
        
        return actual_fee / median_fee
    
    def _score_from_ratio(self, ratio: float) -> float:
        """
        Convertit un ratio en score.
        
        Optimal: ratio proche de 1.0 (égal à la médiane)
        Acceptable: 0.5 - 2.0 (50% moins à 2x plus)
        Non compétitif: > 2.0 ou < 0.5
        
        Args:
            ratio: Ratio fee/médiane
            
        Returns:
            Score 0.0 - 1.0
        """
        if ratio < 0.5:
            # Trop bas (0.5x ou moins)
            # Score = ratio / 0.5 (0 si gratuit, 1 si 0.5x médiane)
            return ratio / 0.5
        
        elif ratio <= 1.5:
            # Zone optimale (0.5x - 1.5x médiane)
            # Score parfait
            return 1.0
        
        elif ratio <= 3.0:
            # Assez élevé (1.5x - 3x médiane)
            # Score décroît linéairement
            return 1.0 - ((ratio - 1.5) / 1.5) * 0.5
        
        else:
            # Très élevé (> 3x médiane)
            # Score faible
            return max(0.0, 0.5 - ((ratio - 3.0) / 10.0))
    
    def get_pricing_tier(self, channel_data: Dict[str, Any]) -> str:
        """
        Retourne le tier de pricing.
        
        Args:
            channel_data: Données du canal
            
        Returns:
            Tier: "very_cheap", "cheap", "competitive", "expensive", "very_expensive"
        """
        fee_rate = channel_data.get("fee_rate_ppm", 0)
        ratio = fee_rate / self.network_median_fee_rate
        
        if ratio < 0.5:
            return "very_cheap"
        elif ratio < 0.8:
            return "cheap"
        elif ratio <= 1.5:
            return "competitive"
        elif ratio <= 3.0:
            return "expensive"
        else:
            return "very_expensive"
    
    def get_explanation(self, score: float, channel_data: Dict[str, Any]) -> str:
        """
        Génère une explication du score.
        
        Args:
            score: Score calculé
            channel_data: Données du canal
            
        Returns:
            Explication textuelle
        """
        tier = self.get_pricing_tier(channel_data)
        
        base_fee = channel_data.get("base_fee_msat", 0)
        fee_rate = channel_data.get("fee_rate_ppm", 0)
        
        base_ratio = base_fee / self.network_median_base_fee
        rate_ratio = fee_rate / self.network_median_fee_rate
        
        explanations = {
            "very_cheap": f"Very low fees ({rate_ratio:.1f}x median) - may be underpricing",
            "cheap": f"Below-market fees ({rate_ratio:.1f}x median) - competitive for volume",
            "competitive": f"Market-rate fees ({rate_ratio:.1f}x median) - well positioned",
            "expensive": f"Above-market fees ({rate_ratio:.1f}x median) - may limit routing",
            "very_expensive": f"Very high fees ({rate_ratio:.1f}x median) - likely non-competitive"
        }
        
        return explanations.get(tier, "Pricing status unclear")
    
    def suggest_fee_adjustment(self, 
                              channel_data: Dict[str, Any],
                              target_percentile: float = 50.0) -> Dict[str, int]:
        """
        Suggère un ajustement de fees pour atteindre un percentile cible.
        
        Args:
            channel_data: Données du canal
            target_percentile: Percentile cible (défaut: 50 = médiane)
            
        Returns:
            Dict avec base_fee_msat et fee_rate_ppm suggérés
        """
        # Convertir percentile en ratio
        # 50th percentile = 1.0x médiane
        # 25th percentile = 0.75x médiane
        # 75th percentile = 1.25x médiane
        ratio = 0.5 + (target_percentile / 100)
        
        suggested_base = int(self.network_median_base_fee * ratio)
        suggested_rate = int(self.network_median_fee_rate * ratio)
        
        logger.info("fee_adjustment_suggested",
                   channel_id=channel_data.get("channel_id"),
                   suggested_base=suggested_base,
                   suggested_rate=suggested_rate,
                   target_percentile=target_percentile)
        
        return {
            "base_fee_msat": suggested_base,
            "fee_rate_ppm": suggested_rate
        }
    
    def update_network_stats(self, network_stats: Dict[str, Any]):
        """
        Met à jour les statistiques réseau.
        
        Args:
            network_stats: Nouvelles stats
        """
        self.network_median_base_fee = network_stats.get("median_base_fee", self.network_median_base_fee)
        self.network_median_fee_rate = network_stats.get("median_fee_rate", self.network_median_fee_rate)
        
        logger.info("network_stats_updated",
                   median_base=self.network_median_base_fee,
                   median_rate=self.network_median_fee_rate)
