#!/usr/bin/env python3
import os
import json
import argparse
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, Any, List, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = "cache_analysis"

def load_results(file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Charge les résultats d'analyse depuis un fichier JSON ou trouve 
    le fichier le plus récent dans le répertoire d'analyse.
    
    Args:
        file_path: Chemin d'accès au fichier à charger (optionnel)
        
    Returns:
        Dictionnaire des résultats d'analyse
    """
    if not os.path.exists(OUTPUT_DIR):
        logger.error(f"Le répertoire d'analyse {OUTPUT_DIR} n'existe pas.")
        return {}
    
    if file_path and os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    
    # Trouver le fichier d'analyse le plus récent
    json_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.json')]
    if not json_files:
        logger.error(f"Aucun fichier d'analyse trouvé dans {OUTPUT_DIR}.")
        return {}
    
    # Trier par date de modification (le plus récent en premier)
    json_files.sort(key=lambda x: os.path.getmtime(os.path.join(OUTPUT_DIR, x)), reverse=True)
    most_recent = os.path.join(OUTPUT_DIR, json_files[0])
    
    logger.info(f"Chargement du fichier d'analyse le plus récent: {most_recent}")
    with open(most_recent, 'r') as f:
        return json.load(f)

def visualize_results(results: Dict[str, Any], output_path: Optional[str] = None):
    """
    Génère des visualisations des résultats d'analyse du cache.
    
    Args:
        results: Dictionnaire des résultats d'analyse
        output_path: Chemin de sortie pour le graphique (optionnel)
    """
    if not results:
        logger.error("Aucun résultat à visualiser.")
        return
    
    test_sizes = results.get("test_sizes", [])
    write_times = results.get("write_times", {})
    redis_read_times = results.get("redis_read_times", {})
    memory_read_times = results.get("memory_read_times", {})
    timestamp = results.get("timestamp", datetime.now().strftime("%Y%m%d_%H%M%S"))
    
    if not test_sizes or not write_times or not redis_read_times or not memory_read_times:
        logger.error("Les données de résultats sont incomplètes ou mal formatées.")
        return
    
    # Calculer les gains de performance
    gains = {}
    for data_type in write_times.keys():
        gains[data_type] = [r/m if m > 0 else 0 for r, m in 
                           zip(redis_read_times[data_type], memory_read_times[data_type])]
    
    # Configurer la figure
    plt.figure(figsize=(15, 10))
    
    # 1. Graphique des temps d'écriture
    plt.subplot(2, 2, 1)
    for data_type in write_times.keys():
        plt.plot(test_sizes, write_times[data_type], marker='o', label=data_type)
    plt.title("Temps d'écriture par élément")
    plt.xlabel("Nombre d'éléments")
    plt.ylabel("Temps (ms)")
    plt.legend()
    plt.grid(True)
    
    # 2. Graphique des temps de lecture depuis Redis
    plt.subplot(2, 2, 2)
    for data_type in redis_read_times.keys():
        plt.plot(test_sizes, redis_read_times[data_type], marker='o', label=data_type)
    plt.title("Temps de lecture depuis Redis par élément")
    plt.xlabel("Nombre d'éléments")
    plt.ylabel("Temps (ms)")
    plt.legend()
    plt.grid(True)
    
    # 3. Graphique des temps de lecture depuis la mémoire
    plt.subplot(2, 2, 3)
    for data_type in memory_read_times.keys():
        plt.plot(test_sizes, memory_read_times[data_type], marker='o', label=data_type)
    plt.title("Temps de lecture depuis la mémoire par élément")
    plt.xlabel("Nombre d'éléments")
    plt.ylabel("Temps (ms)")
    plt.legend()
    plt.grid(True)
    
    # 4. Graphique comparatif des gains de performance
    plt.subplot(2, 2, 4)
    for data_type in gains.keys():
        plt.plot(test_sizes, gains[data_type], marker='o', label=data_type)
    plt.title("Gain de performance mémoire vs Redis")
    plt.xlabel("Nombre d'éléments")
    plt.ylabel("Facteur d'accélération (x)")
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    
    # Titre global
    plt.suptitle(f"Analyse des performances du cache multi-niveaux - {timestamp}", fontsize=16)
    plt.subplots_adjust(top=0.93)
    
    # Enregistrer ou afficher le graphique
    if output_path:
        plt.savefig(output_path)
        logger.info(f"Graphique enregistré: {output_path}")
    else:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_file = f"{OUTPUT_DIR}/cache_performance_view_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(output_file)
        logger.info(f"Graphique enregistré: {output_file}")
        
    # Afficher le graphique
    plt.show()

def compare_results(file_paths: List[str]):
    """
    Compare plusieurs fichiers de résultats d'analyse.
    
    Args:
        file_paths: Liste des chemins de fichiers à comparer
    """
    if not file_paths or len(file_paths) < 2:
        logger.error("Au moins deux fichiers sont nécessaires pour effectuer une comparaison.")
        return
    
    all_results = []
    timestamps = []
    
    # Charger tous les résultats
    for file_path in file_paths:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                results = json.load(f)
                all_results.append(results)
                timestamps.append(results.get("timestamp", "inconnu"))
        else:
            logger.warning(f"Le fichier {file_path} n'existe pas et sera ignoré.")
    
    if len(all_results) < 2:
        logger.error("Pas assez de fichiers valides pour effectuer une comparaison.")
        return
    
    # Configuration de la figure comparative
    plt.figure(figsize=(15, 12))
    
    # Sélectionner un type de données commun pour la comparaison
    data_type = "embeddings"  # Le plus souvent utilisé
    
    # 1. Comparaison des temps d'écriture
    plt.subplot(2, 2, 1)
    for i, results in enumerate(all_results):
        test_sizes = results.get("test_sizes", [])
        write_times = results.get("write_times", {}).get(data_type, [])
        if test_sizes and write_times:
            plt.plot(test_sizes, write_times, marker='o', label=f"Analyse {timestamps[i]}")
    plt.title(f"Comparaison des temps d'écriture ({data_type})")
    plt.xlabel("Nombre d'éléments")
    plt.ylabel("Temps (ms)")
    plt.legend()
    plt.grid(True)
    
    # 2. Comparaison des temps de lecture Redis
    plt.subplot(2, 2, 2)
    for i, results in enumerate(all_results):
        test_sizes = results.get("test_sizes", [])
        redis_times = results.get("redis_read_times", {}).get(data_type, [])
        if test_sizes and redis_times:
            plt.plot(test_sizes, redis_times, marker='o', label=f"Analyse {timestamps[i]}")
    plt.title(f"Comparaison des temps de lecture Redis ({data_type})")
    plt.xlabel("Nombre d'éléments")
    plt.ylabel("Temps (ms)")
    plt.legend()
    plt.grid(True)
    
    # 3. Comparaison des temps de lecture mémoire
    plt.subplot(2, 2, 3)
    for i, results in enumerate(all_results):
        test_sizes = results.get("test_sizes", [])
        memory_times = results.get("memory_read_times", {}).get(data_type, [])
        if test_sizes and memory_times:
            plt.plot(test_sizes, memory_times, marker='o', label=f"Analyse {timestamps[i]}")
    plt.title(f"Comparaison des temps de lecture mémoire ({data_type})")
    plt.xlabel("Nombre d'éléments")
    plt.ylabel("Temps (ms)")
    plt.legend()
    plt.grid(True)
    
    # 4. Comparaison des gains de performance
    plt.subplot(2, 2, 4)
    for i, results in enumerate(all_results):
        test_sizes = results.get("test_sizes", [])
        redis_times = results.get("redis_read_times", {}).get(data_type, [])
        memory_times = results.get("memory_read_times", {}).get(data_type, [])
        if test_sizes and redis_times and memory_times:
            gains = [r/m if m > 0 else 0 for r, m in zip(redis_times, memory_times)]
            plt.plot(test_sizes, gains, marker='o', label=f"Analyse {timestamps[i]}")
    plt.title(f"Comparaison des gains de performance ({data_type})")
    plt.xlabel("Nombre d'éléments")
    plt.ylabel("Facteur d'accélération (x)")
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    
    # Titre global
    plt.suptitle("Comparaison des analyses de performance du cache multi-niveaux", fontsize=16)
    plt.subplots_adjust(top=0.93)
    
    # Enregistrer et afficher
    output_file = f"{OUTPUT_DIR}/cache_performance_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    plt.savefig(output_file)
    logger.info(f"Graphique de comparaison enregistré: {output_file}")
    
    plt.show()

def list_available_results():
    """Liste les fichiers d'analyse disponibles."""
    if not os.path.exists(OUTPUT_DIR):
        logger.error(f"Le répertoire d'analyse {OUTPUT_DIR} n'existe pas.")
        return
    
    json_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.json')]
    if not json_files:
        logger.info(f"Aucun fichier d'analyse trouvé dans {OUTPUT_DIR}.")
        return
    
    # Trier par date de modification (le plus récent en premier)
    json_files.sort(key=lambda x: os.path.getmtime(os.path.join(OUTPUT_DIR, x)), reverse=True)
    
    logger.info(f"Fichiers d'analyse disponibles dans {OUTPUT_DIR}:")
    for i, file in enumerate(json_files):
        file_path = os.path.join(OUTPUT_DIR, file)
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        size = os.path.getsize(file_path) / 1024  # taille en KB
        logger.info(f"{i+1}. {file} - {mtime.strftime('%Y-%m-%d %H:%M:%S')} - {size:.1f} KB")

def main():
    parser = argparse.ArgumentParser(description="Visualisation des résultats d'analyse du cache multi-niveaux")
    parser.add_argument('--file', type=str, help='Chemin vers un fichier de résultats spécifique')
    parser.add_argument('--output', type=str, help='Chemin de sortie pour le graphique')
    parser.add_argument('--compare', nargs='+', help='Comparer plusieurs fichiers de résultats')
    parser.add_argument('--list', action='store_true', help='Lister les fichiers de résultats disponibles')
    
    args = parser.parse_args()
    
    if args.list:
        list_available_results()
        return
    
    if args.compare:
        compare_results(args.compare)
        return
    
    results = load_results(args.file)
    visualize_results(results, args.output)

if __name__ == "__main__":
    main() 