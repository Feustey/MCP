import os
import sys
import requests
import time
import json
from dotenv import load_dotenv
import asyncio
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

async def test_lnbits_connection():
    """Test de connexion à LNBits sur le réseau local"""
    logger.info("🔄 Test de connexion à LNBits...")
    
    # URL spécifiée par l'utilisateur
    lnbits_url = "http://192.168.0.45:5000"
    lnbits_wallet_id = "ab6380529b624321ade9ccb2aae3646b"
    lnbits_admin_key = "a271475725244124a5997ead1c7deb39"
    lnbits_invoice_key = "6139932367744b4abaf4c83a5113aca4"
    
    results = []
    
    # Test 1: API de santé
    try:
        start_time = time.time()
        response = requests.get(f"{lnbits_url}/api/v1/health", verify=False, timeout=5)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            logger.info(f"✅ Connexion à l'API de santé LNBits réussie ! Temps de réponse: {duration:.2f}s")
            logger.info(f"Réponse : {response.json()}")
            results.append(True)
        else:
            logger.error(f"❌ Erreur de connexion à l'API de santé. Code: {response.status_code}")
            logger.error(f"Réponse : {response.text}")
            results.append(False)
    except Exception as e:
        logger.error(f"❌ Erreur lors de la connexion à l'API de santé LNBits : {str(e)}")
        results.append(False)
    
    # Test 2: API wallet avec authentification
    try:
        headers = {
            "X-Api-Key": lnbits_admin_key,
            "Content-type": "application/json"
        }
        
        wallet_url = f"{lnbits_url}/api/v1/wallet"
        logger.info(f"Test de l'API wallet : {wallet_url}")
        
        start_time = time.time()
        response = requests.get(wallet_url, headers=headers, verify=False, timeout=5)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            logger.info(f"✅ Connexion à l'API wallet LNBits réussie ! Temps: {duration:.2f}s")
            logger.info(f"Réponse : {str(response.json())[:100]}...")
            results.append(True)
        else:
            logger.error(f"❌ Erreur de connexion à l'API wallet. Code: {response.status_code}")
            logger.error(f"Réponse : {response.text}")
            results.append(False)
    except Exception as e:
        logger.error(f"❌ Erreur lors de la connexion à l'API wallet LNBits : {str(e)}")
        results.append(False)
    
    # Test 3: API invoice avec authentification
    try:
        headers = {
            "X-Api-Key": lnbits_invoice_key,
            "Content-type": "application/json"
        }
        
        invoice_data = {
            "out": False,
            "amount": 10,
            "memo": "Test invoice"
        }
        
        invoice_url = f"{lnbits_url}/api/v1/payments"
        logger.info(f"Test de création d'invoice : {invoice_url}")
        
        start_time = time.time()
        response = requests.post(invoice_url, json=invoice_data, headers=headers, verify=False, timeout=5)
        duration = time.time() - start_time
        
        if response.status_code == 201:
            logger.info(f"✅ Création d'invoice LNBits réussie ! Temps: {duration:.2f}s")
            logger.info(f"Réponse : {str(response.json())[:100]}...")
            results.append(True)
        else:
            logger.error(f"❌ Erreur de création d'invoice. Code: {response.status_code}")
            logger.error(f"Réponse : {response.text}")
            results.append(False)
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création d'invoice LNBits : {str(e)}")
        results.append(False)
    
    # Considérer le test comme réussi si au moins un des endpoints répond
    return any(results)

async def test_openai_connection():
    """Test de connexion à l'API OpenAI"""
    try:
        import openai
        
        logger.info("🔄 Test de connexion à l'API OpenAI...")
        
        # Utiliser la clé API du fichier test_openai_connection.py
        api_key = "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"
        
        # Configuration du client OpenAI avec la clé API
        client = openai.OpenAI(api_key=api_key)
        
        # Test de création d'embedding
        start_time = time.time()
        embedding_response = client.embeddings.create(
            model="text-embedding-ada-002",
            input="Ceci est un test de connexion à l'API OpenAI pour vérifier les fonctionnalités RAG."
        )
        embedding_duration = time.time() - start_time
        
        if len(embedding_response.data[0].embedding) > 0:
            logger.info(f"✅ Création d'embedding réussie. Dimensions: {len(embedding_response.data[0].embedding)}, Temps: {embedding_duration:.2f}s")
        else:
            logger.error("❌ La création d'embedding a échoué.")
            return False
        
        # Test de complétion (chat)
        start_time = time.time()
        chat_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Vous êtes un assistant d'analyse de nœud Lightning Network."},
                {"role": "user", "content": "Comment optimiser la liquidité d'un nœud Lightning Network?"}
            ]
        )
        chat_duration = time.time() - start_time
        
        if chat_response.choices[0].message.content:
            logger.info(f"✅ Complétion chat réussie. Temps: {chat_duration:.2f}s")
            logger.info(f"Exemple de réponse: {chat_response.choices[0].message.content[:100]}...")
            return True
        else:
            logger.error("❌ La complétion chat a échoué.")
            return False
    except ImportError:
        logger.error("❌ Module OpenAI non disponible. Installez-le avec 'pip install openai'.")
        return False
    except Exception as e:
        logger.error(f"❌ Erreur lors de la connexion à OpenAI : {str(e)}")
        return False

