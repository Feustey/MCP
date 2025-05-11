#!/usr/bin/env python3
# coding: utf-8
"""
Module de suivi des performances pour l'optimisation des nœuds Lightning.
Enregistre l'impact des actions et apprend à optimiser les décisions futures.

Dernière mise à jour: 10 mai 2025
"""

import logging
import pickle
import os
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger("performance_tracker")

# Répertoire pour stocker les modèles entraînés
MODELS_DIR = Path("data/models")

class PerformanceTracker:
    def __init__(self, db_connection, model_dir=None):
        """
        Initialise le tracker de performance
        
        Args:
            db_connection: Connexion à la base de données pour persister les données
            model_dir: Répertoire pour stocker les modèles (optional)
        """
        self.db = db_connection
        self.model_dir = Path(model_dir) if model_dir else MODELS_DIR
        self.model = self._initialize_model()
        
        # S'assurer que le répertoire des modèles existe
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
    def _initialize_model(self):
        """
        Initialise un modèle simple d'apprentissage ou charge un modèle existant
        
        Returns:
            Modèle d'apprentissage
        """
        model_path = self.model_dir / "performance_model.pkl"
        
        try:
            if model_path.exists():
                logger.info(f"Chargement du modèle depuis {model_path}")
                with open(model_path, 'rb') as f:
                    return pickle.load(f)
            
            # Par défaut, utiliser une régression linéaire simple
            logger.info("Initialisation d'un nouveau modèle de régression linéaire")
            try:
                from sklearn.linear_model import LinearRegression
                return LinearRegression()
            except ImportError:
                logger.warning("sklearn non disponible, utilisation d'un modèle de substitution")
                return SimpleFallbackModel()
                
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du modèle: {e}")
            return SimpleFallbackModel()
        
    def record_performance(self, node_id, actions, initial_state, final_state):
        """
        Enregistre la performance d'une action pour apprentissage
        
        Args:
            node_id: ID du nœud
            actions: Actions effectuées
            initial_state: État du nœud avant les actions
            final_state: État du nœud après les actions
            
        Returns:
            Dict contenant les métriques de performance
        """
        try:
            # Calculer les métriques de performance
            performance = {
                "node_id": node_id,
                "timestamp": datetime.now(),
                "action_type": actions[0]["action"] if actions else "none",
                "revenue_change": final_state["revenue"] - initial_state["revenue"],
                "success_rate_change": final_state["success_rate"] - initial_state["success_rate"],
                "liquidity_balance_change": final_state["liquidity_balance"] - initial_state["liquidity_balance"],
                "net_improvement": self._calculate_improvement(initial_state, final_state),
                "initial_state": initial_state,
                "final_state": final_state,
                "actions": actions
            }
            
            # Stocker dans la base de données
            logger.info(f"Enregistrement des performances pour le nœud {node_id}")
            self.db.performance_records.insert_one(performance)
            
            # Mettre à jour le modèle d'apprentissage (tous les 50 enregistrements)
            if self.db.performance_records.count_documents({}) % 50 == 0:
                logger.info("Mise à jour du modèle d'apprentissage")
                self._update_model()
                
            return performance
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement des performances: {e}")
            return {"error": str(e)}
        
    def _calculate_improvement(self, initial, final):
        """
        Calcule l'amélioration globale après une action
        
        Args:
            initial: État initial du nœud
            final: État final du nœud
            
        Returns:
            Score d'amélioration (-1 à 1)
        """
        # Formule prenant en compte le revenu, taux de succès et équilibre
        revenue_weight = 0.5
        success_weight = 0.3
        balance_weight = 0.2
        
        # Éviter les divisions par zéro
        if initial["revenue"] == 0:
            revenue_improvement = final["revenue"] / 100 if final["revenue"] > 0 else 0
        else:
            revenue_improvement = (final["revenue"] - initial["revenue"]) / max(1, initial["revenue"])
        
        success_improvement = final["success_rate"] - initial["success_rate"]
        
        # Pour l'équilibre, on vise 0.5 (50% local, 50% remote)
        initial_balance_distance = abs(0.5 - initial["liquidity_balance"])
        final_balance_distance = abs(0.5 - final["liquidity_balance"])
        
        if initial_balance_distance == 0:
            balance_improvement = 0  # Déjà parfaitement équilibré
        else:
            balance_improvement = (initial_balance_distance - final_balance_distance) / initial_balance_distance
        
        # Calculer l'amélioration globale pondérée
        net_improvement = (
            revenue_improvement * revenue_weight +
            success_improvement * success_weight +
            balance_improvement * balance_weight
        )
        
        logger.debug(f"Amélioration: revenu={revenue_improvement:.4f}, succès={success_improvement:.4f}, "
                    f"équilibre={balance_improvement:.4f}, net={net_improvement:.4f}")
        
        return net_improvement
                
    def _update_model(self):
        """Met à jour le modèle d'apprentissage avec les données historiques"""
        try:
            # Récupérer les données historiques
            records = list(self.db.performance_records.find({}))
            
            if len(records) < 10:  # Besoin d'un minimum de données
                logger.info("Pas assez de données pour mettre à jour le modèle")
                return
                
            # Préparer features et target
            X = []
            y = []
            
            for record in records:
                # Extraire les features
                X.append(self._extract_features(record))
                
                # Target est l'amélioration nette
                y.append(record["net_improvement"])
                
            # Entraîner le modèle
            logger.info(f"Entrainement du modèle avec {len(X)} exemples")
            self.model.fit(X, y)
            
            # Sauvegarder le modèle
            model_path = self.model_dir / "performance_model.pkl"
            with open(model_path, 'wb') as f:
                pickle.dump(self.model, f)
                
            logger.info(f"Modèle entraîné et sauvegardé dans {model_path}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du modèle: {e}")
    
    def _extract_features(self, record: Dict) -> List[float]:
        """
        Extrait les features pour l'entraînement du modèle
        
        Args:
            record: Enregistrement de performance
            
        Returns:
            Liste de features
        """
        # Actions encodées (one-hot)
        action_type = record["action_type"]
        is_fee_adjustment = 1.0 if action_type == "fee_adjustment" else 0.0
        is_rebalance = 1.0 if action_type == "rebalance" else 0.0
        
        # Récupérer les caractéristiques de l'état initial
        initial_state = record.get("initial_state", {})
        success_rate = initial_state.get("success_rate", 0.5)
        liquidity_balance = initial_state.get("liquidity_balance", 0.5)
        
        # Caractéristiques supplémentaires
        if action_type == "fee_adjustment":
            direction = 1.0
            for action in record.get("actions", []):
                if action.get("direction") == "decrease":
                    direction = -1.0
                    break
        else:
            direction = 0.0
            
        # Retourner le vecteur de features
        return [
            is_fee_adjustment,
            is_rebalance,
            success_rate,
            liquidity_balance,
            abs(0.5 - liquidity_balance),  # Distance à l'équilibre parfait
            direction
        ]
        
    def predict_best_action(self, node_state):
        """
        Prédit l'action optimale pour un état de nœud donné
        
        Args:
            node_state: État actuel du nœud
            
        Returns:
            Dict avec l'action recommandée et les détails
        """
        try:
            # Vérifier si le modèle est entraîné
            if not hasattr(self.model, "predict"):
                logger.warning("Modèle non entraîné, utilisation des règles par défaut")
                return self._fallback_recommendation(node_state)
                
            # Prédire pour chaque type d'action possible
            predictions = {}
            
            # 1. Ajustement des frais à la hausse
            X_fee_up = [
                1.0,  # is_fee_adjustment
                0.0,  # is_rebalance
                node_state.get("success_rate", 0.5),
                node_state.get("liquidity_balance", 0.5),
                abs(0.5 - node_state.get("liquidity_balance", 0.5)),
                1.0   # direction (hausse)
            ]
            
            # 2. Ajustement des frais à la baisse
            X_fee_down = [
                1.0,  # is_fee_adjustment
                0.0,  # is_rebalance
                node_state.get("success_rate", 0.5),
                node_state.get("liquidity_balance", 0.5),
                abs(0.5 - node_state.get("liquidity_balance", 0.5)),
                -1.0  # direction (baisse)
            ]
            
            # 3. Rééquilibrage
            X_rebalance = [
                0.0,  # is_fee_adjustment
                1.0,  # is_rebalance
                node_state.get("success_rate", 0.5),
                node_state.get("liquidity_balance", 0.5),
                abs(0.5 - node_state.get("liquidity_balance", 0.5)),
                0.0   # direction (N/A)
            ]
            
            # Effectuer les prédictions
            predictions["fee_up"] = float(self.model.predict([X_fee_up])[0])
            predictions["fee_down"] = float(self.model.predict([X_fee_down])[0])
            predictions["rebalance"] = float(self.model.predict([X_rebalance])[0])
            
            # Trouver la meilleure action
            best_action = max(predictions.items(), key=lambda x: x[1])
            
            logger.info(f"Prédictions: {predictions}")
            logger.info(f"Meilleure action: {best_action[0]} (amélioration prédite: {best_action[1]:.4f})")
            
            # Traduire en action concrète
            action_mapping = {
                "fee_up": {"action": "fee_adjustment", "direction": 1},
                "fee_down": {"action": "fee_adjustment", "direction": -1},
                "rebalance": {"action": "rebalance", "emergency": False}
            }
            
            # Calculer la confiance
            confidence = self._calculate_confidence(predictions)
            
            return {
                "recommended_action": action_mapping[best_action[0]],
                "predicted_improvement": best_action[1],
                "confidence": confidence,
                "all_predictions": predictions
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la prédiction de la meilleure action: {e}")
            return self._fallback_recommendation(node_state)
        
    def _fallback_recommendation(self, node_state):
        """
        Génère une recommandation basée sur des règles simples en cas d'échec du modèle
        
        Args:
            node_state: État actuel du nœud
            
        Returns:
            Dict avec l'action recommandée
        """
        success_rate = node_state.get("success_rate", 0.5)
        liquidity_balance = node_state.get("liquidity_balance", 0.5)
        
        # Règles simples
        if abs(0.5 - liquidity_balance) > 0.2:
            # Déséquilibre significatif
            action = {"action": "rebalance", "emergency": abs(0.5 - liquidity_balance) > 0.3}
        elif success_rate < 0.75:
            # Mauvais taux de succès
            action = {"action": "fee_adjustment", "direction": -1}
        else:
            # Essayer d'augmenter les frais si tout va bien
            action = {"action": "fee_adjustment", "direction": 1}
            
        return {
            "recommended_action": action,
            "predicted_improvement": 0.1,
            "confidence": 0.5,
            "fallback": True
        }
        
    def _calculate_confidence(self, predictions):
        """
        Calcule un score de confiance pour la prédiction
        
        Args:
            predictions: Dict avec les prédictions pour chaque action
            
        Returns:
            Score de confiance (0-1)
        """
        values = list(predictions.values())
        if len(values) <= 1:
            return 0
            
        # Trier les valeurs par ordre décroissant
        sorted_values = sorted(values, reverse=True)
        best = sorted_values[0]
        second_best = sorted_values[1]
        
        # Plus l'écart est grand, plus la confiance est élevée
        return min(1.0, max(0.0, (best - second_best) / max(0.01, abs(best))))


class SimpleFallbackModel:
    """Modèle de substitution simple quand sklearn n'est pas disponible"""
    
    def fit(self, X, y):
        """
        Méthode d'entraînement simplifiée qui calcule des poids moyens
        """
        if not X or not y:
            return
            
        self.weights = [0.0] * len(X[0])
        
        # Calculer des poids simples basés sur la corrélation
        for i in range(len(self.weights)):
            feature_values = [x[i] for x in X]
            
            # Calculer un poids simple basé sur la corrélation
            sum_xy = sum(f * t for f, t in zip(feature_values, y))
            sum_x = sum(feature_values)
            sum_y = sum(y)
            sum_x2 = sum(f * f for f in feature_values)
            n = len(X)
            
            if sum_x2 - (sum_x * sum_x) / n == 0:
                self.weights[i] = 0
            else:
                self.weights[i] = (sum_xy - (sum_x * sum_y) / n) / (sum_x2 - (sum_x * sum_x) / n)
    
    def predict(self, X):
        """
        Prédit en utilisant une combinaison linéaire simple
        """
        if not hasattr(self, 'weights'):
            return [0.0] * len(X)
            
        return [sum(w * x[i] for i, w in enumerate(self.weights)) for x in X] 