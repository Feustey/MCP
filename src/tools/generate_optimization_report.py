#!/usr/bin/env python3
# coding: utf-8
"""
Script de génération d'un rapport d'optimisation des nœuds Lightning.
Analyse les logs pour résumer les actions d'optimisation entreprises.

Dernière mise à jour: 10 mai 2025
"""

import re
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd
import json
import argparse

# Constantes
LOG_FILE = "logs/optimizer.log"
REPORT_DIR = Path("data/reports")
ACTION_PATTERNS = {
    "rebalance": r"rééquilibrage .* pour (\d+) canaux",
    "fee_adjustment": r"(augmentation|baisse) des frais pour (\d+) canaux",
    "evaluation": r"Évaluation du nœud: score=([0-9.]+), recommandation=(.+)"
}

def parse_args():
    """Parse les arguments de ligne de commande"""
    parser = argparse.ArgumentParser(description="Génération de rapports d'optimisation")
    parser.add_argument("--log-file", default=LOG_FILE, help="Fichier de log à analyser")
    parser.add_argument("--output-dir", default=str(REPORT_DIR), help="Répertoire de sortie des rapports")
    parser.add_argument("--format", choices=["html", "csv", "md", "json"], default="md", 
                       help="Format de sortie du rapport")
    return parser.parse_args()

def parse_log_file(log_file):
    """
    Analyse un fichier de log pour extraire les informations d'optimisation
    
    Args:
        log_file: Chemin du fichier de log
        
    Returns:
        Liste des enregistrements d'optimisation
    """
    if not os.path.exists(log_file):
        print(f"Erreur: Le fichier de log {log_file} n'existe pas.")
        return []
        
    records = []
    current_record = None
    
    with open(log_file, 'r') as f:
        for line in f:
            # Début d'une nouvelle optimisation
            if "Démarrage de l'optimisation pour le nœud" in line:
                # Sauvegarder l'enregistrement précédent s'il existe
                if current_record:
                    records.append(current_record)
                    
                # Extraire la date et l'ID du nœud
                parts = line.split(" - ")
                timestamp = parts[0]
                node_match = re.search(r"nœud (\w+)", line)
                node_id = node_match.group(1) if node_match else "unknown"
                
                # Créer un nouvel enregistrement
                current_record = {
                    "timestamp": timestamp,
                    "node_id": node_id,
                    "profile": None,
                    "score": None,
                    "recommendation": None,
                    "actions": [],
                    "liquidity_balance": None,
                    "success_rate": None
                }
                
            # Informations sur le profil
            elif current_record and "Génération de données simulées" in line:
                profile_match = re.search(r"profil: (\w+)", line)
                if profile_match:
                    current_record["profile"] = profile_match.group(1)
                    
            # État du nœud
            elif current_record and "État actuel du nœud" in line:
                try:
                    # Extraire les données d'état au format JSON
                    state_match = re.search(r"État actuel du nœud: (.+?)$", line)
                    if state_match:
                        state_str = state_match.group(1)
                        state = json.loads(state_str)  # Sécurisé avec json.loads
                        
                        current_record["success_rate"] = state.get("success_rate")
                        current_record["liquidity_balance"] = state.get("liquidity_balance")
                        current_record["revenue"] = state.get("revenue")
                except Exception as e:
                    print(f"Erreur lors de l'analyse de l'état du nœud: {e}")
                    
            # Évaluation du nœud
            elif current_record and "Évaluation du nœud: score=" in line:
                eval_match = re.search(ACTION_PATTERNS["evaluation"], line)
                if eval_match:
                    current_record["score"] = float(eval_match.group(1))
                    current_record["recommendation"] = eval_match.group(2)
                    
            # Actions proposées (dry-run)
            elif current_record and "Actions proposées (dry-run)" in line:
                try:
                    # Extraire les actions au format JSON
                    actions_match = re.search(r"Actions proposées \(dry-run\): (.+?)$", line)
                    if actions_match:
                        actions_str = actions_match.group(1)
                        actions = json.loads(actions_str)  # Sécurisé avec json.loads
                        
                        # Convertir les actions dry-run en actions régulières pour le rapport
                        for action in actions:
                            action_type = action.get("action", "")
                            if "rebalance_dry_run" in action_type:
                                current_record["actions"].append({
                                    "type": "rebalance",
                                    "emergency": action.get("emergency", False),
                                    "channels": action.get("channels_to_rebalance", 0)
                                })
                            elif "fee_adjustment_dry_run" in action_type:
                                current_record["actions"].append({
                                    "type": "fee_adjustment",
                                    "direction": action.get("direction", "unknown"),
                                    "channels": action.get("channels_to_update", 0)
                                })
                except Exception as e:
                    print(f"Erreur lors de l'analyse des actions proposées: {e}")
                            
            # Actions de rééquilibrage
            elif current_record and ("rééquilibrage" in line.lower() or "rebalance" in line.lower()):
                rebalance_match = re.search(ACTION_PATTERNS["rebalance"], line)
                if rebalance_match:
                    num_channels = int(rebalance_match.group(1))
                    emergency = "d'urgence" in line or "emergency=True" in line
                    
                    current_record["actions"].append({
                        "type": "rebalance",
                        "emergency": emergency,
                        "channels": num_channels
                    })
                    
            # Actions d'ajustement de frais
            elif current_record and ("ajustement des frais" in line or "fee_adjustment" in line):
                fee_match = re.search(ACTION_PATTERNS["fee_adjustment"], line)
                if fee_match:
                    direction = "increase" if fee_match.group(1) == "augmentation" else "decrease"
                    num_channels = int(fee_match.group(2))
                    
                    current_record["actions"].append({
                        "type": "fee_adjustment",
                        "direction": direction,
                        "channels": num_channels
                    })
                    
    # Ajouter le dernier enregistrement s'il existe
    if current_record:
        records.append(current_record)
        
    return records

