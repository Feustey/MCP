#!/usr/bin/env python3
"""
Script pour lancer le système RAG MCP avec Ollama en local
Dernière mise à jour: 25 mai 2025
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Ajouter le répertoire du projet au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importer les modules nécessaires
try:
    from rag.rag import RAGWorkflow, OllamaEmbedder
    from rag.mongo_operations import MongoOperations
except ImportError as e:
    logger.error(f"Erreur d'import: {e}")
    logger.info("Utilisation d'une version simplifiée sans dépendances problématiques")
    
    # Version simplifiée pour contourner les problèmes d'import
    import httpx
    import json
    
    class SimpleOllamaClient:
        def __init__(self, base_url="http://localhost:11434"):
            self.base_url = base_url
            
        async def get_embedding(self, text: str):
            """Obtient un embedding via Ollama."""
            try:
                url = f"{self.base_url}/api/embeddings"
                data = {
                    "model": "llama3",
                    "prompt": text
                }
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, json=data)
                    response.raise_for_status()
                    result = response.json()
                    return result.get("embedding", [])
            except Exception as e:
                logger.error(f"Erreur embedding: {e}")
                return []
        
        async def generate_response(self, prompt: str, model="llama3"):
            """Génère une réponse via Ollama."""
            try:
                url = f"{self.base_url}/api/generate"
                data = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
                
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, json=data)
                    response.raise_for_status()
                    result = response.json()
                    return result.get("response", "")
            except Exception as e:
                logger.error(f"Erreur génération: {e}")
                return f"Erreur: {e}"


async def test_ollama_connection():
    """Test la connexion à Ollama."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            response.raise_for_status()
            models = response.json()
            logger.info(f"Ollama accessible. Modèles disponibles: {[m['name'] for m in models['models']]}")
            return True
    except Exception as e:
        logger.error(f"Ollama non accessible: {e}")
        return False


async def run_simple_rag_test():
    """Lance un test simple du système RAG avec Ollama."""
    
    # Test de connexion Ollama
    if not await test_ollama_connection():
        logger.error("Impossible de se connecter à Ollama. Assurez-vous qu'il est lancé.")
        return False
    
    # Créer le client Ollama
    client = SimpleOllamaClient()
    
    # Test d'embedding
    logger.info("Test de génération d'embedding...")
    test_text = "Configuration des frais Lightning Network pour optimiser les revenus"
    embedding = await client.get_embedding(test_text)
    
    if embedding:
        logger.info(f"Embedding généré avec succès (dimension: {len(embedding)})")
    else:
        logger.error("Échec de génération d'embedding")
        return False
    
    # Test de génération de réponse
    logger.info("Test de génération de réponse...")
    prompt = """En tant qu'expert Lightning Network, analysez cette situation:

Un nœud Lightning a les métriques suivantes:
- Capacité totale: 5 BTC
- Liquidité sortante: 2.5 BTC  
- Liquidité entrante: 2.5 BTC
- Frais base: 1000 msat
- Frais proportionnels: 100 ppm

Question: Quelles recommandations donneriez-vous pour optimiser les revenus de ce nœud?

Répondez de manière concise et pratique."""

    response = await client.generate_response(prompt)
    
    if response and "Erreur:" not in response:
        logger.info("Réponse générée avec succès:")
        logger.info(f"Réponse: {response[:300]}...")
        return True
    else:
        logger.error(f"Échec de génération de réponse: {response}")
        return False


async def run_full_rag_workflow():
    """Lance le workflow RAG complet si les dépendances sont disponibles."""
    try:
        # Créer les répertoires nécessaires
        os.makedirs("rag/RAG_assets/reports", exist_ok=True)
        os.makedirs("data/raw", exist_ok=True)
        
        # Initialiser le workflow RAG
        logger.info("Initialisation du workflow RAG complet...")
        rag = RAGWorkflow()
        
        # Test d'une requête simple
        query = "Quelles sont les meilleures pratiques pour optimiser les frais d'un nœud Lightning?"
        logger.info(f"Test de requête: {query}")
        
        response = await rag.query(query)
        logger.info(f"Réponse RAG: {response}")
        
        return True
    except Exception as e:
        logger.error(f"Erreur dans le workflow RAG complet: {e}")
        return False


async def main():
    """Fonction principale."""
    print("🚀 Lancement du système RAG MCP avec Ollama")
    print("=" * 50)
    
    # Test simple d'abord
    logger.info("Phase 1: Test simple avec Ollama")
    simple_success = await run_simple_rag_test()
    
    if simple_success:
        print("✅ Test simple Ollama réussi")
        
        # Tentative du workflow complet
        logger.info("Phase 2: Tentative du workflow RAG complet")
        try:
            full_success = await run_full_rag_workflow()
            if full_success:
                print("✅ Workflow RAG complet réussi")
            else:
                print("⚠️  Workflow complet échoué, mais test simple OK")
        except Exception as e:
            logger.info(f"Workflow complet non disponible: {e}")
            print("⚠️  Workflow complet non disponible, mais test simple fonctionne")
    else:
        print("❌ Test simple Ollama échoué")
        return 1
    
    print("\n🎯 Système RAG opérationnel avec Ollama!")
    print("📍 Pour tester manuellement:")
    print("   curl -X POST http://localhost:11434/api/generate -d '{\"model\":\"llama3\",\"prompt\":\"Test\",\"stream\":false}'")
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main())) 