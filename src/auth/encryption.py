"""
Encryption Utilities - Chiffrement pour credentials sensibles

Gère le chiffrement/déchiffrement des credentials (macaroons, API keys)
avec AES-256-GCM.

Auteur: MCP Team
Date: 13 octobre 2025
"""

import base64
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import structlog

logger = structlog.get_logger(__name__)


class EncryptionManager:
    """
    Gère le chiffrement/déchiffrement de données sensibles.
    
    Utilise AES-256-GCM pour chiffrement authentifié.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialise le gestionnaire de chiffrement.
        
        Args:
            encryption_key: Clé de chiffrement (32 bytes base64).
                          Si None, utilise ENCRYPTION_KEY de l'environnement.
        """
        if encryption_key is None:
            encryption_key = os.environ.get("ENCRYPTION_KEY")
            
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY must be provided or set in environment")
        
        # Decode la clé (devrait être 32 bytes en base64)
        try:
            self.key = base64.b64decode(encryption_key)
            if len(self.key) != 32:
                raise ValueError("Encryption key must be 32 bytes")
        except Exception as e:
            raise ValueError(f"Invalid encryption key format: {e}")
        
        self.aesgcm = AESGCM(self.key)
        logger.info("encryption_manager_initialized")
    
    def encrypt(self, plaintext: str, associated_data: Optional[str] = None) -> str:
        """
        Chiffre un texte avec AES-256-GCM.
        
        Args:
            plaintext: Texte à chiffrer
            associated_data: Données associées (optionnel, pour authentification)
            
        Returns:
            Texte chiffré en base64 (format: nonce||ciphertext)
        """
        try:
            # Générer un nonce aléatoire (12 bytes pour GCM)
            nonce = os.urandom(12)
            
            # Préparer les données
            plaintext_bytes = plaintext.encode('utf-8')
            aad = associated_data.encode('utf-8') if associated_data else None
            
            # Chiffrer
            ciphertext = self.aesgcm.encrypt(nonce, plaintext_bytes, aad)
            
            # Combiner nonce + ciphertext et encoder en base64
            encrypted = nonce + ciphertext
            encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')
            
            logger.debug("data_encrypted", 
                        plaintext_length=len(plaintext),
                        encrypted_length=len(encrypted_b64))
            
            return encrypted_b64
            
        except Exception as e:
            logger.error("encryption_failed", error=str(e))
            raise
    
    def decrypt(self, ciphertext_b64: str, 
                associated_data: Optional[str] = None) -> str:
        """
        Déchiffre un texte chiffré avec AES-256-GCM.
        
        Args:
            ciphertext_b64: Texte chiffré en base64
            associated_data: Données associées (doivent matcher l'encryption)
            
        Returns:
            Texte en clair
        """
        try:
            # Decoder le base64
            encrypted = base64.b64decode(ciphertext_b64)
            
            # Séparer nonce (12 bytes) et ciphertext
            nonce = encrypted[:12]
            ciphertext = encrypted[12:]
            
            # Préparer les données associées
            aad = associated_data.encode('utf-8') if associated_data else None
            
            # Déchiffrer
            plaintext_bytes = self.aesgcm.decrypt(nonce, ciphertext, aad)
            plaintext = plaintext_bytes.decode('utf-8')
            
            logger.debug("data_decrypted",
                        ciphertext_length=len(ciphertext_b64),
                        plaintext_length=len(plaintext))
            
            return plaintext
            
        except Exception as e:
            logger.error("decryption_failed", error=str(e))
            raise
    
    @staticmethod
    def generate_key() -> str:
        """
        Génère une nouvelle clé de chiffrement aléatoire.
        
        Returns:
            Clé de 32 bytes encodée en base64
        """
        key = os.urandom(32)
        key_b64 = base64.b64encode(key).decode('utf-8')
        logger.info("encryption_key_generated")
        return key_b64
    
    @staticmethod
    def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> str:
        """
        Dérive une clé de chiffrement depuis un mot de passe.
        
        Args:
            password: Mot de passe
            salt: Salt pour la dérivation (32 bytes). Si None, génère aléatoirement.
            
        Returns:
            Clé dérivée en base64
        """
        if salt is None:
            salt = os.urandom(32)
        
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP recommended
        )
        
        key = kdf.derive(password.encode('utf-8'))
        key_b64 = base64.b64encode(key).decode('utf-8')
        
        logger.info("key_derived_from_password")
        return key_b64


# Instance globale
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager() -> EncryptionManager:
    """
    Retourne l'instance globale du gestionnaire de chiffrement.
    
    Returns:
        EncryptionManager instance
    """
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


def init_encryption_manager(encryption_key: Optional[str] = None) -> EncryptionManager:
    """
    Initialise le gestionnaire de chiffrement global.
    
    Args:
        encryption_key: Clé de chiffrement (32 bytes base64)
        
    Returns:
        EncryptionManager instance
    """
    global _encryption_manager
    _encryption_manager = EncryptionManager(encryption_key)
    return _encryption_manager


def encrypt_credential(credential: str, 
                       credential_type: str = "api_key") -> str:
    """
    Fonction helper pour chiffrer un credential.
    
    Args:
        credential: Credential à chiffrer
        credential_type: Type de credential (pour associated data)
        
    Returns:
        Credential chiffré en base64
    """
    manager = get_encryption_manager()
    return manager.encrypt(credential, associated_data=credential_type)


def decrypt_credential(encrypted_credential: str,
                       credential_type: str = "api_key") -> str:
    """
    Fonction helper pour déchiffrer un credential.
    
    Args:
        encrypted_credential: Credential chiffré en base64
        credential_type: Type de credential (pour associated data)
        
    Returns:
        Credential en clair
    """
    manager = get_encryption_manager()
    return manager.decrypt(encrypted_credential, associated_data=credential_type)