def calculate_stats(records):
    """
    Calcule des statistiques à partir des enregistrements
    
    Args:
        records: Liste des enregistrements d'optimisation
        
    Returns:
        Dict avec les statistiques calculées
    """
    if not records:
        return {}
        
    # Statistiques par profil
    profile_stats = {}
    
    for record in records:
        profile = record.get("profile", "unknown")
        
        if profile not in profile_stats:
            profile_stats[profile] = {
                "count": 0,
                "avg_score": 0,
                "rebalance_count": 0,
                "fee_adjustment_count": 0,
                "emergency_count": 0,
                "increase_fees_count": 0,
                "decrease_fees_count": 0
            }
            
        stats = profile_stats[profile]
        stats["count"] += 1
        stats["avg_score"] += record.get("score", 0) or 0
        
        # Compter les actions
        for action in record.get("actions", []):
            action_type = action.get("type")
            
            if action_type == "rebalance":
                stats["rebalance_count"] += 1
                if action.get("emergency"):
                    stats["emergency_count"] += 1
                    
            elif action_type == "fee_adjustment":
                stats["fee_adjustment_count"] += 1
                if action.get("direction") == "increase":
                    stats["increase_fees_count"] += 1
                else:
                    stats["decrease_fees_count"] += 1
                    
    # Calculer les moyennes
    for profile, stats in profile_stats.items():
        if stats["count"] > 0:
            stats["avg_score"] /= stats["count"]
            
    return {
        "profiles": profile_stats,
        "total_nodes": len(records),
        "total_actions": sum(len(r.get("actions", [])) for r in records)
    }

