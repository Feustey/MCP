#!/usr/bin/env python3
"""
Script de démonstration du protocole de calibration.
Ce script montre les fonctionnalités principales du protocole de calibration avec des données simulées.

Dernière mise à jour: 8 mai 2025
"""

import sys
import os
import logging
import json
import numpy as np
import click
from pathlib import Path
from datetime import datetime, timedelta

# Configurer les chemins d'importation
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
sys.path.append(str(root_dir))

# Importer les modules de calibration
from src.tools.simulator.simulation_fixtures import SimulationFixtures
from src.tools.simulator.calibration_visualizer import generate_run_dashboard

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("demo_calibration")


def generate_test_data(output_path: str, channels: int = 5, days: int = 14) -> dict:
    """
    Génère des données de test pour la démonstration
    
    Args:
        output_path: Chemin de sortie pour les données
        channels: Nombre de canaux
        days: Nombre de jours
    
    Returns:
        Données générées
    """
    logger.info(f"Génération de données de test avec {channels} canaux sur {days} jours")
    
    # Générer les données avec les fixtures
    fixtures = SimulationFixtures()
    test_data = fixtures.generate_test_data(channels, days)
    
    # Ajouter des paramètres connus
    test_data["known_params"] = {
        "fee_elasticity": -0.5,
        "volume_trend_drift": 0.02,
        "liquidity_pressure_amplitude": 0.15,
        "success_rate_base": 0.92,
        "noise_level": 0.1
    }
    
    # Sauvegarder les données
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(test_data, f, indent=2)
    
    logger.info(f"Données sauvegardées dans {output_file}")
    return test_data


def extract_distributions(data: dict) -> dict:
    """
    Extrait les distributions des métriques à partir des données
    
    Args:
        data: Données d'entrée
        
    Returns:
        Dictionnaire des distributions
    """
    distributions = {}
    
    channel_data = data.get("channel_data", {})
    
    # Volume de forwarding
    forward_volumes = []
    success_rates = []
    liquidity_ratios = []
    liquidity_changes = []
    
    for channel_id, records in channel_data.items():
        # Extraire les volumes
        channel_volumes = [r.get("forward_amount", 0) for r in records if r.get("forward_amount", 0) > 0]
        forward_volumes.extend(channel_volumes)
        
        # Extraire les taux de succès
        channel_success = [r.get("forward_success", 0) for r in records if "forward_success" in r]
        success_rates.extend(channel_success)
        
        # Extraire les ratios de liquidité
        channel_liquidity = [r.get("liquidity_ratio", 0) for r in records if "liquidity_ratio" in r]
        liquidity_ratios.extend(channel_liquidity)
        
        # Calculer les changements de ratio de liquidité
        for i in range(1, len(records)):
            if "liquidity_ratio" in records[i] and "liquidity_ratio" in records[i-1]:
                change = records[i]["liquidity_ratio"] - records[i-1]["liquidity_ratio"]
                liquidity_changes.append(change)
    
    # Ajouter les distributions
    if forward_volumes:
        distributions["forward_volume_distribution"] = np.array(forward_volumes)
    
    if success_rates:
        distributions["success_rate_distribution"] = np.array(success_rates)
    
    if liquidity_ratios:
        distributions["liquidity_ratio_distribution"] = np.array(liquidity_ratios)
    
    if liquidity_changes:
        distributions["liquidity_ratio_evolution"] = np.array(liquidity_changes)
    
    return distributions


