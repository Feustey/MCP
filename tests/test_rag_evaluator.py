#!/usr/bin/env python3
import asyncio
import argparse
import logging
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from rag.rag_evaluator import RAGEvaluator, evaluate_rag_response, RAGAS_AVAILABLE

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Exemples pour test
SAMPLE_QUERY = "Quelles sont les recommandations pour optimiser les frais du nœud Feustey?"

SAMPLE_CONTEXTS = [
    "Le nœud Feustey (pubkey: 02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b) maintient actuellement une politique de frais relativement élevée avec un taux de base de 1000 sats et un taux proportionnel de 200 ppm. Cette politique a été établie en février 2025 et peut empêcher certains paiements de transiter par les canaux du nœud.",
    "Les nœuds avec des politiques de frais optimisées maintiennent généralement un taux de base entre 0 et 500 sats et un taux proportionnel entre 50 et 150 ppm. Cette fourchette permet d'attirer du trafic tout en compensant les coûts de maintenance des canaux.",
    "L'analyse des 10 derniers jours montre que le nœud Feustey a acheminé 18 paiements réussis pour un volume total de 3.2M sats. Cependant, 32 tentatives de routage ont échoué en raison de frais trop élevés selon les logs. Le revenu total généré par les frais s'élève à 5800 sats sur cette période."
]

# Exemple de réponse fidèle aux contextes
SAMPLE_GOOD_RESPONSE = """
Pour optimiser les frais du nœud Feustey, voici les recommandations basées sur l'analyse des données:

1. Résumé exécutif:
   Le nœud Feustey utilise actuellement une politique de frais trop élevée (1000 sats de base + 200 ppm) qui bloque une partie du trafic potentiel, comme en témoignent les 32 tentatives de routage échouées récemment.

2. Analyse détaillée:
   - Les statistiques des 10 derniers jours montrent 18 paiements réussis (3.2M sats au total)
   - 32 tentatives de routage ont échoué en raison des frais trop élevés
   - Revenu actuel: 5800 sats sur cette période
   - Les nœuds optimisés utilisent généralement des frais bien plus bas:
     * Taux de base: 0-500 sats (vs 1000 actuellement)
     * Taux proportionnel: 50-150 ppm (vs 200 actuellement)

3. Recommandations pratiques:
   - Réduire le taux de base à 300-500 sats
   - Abaisser le taux proportionnel à 100-150 ppm
   - Surveiller l'évolution du trafic après ces changements pour optimiser davantage
"""

# Exemple de réponse non fidèle/hallucination
SAMPLE_BAD_RESPONSE = """
Pour optimiser les frais du nœud Feustey, je recommande les actions suivantes:

1. Résumé exécutif:
   Le nœud Feustey a besoin d'améliorer sa politique tarifaire pour augmenter sa profitabilité.

2. Analyse détaillée:
   - Les statistiques montrent une performance médiocre avec seulement 5% de réussite de routage
   - Le nœud génère actuellement 50,000 sats par mois en revenus
   - La stratégie optimale selon les études de LightningLabs est d'utiliser une tarification dynamique
   - Il existe 3 logiciels qui permettent d'automatiser cette tarification: Lightning Terminal, Charge-lnd et ThunderHub

3. Recommandations pratiques:
   - Installer Lightning Terminal pour la gestion automatique des frais
   - Réduire le taux de base à 200 sats et le taux proportionnel à 100 ppm
   - Ajouter 5 nouveaux canaux avec des nœuds centraux comme Bitrefill et LNBIG
   - Augmenter la liquidité totale à 100M sats minimum
"""

