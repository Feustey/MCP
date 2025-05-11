#!/usr/bin/env python3
import asyncio
import argparse
import logging
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from tiktoken import encoding_for_model
from llama_index.core.schema import NodeWithScore, Node
from llama_index.llms.ollama import Ollama
from rag.advanced_generator import AdvancedResponseGenerator
from rag.hybrid_retriever import HybridRetriever

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Requêtes et contextes de test
TEST_QUERY = "Quelles sont les recommandations pour optimiser les frais du nœud Feustey?"

SAMPLE_DOCS = [
    {
        "content": "Le nœud Feustey (pubkey: 02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b) maintient actuellement une politique de frais relativement élevée avec un taux de base de 1000 sats et un taux proportionnel de 200 ppm. Cette politique a été établie en février 2025 et peut empêcher certains paiements de transiter par les canaux du nœud.",
        "score": 0.92,
        "metadata": {
            "source": "analyse_feustey.json",
            "node_id": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
            "alias": "Feustey",
            "update_date": "2025-04-01"
        }
    },
    {
        "content": "Les nœuds avec des politiques de frais optimisées maintiennent généralement un taux de base entre 0 et 500 sats et un taux proportionnel entre 50 et 150 ppm. Cette fourchette permet d'attirer du trafic tout en compensant les coûts de maintenance des canaux. Les nœuds les plus centraux comme ACINQ et Bitfinex utilisent des taux encore plus bas pour maximiser leur volume de transactions.",
        "score": 0.85,
        "metadata": {
            "source": "best_practices.json",
            "document_type": "recommandations",
            "created_at": "2025-03-15"
        }
    },
    {
        "content": "L'analyse des 10 derniers jours montre que le nœud Feustey a acheminé 18 paiements réussis pour un volume total de 3.2M sats. Cependant, 32 tentatives de routage ont échoué en raison de frais trop élevés selon les logs. Le revenu total généré par les frais s'élève à 5800 sats sur cette période.",
        "score": 0.78,
        "metadata": {
            "source": "stats_feustey_10days.json",
            "node_id": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
            "alias": "Feustey",
            "update_date": "2025-04-12"
        }
    },
    {
        "content": "Pour les nœuds de taille moyenne (5-20 canaux), il est recommandé d'adopter une politique de frais différenciée selon les canaux : des frais plus bas (0-100 sats + 25-50 ppm) pour les canaux avec des nœuds bien connectés qui peuvent apporter du volume, et des frais légèrement plus élevés (200-500 sats + 100-150 ppm) pour les canaux avec des nœuds moins centraux.",
        "score": 0.75,
        "metadata": {
            "source": "fee_strategies.json",
            "document_type": "recommandations",
            "created_at": "2025-02-28"
        }
    },
    {
        "content": "Le nœud Feustey dispose actuellement de 12 canaux actifs avec une capacité totale de 38M sats. Les principaux canaux sont établis avec ACINQ (10M sats), LightningTipBot (5M sats), Bitfinex (5M sats) et plusieurs nœuds de taille moyenne.",
        "score": 0.65,
        "metadata": {
            "source": "channels_feustey.json", 
            "node_id": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
            "alias": "Feustey",
            "update_date": "2025-04-10"
        }
    },
    {
        "content": "La réduction des frais doit être équilibrée avec la nécessité de protéger contre l'épuisement des liquidités. Pour éviter ce problème, vous pouvez implémenter des Déséquilibres Maximum (Maximum Channel Imbalance) qui limitent la quantité de satoshis pouvant être routés dans une seule direction, plutôt que de simplement augmenter les frais.",
        "score": 0.62,
        "metadata": {
            "source": "liquidity_management.json",
            "document_type": "recommandations",
            "created_at": "2025-01-20"
        }
    }
]

KEYWORDS = ["frais", "politique", "optimisation", "routage", "Lightning Network"]

async def test_advanced_generator():
    """Teste le générateur de réponses avancé."""
    try:
        logger.info("=== TEST DU GÉNÉRATEUR DE RÉPONSES AVANCÉ ===")
        
        # Initialiser le modèle LLM
        llm_model = os.getenv('LLAMA_MODEL', 'thebloke/llama-2-7b-chat-gguf')
        llm = Ollama(model=llm_model)
        
        # Initialiser le tokenizer
        tokenizer = encoding_for_model("gpt-3.5-turbo")
        
        # Créer le générateur avancé
        advanced_generator = AdvancedResponseGenerator(
            llm=llm,
            tokenizer=tokenizer
        )
        
        # Convertir les documents de test en NodeWithScore
        nodes = []
        for doc in SAMPLE_DOCS:
            node = Node(text=doc["content"], metadata=doc.get("metadata", {}))
            score = doc.get("score", 0.0)
            nodes.append(NodeWithScore(node=node, score=score))
        
        # Tester d'abord l'optimisation de la fenêtre de contexte
        logger.info("Test de l'optimisation de la fenêtre de contexte...")
        
        # Convertir en format pour optimize_context_window
        docs_for_opt = []
        for doc in SAMPLE_DOCS:
            docs_for_opt.append({
                "content": doc["content"],
                "score": doc["score"],
                "metadata": doc.get("metadata", {})
            })
        
        optimized_docs = advanced_generator.optimize_context_window(docs_for_opt, TEST_QUERY)
        
        logger.info(f"Documents originaux: {len(SAMPLE_DOCS)}")
        logger.info(f"Documents optimisés: {len(optimized_docs)}")
        
        # Tester la construction du prompt avancé
        logger.info("Test de la construction du prompt avancé...")
        system_prompt, user_prompt = advanced_generator.build_enhanced_prompt(TEST_QUERY, optimized_docs)
        
        logger.info(f"System prompt: {len(system_prompt)} caractères")
        logger.info(f"User prompt: {len(user_prompt)} caractères")
        
        if advanced_generator.debug_mode:
            logger.info("=== SYSTEM PROMPT ===")
            logger.info(system_prompt)
            logger.info("=== USER PROMPT ===")
            logger.info(user_prompt)
        
        # Tester la génération de réponse complète
        logger.info("Test de la génération de réponse complète...")
        start_time = datetime.now()
        
        response = await advanced_generator.generate_response(
            query=TEST_QUERY,
            nodes=nodes,
            keywords=KEYWORDS
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Temps de génération: {processing_time:.2f} secondes")
        logger.info(f"Longueur de la réponse: {len(response)} caractères")
        logger.info("=== RÉPONSE GÉNÉRÉE ===")
        logger.info(response)
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors du test: {str(e)}")
        return False

def main():
    # Charger les variables d'environnement
    load_dotenv()
    
    # Parser les arguments de ligne de commande
    parser = argparse.ArgumentParser(description="Test du générateur de réponses avancé")
    parser.add_argument('--debug', action='store_true', help='Activer le mode debug')
    args = parser.parse_args()
    
    # Exécuter le test
    success = asyncio.run(test_advanced_generator())
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main()) 