#!/usr/bin/env python3
# rag_asset_generator.py

import sys
import os
import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ajouter le répertoire racine au path pour les imports
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/rag_asset_generation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import des modules nécessaires
try:
    from src.data_aggregator import DataAggregator
    from rag.rag import RAGWorkflow
    from lnbits_client import LNBitsClient
    from lnbits_rag_integration import LNbitsRAGIntegration
    from feustey_fee_optimizer import main as optimize_feustey_fees
except ImportError as e:
    logger.error(f"Erreur d'importation: {e}")
    logger.error("Certains modules n'ont pas pu être importés. Vérifiez les dépendances.")
    sys.exit(1)

# Définition des chemins
RAG_ASSETS_DIR = Path("rag/RAG_assets")
REPORTS_DIR = RAG_ASSETS_DIR / "reports"
MARKET_DATA_DIR = RAG_ASSETS_DIR / "market_data"
NODES_DIR = RAG_ASSETS_DIR / "nodes"
METRICS_DIR = RAG_ASSETS_DIR / "metrics"
LOGS_DIR = RAG_ASSETS_DIR / "logs"

# Créer les répertoires s'ils n'existent pas
for directory in [REPORTS_DIR, MARKET_DATA_DIR, NODES_DIR, METRICS_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True, parents=True)

