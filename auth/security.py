from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
from jose import JWTError, jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidKey
import json

class SecurityManager:
    """Gestionnaire de sécurité pour les tokens JWT et les clés."""
    
    def __init__(self, keys_dir: str = "keys"):
        self.secret_key = os.getenv("JWT_SECRET_KEY")
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.key_rotation_interval = timedelta(days=30)  # Rotation des clés tous les 30 jours
        self.max_token_size = 1024 * 1024  # 1MB max pour les tokens JWE
        self.keys_dir = keys_dir
        self._load_or_create_keys()
    
    def _load_or_create_keys(self):
        """Charge ou crée les clés de signature."""
        if not os.path.exists(self.keys_dir):
            os.makedirs(self.keys_dir)
        
        current_key_path = os.path.join(self.keys_dir, "current.key")
        if not os.path.exists(current_key_path):
            # Créer une nouvelle paire de clés
            private_key = ec.generate_private_key(ec.SECP256R1())
            public_key = private_key.public_key()
            
            # Sauvegarder la clé privée
            with open(current_key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Sauvegarder la clé publique
            with open(os.path.join(self.keys_dir, "current.pub"), "wb") as f:
                f.write(public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))
        
        self.current_key_path = current_key_path
        self.last_rotation = datetime.fromtimestamp(os.path.getmtime(current_key_path))
    
    def _should_rotate_keys(self) -> bool:
        """Vérifie si les clés doivent être tournées."""
        return datetime.now() - self.last_rotation > self.key_rotation_interval
    
    def _rotate_keys(self):
        """Effectue la rotation des clés."""
        if not self._should_rotate_keys():
            return
        
        # Sauvegarder l'ancienne clé
        old_key_path = self.current_key_path
        backup_path = old_key_path + ".backup"
        os.rename(old_key_path, backup_path)
        
        # Créer une nouvelle paire de clés
        self._load_or_create_keys()
        
        # Supprimer l'ancienne sauvegarde après une période de grâce
        if os.path.exists(backup_path):
            os.remove(backup_path)
    
    def validate_token_size(self, token: str) -> bool:
        """Valide la taille du token JWE."""
        return len(token.encode()) <= self.max_token_size
    
    def validate_ecdsa_key(self, key_data: bytes) -> bool:
        """Valide une clé ECDSA."""
        try:
            # Tenter de charger la clé
            key = serialization.load_pem_private_key(key_data, password=None)
            
            # Vérifier que c'est une clé ECDSA
            if not isinstance(key, ec.EllipticCurvePrivateKey):
                return False
            
            # Vérifier la courbe (doit être au moins 256 bits)
            if key.curve.name not in ["secp256r1", "secp384r1", "secp521r1"]:
                return False
            
            return True
        except (ValueError, InvalidKey):
            return False
    
    def encode_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Encode un token JWT avec des vérifications de sécurité."""
        # Vérifier la rotation des clés
        self._rotate_keys()
        
        # Préparer les données
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        
        # Encoder le token
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        # Vérifier la taille
        if not self.validate_token_size(encoded_jwt):
            raise ValueError("Token trop grand")
        
        return encoded_jwt
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Décode un token JWT avec des vérifications de sécurité."""
        try:
            # Vérifier la taille
            if not self.validate_token_size(token):
                raise ValueError("Token trop grand")
            
            # Décoder le token sans vérification automatique de l'expiration
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            
            # Vérifier l'expiration manuellement
            exp = payload.get("exp")
            if exp is None:
                raise ValueError("Token sans expiration")
            
            if datetime.fromtimestamp(exp) < datetime.utcnow():
                raise ValueError("Token expiré")
            
            return payload
        except JWTError as e:
            raise ValueError(f"Token invalide: {str(e)}") 