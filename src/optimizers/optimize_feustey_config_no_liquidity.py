#!/usr/bin/env python3
"""
Version modifiée de optimize_feustey_config.py sans le scan de liquidité.
"""
import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Any

from src.rag import RAGWorkflow
from src.llm_selector import get_llm
from lnbits_client import LNBitsClient
from test_scenarios import TestScenarioManager

# Initialisation du modèle LLM (OpenAI par défaut)
rag_llm = get_llm("openai", model="gpt-4o-mini", temperature=0.7)
rag_system = RAGWorkflow()

# Configuration LNBits testnet
lnbits_testnet = LNBitsClient(
    url="https://testnet.lnbits.com",
    api_key="votre_api_key_testnet"
)

# Gestionnaire de scénarios de test
test_manager = TestScenarioManager(lnbits_client=lnbits_testnet)

# Fonction mockée pour remplacer le scan de liquidité
async def scan_popular_nodes(*args, **kwargs):
    print("Scan de liquidité désactivé. Passage à l'étape suivante...")
    return {}

# Fonction mockée pour l'évaluation de liquidité
async def evaluate_node_liquidity(node_pubkey: str, test_id: str) -> Dict[str, Any]:
    print(f"Évaluation de liquidité désactivée pour le nœud")
    # Retourner un dict vide pour ne pas perturber le calcul du score
    return {}

async def generate_test_scenarios():
    print("Génération de 5 scénarios de configuration différents...")
    
    prompt_template = """
    En utilisant les informations de l'article sur la vitesse des paiements Lightning Network,
    génère 5 scénarios distincts de configuration pour le nœud Feustey.
    Pour chaque scénario, fournis une configuration complète incluant:
    
    1. Structure des frais (base_fee, fee_rate pour canaux entrants/sortants)
    2. Stratégie de connexion (types de nœuds à cibler, score minimum de 75+)
    3. Politique de gestion de liquidité (ratio local/distant cible, minimum 66% de canaux liquides)
    4. Fréquence de rééquilibrage (basée sur le temps de réponse HTLC cible de 0.3s)
    5. Configuration spécifique pour testnet
    
    Explique brièvement la logique de chaque scénario et son avantage compétitif.
    Format: JSON structuré avec identifiant unique pour chaque scénario.
    """
    
    # Interroger le RAG
    result = await rag_system.query(prompt_template)
    scenarios_raw = result.get("answer", "")
    
    # Extraire et parser les scénarios JSON
    try:
        # Extraction du bloc JSON si nécessaire
        json_start = scenarios_raw.find("{")
        json_end = scenarios_raw.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            scenarios_json = scenarios_raw[json_start:json_end]
        else:
            raise ValueError("Format JSON non détecté dans la réponse")
            
        scenarios = json.loads(scenarios_json)
        
        # Valider chaque scénario
        validated_scenarios = {}
        for scenario_id, scenario in scenarios.items():
            validation_result = await rag_system.validate_lightning_config(scenario)
            
            # Ne conserver que les scénarios avec un score acceptable
            if validation_result.get("score", 0) >= 6:
                validated_scenarios[scenario_id] = {
                    **scenario,
                    "validation": {
                        "score": validation_result.get("score", 0),
                        "feedback": validation_result.get("feedback", ""),
                        "improvements": validation_result.get("improvements", [])
                    }
                }
                print(f"Scénario {scenario_id} validé avec un score de {validation_result.get('score', 0)}/10")
            else:
                print(f"Scénario {scenario_id} rejeté avec un score de {validation_result.get('score', 0)}/10")
                print(f"Raison: {validation_result.get('feedback', 'Score trop bas')}")
        
        # Sauvegarde des scénarios validés générés
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"rag/RAG_assets/experiments/feustey_{timestamp}_scenarios.json")
        output_path.parent.mkdir(exist_ok=True, parents=True)
        
        with open(output_path, "w") as f:
            json.dump(validated_scenarios, f, indent=2)
            
        print(f"Scénarios validés enregistrés dans {output_path}")
        
        return validated_scenarios, output_path
        
    except Exception as e:
        print(f"Erreur lors du traitement des scénarios: {e}")
        return None, None

async def run_test_scenarios(scenarios):
    results = {}
    
    print("Déploiement et test des scénarios sur LNBits testnet...")
    for scenario_id, scenario in scenarios.items():
        print(f"\nTest du scénario {scenario_id}: {scenario.get('name', 'Sans nom')}")
        print(f"Description: {scenario.get('description', 'Aucune description')}")
        
        # Configuration du nœud testnet selon le scénario
        await test_manager.configure_node(scenario)
        
        # Démarrage des tests avec mécanisme de retry
        test_id = None
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                test_id = await test_manager.start_test_session(
                    scenario_id=scenario_id,
                    duration_minutes=10,  # Version accélérée pour la démonstration
                    payment_count=25
                )
                break
            except Exception as e:
                print(f"Tentative {attempt+1}/{max_retries}: Erreur lors du démarrage du test: {e}")
                if attempt == max_retries - 1:
                    print(f"Échec du test pour le scénario {scenario_id} après {max_retries} tentatives")
                else:
                    await asyncio.sleep(2)  # Attendre avant de réessayer
        
        if test_id:
            results[scenario_id] = {
                "test_id": test_id,
                "scenario": scenario,
                "status": "running"
            }
        else:
            print(f"Test ignoré pour le scénario {scenario_id} en raison d'erreurs persistantes")
    
    return results

