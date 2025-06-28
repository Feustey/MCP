#!/usr/bin/env python3
import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import re

from rag.rag import RAGWorkflow
from src.llm_selector import get_llm
from lnbits_client import LNBitsClient
from test_scenarios import TestScenarioManager
from liquidity_scanner import LiquidityScanManager, get_popular_lightning_nodes

# Initialisation du modèle Ollama avec paramètres configurables
ollama_llm = get_llm("ollama", model="llama3", temperature=0.7)
rag_system = RAGWorkflow(llm=ollama_llm)

# Configuration LNBits testnet - utilise les variables d'environnement
lnbits_testnet = LNBitsClient()

# Gestionnaire de scénarios de test
test_manager = TestScenarioManager(lnbits_client=lnbits_testnet)

# Scanner de liquidité LNRouter
liquidity_scanner = LiquidityScanManager(lnbits_client=lnbits_testnet)

async def scan_popular_nodes(max_nodes=5, sample_size=5):
    """Scanne les nœuds populaires pour analyser leur liquidité."""
    print(f"Lancement du scan de liquidité pour les nœuds populaires...")
    
    # Récupérer les nœuds populaires
    popular_nodes = await get_popular_lightning_nodes()
    nodes_to_scan = popular_nodes[:max_nodes]  # Limiter à max_nodes
    
    node_aliases = {node["pubkey"]: node["alias"] for node in nodes_to_scan}
    
    # Scanner les nœuds
    node_liquidity_data = {}
    for node in nodes_to_scan:
        print(f"Scan du nœud {node['alias']} ({node['pubkey'][:8]}...)")
        scan_result = await liquidity_scanner.bulk_scan_node_channels(
            node["pubkey"], 
            sample_size=sample_size
        )
        
        if scan_result["eligible"]:
            liquidity_score = scan_result.get("liquidity_score", 0)
            bidirectional_count = scan_result.get("bidirectional_count", 0)
            tested_count = scan_result.get("tested_channels", 1)
            
            node_liquidity_data[node["pubkey"]] = {
                "alias": node["alias"],
                "liquidity_score": liquidity_score,
                "bidirectional_ratio": bidirectional_count / tested_count if tested_count > 0 else 0,
                "bidirectional_count": bidirectional_count,
                "total_tested": tested_count,
                "scan_date": datetime.now().isoformat()
            }
            print(f"  ✓ Score de liquidité: {liquidity_score:.1f}/100")
        else:
            print(f"  ✗ Nœud non éligible pour le scan")
    
    # Sauvegarder les données
    if node_liquidity_data:
        await liquidity_scanner.save_scan_results(node_aliases)
        print(f"Données de liquidité pour {len(node_liquidity_data)} nœuds enregistrées")
    
    return node_liquidity_data

