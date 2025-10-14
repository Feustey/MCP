"""
Macaroon Manager - Gestion des macaroons LNBits/LND

Gère la génération, stockage, rotation et révocation des macaroons
pour l'authentification avec LNBits et LND.

Auteur: MCP Team
Date: 13 octobre 2025
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import json

import structlog
from pymongo.collection import Collection

from src.auth.encryption import get_encryption_manager

logger = structlog.get_logger(__name__)


@dataclass
class Macaroon:
    """Représente un macaroon avec ses métadonnées."""
    id: str
    name: str
    service: str  # lnbits, lnd, etc.
    macaroon: str  # Macaroon chiffré
    permissions: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour stockage."""
        data = asdict(self)
        # Convertir datetimes en ISO strings
        for key in ['created_at', 'expires_at', 'revoked_at', 'last_used']:
            if data[key]:
                data[key] = data[key].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Macaroon':
        """Crée depuis un dictionnaire."""
        # Convertir ISO strings en datetimes
        for key in ['created_at', 'expires_at', 'revoked_at', 'last_used']:
            if data.get(key):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**data)
    
    def is_valid(self) -> bool:
        """Vérifie si le macaroon est valide."""
        if self.revoked:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True


class MacaroonManager:
    """
    Gère le cycle de vie des macaroons.
    
    Fonctionnalités:
    - Stockage sécurisé (chiffrement)
    - Rotation automatique
    - Révocation
    - Audit des usages
    """
    
    def __init__(self, 
                 mongodb_collection: Optional[Collection] = None,
                 rotation_days: int = 30):
        """
        Initialise le gestionnaire de macaroons.
        
        Args:
            mongodb_collection: Collection MongoDB pour stockage
            rotation_days: Jours avant rotation automatique
        """
        self.collection = mongodb_collection
        self.rotation_days = rotation_days
        self.encryption_manager = get_encryption_manager()
        
        # Cache en mémoire pour performance
        self._cache: Dict[str, Macaroon] = {}
        
        logger.info("macaroon_manager_initialized",
                   rotation_days=rotation_days)
    
    def store_macaroon(self,
                      name: str,
                      service: str,
                      macaroon: str,
                      permissions: List[str],
                      expires_days: Optional[int] = None) -> Macaroon:
        """
        Stocke un nouveau macaroon de manière sécurisée.
        
        Args:
            name: Nom du macaroon (ex: "lnbits_admin", "lnd_readonly")
            service: Service associé (lnbits, lnd)
            macaroon: Macaroon en clair
            permissions: Liste des permissions
            expires_days: Jours avant expiration (None = jamais)
            
        Returns:
            Objet Macaroon créé
        """
        # Chiffrer le macaroon
        encrypted_macaroon = self.encryption_manager.encrypt(
            macaroon, 
            associated_data=f"{service}:{name}"
        )
        
        # Créer l'objet
        macaroon_obj = Macaroon(
            id=f"{service}_{name}_{datetime.utcnow().timestamp()}",
            name=name,
            service=service,
            macaroon=encrypted_macaroon,
            permissions=permissions,
            created_at=datetime.utcnow(),
            expires_at=(datetime.utcnow() + timedelta(days=expires_days) 
                       if expires_days else None)
        )
        
        # Stocker en DB
        if self.collection:
            try:
                self.collection.insert_one(macaroon_obj.to_dict())
                logger.info("macaroon_stored",
                           id=macaroon_obj.id,
                           name=name,
                           service=service)
            except Exception as e:
                logger.error("macaroon_storage_failed",
                            name=name,
                            error=str(e))
                raise
        
        # Mettre en cache
        self._cache[macaroon_obj.id] = macaroon_obj
        
        return macaroon_obj
    
    def get_macaroon(self, macaroon_id: str) -> Optional[Macaroon]:
        """
        Récupère un macaroon par son ID.
        
        Args:
            macaroon_id: ID du macaroon
            
        Returns:
            Objet Macaroon ou None
        """
        # Check cache
        if macaroon_id in self._cache:
            return self._cache[macaroon_id]
        
        # Chercher en DB
        if self.collection:
            try:
                data = self.collection.find_one({"id": macaroon_id})
                if data:
                    macaroon = Macaroon.from_dict(data)
                    self._cache[macaroon_id] = macaroon
                    return macaroon
            except Exception as e:
                logger.error("macaroon_retrieval_failed",
                            id=macaroon_id,
                            error=str(e))
        
        return None
    
    def get_macaroon_by_name(self, name: str, 
                            service: str) -> Optional[Macaroon]:
        """
        Récupère le macaroon actif pour un service/nom.
        
        Args:
            name: Nom du macaroon
            service: Service
            
        Returns:
            Macaroon actif ou None
        """
        if self.collection:
            try:
                # Chercher macaroon non-révoqué le plus récent
                data = self.collection.find_one(
                    {
                        "name": name,
                        "service": service,
                        "revoked": False
                    },
                    sort=[("created_at", -1)]
                )
                
                if data:
                    macaroon = Macaroon.from_dict(data)
                    
                    # Vérifier validité
                    if not macaroon.is_valid():
                        logger.warning("macaroon_expired",
                                      name=name,
                                      service=service)
                        return None
                    
                    self._cache[macaroon.id] = macaroon
                    return macaroon
                    
            except Exception as e:
                logger.error("macaroon_lookup_failed",
                            name=name,
                            service=service,
                            error=str(e))
        
        return None
    
    def decrypt_macaroon(self, macaroon_obj: Macaroon) -> str:
        """
        Déchiffre un macaroon pour utilisation.
        
        Args:
            macaroon_obj: Objet Macaroon
            
        Returns:
            Macaroon en clair
        """
        if not macaroon_obj.is_valid():
            raise ValueError(f"Macaroon {macaroon_obj.id} is not valid")
        
        try:
            plaintext = self.encryption_manager.decrypt(
                macaroon_obj.macaroon,
                associated_data=f"{macaroon_obj.service}:{macaroon_obj.name}"
            )
            
            # Incrémenter compteur usage
            self._update_usage(macaroon_obj.id)
            
            return plaintext
            
        except Exception as e:
            logger.error("macaroon_decryption_failed",
                        id=macaroon_obj.id,
                        error=str(e))
            raise
    
    def _update_usage(self, macaroon_id: str):
        """Met à jour les statistiques d'usage."""
        if self.collection:
            try:
                self.collection.update_one(
                    {"id": macaroon_id},
                    {
                        "$set": {"last_used": datetime.utcnow()},
                        "$inc": {"usage_count": 1}
                    }
                )
            except Exception as e:
                logger.error("usage_update_failed",
                            id=macaroon_id,
                            error=str(e))
    
    def revoke_macaroon(self, macaroon_id: str, 
                       reason: str = "manual") -> bool:
        """
        Révoque un macaroon.
        
        Args:
            macaroon_id: ID du macaroon
            reason: Raison de la révocation
            
        Returns:
            True si succès
        """
        if self.collection:
            try:
                result = self.collection.update_one(
                    {"id": macaroon_id},
                    {
                        "$set": {
                            "revoked": True,
                            "revoked_at": datetime.utcnow(),
                            "revoke_reason": reason
                        }
                    }
                )
                
                # Invalider cache
                if macaroon_id in self._cache:
                    del self._cache[macaroon_id]
                
                logger.info("macaroon_revoked",
                           id=macaroon_id,
                           reason=reason)
                
                return result.modified_count > 0
                
            except Exception as e:
                logger.error("macaroon_revocation_failed",
                            id=macaroon_id,
                            error=str(e))
                return False
        
        return False
    
    def rotate_macaroon(self, name: str, service: str, 
                       new_macaroon: str) -> Optional[Macaroon]:
        """
        Rotate un macaroon (révoque l'ancien, crée le nouveau).
        
        Args:
            name: Nom du macaroon
            service: Service
            new_macaroon: Nouveau macaroon en clair
            
        Returns:
            Nouveau Macaroon créé
        """
        # Récupérer l'ancien
        old_macaroon = self.get_macaroon_by_name(name, service)
        
        if old_macaroon:
            # Révoquer l'ancien
            self.revoke_macaroon(old_macaroon.id, reason="rotation")
            permissions = old_macaroon.permissions
        else:
            permissions = []
        
        # Créer le nouveau
        new_macaroon_obj = self.store_macaroon(
            name=name,
            service=service,
            macaroon=new_macaroon,
            permissions=permissions,
            expires_days=self.rotation_days
        )
        
        logger.info("macaroon_rotated",
                   name=name,
                   service=service,
                   old_id=old_macaroon.id if old_macaroon else None,
                   new_id=new_macaroon_obj.id)
        
        return new_macaroon_obj
    
    def check_rotation_needed(self, name: str, service: str) -> bool:
        """
        Vérifie si un macaroon doit être rotaté.
        
        Args:
            name: Nom du macaroon
            service: Service
            
        Returns:
            True si rotation recommandée
        """
        macaroon = self.get_macaroon_by_name(name, service)
        
        if not macaroon:
            return False
        
        # Check âge
        age = datetime.utcnow() - macaroon.created_at
        if age > timedelta(days=self.rotation_days):
            logger.warning("macaroon_rotation_needed",
                          name=name,
                          service=service,
                          age_days=age.days)
            return True
        
        return False
    
    def list_macaroons(self, service: Optional[str] = None) -> List[Macaroon]:
        """
        Liste tous les macaroons (actifs uniquement).
        
        Args:
            service: Filtrer par service (optionnel)
            
        Returns:
            Liste de Macaroons
        """
        if not self.collection:
            return []
        
        try:
            query = {"revoked": False}
            if service:
                query["service"] = service
            
            macaroons = []
            for data in self.collection.find(query).sort("created_at", -1):
                macaroon = Macaroon.from_dict(data)
                if macaroon.is_valid():
                    macaroons.append(macaroon)
            
            return macaroons
            
        except Exception as e:
            logger.error("macaroon_listing_failed",
                        service=service,
                        error=str(e))
            return []
    
    def get_audit_log(self, macaroon_id: str) -> Dict:
        """
        Récupère l'audit log d'un macaroon.
        
        Args:
            macaroon_id: ID du macaroon
            
        Returns:
            Statistiques d'usage
        """
        macaroon = self.get_macaroon(macaroon_id)
        
        if not macaroon:
            return {}
        
        return {
            "id": macaroon.id,
            "name": macaroon.name,
            "service": macaroon.service,
            "created_at": macaroon.created_at.isoformat(),
            "expires_at": macaroon.expires_at.isoformat() if macaroon.expires_at else None,
            "last_used": macaroon.last_used.isoformat() if macaroon.last_used else None,
            "usage_count": macaroon.usage_count,
            "revoked": macaroon.revoked,
            "is_valid": macaroon.is_valid(),
            "permissions": macaroon.permissions
        }


# Instance globale
_macaroon_manager: Optional[MacaroonManager] = None


def get_macaroon_manager() -> MacaroonManager:
    """
    Retourne l'instance globale du gestionnaire de macaroons.
    
    Returns:
        MacaroonManager instance
    """
    global _macaroon_manager
    if _macaroon_manager is None:
        _macaroon_manager = MacaroonManager()
    return _macaroon_manager


def init_macaroon_manager(mongodb_collection: Optional[Collection] = None,
                         rotation_days: int = 30) -> MacaroonManager:
    """
    Initialise le gestionnaire de macaroons global.
    
    Args:
        mongodb_collection: Collection MongoDB pour stockage
        rotation_days: Jours avant rotation automatique
        
    Returns:
        MacaroonManager instance
    """
    global _macaroon_manager
    _macaroon_manager = MacaroonManager(mongodb_collection, rotation_days)
    return _macaroon_manager
