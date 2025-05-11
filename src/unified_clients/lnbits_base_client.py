import httpx
import logging
from typing import Dict, Any, Optional, Union, List
import time
import asyncio
from enum import Enum
from pydantic import BaseModel, field_validator, ConfigDict

# Configuration du logging
logger = logging.getLogger(__name__)

class LNBitsErrorType(Enum):
    """Types d'erreurs spécifiques à LNBits"""
    NETWORK_ERROR = "Erreur de connexion réseau"
    AUTHENTICATION_ERROR = "Erreur d'authentification"
    RATE_LIMIT_ERROR = "Limite de requêtes dépassée"
    SERVER_ERROR = "Erreur du serveur LNBits"
    REQUEST_ERROR = "Erreur de requête"
    UNKNOWN_ERROR = "Erreur inconnue"

class LNBitsError(Exception):
    """Classe d'erreur standardisée pour LNBits"""
    def __init__(
        self,
        message: str,
        error_type: LNBitsErrorType = LNBitsErrorType.UNKNOWN_ERROR,
        status_code: Optional[int] = None,
        raw_response: Optional[Any] = None
    ):
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.raw_response = raw_response
        super().__init__(self.message)

class RetryConfig(BaseModel):
    """Configuration pour la stratégie de retry"""
    max_attempts: int = 3
    base_delay: float = 1.0  # en secondes
    max_delay: float = 30.0  # en secondes
    backoff_factor: float = 2.0
    
    model_config = ConfigDict(frozen=True)
    
    @field_validator('max_attempts')
    def validate_max_attempts(cls, v):
        if v < 1:
            raise ValueError("Le nombre maximum de tentatives doit être au moins 1")
        return v

class LNBitsBaseClient:
    """Client de base pour interagir avec l'API LNBits"""
    
    def __init__(
        self,
        url: str,
        invoice_key: Optional[str] = None,
        admin_key: Optional[str] = None,
        timeout: float = 30.0,
        retry_config: Optional[RetryConfig] = None
    ):
        self.url = url.rstrip('/')
        self.invoice_key = invoice_key
        self.admin_key = admin_key
        self.timeout = timeout
        self.retry_config = retry_config or RetryConfig()
        self.client = httpx.AsyncClient(timeout=self.timeout)
        
        # Vérification des paramètres
        if not url:
            raise ValueError("L'URL de l'API LNBits est obligatoire")
            
        logger.info(f"Client LNBits initialisé avec l'URL: {self.url}")

    def _get_headers(self, use_admin_key: bool = False) -> Dict[str, str]:
        """Crée les en-têtes HTTP avec l'authentification appropriée"""
        headers = {"Content-Type": "application/json"}
        
        if use_admin_key:
            if not self.admin_key:
                raise LNBitsError(
                    "Clé admin non fournie mais requise pour cette opération",
                    error_type=LNBitsErrorType.AUTHENTICATION_ERROR
                )
            headers["X-Api-Key"] = self.admin_key
        else:
            if not self.invoice_key:
                raise LNBitsError(
                    "Clé invoice non fournie mais requise pour cette opération",
                    error_type=LNBitsErrorType.AUTHENTICATION_ERROR
                )
            headers["X-Api-Key"] = self.invoice_key
            
        return headers

    async def _execute_with_retry(
        self,
        method: str,
        endpoint: str,
        use_admin_key: bool = False,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Exécute une requête HTTP avec mécanisme de retry"""
        
        url = f"{self.url}/{endpoint}"
        headers = self._get_headers(use_admin_key)
        
        attempt = 0
        last_error = None
        
        while attempt < self.retry_config.max_attempts:
            try:
                attempt += 1
                logger.debug(f"Tentative {attempt}/{self.retry_config.max_attempts} pour {method} {url}")
                
                if method.lower() == "get":
                    response = await self.client.get(url, headers=headers, params=params)
                elif method.lower() == "post":
                    response = await self.client.post(url, headers=headers, json=json_data)
                elif method.lower() == "put":
                    response = await self.client.put(url, headers=headers, json=json_data)
                elif method.lower() == "delete":
                    response = await self.client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Méthode HTTP non supportée: {method}")
                
                # Vérification du code de statut
                if response.status_code >= 400:
                    error_type = self._determine_error_type(response)
                    error_msg = f"Erreur {response.status_code} lors de l'appel à {endpoint}"
                    
                    # Si c'est une erreur que l'on peut retenter (serveur ou rate limit)
                    if error_type in [LNBitsErrorType.SERVER_ERROR, LNBitsErrorType.RATE_LIMIT_ERROR]:
                        last_error = LNBitsError(
                            error_msg,
                            error_type=error_type,
                            status_code=response.status_code,
                            raw_response=response.text
                        )
                        await self._handle_retry_delay(attempt)
                        continue  # Passer à la prochaine tentative
                    
                    # Pour les autres erreurs, on lève immédiatement l'exception
                    raise LNBitsError(
                        error_msg,
                        error_type=error_type,
                        status_code=response.status_code,
                        raw_response=response.text
                    )
                
                # En cas de succès, on retourne les données
                try:
                    return response.json()
                except ValueError:
                    return {"success": True, "raw_response": response.text}
                
            except httpx.HTTPError as e:
                last_error = LNBitsError(
                    f"Erreur de connexion: {str(e)}",
                    error_type=LNBitsErrorType.NETWORK_ERROR
                )
                await self._handle_retry_delay(attempt)
        
        # Si on arrive ici, c'est qu'on a épuisé toutes les tentatives
        if last_error:
            raise last_error
        
        # Cas improbable, mais pour être complet
        raise LNBitsError("Échec de toutes les tentatives", error_type=LNBitsErrorType.UNKNOWN_ERROR)

    async def _handle_retry_delay(self, attempt: int):
        """Calcule et attend le délai avant la prochaine tentative"""
        if attempt < self.retry_config.max_attempts:
            delay = min(
                self.retry_config.base_delay * (self.retry_config.backoff_factor ** (attempt - 1)),
                self.retry_config.max_delay
            )
            logger.warning(f"Attente de {delay:.2f}s avant la prochaine tentative")
            await asyncio.sleep(delay)

    def _determine_error_type(self, response) -> LNBitsErrorType:
        """Détermine le type d'erreur en fonction du code de statut"""
        status_code = response.status_code
        
        if status_code == 401 or status_code == 403:
            return LNBitsErrorType.AUTHENTICATION_ERROR
        elif status_code == 429:
            return LNBitsErrorType.RATE_LIMIT_ERROR
        elif status_code >= 500:
            return LNBitsErrorType.SERVER_ERROR
        elif status_code >= 400:
            return LNBitsErrorType.REQUEST_ERROR
        
        return LNBitsErrorType.UNKNOWN_ERROR

    async def check_connection(self) -> bool:
        """Vérifie la connexion à l'API LNBits"""
        try:
            # Utilise un endpoint qui ne nécessite pas d'authentification
            # ou un endpoint de santé s'il existe
            url = f"{self.url}/health"
            response = await self.client.get(url)
            return response.status_code < 400
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de connexion: {e}")
            return False

    async def close(self):
        """Ferme proprement le client HTTP"""
        if self.client:
            await self.client.aclose()
            
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close() 