class RAGAssetGenerator:
    """Classe principale pour générer les assets RAG"""

    def __init__(self):
        """Initialisation des composants nécessaires"""
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"Initialisation du générateur d'assets RAG (timestamp: {self.timestamp})")
        
        # Initialisation des composants (à faire dans initialize)
        self.data_aggregator = None
        self.rag_workflow = None
        self.lnbits_client = None
        self.lnbits_rag = None
        
        # Informations sur les nœuds cibles
        self.target_nodes = {
            "feustey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
            "barcelona": "03ea0975a7136641752f657f618c8b4c1ee70e03c0baa3c2c6ecfff628cf9d5cb9",
        }

    async def initialize(self):
        """Initialisation asynchrone des composants"""
        try:
            logger.info("Initialisation des composants...")
            
            # DataAggregator pour collecter les données
            self.data_aggregator = DataAggregator()
            await self.data_aggregator.initialize()
            
            # RAG Workflow pour les analyses
            self.rag_workflow = RAGWorkflow()
            
            # LNBits Client pour les données des nœuds
            lnbits_url = os.getenv("LNBITS_URL", "http://localhost:5000")
            lnbits_admin_key = os.getenv("LNBITS_ADMIN_KEY")
            self.lnbits_client = LNBitsClient(lnbits_url, lnbits_admin_key)
            
            # Intégration RAG LNBits
            self.lnbits_rag = LNbitsRAGIntegration()
            
            logger.info("Initialisation terminée avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur d'initialisation: {str(e)}")
            return False

    async def collect_market_data(self):
        """Collecte les données du marché Lightning"""
        logger.info("Collecte des données du marché Lightning...")
        
        try:
            # Créer un répertoire pour le snapshot actuel
            snapshot_dir = MARKET_DATA_DIR / "network_snapshots" / self.timestamp
            snapshot_dir.mkdir(exist_ok=True, parents=True)
            
            # Collecter les données via DataAggregator
            await self.data_aggregator.aggregate_data()
            
            # Copier les données collectées dans le répertoire snapshot
            collected_data_path = Path("collected_data")
            if collected_data_path.exists():
                for json_file in collected_data_path.glob("*.json"):
                    target_path = snapshot_dir / json_file.name
                    with open(json_file, 'r') as src, open(target_path, 'w') as dest:
                        dest.write(src.read())
            
            # Mettre à jour le lien symbolique latest
            latest_link = MARKET_DATA_DIR / "network_snapshots" / "latest"
            if latest_link.exists():
                os.unlink(latest_link)
            os.symlink(snapshot_dir, latest_link, target_is_directory=True)
            
            # Sauvegarder la date de mise à jour
            with open(MARKET_DATA_DIR / "network_snapshots" / "last_update.txt", "w") as f:
                f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            logger.info(f"Données de marché sauvegardées dans {snapshot_dir}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la collecte des données de marché: {str(e)}")
            return False

    async def generate_node_report(self, node_alias: str, node_pubkey: str):
        """Génère un rapport pour un nœud spécifique"""
        logger.info(f"Génération du rapport pour le nœud {node_alias} ({node_pubkey})...")
        
        try:
            # Créer le répertoire pour ce nœud s'il n'existe pas
            node_dir = REPORTS_DIR / node_alias
            node_dir.mkdir(exist_ok=True, parents=True)
            
            # Générer le nom du fichier de rapport avec la date
            report_filename = f"{datetime.now().strftime('%Y-%m-%d')}_{node_alias}_analysis.md"
            report_path = node_dir / report_filename
            
            # Récupérer le template de rapport
            template_path = node_dir / "rapport_template.md"
            if not template_path.exists():
                template_path = REPORTS_DIR / "unknown" / "rapport_template.md"
            
            # Lire le template
            if template_path.exists():
                with open(template_path, 'r') as f:
                    template_content = f.read()
            else:
                logger.warning(f"Template non trouvé pour {node_alias}, utilisation d'un template par défaut")
                template_content = "# Rapport d'analyse du nœud {{alias}} ({{pubkey}})\n\n## Analyse générée le {{date}}\n\n"
            
            # Collecter les données du nœud
            node_data = await self.collect_node_data(node_alias, node_pubkey)
            
            # Générer le prompt pour RAG
            prompt = f"""
            En tant qu'expert du réseau Lightning, génère un rapport d'analyse approfondi pour le nœud {node_alias} ({node_pubkey}).
            
            Utilise toutes les données suivantes pour ton analyse:
            {json.dumps(node_data, indent=2)}
            
            Le rapport doit inclure:
            1. Un résumé exécutif de la position du nœud dans le réseau
            2. Une analyse des métriques de centralité
            3. Un aperçu détaillé des canaux (nombre, capacité, équilibre)
            4. Une analyse des frais appliqués et recommandations d'optimisation
            5. Des recommandations pour améliorer la rentabilité et l'efficacité
            6. Un plan d'action concret avec des étapes précises
            
            Format ton rapport en Markdown bien structuré.
            """
            
            # Exécuter la requête RAG
            rag_result = await self.rag_workflow.query(prompt)
            report_content = rag_result.get("answer", "Erreur lors de la génération du rapport")
            
            # Remplacer les variables dans le template
            final_report = template_content.replace(
                "{{alias}}", node_alias
            ).replace(
                "{{pubkey}}", node_pubkey
            ).replace(
                "{{date_verif}}", datetime.now().strftime("%Y-%m-%d")
            )
            
            # Ajouter les sections générées par le RAG
            final_report += "\n\n" + report_content
            
            # Écrire le rapport dans le fichier
            with open(report_path, 'w') as f:
                f.write(final_report)
            
            logger.info(f"Rapport généré avec succès: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport pour {node_alias}: {str(e)}")
            return None

    async def collect_node_data(self, node_alias: str, node_pubkey: str) -> Dict[str, Any]:
        """Collecte les données spécifiques à un nœud"""
        logger.info(f"Collecte des données pour le nœud {node_alias}...")
        
        try:
            # Données de base
            node_data = {
                "alias": node_alias,
                "pubkey": node_pubkey,
                "timestamp": self.timestamp,
                "channels": [],
                "metrics": {},
                "fees": {"in": {}, "out": {}},
                "cumul_fees": 0,  # À calculer à partir des données historiques
            }
            
            # Récupérer les données des canaux via LNBits si disponible
            if self.lnbits_client:
                channels_data = await self.lnbits_client.get_channels(node_pubkey)
                if channels_data:
                    node_data["channels"] = channels_data
            
            # Si c'est feustey, essayer de charger les données CSV spécifiques
            if node_alias == "feustey":
                csv_path = REPORTS_DIR / "feustey" / "active-channels-feustey.csv"
                if csv_path.exists():
                    import csv
                    channels = []
                    with open(csv_path, 'r', newline='') as csvfile:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            channels.append(row)
                    node_data["channels_csv"] = channels
            
            # Récupérer les métriques de centralité (simulation)
            node_data["metrics"] = {
                "centrality": {
                    "betweenness": 0.45,  # Valeurs simulées
                    "closeness": 0.67,
                    "eigenvector": 0.38,
                },
                "activity": {
                    "forwards_count": 120,
                    "success_rate": 0.93,
                    "avg_fee_earned": 42,
                }
            }
            
            # Sauvegarder les données du nœud pour référence future
            node_raw_data_dir = NODES_DIR / node_alias / "raw_data"
            node_raw_data_dir.mkdir(exist_ok=True, parents=True)
            with open(node_raw_data_dir / f"{self.timestamp}_data.json", 'w') as f:
                json.dump(node_data, f, indent=2)
            
            return node_data
            
        except Exception as e:
            logger.error(f"Erreur lors de la collecte des données pour {node_alias}: {str(e)}")
            return {"error": str(e), "alias": node_alias, "pubkey": node_pubkey}

    async def get_previous_report_date(self, node_alias: str) -> Optional[str]:
        """Récupère la date du rapport précédent"""
        node_dir = REPORTS_DIR / node_alias
        if not node_dir.exists():
            return None
        
        reports = list(node_dir.glob("*_analysis.md"))
        if not reports:
            return None
        
        # Trier les rapports par date de modification
        reports.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        if len(reports) > 1:
            # Récupérer le deuxième rapport le plus récent
            report_filename = reports[1].name
            date_str = report_filename.split('_')[0]
            return date_str
        
        return None

    async def optimize_feustey_fees(self):
        """Lance l'optimisation des frais pour le nœud feustey"""
        logger.info("Optimisation des frais pour le nœud feustey...")
        
        try:
            # Appel au script d'optimisation des frais
            optimize_feustey_fees()
            logger.info("Optimisation des frais feustey terminée")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation des frais feustey: {str(e)}")
            return False

    async def generate_all_assets(self):
        """Génère tous les assets RAG en exécutant le workflow complet"""
        logger.info("Démarrage de la génération de tous les assets RAG...")
        
        # 1. Initialisation des composants
        if not await self.initialize():
            logger.error("Échec de l'initialisation, impossible de continuer")
            return False
        
        # 2. Collecte des données du marché
        await self.collect_market_data()
        
        # 3. Générer les rapports pour chaque nœud cible
        for node_alias, node_pubkey in self.target_nodes.items():
            await self.generate_node_report(node_alias, node_pubkey)
        
        # 4. Optimisation spécifique pour feustey (frais)
        if "feustey" in self.target_nodes:
            await self.optimize_feustey_fees()
        
        # 5. Générer le rapport de synthèse
        await self.generate_summary_report()
        
        # 6. Nettoyage des anciens snapshots
        await self.cleanup_old_snapshots()
        
        logger.info("Génération des assets RAG terminée avec succès")
        return True

    async def generate_summary_report(self):
        """Génère un rapport de synthèse global"""
        logger.info("Génération du rapport de synthèse...")
        
        try:
            # Créer le répertoire pour les métriques
            metrics_dir = METRICS_DIR
            metrics_dir.mkdir(exist_ok=True, parents=True)
            
            # Récupérer des infos sur les rapports générés
            reports = {}
            for node_alias in self.target_nodes:
                node_dir = REPORTS_DIR / node_alias
                if node_dir.exists():
                    node_reports = list(node_dir.glob("*_analysis.md"))
                    reports[node_alias] = [r.name for r in node_reports]
            
            # Générer un rapport de synthèse
            summary = {
                "timestamp": self.timestamp,
                "nodes_analyzed": list(self.target_nodes.keys()),
                "reports_generated": reports,
                "market_data_snapshot": self.timestamp
            }
            
            # Sauvegarder le rapport de synthèse
            with open(metrics_dir / f"{self.timestamp}_summary.json", 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info("Rapport de synthèse généré avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport de synthèse: {str(e)}")
            return False

    async def cleanup_old_snapshots(self):
        """Nettoie les anciens snapshots pour économiser de l'espace"""
        logger.info("Nettoyage des anciens snapshots...")
        
        try:
            # Garder seulement les 5 derniers snapshots
            snapshot_dir = MARKET_DATA_DIR / "network_snapshots"
            if snapshot_dir.exists():
                snapshots = [d for d in snapshot_dir.iterdir() if d.is_dir() and d.name not in ["latest"]]
                snapshots.sort(key=lambda x: x.name, reverse=True)
                
                # Supprimer les snapshots en trop
                if len(snapshots) > 5:
                    for old_snapshot in snapshots[5:]:
                        import shutil
                        shutil.rmtree(old_snapshot)
                        logger.info(f"Snapshot supprimé: {old_snapshot}")
            
            logger.info("Nettoyage des snapshots terminé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des snapshots: {str(e)}")
            return False

    async def close(self):
        """Ferme proprement les connexions"""
        logger.info("Fermeture des connexions...")
        
        if hasattr(self, 'data_aggregator') and self.data_aggregator:
            if hasattr(self.data_aggregator, 'mongo_ops') and self.data_aggregator.mongo_ops:
                await self.data_aggregator.mongo_ops.close()
        
        logger.info("Connexions fermées")


async def main():
    """Fonction principale"""
    try:
        logger.info("Démarrage du générateur d'assets RAG...")
        
        generator = RAGAssetGenerator()
        await generator.generate_all_assets()
        
        logger.info("Processus terminé avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution: {str(e)}")
    finally:
        if 'generator' in locals():
            await generator.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Processus interrompu par l'utilisateur")
    except Exception as e:
        logger.critical(f"Erreur fatale: {str(e)}")
        sys.exit(1) 