"""
Système d'exceptions hiérarchique pour MCP
Inclut contextualisation, logging automatique et traçabilité

Dernière mise à jour: 9 janvier 2025
"""

import sys
import traceback
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from src.logging_config import get_logger

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """Niveaux de sévérité des erreurs"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Catégories d'erreurs"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    DATABASE = "database"
    CACHE = "cache"
    EXTERNAL_API = "external_api"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Contexte enrichi pour les erreurs"""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    operation: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    component: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le contexte en dictionnaire"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "operation": self.operation,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "component": self.component,
            "additional_data": self.additional_data
        }


class MCPBaseException(Exception):
    """Exception de base pour toutes les erreurs MCP"""
    
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None,
        recoverable: bool = True,
        user_message: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.category = category
        self.context = context or ErrorContext()
        self.original_error = original_error
        self.recoverable = recoverable
        self.user_message = user_message or "Une erreur s'est produite"
        self.error_id = self._generate_error_id()
        
        # Log automatique de l'erreur
        self._log_error()
    
    def _generate_error_id(self) -> str:
        """Génère un ID unique pour l'erreur"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _log_error(self):
        """Log automatique de l'erreur avec contexte"""
        log_data = {
            "error_id": self.error_id,
            "error_type": self.__class__.__name__,
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category.value,
            "recoverable": self.recoverable,
            "context": self.context.to_dict()
        }
        
        if self.original_error:
            log_data["original_error"] = {
                "type": type(self.original_error).__name__,
                "message": str(self.original_error),
                "traceback": traceback.format_exception(
                    type(self.original_error),
                    self.original_error,
                    self.original_error.__traceback__
                )
            }
        
        # Log selon la sévérité
        if self.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            logger.error("Erreur critique détectée", **log_data)
        elif self.severity == ErrorSeverity.MEDIUM:
            logger.warning("Erreur moyenne détectée", **log_data)
        else:
            logger.info("Erreur mineure détectée", **log_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'exception en dictionnaire pour sérialisation"""
        return {
            "error_id": self.error_id,
            "type": self.__class__.__name__,
            "message": self.message,
            "user_message": self.user_message,
            "severity": self.severity.value,
            "category": self.category.value,
            "recoverable": self.recoverable,
            "context": self.context.to_dict(),
            "original_error": str(self.original_error) if self.original_error else None
        }
    
    def add_context(self, **kwargs):
        """Ajoute du contexte à l'erreur"""
        self.context.additional_data.update(kwargs)
        return self


# === Exceptions de Validation ===

class ValidationError(MCPBaseException):
    """Erreur de validation des données"""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
            context=context,
            user_message="Les données fournies ne sont pas valides"
        )
        self.field = field
        self.value = value
        
        if field:
            self.add_context(field=field, value=str(value) if value is not None else None)


class SchemaValidationError(ValidationError):
    """Erreur de validation de schéma"""
    
    def __init__(
        self,
        message: str,
        schema_errors: List[Dict] = None,
        context: Optional[ErrorContext] = None
    ):
        super().__init__(message, context=context)
        self.schema_errors = schema_errors or []
        self.add_context(schema_errors=self.schema_errors)


# === Exceptions d'Authentification/Autorisation ===

class AuthenticationError(MCPBaseException):
    """Erreur d'authentification"""
    
    def __init__(
        self,
        message: str = "Authentification requise",
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.AUTHENTICATION,
            context=context,
            recoverable=False,
            user_message="Veuillez vous authentifier"
        )


class AuthorizationError(MCPBaseException):
    """Erreur d'autorisation"""
    
    def __init__(
        self,
        message: str = "Accès non autorisé",
        required_permission: Optional[str] = None,
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.AUTHORIZATION,
            context=context,
            recoverable=False,
            user_message="Vous n'avez pas les permissions nécessaires"
        )
        if required_permission:
            self.add_context(required_permission=required_permission)


# === Exceptions de Configuration ===

