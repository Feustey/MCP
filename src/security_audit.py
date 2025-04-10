import asyncio
import logging
import time
import json
import hashlib
import os
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
import hmac
import base64
import secrets
from enum import Enum
import jwt

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("security_audit")

class SecurityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SecurityEvent(Enum):
    LOGIN_ATTEMPT = "login_attempt"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    API_REQUEST = "api_request"
    NODE_OPERATION = "node_operation"
    CHANNEL_OPERATION = "channel_operation"
    WALLET_OPERATION = "wallet_operation"
    CONFIGURATION_CHANGE = "configuration_change"
    PERMISSION_CHANGE = "permission_change"
    UNUSUAL_ACTIVITY = "unusual_activity"
    UNAUTHORIZED_ACCESS = "unauthorized_access"

class SecurityAuditManager:
    """
    Gestionnaire d'audit de sécurité pour surveiller et enregistrer les opérations
    sensibles sur les nœuds Lightning.
    """
    
    def __init__(self, 
                 audit_log_path: str = "logs/security_audit.log",
                 max_log_size_mb: int = 10,
                 max_log_age_days: int = 30,
                 jwt_secret: Optional[str] = None):
        self.audit_log_path = audit_log_path
        self.max_log_size_mb = max_log_size_mb
        self.max_log_age_days = max_log_age_days
        self.jwt_secret = jwt_secret or os.environ.get("JWT_SECRET") or secrets.token_hex(32)
        
        # Assurer que le répertoire de logs existe
        os.makedirs(os.path.dirname(audit_log_path), exist_ok=True)
        
        # Configurer le handler de fichier pour le logging
        self.file_handler = logging.FileHandler(audit_log_path)
        self.file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(self.file_handler)
        
        # Liste des opérations sensibles qui nécessitent une vérification supplémentaire
        self.sensitive_operations = {
            "open_channel",
            "close_channel",
            "withdraw_funds",
            "change_permissions",
            "update_configuration",
            "add_invoice",
            "cancel_invoice",
            "pay_invoice"
        }
        
        # Dictionnaire pour suivre les tentatives d'opérations échouées
        self.failed_attempts = {}
        
        # Liste d'adresses IP bannies temporairement
        self.banned_ips = set()
        
        # Cache des signatures validées récemment
        self.signature_cache = {}
        
    async def log_event(self, 
                   event_type: SecurityEvent, 
                   user_id: str,
                   ip_address: str,
                   details: Dict[str, Any],
                   level: SecurityLevel = SecurityLevel.MEDIUM) -> str:
        """
        Enregistre un événement de sécurité dans le journal d'audit
        
        Args:
            event_type: Type d'événement de sécurité
            user_id: Identifiant de l'utilisateur
            ip_address: Adresse IP de l'utilisateur
            details: Détails de l'événement
            level: Niveau de sécurité de l'événement
            
        Returns:
            L'identifiant unique de l'entrée de journal
        """
        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Créer l'entrée de journal
        log_entry = {
            "event_id": event_id,
            "timestamp": timestamp,
            "event_type": event_type.value,
            "security_level": level.value,
            "user_id": user_id,
            "ip_address": ip_address,
            "details": details
        }
        
        # Enregistrer dans le fichier de log
        log_str = json.dumps(log_entry)
        if level == SecurityLevel.HIGH or level == SecurityLevel.CRITICAL:
            logger.warning(log_str)
        else:
            logger.info(log_str)
            
        # Vérifier si la rotation des logs est nécessaire
        await self._check_log_rotation()
        
        # Pour les événements critiques, envoyer une alerte
        if level == SecurityLevel.CRITICAL:
            await self._send_security_alert(log_entry)
            
        return event_id
    
    async def verify_operation(self, 
                         operation: str,
                         user_id: str, 
                         ip_address: str,
                         params: Dict[str, Any],
                         signature: Optional[str] = None) -> Tuple[bool, str]:
        """
        Vérifie si une opération est autorisée et valide
        
        Args:
            operation: Nom de l'opération
            user_id: Identifiant de l'utilisateur
            ip_address: Adresse IP de l'utilisateur
            params: Paramètres de l'opération
            signature: Signature de sécurité pour l'opération (si applicable)
            
        Returns:
            Un tuple (autorisé, message)
        """
        # Vérifier si l'IP est bannie
        if ip_address in self.banned_ips:
            await self.log_event(
                SecurityEvent.UNAUTHORIZED_ACCESS,
                user_id,
                ip_address,
                {"operation": operation, "reason": "IP bannie"},
                SecurityLevel.HIGH
            )
            return False, "Accès refusé: votre adresse IP est temporairement bloquée"
        
        # Vérifier si l'opération est sensible
        is_sensitive = operation in self.sensitive_operations
        
        # Pour les opérations sensibles, effectuer des vérifications supplémentaires
        if is_sensitive:
            # 1. Vérifier la signature si fournie
            if signature:
                sig_valid = await self._verify_signature(user_id, operation, params, signature)
                if not sig_valid:
                    # Enregistrer la tentative échouée
                    await self._record_failed_attempt(user_id, ip_address, operation)
                    
                    await self.log_event(
                        SecurityEvent.UNAUTHORIZED_ACCESS,
                        user_id,
                        ip_address,
                        {"operation": operation, "reason": "Signature invalide"},
                        SecurityLevel.HIGH
                    )
                    return False, "Signature de sécurité invalide"
            else:
                # Opération sensible sans signature
                await self.log_event(
                    SecurityEvent.UNAUTHORIZED_ACCESS,
                    user_id,
                    ip_address,
                    {"operation": operation, "reason": "Signature manquante"},
                    SecurityLevel.HIGH
                )
                return False, "Cette opération nécessite une signature de sécurité"
                
            # 2. Vérifier les limites et seuils spécifiques à l'opération
            operation_allowed, reason = await self._check_operation_limits(operation, user_id, params)
            if not operation_allowed:
                await self.log_event(
                    SecurityEvent.UNAUTHORIZED_ACCESS,
                    user_id,
                    ip_address,
                    {"operation": operation, "reason": reason},
                    SecurityLevel.MEDIUM
                )
                return False, reason
        
        # Enregistrer l'opération autorisée
        security_level = SecurityLevel.HIGH if is_sensitive else SecurityLevel.MEDIUM
        await self.log_event(
            SecurityEvent.NODE_OPERATION if "channel" in operation else SecurityEvent.API_REQUEST,
            user_id,
            ip_address,
            {"operation": operation, "params": self._sanitize_params(params)},
            security_level
        )
        
        return True, "Opération autorisée"
    
    async def generate_operation_token(self, 
                                 user_id: str, 
                                 operation: str, 
                                 params: Dict[str, Any],
                                 expiration_minutes: int = 15) -> str:
        """
        Génère un token JWT pour une opération sensible
        
        Args:
            user_id: Identifiant de l'utilisateur
            operation: Nom de l'opération
            params: Paramètres de l'opération
            expiration_minutes: Durée de validité du token en minutes
            
        Returns:
            Token JWT encodé
        """
        # Créer les données du payload
        payload = {
            "sub": user_id,
            "operation": operation,
            "params_hash": self._hash_params(params),
            "exp": datetime.utcnow() + timedelta(minutes=expiration_minutes),
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4())
        }
        
        # Encoder le token JWT
        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        
        return token
    
    async def verify_operation_token(self, token: str, operation: str, params: Dict[str, Any]) -> Tuple[bool, str, str]:
        """
        Vérifie un token JWT pour une opération sensible
        
        Args:
            token: Token JWT à vérifier
            operation: Nom de l'opération
            params: Paramètres de l'opération
            
        Returns:
            Tuple (valide, user_id, message)
        """
        try:
            # Décoder le token JWT
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            
            # Vérifier l'opération
            if payload["operation"] != operation:
                return False, "", "Opération non autorisée par ce token"
                
            # Vérifier le hash des paramètres
            params_hash = self._hash_params(params)
            if payload["params_hash"] != params_hash:
                return False, "", "Paramètres modifiés après génération du token"
                
            # Extraire l'utilisateur
            user_id = payload["sub"]
            
            return True, user_id, "Token valide"
            
        except jwt.ExpiredSignatureError:
            return False, "", "Token expiré"
        except jwt.InvalidTokenError:
            return False, "", "Token invalide"
    
    async def _verify_signature(self, user_id: str, operation: str, params: Dict[str, Any], signature: str) -> bool:
        """Vérifie la signature d'une opération"""
        # Vérifier si la signature est dans le cache
        cache_key = f"{user_id}:{operation}:{self._hash_params(params)}:{signature}"
        if cache_key in self.signature_cache:
            return self.signature_cache[cache_key]
            
        # Logique de vérification de signature
        # Dans un vrai système, on pourrait vérifier avec une clé publique de l'utilisateur
        # ou un autre mécanisme d'authentification
        
        # Pour l'exemple, on considère la signature valide si elle correspond à un format spécifique
        signature_valid = bool(re.match(r'^[a-f0-9]{64}$', signature))
        
        # Mettre en cache le résultat
        self.signature_cache[cache_key] = signature_valid
        
        # Nettoyer le cache si trop grand
        if len(self.signature_cache) > 1000:
            # Garder seulement les 500 plus récentes entrées
            self.signature_cache = dict(list(self.signature_cache.items())[-500:])
            
        return signature_valid
    
    async def _record_failed_attempt(self, user_id: str, ip_address: str, operation: str) -> None:
        """Enregistre une tentative échouée et bannit temporairement l'IP si nécessaire"""
        current_time = time.time()
        
        # Clés pour l'utilisateur et l'IP
        user_key = f"user:{user_id}"
        ip_key = f"ip:{ip_address}"
        
        # Nettoyer les anciennes tentatives (plus de 1 heure)
        for key in [user_key, ip_key]:
            if key in self.failed_attempts:
                self.failed_attempts[key] = [
                    attempt for attempt in self.failed_attempts.get(key, [])
                    if current_time - attempt["timestamp"] < 3600
                ]
        
        # Ajouter la nouvelle tentative
        attempt = {
            "timestamp": current_time,
            "operation": operation
        }
        
        if user_key not in self.failed_attempts:
            self.failed_attempts[user_key] = []
        self.failed_attempts[user_key].append(attempt)
        
        if ip_key not in self.failed_attempts:
            self.failed_attempts[ip_key] = []
        self.failed_attempts[ip_key].append(attempt)
        
        # Vérifier si l'IP doit être bannie (10 tentatives échouées en 1 heure)
        if len(self.failed_attempts.get(ip_key, [])) >= 10:
            self.banned_ips.add(ip_address)
            
            # Programmer la levée du bannissement après 1 heure
            asyncio.create_task(self._unban_ip_after_delay(ip_address, 3600))
            
            logger.warning(f"IP {ip_address} bannie temporairement pour 1 heure")
    
    async def _unban_ip_after_delay(self, ip_address: str, delay_seconds: int) -> None:
        """Retire une IP de la liste des bannis après un délai"""
        await asyncio.sleep(delay_seconds)
        if ip_address in self.banned_ips:
            self.banned_ips.remove(ip_address)
            logger.info(f"IP {ip_address} retirée de la liste des bannis")
    
    async def _check_operation_limits(self, operation: str, user_id: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Vérifie les limites spécifiques à une opération"""
        # Logique spécifique selon le type d'opération
        if operation == "open_channel":
            # Vérifier le montant minimum pour ouvrir un canal
            amount = params.get("amount", 0)
            if amount < 20000:  # 20k sats minimum
                return False, "Le montant minimum pour ouvrir un canal est de 20,000 sats"
                
        elif operation == "withdraw_funds":
            # Vérifier le montant maximum de retrait par jour
            amount = params.get("amount", 0)
            # Logique pour vérifier la limite quotidienne (exemple simplifié)
            if amount > 1000000:  # 1M sats maximum par retrait
                return False, "Le montant maximum par retrait est de 1,000,000 sats"
        
        return True, ""
    
    def _hash_params(self, params: Dict[str, Any]) -> str:
        """Calcule un hash des paramètres d'opération"""
        params_str = json.dumps(params, sort_keys=True)
        return hashlib.sha256(params_str.encode()).hexdigest()
    
    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Nettoie les paramètres sensibles pour le logging"""
        sanitized = params.copy()
        
        # Liste des clés sensibles à masquer
        sensitive_keys = ["password", "token", "secret", "key", "macaroon", "credentials"]
        
        # Masquer les valeurs sensibles
        for key in sanitized:
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "********"
                
        return sanitized
    
    async def _check_log_rotation(self) -> None:
        """Vérifie si la rotation des logs est nécessaire"""
        try:
            # Vérifier la taille du fichier
            file_size_mb = os.path.getsize(self.audit_log_path) / (1024 * 1024)
            
            if file_size_mb >= self.max_log_size_mb:
                await self._rotate_logs()
                
            # Vérifier les anciens fichiers de log à supprimer
            await self._clean_old_logs()
                
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de rotation des logs: {str(e)}")
    
    async def _rotate_logs(self) -> None:
        """Effectue la rotation des fichiers de log"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.audit_log_path}.{timestamp}"
        
        # Fermer le handler de fichier actuel
        self.file_handler.close()
        logger.removeHandler(self.file_handler)
        
        # Renommer le fichier actuel
        os.rename(self.audit_log_path, backup_path)
        
        # Créer un nouveau fichier de log
        self.file_handler = logging.FileHandler(self.audit_log_path)
        self.file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(self.file_handler)
        
        logger.info(f"Rotation des logs effectuée, ancien fichier: {backup_path}")
    
    async def _clean_old_logs(self) -> None:
        """Supprime les fichiers de log plus anciens que max_log_age_days"""
        log_dir = os.path.dirname(self.audit_log_path)
        log_name = os.path.basename(self.audit_log_path)
        
        # Trouver tous les fichiers de backup de log
        for filename in os.listdir(log_dir):
            if filename.startswith(log_name + "."):
                file_path = os.path.join(log_dir, filename)
                
                # Vérifier l'âge du fichier
                file_age_days = (datetime.now() - datetime.fromtimestamp(os.path.getctime(file_path))).days
                
                if file_age_days > self.max_log_age_days:
                    os.remove(file_path)
                    logger.info(f"Ancien fichier de log supprimé: {file_path}")
    
    async def _send_security_alert(self, log_entry: Dict[str, Any]) -> None:
        """Envoie une alerte pour un événement de sécurité critique"""
        # Cette fonction pourrait envoyer un email, un SMS, ou une notification à un système de monitoring
        # Pour l'exemple, on se contente de logger l'alerte
        logger.critical(f"ALERTE DE SÉCURITÉ: {json.dumps(log_entry)}")
        
        # Dans un vrai système, on pourrait avoir:
        # await notify_service.send_email(admin_email, "Alerte de sécurité", json.dumps(log_entry))
        # await notify_service.send_sms(admin_phone, f"Alerte: {log_entry['event_type']} par {log_entry['user_id']}")


# Classe pour auditer les opérations sur les nœuds Lightning
class LightningNodeAuditor:
    """
    Auditeur spécialisé pour les opérations sur les nœuds Lightning.
    Fournit des vérifications et des journalisations spécifiques aux opérations Lightning.
    """
    
    def __init__(self, security_manager: SecurityAuditManager):
        self.security_manager = security_manager
        self.logger = logger
        
        # Définir les limites des opérations
        self.operation_limits = {
            "daily_outbound": 1000000,  # Limite quotidienne de paiements sortants (sats)
            "max_channel_size": 5000000,  # Taille maximale de canal (sats)
            "min_channel_size": 20000,   # Taille minimale de canal (sats)
            "max_fee_rate": 5000,        # Taux de frais maximum (ppm)
        }
        
        # Cache des opérations récentes par utilisateur
        self.user_operations = {}
    
    async def audit_channel_open(self, 
                            user_id: str, 
                            ip_address: str, 
                            node_id: str, 
                            amount: int,
                            is_private: bool = False) -> Tuple[bool, str]:
        """
        Audite et autorise l'ouverture d'un canal Lightning
        
        Args:
            user_id: Identifiant de l'utilisateur
            ip_address: Adresse IP de l'utilisateur
            node_id: Identifiant du nœud destinataire
            amount: Montant en satoshis
            is_private: Si le canal est privé
            
        Returns:
            (autorisé, message)
        """
        # Vérifier les limites de montant
        if amount < self.operation_limits["min_channel_size"]:
            return False, f"Montant trop faible. Minimum: {self.operation_limits['min_channel_size']} sats"
            
        if amount > self.operation_limits["max_channel_size"]:
            return False, f"Montant trop élevé. Maximum: {self.operation_limits['max_channel_size']} sats"
        
        # Vérifier si le nœud est sur une liste noire
        is_blacklisted = await self._check_node_blacklist(node_id)
        if is_blacklisted:
            await self.security_manager.log_event(
                SecurityEvent.CHANNEL_OPERATION,
                user_id,
                ip_address,
                {
                    "operation": "open_channel",
                    "node_id": node_id,
                    "amount": amount,
                    "reason": "nœud sur liste noire"
                },
                SecurityLevel.HIGH
            )
            return False, "Ce nœud est sur la liste noire"
        
        # Enregistrer l'opération dans l'audit
        await self.security_manager.log_event(
            SecurityEvent.CHANNEL_OPERATION,
            user_id,
            ip_address,
            {
                "operation": "open_channel",
                "node_id": node_id,
                "amount": amount,
                "is_private": is_private
            },
            SecurityLevel.HIGH
        )
        
        # Mettre à jour le cache des opérations utilisateur
        self._record_user_operation(user_id, "open_channel", amount)
        
        return True, "Ouverture de canal autorisée"
    
    async def audit_channel_close(self,
                             user_id: str,
                             ip_address: str,
                             channel_id: str,
                             force_close: bool = False) -> Tuple[bool, str]:
        """
        Audite et autorise la fermeture d'un canal Lightning
        
        Args:
            user_id: Identifiant de l'utilisateur
            ip_address: Adresse IP de l'utilisateur
            channel_id: Identifiant du canal
            force_close: Si c'est une fermeture forcée
            
        Returns:
            (autorisé, message)
        """
        # Les fermetures forcées nécessitent plus de vérifications
        if force_close:
            # Enregistrer avec un niveau de sécurité élevé
            await self.security_manager.log_event(
                SecurityEvent.CHANNEL_OPERATION,
                user_id,
                ip_address,
                {
                    "operation": "force_close_channel",
                    "channel_id": channel_id
                },
                SecurityLevel.HIGH
            )
            
            # Vérifier si l'utilisateur a effectué trop de fermetures forcées récemment
            recent_force_closes = self._count_recent_operations(user_id, "force_close_channel", hours=24)
            if recent_force_closes >= 5:  # Limite arbitraire pour l'exemple
                return False, "Trop de fermetures forcées dans les dernières 24 heures"
        else:
            # Fermeture normale (coopérative)
            await self.security_manager.log_event(
                SecurityEvent.CHANNEL_OPERATION,
                user_id,
                ip_address,
                {
                    "operation": "close_channel",
                    "channel_id": channel_id
                },
                SecurityLevel.MEDIUM
            )
        
        # Mettre à jour le cache des opérations utilisateur
        self._record_user_operation(user_id, "close_channel" if not force_close else "force_close_channel")
        
        return True, "Fermeture de canal autorisée"
    
    async def audit_payment(self,
                       user_id: str,
                       ip_address: str,
                       payment_hash: str,
                       amount: int,
                       memo: str = "") -> Tuple[bool, str]:
        """
        Audite et autorise un paiement Lightning
        
        Args:
            user_id: Identifiant de l'utilisateur
            ip_address: Adresse IP de l'utilisateur
            payment_hash: Hash du paiement
            amount: Montant en satoshis
            memo: Description du paiement
            
        Returns:
            (autorisé, message)
        """
        # Vérifier le montant cumulé des paiements quotidiens
        daily_outbound = self._get_daily_outbound(user_id)
        if daily_outbound + amount > self.operation_limits["daily_outbound"]:
            await self.security_manager.log_event(
                SecurityEvent.WALLET_OPERATION,
                user_id,
                ip_address,
                {
                    "operation": "payment",
                    "payment_hash": payment_hash,
                    "amount": amount,
                    "daily_total": daily_outbound,
                    "denied_reason": "limite quotidienne dépassée"
                },
                SecurityLevel.HIGH
            )
            return False, f"Limite quotidienne de paiement dépassée ({daily_outbound}/{self.operation_limits['daily_outbound']} sats)"
            
        # Vérifier si le mémo contient des mots-clés suspects
        if self._contains_suspicious_keywords(memo):
            await self.security_manager.log_event(
                SecurityEvent.WALLET_OPERATION,
                user_id,
                ip_address,
                {
                    "operation": "payment",
                    "payment_hash": payment_hash,
                    "amount": amount,
                    "memo": memo,
                    "flagged": True
                },
                SecurityLevel.HIGH
            )
            # On autorise mais on flag
            self.logger.warning(f"Paiement avec mémo suspect: {memo}")
        
        # Enregistrer le paiement dans l'audit
        await self.security_manager.log_event(
            SecurityEvent.WALLET_OPERATION,
            user_id,
            ip_address,
            {
                "operation": "payment",
                "payment_hash": payment_hash,
                "amount": amount,
                "memo": memo.replace('"', '')[:100]  # Tronquer et nettoyer
            },
            SecurityLevel.MEDIUM
        )
        
        # Mettre à jour le cache des opérations utilisateur
        self._record_user_operation(user_id, "payment", amount)
        
        return True, "Paiement autorisé"
    
    async def _check_node_blacklist(self, node_id: str) -> bool:
        """Vérifie si un nœud est sur la liste noire"""
        # Cette fonction pourrait vérifier une liste noire stockée en base de données
        # Pour l'exemple, on vérifie juste une liste fixe
        blacklisted_nodes = [
            "02aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "03bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        ]
        return node_id in blacklisted_nodes
    
    def _record_user_operation(self, user_id: str, operation: str, amount: int = 0) -> None:
        """Enregistre une opération d'utilisateur dans le cache"""
        if user_id not in self.user_operations:
            self.user_operations[user_id] = []
            
        # Ajouter l'opération
        self.user_operations[user_id].append({
            "operation": operation,
            "amount": amount,
            "timestamp": time.time()
        })
        
        # Nettoyer les opérations anciennes (plus de 24 heures)
        self.user_operations[user_id] = [
            op for op in self.user_operations[user_id]
            if time.time() - op["timestamp"] < 24 * 3600
        ]
    
    def _get_daily_outbound(self, user_id: str) -> int:
        """Calcule le total des paiements sortants pour un utilisateur dans les dernières 24h"""
        if user_id not in self.user_operations:
            return 0
            
        # Filtrer les opérations de paiement des dernières 24h
        payment_ops = [
            op for op in self.user_operations[user_id]
            if op["operation"] == "payment" and time.time() - op["timestamp"] < 24 * 3600
        ]
        
        # Calculer le total
        return sum(op["amount"] for op in payment_ops)
    
    def _count_recent_operations(self, user_id: str, operation_type: str, hours: int = 24) -> int:
        """Compte le nombre d'opérations d'un certain type dans la période spécifiée"""
        if user_id not in self.user_operations:
            return 0
            
        # Filtrer par type d'opération et période
        matching_ops = [
            op for op in self.user_operations[user_id]
            if op["operation"] == operation_type and time.time() - op["timestamp"] < hours * 3600
        ]
        
        return len(matching_ops)
    
    def _contains_suspicious_keywords(self, text: str) -> bool:
        """Vérifie si un texte contient des mots-clés suspects"""
        if not text:
            return False
            
        # Liste de mots-clés suspects (exemple)
        suspicious_keywords = [
            "darknet", "illicit", "illegal", "drugs", "weapons", "hack", "ransom"
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in suspicious_keywords) 