#!/usr/bin/env python3
"""
Interface en ligne de commande pour le processus de calibration.
Ce module fournit un CLI pour exécuter le processus de calibration et visualiser les résultats.

Dernière mise à jour: 8 mai 2025
"""

import click
import numpy as np
import json
import os
import logging
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from scipy import stats
from scipy.spatial import distance
import hashlib

from .calibration_engine import CalibrationEngine, CalibrationConfig, CALIBRATION_RESULTS_PATH, CALIBRATION_ARCHIVE_PATH
from .calibration_metrics import CalibrationMetrics
from .calibration_visualizer import generate_run_dashboard, plot_stability_analysis

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("calibration_cli")

# Chemin pour stocker les résultats
RESULTS_PATH = Path("data/calibration")


class RealNodeDataCollector:
    """
    Collecte des données réelles à partir de LNBits ou d'autres sources
    """
    
    def collect_from_lnbits(self, node_id: str, days: int) -> Dict[str, Any]:
        """
        Collecte des données à partir de LNBits
        
        Args:
            node_id: ID du nœud à collecter
            days: Nombre de jours à collecter
            
        Returns:
            Données collectées
        """
        # Cette méthode devrait être implémentée pour collecter des données réelles
        # Pour l'instant, elle retourne des données factices
        
        logger.warning("Méthode de collecte réelle non implémentée, utilisation de données factices")
        
        # Générer des données factices pour démonstration
        from .simulation_fixtures import SimulationFixtures
        fixtures = SimulationFixtures()
        
        # Générer un réseau avec 5 canaux
        network = fixtures.generate_test_network(5)
        
        # Structurer les données comme si elles venaient de LNBits
        channel_data = {}
        for channel in network["channels"]:
            channel_id = channel["channel_id"]
            
            # Générer un historique de 14 jours
            history = []
            for day in range(days):
                # Calculer des métriques avec un peu de variation aléatoire
                forward_amount = channel["avg_daily_volume"] * (0.8 + 0.4 * np.random.random())
                success_rate = channel["success_rate_base"] * (0.9 + 0.2 * np.random.random())
                local_balance = channel["local_balance"] * (0.9 + 0.2 * np.random.random())
                
                # Ajouter à l'historique
                timestamp = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                timestamp = timestamp.replace(day=timestamp.day - day)
                
                history.append({
                    "timestamp": timestamp.isoformat(),
                    "forward_amount": forward_amount,
                    "forward_success": success_rate,
                    "local_balance": local_balance,
                    "capacity": channel["capacity"]
                })
            
            channel_data[channel_id] = history
        
        return channel_data
    
    def collect_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Charge des données à partir d'un fichier JSON
        
        Args:
            file_path: Chemin vers le fichier
            
        Returns:
            Données chargées
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données: {str(e)}")
            return {}
    
    def corrupt_data(self, data: Dict[str, Any], noise_level: float = 0.2, 
                   missing_rate: float = 0.2) -> Dict[str, Any]:
        """
        Corrompt les données avec du bruit et des valeurs manquantes
        
        Args:
            data: Données à corrompre
            noise_level: Niveau de bruit (0-1)
            missing_rate: Taux de données manquantes (0-1)
            
        Returns:
            Données corrompues
        """
        corrupted_data = {}
        
        for channel_id, channel_data in data.items():
            if not isinstance(channel_data, list):
                corrupted_data[channel_id] = channel_data
                continue
            
            corrupted_channel = []
            
            for record in channel_data:
                # Copier le record
                new_record = record.copy()
                
                # Ajouter du bruit aux métriques numériques
                for key, value in record.items():
                    if key == "timestamp":
                        continue
                        
                    if isinstance(value, (int, float)):
                        # Randomiser si on corrompt cette valeur
                        if np.random.random() < noise_level:
                            # Ajouter un bruit gaussien
                            noise = np.random.normal(0, 0.2 * value)
                            new_record[key] = max(0, value + noise)
                        
                        # Randomiser si on supprime cette valeur
                        if np.random.random() < missing_rate:
                            new_record[key] = None
                
                corrupted_channel.append(new_record)
            
            # Randomiser si on supprime des enregistrements complets
            if np.random.random() < missing_rate and len(corrupted_channel) > 2:
                # Supprimer une portion aléatoire des enregistrements
                num_to_remove = int(missing_rate * len(corrupted_channel))
                indices_to_remove = np.random.choice(
                    range(len(corrupted_channel)), 
                    size=num_to_remove, 
                    replace=False
                )
                
                corrupted_channel = [r for i, r in enumerate(corrupted_channel) 
                                  if i not in indices_to_remove]
            
            corrupted_data[channel_id] = corrupted_channel
        
        return corrupted_data