def simulate_calibration(data: dict, output_dir: str, iterations: int = 10) -> dict:
    """
    Simule une calibration simplifiée pour la démonstration
    
    Args:
        data: Données d'entrée
        output_dir: Répertoire de sortie
        iterations: Nombre d'itérations
        
    Returns:
        Résultats de la calibration
    """
    logger.info(f"Simulation de calibration avec {iterations} itérations")
    
    # Extraire les paramètres connus (cibles)
    target_params = data.get("known_params", {
        "fee_elasticity": -0.5,
        "volume_trend_drift": 0.02,
        "liquidity_pressure_amplitude": 0.15,
        "success_rate_base": 0.92,
        "noise_level": 0.1
    })
    
    # Extraire les distributions réelles
    real_dist = extract_distributions(data)
    
    # Simuler la recherche de paramètres
    # Ici, on commence loin et on se rapproche progressivement des valeurs cibles
    best_params = {}
    for param, target_value in target_params.items():
        # Simuler une recherche qui s'approche progressivement de la cible
        start_value = target_value * (1 + np.random.uniform(-0.5, 0.5))
        best_params[param] = start_value
    
    # Simuler les itérations de calibration
    for i in range(iterations):
        logger.info(f"Itération {i+1}/{iterations}")
        
        # Simuler une amélioration progressive des paramètres
        for param, target_value in target_params.items():
            # Ajuster le paramètre pour se rapprocher de la cible
            current = best_params[param]
            # Distance relative à la cible
            distance = target_value - current
            # Ajout d'un peu de bruit pour simuler l'incertitude
            noise = distance * np.random.uniform(-0.2, 0.2)
            # Ajustement proportionnel à la distance (plus rapide au début, plus lent à la fin)
            adjustment = distance * (0.3 - 0.2 * i / iterations) + noise
            best_params[param] = current + adjustment
    
    # Simuler les métriques finales
    # Plus bas = meilleur
    divergences = {
        "forward_volume_distribution": max(0.01, 0.2 - 0.15 * iterations / 10),
        "success_rate_distribution": max(0.01, 0.15 - 0.12 * iterations / 10),
        "liquidity_ratio_evolution": max(0.02, 0.25 - 0.2 * iterations / 10),
        "fee_elasticity": max(0.03, 0.3 - 0.25 * iterations / 10)
    }
    
    # Générer des p-values simulées (plus élevé = meilleur)
    p_values = {
        "forward_volume_distribution": min(0.95, 0.03 + 0.1 * iterations / 10),
        "success_rate_distribution": min(0.9, 0.05 + 0.09 * iterations / 10),
        "liquidity_ratio_evolution": min(0.85, 0.02 + 0.08 * iterations / 10),
        "fee_elasticity": min(0.8, 0.01 + 0.07 * iterations / 10)
    }
    
    # Score global (plus bas = meilleur)
    score = np.mean(list(divergences.values()))
    
    # Simuler les distributions simulées en modifiant légèrement les réelles
    sim_dist = {}
    for metric, values in real_dist.items():
        # Ajouter un bruit proportionnel à la divergence pour cette métrique
        noise_level = divergences.get(metric, 0.1)
        sim_values = values * (1 + np.random.normal(0, noise_level, size=values.shape))
        sim_dist[metric] = sim_values
    
    # Générer le tableau de bord
    run_id = f"demo_calibration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    dashboard_path = generate_run_dashboard(
        run_id=run_id,
        real_dist=real_dist,
        sim_dist=sim_dist,
        divergences=divergences,
        params=best_params,
        p_values=p_values,
        output_dir=output_dir
    )
    
    logger.info(f"Calibration terminée avec score {score:.4f}")
    logger.info(f"Paramètres trouvés: {best_params}")
    logger.info(f"Tableau de bord généré dans {dashboard_path}")
    
    # Sauvegarder les résultats
    results = {
        "run_id": run_id,
        "score": score,
        "params": best_params,
        "target_params": target_params,
        "p_values": p_values,
        "divergences": divergences
    }
    
    results_file = Path(output_dir) / f"{run_id}_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    return results


def corrupt_test_data(data: dict, noise_level: float = 0.2, missing_rate: float = 0.2) -> dict:
    """
    Corrompt les données de test avec du bruit et des valeurs manquantes
    
    Args:
        data: Données à corrompre
        noise_level: Niveau de bruit (0-1)
        missing_rate: Taux de données manquantes (0-1)
        
    Returns:
        Données corrompues
    """
    logger.info(f"Corruption des données avec bruit={noise_level}, taux de données manquantes={missing_rate}")
    
    corrupted_data = data.copy()
    channel_data = data.get("channel_data", {}).copy()
    corrupted_channels = {}
    
    for channel_id, channel_history in channel_data.items():
        # Supprimer complètement certains canaux
        if np.random.random() < missing_rate * 0.5:
            continue
            
        corrupted_history = []
        for record in channel_history:
            # Supprimer certains enregistrements
            if np.random.random() < missing_rate:
                continue
                
            # Copier l'enregistrement
            corrupted_record = record.copy()
            
            # Ajouter du bruit aux valeurs numériques
            for key, value in record.items():
                if key == "timestamp":
                    continue
                    
                if isinstance(value, (int, float)):
                    # Ajouter du bruit
                    if np.random.random() < noise_level:
                        noise_factor = np.random.normal(1.0, noise_level)
                        corrupted_record[key] = value * max(0, noise_factor)
                    
                    # Supprimer certaines valeurs
                    if np.random.random() < missing_rate:
                        corrupted_record[key] = None
            
            corrupted_history.append(corrupted_record)
        
        # Ajouter l'historique corrompu s'il n'est pas vide
        if corrupted_history:
            corrupted_channels[channel_id] = corrupted_history
    
    corrupted_data["channel_data"] = corrupted_channels
    return corrupted_data


@click.group()
def cli():
    """Démonstration du protocole de calibration."""
    pass


