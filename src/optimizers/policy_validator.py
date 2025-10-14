"""
Policy Validator - Validation des policies avant application
Dernière mise à jour: 12 octobre 2025
Version: 1.0.0

Valide les policies de fees avant application pour:
- Respect des limites min/max
- Changements raisonnables
- Règles business
- Blacklist/Whitelist
- Limites de sécurité
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

import structlog

logger = structlog.get_logger(__name__)


class ValidationResult(Enum):
    """Résultats de validation possibles"""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    BLOCKED = "blocked"


@dataclass
class PolicyLimits:
    """Limites pour les policies"""
    min_base_fee_msat: int = 0
    max_base_fee_msat: int = 10000
    min_fee_rate_ppm: int = 1
    max_fee_rate_ppm: int = 10000
    max_change_percent: float = 50.0  # Changement max en %
    min_channel_age_days: int = 7
    min_channel_capacity_sats: int = 100000
    max_changes_per_day: int = 5
    cooldown_hours: int = 24


@dataclass
class ValidationError:
    """Détails d'une erreur de validation"""
    field: str
    message: str
    current_value: Any
    expected_value: Any
    severity: ValidationResult


class PolicyValidator:
    """
    Validateur de policies Lightning
    
    Vérifie que les policies respectent:
    - Les limites techniques
    - Les règles business
    - Les contraintes de sécurité
    - Les blacklists/whitelists
    """
    
    def __init__(
        self,
        limits: Optional[PolicyLimits] = None,
        blacklist_channels: Optional[List[str]] = None,
        whitelist_nodes: Optional[List[str]] = None,
        dry_run: bool = True
    ):
        """
        Initialise le validateur
        
        Args:
            limits: Limites de validation
            blacklist_channels: Canaux interdits
            whitelist_nodes: Nœuds autorisés (None = tous)
            dry_run: Mode dry-run (validation only)
        """
        self.limits = limits or PolicyLimits()
        self.blacklist_channels = set(blacklist_channels or [])
        self.whitelist_nodes = set(whitelist_nodes or []) if whitelist_nodes else None
        self.dry_run = dry_run
        
        # Historique des changements (pour limites quotidiennes)
        self._change_history: Dict[str, List[datetime]] = {}
        
        logger.info(
            "policy_validator_initialized",
            dry_run=dry_run,
            blacklist_count=len(self.blacklist_channels),
            whitelist_enabled=self.whitelist_nodes is not None
        )
    
    def validate_policy(
        self,
        channel_id: str,
        new_policy: Dict[str, Any],
        current_policy: Optional[Dict[str, Any]] = None,
        node_pubkey: Optional[str] = None,
        channel_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[ValidationResult, List[ValidationError]]:
        """
        Valide une policy complète
        
        Args:
            channel_id: ID du canal
            new_policy: Nouvelle policy proposée
            current_policy: Policy actuelle (None si nouvelle)
            node_pubkey: Pubkey du nœud peer
            channel_info: Informations du canal
            
        Returns:
            Tuple (result, errors)
        """
        errors: List[ValidationError] = []
        
        # 1. Vérifier blacklist
        if channel_id in self.blacklist_channels:
            errors.append(ValidationError(
                field="channel_id",
                message="Channel is blacklisted",
                current_value=channel_id,
                expected_value=None,
                severity=ValidationResult.BLOCKED
            ))
            return ValidationResult.BLOCKED, errors
        
        # 2. Vérifier whitelist nœud
        if self.whitelist_nodes is not None and node_pubkey:
            if node_pubkey not in self.whitelist_nodes:
                errors.append(ValidationError(
                    field="node_pubkey",
                    message="Node is not whitelisted",
                    current_value=node_pubkey,
                    expected_value=None,
                    severity=ValidationResult.BLOCKED
                ))
                return ValidationResult.BLOCKED, errors
        
        # 3. Vérifier les limites de fees
        fee_errors = self._validate_fee_limits(new_policy)
        errors.extend(fee_errors)
        
        # 4. Vérifier les changements raisonnables
        if current_policy:
            change_errors = self._validate_changes(
                channel_id,
                new_policy,
                current_policy
            )
            errors.extend(change_errors)
        
        # 5. Vérifier éligibilité du canal
        if channel_info:
            eligibility_errors = self._validate_eligibility(channel_info)
            errors.extend(eligibility_errors)
        
        # 6. Vérifier limites quotidiennes
        rate_errors = self._validate_change_rate(channel_id)
        errors.extend(rate_errors)
        
        # Déterminer le résultat global
        has_invalid = any(e.severity == ValidationResult.INVALID for e in errors)
        has_blocked = any(e.severity == ValidationResult.BLOCKED for e in errors)
        has_warning = any(e.severity == ValidationResult.WARNING for e in errors)
        
        if has_blocked:
            return ValidationResult.BLOCKED, errors
        elif has_invalid:
            return ValidationResult.INVALID, errors
        elif has_warning:
            return ValidationResult.WARNING, errors
        else:
            return ValidationResult.VALID, errors
    
    def _validate_fee_limits(
        self,
        policy: Dict[str, Any]
    ) -> List[ValidationError]:
        """Valide les limites de fees"""
        errors = []
        
        # Base fee
        base_fee = policy.get("base_fee_msat", 0)
        if base_fee < self.limits.min_base_fee_msat:
            errors.append(ValidationError(
                field="base_fee_msat",
                message=f"Base fee below minimum",
                current_value=base_fee,
                expected_value=f">= {self.limits.min_base_fee_msat}",
                severity=ValidationResult.INVALID
            ))
        
        if base_fee > self.limits.max_base_fee_msat:
            errors.append(ValidationError(
                field="base_fee_msat",
                message=f"Base fee above maximum",
                current_value=base_fee,
                expected_value=f"<= {self.limits.max_base_fee_msat}",
                severity=ValidationResult.INVALID
            ))
        
        # Fee rate
        fee_rate = policy.get("fee_rate_ppm", 0)
        if fee_rate < self.limits.min_fee_rate_ppm:
            errors.append(ValidationError(
                field="fee_rate_ppm",
                message=f"Fee rate below minimum",
                current_value=fee_rate,
                expected_value=f">= {self.limits.min_fee_rate_ppm}",
                severity=ValidationResult.INVALID
            ))
        
        if fee_rate > self.limits.max_fee_rate_ppm:
            errors.append(ValidationError(
                field="fee_rate_ppm",
                message=f"Fee rate above maximum",
                current_value=fee_rate,
                expected_value=f"<= {self.limits.max_fee_rate_ppm}",
                severity=ValidationResult.INVALID
            ))
        
        return errors
    
    def _validate_changes(
        self,
        channel_id: str,
        new_policy: Dict[str, Any],
        current_policy: Dict[str, Any]
    ) -> List[ValidationError]:
        """Valide que les changements sont raisonnables"""
        errors = []
        
        # Vérifier base fee change
        current_base_fee = current_policy.get("base_fee_msat", 0)
        new_base_fee = new_policy.get("base_fee_msat", 0)
        
        if current_base_fee > 0:
            change_percent = abs(new_base_fee - current_base_fee) / current_base_fee * 100
            
            if change_percent > self.limits.max_change_percent:
                errors.append(ValidationError(
                    field="base_fee_msat",
                    message=f"Base fee change too large ({change_percent:.1f}%)",
                    current_value=new_base_fee,
                    expected_value=f"Change < {self.limits.max_change_percent}%",
                    severity=ValidationResult.WARNING
                ))
        
        # Vérifier fee rate change
        current_rate = current_policy.get("fee_rate_ppm", 0)
        new_rate = new_policy.get("fee_rate_ppm", 0)
        
        if current_rate > 0:
            change_percent = abs(new_rate - current_rate) / current_rate * 100
            
            if change_percent > self.limits.max_change_percent:
                errors.append(ValidationError(
                    field="fee_rate_ppm",
                    message=f"Fee rate change too large ({change_percent:.1f}%)",
                    current_value=new_rate,
                    expected_value=f"Change < {self.limits.max_change_percent}%",
                    severity=ValidationResult.WARNING
                ))
        
        return errors
    
    def _validate_eligibility(
        self,
        channel_info: Dict[str, Any]
    ) -> List[ValidationError]:
        """Valide l'éligibilité du canal pour optimisation"""
        errors = []
        
        # Âge du canal
        if "age_days" in channel_info:
            age_days = channel_info["age_days"]
            if age_days < self.limits.min_channel_age_days:
                errors.append(ValidationError(
                    field="age_days",
                    message=f"Channel too young",
                    current_value=age_days,
                    expected_value=f">= {self.limits.min_channel_age_days} days",
                    severity=ValidationResult.INVALID
                ))
        
        # Capacité du canal
        capacity = channel_info.get("capacity", 0)
        if capacity < self.limits.min_channel_capacity_sats:
            errors.append(ValidationError(
                field="capacity",
                message=f"Channel capacity too low",
                current_value=capacity,
                expected_value=f">= {self.limits.min_channel_capacity_sats} sats",
                severity=ValidationResult.INVALID
            ))
        
        return errors
    
    def _validate_change_rate(self, channel_id: str) -> List[ValidationError]:
        """Valide le taux de changements (limites quotidiennes)"""
        errors = []
        
        # Nettoyer l'historique (> 24h)
        cutoff = datetime.now() - timedelta(hours=24)
        if channel_id in self._change_history:
            self._change_history[channel_id] = [
                ts for ts in self._change_history[channel_id]
                if ts > cutoff
            ]
        
        # Vérifier la limite
        changes_today = len(self._change_history.get(channel_id, []))
        
        if changes_today >= self.limits.max_changes_per_day:
            errors.append(ValidationError(
                field="changes_per_day",
                message=f"Too many changes today",
                current_value=changes_today,
                expected_value=f"< {self.limits.max_changes_per_day}",
                severity=ValidationResult.BLOCKED
            ))
        
        # Vérifier le cooldown
        if channel_id in self._change_history and self._change_history[channel_id]:
            last_change = self._change_history[channel_id][-1]
            hours_since = (datetime.now() - last_change).total_seconds() / 3600
            
            if hours_since < self.limits.cooldown_hours:
                errors.append(ValidationError(
                    field="cooldown",
                    message=f"Cooldown period not expired",
                    current_value=f"{hours_since:.1f}h",
                    expected_value=f">= {self.limits.cooldown_hours}h",
                    severity=ValidationResult.BLOCKED
                ))
        
        return errors
    
    def record_change(self, channel_id: str):
        """Enregistre un changement dans l'historique"""
        if channel_id not in self._change_history:
            self._change_history[channel_id] = []
        
        self._change_history[channel_id].append(datetime.now())
        
        logger.info(
            "policy_change_recorded",
            channel_id=channel_id,
            changes_today=len(self._change_history[channel_id])
        )
    
    def get_validation_summary(
        self,
        result: ValidationResult,
        errors: List[ValidationError]
    ) -> Dict[str, Any]:
        """
        Génère un résumé de validation
        
        Args:
            result: Résultat global
            errors: Liste des erreurs
            
        Returns:
            Résumé formaté
        """
        return {
            "result": result.value,
            "valid": result == ValidationResult.VALID,
            "error_count": len(errors),
            "errors": [
                {
                    "field": e.field,
                    "message": e.message,
                    "current": e.current_value,
                    "expected": e.expected_value,
                    "severity": e.severity.value
                }
                for e in errors
            ],
            "timestamp": datetime.now().isoformat()
        }


# ═══════════════════════════════════════════════════════════
# RÈGLES BUSINESS SPÉCIFIQUES
# ═══════════════════════════════════════════════════════════

class BusinessRules:
    """Règles métier pour la validation de policies"""
    
    @staticmethod
    def validate_fee_competitiveness(
        new_fee_rate: int,
        network_median: int,
        tolerance_ppm: int = 500
    ) -> Optional[ValidationError]:
        """
        Valide que les fees restent compétitifs
        
        Args:
            new_fee_rate: Nouveau fee rate
            network_median: Médiane du réseau
            tolerance_ppm: Tolérance en ppm
            
        Returns:
            ValidationError si non compétitif
        """
        # Trop au-dessus de la médiane
        if new_fee_rate > network_median + tolerance_ppm:
            return ValidationError(
                field="fee_rate_ppm",
                message="Fee rate significantly above network median",
                current_value=new_fee_rate,
                expected_value=f"<= {network_median + tolerance_ppm}",
                severity=ValidationResult.WARNING
            )
        
        return None
    
    @staticmethod
    def validate_liquidity_impact(
        channel_balance: Dict[str, int],
        new_fees: Dict[str, int]
    ) -> Optional[ValidationError]:
        """
        Valide l'impact sur la liquidité
        
        Args:
            channel_balance: Balance actuelle (local, remote)
            new_fees: Nouveaux fees proposés
            
        Returns:
            ValidationError si impact négatif potentiel
        """
        local = channel_balance.get("local_balance", 0)
        remote = channel_balance.get("remote_balance", 0)
        total = local + remote
        
        if total == 0:
            return None
        
        local_ratio = local / total
        
        # Si trop de liquidité locale et fees augmentent → problème
        if local_ratio > 0.8 and new_fees.get("fee_rate_ppm", 0) > 1000:
            return ValidationError(
                field="fee_rate_ppm",
                message="High fees with high local balance may reduce outbound",
                current_value=new_fees.get("fee_rate_ppm"),
                expected_value="Consider lower fees to encourage outbound",
                severity=ValidationResult.WARNING
            )
        
        # Si peu de liquidité locale et fees diminuent → ok mais warning
        if local_ratio < 0.2 and new_fees.get("fee_rate_ppm", 0) < 10:
            return ValidationError(
                field="fee_rate_ppm",
                message="Low fees with low local balance",
                current_value=new_fees.get("fee_rate_ppm"),
                expected_value="Consider higher fees or rebalancing first",
                severity=ValidationResult.WARNING
            )
        
        return None
    
    @staticmethod
    def validate_peer_quality(
        peer_info: Dict[str, Any],
        min_uptime: float = 0.9
    ) -> Optional[ValidationError]:
        """
        Valide la qualité du peer
        
        Args:
            peer_info: Informations du peer
            min_uptime: Uptime minimum requis
            
        Returns:
            ValidationError si peer de faible qualité
        """
        uptime = peer_info.get("uptime", 1.0)
        
        if uptime < min_uptime:
            return ValidationError(
                field="peer_uptime",
                message="Peer has low uptime",
                current_value=f"{uptime * 100:.1f}%",
                expected_value=f">= {min_uptime * 100:.1f}%",
                severity=ValidationResult.WARNING
            )
        
        return None