async def evaluate_results(test_results):
    print("\nÉvaluation des résultats après la période de test...")
    
    # Récupérer les métriques de performance pour chaque scénario
    scored_results = {}
    
    for scenario_id, test_info in test_results.items():
        # Récupération des métriques avec mécanisme de retry
        metrics = None
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Récupérer uniquement les métriques standards sans liquidité
                metrics = await test_manager.get_test_metrics(test_info["test_id"])
                break
            except Exception as e:
                print(f"Tentative {attempt+1}/{max_retries}: Erreur lors de la récupération des métriques: {e}")
                if attempt == max_retries - 1:
                    print(f"Impossible de récupérer les métriques pour le scénario {scenario_id}")
                else:
                    await asyncio.sleep(2)
        
        if metrics:
            # Calcul du score composite
            score = calculate_score(metrics)
            
            scored_results[scenario_id] = {
                "scenario": test_info["scenario"],
                "metrics": metrics,
                "score": score
            }
        else:
            print(f"Scénario {scenario_id} ignoré dans l'évaluation en raison d'erreurs de métrique")
    
    # Trier par score décroissant
    sorted_results = sorted(
        scored_results.items(), 
        key=lambda x: x[1]["score"], 
        reverse=True
    )
    
    # Sélectionner les 2 meilleurs
    top_scenarios = sorted_results[:2] if len(sorted_results) >= 2 else sorted_results
    
    # Générer un rapport détaillé
    report_path = await generate_final_report(top_scenarios, scored_results)
    
    return top_scenarios, report_path

def calculate_score(metrics: Dict[str, float]) -> float:
    """
    Calcule un score composite basé sur les métriques de performance du nœud.
    Version simplifiée sans les métriques de liquidité.
    
    Args:
        metrics: Dictionnaire contenant les métriques du nœud
        
    Returns:
        float: Score entre 0 et 100
    """
    # Poids des différentes composantes (total = 1.0)
    weights = {
        "htlc_response_time": 0.40,      # Temps de réponse HTLC (crucial selon l'article)
        "liquidity_balance": 0.30,       # Équilibre de la liquidité des canaux
        "routing_success_rate": 0.20,    # Taux de succès des routages
        "revenue_efficiency": 0.10       # Efficacité des revenus
    }
    
    # 1. Score du temps de réponse HTLC
    # Objectif : 0.3s ou moins = score maximal
    # Plus de 2s = score minimal
    htlc_time = metrics.get("htlc_response_time", 2.0)
    htlc_score = max(0, min(100, (2.0 - htlc_time) / 1.7 * 100))
    
    # 2. Score de l'équilibre de liquidité
    # Combine le channel_balance_quality et le % de canaux liquides
    liquidity_score = (
        metrics.get("channel_balance_quality", 0) * 60 +  # Qualité de l'équilibre (0-1) * 60
        min(1.0, metrics.get("liquid_channels_ratio", 0) / 0.66) * 40  # % canaux liquides, cible 66%
    )
    
    # 3. Score du taux de succès des routages
    routing_score = metrics.get("routing_success_rate", 0) * 100
    
    # 4. Score de l'efficacité des revenus
    # Combine revenue_per_sat_locked et average_fee_earned
    revenue_score = (
        min(1.0, metrics.get("revenue_per_sat_locked", 0) / 0.0001) * 50 +  # Normalisation des revenus/sat
        min(1.0, metrics.get("average_fee_earned", 0) / 100) * 50  # Normalisation des frais moyens
    )
    
    # Calcul du score final pondéré
    final_score = (
        weights["htlc_response_time"] * htlc_score +
        weights["liquidity_balance"] * liquidity_score +
        weights["routing_success_rate"] * routing_score +
        weights["revenue_efficiency"] * revenue_score
    )
    
    # Bonus/Malus basés sur des facteurs critiques
    if htlc_time > 8.0:  # Pénalité pour temps de réponse très lent
        final_score *= 0.7
    if metrics.get("channel_balance_quality", 0) < 0.3:  # Pénalité pour déséquilibre sévère
        final_score *= 0.8
        
    return round(final_score, 2)