def generate_param_ranges_from_config(config_file: str = None) -> Dict[str, np.ndarray]:
    """
    Génère les plages de paramètres à partir d'un fichier de configuration ou utilise des valeurs par défaut
    
    Args:
        config_file: Chemin vers le fichier de configuration
        
    Returns:
        Plages de paramètres
    """
    default_ranges = {
        "fee_elasticity": np.linspace(-0.8, -0.2, 10),  # 10 valeurs de -0.8 à -0.2
        "volume_trend_drift": np.linspace(-0.05, 0.05, 5),  # 5 valeurs de -0.05 à 0.05
        "liquidity_pressure_amplitude": np.linspace(0.1, 0.3, 5),  # 5 valeurs de 0.1 à 0.3
        "success_rate_base": np.linspace(0.8, 0.98, 5),  # 5 valeurs de 0.8 à 0.98
        "noise_level": np.linspace(0.05, 0.2, 4)  # 4 valeurs de 0.05 à 0.2
    }
    
    if not config_file:
        return default_ranges
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        if 'param_ranges' not in config:
            logger.warning("Pas de plages de paramètres trouvées dans le fichier de configuration")
            return default_ranges
        
        param_ranges = {}
        for param, range_config in config['param_ranges'].items():
            if all(k in range_config for k in ['min', 'max', 'steps']):
                param_ranges[param] = np.linspace(
                    range_config['min'],
                    range_config['max'],
                    range_config['steps']
                )
            else:
                logger.warning(f"Configuration invalide pour {param}, utilisation des valeurs par défaut")
                param_ranges[param] = default_ranges.get(param, np.linspace(0, 1, 10))
        
        # S'assurer que tous les paramètres par défaut sont présents
        for param, values in default_ranges.items():
            if param not in param_ranges:
                param_ranges[param] = values
        
        return param_ranges
    
    except Exception as e:
        logger.error(f"Erreur lors du chargement du fichier de configuration: {str(e)}")
        return default_ranges


def save_calibrated_params(params: Dict[str, float], final_p_value: float, 
                         node_id: str, output_dir: str) -> None:
    """
    Sauvegarde les paramètres calibrés dans un format utilisable
    
    Args:
        params: Paramètres calibrés
        final_p_value: P-valeur du test final
        node_id: ID du nœud
        output_dir: Répertoire de sortie
    """
    result = {
        "node_id": node_id,
        "timestamp": datetime.now().isoformat(),
        "params": params,
        "final_p_value": final_p_value,
        "valid": final_p_value > 0.05,
        "calibration_config": {
            "time_granularity": CalibrationConfig.TIME_GRANULARITY,
            "simulation_ticks": CalibrationConfig.SIMULATION_TICKS,
            "convergence_threshold": CalibrationConfig.CONVERGENCE_THRESHOLD
        }
    }
    
    # Sauvegarder au format JSON
    output_path = Path(output_dir) / "calibrated_params.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Paramètres calibrés sauvegardés dans {output_path}")


