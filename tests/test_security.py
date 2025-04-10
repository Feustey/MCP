import pytest
from datetime import datetime, timedelta
import os
import shutil
from auth.security import SecurityManager
from jose import JWTError, jwt

@pytest.fixture
def security_manager():
    """Fixture pour créer un SecurityManager avec un répertoire temporaire."""
    # Créer un répertoire temporaire pour les tests
    test_keys_dir = "test_keys"
    os.makedirs(test_keys_dir, exist_ok=True)
    
    # Sauvegarder les variables d'environnement
    old_secret = os.environ.get("JWT_SECRET_KEY")
    old_algo = os.environ.get("JWT_ALGORITHM")
    
    # Définir les variables d'environnement pour les tests
    os.environ["JWT_SECRET_KEY"] = "test_secret_key"
    os.environ["JWT_ALGORITHM"] = "HS256"
    
    # Créer le gestionnaire de sécurité avec le répertoire temporaire
    manager = SecurityManager(keys_dir=test_keys_dir)
    
    yield manager
    
    # Nettoyer après les tests
    if os.path.exists(test_keys_dir):
        shutil.rmtree(test_keys_dir)
    
    # Restaurer les variables d'environnement
    if old_secret:
        os.environ["JWT_SECRET_KEY"] = old_secret
    else:
        del os.environ["JWT_SECRET_KEY"]
    
    if old_algo:
        os.environ["JWT_ALGORITHM"] = old_algo
    else:
        del os.environ["JWT_ALGORITHM"]

def test_key_creation(security_manager):
    """Test la création initiale des clés."""
    assert os.path.exists(os.path.join(security_manager.keys_dir, "current.key"))
    assert os.path.exists(os.path.join(security_manager.keys_dir, "current.pub"))
    assert security_manager.last_rotation is not None

def test_key_rotation(security_manager):
    """Test la rotation des clés."""
    # Forcer la rotation en modifiant la date de dernière rotation
    security_manager.last_rotation = datetime.now() - timedelta(days=31)
    
    # Sauvegarder l'ancienne clé
    old_key_path = os.path.join(security_manager.keys_dir, "current.key")
    with open(old_key_path, "rb") as f:
        old_key_data = f.read()
    
    # Effectuer la rotation
    security_manager._rotate_keys()
    
    # Vérifier que la nouvelle clé est différente
    new_key_path = os.path.join(security_manager.keys_dir, "current.key")
    with open(new_key_path, "rb") as f:
        new_key_data = f.read()
    
    assert old_key_data != new_key_data
    assert security_manager.last_rotation > datetime.now() - timedelta(minutes=1)

def test_token_size_validation(security_manager):
    """Test la validation de la taille des tokens."""
    # Token valide
    valid_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNzEwMDAwMDAwfQ.test"
    assert security_manager.validate_token_size(valid_token)
    
    # Token trop grand
    large_token = "x" * (security_manager.max_token_size + 1)
    assert not security_manager.validate_token_size(large_token)

def test_ecdsa_key_validation(security_manager):
    """Test la validation des clés ECDSA."""
    # Clé valide
    valid_key_path = os.path.join(security_manager.keys_dir, "current.key")
    with open(valid_key_path, "rb") as f:
        valid_key_data = f.read()
    assert security_manager.validate_ecdsa_key(valid_key_data)
    
    # Clé invalide
    invalid_key_data = b"INVALID KEY DATA"
    assert not security_manager.validate_ecdsa_key(invalid_key_data)

def test_token_encoding_decoding(security_manager):
    """Test l'encodage et le décodage des tokens."""
    # Données de test
    test_data = {
        "sub": "test_user",
        "role": "admin"
    }
    
    # Encoder le token
    token = security_manager.encode_token(test_data, expires_delta=timedelta(minutes=15))
    assert isinstance(token, str)
    assert security_manager.validate_token_size(token)
    
    # Décoder le token
    decoded_data = security_manager.decode_token(token)
    assert decoded_data["sub"] == test_data["sub"]
    assert decoded_data["role"] == test_data["role"]
    assert "exp" in decoded_data

def test_token_expiration(security_manager):
    """Test la gestion de l'expiration des tokens."""
    # Créer un token expiré en utilisant jwt.encode directement
    expired_data = {
        "sub": "test_user",
        "exp": int((datetime.utcnow() - timedelta(minutes=1)).timestamp())
    }
    expired_token = jwt.encode(expired_data, os.environ["JWT_SECRET_KEY"], algorithm="HS256")
    
    # Vérifier que le décodage échoue
    with pytest.raises(ValueError) as exc_info:
        security_manager.decode_token(expired_token)
    assert "Token expiré" in str(exc_info.value)

def test_invalid_token(security_manager):
    """Test la gestion des tokens invalides."""
    # Token invalide
    invalid_token = "invalid.token.format"
    
    # Vérifier que le décodage échoue
    with pytest.raises(ValueError) as exc_info:
        security_manager.decode_token(invalid_token)
    assert "Token invalide" in str(exc_info.value)

def test_token_without_expiration(security_manager):
    """Test la gestion des tokens sans expiration."""
    # Créer un token sans expiration en utilisant jwt.encode directement
    data = {
        "sub": "test_user",
        "role": "admin"
    }
    token = jwt.encode(data, os.environ["JWT_SECRET_KEY"], algorithm="HS256")
    
    # Vérifier que le décodage échoue
    with pytest.raises(ValueError) as exc_info:
        security_manager.decode_token(token)
    assert "Token sans expiration" in str(exc_info.value) 