async def generate_final_report(top_scenarios, all_results):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path(f"rag/RAG_assets/reports/feustey/feustey_{timestamp}_test_report.md")
    report_path.parent.mkdir(exist_ok=True, parents=True)
    
    # Utiliser le RAG pour générer un rapport comparatif
    prompt = f"""
    Génère un rapport détaillé comparant ces scénarios de nœuds Lightning Network.
    
    Voici les résultats des tests:
    {json.dumps(all_results, indent=2)}
    
    Les meilleurs scénarios sont:
    {json.dumps(top_scenarios, indent=2)}
    
    Analyse en détail pourquoi ces configurations sont supérieures en te basant sur:
    1. Le temps de réponse HTLC (objectif 0.3s)
    2. L'équilibre de liquidité (minimum 66% de canaux liquides)
    3. Le taux de succès des routages
    4. L'efficacité des revenus

    Compare leurs forces et faiblesses respectives.
    Recommande des améliorations supplémentaires pour chacun.
    
    Format: Markdown structuré et professionnel.
    """
    
    # Utilisation du système RAG pour générer le rapport
    report_result = await rag_system.query(prompt)
    report_content = report_result.get("answer", "Rapport non généré")
    
    # Validation du rapport généré
    validated_report = await rag_system.validate_report(report_content)
    
    # Construction du rapport final
    final_report = f"# Rapport d'Analyse des Scénarios de Configuration Feustey\n\n"
    final_report += f"*Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
    final_report += f"## Résultats\n\n{report_content}\n\n"
    final_report += f"## Validation du Rapport\n\n{validated_report}"
    
    with open(report_path, "w") as f:
        f.write(final_report)
    
    print(f"\nRapport détaillé sauvegardé dans {report_path}")
    return report_path

async def main():
    print("Démarrage du processus d'optimisation du nœud Feustey via RAG (sans scan de liquidité)...")
    start_time = datetime.now()
    
    try:
        # Étape 1: Génération des scénarios avec validation
        print("\n=== Phase 1: Génération de Scénarios ===")
        scenarios, scenarios_path = await generate_test_scenarios()
        if not scenarios:
            print("Échec de la génération des scénarios. Arrêt du processus.")
            return
        
        if len(scenarios) == 0:
            print("Aucun scénario n'a passé la validation. Arrêt du processus.")
            return
        
        # Étape 2: Lancement des tests
        print("\n=== Phase 2: Lancement des Tests ===")
        test_results = await run_test_scenarios(scenarios)
        
        if not test_results:
            print("Aucun test n'a pu être lancé. Arrêt du processus.")
            return
        
        # Étape 3: Attente pendant la période de test (avec surveillance)
        print("\n=== Phase 3: Surveillance des Tests ===")
        test_duration = 3600  # 1 heure
        interval = 300  # 5 minutes
        
        for i in range(0, test_duration, interval):
            await asyncio.sleep(interval)
            time_remaining = test_duration - i - interval
            if time_remaining > 0:
                print(f"Tests en cours. Temps restant: {time_remaining//60} minutes")
                
                # Vérification intermédiaire des métriques
                for scenario_id, test_info in test_results.items():
                    try:
                        metrics = await test_manager.get_test_metrics(test_info["test_id"])
                        if metrics:
                            htlc_time = metrics.get("htlc_response_time", 0)
                            success_rate = metrics.get("routing_success_rate", 0)
                            print(f"  - Scénario {scenario_id}: Temps HTLC = {htlc_time:.2f}s, "
                                  f"Taux de succès = {success_rate*100:.1f}%")
                    except Exception as e:
                        print(f"  - Scénario {scenario_id}: Erreur de vérification: {e}")
        
        # Étape 4: Évaluation des résultats
        print("\n=== Phase 4: Évaluation des Résultats ===")
        top_scenarios, report_path = await evaluate_results(test_results)
        
        # Étape 5: Conclusions et recommandations
        print("\n=== Phase 5: Conclusions ===")
        print("\nProcessus d'optimisation terminé avec succès!")
        print(f"Durée totale: {(datetime.now() - start_time).total_seconds()/60:.1f} minutes")
        print(f"Rapport final disponible dans: {report_path}")
        
        # Afficher les meilleurs scénarios
        if top_scenarios:
            print("\nMeilleurs scénarios identifiés:")
            for i, (scenario_id, data) in enumerate(top_scenarios):
                print(f"{i+1}. Scénario {scenario_id}: Score {data['score']:.2f}/100")
                print(f"   {data['scenario'].get('name', 'Sans nom')}")
                print(f"   HTLC Time: {data['metrics'].get('htlc_response_time', 0):.2f}s, "
                      f"Success Rate: {data['metrics'].get('routing_success_rate', 0)*100:.1f}%")
        else:
            print("Aucun scénario n'a pu être évalué complètement.")
            
    except Exception as e:
        print(f"Erreur pendant le processus d'optimisation: {e}")
        return

if __name__ == "__main__":
    asyncio.run(main()) 
