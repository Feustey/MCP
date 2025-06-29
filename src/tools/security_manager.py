#!/usr/bin/env python3
"""
Gestionnaire de sécurité pour MCP - Validation, traçabilité et rate limiting
Dernière mise à jour: 7 mai 2025
"""

import logging
import time
from datetime import datetime
from typing import Dict, Optional, Any
from dataclasses import dataclass
import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

@dataclass
class Action:
    """Représente une action à valider et tracer"""
    action_id: str
    node_id: str
    action_type: str
    parameters: Dict[str, Any]
    timestamp: datetime = datetime.now()

class SecurityManager:
    """
    Gestionnaire de sécurité pour MCP avec validation des actions,
    traçabilité complète et rate limiting.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialise le gestionnaire de sécurité
        
        Args:
            redis_url: URL de connexion Redis pour le rate limiting
        """
        self.redis = redis.from_url(redis_url)
        self.rate_limits = {
            "fee_update": {"count": 10, "window": 3600},  # 10 par heure
            "rebalance": {"count": 5, "window": 3600},    # 5 par heure
            "channel_open": {"count": 3, "window": 3600}, # 3 par heure
            "channel_close": {"count": 2, "window": 3600} # 2 par heure
        }
        
    def validate_action(self, action: Action) -> bool:
        """
        Valide une action avant son exécution
        
        Args:
            action: Action à valider
            
        Returns:
            bool: True si l'action est valide
            
        Raises:
            ValueError: Si l'action est invalide
        """
        try:
            # 1. Validation de base
            if not action.action_id or not action.node_id:
                raise ValueError("Action ID et Node ID requis")
                
            # 2. Validation du type d'action
            if action.action_type not in self.rate_limits:
                raise ValueError(f"Type d'action non supporté: {action.action_type}")
                
            # 3. Validation des paramètres selon le type
            self._validate_parameters(action)
            
            # 4. Vérification du rate limiting
            if not self.check_rate_limit(action.node_id, action.action_type):
                raise ValueError(f"Rate limit dépassé pour {action.action_type}")
                
            # 5. Validation spécifique au type d'action
            if action.action_type == "fee_update":
                self._validate_fee_update(action)
            elif action.action_type == "rebalance":
                self._validate_rebalance(action)
                
            return True
            
        except ValueError as e:
            logger.warning(f"Validation échouée pour {action.action_id}: {str(e)}")
            raise
            
    def audit_trail(self, action: Action) -> None:
        """
        Enregistre une trace d'audit pour une action
        
        Args:
            action: Action à tracer
        """
        try:
            audit_entry = {
                "action_id": action.action_id,
                "node_id": action.node_id,
                "action_type": action.action_type,
                "parameters": action.parameters,
                "timestamp": action.timestamp.isoformat(),
                "status": "validated"
            }
            
            # Stocker dans Redis avec TTL de 30 jours
            key = f"audit:{action.action_id}"
            self.redis.setex(key, 30 * 24 * 3600, str(audit_entry))
            
            logger.info(f"Audit trail enregistré pour {action.action_id}")
            
        except RedisError as e:
            logger.error(f"Erreur lors de l'enregistrement de l'audit: {e}")
            # Continuer même si Redis échoue
            
    def check_rate_limit(self, node_id: str, action_type: str) -> bool:
        """
        Vérifie si une action respecte les limites de fréquence
        
        Args:
            node_id: ID du nœud
            action_type: Type d'action
            
        Returns:
            bool: True si l'action est autorisée
        """
        try:
            limit = self.rate_limits.get(action_type)
            if not limit:
                return True
                
            key = f"ratelimit:{node_id}:{action_type}"
            current = self.redis.get(key)
            
            if not current:
                # Premier appel
                self.redis.setex(key, limit["window"], 1)
                return True
                
            count = int(current)
            if count >= limit["count"]:
                return False
                
            # Incrémenter le compteur
            self.redis.incr(key)
            return True
            
        except RedisError as e:
            logger.error(f"Erreur Redis pour rate limiting: {e}")
            # En cas d'erreur Redis, autoriser par défaut
            return True
            
    def _validate_parameters(self, action: Action) -> None:
        """
        Valide les paramètres selon le type d'action
        
        Args:
            action: Action à valider
            
        Raises:
            ValueError: Si les paramètres sont invalides
        """
        required_params = {
            "fee_update": ["channel_id", "new_base_fee", "new_fee_rate"],
            "rebalance": ["source_channel", "dest_channel", "amount"],
            "channel_open": ["peer_id", "capacity"],
            "channel_close": ["channel_id"]
        }
        
        params = required_params.get(action.action_type, [])
        for param in params:
            if param not in action.parameters:
                raise ValueError(f"Paramètre requis manquant: {param}")
                
    def _validate_fee_update(self, action: Action) -> None:
        """
        Validation spécifique pour les mises à jour de frais
        
        Args:
            action: Action de type fee_update à valider
            
        Raises:
            ValueError: Si les paramètres de frais sont invalides
        """
        params = action.parameters
        
        # Valider base_fee
        base_fee = params.get("new_base_fee", 0)
        if not 0 <= base_fee <= 10000:
            raise ValueError("Base fee doit être entre 0 et 10000 msat")
            
        # Valider fee_rate
        fee_rate = params.get("new_fee_rate", 0)
        if not 0 <= fee_rate <= 100000:
            raise ValueError("Fee rate doit être entre 0 et 100000 ppm")
            
    def _validate_rebalance(self, action: Action) -> None:
        """
        Validation spécifique pour les rebalancements
        
        Args:
            action: Action de type rebalance à valider
            
        Raises:
            ValueError: Si les paramètres de rebalancing sont invalides
        """
        params = action.parameters
        
        # Valider le montant
        amount = params.get("amount", 0)
        if amount <= 0:
            raise ValueError("Le montant doit être positif")
            
        # Éviter les boucles
        if params.get("source_channel") == params.get("dest_channel"):
            raise ValueError("Source et destination identiques") 