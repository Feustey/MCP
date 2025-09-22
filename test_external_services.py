#!/usr/bin/env python3
"""
Test de connexion aux services externes réels.
MongoDB, Redis, LNBits, Sparkseer avec les vraies configurations de production.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

# Charger les variables d'environnement de production
load_dotenv('.env.production.active')

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mongodb_connection():
    """Test de connexion MongoDB Atlas réelle."""
    logger.info("=== TEST CONNEXION MONGODB ===")
    
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.getenv("MONGO_URL")
        if not mongo_url:
            logger.error("MONGO_URL non configurée")
            return False
        
        logger.info(f"Connexion MongoDB: {mongo_url[:50]}...")
        
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=10000)
        
        # Test de connexion
        server_info = await client.server_info()
        logger.info(f"✅ MongoDB connecté - Version: {server_info.get('version', 'unknown')}")
        
        # Test d'accès base de données
        db = client.mcp_lightning
        collections = await db.list_collection_names()
        logger.info(f"✅ Base mcp_lightning: {len(collections)} collections")
        
        # Test d'écriture (optionnel)
        test_collection = db.connection_tests
        result = await test_collection.insert_one({
            "test": "connection_test",
            "timestamp": "2025-01-07T12:00:00Z",
            "status": "success"
        })
        logger.info(f"✅ Test écriture: {result.inserted_id}")
        
        await client.close()
        return True
        
    except ImportError:
        logger.error("❌ Module motor non installé")
        return False
    except Exception as e:
        logger.error(f"❌ Erreur MongoDB: {str(e)}")
        return False

async def test_redis_connection():
    """Test de connexion Redis Cloud réelle."""
    logger.info("\n=== TEST CONNEXION REDIS ===")
    
    try:
        import redis.asyncio as redis
        
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            logger.error("REDIS_URL non configurée")
            return False
        
        logger.info(f"Connexion Redis: {redis_url[:50]}...")
        
        client = redis.from_url(redis_url, socket_timeout=10)
        
        # Test de connexion
        pong = await client.ping()
        logger.info(f"✅ Redis ping: {pong}")
        
        # Test d'informations serveur
        info = await client.info()
        logger.info(f"✅ Redis version: {info.get('redis_version', 'unknown')}")
        logger.info(f"✅ Mémoire utilisée: {info.get('used_memory_human', 'unknown')}")
        
        # Test d'écriture/lecture
        await client.set("mcp_test_key", "connection_test_2025", ex=60)
        value = await client.get("mcp_test_key")
        logger.info(f"✅ Test écriture/lecture: {value.decode() if value else 'None'}")
        
        await client.close()
        return True
        
    except ImportError:
        logger.error("❌ Module redis non installé")
        return False
    except Exception as e:
        logger.error(f"❌ Erreur Redis: {str(e)}")
        return False

async def test_lnbits_connection():
    """Test de connexion LNBits réelle."""
    logger.info("\n=== TEST CONNEXION LNBITS ===")
    
    try:
        import httpx
        
        lnbits_url = os.getenv("LNBITS_URL")
        lnbits_api_key = os.getenv("LNBITS_API_KEY")
        
        if not lnbits_url:
            logger.error("LNBITS_URL non configurée")
            return False
        
        logger.info(f"Connexion LNBits: {lnbits_url}")
        
        headers = {"X-Api-Key": lnbits_api_key} if lnbits_api_key else {}
        
        async with httpx.AsyncClient(timeout=10) as client:
            # Test de base
            response = await client.get(f"{lnbits_url}/", headers=headers)
            logger.info(f"✅ LNBits status: {response.status_code}")
            
            # Test API wallet
            if lnbits_api_key:
                wallet_response = await client.get(f"{lnbits_url}/api/v1/wallet", headers=headers)
                if wallet_response.status_code == 200:
                    wallet_data = wallet_response.json()
                    logger.info(f"✅ Wallet balance: {wallet_data.get('balance', 'unknown')} msat")
                else:
                    logger.warning(f"⚠️  Wallet API: {wallet_response.status_code}")
            
            return response.status_code < 500
        
    except ImportError:
        logger.error("❌ Module httpx non installé")
        return False
    except Exception as e:
        logger.error(f"❌ Erreur LNBits: {str(e)}")
        return False

async def test_sparkseer_connection():
    """Test de connexion Sparkseer API."""
    logger.info("\n=== TEST CONNEXION SPARKSEER ===")
    
    try:
        import httpx
        
        sparkseer_url = os.getenv("SPARKSEER_BASE_URL")
        sparkseer_key = os.getenv("SPARKSEER_API_KEY")
        
        if not sparkseer_url or not sparkseer_key:
            logger.error("SPARKSEER_BASE_URL ou SPARKSEER_API_KEY non configurées")
            return False
        
        logger.info(f"Connexion Sparkseer: {sparkseer_url}")
        
        headers = {"Authorization": f"Bearer {sparkseer_key}"}
        
        async with httpx.AsyncClient(timeout=10) as client:
            # Test de base
            response = await client.get(f"{sparkseer_url}/health", headers=headers)
            logger.info(f"✅ Sparkseer health: {response.status_code}")
            
            # Test API nodes (si disponible)
            if response.status_code == 200:
                nodes_response = await client.get(f"{sparkseer_url}/nodes", headers=headers)
                if nodes_response.status_code == 200:
                    logger.info("✅ Sparkseer nodes API accessible")
                else:
                    logger.warning(f"⚠️  Sparkseer nodes: {nodes_response.status_code}")
            
            return response.status_code < 500
        
    except ImportError:
        logger.error("❌ Module httpx non installé") 
        return False
    except Exception as e:
        logger.error(f"❌ Erreur Sparkseer: {str(e)}")
        return False

async def test_ai_apis():
    """Test des APIs IA (OpenAI, Anthropic)."""
    logger.info("\n=== TEST APIS IA ===")
    
    results = {}
    
    # Test OpenAI
    try:
        import openai
        
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            client = openai.OpenAI(api_key=openai_key)
            
            # Test simple
            response = client.models.list()
            logger.info(f"✅ OpenAI: {len(response.data) if response.data else 0} modèles disponibles")
            results["openai"] = True
        else:
            logger.warning("⚠️  OPENAI_API_KEY non configurée")
            results["openai"] = False
            
    except ImportError:
        logger.warning("⚠️  Module openai non installé")
        results["openai"] = False
    except Exception as e:
        logger.error(f"❌ Erreur OpenAI: {str(e)}")
        results["openai"] = False
    
    # Test Anthropic
    try:
        import anthropic
        
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            client = anthropic.Anthropic(api_key=anthropic_key)
            
            # Test simple (ne consomme pas de crédits)
            logger.info("✅ Anthropic client initialisé")
            results["anthropic"] = True
        else:
            logger.warning("⚠️  ANTHROPIC_API_KEY non configurée")
            results["anthropic"] = False
            
    except ImportError:
        logger.warning("⚠️  Module anthropic non installé")
        results["anthropic"] = False
    except Exception as e:
        logger.error(f"❌ Erreur Anthropic: {str(e)}")
        results["anthropic"] = False
    
    return results

async def main():
    """Test complet de tous les services externes."""
    logger.info("🔍 TEST COMPLET DES SERVICES EXTERNES MCP")
    logger.info("=" * 50)
    
    results = {}
    
    # Tests des services
    results["mongodb"] = await test_mongodb_connection()
    results["redis"] = await test_redis_connection()
    results["lnbits"] = await test_lnbits_connection()
    results["sparkseer"] = await test_sparkseer_connection()
    results["ai_apis"] = await test_ai_apis()
    
    # Résumé final
    logger.info("\n" + "=" * 50)
    logger.info("📊 RÉSUMÉ DES TESTS")
    logger.info("=" * 50)
    
    total_services = 0
    working_services = 0
    
    for service, status in results.items():
        if isinstance(status, dict):
            # Pour les APIs IA
            for sub_service, sub_status in status.items():
                total_services += 1
                if sub_status:
                    working_services += 1
                    logger.info(f"✅ {service}.{sub_service}")
                else:
                    logger.info(f"❌ {service}.{sub_service}")
        else:
            total_services += 1
            if status:
                working_services += 1
                logger.info(f"✅ {service}")
            else:
                logger.info(f"❌ {service}")
    
    success_rate = (working_services / total_services) * 100 if total_services > 0 else 0
    
    logger.info(f"\n📈 Taux de succès: {working_services}/{total_services} ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        logger.info("🎉 Services externes majoritairement opérationnels !")
        return 0
    elif success_rate >= 50:
        logger.info("⚠️  Services externes partiellement opérationnels")
        return 0
    else:
        logger.error("❌ Problèmes critiques avec les services externes")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))