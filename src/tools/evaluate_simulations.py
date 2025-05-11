#!/usr/bin/env python3
# coding: utf-8
"""
Script d'évaluation comparative des simulations de nœuds Lightning.
Ce script analyse les simulations générées pour différents profils de nœuds
et produit une analyse détaillée avec recommandations.

Dernière mise à jour: 10 mai 2025
"""

import json
import os
import glob
import csv
import pandas as pd
import numpy as np
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Configuration du logging
logger = logging.getLogger("evaluate_simulations")

# Chemin vers les simulations
SIMULATOR_OUTPUT_PATH = Path("rag/RAG_assets/nodes/simulations")

# Poids des différentes métriques pour le scoring
SCORE_WEIGHTS = {
    "success_rate": 0.25,        # Taux de succès des forwards
    "forwards_count": 0.20,      # Volume d'activité
    "fee_efficiency": 0.15,      # Efficacité des frais (revenus par sat verrouillé)
    "liquidity_balance": 0.15,   # Équilibre de liquidité (proche de 50%)
    "centrality": 0.10,          # Centralité du nœud dans le réseau
    "stability": 0.10,           # Stabilité du nœud (uptime)
    "channel_count": 0.05        # Nombre de canaux
}

# Seuils pour les recommandations
THRESHOLDS = {
    "overall_score": {
        "excellent": 85,
        "good": 70,
        "average": 50,
        "poor": 30
    },
    "success_rate": {
        "critical": 0.6,  # En dessous de ce seuil, action critique requise
        "warning": 0.8,   # En dessous de ce seuil, avertissement
        "target": 0.95    # Objectif à atteindre
    },
    "fee_efficiency": {
        "low": 2.0,       # sats gagnés par million de sats verrouillés par jour
        "target": 10.0    # objectif
    }
}

def load_latest_simulations() -> Tuple[List[Dict], str]:
    """
    Charge l'ensemble de simulations le plus récent
    
    Returns:
        Tuple[List[Dict], str]: Liste des simulations et horodatage
    """
    # Trouver tous les fichiers de simulation
    sim_files = list(SIMULATOR_OUTPUT_PATH.glob("feustey_sim_*_*.json"))
    
    if not sim_files:
        raise FileNotFoundError("Aucune simulation trouvée")
    
    # Extraire les horodatages uniques
    timestamps = set()
    for file in sim_files:
        parts = file.name.split("_")
        if len(parts) >= 4:
            ts = f"{parts[-2]}_{parts[-1].split('.')[0]}"
            timestamps.add(ts)
    
    if not timestamps:
        raise ValueError("Format de nom de fichier inattendu")
    
    # Utiliser le dernier horodatage
    latest_ts = max(timestamps)
    
    # Charger toutes les simulations avec cet horodatage
    latest_simulations = []
    for file in SIMULATOR_OUTPUT_PATH.glob(f"*{latest_ts}.json"):
        with open(file, "r") as f:
            sim_data = json.load(f)
            latest_simulations.append(sim_data)
    
    return latest_simulations, latest_ts

