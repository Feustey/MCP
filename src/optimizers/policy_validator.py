#!/usr/bin/env python3
"""
Policy Validator - Validation sécurisée des changements de policies

Ce module valide tous les changements de policies avant application :
- Limites de sécurité (min/max fees)
- Fréquence des changements (cooldown)
- Blacklist de canaux critiques
- Ratios acceptables
- Montants de rebalance

Dernière mise à jour: 15 octobre 2025
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Exception levée lors d'une validation échouée."""
    pass


class PolicyChangeType(Enum):
    """Types de changements de policy."""
    FEE_INCREASE = "fee_increase"
    FEE_DECREASE = "fee_decrease"
    REBALANCE = "rebalance"
    CLOSE = "close"


class PolicyValidator:
    """
    Validateur de changements de policies avec règles de sécurité.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialise le validateur avec configuration.
        
        Args:
            config: Configuration personnalisée (optionnel)
        """
        self.config = config or self._get_default_config()
        self.safety_rules = self.config.get("safety_rules", {})
        self.rate_limits = self.config.get("rate_limits", {})
        self.blacklist = self.config.get("blacklist_channels", [])
        
        # Historique des changements (pour cooldown)
        self.change_history = {}
        
        logger.info("PolicyValidator initialisé")
    
    def _get_default_config(self) -> Dict:
        """Configuration par défaut."""
        return {
            "safety_rules": {
                "base_fee_msat_min": 0,
                "base_fee_msat_max": 10000,  # 10 sats max
                "fee_rate_ppm_min": 1,
                "fee_rate_ppm_max": 10000,   # 1% max
                "max_change_percent": 0.5,    # ±50% max en une fois
                "min_htlc_msat": 1000,        # 1 sat minimum
                "time_lock_delta_min": 18,
                "time_lock_delta_max": 144
            },
            "rate_limits": {
                "max_changes_per_day": 5,
                "cooldown_minutes": 60,       # 1h entre changements
                "max_changes_per_channel_per_day": 3
            },
            "rebalance_rules": {
                "max_amount_percent": 0.5,    # 50% de capacité max
                "max_cost_percent": 0.005,    # 0.5% du montant max
                "min_amount_sats": 100000     # 100k sats minimum
            },
            "blacklist_channels": []
        }
    
    def validate_policy_change(
        self,
        channel: Dict[str, Any],
        new_policy: Dict[str, Any],
        change_type: PolicyChangeType
    ) -> Tuple[bool, Optional[str]]:
        """
        Valide un changement de policy.
        
        Args:
            channel: Données du canal
            new_policy: Nouvelle policy proposée
            change_type: Type de changement
        
        Returns:
            (is_valid, error_message)
        """
        channel_id = channel.get("channel_id")
        
        try:
            # 1. Vérifier blacklist
            if channel_id in self.blacklist:
                return False, f"Canal {channel_id[:8]} dans la blacklist"
            
            # 2. Vérifier limites de sécurité
            self._check_safety_limits(new_policy)
            
            # 3. Vérifier taux de changement
            self._check_rate_limit(channel_id)
            
            # 4. Vérifier magnitude du changement
            current_policy = channel.get("policy", {})
            self._check_change_magnitude(current_policy, new_policy)
            
            # 5. Validations spécifiques au type
            if change_type == PolicyChangeType.REBALANCE:
                self._validate_rebalance(channel, new_policy)
            
            logger.debug(f"Validation OK pour canal {channel_id[:8]}")
            return True, None
            
        except ValidationError as e:
            logger.warning(f"Validation échouée pour {channel_id[:8]}: {e}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Erreur validation {channel_id[:8]}: {e}")
            return False, f"Erreur interne: {e}"
    
    def _check_safety_limits(self, policy: Dict[str, Any]):
        """
        Vérifie que les valeurs de policy respectent les limites de sécurité.
        
        Raises:
            ValidationError si hors limites
        """
        rules = self.safety_rules
        
        # Base fee
        base_fee = int(policy.get("base_fee_msat", 0))
        if base_fee < rules["base_fee_msat_min"]:
            raise ValidationError(
                f"base_fee_msat trop faible: {base_fee} < {rules['base_fee_msat_min']}"
            )
        if base_fee > rules["base_fee_msat_max"]:
            raise ValidationError(
                f"base_fee_msat trop élevé: {base_fee} > {rules['base_fee_msat_max']}"
            )
        
        # Fee rate
        fee_rate = int(policy.get("fee_rate_ppm", 0))
        if fee_rate < rules["fee_rate_ppm_min"]:
            raise ValidationError(
                f"fee_rate_ppm trop faible: {fee_rate} < {rules['fee_rate_ppm_min']}"
            )
        if fee_rate > rules["fee_rate_ppm_max"]:
            raise ValidationError(
                f"fee_rate_ppm trop élevé: {fee_rate} > {rules['fee_rate_ppm_max']}"
            )
        
        # Time lock delta
        time_lock = int(policy.get("time_lock_delta", 40))
        if time_lock < rules["time_lock_delta_min"]:
            raise ValidationError(
                f"time_lock_delta trop faible: {time_lock} < {rules['time_lock_delta_min']}"
            )
        if time_lock > rules["time_lock_delta_max"]:
            raise ValidationError(
                f"time_lock_delta trop élevé: {time_lock} > {rules['time_lock_delta_max']}"
            )
    
    def _check_rate_limit(self, channel_id: str):
        """
        Vérifie que le taux de changement est respecté (cooldown).
        
        Raises:
            ValidationError si trop de changements récents
        """
        now = datetime.utcnow()
        
        # Récupérer historique
        history = self.change_history.get(channel_id, [])
        
        # Filtrer les changements des dernières 24h
        cutoff = now - timedelta(days=1)
        recent_changes = [
            ts for ts in history
            if isinstance(ts, datetime) and ts > cutoff
        ]
        
        # Vérifier nombre de changements par jour
        max_per_day = self.rate_limits["max_changes_per_channel_per_day"]
        if len(recent_changes) >= max_per_day:
            raise ValidationError(
                f"Trop de changements récents: {len(recent_changes)}/{max_per_day} par jour"
            )
        
        # Vérifier cooldown
        if recent_changes:
            last_change = max(recent_changes)
            cooldown_minutes = self.rate_limits["cooldown_minutes"]
            cooldown = timedelta(minutes=cooldown_minutes)
            
            if now - last_change < cooldown:
                remaining = cooldown - (now - last_change)
                raise ValidationError(
                    f"Cooldown actif: {remaining.seconds // 60} minutes restantes"
                )
    
    def _check_change_magnitude(
        self,
        current_policy: Dict[str, Any],
        new_policy: Dict[str, Any]
    ):
        """
        Vérifie que le changement n'est pas trop brutal.
        
        Raises:
            ValidationError si changement trop important
        """
        max_change_pct = self.safety_rules["max_change_percent"]
        
        # Vérifier base_fee
        current_base = int(current_policy.get("base_fee_msat", 1000))
        new_base = int(new_policy.get("base_fee_msat", 1000))
        
        if current_base > 0:
            change_ratio = abs(new_base - current_base) / current_base
            if change_ratio > max_change_pct:
                raise ValidationError(
                    f"Changement base_fee trop important: {change_ratio*100:.1f}% > {max_change_pct*100:.1f}%"
                )
        
        # Vérifier fee_rate
        current_rate = int(current_policy.get("fee_rate_ppm", 500))
        new_rate = int(new_policy.get("fee_rate_ppm", 500))
        
        if current_rate > 0:
            change_ratio = abs(new_rate - current_rate) / current_rate
            if change_ratio > max_change_pct:
                raise ValidationError(
                    f"Changement fee_rate trop important: {change_ratio*100:.1f}% > {max_change_pct*100:.1f}%"
                )
    
    def _validate_rebalance(
        self,
        channel: Dict[str, Any],
        rebalance_params: Dict[str, Any]
    ):
        """
        Valide une opération de rebalance.
        
        Raises:
            ValidationError si rebalance invalide
        """
        rules = self.config.get("rebalance_rules", {})
        
        capacity = int(channel.get("capacity", 0))
        amount = int(rebalance_params.get("amount_sats", 0))
        
        # Montant minimum
        min_amount = rules.get("min_amount_sats", 100000)
        if amount < min_amount:
            raise ValidationError(
                f"Montant rebalance trop faible: {amount} < {min_amount} sats"
            )
        
        # Montant maximum (% de capacité)
        max_pct = rules.get("max_amount_percent", 0.5)
        max_amount = int(capacity * max_pct)
        
        if amount > max_amount:
            raise ValidationError(
                f"Montant rebalance trop élevé: {amount} > {max_amount} sats ({max_pct*100:.0f}% de capacité)"
            )
        
        # Coût maximum
        cost = int(rebalance_params.get("cost_sats", 0))
        max_cost_pct = rules.get("max_cost_percent", 0.005)
        max_cost = int(amount * max_cost_pct)
        
        if cost > max_cost:
            raise ValidationError(
                f"Coût rebalance trop élevé: {cost} > {max_cost} sats ({max_cost_pct*100:.2f}% du montant)"
            )
        
        # Vérifier disponibilité liquidité
        direction = rebalance_params.get("direction", "outbound")
        local_balance = int(channel.get("local_balance", 0))
        remote_balance = int(channel.get("remote_balance", 0))
        
        if direction == "outbound" and amount > local_balance:
            raise ValidationError(
                f"Liquidité locale insuffisante: {amount} > {local_balance} sats"
            )
        elif direction == "inbound" and amount > remote_balance:
            raise ValidationError(
                f"Liquidité remote insuffisante: {amount} > {remote_balance} sats"
            )
    
    def record_change(self, channel_id: str):
        """
        Enregistre un changement dans l'historique (pour cooldown).
        
        Args:
            channel_id: ID du canal
        """
        if channel_id not in self.change_history:
            self.change_history[channel_id] = []
        
        self.change_history[channel_id].append(datetime.utcnow())
        
        logger.debug(f"Changement enregistré pour canal {channel_id[:8]}")
    
    def add_to_blacklist(self, channel_id: str):
        """Ajoute un canal à la blacklist."""
        if channel_id not in self.blacklist:
            self.blacklist.append(channel_id)
            logger.info(f"Canal {channel_id[:8]} ajouté à la blacklist")
    
    def remove_from_blacklist(self, channel_id: str):
        """Retire un canal de la blacklist."""
        if channel_id in self.blacklist:
            self.blacklist.remove(channel_id)
            logger.info(f"Canal {channel_id[:8]} retiré de la blacklist")
    
    def get_validation_report(self, channel: Dict[str, Any]) -> Dict[str, Any]:
        """
        Génère un rapport de validation pour un canal.
        
        Args:
            channel: Données du canal
        
        Returns:
            Dict avec état de validation et contraintes
        """
        channel_id = channel.get("channel_id")
        current_policy = channel.get("policy", {})
        
        report = {
            "channel_id": channel_id,
            "blacklisted": channel_id in self.blacklist,
            "current_policy": current_policy,
            "constraints": {
                "base_fee_range": [
                    self.safety_rules["base_fee_msat_min"],
                    self.safety_rules["base_fee_msat_max"]
                ],
                "fee_rate_range": [
                    self.safety_rules["fee_rate_ppm_min"],
                    self.safety_rules["fee_rate_ppm_max"]
                ],
                "max_change_percent": self.safety_rules["max_change_percent"] * 100
            },
            "cooldown": {}
        }
        
        # Calculer cooldown restant
        history = self.change_history.get(channel_id, [])
        if history:
            last_change = max(h for h in history if isinstance(h, datetime))
            cooldown_end = last_change + timedelta(minutes=self.rate_limits["cooldown_minutes"])
            now = datetime.utcnow()
            
            if cooldown_end > now:
                report["cooldown"] = {
                    "active": True,
                    "remaining_minutes": (cooldown_end - now).seconds // 60
                }
            else:
                report["cooldown"] = {"active": False}
        else:
            report["cooldown"] = {"active": False}
        
        # Compter changements récents
        cutoff = datetime.utcnow() - timedelta(days=1)
        recent = [h for h in history if isinstance(h, datetime) and h > cutoff]
        report["recent_changes_24h"] = len(recent)
        report["remaining_changes_today"] = max(
            0,
            self.rate_limits["max_changes_per_channel_per_day"] - len(recent)
        )
        
        return report