class ConfigurationError(MCPBaseException):
    """Erreur de configuration"""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.CONFIGURATION,
            context=context,
            recoverable=False,
            user_message="Erreur de configuration du système"
        )
        if config_key:
            self.add_context(config_key=config_key)


# === Exceptions Réseau et API ===

class NetworkError(MCPBaseException):
    """Erreur réseau générique"""
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            context=context,
            original_error=original_error,
            user_message="Erreur de connexion réseau"
        )
        if url:
            self.add_context(url=url)
        if status_code:
            self.add_context(status_code=status_code)


class TimeoutError(NetworkError):
    """Erreur de timeout"""
    
    def __init__(
        self,
        message: str,
        timeout_duration: Optional[float] = None,
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            message,
            context=context,
            user_message="La requête a pris trop de temps"
        )
        if timeout_duration:
            self.add_context(timeout_duration=timeout_duration)


class ExternalAPIError(NetworkError):
    """Erreur d'API externe"""
    
    def __init__(
        self,
        message: str,
        api_name: str,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        response_data: Optional[Dict] = None,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message,
            status_code=status_code,
            context=context,
            original_error=original_error
        )
        self.category = ErrorCategory.EXTERNAL_API
        self.api_name = api_name
        
        self.add_context(
            api_name=api_name,
            endpoint=endpoint,
            response_data=response_data
        )


# === Exceptions Base de Données ===

class DatabaseError(MCPBaseException):
    """Erreur de base de données"""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DATABASE,
            context=context,
            original_error=original_error,
            user_message="Erreur de base de données"
        )
        if operation:
            self.add_context(operation=operation)
        if table:
            self.add_context(table=table)


class DatabaseConnectionError(DatabaseError):
    """Erreur de connexion à la base de données"""
    
    def __init__(
        self,
        message: str = "Impossible de se connecter à la base de données",
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message,
            context=context,
            original_error=original_error
        )
        self.severity = ErrorSeverity.CRITICAL


# === Exceptions Cache ===

class CacheError(MCPBaseException):
    """Erreur de cache"""
    
    def __init__(
        self,
        message: str,
        cache_key: Optional[str] = None,
        operation: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.CACHE,
            context=context,
            original_error=original_error,
            user_message="Erreur de cache"
        )
        if cache_key:
            self.add_context(cache_key=cache_key)
        if operation:
            self.add_context(operation=operation)


# === Exceptions RAG et IA ===

class RAGError(MCPBaseException):
    """Erreur du système RAG"""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.BUSINESS_LOGIC,
            context=context,
            original_error=original_error,
            user_message="Erreur du système d'analyse"
        )
        if operation:
            self.add_context(operation=operation)


class EmbeddingError(RAGError):
    """Erreur de génération d'embeddings"""
    
    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        text_length: Optional[int] = None,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message,
            operation="embedding_generation",
            context=context,
            original_error=original_error
        )
        if model:
            self.add_context(model=model)
        if text_length:
            self.add_context(text_length=text_length)


# === Exceptions Lightning Network ===

class LightningError(MCPBaseException):
    """Erreur Lightning Network"""
    
    def __init__(
        self,
        message: str,
        node_id: Optional[str] = None,
        operation: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.EXTERNAL_API,
            context=context,
            original_error=original_error,
            user_message="Erreur du réseau Lightning"
        )
        if node_id:
            self.add_context(node_id=node_id)
        if operation:
            self.add_context(operation=operation)


class ChannelError(LightningError):
    """Erreur de canal Lightning"""
    
    def __init__(
        self,
        message: str,
        channel_id: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message,
            operation="channel_management",
            context=context,
            original_error=original_error
        )
        if channel_id:
            self.add_context(channel_id=channel_id)