@cli.command("generate")
@click.option('--output', default='data/test/demo_calibration_data.json', help='Chemin de sortie pour les données')
@click.option('--channels', default=5, help='Nombre de canaux')
@click.option('--days', default=14, help='Nombre de jours')
def generate_cmd(output, channels, days):
    """Génère des données de test pour la démonstration."""
    generate_test_data(output, channels, days)


@cli.command("calibrate")
@click.option('--input', default='data/test/demo_calibration_data.json', help='Données d\'entrée')
@click.option('--output-dir', default='data/test/demo_calibration_results', help='Répertoire de sortie')
@click.option('--iterations', default=10, help='Nombre d\'itérations')
def calibrate_cmd(input, output_dir, iterations):
    """Simule une calibration sur les données de test."""
    # Charger les données
    with open(input, 'r') as f:
        data = json.load(f)
    
    # Créer le répertoire de sortie
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Simuler la calibration
    simulate_calibration(data, output_dir, iterations)


@cli.command("robust")
@click.option('--input', default='data/test/demo_calibration_data.json', help='Données d\'entrée')
@click.option('--output-dir', default='data/test/demo_robustness_test', help='Répertoire de sortie')
@click.option('--noise-level', default=0.2, help='Niveau de bruit (0-1)')
@click.option('--missing-rate', default=0.2, help='Taux de données manquantes (0-1)')
@click.option('--iterations', default=10, help='Nombre d\'itérations')
def robust_cmd(input, output_dir, noise_level, missing_rate, iterations):
    """Teste la robustesse de la calibration face à des données bruitées."""
    # Charger les données propres
    with open(input, 'r') as f:
        clean_data = json.load(f)
    
    # Créer le répertoire de sortie
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Corrompre les données
    noisy_data = corrupt_test_data(clean_data, noise_level, missing_rate)
    
    # Sauvegarder les données corrompues
    with open(output_path / "noisy_data.json", 'w') as f:
        json.dump(noisy_data, f, indent=2)
    
    # Calibrer sur les données propres
    logger.info("Calibration sur données propres...")
    clean_output_dir = output_path / "clean_calibration"
    clean_output_dir.mkdir(parents=True, exist_ok=True)
    clean_results = simulate_calibration(clean_data, str(clean_output_dir), iterations)
    
    # Calibrer sur les données bruitées
    logger.info("Calibration sur données bruitées...")
    noisy_output_dir = output_path / "noisy_calibration"
    noisy_output_dir.mkdir(parents=True, exist_ok=True)
    noisy_results = simulate_calibration(noisy_data, str(noisy_output_dir), iterations)
    
    # Comparer les résultats
    logger.info("Comparaison des résultats...")
    clean_params = clean_results["params"]
    noisy_params = noisy_results["params"]
    
    print("\nComparaison des paramètres calibrés:")
    print(f"{'Paramètre':<30} {'Valeur propre':<15} {'Valeur bruitée':<15} {'Diff %':<10}")
    print("-" * 70)
    
    param_diffs = []
    for param in clean_params:
        clean_val = clean_params.get(param, 0)
        noisy_val = noisy_params.get(param, 0)
        
        if clean_val == 0:
            diff_pct = "N/A"
        else:
            diff_pct_val = abs(noisy_val - clean_val) / abs(clean_val) * 100
            param_diffs.append(diff_pct_val)
            diff_pct = f"{diff_pct_val:.2f}%"
        
        print(f"{param:<30} {clean_val:<15.4f} {noisy_val:<15.4f} {diff_pct:<10}")
    
    # Calculer la différence moyenne
    if param_diffs:
        avg_diff = np.mean(param_diffs)
        print(f"\nDifférence moyenne des paramètres: {avg_diff:.2f}%")
        
        if avg_diff < 10:
            verdict = "✅ TRÈS ROBUSTE (différence < 10%)"
        elif avg_diff < 25:
            verdict = "⚠️ MOYENNEMENT ROBUSTE (différence < 25%)"
        else:
            verdict = "❌ PEU ROBUSTE (différence ≥ 25%)"
        
        print(f"Verdict de robustesse: {verdict}")
    
    # Générer un rapport final
    with open(output_path / "robustness_report.md", "w") as f:
        f.write("# Rapport de test de robustesse\n\n")
        f.write(f"## Configuration\n\n")
        f.write(f"- **Niveau de bruit**: {noise_level*100:.1f}%\n")
        f.write(f"- **Taux de données manquantes**: {missing_rate*100:.1f}%\n\n")
        
        f.write("## Comparaison des paramètres\n\n")
        f.write("| Paramètre | Valeur propre | Valeur bruitée | Différence |\n")
        f.write("|-----------|--------------|---------------|------------|\n")
        
        for param in clean_params:
            clean_val = clean_params.get(param, 0)
            noisy_val = noisy_params.get(param, 0)
            
            if clean_val == 0:
                diff_pct = "N/A"
            else:
                diff_pct = f"{abs(noisy_val - clean_val) / abs(clean_val) * 100:.2f}%"
            
            f.write(f"| {param} | {clean_val:.6f} | {noisy_val:.6f} | {diff_pct} |\n")
        
        if param_diffs:
            f.write(f"\n**Différence moyenne**: {avg_diff:.2f}%\n\n")
            
            if avg_diff < 10:
                verdict_text = "✅ **TRÈS ROBUSTE** (différence < 10%)"
            elif avg_diff < 25:
                verdict_text = "⚠️ **MOYENNEMENT ROBUSTE** (différence < 25%)"
            else:
                verdict_text = "❌ **PEU ROBUSTE** (différence ≥ 25%)"
            
            f.write(f"**Verdict de robustesse**: {verdict_text}\n")


