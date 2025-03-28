import re
from typing import Optional
from bech32 import bech32_decode, bech32_encode, CHARSET

class LightningKeyValidator:
    """Validateur de clés publiques Lightning Network."""
    
    # Pattern pour les clés publiques Lightning (33 bytes en hexadécimal)
    PUBKEY_PATTERN = re.compile(r'^[0-9a-fA-F]{66}$')
    
    @classmethod
    def is_valid_pubkey(cls, pubkey: str) -> bool:
        """
        Vérifie si une clé publique Lightning est valide.
        
        Args:
            pubkey: La clé publique à valider
            
        Returns:
            bool: True si la clé est valide, False sinon
        """
        if not pubkey:
            return False
            
        # Vérification du format hexadécimal
        if not cls.PUBKEY_PATTERN.match(pubkey):
            return False
            
        # Vérification du préfixe (02 ou 03)
        if pubkey[:2] not in ['02', '03']:
            return False
            
        return True
    
    @classmethod
    def is_valid_node_id(cls, node_id: str) -> bool:
        """
        Vérifie si un node_id Lightning est valide.
        
        Args:
            node_id: Le node_id à valider
            
        Returns:
            bool: True si le node_id est valide, False sinon
        """
        try:
            # Décodage du node_id bech32
            hrp, data = bech32_decode(node_id)
            
            # Vérification du préfixe (ln)
            if hrp != 'ln':
                return False
                
            # Vérification de la longueur des données (33 bytes)
            if len(data) != 33:
                return False
                
            return True
            
        except Exception:
            return False
    
    @classmethod
    def pubkey_to_node_id(cls, pubkey: str) -> Optional[str]:
        """
        Convertit une clé publique en node_id Lightning.
        
        Args:
            pubkey: La clé publique à convertir
            
        Returns:
            Optional[str]: Le node_id si la conversion réussit, None sinon
        """
        if not cls.is_valid_pubkey(pubkey):
            return None
            
        try:
            # Conversion de l'hexadécimal en bytes
            pubkey_bytes = bytes.fromhex(pubkey)
            
            # Encodage en bech32
            node_id = bech32_encode('ln', pubkey_bytes)
            
            return node_id
            
        except Exception:
            return None
    
    @classmethod
    def node_id_to_pubkey(cls, node_id: str) -> Optional[str]:
        """
        Convertit un node_id Lightning en clé publique.
        
        Args:
            node_id: Le node_id à convertir
            
        Returns:
            Optional[str]: La clé publique si la conversion réussit, None sinon
        """
        if not cls.is_valid_node_id(node_id):
            return None
            
        try:
            # Décodage du node_id
            _, data = bech32_decode(node_id)
            
            # Conversion en hexadécimal
            pubkey = data.hex()
            
            return pubkey
            
        except Exception:
            return None 