async def test_local_api_endpoints():
    """Test des endpoints de l'API locale"""
    logger.info("🔄 Test des endpoints de l'API locale...")
    
    # Liste des endpoints à tester
    endpoints = [
        {"url": "http://localhost:5000/health", "method": "GET", "name": "Health Check"},
        {"url": "http://localhost:5000/api/v1/status", "method": "GET", "name": "API Status"}
    ]
    
    results = []
    
    for endpoint in endpoints:
        try:
            start_time = time.time()
            if endpoint["method"] == "GET":
                response = requests.get(endpoint["url"], timeout=5)
            elif endpoint["method"] == "POST":
                response = requests.post(endpoint["url"], json={}, timeout=5)
            
            duration = time.time() - start_time
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Endpoint '{endpoint['name']}' accessible. Temps: {duration:.2f}s")
                results.append(True)
            else:
                logger.error(f"❌ Erreur sur l'endpoint '{endpoint['name']}'. Code: {response.status_code}")
                results.append(False)
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'accès à l'endpoint '{endpoint['name']}': {str(e)}")
            results.append(False)
    
    return all(results) if results else False

async def test_rag_functionality():
    """Test de base des fonctionnalités RAG"""
    logger.info("🔄 Test des fonctionnalités RAG...")
    
    try:
        # Tentative d'importation du module rag
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        try:
            import rag
            logger.info("✅ Module RAG importé avec succès")
            
            # Test si la fonction run_rag existe
            if hasattr(rag, 'run_rag'):
                logger.info("✅ Fonction run_rag disponible")
                return True
            else:
                logger.warning("⚠️ Fonction run_rag non disponible dans le module")
                return False
                
        except ImportError:
            logger.error("❌ Impossible d'importer le module RAG")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erreur lors du test RAG: {str(e)}")
        return False

async def run_all_tests():
    """Exécute tous les tests de connexion et de fonctionnalité"""
    logger.info("🚀 Démarrage des tests de connexion et de fonctionnalité...")
    
    # Liste des tests à exécuter
    tests = [
        {"func": test_lnbits_connection, "name": "Connexion LNBits"},
        {"func": test_openai_connection, "name": "Connexion OpenAI"},
        {"func": test_local_api_endpoints, "name": "Endpoints API locale"},
        {"func": test_rag_functionality, "name": "Fonctionnalités RAG"}
    ]
    
    results = {}
    for test in tests:
        logger.info(f"\n{'='*50}\n🧪 Test: {test['name']}\n{'='*50}")
        try:
            start_time = time.time()
            success = await test["func"]()
            duration = time.time() - start_time
            
            results[test["name"]] = {
                "success": success,
                "duration": duration
            }
        except Exception as e:
            logger.error(f"❌ Exception non gérée pendant le test '{test['name']}': {str(e)}")
            results[test["name"]] = {
                "success": False,
                "duration": 0,
                "error": str(e)
            }
    
    # Afficher le résumé des tests
    logger.info("\n" + "="*50)
    logger.info("📊 RÉSUMÉ DES TESTS")
    logger.info("="*50)
    
    success_count = sum(1 for result in results.values() if result["success"])
    for name, result in results.items():
        status = "✅ SUCCÈS" if result["success"] else "❌ ÉCHEC"
        logger.info(f"{status} - {name} ({result['duration']:.2f}s)")
    
    logger.info(f"\nRésultat final: {success_count}/{len(tests)} tests réussis")
    
    return success_count == len(tests)

if __name__ == "__main__":
    asyncio.run(run_all_tests()) 