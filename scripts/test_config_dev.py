#!/usr/bin/env python3
"""
Test de configuration pour développement MCP
Dernière mise à jour: 9 mai 2025
"""

import os
import sys

def test_config_dev():
    """Test de la configuration de développement"""
    print("🧪 Test de configuration développement...")
    
    # Test des variables d'environnement
    required_vars = [
        'MONGO_URL',
        'REDIS_HOST',
        'ENVIRONMENT',
        'AI_OPENAI_API_KEY',
        'SECURITY_SECRET_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {value[:50]}{'...' if len(value) > 50 else ''}")
    
    if missing_vars:
        print(f"❌ Variables manquantes: {', '.join(missing_vars)}")
        return False
    
    # Test d'import de la configuration de développement
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from config_dev import settings
        print("✅ Configuration de développement chargée")
        
        # Test des valeurs
        print(f"📍 Environnement: {settings.environment}")
        print(f"🔧 Debug: {settings.debug}")
        print(f"🗄️ Base de données: {settings.database.url[:50]}...")
        print(f"🔴 Redis: {settings.redis.host}:{settings.redis.port}")
        print(f"🤖 AI Key: {settings.ai.openai_api_key[:20]}...")
        print(f"🔐 Secret: {settings.security.secret_key[:20]}...")
        
        return True
        
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur de configuration: {e}")
        return False

if __name__ == "__main__":
    success = test_config_dev()
    if not success:
        sys.exit(1)
    print("✅ Configuration développement OK") 