def run_calibration_process(
        node_id: str,
        data: Dict[str, Any],
        param_ranges: Dict[str, np.ndarray],
        iterations: int,
        output_dir: str,
        granularity: str) -> Dict[str, Any]:
    """
    Exécute le processus de calibration complet
    
    Args:
        node_id: ID du nœud
        data: Données d'entrée
        param_ranges: Plages de paramètres
        iterations: Nombre d'itérations
        output_dir: Répertoire de sortie
        granularity: Granularité temporelle
        
    Returns:
        Résultats de la calibration
    """
    # Mettre à jour la configuration
    CalibrationConfig.TIME_GRANULARITY = granularity
    
    # Initialiser le moteur de calibration
    engine = CalibrationEngine(node_id=node_id)
    
    # Exécuter la calibration
    best_params, best_score = engine.calibrate_simulator(data, param_ranges, iterations)
    
    # Extraire les distributions réelles et simulées pour les visualisations
    processed_data = engine._preprocess_node_data(data)
    real_dist = engine._extract_distributions(processed_data)
    
    # Exécuter une simulation avec les meilleurs paramètres pour les visualisations finales
    from .stochastic_simulator import LightningSimEnvironment
    
    sim_config = {
        "simulation_days": CalibrationConfig.SIMULATION_TICKS,
        "network_size": len(processed_data) if isinstance(processed_data, dict) else 5,
        "time_granularity": granularity,
        **best_params
    }
    
    simulator = LightningSimEnvironment(sim_config)
    simulator.initialize_evolution_engines()
    dummy_engine = None
    final_sim_data = simulator.run_simulation(steps=CalibrationConfig.SIMULATION_TICKS, decision_engine=dummy_engine)
    
    # Extraire les distributions simulées
    sim_dist = engine._extract_distributions(final_sim_data)
    
    # Calculer les divergences finales
    divergences = engine._calculate_divergences(real_dist, sim_dist)
    
    # Extraire les p-values
    p_values = engine.final_p_values
    
    # Test de Kolmogorov-Smirnov sur la distribution des forwards comme test final
    final_p_value = 0
    if "forward_volume_distribution" in real_dist and "forward_volume_distribution" in sim_dist:
        real_forwards = real_dist["forward_volume_distribution"]
        sim_forwards = sim_dist["forward_volume_distribution"]
        
        if len(real_forwards) > 1 and len(sim_forwards) > 1:
            _, p_value = stats.ks_2samp(real_forwards, sim_forwards)
            final_p_value = p_value
            
            click.echo(f"Test KS final sur volumes: statistique={_:.4f}, p-value={p_value:.4f}")
            click.echo(f"Distribution {'indistinguable' if p_value > 0.05 else 'distinguable'} (seuil: 0.05)")
    
    # Générer le tableau de bord de visualisation
    run_id = f"calibration_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{node_id}"
    dashboard_path = generate_run_dashboard(
        run_id=run_id,
        real_dist=real_dist,
        sim_dist=sim_dist,
        divergences=divergences,
        params=best_params,
        p_values=p_values,
        output_dir=output_dir
    )
    
    click.echo(f"Tableau de bord généré dans {dashboard_path}")
    
    # Sauvegarder les paramètres calibrés
    save_calibrated_params(best_params, final_p_value, node_id, output_dir)
    
    click.echo(f"Calibration terminée. Paramètres optimaux: {best_params}")
    
    return {
        "run_id": run_id,
        "params": best_params,
        "score": best_score,
        "p_values": p_values,
        "divergences": divergences,
        "final_p_value": final_p_value
    }


@click.command()
@click.option('--node-id', required=True, help='ID du nœud à analyser')
@click.option('--days', default=14, help='Nombre de jours de données à collecter')
@click.option('--iterations', default=100, help='Nombre maximum d\'itérations de calibration')
@click.option('--output-dir', default='data/calibration_results', help='Répertoire pour les résultats')
@click.option('--from-file', help='Chemin vers un fichier de données (au lieu de collecter en direct)')
@click.option('--granularity', type=click.Choice(['hourly', 'daily', 'weekly']), default='daily',
             help='Granularité temporelle pour l\'analyse')