def generate_markdown_report(records, stats, output_file):
    """
    Génère un rapport au format Markdown
    
    Args:
        records: Liste des enregistrements d'optimisation
        stats: Statistiques calculées
        output_file: Fichier de sortie
    """
    with open(output_file, 'w') as f:
        # En-tête
        f.write(f"# Rapport d'optimisation des nœuds Lightning\n\n")
        f.write(f"*Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}*\n\n")
        
        # Statistiques globales
        f.write("## Statistiques globales\n\n")
        f.write(f"- Nombre total de nœuds analysés: **{stats['total_nodes']}**\n")
        f.write(f"- Nombre total d'actions: **{stats['total_actions']}**\n\n")
        
        # Statistiques par profil
        f.write("## Statistiques par profil\n\n")
        f.write("| Profil | Nombre | Score moyen | Rééquilibrages | Ajustements de frais | Urgences | ↑ Frais | ↓ Frais |\n")
        f.write("|--------|--------|------------|----------------|---------------------|----------|---------|--------|\n")
        
        for profile, profile_stats in stats["profiles"].items():
            f.write(f"| **{profile}** | {profile_stats['count']} | {profile_stats['avg_score']:.2f} | ")
            f.write(f"{profile_stats['rebalance_count']} | {profile_stats['fee_adjustment_count']} | ")
            f.write(f"{profile_stats['emergency_count']} | {profile_stats['increase_fees_count']} | ")
            f.write(f"{profile_stats['decrease_fees_count']} |\n")
            
        f.write("\n")
        
        # Détails des nœuds
        f.write("## Détails des optimisations\n\n")
        
        for i, record in enumerate(sorted(records, key=lambda r: r.get("score", 0) or 0)):
            node_id = record.get("node_id", "unknown")
            profile = record.get("profile", "unknown")
            score = record.get("score", 0) or 0
            recommendation = record.get("recommendation", "Inconnue")
            
            f.write(f"### {i+1}. Nœud: {node_id} (Profil: {profile})\n\n")
            f.write(f"- **Score**: {score:.2f}\n")
            f.write(f"- **État**: Équilibre={record.get('liquidity_balance', 'N/A')}, ")
            f.write(f"Succès={record.get('success_rate', 'N/A')}, ")
            f.write(f"Revenu={record.get('revenue', 'N/A')}\n")
            f.write(f"- **Recommandation**: {recommendation}\n")
            
            # Actions
            if record.get("actions"):
                f.write("- **Actions**:\n")
                for action in record["actions"]:
                    action_type = action.get("type")
                    
                    if action_type == "rebalance":
                        emergency = " d'urgence" if action.get("emergency") else ""
                        f.write(f"  - Rééquilibrage{emergency} de {action.get('channels')} canaux\n")
                        
                    elif action_type == "fee_adjustment":
                        direction = "augmentés" if action.get("direction") == "increase" else "diminués"
                        f.write(f"  - Frais {direction} pour {action.get('channels')} canaux\n")
            else:
                f.write("- **Actions**: Aucune action nécessaire\n")
                
            f.write("\n")
            
        # Conclusion
        f.write("## Conclusion\n\n")
        
        # Trouver les profils les plus optimisés
        most_actions = max(stats["profiles"].items(), key=lambda x: len(x[1]), default=(None, {"count": 0}))
        highest_score = max(stats["profiles"].items(), key=lambda x: x[1]["avg_score"], default=(None, {"avg_score": 0}))
        
        f.write("### Insights\n\n")
        
        if most_actions[0]:
            f.write(f"- Le profil **{most_actions[0]}** a nécessité le plus d'actions correctives.\n")
            
        if highest_score[0]:
            f.write(f"- Le profil **{highest_score[0]}** a obtenu le meilleur score moyen ({highest_score[1]['avg_score']:.2f}).\n")
            
        # Recommandations générales
        f.write("\n### Recommandations générales\n\n")
        
        # Identifier les tendances
        rebalance_heavy = any(p["rebalance_count"] > p["fee_adjustment_count"] * 2 
                              for p in stats["profiles"].values())
        fee_heavy = any(p["fee_adjustment_count"] > p["rebalance_count"] * 2 
                        for p in stats["profiles"].values())
        emergency_frequent = any(p["emergency_count"] > p["count"] / 2 
                                for p in stats["profiles"].values())
        
        if rebalance_heavy:
            f.write("- Surveiller les équilibres de liquidité plus régulièrement pour éviter les déséquilibres importants.\n")
            
        if fee_heavy:
            f.write("- Considérer une politique de frais plus adaptative pour réduire le besoin d'ajustements fréquents.\n")
            
        if emergency_frequent:
            f.write("- Mettre en place des alertes précoces pour les situations critiques qui nécessitent des interventions d'urgence.\n")
            
        # Recommandation générique si aucune tendance particulière
        if not any([rebalance_heavy, fee_heavy, emergency_frequent]):
            f.write("- Continuer le monitoring régulier et les optimisations périodiques.\n")
            f.write("- Envisager d'augmenter la fréquence des vérifications pour les nœuds à fort volume.\n")

