"""
Validateurs de modèles
Définition des validateurs personnalisés pour les modèles Pydantic

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 27 mai 2025
"""

import re
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import validator, root_validator

# Patterns de validation
EMAIL_PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
USERNAME_PATTERN = r"^[a-zA-Z0-9_-]{3,32}$"
PASSWORD_PATTERN = r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{8,}$"
NODE_ID_PATTERN = r"^[a-zA-Z0-9_-]{3,64}$"
PUBKEY_PATTERN = r"^[0-9a-fA-F]{66}$"
CRON_PATTERN = r"^(\*|[0-9]{1,2}|\*\/[0-9]{1,2}) (\*|[0-9]{1,2}|\*\/[0-9]{1,2}) (\*|[0-9]{1,2}|\*\/[0-9]{1,2}) (\*|[0-9]{1,2}|\*\/[0-9]{1,2}) (\*|[0-7]|\*\/[0-7])$"

class Validators:
    """Classe de validateurs personnalisés"""
    
    @staticmethod
    def validate_email(email: str) -> str:
        """Valide le format d'un email"""
        if not re.match(EMAIL_PATTERN, email):
            raise ValueError("Format d'email invalide")
        return email.lower()
    
    @staticmethod
    def validate_username(username: str) -> str:
        """Valide le format d'un nom d'utilisateur"""
        if not re.match(USERNAME_PATTERN, username):
            raise ValueError("Format de nom d'utilisateur invalide")
        return username.lower()
    
    @staticmethod
    def validate_password(password: str) -> str:
        """Valide le format d'un mot de passe"""
        if not re.match(PASSWORD_PATTERN, password):
            raise ValueError("Format de mot de passe invalide")
        return password
    
    @staticmethod
    def validate_node_id(node_id: str) -> str:
        """Valide le format d'un identifiant de nœud"""
        if not re.match(NODE_ID_PATTERN, node_id):
            raise ValueError("Format d'identifiant de nœud invalide")
        return node_id
    
    @staticmethod
    def validate_pubkey(pubkey: str) -> str:
        """Valide le format d'une clé publique"""
        if not re.match(PUBKEY_PATTERN, pubkey):
            raise ValueError("Format de clé publique invalide")
        return pubkey
    
    @staticmethod
    def validate_cron(schedule: str) -> str:
        """Valide le format d'un planning cron"""
        if not re.match(CRON_PATTERN, schedule):
            raise ValueError("Format de planning cron invalide")
        return schedule
    
    @staticmethod
    def validate_capacity(capacity: int) -> int:
        """Valide la capacité d'un nœud"""
        if capacity < 0:
            raise ValueError("La capacité doit être positive")
        return capacity
    
    @staticmethod
    def validate_channels(channels: int) -> int:
        """Valide le nombre de canaux"""
        if channels < 0:
            raise ValueError("Le nombre de canaux doit être positif")
        return channels
    
    @staticmethod
    def validate_score(score: float) -> float:
        """Valide le score d'optimisation"""
        if not 0 <= score <= 1:
            raise ValueError("Le score doit être entre 0 et 1")
        return score
    
    @staticmethod
    def validate_status(status: str, valid_statuses: List[str]) -> str:
        """Valide le statut"""
        if status not in valid_statuses:
            raise ValueError(f"Statut invalide. Doit être l'un de {valid_statuses}")
        return status
    
    @staticmethod
    def validate_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Valide les métadonnées"""
        if not isinstance(metadata, dict):
            raise ValueError("Les métadonnées doivent être un dictionnaire")
        return metadata
    
    @staticmethod
    def validate_parameters(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Valide les paramètres"""
        if not isinstance(parameters, dict):
            raise ValueError("Les paramètres doivent être un dictionnaire")
        return parameters
    
    @staticmethod
    def validate_results(results: Dict[str, Any]) -> Dict[str, Any]:
        """Valide les résultats"""
        if not isinstance(results, dict):
            raise ValueError("Les résultats doivent être un dictionnaire")
        return results
    
    @staticmethod
    def validate_permissions(permissions: List[str]) -> List[str]:
        """Valide les permissions"""
        if not isinstance(permissions, list):
            raise ValueError("Les permissions doivent être une liste")
        return permissions
    
    @staticmethod
    def validate_file_size(size: int) -> int:
        """Valide la taille d'un fichier"""
        if size < 0:
            raise ValueError("La taille du fichier doit être positive")
        return size
    
    @staticmethod
    def validate_mime_type(mime_type: str) -> str:
        """Valide le type MIME"""
        if not mime_type or not "/" in mime_type:
            raise ValueError("Type MIME invalide")
        return mime_type
    
    @staticmethod
    def validate_date_range(start_date: datetime, end_date: datetime) -> None:
        """Valide une plage de dates"""
        if start_date > end_date:
            raise ValueError("La date de début doit être antérieure à la date de fin")
    
    @staticmethod
    def validate_pagination(page: int, size: int) -> None:
        """Valide les paramètres de pagination"""
        if page < 1:
            raise ValueError("Le numéro de page doit être positif")
        if size < 1 or size > 100:
            raise ValueError("La taille de page doit être entre 1 et 100")
    
    @staticmethod
    def validate_sort_params(sort_by: Optional[str], sort_order: Optional[str]) -> None:
        """Valide les paramètres de tri"""
        if sort_order and sort_order not in ["asc", "desc"]:
            raise ValueError("L'ordre de tri doit être 'asc' ou 'desc'") 