@click.option('--config-file', help='Fichier de configuration pour les plages de paramètres')
@click.option('--replay', help='ID d\'une calibration précédente à rejouer')
@click.option('--stability-check', is_flag=True, help='Exécuter 5 fois et vérifier la stabilité')
@click.option('--robust-test', is_flag=True, help='Tester avec des données bruitées et manquantes')
@click.option('--noise-level', default=0.2, help='Niveau de bruit pour le test de robustesse (0-1)')
@click.option('--missing-rate', default=0.2, help='Taux de données manquantes pour le test de robustesse (0-1)')
def run_calibration(
        node_id, days, iterations, output_dir, from_file, granularity, 
        config_file, replay, stability_check, robust_test, noise_level, missing_rate):
    """Exécute le processus de calibration complet."""
    
    # Créer le répertoire de sortie
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 1. Mode Replay: Rejouer une calibration précédente
    if replay:
        click.echo(f"Mode Replay: Chargement de la calibration {replay}")
        
        # Charger la calibration
        engine = CalibrationEngine()
        calibration_data = engine.load_calibration(replay)
        
        if not calibration_data:
            click.echo(f"Erreur: Calibration {replay} non trouvée")
            return
        
        # Utiliser les paramètres de la calibration précédente
        if 'params' in calibration_data:
            best_params = calibration_data['params']
            
            # Collecter des données pour comparer
            collector = RealNodeDataCollector()
            
            if from_file:
                click.echo(f"Chargement des données depuis {from_file}...")
                real_data = collector.collect_from_file(from_file)
            else:
                click.echo(f"Collecte des données du nœud {node_id} sur {days} jours...")
                real_data = collector.collect_from_lnbits(node_id, days)
            
            # Configuration du simulateur avec les paramètres chargés
            CalibrationConfig.TIME_GRANULARITY = calibration_data.get('simulation_config', {}).get('time_granularity', granularity)
            
            # Prétraiter les données
            engine = CalibrationEngine(node_id=node_id)
            processed_data = engine._preprocess_node_data(real_data)
            real_dist = engine._extract_distributions(processed_data)
            
            # Exécuter la simulation avec les paramètres chargés
            from .stochastic_simulator import LightningSimEnvironment
            sim_config = {
                "simulation_days": days,
                "network_size": len(processed_data) if isinstance(processed_data, dict) else 5,
                "time_granularity": CalibrationConfig.TIME_GRANULARITY,
                **best_params
            }
            
            simulator = LightningSimEnvironment(sim_config)
            simulator.initialize_evolution_engines()
            dummy_engine = None
            final_sim_data = simulator.run_simulation(steps=days, decision_engine=dummy_engine)
            
            # Extraire les distributions simulées
            sim_dist = engine._extract_distributions(final_sim_data)
            
            # Calculer les divergences
            divergences = engine._calculate_divergences(real_dist, sim_dist)
            
            # Test de Kolmogorov-Smirnov pour chaque métrique
            p_values = {}
            for metric_name, real_values in real_dist.items():
                if metric_name not in sim_dist:
                    continue
                    
                sim_values = sim_dist[metric_name]
                
                if len(real_values) < 2 or len(sim_values) < 2:
                    continue
                    
                _, p_value = stats.ks_2samp(real_values, sim_values)
                p_values[metric_name] = p_value
            
            # Générer le tableau de bord
            run_id = f"replay_{replay}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            dashboard_path = generate_run_dashboard(
                run_id=run_id,
                real_dist=real_dist,
                sim_dist=sim_dist,
                divergences=divergences,
                params=best_params,
                p_values=p_values,
                output_dir=output_dir
            )
            
            click.echo(f"Replay terminé. Tableau de bord généré dans {dashboard_path}")
            return
    
    # 2. Mode test de stabilité: Exécuter plusieurs fois et vérifier la variance
    if stability_check:
        click.echo(f"Mode test de stabilité: Exécution de 5 calibrations successives")
        
        # Collecter les données
        collector = RealNodeDataCollector()
        
        if from_file:
            click.echo(f"Chargement des données depuis {from_file}...")
            real_data = collector.collect_from_file(from_file)
        else:
            click.echo(f"Collecte des données du nœud {node_id} sur {days} jours...")
            real_data = collector.collect_from_lnbits(node_id, days)
        
        # Générer les plages de paramètres
        param_ranges = generate_param_ranges_from_config(config_file)
        
        # Exécuter 5 calibrations
        stability_results = []
        for i in range(5):
            click.echo(f"Exécution de calibration {i+1}/5...")
            
            # Utiliser un sous-répertoire pour chaque exécution
            sub_output_dir = output_path / f"stability_run_{i+1}"
            sub_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Exécuter la calibration
            result = run_calibration_process(
                node_id=f"{node_id}_stability_{i+1}",
                data=real_data,
                param_ranges=param_ranges,
                iterations=iterations,
                output_dir=str(sub_output_dir),
                granularity=granularity
            )
            
            stability_results.append(result)
        
        # Générer les visualisations d'analyse de stabilité
        stability_output_dir = output_path / "stability_analysis"
        plot_stability_analysis(stability_results, str(stability_output_dir))
        
        # Calculer l'écart-type des scores
        scores = [r['score'] for r in stability_results]
        std_dev = np.std(scores)
        
        click.echo(f"Analyse de stabilité terminée. Écart-type des scores: {std_dev:.6f}")
        click.echo(f"Résultats sauvegardés dans {stability_output_dir}")
        
        if std_dev < 0.01:
            click.echo("VERDICT: STABLE (écart-type < 0.01)")
        elif std_dev < 0.05:
            click.echo("VERDICT: MOYENNEMENT STABLE (écart-type < 0.05)")
        else:
            click.echo("VERDICT: INSTABLE (écart-type >= 0.05)")
        
        return
    
    # 3. Mode test de robustesse: Tester avec des données bruitées
    if robust_test:
        click.echo(f"Mode test de robustesse: Test avec données bruitées et manquantes")
        click.echo(f"Niveau de bruit: {noise_level*100:.1f}%, Taux de données manquantes: {missing_rate*100:.1f}%")
        
        # Collecter les données de base
        collector = RealNodeDataCollector()
        
        if from_file:
            click.echo(f"Chargement des données depuis {from_file}...")
            clean_data = collector.collect_from_file(from_file)
        else:
            click.echo(f"Collecte des données du nœud {node_id} sur {days} jours...")
            clean_data = collector.collect_from_lnbits(node_id, days)
        
        # Créer une copie corrompue des données
        noisy_data = collector.corrupt_data(clean_data, noise_level, missing_rate)
        
        # Sauvegarder les données propres et bruitées pour référence
        with open(output_path / "clean_data.json", "w") as f:
            json.dump(clean_data, f, indent=2)
            
        with open(output_path / "noisy_data.json", "w") as f:
            json.dump(noisy_data, f, indent=2)
        
        # Générer les plages de paramètres
        param_ranges = generate_param_ranges_from_config(config_file)
        
        # Exécuter la calibration sur les données propres
        click.echo("Calibration sur données propres...")
        clean_output_dir = output_path / "clean_calibration"
        clean_output_dir.mkdir(parents=True, exist_ok=True)
        
        clean_result = run_calibration_process(
            node_id=f"{node_id}_clean",
            data=clean_data,
            param_ranges=param_ranges,
            iterations=iterations,
            output_dir=str(clean_output_dir),
            granularity=granularity
        )
        
        # Exécuter la calibration sur les données bruitées
        click.echo("Calibration sur données bruitées...")
        noisy_output_dir = output_path / "noisy_calibration"
        noisy_output_dir.mkdir(parents=True, exist_ok=True)
        
        noisy_result = run_calibration_process(
            node_id=f"{node_id}_noisy",
            data=noisy_data,
            param_ranges=param_ranges,
            iterations=iterations,
            output_dir=str(noisy_output_dir),
            granularity=granularity
        )
        
        # Comparer les résultats
        click.echo("\nComparaison des résultats:")
        click.echo(f"{'Paramètre':<25} {'Valeur propre':<15} {'Valeur bruitée':<15} {'Différence %':<10}")
        click.echo("-" * 65)
        
        param_diffs = []
        for param in clean_result['params'].keys():
            clean_val = clean_result['params'].get(param, 0)
            noisy_val = noisy_result['params'].get(param, 0)
            
            if clean_val == 0:
                diff_pct = "N/A"
            else:
                diff_pct = abs(noisy_val - clean_val) / abs(clean_val) * 100
                param_diffs.append(diff_pct)
                diff_pct = f"{diff_pct:.2f}%"
            
            click.echo(f"{param:<25} {clean_val:<15.4f} {noisy_val:<15.4f} {diff_pct:<10}")
        
        # Calculer la différence moyenne
        if param_diffs:
            avg_diff = np.mean(param_diffs)
            click.echo(f"\nDifférence moyenne des paramètres: {avg_diff:.2f}%")
            
            if avg_diff < 10:
                click.echo("VERDICT: TRÈS ROBUSTE (différence < 10%)")
            elif avg_diff < 25:
                click.echo("VERDICT: MOYENNEMENT ROBUSTE (différence < 25%)")
            else:
                click.echo("VERDICT: PEU ROBUSTE (différence >= 25%)")
        
        # Sauvegarder le rapport de robustesse
        with open(output_path / "robustness_report.md", "w") as f:
            f.write("# Rapport de test de robustesse\n\n")
            f.write(f"## Configuration du test\n\n")
            f.write(f"- **Niveau de bruit**: {noise_level*100:.1f}%\n")
            f.write(f"- **Taux de données manquantes**: {missing_rate*100:.1f}%\n\n")
            
            f.write("## Comparaison des paramètres\n\n")
            f.write(f"| Paramètre | Valeur propre | Valeur bruitée | Différence | \n")
            f.write(f"|-----------|--------------|---------------|------------|\n")
            
            for param in clean_result['params'].keys():
                clean_val = clean_result['params'].get(param, 0)
                noisy_val = noisy_result['params'].get(param, 0)
                
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
        
        return
    
    # 4. Mode normal: Calibration standard
    # Collecter les données
    collector = RealNodeDataCollector()
    
    if from_file:
        click.echo(f"Chargement des données depuis {from_file}...")
        real_data = collector.collect_from_file(from_file)
    else:
        click.echo(f"Collecte des données du nœud {node_id} sur {days} jours...")
        real_data = collector.collect_from_lnbits(node_id, days)
    
    # Générer les plages de paramètres
    param_ranges = generate_param_ranges_from_config(config_file)
    
    # Exécuter la calibration
    run_calibration_process(
        node_id=node_id,
        data=real_data,
        param_ranges=param_ranges,
        iterations=iterations,
        output_dir=output_dir,
        granularity=granularity
    )


if __name__ == "__main__":
    run_calibration() 