def generate_reports(records, stats, output_dir, format):
    """
    Génère les rapports dans le format spécifié
    
    Args:
        records: Liste des enregistrements d'optimisation
        stats: Statistiques calculées
        output_dir: Répertoire de sortie
        format: Format de sortie (html, csv, md, json)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"optimization_report_{timestamp}"
    
    if format == "md" or format == "html":
        # Générer le markdown
        md_file = os.path.join(output_dir, f"{base_filename}.md")
        generate_markdown_report(records, stats, md_file)
        print(f"Rapport Markdown généré: {md_file}")
        
        if format == "html":
            # Convertir en HTML si nécessaire
            try:
                import markdown
                with open(md_file, 'r') as f:
                    md_content = f.read()
                    
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Rapport d'optimisation des nœuds Lightning</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 1200px; margin: 0 auto; padding: 20px; }}
                        table {{ border-collapse: collapse; width: 100%; }}
                        th, td {{ border: 1px solid #ddd; padding: 8px; }}
                        th {{ background-color: #f2f2f2; }}
                        tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    </style>
                </head>
                <body>
                    {markdown.markdown(md_content, extensions=['tables'])}
                </body>
                </html>
                """
                
                html_file = os.path.join(output_dir, f"{base_filename}.html")
                with open(html_file, 'w') as f:
                    f.write(html_content)
                    
                print(f"Rapport HTML généré: {html_file}")
                
            except ImportError:
                print("Package 'markdown' non disponible. Le rapport HTML n'a pas été généré.")
                
    elif format == "csv":
        # Générer un CSV des nœuds
        nodes_df = pd.DataFrame(records)
        
        # Simplifier la colonne actions
        def simplify_actions(actions):
            if not actions:
                return ""
                
            result = []
            for action in actions:
                if action["type"] == "rebalance":
                    emergency = "emergency" if action.get("emergency") else "normal"
                    result.append(f"rebalance_{emergency}")
                elif action["type"] == "fee_adjustment":
                    result.append(f"fee_{action.get('direction', 'unknown')}")
                    
            return ", ".join(result)
            
        nodes_df["actions_summary"] = nodes_df["actions"].apply(simplify_actions)
        
        # Supprimer la colonne actions originale (trop complexe pour CSV)
        if "actions" in nodes_df:
            del nodes_df["actions"]
            
        # Enregistrer en CSV
        csv_file = os.path.join(output_dir, f"{base_filename}.csv")
        nodes_df.to_csv(csv_file, index=False)
        print(f"Rapport CSV généré: {csv_file}")
        
        # Générer un CSV des statistiques par profil
        profiles_data = []
        for profile, profile_stats in stats["profiles"].items():
            profile_data = {"profile": profile}
            profile_data.update(profile_stats)
            profiles_data.append(profile_data)
            
        profiles_df = pd.DataFrame(profiles_data)
        profiles_csv = os.path.join(output_dir, f"{base_filename}_profiles.csv")
        profiles_df.to_csv(profiles_csv, index=False)
        print(f"Rapport CSV des profils généré: {profiles_csv}")
        
    elif format == "json":
        # Générer un JSON complet
        json_data = {
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "total_nodes": stats["total_nodes"],
                "total_actions": stats["total_actions"]
            },
            "stats": stats,
            "nodes": records
        }
        
        json_file = os.path.join(output_dir, f"{base_filename}.json")
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=2)
            
        print(f"Rapport JSON généré: {json_file}")

def main():
    """Fonction principale"""
    args = parse_args()
    
    print(f"Analyse du fichier de log: {args.log_file}")
    records = parse_log_file(args.log_file)
    
    if not records:
        print("Aucun enregistrement d'optimisation trouvé dans les logs.")
        return 1
        
    print(f"Nombre d'enregistrements trouvés: {len(records)}")
    
    stats = calculate_stats(records)
    
    print(f"Génération du rapport au format {args.format}")
    generate_reports(records, stats, args.output_dir, args.format)
    
    print(f"Rapport généré avec succès dans le répertoire: {args.output_dir}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 