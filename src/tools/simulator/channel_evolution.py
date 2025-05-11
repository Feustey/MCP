#!/usr/bin/env python3
"""
Moteur d'évolution stochastique pour les canaux Lightning.
Ce module simule l'évolution naturelle des canaux et l'impact des changements de politique.

Dernière mise à jour: 7 mai 2025
"""

import math
import random
import numpy as np
import logging
from typing import Dict, Any, List, Callable, Optional, Tuple
from datetime import datetime, timedelta

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("channel_evolution")

class StochasticChannelEvolution:
    """
    Moteur d'évolution stochastique pour simuler le comportement des canaux Lightning
    et leur réaction aux changements de politique de frais.
    """
    
    def __init__(self, base_parameters: Dict[str, Any], volatility_factors: Dict[str, float]):
        """
        Initialise le moteur d'évolution avec des paramètres de base et des facteurs de volatilité
        
        Args:
            base_parameters: Paramètres initiaux du canal
            volatility_factors: Coefficients de variation pour chaque métrique
        """
        self.base = base_parameters
        self.volatility = volatility_factors
        self.state_history = []
        self.current_state = self.base.copy()
        self.timestamp = datetime.now()
        
        # Configuration des courbes de réponse du marché
        self.response_curves = {
            # Sensibilité aux changements de frais (elasticity < 0 : baisse de volume si frais augmentent)
            "fee_elasticity": lambda x: -0.4 * math.log(x/50 + 0.1) + random.normalvariate(0, 0.15),
            
            # Tendance de volume (marche aléatoire avec drift léger)
            "volume_trend": self._generate_random_walk(drift=0.01),
            
            # Pression de liquidité (pattern saisonnier)
            "liquidity_pressure": self._generate_seasonal_pattern()
        }
        
        # Initialiser l'historique avec l'état actuel
        self.state_history.append(self.current_state.copy())
        
        logger.info(f"Évolution stochastique initialisée pour canal {self.base.get('channel_id', 'inconnu')}")
    
    def _generate_random_walk(self, drift: float = 0.0, volatility: float = 0.05) -> Callable:
        """
        Génère une fonction de marche aléatoire avec drift
        
        Args:
            drift: Tendance directionnelle (bias)
            volatility: Amplitude des fluctuations
            
        Returns:
            Fonction qui génère le prochain pas de la marche aléatoire
        """
        last_value = 0
        
        def random_walk():
            nonlocal last_value
            last_value += drift + random.normalvariate(0, volatility)
            return last_value
            
        return random_walk
    
    def _generate_seasonal_pattern(self, amplitude: float = 0.2, period: int = 7) -> Callable:
        """
        Génère une fonction qui produit un pattern saisonnier avec bruit
        
        Args:
            amplitude: Amplitude de la saisonnalité
            period: Période en jours
            
        Returns:
            Fonction qui génère la valeur saisonnière pour un jour donné
        """
        day = 0
        # Phase aléatoire pour éviter que tous les canaux soient synchronisés
        phase = random.uniform(0, 2 * math.pi)
        
        def seasonal():
            nonlocal day
            day += 1
            # Composante saisonnière (sinusoïdale)
            seasonal_component = amplitude * math.sin(2 * math.pi * day / period + phase)
            # Ajouter du bruit
            noise = random.normalvariate(0, amplitude / 3)
            return seasonal_component + noise
            
        return seasonal
    
    def _apply_natural_evolution(self, time_delta: int) -> Dict[str, Any]:
        """
        Applique l'évolution naturelle basée sur les tendances et la volatilité
        
        Args:
            time_delta: Nombre de jours à simuler
            
        Returns:
            Nouvel état du canal après évolution naturelle
        """
        new_state = self.current_state.copy()
        
        # Évolution du volume de transactions
        volume_trend = self.response_curves["volume_trend"]()
        liquidity_pressure = self.response_curves["liquidity_pressure"]()
        
        # Facteurs d'évolution pour différentes métriques
        evolution_factors = {
            "total_forwards": 1.0 + volume_trend * self.volatility.get("volume", 0.1) * time_delta,
            "successful_forwards": 1.0 + (volume_trend - 0.05) * self.volatility.get("success_rate", 0.05) * time_delta,
            "local_balance": 1.0 + liquidity_pressure * self.volatility.get("liquidity", 0.2) * time_delta,
        }
        
        # Appliquer les facteurs d'évolution
        for metric, factor in evolution_factors.items():
            if metric in new_state:
                # S'assurer que les valeurs restent positives
                new_state[metric] = max(0, new_state[metric] * factor)
                
                # Ajouter du bruit pour plus de réalisme
                noise_factor = 1.0 + random.normalvariate(0, self.volatility.get("noise", 0.05))
                new_state[metric] *= noise_factor
        
        # Ajuster les balances pour assurer que la capacité reste constante
        capacity = new_state.get("capacity", 0)
        if capacity > 0 and "local_balance" in new_state:
            # La somme local + remote doit rester égale à la capacité
            local_balance = min(capacity, max(0, new_state["local_balance"]))
            new_state["local_balance"] = local_balance
            new_state["remote_balance"] = capacity - local_balance
        
        # Assurer la cohérence des forwards (successful <= total)
        if "total_forwards" in new_state and "successful_forwards" in new_state:
            new_state["successful_forwards"] = min(
                new_state["successful_forwards"], 
                new_state["total_forwards"]
            )
            
        # Calculer les métriques dérivées
        if "total_forwards" in new_state and "successful_forwards" in new_state:
            new_state["htlc_success_rate"] = (new_state["successful_forwards"] / 
                                           max(1, new_state["total_forwards"]))
                
        # Générer des revenus basés sur les forwards réussis et les frais
        if "successful_forwards" in new_state:
            fee_base = new_state.get("local_fee_base_msat", 1000) / 1000  # Convertir en sat
            fee_rate = new_state.get("local_fee_rate", 500) / 1000000  # Convertir en sat/sat
            avg_forward_size = new_state.get("avg_forward_size", 50000)  # Taille moyenne en sats
            
            # Revenus = (base_fee + forward_size * fee_rate) * successful_forwards
            new_revenue = (fee_base + avg_forward_size * fee_rate) * new_state["successful_forwards"]
            
            # Ajouter les revenus à l'état
            if "revenue" in new_state:
                new_state["revenue"] += new_revenue
            else:
                new_state["revenue"] = new_revenue
        
        return new_state
    
    def _apply_policy_impact(self, state: Dict[str, Any], policy_changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applique l'impact des changements de politique sur l'état du canal
        
        Args:
            state: État actuel du canal
            policy_changes: Changements de politique à appliquer
            
        Returns:
            Nouvel état après application des changements de politique
        """
        new_state = state.copy()
        
        # Extraire les changements
        fee_base_change = policy_changes.get("fee_base_change", 0)  # En sats
        fee_rate_change = policy_changes.get("fee_rate_change", 0)  # En ppm
        
        # Appliquer les changements aux frais actuels
        if "local_fee_base_msat" in new_state and fee_base_change != 0:
            new_state["local_fee_base_msat"] = max(0, new_state["local_fee_base_msat"] + fee_base_change * 1000)
            
        if "local_fee_rate" in new_state and fee_rate_change != 0:
            new_state["local_fee_rate"] = max(0, new_state["local_fee_rate"] + fee_rate_change)
        
        # Calculer l'impact sur le volume de transactions
        # Plus le canal est actif/central, moins il est sensible aux changements de frais
        centrality = new_state.get("centrality_score", 0.5)
        volume = new_state.get("total_forwards", 0)
        
        # Calculer l'élasticité - les canaux à forte centralité sont moins sensibles
        base_elasticity = self.response_curves["fee_elasticity"](new_state.get("local_fee_rate", 500))
        # Atténuer l'élasticité en fonction de la centralité
        adjusted_elasticity = base_elasticity * (1 - 0.7 * centrality)
        
        # Ajustement du volume basé sur l'élasticité et les changements relatifs de frais
        if "local_fee_rate" in new_state and new_state["local_fee_rate"] > 0:
            previous_fee_rate = new_state["local_fee_rate"] - fee_rate_change
            if previous_fee_rate > 0:
                fee_rate_relative_change = fee_rate_change / previous_fee_rate
                
                # Impact sur le volume 
                volume_impact_factor = 1 + adjusted_elasticity * fee_rate_relative_change
                
                # Appliquer l'impact au volume
                if "total_forwards" in new_state:
                    new_state["total_forwards"] *= volume_impact_factor
                    
                # Impact similaire sur les forwards réussis (peut varier légèrement)
                success_variance = random.uniform(0.9, 1.1)
                if "successful_forwards" in new_state:
                    new_state["successful_forwards"] *= volume_impact_factor * success_variance
        
        # Assurer la cohérence des forwards
        if "total_forwards" in new_state and "successful_forwards" in new_state:
            new_state["successful_forwards"] = min(
                new_state["successful_forwards"], 
                new_state["total_forwards"]
            )
            
        # Autres impacts secondaires possibles:
        # 1. Impact sur la balance (les frais élevés peuvent attirer plus de liquidité entrante)
        if fee_rate_change > 0 and random.random() < 0.3:  # 30% de chance
            liquidity_shift = fee_rate_change / 10000  # Impact modéré sur la balance
            capacity = new_state.get("capacity", 0)
            if "local_balance" in new_state and "remote_balance" in new_state and capacity > 0:
                shift_amount = capacity * liquidity_shift
                new_state["remote_balance"] = min(capacity, max(0, new_state["remote_balance"] + shift_amount))
                new_state["local_balance"] = capacity - new_state["remote_balance"]
        
        return new_state
    
    def simulate_step(self, time_delta: int = 1, policy_changes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Simule l'évolution du canal sur un pas de temps
        
        Args:
            time_delta: Nombre de jours à simuler
            policy_changes: Changements de politique à appliquer (optionnel)
            
        Returns:
            Nouvel état du canal
        """
        # Appliquer d'abord l'évolution naturelle
        new_state = self._apply_natural_evolution(time_delta)
        
        # Puis appliquer l'impact des changements de politique si applicable
        if policy_changes:
            new_state = self._apply_policy_impact(new_state, policy_changes)
        
        # Mettre à jour l'état courant et l'historique
        self.current_state = new_state
        self.state_history.append(new_state.copy())
        
        # Mettre à jour le timestamp
        self.timestamp += timedelta(days=time_delta)
        
        return new_state
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        Obtient l'état actuel du canal
        
        Returns:
            État actuel du canal
        """
        return self.current_state.copy()
    
    def get_historical_states(self) -> List[Dict[str, Any]]:
        """
        Obtient l'historique complet des états du canal
        
        Returns:
            Liste des états historiques
        """
        return self.state_history.copy()
    
    def get_metric_history(self, metric_name: str) -> List[float]:
        """
        Obtient l'historique d'une métrique spécifique
        
        Args:
            metric_name: Nom de la métrique
            
        Returns:
            Liste des valeurs historiques de la métrique
        """
        return [state.get(metric_name, 0) for state in self.state_history] 