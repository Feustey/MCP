import pytest
import asyncio
import time
import os
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from src.security_audit import (
    SecurityAuditManager,
    LightningNodeAuditor,
    SecurityEvent,
    SecurityLevel
)

@pytest.fixture
async def security_manager():
    """Fixture pour le gestionnaire d'audit de sécurité"""
    test_log_path = "logs/test_security_audit.log"
    
    # Supprimer le fichier de log s'il existe déjà
    if os.path.exists(test_log_path):
        os.remove(test_log_path)
        
    manager = SecurityAuditManager(
        audit_log_path=test_log_path,
        max_log_size_mb=1,
        max_log_age_days=1,
        jwt_secret="test_secret_key"
    )
    
    yield manager
    
    # Nettoyage
    if os.path.exists(test_log_path):
        os.remove(test_log_path)

@pytest.fixture
async def lightning_auditor(security_manager):
    """Fixture pour l'auditeur de nœuds Lightning"""
    return LightningNodeAuditor(security_manager)

@pytest.mark.asyncio
async def test_log_event(security_manager):
    """Test de la journalisation d'événements"""
    event_id = await security_manager.log_event(
        SecurityEvent.API_REQUEST,
        "test_user",
        "127.0.0.1",
        {"action": "test_action"},
        SecurityLevel.MEDIUM
    )
    
    # Vérifier que l'ID d'événement est valide
    assert isinstance(event_id, str)
    assert len(event_id) > 0
    
    # Vérifier que le fichier de log existe et contient l'entrée
    assert os.path.exists(security_manager.audit_log_path)
    
    with open(security_manager.audit_log_path, 'r') as f:
        log_contents = f.read()
        assert "test_user" in log_contents
        assert "127.0.0.1" in log_contents
        assert "test_action" in log_contents

@pytest.mark.asyncio
async def test_operation_token(security_manager):
    """Test de génération et vérification de tokens d'opération"""
    user_id = "test_user"
    operation = "test_operation"
    params = {"param1": "value1", "param2": 123}
    
    # Générer un token
    token = await security_manager.generate_operation_token(
        user_id, operation, params
    )
    
    # Vérifier que le token est valide
    is_valid, token_user_id, message = await security_manager.verify_operation_token(
        token, operation, params
    )
    
    assert is_valid is True
    assert token_user_id == user_id
    assert message == "Token valide"
    
    # Vérifier avec des paramètres modifiés
    modified_params = params.copy()
    modified_params["param2"] = 456
    
    is_valid, _, message = await security_manager.verify_operation_token(
        token, operation, modified_params
    )
    
    assert is_valid is False
    assert "Paramètres modifiés" in message
    
    # Vérifier avec une opération différente
    is_valid, _, message = await security_manager.verify_operation_token(
        token, "different_operation", params
    )
    
    assert is_valid is False
    assert "Opération non autorisée" in message

@pytest.mark.asyncio
async def test_verify_operation(security_manager):
    """Test de vérification d'opérations"""
    # Test d'opération non sensible
    is_allowed, message = await security_manager.verify_operation(
        "get_info",
        "test_user",
        "127.0.0.1",
        {"param": "value"}
    )
    
    assert is_allowed is True
    assert message == "Opération autorisée"
    
    # Test d'opération sensible sans signature
    is_allowed, message = await security_manager.verify_operation(
        "open_channel",
        "test_user",
        "127.0.0.1",
        {"node_id": "test_node", "amount": 100000}
    )
    
    assert is_allowed is False
    assert "signature" in message.lower()
    
    # Test avec une signature invalide
    is_allowed, message = await security_manager.verify_operation(
        "open_channel",
        "test_user",
        "127.0.0.1",
        {"node_id": "test_node", "amount": 100000},
        signature="invalid_signature"
    )
    
    assert is_allowed is False
    assert "invalide" in message.lower()
    
@pytest.mark.asyncio
async def test_ip_banning(security_manager):
    """Test du mécanisme de bannissement d'IP"""
    # Simuler plusieurs tentatives échouées
    user_id = "test_user"
    ip_address = "192.168.1.1"
    operation = "open_channel"
    
    # Patcher la fonction _verify_signature pour qu'elle retourne toujours False
    with patch.object(security_manager, '_verify_signature', return_value=False):
        # Simuler 10 tentatives échouées
        for _ in range(10):
            await security_manager.verify_operation(
                operation,
                user_id,
                ip_address,
                {"node_id": "test_node", "amount": 100000},
                signature="invalid_signature"
            )
    
    # Vérifier que l'IP est bannie
    assert ip_address in security_manager.banned_ips
    
    # Essayer une opération avec l'IP bannie
    is_allowed, message = await security_manager.verify_operation(
        "get_info",
        user_id,
        ip_address,
        {}
    )
    
    assert is_allowed is False
    assert "bloquée" in message.lower()

