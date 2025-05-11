#!/usr/bin/env python3
"""
Fixtures et générateur de bruit contrôlé pour le simulateur stochastique de nœuds Lightning.
Ce module fournit des patterns de données réalistes et des générateurs de bruit.

Dernière mise à jour: 7 mai 2025
"""

import math
import random
import numpy as np
import logging
import json
from typing import Dict, Any, List, Optional, Union, Callable
from pathlib import Path
from datetime import datetime, timedelta
import uuid

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("simulation_fixtures")

# Chemin pour stocker/charger des fixtures
FIXTURES_PATH = Path("data/stress_test/fixtures")

class SimulationFixtures:
    """
    Générateur de fixtures et de bruit contrôlé pour les simulations
    """
    
    @staticmethod
    def load_historical_patterns(pattern_type: str = "seasonal") -> Dict[str, List[float]]:
        """
        Charge des patterns historiques réels ou simulés
        
        Args:
            pattern_type: Type de pattern à charger ("seasonal", "market_shock", "weekly")
            
        Returns:
            Dictionnaire de patterns historiques
        """
        patterns = {
            "seasonal": {
                "weekly_cycle": [0.8, 0.9, 1.0, 1.1, 1.2, 0.9, 0.7],
                "daily_cycle": [0.5, 0.3, 0.2, 0.1, 0.2, 0.4, 0.7, 0.9, 1.0, 
                                1.1, 1.2, 1.1, 1.0, 0.9, 0.8, 0.9, 1.0, 1.2, 
                                1.3, 1.2, 1.0, 0.9, 0.7, 0.6]
            },
            "market_shock": {
                "pre": [1.0, 1.0, 1.0, 1.1, 1.0],
                "shock": [1.5, 2.0, 2.3, 2.0, 1.8],
                "recovery": [1.6, 1.4, 1.3, 1.2, 1.1, 1.0]
            },
            "weekly": {
                "monday": [0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0],  # Croissance lente
                "tuesday": [1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3], # Croissance continue
                "wednesday": [1.3, 1.3, 1.25, 1.2, 1.15, 1.1, 1.0], # Plateau puis déclin
                "thursday": [1.0, 1.1, 1.2, 1.1, 1.0, 0.9, 0.8],    # Pic puis déclin
                "friday": [0.8, 0.9, 1.0, 1.1, 1.0, 1.2, 1.3],      # Varie avec pic en fin
                "saturday": [1.2, 1.0, 0.8, 0.7, 0.6, 0.7, 0.8],    # Déclin puis remontée
                "sunday": [0.8, 0.7, 0.6, 0.6, 0.7, 0.8, 0.7]       # Creux puis remontée modérée
            },
            "monthly": {
                "phase1": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],      # Stable
                "phase2": [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6],      # Croissance forte
                "phase3": [1.6, 1.5, 1.4, 1.3, 1.2, 1.1, 1.0],      # Déclin progressif
                "phase4": [1.0, 0.9, 0.8, 0.7, 0.8, 0.9, 1.0]       # Creux puis remontée
            }
        }
        
        if pattern_type not in patterns:
            logger.warning(f"Type de pattern inconnu: {pattern_type}, utilisation de 'seasonal'")
            pattern_type = "seasonal"
            
        return patterns[pattern_type]
    
    @staticmethod
    def apply_controlled_noise(base_value: float, noise_level: float = 0.1, 
                              distribution: str = "normal") -> float:
        """
        Applique un bruit contrôlé à une valeur de base
        
        Args:
            base_value: Valeur de base
            noise_level: Niveau de bruit (écart-type ou amplitude)
            distribution: Type de distribution ("normal", "uniform", "lognormal")
            
        Returns:
            Valeur avec bruit appliqué
        """
        if distribution == "normal":
            # Distribution normale centrée sur la valeur de base
            return base_value * (1 + random.normalvariate(0, noise_level))
            
        elif distribution == "uniform":
            # Distribution uniforme autour de la valeur de base
            return base_value * (1 + random.uniform(-noise_level, noise_level))
            
        elif distribution == "lognormal":
            # Distribution log-normale, plus de chance d'avoir des valeurs légèrement supérieures
            # et une faible chance d'avoir des valeurs très supérieures
            mu = math.log(1.0)  # Moyenne du log = 0
            sigma = math.sqrt(math.log(1 + noise_level))
            return base_value * math.exp(random.normalvariate(mu, sigma))
            
        elif distribution == "exponential":
            # Distribution exponentielle, valeurs typiquement inférieures avec une queue longue
            lambda_param = 1.0 / noise_level
            return base_value * random.expovariate(lambda_param)
            
        else:
            logger.warning(f"Distribution inconnue: {distribution}, utilisation de 'normal'")
            return base_value * (1 + random.normalvariate(0, noise_level))
    
    @staticmethod
    def generate_seasonal_data(base_value: float, days: int = 30, 
                              amplitude: float = 0.2, 
                              noise_level: float = 0.05) -> List[float]:
        """
        Génère une série temporelle avec composante saisonnière hebdomadaire et bruit
        
        Args:
            base_value: Valeur de base
            days: Nombre de jours à générer
            amplitude: Amplitude de la composante saisonnière
            noise_level: Niveau de bruit aléatoire
            
        Returns:
            Liste de valeurs quotidiennes
        """
        weekly_pattern = SimulationFixtures.load_historical_patterns("seasonal")["weekly_cycle"]
        result = []
        
        for day in range(days):
            # Composante saisonnière
            day_of_week = day % 7
            seasonal_factor = weekly_pattern[day_of_week]
            
            # Valeur avec composante saisonnière
            daily_value = base_value * (1 + (seasonal_factor - 1) * amplitude)
            
            # Ajouter du bruit
            noisy_value = SimulationFixtures.apply_controlled_noise(
                daily_value, noise_level, "normal")
                
            result.append(noisy_value)
            
        return result
    
    @staticmethod
    def generate_shock_event(base_values: List[float], 
                           shock_day: int, 
                           shock_magnitude: float = 2.0,
                           recovery_days: int = 5) -> List[float]:
        """
        Applique un choc ponctuel à une série temporelle existante
        
        Args:
            base_values: Série temporelle de base
            shock_day: Jour où le choc se produit
            shock_magnitude: Amplitude du choc (multiplicateur)
            recovery_days: Nombre de jours pour récupérer
            
        Returns:
            Série temporelle avec choc
        """
        result = base_values.copy()
        
        if shock_day >= len(result):
            logger.warning(f"Jour de choc ({shock_day}) hors limites, choc ignoré")
            return result
            
        # Appliquer le choc
        result[shock_day] = result[shock_day] * shock_magnitude
        
        # Récupération progressive
        for i in range(1, recovery_days + 1):
            if shock_day + i < len(result):
                recovery_factor = 1 + (shock_magnitude - 1) * (1 - i / recovery_days)
                result[shock_day + i] = base_values[shock_day + i] * recovery_factor
                
        return result
    
    @staticmethod
    def generate_trend(base_value: float, days: int = 30, 
                     trend_type: str = "linear", 
                     end_factor: float = 1.5,
                     noise_level: float = 0.05) -> List[float]:
        """
        Génère une série temporelle avec une tendance spécifique
        
        Args:
            base_value: Valeur de départ
            days: Nombre de jours à générer
            trend_type: Type de tendance ("linear", "exponential", "logarithmic", "sinusoidal")
            end_factor: Facteur multiplicatif pour la valeur finale
            noise_level: Niveau de bruit aléatoire
            
        Returns:
            Liste de valeurs avec tendance
        """
        result = []
        
        for day in range(days):
            # Calculer la tendance
            progress = day / (days - 1) if days > 1 else 0
            
            if trend_type == "linear":
                # Tendance linéaire
                trend_value = base_value * (1 + (end_factor - 1) * progress)
                
            elif trend_type == "exponential":
                # Tendance exponentielle
                trend_value = base_value * (end_factor ** progress)
                
            elif trend_type == "logarithmic":
                # Tendance logarithmique (croissance rapide puis plateau)
                # Éviter log(0)
                log_factor = math.log(1 + 9 * progress) / math.log(10)
                trend_value = base_value * (1 + (end_factor - 1) * log_factor)
                
            elif trend_type == "sinusoidal":
                # Tendance sinusoïdale (oscillations)
                cycles = 2  # Nombre de cycles complets
                trend_value = base_value * (1 + (end_factor - 1) * 0.5 * 
                                         (1 + math.sin(2 * math.pi * cycles * progress - math.pi/2)))
                
            else:
                logger.warning(f"Type de tendance inconnu: {trend_type}, utilisation de 'linear'")
                trend_value = base_value * (1 + (end_factor - 1) * progress)
            
            # Ajouter du bruit
            noisy_value = SimulationFixtures.apply_controlled_noise(
                trend_value, noise_level, "normal")
                
            result.append(noisy_value)
            
        return result
    
    @classmethod
    def save_fixture(cls, fixture_data: Dict[str, Any], fixture_name: str) -> bool:
        """
        Sauvegarde des fixtures pour réutilisation
        
        Args:
            fixture_data: Données à sauvegarder
            fixture_name: Nom de la fixture
            
        Returns:
            True si la sauvegarde a réussi, False sinon
        """
        try:
            # Créer le répertoire si nécessaire
            FIXTURES_PATH.mkdir(parents=True, exist_ok=True)
            
            # Nom de fichier avec timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{fixture_name}_{timestamp}.json"
            filepath = FIXTURES_PATH / filename
            
            with open(filepath, "w") as f:
                json.dump(fixture_data, f, indent=2)
                
            logger.info(f"Fixture sauvegardée dans {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la fixture: {e}")
            return False
    
    @classmethod
    def load_fixture(cls, fixture_name: str) -> Optional[Dict[str, Any]]:
        """
        Charge une fixture existante
        
        Args:
            fixture_name: Motif de nom pour la fixture à charger
            
        Returns:
            Données de la fixture ou None si non trouvée
        """
        try:
            # Trouver tous les fichiers correspondant au motif
            matching_files = list(FIXTURES_PATH.glob(f"{fixture_name}*.json"))
            
            if not matching_files:
                logger.warning(f"Aucune fixture trouvée pour '{fixture_name}'")
                return None
                
            # Prendre le plus récent
            latest_file = max(matching_files, key=lambda p: p.stat().st_mtime)
            
            with open(latest_file, "r") as f:
                fixture_data = json.load(f)
                
            logger.info(f"Fixture chargée depuis {latest_file}")
            return fixture_data
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la fixture: {e}")
            return None
    
    @staticmethod
    def generate_historical_scenario(scenario_type: str = "normal", days: int = 30) -> Dict[str, Any]:
        """
        Génère un scénario historique complet pour un nœud
        
        Args:
            scenario_type: Type de scénario ("normal", "growth", "decline", "volatile", "shock")
            days: Nombre de jours d'historique
            
        Returns:
            Dictionnaire avec l'historique simulé
        """
        # Paramètres de base
        base_params = {
            "forwards_per_day": 100,
            "success_rate": 0.95,
            "channel_count": 10,
            "avg_capacity": 5000000,
            "fee_base": 1000,  # msat
            "fee_rate": 500,   # ppm
        }
        
        # Ajuster les paramètres selon le scénario
        if scenario_type == "growth":
            base_params["forwards_per_day"] = 50  # Commence plus bas
            growth_factor = 3.0  # Croissance x3
        elif scenario_type == "decline":
            base_params["forwards_per_day"] = 200  # Commence plus haut
            decline_factor = 0.3  # Déclin à 30%
        elif scenario_type == "volatile":
            base_params["forwards_per_day"] = 100
            volatility = 0.3  # 30% de volatilité
        elif scenario_type == "shock":
            base_params["forwards_per_day"] = 100
            shock_day = days // 2  # Choc au milieu de la période
            shock_magnitude = 0.2  # Chute à 20%
        else:  # normal
            base_params["forwards_per_day"] = 100
            normal_volatility = 0.1  # 10% de volatilité normale
        
        # Générer les séries temporelles
        history = {
            "days": list(range(1, days + 1)),
            "timestamp": [(datetime.now() - timedelta(days=days-i)).strftime("%Y-%m-%d") 
                         for i in range(1, days + 1)],
            "total_forwards": [],
            "successful_forwards": [],
            "revenue": [],
            "fees": {
                "base": [],
                "rate": []
            },
            "channel_stats": {
                "count": [],
                "avg_capacity": [],
                "local_balance_ratio": []
            }
        }
        
        # Générer les forwards totaux selon le scénario
        if scenario_type == "growth":
            history["total_forwards"] = SimulationFixtures.generate_trend(
                base_params["forwards_per_day"], days, "logarithmic", growth_factor, 0.1)
        elif scenario_type == "decline":
            history["total_forwards"] = SimulationFixtures.generate_trend(
                base_params["forwards_per_day"], days, "exponential", decline_factor, 0.1)
        elif scenario_type == "volatile":
            history["total_forwards"] = SimulationFixtures.generate_seasonal_data(
                base_params["forwards_per_day"], days, 0.4, volatility)
        elif scenario_type == "shock":
            base_series = SimulationFixtures.generate_seasonal_data(
                base_params["forwards_per_day"], days, 0.2, 0.1)
            history["total_forwards"] = SimulationFixtures.generate_shock_event(
                base_series, shock_day, shock_magnitude, 7)
        else:  # normal
            history["total_forwards"] = SimulationFixtures.generate_seasonal_data(
                base_params["forwards_per_day"], days, 0.2, normal_volatility)
        
        # Générer les forwards réussis basés sur le taux de succès
        history["successful_forwards"] = [
            min(total, total * SimulationFixtures.apply_controlled_noise(
                base_params["success_rate"], 0.05, "normal"))
            for total in history["total_forwards"]
        ]
        
        # Générer les revenus
        avg_forward_size = 50000  # En sats
        cumulative_revenue = 0
        daily_revenues = []
        
        for i in range(days):
            successful = history["successful_forwards"][i]
            fee_base = base_params["fee_base"] / 1000  # Convertir en sats
            fee_rate = base_params["fee_rate"] / 1000000  # Convertir en sat/sat
            
            # Revenus = (base_fee + forward_size * fee_rate) * successful_forwards
            daily_revenue = (fee_base + avg_forward_size * fee_rate) * successful
            cumulative_revenue += daily_revenue
            daily_revenues.append(daily_revenue)
            history["revenue"].append(cumulative_revenue)
        
        # Générer les frais (peuvent varier dans le temps)
        for i in range(days):
            # Les frais peuvent être ajustés au fil du temps
            fee_base_factor = 1.0
            fee_rate_factor = 1.0
            
            # Scénarios spécifiques pour les frais
            if scenario_type == "growth" and i > days // 2:
                # Augmenter les frais dans la deuxième moitié pour le scénario de croissance
                progress = (i - days // 2) / (days - days // 2)
                fee_base_factor = 1.0 + 0.5 * progress  # +50% max
                fee_rate_factor = 1.0 + 0.3 * progress  # +30% max
            elif scenario_type == "decline" and i > days // 3:
                # Baisser les frais pour tenter de compenser le déclin
                progress = (i - days // 3) / (days - days // 3)
                fee_base_factor = 1.0 - 0.3 * progress  # -30% max
                fee_rate_factor = 1.0 - 0.2 * progress  # -20% max
            
            # Appliquer les facteurs avec un peu de bruit
            history["fees"]["base"].append(base_params["fee_base"] * 
                                         SimulationFixtures.apply_controlled_noise(fee_base_factor, 0.05))
            history["fees"]["rate"].append(base_params["fee_rate"] * 
                                         SimulationFixtures.apply_controlled_noise(fee_rate_factor, 0.05))
        
        # Générer les statistiques de canaux
        for i in range(days):
            # Le nombre de canaux peut varier légèrement
            channel_count = base_params["channel_count"]
            if scenario_type == "growth":
                # Augmentation progressive du nombre de canaux
                progress = i / (days - 1) if days > 1 else 0
                channel_count = base_params["channel_count"] * (1 + 0.5 * progress)  # +50% max
            
            # Ajouter du bruit
            channel_count = max(1, round(SimulationFixtures.apply_controlled_noise(channel_count, 0.1)))
            history["channel_stats"]["count"].append(channel_count)
            
            # Capacité moyenne et ratio de balance
            avg_capacity = SimulationFixtures.apply_controlled_noise(base_params["avg_capacity"], 0.1)
            history["channel_stats"]["avg_capacity"].append(avg_capacity)
            
            # Balance locale en pourcentage de la capacité totale (idéalement autour de 50%)
            local_balance_ratio = 0.5  # Valeur idéale
            if scenario_type == "decline":
                # Déséquilibre progressif dans un scénario de déclin
                progress = i / (days - 1) if days > 1 else 0
                local_balance_ratio = 0.5 - 0.3 * progress  # Jusqu'à 20%
            elif scenario_type == "shock" and i >= shock_day:
                # Déséquilibre soudain après un choc
                days_after_shock = i - shock_day
                if days_after_shock < 7:  # Récupération sur 7 jours
                    local_balance_ratio = 0.5 - 0.3 * (1 - days_after_shock / 7)
                else:
                    local_balance_ratio = 0.5
            
            # Ajouter du bruit
            local_balance_ratio = max(0.05, min(0.95, 
                                             SimulationFixtures.apply_controlled_noise(local_balance_ratio, 0.05)))
            history["channel_stats"]["local_balance_ratio"].append(local_balance_ratio)
        
        return history

    def __init__(self):
        """Initialise les fixtures"""
        # Plages de valeurs par défaut pour les paramètres
        self.default_ranges = {
            "capacity": (1000000, 10000000),  # 1M - 10M sats
            "local_balance": (100000, 5000000),  # 100k - 5M sats
            "base_fee": (0, 1000),  # 0 - 1000 msat
            "fee_rate": (1, 500),  # 1 - 500 ppm
            "cltv_delta": (40, 144),  # 40 - 144 blocks
            "min_htlc": (1000, 10000),  # 1k - 10k sats
            "max_htlc": (100000, 5000000)  # 100k - 5M sats
        }
    
    def generate_test_network(self, num_channels: int = 5) -> Dict[str, Any]:
        """
        Génère un réseau de test avec un nombre spécifié de canaux
        
        Args:
            num_channels: Nombre de canaux à générer
            
        Returns:
            Dictionnaire représentant le réseau
        """
        # Générer les canaux
        channels = []
        for i in range(num_channels):
            # Générer un identifiant de canal unique
            channel_id = str(uuid.uuid4())
            
            # Générer des valeurs aléatoires pour les paramètres du canal
            capacity = np.random.randint(*self.default_ranges["capacity"])
            local_balance = min(np.random.randint(*self.default_ranges["local_balance"]), capacity * 0.9)
            remote_balance = capacity - local_balance
            
            # Générer des valeurs aléatoires pour les paramètres de politique
            base_fee = np.random.randint(*self.default_ranges["base_fee"])
            fee_rate = np.random.randint(*self.default_ranges["fee_rate"])
            cltv_delta = np.random.randint(*self.default_ranges["cltv_delta"])
            min_htlc = np.random.randint(*self.default_ranges["min_htlc"])
            max_htlc = min(np.random.randint(*self.default_ranges["max_htlc"]), capacity * 0.8)
            
            # Générer des valeurs aléatoires pour les métriques de performance
            avg_daily_volume = local_balance * np.random.uniform(0.01, 0.1)  # 1% - 10% de la balance locale
            success_rate_base = np.random.uniform(0.8, 0.98)  # 80% - 98%
            forward_amount = avg_daily_volume * np.random.uniform(0.8, 1.2)  # Variation autour de la moyenne
            
            # Créer le canal
            channel = {
                "channel_id": channel_id,
                "capacity": capacity,
                "local_balance": local_balance,
                "remote_balance": remote_balance,
                "base_fee": base_fee,
                "fee_rate": fee_rate,
                "cltv_delta": cltv_delta,
                "min_htlc": min_htlc,
                "max_htlc": max_htlc,
                "avg_daily_volume": avg_daily_volume,
                "success_rate": success_rate_base,
                "forward_amount": forward_amount,
                "liquidity_ratio": local_balance / capacity
            }
            
            channels.append(channel)
        
        # Créer le réseau
        network = {
            "channels": channels,
            "num_channels": num_channels
        }
        
        return network
    
    def generate_channel_history(self, channel: Dict[str, Any], days: int = 14) -> List[Dict[str, Any]]:
        """
        Génère un historique pour un canal
        
        Args:
            channel: Canal pour lequel générer l'historique
            days: Nombre de jours d'historique à générer
            
        Returns:
            Liste d'enregistrements d'historique
        """
        history = []
        
        # Paramètres de base du canal
        capacity = channel["capacity"]
        initial_local_balance = channel["local_balance"]
        avg_daily_volume = channel["avg_daily_volume"]
        success_rate_base = channel["success_rate"]
        
        # Générer l'historique jour par jour
        current_local_balance = initial_local_balance
        
        for day in range(days):
            # Calculer les variations aléatoires
            volume_factor = np.random.uniform(0.7, 1.3)  # Variation du volume
            success_factor = np.random.uniform(0.95, 1.05)  # Variation du taux de succès
            
            # Calculer les métriques du jour
            forward_amount = avg_daily_volume * volume_factor
            success_rate = min(1.0, success_rate_base * success_factor)
            
            # Simuler un changement de balance locale (flux net)
            balance_change = forward_amount * np.random.uniform(-0.2, 0.2)  # -20% à +20% du volume
            current_local_balance = max(0, min(capacity, current_local_balance + balance_change))
            
            # Créer l'enregistrement
            record = {
                "timestamp": f"2025-05-{(days-day):02d}T00:00:00",
                "forward_amount": forward_amount,
                "forward_success": success_rate,
                "local_balance": current_local_balance,
                "capacity": capacity,
                "liquidity_ratio": current_local_balance / capacity
            }
            
            history.append(record)
        
        return history
    
    def generate_test_data(self, num_channels: int = 5, days: int = 14) -> Dict[str, Any]:
        """
        Génère un jeu de données de test complet
        
        Args:
            num_channels: Nombre de canaux à générer
            days: Nombre de jours d'historique
            
        Returns:
            Données de test complètes
        """
        # Générer le réseau
        network = self.generate_test_network(num_channels)
        
        # Générer l'historique pour chaque canal
        channel_data = {}
        for channel in network["channels"]:
            channel_id = channel["channel_id"]
            history = self.generate_channel_history(channel, days)
            channel_data[channel_id] = history
        
        # Créer les données complètes
        test_data = {
            "channel_data": channel_data,
            "network": network,
            "days": days,
            "num_channels": num_channels
        }
        
        return test_data 