def calculate_node_score(simulation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcule un score pour un nœud simulé en fonction de ses métriques
    
    Args:
        simulation: Données de simulation du nœud
        
    Returns:
        Dict avec les scores calculés
    """
    metrics = simulation.get("metrics", {})
    
    # Extraire les métriques clés
    success_rate = metrics.get("activity", {}).get("success_rate", 0)
    forwards_count = metrics.get("activity", {}).get("forwards_count", 0)
    
    # Calculer l'équilibre moyen de liquidité des canaux
    channels = simulation.get("channels", [])
    if not channels:
        return {"error": "Aucun canal trouvé"}
    
    # Calculer le ratio moyen de liquidité sortante
    outbound_ratio_sum = 0
    for channel in channels:
        local_balance = channel.get("local_balance", 0)
        remote_balance = channel.get("remote_balance", 0)
        total_balance = local_balance + remote_balance
        
        if total_balance > 0:
            outbound_ratio = local_balance / total_balance
            outbound_ratio_sum += outbound_ratio
    
    avg_outbound_ratio = outbound_ratio_sum / len(channels) if channels else 0
    
    # Score d'équilibre de liquidité (maximal à 0.5, donc 50%)
    liquidity_balance_score = 1.0 - abs(0.5 - avg_outbound_ratio) * 2.0
    
    # Métriques de centralité
    centrality_score = metrics.get("centrality", {}).get("betweenness", 0.5)
    
    # Nombre de forwards normalisé (1000+ forwards = score maximal)
    forwards_score = min(forwards_count / 1000, 1.0)
    
    # Efficacité des frais (frais cumulés par forward)
    cumul_fees = simulation.get("cumul_fees", 0)
    fee_per_forward = cumul_fees / forwards_count if forwards_count > 0 else 0
    
    # Calcul du score global pondéré
    weighted_scores = {
        "success_rate": success_rate * SCORE_WEIGHTS["success_rate"],
        "forwards_count": forwards_score * SCORE_WEIGHTS["forwards_count"],
        "fee_efficiency": min(fee_per_forward / 1000, 1.0) * SCORE_WEIGHTS["fee_efficiency"],
        "liquidity_balance": liquidity_balance_score * SCORE_WEIGHTS["liquidity_balance"],
        "centrality": centrality_score * SCORE_WEIGHTS["centrality"],
        "stability": 0.9 * SCORE_WEIGHTS["stability"],  # Valeur simulée
        "channel_count": min(len(channels) / 20, 1.0) * SCORE_WEIGHTS["channel_count"]
    }
    
    # Score global (sur 100)
    overall_score = sum(weighted_scores.values()) * 100
    
    # Calculer un PerformanceIndex (mesure synthétique d'efficacité)
    # Formule: (forwards * success_rate * fee_per_forward) / (total_capacity * 10000)
    total_capacity = sum(float(channel.get("Capacity", 0)) for channel in channels)
    performance_index = 0
    if total_capacity > 0:
        performance_index = (forwards_count * success_rate * fee_per_forward) / (total_capacity / 10000)
    
    # Recommandation automatique
    recommendation = determine_recommendation(
        success_rate=success_rate,
        forwards_count=forwards_count,
        fee_per_forward=fee_per_forward,
        liquidity_balance=liquidity_balance_score,
        overall_score=overall_score
    )
    
    return {
        "profile": simulation.get("simulation_info", {}).get("profile", "unknown"),
        "overall_score": round(overall_score, 2),
        "individual_scores": {k: round(v * 100, 2) for k, v in weighted_scores.items()},
        "forwards_count": forwards_count,
        "success_rate": round(success_rate * 100, 2),
        "fee_per_forward": round(fee_per_forward, 2),
        "total_fees": cumul_fees,
        "avg_outbound_ratio": round(avg_outbound_ratio * 100, 2),
        "performance_index": round(performance_index, 4),
        "recommendation": recommendation
    }

def determine_recommendation(success_rate: float, forwards_count: int, 
                           fee_per_forward: float, liquidity_balance: float,
                           overall_score: float) -> str:
    """
    Détermine la recommandation d'action basée sur les métriques du nœud
    
    Returns:
        str: Recommandation d'action
    """
    if success_rate < THRESHOLDS["success_rate"]["critical"]:
        return "CRITIQUE: Rééquilibrer les canaux immédiatement et ajuster les frais"
        
    if success_rate < THRESHOLDS["success_rate"]["warning"]:
        if forwards_count < 50:
            return "ATTENTION: Taux de succès faible avec peu d'activité - Problème de connectivité"
        else:
            return "ATTENTION: Taux de succès faible malgré l'activité - Réviser la politique tarifaire"
    
    if forwards_count > 500 and fee_per_forward < 100:
        return "OPTIMISATION: Fort volume mais faibles frais - Augmenter les frais"
        
    if forwards_count < 20:
        return "ATTENTION: Activité très faible - Vérifier connectivité ou frais trop élevés"
    
    if forwards_count > 800 and success_rate > 0.95:
        return "EXCELLENT: Nœud très performant - Maintenir configuration"
        
    if liquidity_balance < 0.3:
        return "ACTION: Déséquilibre de liquidité - Rééquilibrer les canaux"
        
    if overall_score > THRESHOLDS["overall_score"]["excellent"]:
        return "EXCELLENT: Performance optimale - Maintenir configuration"
        
    if overall_score > THRESHOLDS["overall_score"]["good"]:
        return "BON: Performance satisfaisante - Optimisations mineures possibles"
        
    return "NORMAL: Performance dans la moyenne - Améliorations possibles"

def generate_comparison_table(evaluation_results: List[Dict]) -> pd.DataFrame:
    """
    Génère un tableau comparatif des résultats d'évaluation
    
    Args:
        evaluation_results: Liste des résultats d'évaluation
        
    Returns:
        DataFrame pandas avec le tableau comparatif
    """
    # Construire le DataFrame
    df = pd.DataFrame(evaluation_results)
    
    # Trier par score global décroissant
    df = df.sort_values("overall_score", ascending=False)
    
    return df

def export_results(df: pd.DataFrame, timestamp: str):
    """
    Exporte les résultats au format CSV et génère un rapport
    
    Args:
        df: DataFrame avec les résultats
        timestamp: Horodatage des simulations analysées
    """
    # Exporter au format CSV
    csv_path = SIMULATOR_OUTPUT_PATH / f"simulation_comparison_{timestamp}.csv"
    df.to_csv(csv_path, index=False)
    
    # Générer un rapport Markdown
    md_path = SIMULATOR_OUTPUT_PATH / f"simulation_evaluation_{timestamp}.md"
    
    with open(md_path, "w") as f:
        f.write(f"# Évaluation des simulations de nœuds Lightning\n\n")
        f.write(f"Date de l'analyse: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Simulations analysées: {timestamp}\n\n")
        
        f.write("## Tableau comparatif des profils\n\n")
        
        # Créer un tableau markdown manuellement car to_markdown peut ne pas être disponible
        headers = ["Profile", "Score Global", "Forwards", "Taux de Succès (%)", "Frais/Forward", "Frais Totaux", "Équilibre (%)", "Perf. Index"]
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("| " + " | ".join(["---" for _ in headers]) + " |\n")
        
        for _, row in df.iterrows():
            values = [
                row["profile"],
                f"{row['overall_score']:.2f}",
                f"{row['forwards_count']}",
                f"{row['success_rate']:.1f}",
                f"{row['fee_per_forward']:.1f}",
                f"{row['total_fees']}",
                f"{row['avg_outbound_ratio']:.1f}",
                f"{row['performance_index']:.4f}"
            ]
            f.write("| " + " | ".join(values) + " |\n")
        
        f.write("\n\n## Recommandations par profil\n\n")
        for _, row in df.iterrows():
            f.write(f"### {row['profile']}\n")
            f.write(f"* Score global: {row['overall_score']}\n")
            f.write(f"* Recommandation: **{row['recommendation']}**\n")
            f.write(f"* Performance Index: {row['performance_index']}\n\n")
            
        f.write("\n\n## Métriques clés à surveiller\n\n")
        f.write("1. **Taux de succès** - Objectif: >95%\n")
        f.write("2. **Équilibre de liquidité** - Objectif: proche de 50%\n")
        f.write("3. **Performance Index** - Mesure synthétique de l'efficacité du capital\n\n")
        
        # Ajouter un graphique textuel simple des scores
        f.write("## Classement des profils par score global\n\n")
        f.write("```\n")
        max_score = df["overall_score"].max()
        for _, row in df.iterrows():
            bar_length = int((row["overall_score"] / max_score) * 40)
            bar = "#" * bar_length
            f.write(f"{row['profile']:15} [{bar:<40}] {row['overall_score']}\n")
        f.write("```\n")
    
    print(f"Résultats exportés dans {csv_path} et {md_path}")

def main():
    """Fonction principale d'évaluation des simulations"""
    try:
        # Charger les simulations les plus récentes
        logger.info("Chargement des simulations les plus récentes...")
        simulations, timestamp = load_latest_simulations()
        logger.info(f"Chargement terminé: {len(simulations)} simulations du {timestamp}")
        
        # Calculer les scores pour chaque simulation
        logger.info("Évaluation des simulations...")
        evaluation_results = []
        
        for sim in simulations:
            profile_type = sim.get("simulation_info", {}).get("profile", "unknown")
            logger.info(f"Évaluation du profil '{profile_type}'...")
            
            score_data = calculate_node_score(sim)
            evaluation_results.append(score_data)
        
        # Générer le tableau comparatif
        logger.info("Génération du tableau comparatif...")
        comparison_table = generate_comparison_table(evaluation_results)
        
        # Exporter les résultats
        logger.info("Exportation des résultats...")
        export_results(comparison_table, timestamp)
        
        logger.info("Évaluation terminée avec succès!")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'évaluation des simulations: {e}")

if __name__ == "__main__":
    main() 