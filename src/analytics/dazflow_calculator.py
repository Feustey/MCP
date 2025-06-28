#!/usr/bin/env python3
"""
Module de calcul DazFlow Index pour l'analyse du Lightning Network
Approche révolutionnaire inspirée d'Amboss pour évaluer la santé du réseau

Dernière mise à jour: 7 mai 2025
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class DazFlowAnalysis:
    """Résultat d'une analyse DazFlow Index"""
    node_id: str
    timestamp: datetime
    payment_amounts: List[int]
    success_probabilities: List[float]
    dazflow_index: float
    bottleneck_channels: List[str]
    liquidity_efficiency: float
    network_centrality: float

@dataclass
class ReliabilityCurve:
    """Courbe de fiabilité des paiements"""
    amounts: List[int]
    probabilities: List[float]
    confidence_intervals: List[Tuple[float, float]]
    recommended_amounts: List[int]

class DazFlowCalculator:
    """
    Calculateur de métriques DazFlow Index pour l'analyse du Lightning Network.
    Basé sur l'approche Amboss pour évaluer la probabilité de succès des paiements.
    """
    
    def __init__(self):
        """Initialise le calculateur DazFlow Index"""
        self.logger = logging.getLogger(f"{__name__}.DazFlowCalculator")
        
    def calculate_payment_success_probability(
        self, 
        node_data: Dict[str, Any], 
        amount: int
    ) -> float:
        """
        Calcule la probabilité de succès d'un paiement d'un montant donné.
        """
        try:
            channels = node_data.get("channels", [])
            if not channels:
                return 0.0
                
            # Calculer la capacité de flux disponible
            available_flow = self._calculate_available_flow(channels, amount)
            
            # Facteurs de succès
            liquidity_factor = self._calculate_liquidity_factor(channels, amount)
            connectivity_factor = self._calculate_connectivity_factor(node_data)
            historical_success = node_data.get("historical_success_rate", 0.85)
            
            # Probabilité de base basée sur la capacité
            base_probability = min(1.0, available_flow / amount) if amount > 0 else 1.0
            
            # Ajuster avec les facteurs
            final_probability = (
                base_probability * 
                liquidity_factor * 
                connectivity_factor * 
                historical_success
            )
            
            return max(0.0, min(1.0, final_probability))
            
        except Exception as e:
            self.logger.error(f"Erreur calcul probabilité succès: {e}")
            return 0.0
    
    def generate_reliability_curve(
        self, 
        node_data: Dict[str, Any], 
        amounts: List[int]
    ) -> ReliabilityCurve:
        """
        Génère la courbe de fiabilité des paiements.
        """
        try:
            probabilities = []
            confidence_intervals = []
            
            for amount in amounts:
                prob = self.calculate_payment_success_probability(node_data, amount)
                probabilities.append(prob)
                
                # Intervalle de confiance simple
                margin = 0.1
                confidence_intervals.append((max(0, prob - margin), min(1, prob + margin)))
            
            # Montants recommandés (probabilité > 0.8)
            recommended_amounts = [
                amount for amount, prob in zip(amounts, probabilities) 
                if prob >= 0.8
            ]
            
            return ReliabilityCurve(
                amounts=amounts,
                probabilities=probabilities,
                confidence_intervals=confidence_intervals,
                recommended_amounts=recommended_amounts
            )
            
        except Exception as e:
            self.logger.error(f"Erreur génération courbe fiabilité: {e}")
            return ReliabilityCurve([], [], [], [])
    
    def identify_bottlenecks(self, node_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identifie les goulots d'étranglement de liquidité.
        """
        try:
            bottlenecks = []
            channels = node_data.get("channels", [])
            
            for channel in channels:
                capacity = channel.get("capacity", 0)
                local_balance = channel.get("local_balance", 0)
                remote_balance = channel.get("remote_balance", 0)
                
                if capacity == 0:
                    continue
                    
                # Calculer le déséquilibre
                total_balance = local_balance + remote_balance
                if total_balance == 0:
                    continue
                    
                imbalance_ratio = abs(local_balance - remote_balance) / total_balance
                
                # Identifier les problèmes
                issues = []
                if imbalance_ratio > 0.5:
                    issues.append("déséquilibre_liquidité")
                    
                if local_balance < capacity * 0.1:
                    issues.append("liquidité_sortante_faible")
                    
                if remote_balance < capacity * 0.1:
                    issues.append("liquidité_entrante_faible")
                
                if issues:
                    bottlenecks.append({
                        "channel_id": channel.get("channel_id", "unknown"),
                        "peer_alias": channel.get("peer_alias", "unknown"),
                        "capacity": capacity,
                        "local_balance": local_balance,
                        "remote_balance": remote_balance,
                        "imbalance_ratio": imbalance_ratio,
                        "issues": issues,
                        "severity": "high" if imbalance_ratio > 0.8 else "medium"
                    })
            
            return sorted(bottlenecks, key=lambda x: x["imbalance_ratio"], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Erreur identification goulots: {e}")
            return []
    
    def analyze_dazflow_index(self, node_data: Dict[str, Any]) -> DazFlowAnalysis:
        """
        Analyse complète de l'indice DazFlow d'un nœud.
        """
        try:
            target_amounts = [1000, 10000, 100000, 1000000, 10000000]
            node_id = node_data.get("node_id", "unknown")
            
            # Générer la courbe de fiabilité
            reliability_curve = self.generate_reliability_curve(node_data, target_amounts)
            
            # Identifier les goulots
            bottlenecks = self.identify_bottlenecks(node_data)
            bottleneck_channels = [b["channel_id"] for b in bottlenecks]
            
            # Calculer l'efficacité
            liquidity_efficiency = self._calculate_liquidity_efficiency(node_data)
            
            # Centralité du réseau
            centrality_data = node_data.get("metrics", {}).get("centrality", {})
            network_centrality = centrality_data.get("betweenness", 0.5)
            
            # Indice DazFlow
            dazflow_index = np.average(
                reliability_curve.probabilities,
                weights=target_amounts
            )
            
            return DazFlowAnalysis(
                node_id=node_id,
                timestamp=datetime.utcnow(),
                payment_amounts=target_amounts,
                success_probabilities=reliability_curve.probabilities,
                dazflow_index=dazflow_index,
                bottleneck_channels=bottleneck_channels,
                liquidity_efficiency=liquidity_efficiency,
                network_centrality=network_centrality
            )
            
        except Exception as e:
            self.logger.error(f"Erreur analyse DazFlow Index: {e}")
            return None
    
    def _calculate_available_flow(self, channels: List[Dict[str, Any]], amount: int) -> float:
        """Calcule le flux disponible pour un montant donné"""
        try:
            total_flow = 0.0
            
            for channel in channels:
                capacity = channel.get("capacity", 0)
                local_balance = channel.get("local_balance", 0)
                remote_balance = channel.get("remote_balance", 0)
                
                # Flux disponible = min(local_balance, remote_balance)
                available = min(local_balance, remote_balance)
                
                # Ajuster pour la taille du paiement
                if available >= amount:
                    total_flow += amount
                else:
                    total_flow += available * 0.5
            
            return total_flow
            
        except Exception as e:
            self.logger.error(f"Erreur calcul flux disponible: {e}")
            return 0.0
    
    def _calculate_liquidity_factor(self, channels: List[Dict[str, Any]], amount: int) -> float:
        """Calcule le facteur de liquidité"""
        try:
            if not channels:
                return 0.0
            
            total_local = sum(c.get("local_balance", 0) for c in channels)
            total_remote = sum(c.get("remote_balance", 0) for c in channels)
            total_capacity = sum(c.get("capacity", 0) for c in channels)
            
            if total_capacity == 0:
                return 0.0
            
            # Équilibre optimal = 0.5
            balance_ratio = total_local / total_capacity
            balance_factor = 1.0 - abs(balance_ratio - 0.5) * 2
            
            # Facteur de couverture
            coverage_ratio = min(1.0, (total_local + total_remote) / (amount * 2))
            
            return max(0.0, min(1.0, balance_factor * coverage_ratio))
            
        except Exception as e:
            self.logger.error(f"Erreur calcul facteur liquidité: {e}")
            return 0.5
    
    def _calculate_connectivity_factor(self, node_data: Dict[str, Any]) -> float:
        """Calcule le facteur de connectivité"""
        try:
            channels = node_data.get("channels", [])
            if not channels:
                return 0.0
            
            active_channels = sum(1 for c in channels if c.get("active", True))
            connectivity_ratio = active_channels / len(channels)
            
            centrality = node_data.get("metrics", {}).get("centrality", {})
            betweenness = centrality.get("betweenness", 0.5)
            
            return max(0.0, min(1.0, connectivity_ratio * betweenness))
            
        except Exception as e:
            self.logger.error(f"Erreur calcul facteur connectivité: {e}")
            return 0.5
    
    def _calculate_liquidity_efficiency(self, node_data: Dict[str, Any]) -> float:
        """Calcule l'efficacité de liquidité"""
        try:
            channels = node_data.get("channels", [])
            if not channels:
                return 0.0
            
            total_local = sum(c.get("local_balance", 0) for c in channels)
            total_remote = sum(c.get("remote_balance", 0) for c in channels)
            total_capacity = sum(c.get("capacity", 0) for c in channels)
            
            if total_capacity == 0:
                return 0.0
            
            # Équilibre optimal
            balance_ratio = total_local / total_capacity
            balance_score = 1.0 - abs(balance_ratio - 0.5) * 2
            
            # Utilisation des canaux
            utilization = (total_local + total_remote) / total_capacity
            
            return (balance_score * 0.7 + utilization * 0.3)
            
        except Exception as e:
            self.logger.error(f"Erreur calcul efficacité liquidité: {e}")
            return 0.0 