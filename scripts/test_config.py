#!/usr/bin/env python3

# Script de test de configuration pour MCP
# Dernière mise à jour: 9 mai 2025

import os
import sys

def test_config():
    """Test de la configuration des variables d'environnement"""
    
    print("🧪 Test de la configuration MCP...")
    
    # Variables requises
    required_vars = [
        'MONGO_URL',
        'REDIS_HOST',
        'REDIS_PORT',
        'REDIS_USERNAME',
        'REDIS_PASSWORD',
        'ENVIRONMENT'
    ]
    
    # Test des variables
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value[:50]}{'...' if len(value) > 50 else ''}")
        else:
            print(f"❌ {var}: MANQUANT")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n❌ Variables manquantes: {', '.join(missing_vars)}")
        return False
    
    # Test d'import des modules
    print("\n📦 Test des imports...")
    try:
        import fastapi
        print("✅ FastAPI importé")
    except ImportError as e:
        print(f"❌ FastAPI: {e}")
        return False
    
    try:
        import pydantic
        print("✅ Pydantic importé")
    except ImportError as e:
        print(f"❌ Pydantic: {e}")
        return False
    
    try:
        import uvicorn
        print("✅ Uvicorn importé")
    except ImportError as e:
        print(f"❌ Uvicorn: {e}")
        return False
    
    # Test de la configuration
    print("\n⚙️ Test de la configuration...")
    try:
        from config import settings
        print(f"✅ Configuration chargée: {settings.database.url[:50]}...")
        return True
    except Exception as e:
        print(f"❌ Erreur de configuration: {e}")
        return False

if __name__ == "__main__":
    success = test_config()
    if success:
        print("\n🎉 Configuration OK - Prêt à démarrer!")
        sys.exit(0)
    else:
        print("\n❌ Configuration échouée")
        sys.exit(1) 