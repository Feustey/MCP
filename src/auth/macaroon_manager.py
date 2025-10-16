#!/usr/bin/env python3
"""
Macaroon Manager - Gestion sécurisée des macaroons LND/LNBits

Ce module gère :
- Génération de macaroons
- Stockage chiffré (AES-256-GCM)
- Rotation automatique
- Révocation
- Audit logging

Dernière mise à jour: 15 octobre 2025
"""

import os
import base64
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuration
MACAROON_DIR = Path("data/macaroons")
MACAROON_DIR.mkdir(exist_ok=True, parents=True)

ROTATION_DAYS = int(os.getenv("MACAROON_ROTATION_DAYS", "30"))
KEY_SIZE = 32  # 256 bits pour AES-256


class MacaroonManager:
    """Gestionnaire de macaroons avec stockage chiffré et rotation automatique."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialise le gestionnaire de macaroons.
        
        Args:
            encryption_key: Clé de chiffrement (32 bytes). Si None, utilise MACAROON_ENCRYPTION_KEY de .env
        """
        self.encryption_key = encryption_key or os.getenv("MACAROON_ENCRYPTION_KEY")
        
        if not self.encryption_key:
            logger.warning("Aucune clé de chiffrement fournie. Génération d'une nouvelle clé...")
            self.encryption_key = self._generate_encryption_key()
            logger.info(f"Nouvelle clé générée. Ajoutez-la à votre .env : MACAROON_ENCRYPTION_KEY={self.encryption_key}")
        
        # Dériver une clé de 32 bytes si nécessaire
        if len(self.encryption_key) != KEY_SIZE:
            self.encryption_key = self._derive_key(self.encryption_key.encode())
        else:
            self.encryption_key = self.encryption_key.encode() if isinstance(self.encryption_key, str) else self.encryption_key
        
        self.aesgcm = AESGCM(self.encryption_key)
        self.macaroons_file = MACAROON_DIR / "macaroons.enc.json"
        self.audit_file = MACAROON_DIR / "audit.log"
        
        logger.info("MacaroonManager initialisé")
    
    @staticmethod
    def _generate_encryption_key() -> str:
        """Génère une nouvelle clé de chiffrement aléatoire."""
        key = os.urandom(KEY_SIZE)
        return base64.b64encode(key).decode('utf-8')
    
    @staticmethod
    def _derive_key(password: bytes, salt: Optional[bytes] = None) -> bytes:
        """
        Dérive une clé de 32 bytes à partir d'un mot de passe.
        
        Args:
            password: Mot de passe
            salt: Salt optionnel (généré si non fourni)
        """
        if salt is None:
            salt = b"mcp_macaroon_salt"  # Salt fixe pour cohérence
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password)
    
    def _encrypt(self, data: str) -> str:
        """
        Chiffre des données avec AES-256-GCM.
        
        Args:
            data: Données à chiffrer
            
        Returns:
            Données chiffrées encodées en base64 (nonce + ciphertext)
        """
        nonce = os.urandom(12)  # 96 bits pour GCM
        ciphertext = self.aesgcm.encrypt(nonce, data.encode(), None)
        
        # Combiner nonce + ciphertext
        encrypted = nonce + ciphertext
        return base64.b64encode(encrypted).decode('utf-8')
    
    def _decrypt(self, encrypted_data: str) -> str:
        """
        Déchiffre des données avec AES-256-GCM.
        
        Args:
            encrypted_data: Données chiffrées encodées en base64
            
        Returns:
            Données déchiffrées
        """
        encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        
        # Séparer nonce et ciphertext
        nonce = encrypted_bytes[:12]
        ciphertext = encrypted_bytes[12:]
        
        plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')
    
    def _load_macaroons(self) -> Dict:
        """Charge les macaroons depuis le stockage chiffré."""
        if not self.macaroons_file.exists():
            return {}
        
        try:
            with open(self.macaroons_file, 'r') as f:
                encrypted_data = f.read()
            
            decrypted_json = self._decrypt(encrypted_data)
            return json.loads(decrypted_json)
        except Exception as e:
            logger.error(f"Erreur lors du chargement des macaroons: {e}")
            return {}
    
    def _save_macaroons(self, macaroons: Dict):
        """Sauvegarde les macaroons dans le stockage chiffré."""
        try:
            json_data = json.dumps(macaroons, indent=2)
            encrypted_data = self._encrypt(json_data)
            
            with open(self.macaroons_file, 'w') as f:
                f.write(encrypted_data)
            
            # Permissions restrictives
            os.chmod(self.macaroons_file, 0o600)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des macaroons: {e}")
            raise
    
    def _audit_log(self, action: str, node_id: str, details: Optional[str] = None):
        """Enregistre une action dans le journal d'audit."""
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp} | {action} | Node: {node_id[:8]}... | {details or 'N/A'}\n"
        
        try:
            with open(self.audit_file, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Erreur lors de l'écriture du log d'audit: {e}")
    
    def store_macaroon(
        self, 
        node_id: str, 
        macaroon: str, 
        macaroon_type: str = "admin",
        expiry_days: Optional[int] = None
    ) -> Dict:
        """
        Stocke un macaroon de manière sécurisée.
        
        Args:
            node_id: ID du nœud
            macaroon: Macaroon en base64 ou hex
            macaroon_type: Type de macaroon (admin, invoice, readonly)
            expiry_days: Expiration en jours (None = ROTATION_DAYS)
            
        Returns:
            Informations sur le macaroon stocké
        """
        macaroons = self._load_macaroons()
        
        if node_id not in macaroons:
            macaroons[node_id] = {}
        
        expiry = datetime.now() + timedelta(days=expiry_days or ROTATION_DAYS)
        
        macaroon_info = {
            "macaroon": macaroon,
            "type": macaroon_type,
            "created_at": datetime.now().isoformat(),
            "expires_at": expiry.isoformat(),
            "revoked": False
        }
        
        macaroons[node_id][macaroon_type] = macaroon_info
        self._save_macaroons(macaroons)
        
        self._audit_log("STORE", node_id, f"Type: {macaroon_type}, Expiry: {expiry.date()}")
        logger.info(f"Macaroon {macaroon_type} stocké pour le nœud {node_id[:8]}...")
        
        return macaroon_info
    
    def get_macaroon(self, node_id: str, macaroon_type: str = "admin") -> Optional[str]:
        """
        Récupère un macaroon.
        
        Args:
            node_id: ID du nœud
            macaroon_type: Type de macaroon
            
        Returns:
            Macaroon ou None si non trouvé/expiré/révoqué
        """
        macaroons = self._load_macaroons()
        
        if node_id not in macaroons or macaroon_type not in macaroons[node_id]:
            logger.warning(f"Macaroon {macaroon_type} introuvable pour {node_id[:8]}...")
            return None
        
        macaroon_info = macaroons[node_id][macaroon_type]
        
        # Vérifier révocation
        if macaroon_info.get("revoked", False):
            logger.warning(f"Macaroon {macaroon_type} révoqué pour {node_id[:8]}...")
            return None
        
        # Vérifier expiration
        expiry = datetime.fromisoformat(macaroon_info["expires_at"])
        if datetime.now() > expiry:
            logger.warning(f"Macaroon {macaroon_type} expiré pour {node_id[:8]}... (expiré le {expiry.date()})")
            return None
        
        self._audit_log("GET", node_id, f"Type: {macaroon_type}")
        return macaroon_info["macaroon"]
    
    def revoke_macaroon(self, node_id: str, macaroon_type: str = "admin") -> bool:
        """
        Révoque un macaroon.
        
        Args:
            node_id: ID du nœud
            macaroon_type: Type de macaroon
            
        Returns:
            True si révocation réussie
        """
        macaroons = self._load_macaroons()
        
        if node_id not in macaroons or macaroon_type not in macaroons[node_id]:
            logger.warning(f"Macaroon {macaroon_type} introuvable pour révocation: {node_id[:8]}...")
            return False
        
        macaroons[node_id][macaroon_type]["revoked"] = True
        macaroons[node_id][macaroon_type]["revoked_at"] = datetime.now().isoformat()
        self._save_macaroons(macaroons)
        
        self._audit_log("REVOKE", node_id, f"Type: {macaroon_type}")
        logger.info(f"Macaroon {macaroon_type} révoqué pour {node_id[:8]}...")
        
        return True
    
    def rotate_macaroon(
        self, 
        node_id: str, 
        new_macaroon: str,
        macaroon_type: str = "admin"
    ) -> Dict:
        """
        Effectue une rotation de macaroon (révoque l'ancien, stocke le nouveau).
        
        Args:
            node_id: ID du nœud
            new_macaroon: Nouveau macaroon
            macaroon_type: Type de macaroon
            
        Returns:
            Informations sur le nouveau macaroon
        """
        # Révoquer l'ancien
        self.revoke_macaroon(node_id, macaroon_type)
        
        # Stocker le nouveau
        new_info = self.store_macaroon(node_id, new_macaroon, macaroon_type)
        
        self._audit_log("ROTATE", node_id, f"Type: {macaroon_type}")
        logger.info(f"Rotation de macaroon {macaroon_type} effectuée pour {node_id[:8]}...")
        
        return new_info
    
    def check_expiry(self, node_id: str, macaroon_type: str = "admin") -> Optional[Dict]:
        """
        Vérifie l'expiration d'un macaroon.
        
        Returns:
            Dict avec informations d'expiration ou None si non trouvé
        """
        macaroons = self._load_macaroons()
        
        if node_id not in macaroons or macaroon_type not in macaroons[node_id]:
            return None
        
        macaroon_info = macaroons[node_id][macaroon_type]
        expires_at = datetime.fromisoformat(macaroon_info["expires_at"])
        now = datetime.now()
        
        days_remaining = (expires_at - now).days
        is_expired = now > expires_at
        needs_rotation = days_remaining <= 7  # Rotation si < 7 jours
        
        return {
            "expires_at": macaroon_info["expires_at"],
            "days_remaining": days_remaining,
            "is_expired": is_expired,
            "needs_rotation": needs_rotation,
            "revoked": macaroon_info.get("revoked", False)
        }
    
    def list_macaroons(self, node_id: Optional[str] = None) -> Dict:
        """
        Liste tous les macaroons stockés.
        
        Args:
            node_id: Filtrer par node_id (optionnel)
            
        Returns:
            Dict des macaroons (sans les valeurs sensibles)
        """
        macaroons = self._load_macaroons()
        
        result = {}
        
        nodes_to_list = [node_id] if node_id else macaroons.keys()
        
        for nid in nodes_to_list:
            if nid not in macaroons:
                continue
            
            result[nid] = {}
            for mtype, minfo in macaroons[nid].items():
                result[nid][mtype] = {
                    "type": minfo["type"],
                    "created_at": minfo["created_at"],
                    "expires_at": minfo["expires_at"],
                    "revoked": minfo.get("revoked", False),
                    "expiry_check": self.check_expiry(nid, mtype)
                }
        
        return result


# Fonction utilitaire pour usage CLI
def main():
    """Fonction principale pour usage en ligne de commande."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Macaroon Manager CLI")
    parser.add_argument("action", choices=["store", "get", "revoke", "rotate", "list", "check"])
    parser.add_argument("--node-id", required=False, help="ID du nœud")
    parser.add_argument("--macaroon", required=False, help="Macaroon à stocker")
    parser.add_argument("--type", default="admin", help="Type de macaroon (admin, invoice, readonly)")
    parser.add_argument("--encryption-key", required=False, help="Clé de chiffrement")
    
    args = parser.parse_args()
    
    manager = MacaroonManager(encryption_key=args.encryption_key)
    
    if args.action == "store":
        if not args.node_id or not args.macaroon:
            print("❌ --node-id et --macaroon requis pour store")
            return 1
        result = manager.store_macaroon(args.node_id, args.macaroon, args.type)
        print(f"✅ Macaroon stocké. Expire le {result['expires_at']}")
    
    elif args.action == "get":
        if not args.node_id:
            print("❌ --node-id requis pour get")
            return 1
        macaroon = manager.get_macaroon(args.node_id, args.type)
        if macaroon:
            print(f"✅ Macaroon: {macaroon[:20]}...{macaroon[-20:]}")
        else:
            print("❌ Macaroon introuvable ou expiré")
    
    elif args.action == "revoke":
        if not args.node_id:
            print("❌ --node-id requis pour revoke")
            return 1
        success = manager.revoke_macaroon(args.node_id, args.type)
        print("✅ Macaroon révoqué" if success else "❌ Échec révocation")
    
    elif args.action == "rotate":
        if not args.node_id or not args.macaroon:
            print("❌ --node-id et --macaroon requis pour rotate")
            return 1
        result = manager.rotate_macaroon(args.node_id, args.macaroon, args.type)
        print(f"✅ Rotation effectuée. Expire le {result['expires_at']}")
    
    elif args.action == "list":
        macaroons = manager.list_macaroons(args.node_id)
        print(json.dumps(macaroons, indent=2))
    
    elif args.action == "check":
        if not args.node_id:
            print("❌ --node-id requis pour check")
            return 1
        expiry_info = manager.check_expiry(args.node_id, args.type)
        if expiry_info:
            print(json.dumps(expiry_info, indent=2))
        else:
            print("❌ Macaroon introuvable")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
