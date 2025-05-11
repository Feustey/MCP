#!/usr/bin/env python3
"""
Script de test pour le protocole de calibration.
Ce script permet de tester rapidement le protocole de calibration avec des données simulées.

Dernière mise à jour: 8 mai 2025
"""

import sys
import os
import logging
import json
import numpy as np
from pathlib import Path
from typing import Dict, Any

# Chemin absolu du répertoire parent pour l'import
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent.parent
sys.path.append(str(parent_dir))

from tools.simulator.calibration_cli import run_calibration, RealNodeDataCollector
from tools.simulator.simulation_fixtures import SimulationFixtures
from tools.simulator.stochastic_simulator import LightningSimEnvironment


def generate_test_data(output_path: str, days: int = 14, channels: int = 5) -> None:
    """
    Génère des données de test pour la calibration
    
    Args:
        output_path: Chemin du fichier de sortie
        days: Nombre de jours de données
        channels: Nombre de canaux à simuler
    """
    # Paramètres connus pour générer des données de référence
    known_params = {
        "fee_elasticity": -0.5,
        "volume_trend_drift": 0.02,
        "liquidity_pressure_amplitude": 0.15,
        "success_rate_base": 0.92,
        "noise_level": 0.1
    }
    
    # Initialiser les fixtures
    fixtures = SimulationFixtures()
    
    # Générer directement les données de test
    test_data = fixtures.generate_test_data(channels, days)
    
    # Ajouter les paramètres connus
    test_data["known_params"] = known_params
    
    # Sauvegarder les données dans un fichier JSON
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(test_data, f, indent=2)
    
    print(f"Données de test générées dans {output_file}")
    print(f"Paramètres utilisés: {known_params}")


def corrupt_data(data: Dict[str, Any], noise_level: float = 0.2, missing_rate: float = 0.2) -> Dict[str, Any]:
    """
    Corrompt les données avec du bruit et des valeurs manquantes
    
    Args:
        data: Données à corrompre
        noise_level: Niveau de bruit (0-1)
        missing_rate: Taux de données manquantes (0-1)
        
    Returns:
        Données corrompues
    """
    if "channel_data" not in data:
        print("Format de données invalide")
        return data
    
    channel_data = data["channel_data"]
    corrupted_data = {}
    
    for channel_id, channel_history in channel_data.items():
        # Générer un nouvel historique corrompu
        corrupted_history = []
        
        # Déterminer si on supprime complètement ce canal
        if np.random.random() < missing_rate * 0.5:  # Plus faible probabilité de supprimer un canal entier
            continue
        
        for record in channel_history:
            # Déterminer si on supprime cet enregistrement
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
                        # Bruit gaussien proportionnel à la valeur
                        noise_factor = np.random.normal(1.0, noise_level)
                        new_value = value * max(0, noise_factor)
                        corrupted_record[key] = new_value
                    
                    # Supprimer la valeur
                    if np.random.random() < missing_rate:
                        corrupted_record[key] = None
            
            corrupted_history.append(corrupted_record)
        
        # N'ajouter le canal que s'il a encore des données
        if corrupted_history:
            corrupted_data[channel_id] = corrupted_history
    
    # Retourner les données corrompues au même format
    return {
        "channel_data": corrupted_data,
        "known_params": data.get("known_params", {}),
        "days": data.get("days", 14),
        "num_channels": len(corrupted_data)
    }