async def generate_test_scenarios():
    print("Génération de 5 scénarios de configuration différents...")
    
    # Récupérer les dernières données de liquidité
    liquidity_data_path = Path("rag/RAG_assets/market_data/latest_liquidity_scan.json")
    liquidity_data = {}
    
    if liquidity_data_path.exists():
        try:
            with open(liquidity_data_path, "r") as f:
                scan_data = json.load(f)
                liquidity_data = scan_data.get("node_results", {})
                print(f"Utilisation des données de liquidité existantes pour {len(liquidity_data)} nœuds")
        except Exception as e:
            print(f"Erreur lors de la lecture des données de liquidité: {e}")
    else:
        print("Aucune donnée de liquidité existante trouvée")
    
    # Créer un template de prompt sans utiliser de f-string avec backslash
    base_prompt = """
    En utilisant les informations de l'article sur la vitesse des paiements Lightning Network
    et les résultats du scan de liquidité des nœuds populaires (si disponibles),
    génère 5 scénarios distincts de configuration pour le nœud Feustey.
    
    {liquidity_data}
    
    Pour chaque scénario, fournis une configuration complète incluant:
    
    1. Structure des frais (base_fee, fee_rate pour canaux entrants/sortants)
    2. Stratégie de connexion (types de nœuds à cibler, score minimum de 75+)
       - Si des données de liquidité sont disponibles, privilégie les nœuds avec un score de liquidité élevé
    3. Politique de gestion de liquidité (ratio local/distant cible, minimum 66% de canaux liquides)
       - Inclure une stratégie pour maintenir au moins 500 000 sats de liquidité dans chaque direction
    4. Fréquence de rééquilibrage (basée sur le temps de réponse HTLC cible de 0.3s)
    5. Configuration spécifique pour testnet
    
    IMPORTANT: Réponds avec un format JSON valide contenant les scénarios.
    Assure-toi que le JSON soit structuré avec un identifiant unique pour chaque scénario.
    
    Voici un exemple de structure attendue:
    ```json
    {{
        "scenario1": {{
            "id": "feustey_scen1",
            "name": "Équilibre Optimisé",
            "description": "Optimisé pour l'équilibre de liquidité et la fiabilité",
            "fees": {{
                "base_fee": 1000,
                "fee_rate": 0.000001
            }},
            "connection_strategy": {{
                "target_nodes": ["nodes_with_high_liquidity", "popular_nodes"],
                "min_score": 80
            }},
            "liquidity_policy": {{
                "local_remote_ratio": 0.5,
                "min_bidirectional_channels_percent": 70,
                "min_liquidity_per_direction": 500000
            }},
            "rebalancing": {{
                "frequency": "hourly",
                "thresholds": {{
                    "unbalanced_ratio": 0.7,
                    "target_ratio": 0.5
                }}
            }}
        }},
        "scenario2": {{
            ...
        }}
    }}
    ```
    """
    
    # Préparer les données de liquidité formatées
    liquidity_data_formatted = ""
    if liquidity_data:
        liquidity_data_formatted = "Données du scan de liquidité:\n```\n" + json.dumps(liquidity_data, indent=2) + "\n```\n"
    
    # Insérer les données dans le template
    prompt_template = base_prompt.format(liquidity_data=liquidity_data_formatted)
    
    # Interroger le RAG avec des retries
    max_retries = 3
    scenarios_raw = None
    
    for attempt in range(max_retries):
        try:
            result = await rag_system.query(prompt_template)
            scenarios_raw = result.get("answer", "")
            
            if scenarios_raw:
                break
        except Exception as e:
            print(f"Tentative {attempt+1}/{max_retries}: Erreur lors de la génération avec RAG: {e}")
            await asyncio.sleep(2)  # Attendre avant de réessayer
    
    if not scenarios_raw:
        print("Échec de la génération des scénarios après plusieurs tentatives")
        return None, None
    
    # Extraire et parser les scénarios JSON
    try:
        # Extraction du bloc JSON - recherche du premier { et du dernier } pour extraire le JSON complet
        # Ne pas utiliser regex qui peut être trompé par des exemples de code
        json_content = scenarios_raw
        
        # Si la réponse contient du texte avant ou après le JSON, essayons de l'extraire
        if not scenarios_raw.strip().startswith('{') or not scenarios_raw.strip().endswith('}'):
            # Chercher des blocs de code markdown qui contiendraient du JSON
            json_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)```', scenarios_raw)
            if json_blocks:
                for block in json_blocks:
                    if block.strip().startswith('{') and block.strip().endswith('}'):
                        json_content = block
                        break
            else:
                # Chercher simplement le premier { et le dernier } si pas de blocs markdown
                json_start = scenarios_raw.find('{')
                json_end = scenarios_raw.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
                    json_content = scenarios_raw[json_start:json_end]
        else:
                    print("Format JSON non détecté dans la réponse")
                    print("Réponse brute:", scenarios_raw[:200] + "..." if len(scenarios_raw) > 200 else scenarios_raw)
                    return None, None
        
        # Nettoyage et parsing du JSON
        try:
            scenarios = json.loads(json_content)
        except json.JSONDecodeError as e:
            print(f"Erreur lors du parsing JSON: {e}")
            print("Tentative de nettoyage du JSON...")
            
            # Essayer de nettoyer le JSON - remplacer les guillemets simples par des doubles, etc.
            cleaned_json = json_content.replace("'", '"')
            cleaned_json = re.sub(r'(\w+):', r'"\1":', cleaned_json)  # Mettre les clés sans guillemets entre guillemets
            
            try:
                scenarios = json.loads(cleaned_json)
                print("Parsing JSON réussi après nettoyage")
            except json.JSONDecodeError as e2:
                print(f"Échec du nettoyage JSON: {e2}")
                return None, None
        
        # Valider chaque scénario
        validated_scenarios = {}
        for scenario_id, scenario in scenarios.items():
            # Ajouter un ID si manquant
            if "id" not in scenario:
                scenario["id"] = f"feustey_{scenario_id}"
                
            try:
            validation_result = await rag_system.validate_lightning_config(scenario)
            
            # Ne conserver que les scénarios avec un score acceptable
                score = validation_result.get("score", 0)
                if score >= 6:
                validated_scenarios[scenario_id] = {
                    **scenario,
                    "validation": {
                            "score": score,
                        "feedback": validation_result.get("feedback", ""),
                        "improvements": validation_result.get("improvements", [])
                    }
                }
                    print(f"Scénario {scenario_id} validé avec un score de {score}/10")
            else:
                    print(f"Scénario {scenario_id} rejeté avec un score de {score}/10")
                print(f"Raison: {validation_result.get('feedback', 'Score trop bas')}")
            except Exception as e:
                print(f"Erreur lors de la validation du scénario {scenario_id}: {e}")
        
        # Sauvegarde des scénarios validés générés
        if validated_scenarios:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"rag/RAG_assets/experiments/feustey_{timestamp}_scenarios.json")
        output_path.parent.mkdir(exist_ok=True, parents=True)
        
        with open(output_path, "w") as f:
            json.dump(validated_scenarios, f, indent=2)
            
        print(f"Scénarios validés enregistrés dans {output_path}")
        
        return validated_scenarios, output_path
        else:
            print("Aucun scénario n'a passé la validation")
            return {}, None
        
    except Exception as e:
        print(f"Erreur lors du traitement des scénarios: {e}")
        import traceback
        traceback.print_exc()
        return None, None

async def evaluate_node_liquidity(node_pubkey: str, test_id: str) -> Dict[str, Any]:
    """Évalue la liquidité d'un nœud pendant les tests."""
    try:
        # Récupérer les métriques de performance
        metrics = await test_manager.get_test_metrics(test_id)
        
        # Scanner un échantillon de canaux pour la liquidité
        scan_result = await liquidity_scanner.bulk_scan_node_channels(
            node_pubkey, 
            sample_size=3  # Tester seulement 3 canaux pendant l'évaluation
        )
        
        if scan_result["eligible"] and scan_result["results"]:
            # Calculer les métriques de liquidité
            bidirectional_ratio = scan_result["bidirectional_count"] / len(scan_result["results"])
            
            # Ajouter ces métriques au résultat
            metrics["bidirectional_channels_ratio"] = bidirectional_ratio
            metrics["liquidity_score"] = scan_result["liquidity_score"]
            
            # Enrichir le score basé sur la liquidité
            # (Ceci sera pris en compte dans calculate_score)
            
        return metrics
        
    except Exception as e:
        print(f"Erreur lors de l'évaluation de la liquidité: {e}")
        return {}

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
                # Récupérer les métriques standards puis les enrichir avec les métriques de liquidité
                standard_metrics = await test_manager.get_test_metrics(test_info["test_id"])
                
                # Évaluer la liquidité
                node_pubkey = test_info["scenario"].get("node_pubkey", "default_node_pubkey")
                enhanced_metrics = await evaluate_node_liquidity(node_pubkey, test_info["test_id"])
                
                # Fusionner les métriques
                metrics = {**standard_metrics, **enhanced_metrics}
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

def calculate_score(metrics: Dict[str, float], weights: Dict[str, float] = None) -> float:
    """
    Calcule un score composite basé sur les métriques de performance du nœud.
    Les pondérations sont basées sur l'importance relative des métriques ou
    ajustées dynamiquement selon les performances historiques.
    
    Args:
        metrics: Dictionnaire contenant les métriques du nœud
        weights: Dictionnaire de poids personnalisés (facultatif)
        
    Returns:
        float: Score entre 0 et 100
    """
    # Poids des différentes composantes (total = 1.0)
    # Si aucun poids personnalisé n'est fourni, utiliser les valeurs par défaut
    if not weights:
        weights = {
            "htlc_response_time": 0.30,      # Temps de réponse HTLC (crucial selon l'article)
            "liquidity_balance": 0.30,       # Équilibre de la liquidité des canaux
            "routing_success_rate": 0.20,    # Taux de succès des routages
            "revenue_efficiency": 0.10,      # Efficacité des revenus
            "liquidity_score": 0.10          # Score de liquidité (nouveau)
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
    
    # 5. Score de liquidité (nouveau)
    # Utilise directement le score de liquidité calculé par LiquidityScanManager ou 0 si non disponible
    liquidity_scan_score = metrics.get("liquidity_score", 0)
    
    # Bonus pour les canaux bidirectionnels
    bidirectional_ratio = metrics.get("bidirectional_channels_ratio", 0)
    if bidirectional_ratio > 0.8:  # Plus de 80% de canaux bidirectionnels
        liquidity_scan_score *= 1.2
        liquidity_scan_score = min(100, liquidity_scan_score)  # Plafonner à 100
    
    # Calcul du score final pondéré
    final_score = (
        weights["htlc_response_time"] * htlc_score +
        weights["liquidity_balance"] * liquidity_score +
        weights["routing_success_rate"] * routing_score +
        weights["revenue_efficiency"] * revenue_score +
        weights["liquidity_score"] * liquidity_scan_score
    )
    
    # Bonus/Malus basés sur des facteurs critiques
    # Note: Dans un système avancé, ces seuils seraient également ajustables dynamiquement
    if htlc_time > 8.0:  # Pénalité pour temps de réponse très lent
        final_score *= 0.7
    if metrics.get("channel_balance_quality", 0) < 0.3:  # Pénalité pour déséquilibre sévère
        final_score *= 0.8
    if bidirectional_ratio < 0.5:  # Pénalité pour faible taux de canaux bidirectionnels
        final_score *= 0.9
        
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
    5. Le score de liquidité et le ratio de canaux bidirectionnels

    Compare leurs forces et faiblesses respectives.
    Recommande des améliorations supplémentaires pour chacun, notamment concernant:
    - La stratégie de sélection des pairs basée sur leur score de liquidité
    - La fréquence et les seuils de rééquilibrage pour maintenir la bidirectionnalité des canaux
    
    Format: Markdown structuré et professionnel.
    """
    
    # Utilisation du système RAG pour générer le rapport
    report_result = await rag_system.query(prompt)
    report_content = report_result.get("answer", "Rapport non généré")
    
    # Validation du rapport généré
    validated_report = await rag_system.validate_report_with_ollama(report_content)
    
    # Construction du rapport final
    final_report = f"# Rapport d'Analyse des Scénarios de Configuration Feustey\n\n"
    final_report += f"*Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
    final_report += f"## Résultats\n\n{report_content}\n\n"
    final_report += f"## Validation du Rapport\n\n{validated_report}"
    
    with open(report_path, "w") as f:
        f.write(final_report)
    
    print(f"\nRapport détaillé sauvegardé dans {report_path}")
    return report_path

async def run_a_b_test(base_scenario: Dict[str, Any]) -> Dict[str, Any]:
    """
    Exécute un test A/B/C avec trois configurations:
    - Heuristique (celle générée par notre algorithme)
    - Aléatoire (configuration avec des paramètres aléatoires)
    - Baseline (configuration simple maximisant les frais)
    
    Args:
        base_scenario: Scénario de base à tester (heuristique)
        
    Returns:
        Résultats du test et scénario gagnant
    """
    print("\n=== Lancement de tests A/B/C comparatifs ===")
    
    # Générer les scénarios pour le test A/B/C
    scenarios = await test_manager.generate_a_b_test(base_scenario)
    
    print(f"Test comparatif de {len(scenarios)} scénarios différents:")
    for scenario in scenarios:
        print(f" - {scenario['type']}: {scenario.get('name', 'Sans nom')}")
    
    # Exécuter les tests pour chaque scénario
    test_results = {}
    for scenario in scenarios:
        scenario_id = scenario["id"]
        print(f"\nTest du scénario {scenario_id} ({scenario['type']})")
        
        # Configurer le nœud avec ce scénario
        await test_manager.configure_node(scenario)
        
        # Lancer le test
        test_id = await test_manager.start_test_session(
            scenario_id=scenario_id,
            duration_minutes=60,  # Test d'une heure
            payment_count=30
        )
        
        if test_id:
            test_results[scenario_id] = {
                "test_id": test_id,
                "scenario": scenario,
                "type": scenario["type"]
            }
        else:
            print(f"Échec du lancement du test pour {scenario_id}")
    
    # Attendre que tous les tests soient terminés
    print("\nAttente de la fin des tests (60 minutes)...")
    await asyncio.sleep(3600)  # 60 minutes
    
    # Évaluer les résultats
    print("\nAnalyse des résultats du test A/B/C...")
    scenario_ids = list(test_results.keys())
    winner = await test_manager.action_tracker.identify_winners(scenario_ids)
    
    if winner:
        print(f"\nScénario gagnant: {winner['scenario_id']} ({winner['action_type']})")
        print(f"Delta de sats forwardés: +{winner['delta_24h']}")
        
        # Si le gagnant est heuristique, c'est bon
        # Si c'est random ou baseline, nous devons ajuster notre heuristique
        if winner['action_type'] != "heuristic":
            print("\n⚠️ Notre heuristique a été battue! Ajustement nécessaire.")
            # Récupérer de nouveaux poids basés sur les performances
            new_weights = await test_manager.action_tracker.calculate_weight_adjustment()
            print(f"Nouveaux poids suggérés: {new_weights}")
            return {"winner": winner, "new_weights": new_weights}
    else:
        print("Impossible de déterminer un gagnant. Tests inconclussifs.")
    
    return {"winner": winner}

async def main():
    print("Démarrage du processus d'optimisation du nœud Feustey via RAG+Ollama...")
    start_time = datetime.now()
    
    try:
        # Étape 0: Scan de liquidité des nœuds populaires
        print("\n=== Phase 1: Scan de Liquidité ===")
        liquidity_data = await scan_popular_nodes(max_nodes=3, sample_size=3)
        
        # Étape 1: Génération des scénarios avec validation
        print("\n=== Phase 2: Génération de Scénarios ===")
        scenarios, scenarios_path = await generate_test_scenarios()
        if not scenarios:
            print("Échec de la génération des scénarios. Arrêt du processus.")
            return
        
        if len(scenarios) == 0:
            print("Aucun scénario n'a passé la validation. Arrêt du processus.")
            return
        
        # Étape 2: Lancement des tests
        print("\n=== Phase 3: Lancement des Tests ===")
        test_results = await run_test_scenarios(scenarios)
        
        if not test_results:
            print("Aucun test n'a pu être lancé. Arrêt du processus.")
            return
        
        # Étape 3: Attente pendant la période de test (avec surveillance)
        print("\n=== Phase 4: Surveillance des Tests ===")
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
        print("\n=== Phase 5: Évaluation des Résultats ===")
        top_scenarios, report_path = await evaluate_results(test_results)
        
        # Étape 4.5: Test A/B des meilleurs scénarios contre randomisé
        if top_scenarios and len(top_scenarios) > 0:
            best_scenario_id, best_data = top_scenarios[0]
            print("\n=== Phase 5.5: Test A/B/C du Meilleur Scénario ===")
            ab_results = await run_a_b_test(best_data["scenario"])
            
            # Si notre heuristique a été battue, ajuster les poids
            if ab_results.get("new_weights"):
                print(f"\nAjustement des poids de l'heuristique basé sur les tests A/B/C:")
                for metric, weight in ab_results["new_weights"].items():
                    print(f"  - {metric}: {weight:.2f}")
        
        # Étape 5: Conclusions et recommandations
        print("\n=== Phase 6: Conclusions ===")
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
                
                # Afficher les métriques de liquidité si disponibles
                liquidity_score = data['metrics'].get('liquidity_score')
                if liquidity_score is not None:
                    print(f"   Liquidity Score: {liquidity_score:.1f}/100")
                    
                bidirectional_ratio = data['metrics'].get('bidirectional_channels_ratio')
                if bidirectional_ratio is not None:
                    print(f"   Bidirectional Channels: {bidirectional_ratio*100:.1f}%")
                    
                # Afficher le delta de sats forwardés si disponible
                if 'delta_24h' in data:
                    print(f"   Δ Sats Forwardés (24h): {data['delta_24h']} sats")
        else:
            print("Aucun scénario n'a pu être évalué complètement.")
            
        # Nettoyage des tests
        await test_manager.cleanup_tests()
            
    except Exception as e:
        print(f"Erreur pendant le processus d'optimisation: {e}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    asyncio.run(main()) 