@pytest.mark.asyncio
async def test_lightning_node_auditor(lightning_auditor):
    """Test de l'auditeur de nœuds Lightning"""
    user_id = "test_user"
    ip_address = "127.0.0.1"
    
    # Test d'ouverture de canal valide
    is_allowed, message = await lightning_auditor.audit_channel_open(
        user_id,
        ip_address,
        "03cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
        50000
    )
    
    assert is_allowed is True
    assert "autorisée" in message.lower()
    
    # Test d'ouverture de canal avec montant trop faible
    is_allowed, message = await lightning_auditor.audit_channel_open(
        user_id,
        ip_address,
        "03cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
        10000
    )
    
    assert is_allowed is False
    assert "minimum" in message.lower()
    
    # Test d'ouverture de canal avec nœud sur liste noire
    is_allowed, message = await lightning_auditor.audit_channel_open(
        user_id,
        ip_address,
        "02aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        50000
    )
    
    assert is_allowed is False
    assert "liste noire" in message.lower()

@pytest.mark.asyncio
async def test_payment_auditing(lightning_auditor):
    """Test de l'audit des paiements"""
    user_id = "test_user"
    ip_address = "127.0.0.1"
    
    # Test de paiement valide
    is_allowed, message = await lightning_auditor.audit_payment(
        user_id,
        ip_address,
        "test_payment_hash",
        50000,
        "Paiement de test"
    )
    
    assert is_allowed is True
    assert "autorisé" in message.lower()
    
    # Test de paiement avec mémo suspect
    is_allowed, message = await lightning_auditor.audit_payment(
        user_id,
        ip_address,
        "another_payment_hash",
        50000,
        "Paiement pour darknet services"
    )
    
    # Le paiement est flaggé mais quand même autorisé
    assert is_allowed is True
    assert "autorisé" in message.lower()
    
    # Simuler plusieurs paiements pour atteindre la limite quotidienne
    # La limite est de 1,000,000 sats
    for _ in range(18):
        await lightning_auditor.audit_payment(
            user_id,
            ip_address,
            f"payment_hash_{_}",
            50000,
            "Paiement de test"
        )
    
    # Le prochain paiement devrait dépasser la limite quotidienne
    is_allowed, message = await lightning_auditor.audit_payment(
        user_id,
        ip_address,
        "final_payment_hash",
        50000,
        "Paiement de test"
    )
    
    assert is_allowed is False
    assert "limite quotidienne" in message.lower()

@pytest.mark.asyncio
async def test_log_rotation(security_manager):
    """Test de la rotation des logs"""
    # Patcher la méthode _rotate_logs pour vérifier qu'elle est appelée
    with patch.object(security_manager, '_rotate_logs') as mock_rotate:
        # Patcher la méthode os.path.getsize pour simuler un fichier de log volumineux
        with patch('os.path.getsize', return_value=(security_manager.max_log_size_mb + 1) * 1024 * 1024):
            # Générer un événement pour déclencher la vérification de rotation
            await security_manager.log_event(
                SecurityEvent.API_REQUEST,
                "test_user",
                "127.0.0.1",
                {"action": "test_action"},
                SecurityLevel.MEDIUM
            )
            
            # Vérifier que la rotation a été appelée
            mock_rotate.assert_called_once()

@pytest.mark.asyncio
async def test_critical_event_alert(security_manager):
    """Test de l'alerte pour événements critiques"""
    # Patcher la méthode _send_security_alert pour vérifier qu'elle est appelée
    with patch.object(security_manager, '_send_security_alert') as mock_alert:
        # Générer un événement critique
        await security_manager.log_event(
            SecurityEvent.UNAUTHORIZED_ACCESS,
            "test_user",
            "127.0.0.1",
            {"action": "unauthorized_action"},
            SecurityLevel.CRITICAL
        )
        
        # Vérifier que l'alerte a été envoyée
        mock_alert.assert_called_once()

@pytest.mark.asyncio
async def test_channel_close_auditing(lightning_auditor):
    """Test de l'audit des fermetures de canaux"""
    user_id = "test_user"
    ip_address = "127.0.0.1"
    channel_id = "test_channel_id"
    
    # Test de fermeture normale
    is_allowed, message = await lightning_auditor.audit_channel_close(
        user_id,
        ip_address,
        channel_id,
        force_close=False
    )
    
    assert is_allowed is True
    assert "autorisée" in message.lower()
    
    # Test de fermeture forcée
    is_allowed, message = await lightning_auditor.audit_channel_close(
        user_id,
        ip_address,
        channel_id,
        force_close=True
    )
    
    assert is_allowed is True
    
    # Simuler plusieurs fermetures forcées
    for _ in range(4):
        await lightning_auditor.audit_channel_close(
            user_id,
            ip_address,
            f"channel_{_}",
            force_close=True
        )
    
    # La 6ème fermeture forcée devrait être refusée
    is_allowed, message = await lightning_auditor.audit_channel_close(
        user_id,
        ip_address,
        "last_channel",
        force_close=True
    )
    
    assert is_allowed is False
    assert "trop de fermetures" in message.lower() 