if __name__ == "__main__":
    import click
    
    @click.group()
    def cli():
        """Outils de test pour le protocole de calibration"""
        pass
    
    @cli.command("generate")
    @click.option('--output', default='data/test/calibration_test_data.json', 
                help='Chemin du fichier de sortie')
    @click.option('--days', default=14, help='Nombre de jours de données')
    @click.option('--channels', default=5, help='Nombre de canaux à simuler')
    def generate_cmd(output, days, channels):
        """Génère des données de test pour la calibration"""
        generate_test_data(output, days, channels)
    
    @cli.command("test")
    @click.option('--input', default='data/test/calibration_test_data.json', 
                help='Données de test à utiliser')
    @click.option('--output-dir', default='data/test/calibration_results', 
                help='Répertoire pour les résultats')
    @click.option('--iterations', default=20, help='Nombre d\'itérations de calibration')
    def test_cmd(input, output_dir, iterations):
        """Exécute le protocole de calibration sur des données de test"""
        # Charger les données pour récupérer les paramètres connus
        with open(input, 'r') as f:
            test_data = json.load(f)
            
        known_params = test_data.get("known_params", {})
        
        print(f"Exécution de la calibration sur les données de test avec {iterations} itérations")
        print(f"Paramètres connus: {known_params}")
        
        # Exécuter la calibration avec les paramètres CLI
        run_calibration.callback(
            node_id="test_node",
            days=14,
            iterations=iterations,
            output_dir=output_dir,
            from_file=input,
            granularity="daily",
            config_file=None,
            replay=None,
            stability_check=False,
            robust_test=False,
            noise_level=0.2,
            missing_rate=0.2
        )
        
        # Charger les paramètres calibrés
        result_file = Path(output_dir) / "calibrated_params.json"
        if result_file.exists():
            with open(result_file, 'r') as f:
                calibrated = json.load(f)
                
            calibrated_params = calibrated.get("params", {})
            
            # Comparer les paramètres calibrés avec les paramètres connus
            print("\nComparaison des paramètres calibrés avec les paramètres connus:")
            print(f"{'Paramètre':<30} {'Valeur connue':<15} {'Valeur calibrée':<15} {'Diff %':<10}")
            print("-" * 70)
            
            for param, known_value in known_params.items():
                calibrated_value = calibrated_params.get(param, 0)
                if known_value == 0:
                    diff_pct = "N/A"
                else:
                    diff_pct = abs(calibrated_value - known_value) / abs(known_value) * 100
                    diff_pct = f"{diff_pct:.2f}%"
                
                print(f"{param:<30} {known_value:<15.4f} {calibrated_value:<15.4f} {diff_pct:<10}")
    
    @cli.command("full")
    @click.option('--output-dir', default='data/test/calibration_results', 
                help='Répertoire pour les résultats')
    @click.option('--iterations', default=20, help='Nombre d\'itérations de calibration')
    @click.option('--days', default=14, help='Nombre de jours de données')
    @click.option('--channels', default=5, help='Nombre de canaux à simuler')
    def full_cmd(output_dir, iterations, days, channels):
        """Génère des données de test et exécute la calibration"""
        # Générer les données de test
        test_data_path = 'data/test/calibration_test_data.json'
        generate_test_data(test_data_path, days, channels)
        
        # Exécuter la calibration
        test_cmd.callback(test_data_path, output_dir, iterations)
    
    @cli.command("robust")
    @click.option('--output-dir', default='data/test/calibration_robust_test', 
                help='Répertoire pour les résultats')
    @click.option('--iterations', default=20, help='Nombre d\'itérations de calibration')
    @click.option('--noise-level', default=0.2, help='Niveau de bruit (0-1)')
    @click.option('--missing-rate', default=0.2, help='Taux de données manquantes (0-1)')
    def robust_cmd(output_dir, iterations, noise_level, missing_rate):
        """Teste la robustesse du protocole face à des données bruitées"""
        # Générer des données propres
        clean_data_path = 'data/test/calibration_clean_data.json'
        generate_test_data(clean_data_path)
        
        # Charger et corrompre les données
        with open(clean_data_path, 'r') as f:
            data = json.load(f)
        
        noisy_data = corrupt_data(data, noise_level, missing_rate)
        noisy_data_path = 'data/test/calibration_noisy_data.json'
        
        with open(noisy_data_path, 'w') as f:
            json.dump(noisy_data, f, indent=2)
        
        # Créer le répertoire de sortie
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Exécuter la calibration sur les données propres
        print(f"Exécution de la calibration sur données propres...")
        clean_output_dir = output_path / "clean_calibration"
        clean_output_dir.mkdir(parents=True, exist_ok=True)
        
        run_calibration.callback(
            node_id="clean_test",
            days=14,
            iterations=iterations,
            output_dir=str(clean_output_dir),
            from_file=clean_data_path,
            granularity="daily",
            config_file=None,
            replay=None,
            stability_check=False,
            robust_test=False,
            noise_level=0,
            missing_rate=0
        )
        
        # Exécuter la calibration sur les données bruitées
        print(f"\nExécution de la calibration sur données bruitées...")
        print(f"Niveau de bruit: {noise_level*100:.1f}%, Taux de données manquantes: {missing_rate*100:.1f}%")
        
        noisy_output_dir = output_path / "noisy_calibration"
        noisy_output_dir.mkdir(parents=True, exist_ok=True)
        
        run_calibration.callback(
            node_id="noisy_test",
            days=14,
            iterations=iterations,
            output_dir=str(noisy_output_dir),
            from_file=noisy_data_path,
            granularity="daily",
            config_file=None,
            replay=None,
            stability_check=False,
            robust_test=False,
            noise_level=0,
            missing_rate=0
        )
        
        # Comparer les résultats
        clean_result_file = clean_output_dir / "calibrated_params.json"
        noisy_result_file = noisy_output_dir / "calibrated_params.json"
        
        if clean_result_file.exists() and noisy_result_file.exists():
            with open(clean_result_file, 'r') as f:
                clean_calibrated = json.load(f)
            
            with open(noisy_result_file, 'r') as f:
                noisy_calibrated = json.load(f)
            
            clean_params = clean_calibrated.get("params", {})
            noisy_params = noisy_calibrated.get("params", {})
            
            # Comparer les paramètres
            print("\nComparaison des paramètres calibrés entre données propres et bruitées:")
            print(f"{'Paramètre':<30} {'Valeur propre':<15} {'Valeur bruitée':<15} {'Diff %':<10}")
            print("-" * 70)
            
            param_diffs = []
            for param in clean_params.keys():
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
                    print("VERDICT: TRÈS ROBUSTE (différence < 10%)")
                elif avg_diff < 25:
                    print("VERDICT: MOYENNEMENT ROBUSTE (différence < 25%)")
                else:
                    print("VERDICT: PEU ROBUSTE (différence >= 25%)")
            
            # Générer un rapport de robustesse
            with open(output_path / "robustness_report.md", "w") as f:
                f.write("# Rapport de test de robustesse\n\n")
                f.write(f"## Configuration du test\n\n")
                f.write(f"- **Niveau de bruit**: {noise_level*100:.1f}%\n")
                f.write(f"- **Taux de données manquantes**: {missing_rate*100:.1f}%\n\n")
                
                f.write("## Comparaison des paramètres\n\n")
                f.write(f"| Paramètre | Valeur propre | Valeur bruitée | Différence | \n")
                f.write(f"|-----------|--------------|---------------|------------|\n")
                
                for param in clean_params.keys():
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
                        verdict = "✅ **TRÈS ROBUSTE** (différence < 10%)"
                    elif avg_diff < 25:
                        verdict = "⚠️ **MOYENNEMENT ROBUSTE** (différence < 25%)"
                    else:
                        verdict = "❌ **PEU ROBUSTE** (différence >= 25%)"
                    
                    f.write(f"**Verdict de robustesse**: {verdict}\n")
    
    @cli.command("stability")
    @click.option('--output-dir', default='data/test/calibration_stability_test', 
                help='Répertoire pour les résultats')
    @click.option('--iterations', default=20, help='Nombre d\'itérations de calibration')
    @click.option('--runs', default=5, help='Nombre d\'exécutions pour le test de stabilité')
    def stability_cmd(output_dir, iterations, runs):
        """Teste la stabilité du protocole avec plusieurs exécutions"""
        # Générer des données de test
        test_data_path = 'data/test/calibration_stability_data.json'
        generate_test_data(test_data_path)
        
        # Créer le répertoire de sortie
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Exécuter la calibration plusieurs fois
        results = []
        for i in range(runs):
            print(f"Exécution de calibration {i+1}/{runs}...")
            
            # Utiliser un sous-répertoire pour chaque exécution
            sub_output_dir = output_path / f"stability_run_{i+1}"
            sub_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Exécuter la calibration
            run_calibration.callback(
                node_id=f"stability_test_{i+1}",
                days=14,
                iterations=iterations,
                output_dir=str(sub_output_dir),
                from_file=test_data_path,
                granularity="daily",
                config_file=None,
                replay=None,
                stability_check=False,
                robust_test=False,
                noise_level=0,
                missing_rate=0
            )
            
            # Charger les résultats
            result_file = sub_output_dir / "calibrated_params.json"
            if result_file.exists():
                with open(result_file, 'r') as f:
                    result = json.load(f)
                results.append(result)
        
        # Analyser la stabilité
        if results:
            # Extraire les scores et paramètres
            scores = [r.get("score", 0) for r in results]
            
            # Calculer l'écart-type
            std_dev = np.std(scores)
            mean_score = np.mean(scores)
            
            print(f"\nAnalyse de stabilité:")
            print(f"Score moyen: {mean_score:.6f}")
            print(f"Écart-type: {std_dev:.6f}")
            print(f"Coefficient de variation: {std_dev/mean_score:.2%}")
            
            if std_dev < 0.01:
                print("VERDICT: STABLE (écart-type < 0.01)")
            elif std_dev < 0.05:
                print("VERDICT: MOYENNEMENT STABLE (écart-type < 0.05)")
            else:
                print("VERDICT: INSTABLE (écart-type >= 0.05)")
            
            # Générer un rapport de stabilité
            params_by_run = {}
            for i, result in enumerate(results):
                params = result.get("params", {})
                for param, value in params.items():
                    if param not in params_by_run:
                        params_by_run[param] = []
                    params_by_run[param].append(value)
            
            # Calculer les statistiques de stabilité pour chaque paramètre
            param_stats = {}
            for param, values in params_by_run.items():
                param_stats[param] = {
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "cv": np.std(values) / np.mean(values) if np.mean(values) != 0 else 0,
                    "min": min(values),
                    "max": max(values)
                }
            
            # Afficher les statistiques
            print("\nStatistiques de stabilité des paramètres:")
            print(f"{'Paramètre':<30} {'Moyenne':<10} {'Écart-type':<10} {'CV':<10}")
            print("-" * 60)
            
            for param, stats in param_stats.items():
                print(f"{param:<30} {stats['mean']:<10.4f} {stats['std']:<10.4f} {stats['cv']:<10.2%}")
            
            # Générer le rapport
            with open(output_path / "stability_report.md", "w") as f:
                f.write("# Rapport d'analyse de stabilité\n\n")
                
                f.write("## Stabilité des scores\n\n")
                f.write(f"- **Nombre d'exécutions**: {len(scores)}\n")
                f.write(f"- **Score moyen**: {mean_score:.6f}\n")
                f.write(f"- **Écart-type**: {std_dev:.6f}\n")
                f.write(f"- **Coefficient de variation**: {std_dev/mean_score:.2%}\n\n")
                
                # Verdict sur la stabilité
                if std_dev < 0.01:
                    stability_verdict = "✅ **STABLE** (écart-type < 0.01)"
                elif std_dev < 0.05:
                    stability_verdict = "⚠️ **MOYENNEMENT STABLE** (écart-type < 0.05)"
                else:
                    stability_verdict = "❌ **INSTABLE** (écart-type >= 0.05)"
                
                f.write(f"**Verdict de stabilité**: {stability_verdict}\n\n")
                
                f.write("## Stabilité des paramètres\n\n")
                
                f.write("| Paramètre | Moyenne | Écart-type | CV | Min | Max |\n")
                f.write("|-----------|---------|------------|-------|-----|-----|\n")
                
                for param, stats in param_stats.items():
                    f.write(
                        f"| {param} | {stats['mean']:.6f} | {stats['std']:.6f} | "
                        f"{stats['cv']:.2%} | {stats['min']:.6f} | {stats['max']:.6f} |\n"
                    )
    
    cli() 