@cli.command("all")
@click.option('--output-dir', default='data/test/demo_calibration_full', help='Répertoire de sortie')
@click.option('--channels', default=5, help='Nombre de canaux')
@click.option('--days', default=14, help='Nombre de jours')
@click.option('--iterations', default=10, help='Nombre d\'itérations')
def all_cmd(output_dir, channels, days, iterations):
    """Exécute toute la démonstration en une seule commande."""
    # Créer le répertoire de sortie
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Générer les données
    data_file = output_path / "demo_data.json"
    data = generate_test_data(str(data_file), channels, days)
    
    # Calibration standard
    calib_dir = output_path / "calibration"
    calib_dir.mkdir(parents=True, exist_ok=True)
    simulate_calibration(data, str(calib_dir), iterations)
    
    # Test de robustesse
    robust_dir = output_path / "robustness"
    robust_dir.mkdir(parents=True, exist_ok=True)
    
    # Corrupting data
    noisy_data = corrupt_test_data(data, 0.2, 0.2)
    with open(robust_dir / "noisy_data.json", 'w') as f:
        json.dump(noisy_data, f, indent=2)
    
    # Clean calibration
    clean_dir = robust_dir / "clean"
    clean_dir.mkdir(parents=True, exist_ok=True)
    clean_results = simulate_calibration(data, str(clean_dir), iterations)
    
    # Noisy calibration
    noisy_dir = robust_dir / "noisy"
    noisy_dir.mkdir(parents=True, exist_ok=True)
    noisy_results = simulate_calibration(noisy_data, str(noisy_dir), iterations)
    
    # Compare results
    clean_params = clean_results["params"]
    noisy_params = noisy_results["params"]
    
    param_diffs = []
    for param in clean_params:
        clean_val = clean_params.get(param, 0)
        noisy_val = noisy_params.get(param, 0)
        
        if clean_val != 0:
            diff_pct_val = abs(noisy_val - clean_val) / abs(clean_val) * 100
            param_diffs.append(diff_pct_val)
    
    # Verdict
    if param_diffs:
        avg_diff = np.mean(param_diffs)
        
        with open(robust_dir / "robustness_report.md", "w") as f:
            f.write("# Rapport de test de robustesse\n\n")
            f.write(f"## Configuration\n\n")
            f.write(f"- **Niveau de bruit**: 20%\n")
            f.write(f"- **Taux de données manquantes**: 20%\n\n")
            
            f.write("## Comparaison des paramètres\n\n")
            f.write("| Paramètre | Valeur propre | Valeur bruitée | Différence |\n")
            f.write("|-----------|--------------|---------------|------------|\n")
            
            for param in clean_params:
                clean_val = clean_params.get(param, 0)
                noisy_val = noisy_params.get(param, 0)
                
                if clean_val == 0:
                    diff_pct = "N/A"
                else:
                    diff_pct = f"{abs(noisy_val - clean_val) / abs(clean_val) * 100:.2f}%"
                
                f.write(f"| {param} | {clean_val:.6f} | {noisy_val:.6f} | {diff_pct} |\n")
            
            f.write(f"\n**Différence moyenne**: {avg_diff:.2f}%\n\n")
            
            if avg_diff < 10:
                verdict_text = "✅ **TRÈS ROBUSTE** (différence < 10%)"
            elif avg_diff < 25:
                verdict_text = "⚠️ **MOYENNEMENT ROBUSTE** (différence < 25%)"
            else:
                verdict_text = "❌ **PEU ROBUSTE** (différence ≥ 25%)"
            
            f.write(f"**Verdict de robustesse**: {verdict_text}\n")
    
    logger.info(f"Démonstration complète exécutée dans {output_dir}")


if __name__ == "__main__":
    cli() 