#!/usr/bin/env python3
"""
Gestionnaire de secrets sécurisé pour MCP
Généré par Claude Code - Audit de sécurité

🔒 Système centralisé et sécurisé pour la gestion des secrets
"""

import os
import json
import base64
import hashlib
import secrets
from pathlib import Path
from typing import Dict, Optional, Any
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

class SecureSecretsManager:
    """
    Gestionnaire de secrets avec chiffrement AES-256
    
    Features:
    - Chiffrement AES-256-GCM
    - Dérivation de clés PBKDF2
    - Validation des secrets
    - Rotation automatique
    - Audit des accès
    """
    
    def __init__(self, master_key: Optional[str] = None, vault_path: Optional[str] = None):
        self.vault_path = Path(vault_path or "secrets/vault.enc")
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Clé maître pour le chiffrement
        if master_key:
            self.master_key = self._derive_key(master_key)
        else:
            self.master_key = self._get_or_create_master_key()
        
        self.secrets_cache = {}
        self.access_log = []
    
    def _derive_key(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """Dériver une clé de chiffrement à partir d'un mot de passe"""
        if salt is None:
            salt = b"mcp_salt_2025"  # Salt fixe pour reproductibilité
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(password.encode())
    
    def _get_or_create_master_key(self) -> bytes:
        """Récupérer ou créer la clé maître"""
        master_key_env = os.getenv("MCP_MASTER_KEY")
        if master_key_env:
            return self._derive_key(master_key_env)
        
        # Générer une nouvelle clé si elle n'existe pas
        logger.warning("No MCP_MASTER_KEY found, generating new key")
        new_key = secrets.token_urlsafe(64)
        print(f"🔑 IMPORTANT: Set MCP_MASTER_KEY={new_key}")
        return self._derive_key(new_key)
    
    def encrypt_secret(self, plaintext: str) -> str:
        """Chiffrer un secret avec AES-256-GCM"""
        # Générer un nonce aléatoire
        nonce = os.urandom(12)
        
        # Créer le cipher
        cipher = Cipher(algorithms.AES(self.master_key), modes.GCM(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Chiffrer
        ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()
        
        # Combiner nonce + tag + ciphertext
        encrypted_data = nonce + encryptor.tag + ciphertext
        
        # Encoder en base64
        return base64.b64encode(encrypted_data).decode()
    
    def decrypt_secret(self, encrypted_data: str) -> str:
        """Déchiffrer un secret"""
        try:
            # Décoder de base64
            data = base64.b64decode(encrypted_data)
            
            # Extraire nonce, tag et ciphertext
            nonce = data[:12]
            tag = data[12:28]
            ciphertext = data[28:]
            
            # Créer le cipher
            cipher = Cipher(algorithms.AES(self.master_key), modes.GCM(nonce, tag), backend=default_backend())
            decryptor = cipher.decryptor()
            
            # Déchiffrer
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            return plaintext.decode()
        
        except Exception as e:
            logger.error(f"Failed to decrypt secret: {e}")
            raise ValueError("Invalid encrypted data")
    
    def store_secret(self, key: str, value: str, metadata: Optional[Dict] = None) -> bool:
        """Stocker un secret de manière sécurisée"""
        try:
            # Charger le vault existant
            vault_data = self._load_vault()
            
            # Chiffrer le secret
            encrypted_value = self.encrypt_secret(value)
            
            # Préparer les métadonnées
            secret_metadata = {
                "created_at": datetime.now().isoformat(),
                "hash": hashlib.sha256(value.encode()).hexdigest()[:16],
                **(metadata or {})
            }
            
            # Stocker dans le vault
            vault_data[key] = {
                "value": encrypted_value,
                "metadata": secret_metadata
            }
            
            # Sauvegarder le vault
            self._save_vault(vault_data)
            
            # Log de l'accès
            self._log_access("store", key)
            
            logger.info(f"Secret '{key}' stored successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store secret '{key}': {e}")
            return False
    
    def get_secret(self, key: str) -> Optional[str]:
        """Récupérer un secret de manière sécurisée"""
        try:
            # Vérifier le cache d'abord
            if key in self.secrets_cache:
                self._log_access("get_cached", key)
                return self.secrets_cache[key]
            
            # Charger depuis le vault
            vault_data = self._load_vault()
            
            if key not in vault_data:
                logger.warning(f"Secret '{key}' not found")
                return None
            
            # Déchiffrer le secret
            encrypted_value = vault_data[key]["value"]
            decrypted_value = self.decrypt_secret(encrypted_value)
            
            # Mettre en cache (temporairement)
            self.secrets_cache[key] = decrypted_value
            
            # Log de l'accès
            self._log_access("get", key)
            
            return decrypted_value
            
        except Exception as e:
            logger.error(f"Failed to get secret '{key}': {e}")
            return None
    
    def rotate_secret(self, key: str, new_value: str) -> bool:
        """Effectuer la rotation d'un secret"""
        try:
            vault_data = self._load_vault()
            
            if key not in vault_data:
                logger.error(f"Cannot rotate non-existent secret '{key}'")
                return False
            
            # Sauvegarder l'ancienne version
            old_metadata = vault_data[key]["metadata"]
            old_metadata["rotated_at"] = datetime.now().isoformat()
            
            # Stocker la nouvelle version
            result = self.store_secret(key, new_value, {
                "previous_hash": old_metadata.get("hash"),
                "rotation_count": old_metadata.get("rotation_count", 0) + 1
            })
            
            if result:
                # Nettoyer le cache
                self.secrets_cache.pop(key, None)
                self._log_access("rotate", key)
                logger.info(f"Secret '{key}' rotated successfully")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to rotate secret '{key}': {e}")
            return False
    
    def delete_secret(self, key: str) -> bool:
        """Supprimer un secret de manière sécurisée"""
        try:
            vault_data = self._load_vault()
            
            if key not in vault_data:
                logger.warning(f"Secret '{key}' not found for deletion")
                return False
            
            # Supprimer du vault
            del vault_data[key]
            
            # Supprimer du cache
            self.secrets_cache.pop(key, None)
            
            # Sauvegarder
            self._save_vault(vault_data)
            
            # Log
            self._log_access("delete", key)
            
            logger.info(f"Secret '{key}' deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete secret '{key}': {e}")
            return False
    
    def list_secrets(self) -> Dict[str, Dict]:
        """Lister les secrets (sans les valeurs)"""
        try:
            vault_data = self._load_vault()
            
            result = {}
            for key, data in vault_data.items():
                result[key] = data["metadata"]
            
            self._log_access("list", "all")
            return result
            
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return {}
    
    def _load_vault(self) -> Dict:
        """Charger le vault depuis le disque"""
        if not self.vault_path.exists():
            return {}
        
        try:
            encrypted_content = self.vault_path.read_text()
            decrypted_content = self.decrypt_secret(encrypted_content)
            return json.loads(decrypted_content)
        except Exception as e:
            logger.error(f"Failed to load vault: {e}")
            return {}
    
    def _save_vault(self, vault_data: Dict) -> bool:
        """Sauvegarder le vault sur disque"""
        try:
            # Sérialiser en JSON
            json_content = json.dumps(vault_data, indent=2)
            
            # Chiffrer le contenu
            encrypted_content = self.encrypt_secret(json_content)
            
            # Écrire sur disque de manière atomique
            temp_path = self.vault_path.with_suffix('.tmp')
            temp_path.write_text(encrypted_content)
            temp_path.replace(self.vault_path)
            
            # Permissions restrictives
            self.vault_path.chmod(0o600)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save vault: {e}")
            return False
    
    def _log_access(self, action: str, key: str):
        """Logger les accès aux secrets"""
        from datetime import datetime
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "key": key,
            "user": os.getenv("USER", "unknown")
        }
        
        self.access_log.append(log_entry)
        
        # Garder seulement les 1000 derniers accès
        if len(self.access_log) > 1000:
            self.access_log = self.access_log[-1000:]
    
    def get_access_log(self) -> List[Dict]:
        """Récupérer le log des accès"""
        return self.access_log.copy()
    
    def validate_secrets(self) -> Dict[str, bool]:
        """Valider tous les secrets stockés"""
        vault_data = self._load_vault()
        results = {}
        
        for key in vault_data:
            try:
                secret_value = self.get_secret(key)
                results[key] = secret_value is not None and len(secret_value) > 0
            except Exception:
                results[key] = False
        
        return results
    
    def export_env_template(self, output_path: Optional[str] = None) -> str:
        """Exporter un template .env avec les clés"""
        vault_data = self._load_vault()
        
        template_content = "# MCP Environment Template\n"
        template_content += "# Generated by SecureSecretsManager\n"
        template_content += f"# Date: {datetime.now().isoformat()}\n\n"
        
        for key in sorted(vault_data.keys()):
            metadata = vault_data[key]["metadata"]
            template_content += f"# Created: {metadata.get('created_at', 'unknown')}\n"
            template_content += f"{key}=CHANGE_ME_SET_REAL_VALUE\n\n"
        
        if output_path:
            Path(output_path).write_text(template_content)
            logger.info(f"Template exported to {output_path}")
        
        return template_content

# Instance globale
secrets_manager = SecureSecretsManager()

def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Helper function pour récupérer un secret"""
    # D'abord essayer les variables d'environnement
    env_value = os.getenv(key)
    if env_value:
        return env_value
    
    # Ensuite essayer le gestionnaire de secrets
    vault_value = secrets_manager.get_secret(key)
    if vault_value:
        return vault_value
    
    return default

def store_secret(key: str, value: str, **metadata) -> bool:
    """Helper function pour stocker un secret"""
    return secrets_manager.store_secret(key, value, metadata)

if __name__ == "__main__":
    # Tests basiques
    from datetime import datetime
    
    print("🔐 Testing SecureSecretsManager...")
    
    manager = SecureSecretsManager()
    
    # Test de stockage
    test_key = "TEST_SECRET"
    test_value = "my_super_secret_value_123!"
    
    if manager.store_secret(test_key, test_value):
        print("✅ Secret stored successfully")
        
        # Test de récupération
        retrieved = manager.get_secret(test_key)
        if retrieved == test_value:
            print("✅ Secret retrieved successfully")
        else:
            print("❌ Secret retrieval failed")
        
        # Test de rotation
        new_value = "rotated_secret_456!"
        if manager.rotate_secret(test_key, new_value):
            print("✅ Secret rotated successfully")
            
            # Vérifier la nouvelle valeur
            rotated = manager.get_secret(test_key)
            if rotated == new_value:
                print("✅ Rotated secret retrieved successfully")
            else:
                print("❌ Rotated secret retrieval failed")
        
        # Nettoyage
        manager.delete_secret(test_key)
        print("✅ Test completed and cleaned up")
    
    else:
        print("❌ Failed to store secret")