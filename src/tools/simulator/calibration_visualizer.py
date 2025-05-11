#!/usr/bin/env python3
"""
Visualisateur automatique pour le processus de calibration.
Ce module génère automatiquement des visualisations pour les résultats de calibration.

Dernière mise à jour: 8 mai 2025
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
from typing import Dict, Any, List
from scipy import stats
from scipy.spatial import distance

from .calibration_metrics import CalibrationMetrics
from .calibration_engine import CalibrationConfig

# Configuration pour les visualisations
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("Set2")


def generate_run_dashboard(run_id: str, 
                         real_dist: Dict[str, np.ndarray],
                         sim_dist: Dict[str, np.ndarray], 
                         divergences: Dict[str, float],
                         params: Dict[str, float],
                         p_values: Dict[str, float],
                         output_dir: str) -> str:
    """
    Génère un tableau de bord complet pour un run de calibration
    
    Args:
        run_id: Identifiant du run
        real_dist: Distributions réelles
        sim_dist: Distributions simulées
        divergences: Divergences calculées
        params: Paramètres utilisés
        p_values: P-values calculées
        output_dir: Répertoire de sortie
    
    Returns:
        Chemin du tableau de bord
    """
    # Créer le répertoire du tableau de bord
    dash_dir = Path(output_dir) / f"dashboard_{run_id}"
    dash_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Histogrammes croisés pour toutes les métriques
    for metric_name, real_values in real_dist.items():
        if metric_name not in sim_dist:
            continue
            
        sim_values = sim_dist[metric_name]
        
        # Obtenir la configuration de la métrique
        metrics = CalibrationMetrics()
        metric_config = metrics.get_metric_config(metric_name)
        
        if metric_config is None:
            continue
        
        # Créer la figure
        plt.figure(figsize=(12, 8))
        
        # Choisir les bins appropriés
        if metric_config.bins is not None:
            bins = metric_config.bins
        else:
            # Si pas de bins définis, utiliser l'union des valeurs
            all_values = np.concatenate([real_values, sim_values])
            bins = np.linspace(np.min(all_values), np.max(all_values), 20)
        
        # Tracer les histogrammes
        plt.hist(real_values, bins=bins, alpha=0.7, label="Données réelles", color="blue")
        plt.hist(sim_values, bins=bins, alpha=0.7, label="Données simulées", color="orange")
        
        # Ajouter les informations de test statistique
        if metric_name in p_values:
            p_value = p_values[metric_name]
            verdict = "Indistinguable" if p_value > 0.05 else "Distinguable"
            plt.title(f"{metric_config.description}\np-value: {p_value:.4f} ({verdict})", fontsize=14)
        else:
            plt.title(f"{metric_config.description}", fontsize=14)
        
        plt.xlabel("Valeur", fontsize=12)
        plt.ylabel("Fréquence", fontsize=12)
        plt.legend(fontsize=12)
        
        # Sauvegarder
        plt.tight_layout()
        plt.savefig(dash_dir / f"{metric_name}_histogram.png", dpi=300)
        plt.close()
    
    # 2. Courbes temporelles pour métriques spécifiques (si disponibles)
    if "liquidity_ratio_evolution" in real_dist and "liquidity_ratio_evolution" in sim_dist:
        plt.figure(figsize=(12, 6))
        
        # Utiliser des approximations de densité de kernel
        real_values = real_dist["liquidity_ratio_evolution"]
        sim_values = sim_dist["liquidity_ratio_evolution"]
        
        sns.kdeplot(real_values, label="Données réelles", color="blue")
        sns.kdeplot(sim_values, label="Données simulées", color="orange")
        
        plt.title("Distribution des variations de ratio de liquidité", fontsize=14)
        plt.xlabel("Variation du ratio", fontsize=12)
        plt.ylabel("Densité", fontsize=12)
        plt.legend(fontsize=12)
        
        plt.tight_layout()
        plt.savefig(dash_dir / "liquidity_ratio_kde.png", dpi=300)
        plt.close()
    
    # 3. Heatmap des divergences
    plt.figure(figsize=(10, 8))
    
    # Préparer les données pour la heatmap
    divergence_df = pd.DataFrame({
        'métrique': list(divergences.keys()),
        'divergence': list(divergences.values())
    })
    
    # Obtenir les seuils de divergence
    metrics = CalibrationMetrics()
    thresholds = {}
    for metric_name in divergences.keys():
        config = metrics.get_metric_config(metric_name)
        if config:
            thresholds[metric_name] = config.threshold
    
    # Ajouter les seuils et verdicts
    divergence_df['seuil'] = divergence_df['métrique'].map(thresholds)
    divergence_df['verdict'] = divergence_df.apply(
        lambda row: 'Conforme' if row['divergence'] < row['seuil'] else 'Non conforme', 
        axis=1
    )
    
    # Créer un pivot pour la heatmap
    pivot_df = divergence_df.pivot_table(
        index='métrique', 
        values=['divergence', 'seuil'],
        aggfunc='first'
    ).reset_index()
    
    # Tracer la heatmap
    fig, ax = plt.subplots(figsize=(8, len(divergences) * 0.8 + 2))
    
    # Utiliser un dégradé de couleurs vert à rouge
    cmap = sns.diverging_palette(145, 10, as_cmap=True)
    
    # Tracer la barre horizontale pour chaque métrique
    for i, row in pivot_df.iterrows():
        metric = row['métrique']
        div_value = row['divergence']
        threshold = row['seuil']
        
        # Normaliser la valeur sur une échelle 0-1
        normalized_value = min(1.0, div_value / max(1.0, threshold * 2))
        
        # Couleur basée sur la comparaison avec le seuil
        color = cmap(normalized_value)
        
        # Tracer la barre
        ax.barh([i], [div_value], color=color)
        
        # Ajouter une ligne pour le seuil
        ax.axvline(x=threshold, ymin=(i/len(pivot_df)), ymax=((i+1)/len(pivot_df)), 
                  color='black', linestyle='--', alpha=0.5)
        
        # Ajouter le texte
        ax.text(div_value + 0.02, i, f"{div_value:.4f}", va='center')
    
    # Configuration de l'axe
    ax.set_yticks(range(len(pivot_df)))
    ax.set_yticklabels(pivot_df['métrique'])
    ax.set_title("Divergences par métrique vs seuils", fontsize=14)
    ax.set_xlabel("Divergence", fontsize=12)
    
    plt.tight_layout()
    plt.savefig(dash_dir / "divergences_chart.png", dpi=300)
    plt.close()
    
    # 4. Résumé des paramètres
    plt.figure(figsize=(10, 6))
    
    param_df = pd.DataFrame({
        'paramètre': list(params.keys()),
        'valeur': list(params.values())
    })
    
    # Tracer les barres pour les valeurs des paramètres
    bars = sns.barplot(x='paramètre', y='valeur', data=param_df)
    
    # Ajouter les valeurs au-dessus des barres
    for i, p in enumerate(bars.patches):
        bars.annotate(f"{p.get_height():.4f}", 
                     (p.get_x() + p.get_width() / 2., p.get_height()),
                     ha='center', va='center', xytext=(0, 10), 
                     textcoords='offset points')
    
    plt.title("Paramètres optimaux", fontsize=14)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(dash_dir / "parameters.png", dpi=300)
    plt.close()
    
    # 5. Génération du rapport markdown
    generate_markdown_report(
        run_id=run_id,
        params=params,
        p_values=p_values,
        divergences=divergences,
        dashboard_path=dash_dir
    )
    
    return str(dash_dir)


def generate_markdown_report(run_id: str, 
                           params: Dict[str, float], 
                           p_values: Dict[str, float],
                           divergences: Dict[str, float],
                           dashboard_path: Path) -> None:
    """
    Génère un rapport markdown pour le tableau de bord
    
    Args:
        run_id: Identifiant du run
        params: Paramètres optimaux
        p_values: P-values
        divergences: Divergences
        dashboard_path: Chemin du tableau de bord
    """
    with open(dashboard_path / "rapport.md", "w") as f:
        f.write(f"# Rapport de calibration {run_id}\n\n")
        
        # 1. Résumé des résultats
        f.write("## Résumé des résultats\n\n")
        
        # Calculer le verdict global
        all_pass = all(p > 0.05 for p in p_values.values())
        verdict = "✅ **CALIBRATION RÉUSSIE**" if all_pass else "❌ **CALIBRATION ÉCHOUÉE**"
        
        f.write(f"{verdict}\n\n")
        f.write("### Tests statistiques d'indistinguabilité\n\n")
        f.write("| Métrique | p-value | Verdict |\n")
        f.write("|----------|---------|--------|\n")
        
        for metric, p_value in p_values.items():
            metric_verdict = "✅ Indistinguable" if p_value > 0.05 else "❌ Distinguable"
            f.write(f"| {metric} | {p_value:.4f} | {metric_verdict} |\n")
        
        # 2. Visualisations
        f.write("\n## Visualisations\n\n")
        
        # Histogrammes
        f.write("### Distributions\n\n")
        for image in dashboard_path.glob("*_histogram.png"):
            metric_name = image.stem.replace("_histogram", "")
            f.write(f"#### {metric_name}\n\n")
            f.write(f"![{metric_name}](./{image.name})\n\n")
        
        # Divergences
        f.write("### Divergences\n\n")
        f.write("![Divergences](./divergences_chart.png)\n\n")
        
        # Paramètres
        f.write("### Paramètres optimaux\n\n")
        f.write("![Paramètres](./parameters.png)\n\n")
        
        f.write("| Paramètre | Valeur |\n")
        f.write("|-----------|-------|\n")
        for param, value in params.items():
            f.write(f"| {param} | {value:.6f} |\n")
        
        # 3. Configuration de la calibration
        f.write("\n## Configuration de la calibration\n\n")
        f.write(f"- **Granularité temporelle**: {CalibrationConfig.TIME_GRANULARITY}\n")
        f.write(f"- **Nombre de jours simulés**: {CalibrationConfig.SIMULATION_TICKS}\n")
        f.write(f"- **Exécutions par jeu de paramètres**: {CalibrationConfig.SAMPLES_PER_PARAM_SET}\n")


def plot_stability_analysis(stability_results: List[Dict[str, Any]], output_dir: str) -> None:
    """
    Génère des visualisations pour l'analyse de stabilité
    
    Args:
        stability_results: Résultats des exécutions de stabilité
        output_dir: Répertoire de sortie
    """
    # Créer le répertoire si nécessaire
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Collecter les scores totaux
    scores = [r.get('score', 0) for r in stability_results]
    
    # 1. Tracer l'évolution des scores
    plt.figure(figsize=(10, 6))
    plt.plot(range(1, len(scores) + 1), scores, 'o-', linewidth=2)
    plt.axhline(y=np.mean(scores), color='r', linestyle='--', label=f"Moyenne: {np.mean(scores):.4f}")
    
    # Ajouter l'écart-type
    std_dev = np.std(scores)
    plt.fill_between(
        range(1, len(scores) + 1),
        np.mean(scores) - std_dev,
        np.mean(scores) + std_dev,
        alpha=0.2, color='r',
        label=f"Écart-type: {std_dev:.4f}"
    )
    
    plt.title("Stabilité des scores de calibration", fontsize=14)
    plt.xlabel("Exécution", fontsize=12)
    plt.ylabel("Score total (divergence)", fontsize=12)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path / "stability_scores.png", dpi=300)
    plt.close()
    
    # 2. Stabilité des paramètres
    if len(stability_results) > 0 and 'params' in stability_results[0]:
        # Collecter les valeurs de paramètres
        param_values = {}
        for param in stability_results[0]['params'].keys():
            param_values[param] = [r['params'].get(param, 0) for r in stability_results]
        
        # Calculer les statistiques
        param_stats = {}
        for param, values in param_values.items():
            param_stats[param] = {
                'mean': np.mean(values),
                'std': np.std(values),
                'cv': np.std(values) / np.mean(values) if np.mean(values) != 0 else 0,
                'min': np.min(values),
                'max': np.max(values)
            }
        
        # Tracer la distribution des paramètres
        plt.figure(figsize=(14, 4 * len(param_values)))
        
        for i, (param, values) in enumerate(param_values.items()):
            plt.subplot(len(param_values), 1, i+1)
            
            # Box plot
            plt.boxplot(values, vert=False, widths=0.7)
            
            # Ajouter les points individuels
            plt.scatter(values, [1] * len(values), color='blue', alpha=0.6)
            
            # Ajouter les statistiques
            stats_text = (
                f"Moyenne: {param_stats[param]['mean']:.4f}, "
                f"Écart-type: {param_stats[param]['std']:.4f}, "
                f"CV: {param_stats[param]['cv']:.2%}"
            )
            plt.title(f"{param} - {stats_text}", fontsize=12)
            
            plt.grid(True, axis='x')
            plt.tight_layout()
        
        plt.savefig(output_path / "parameter_stability.png", dpi=300)
        plt.close()
        
        # 3. Tableau des statistiques de paramètres
        stats_df = pd.DataFrame.from_dict(param_stats, orient='index')
        stats_df.to_csv(output_path / "parameter_stats.csv")
        
        # 4. Générer un rapport de stabilité
        with open(output_path / "stability_report.md", "w") as f:
            f.write("# Rapport d'analyse de stabilité\n\n")
            
            f.write("## Stabilité des scores\n\n")
            f.write(f"- **Nombre d'exécutions**: {len(scores)}\n")
            f.write(f"- **Score moyen**: {np.mean(scores):.6f}\n")
            f.write(f"- **Écart-type**: {std_dev:.6f}\n")
            f.write(f"- **Coefficient de variation**: {std_dev/np.mean(scores):.2%}\n\n")
            
            # Verdict sur la stabilité
            if std_dev < 0.01:
                stability_verdict = "✅ **STABLE** (écart-type < 0.01)"
            elif std_dev < 0.05:
                stability_verdict = "⚠️ **MOYENNEMENT STABLE** (écart-type < 0.05)"
            else:
                stability_verdict = "❌ **INSTABLE** (écart-type >= 0.05)"
            
            f.write(f"**Verdict de stabilité**: {stability_verdict}\n\n")
            
            f.write("![Stabilité des scores](./stability_scores.png)\n\n")
            
            f.write("## Stabilité des paramètres\n\n")
            
            f.write("| Paramètre | Moyenne | Écart-type | CV | Min | Max |\n")
            f.write("|-----------|---------|------------|-------|-----|-----|\n")
            
            for param, stats in param_stats.items():
                f.write(
                    f"| {param} | {stats['mean']:.6f} | {stats['std']:.6f} | "
                    f"{stats['cv']:.2%} | {stats['min']:.6f} | {stats['max']:.6f} |\n"
                )
            
            f.write("\n![Stabilité des paramètres](./parameter_stability.png)\n\n")
            
            # Recommandations
            f.write("## Recommandations\n\n")
            
            if std_dev < 0.01:
                f.write("- La calibration est très stable, vous pouvez utiliser ces paramètres avec confiance.\n")
            elif std_dev < 0.05:
                f.write("- La calibration est modérément stable. Considérez augmenter le nombre d'échantillons par paramètre pour améliorer la stabilité.\n")
            else:
                f.write("- La calibration est instable. Vérifiez les données d'entrée et considérez :\n")
                f.write("  - Augmenter le nombre d'échantillons par paramètre\n")
                f.write("  - Réduire les plages de paramètres pour affiner la recherche\n")
                f.write("  - Vérifier la qualité et la cohérence des données d'entrée\n") 