async def test_evaluator():
    """Teste le système d'évaluation RAGAS."""
    try:
        logger.info("=== TEST DU SYSTÈME D'ÉVALUATION RAG ===")
        
        if not RAGAS_AVAILABLE:
            logger.error("RAGAS n'est pas disponible. Veuillez l'installer avec: pip install ragas")
            return False
        
        # Créer l'évaluateur
        evaluator = RAGEvaluator()
        
        # Tester avec une bonne réponse
        logger.info("Évaluation d'une bonne réponse...")
        good_scores = await evaluator.evaluate(SAMPLE_QUERY, SAMPLE_GOOD_RESPONSE, SAMPLE_CONTEXTS)
        
        logger.info("Scores pour la bonne réponse:")
        for metric, score in good_scores.items():
            if metric != "timestamp":
                logger.info(f"- {metric}: {score:.4f}")
                
        quality = evaluator.get_quality_assessment(good_scores["composite_score"])
        logger.info(f"Évaluation qualitative: {quality}")
        
        # Tester avec une mauvaise réponse (hallucination)
        logger.info("\nÉvaluation d'une réponse avec hallucinations...")
        bad_scores = await evaluator.evaluate(SAMPLE_QUERY, SAMPLE_BAD_RESPONSE, SAMPLE_CONTEXTS)
        
        logger.info("Scores pour la réponse avec hallucinations:")
        for metric, score in bad_scores.items():
            if metric != "timestamp":
                logger.info(f"- {metric}: {score:.4f}")
                
        quality = evaluator.get_quality_assessment(bad_scores["composite_score"])
        logger.info(f"Évaluation qualitative: {quality}")
        
        # Tester la détection de l'aspect le plus faible
        weakest_aspect, weakest_score = evaluator.get_weakest_aspect(bad_scores)
        logger.info(f"\nPoint faible de la mauvaise réponse: {weakest_aspect} ({weakest_score:.4f})")
        
        # Obtenir un résumé des évaluations
        logger.info("\nGénération d'un résumé des évaluations...")
        summary = evaluator.get_evaluation_summary()
        logger.info(f"Résumé: {json.dumps(summary, indent=2)}")
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors du test: {str(e)}")
        return False

async def test_with_custom_query(query: str):
    """Teste le système d'évaluation avec une requête personnalisée."""
    try:
        from rag import RAGWorkflow
        
        logger.info(f"=== TEST AVEC REQUÊTE PERSONNALISÉE: {query} ===")
        
        if not RAGAS_AVAILABLE:
            logger.error("RAGAS n'est pas disponible. Veuillez l'installer avec: pip install ragas")
            return False
        
        # Initialiser le système RAG
        rag = RAGWorkflow()
        
        # Obtenir une réponse
        logger.info("Génération d'une réponse avec le système RAG...")
        response = await rag.query(query_text=query)
        
        # Récupérer les contextes utilisés pour la génération
        # Note: Cette partie dépend de l'implémentation RAG, 
        # ici on suppose que les contextes sont accessibles
        contexts = []
        if hasattr(rag, "_last_contexts") and rag._last_contexts:
            contexts = rag._last_contexts
        else:
            logger.warning("Impossible de récupérer les contextes. Utilisation de contextes génériques.")
            contexts = SAMPLE_CONTEXTS
        
        # Évaluer la réponse
        logger.info("Évaluation de la réponse générée...")
        scores = await evaluate_rag_response(query, response, contexts)
        
        logger.info("\nRéponse générée:")
        logger.info(response[:300] + "..." if len(response) > 300 else response)
        
        logger.info("\nScores d'évaluation:")
        for metric, score in scores.items():
            if metric != "timestamp":
                logger.info(f"- {metric}: {score:.4f}")
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors du test avec requête personnalisée: {str(e)}")
        return False

def main():
    # Charger les variables d'environnement
    load_dotenv()
    
    # Parser les arguments de ligne de commande
    parser = argparse.ArgumentParser(description="Test du système d'évaluation RAG")
    parser.add_argument('--query', type=str, help='Requête spécifique à tester')
    args = parser.parse_args()
    
    # Exécuter le test approprié
    if args.query:
        success = asyncio.run(test_with_custom_query(args.query))
    else:
        success = asyncio.run(test_evaluator())
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main()) 