class PaymentError(LightningError):
    """Erreur de paiement Lightning"""
    
    def __init__(
        self,
        message: str,
        payment_hash: Optional[str] = None,
        amount_msat: Optional[int] = None,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message,
            operation="payment",
            context=context,
            original_error=original_error
        )
        if payment_hash:
            self.add_context(payment_hash=payment_hash)
        if amount_msat:
            self.add_context(amount_msat=amount_msat)


# === Gestionnaire Global d'Exceptions ===

class ExceptionHandler:
    """Gestionnaire global d'exceptions avec reporting et métriques"""
    
    def __init__(self):
        self.error_counts = {}
        self.error_history = []
        self.max_history = 1000
    
    def handle_exception(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        reraise: bool = True
    ) -> MCPBaseException:
        """Gère une exception et la convertit en exception MCP si nécessaire"""
        
        # Si c'est déjà une exception MCP, on l'enrichit
        if isinstance(error, MCPBaseException):
            if context:
                error.context.additional_data.update(context.to_dict())
            mcp_error = error
        else:
            # Convertit l'exception en exception MCP
            mcp_error = self._convert_to_mcp_exception(error, context)
        
        # Enregistre l'erreur
        self._record_error(mcp_error)
        
        if reraise:
            raise mcp_error
        
        return mcp_error
    
    def _convert_to_mcp_exception(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None
    ) -> MCPBaseException:
        """Convertit une exception standard en exception MCP"""
        
        error_type = type(error).__name__
        error_message = str(error)
        
        # Détection automatique du type d'erreur
        if isinstance(error, ValueError):
            return ValidationError(
                f"Erreur de validation: {error_message}",
                context=context,
                original_error=error
            )
        elif isinstance(error, PermissionError):
            return AuthorizationError(
                f"Accès refusé: {error_message}",
                context=context
            )
        elif isinstance(error, ConnectionError):
            return NetworkError(
                f"Erreur de connexion: {error_message}",
                context=context,
                original_error=error
            )
        elif isinstance(error, TimeoutError):
            return TimeoutError(
                f"Timeout: {error_message}",
                context=context
            )
        else:
            # Exception générique
            return MCPBaseException(
                f"Erreur inattendue ({error_type}): {error_message}",
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.UNKNOWN,
                context=context,
                original_error=error
            )
    
    def _record_error(self, error: MCPBaseException):
        """Enregistre l'erreur pour les statistiques"""
        error_key = f"{error.__class__.__name__}:{error.category.value}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Ajoute à l'historique
        self.error_history.append({
            "timestamp": error.context.timestamp.isoformat(),
            "error_id": error.error_id,
            "type": error.__class__.__name__,
            "category": error.category.value,
            "severity": error.severity.value,
            "message": error.message
        })
        
        # Limite la taille de l'historique
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'erreurs"""
        total_errors = sum(self.error_counts.values())
        
        return {
            "total_errors": total_errors,
            "error_counts": self.error_counts,
            "recent_errors": self.error_history[-10:],  # 10 dernières erreurs
            "top_errors": sorted(
                self.error_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]  # Top 5 des erreurs
        }
    
    def clear_stats(self):
        """Remet à zéro les statistiques"""
        self.error_counts.clear()
        self.error_history.clear()


# Instance globale du gestionnaire d'exceptions
exception_handler = ExceptionHandler()

# Fonctions utilitaires
def handle_exception(
    error: Exception,
    context: Optional[ErrorContext] = None,
    reraise: bool = True
) -> MCPBaseException:
    """Fonction utilitaire pour gérer les exceptions"""
    return exception_handler.handle_exception(error, context, reraise)


def create_error_context(
    operation: str = None,
    component: str = None,
    **kwargs
) -> ErrorContext:
    """Crée un contexte d'erreur enrichi"""
    return ErrorContext(
        operation=operation,
        component=component,
        additional_data=kwargs
    )

class LNBitsClientError(Exception):
    """Exception spécifique pour les erreurs LNbits"""
    pass

class AmbossAPIError(Exception):
    """Exception spécifique pour les erreurs de l'API Amboss"""
    pass 