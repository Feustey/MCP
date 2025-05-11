#!/usr/bin/env python3
"""
Core Fee Optimizer - Pipeline centralisé d'optimisation des frais pour les nœuds Lightning

Ce module orchestre l'ensemble du processus d'optimisation des frais :
1. Collecte dynamique des données (via API LND/LNbits)
2. Évaluation et scoring des canaux
3. Prise de décision pour chaque canal
4. Application des modifications (avec option dry-run)
5. Mécanisme de rollback transactionnel en cas d'échec
6. Logging et monitoring de chaque étape

Dernière mise à jour: 15 mai 2025
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import traceback

# Imports internes au projet (à adapter selon l'intégration réelle)
from src.optimizers.scoring_utils import evaluate_node, DecisionType
from src.optimizers.fee_update_utils import update_channel_fees, get_fee_adjustment
from src.clients.lnd_client import LNDClient
# from src.clients.lnbits_client import LNBitsClient

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/fee_optimizer.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("core_fee_optimizer")

BACKUP_DIR = Path("data/rollbacks")
BACKUP_DIR.mkdir(exist_ok=True, parents=True)

class OptimizationError(Exception):
    """Exception personnalisée pour les erreurs d'optimisation"""
    pass

class CoreFeeOptimizer:
    """
    Pipeline centralisé pour l'optimisation transactionnelle des frais Lightning.
    """
    def __init__(self, node_pubkey: str, dry_run: bool = True, max_changes_per_run: int = 5, backup_enabled: bool = True, lnd_host: str = None, lnd_port: int = None, macaroon_path: str = None, tls_cert_path: str = None):
        self.node_pubkey = node_pubkey
        self.dry_run = dry_run
        self.max_changes_per_run = max_changes_per_run
        self.backup_enabled = backup_enabled
        self.original_state = {}
        self.applied_changes = []
        self.successful_changes = []
        self.failed_changes = []
        self.run_id = f"{int(time.time())}_{node_pubkey[:8]}"
        logger.info(f"Initialisation du pipeline pour le nœud {node_pubkey[:8]} (dry-run={dry_run})")
        # Initialisation du client LND REST avec paramètres explicites ou variables d'env
        self.lnd_client = LNDClient(
            host=lnd_host,
            port=lnd_port,
            macaroon_path=macaroon_path,
            tls_cert_path=tls_cert_path
        )
        # Pour le noeud feustey, possibilité d'ajouter une config dédiée ici si besoin
        self.local_pubkey = node_pubkey  # Pour la sélection de la bonne policy
        # TODO: Initialiser LNBitsClient si besoin

    async def run_pipeline(self) -> Dict[str, Any]:
        """
        Exécute le pipeline complet d'optimisation transactionnelle.
        """
        start_time = time.time()
        results = {
            "status": "unknown",
            "run_id": self.run_id,
            "node_pubkey": self.node_pubkey,
            "timestamp": datetime.now().isoformat(),
            "dry_run": self.dry_run,
            "duration_seconds": 0,
            "changes_applied": 0,
            "changes_failed": 0,
            "total_channels_processed": 0,
            "errors": []
        }
        try:
            # 1. Collecte des données dynamiques (à remplacer par l'appel réel)
            node_data = await self._collect_node_data()
            results["total_channels_processed"] = len(node_data.get("channels", []))
            # 2. Scoring et recommandations (à remplacer par l'appel réel)
            evaluation_results = await self._evaluate_channels(node_data)
            # 3. Sélection des canaux à modifier
            channels_to_update = await self._select_channels_for_update(evaluation_results)
            # 4. Sauvegarde de l'état initial (rollback)
            if self.backup_enabled:
                await self._backup_channel_state(channels_to_update)
            # 5. Application des modifications (ou dry-run)
            update_results = await self._apply_fee_changes(channels_to_update)
            results["changes_applied"] = len(self.successful_changes)
            results["changes_failed"] = len(self.failed_changes)
            results["channels_updated"] = [c.get("channel_id") for c in self.successful_changes]
            results["update_results"] = update_results
            results["status"] = "success"
        except Exception as e:
            error_details = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc()
            }
            logger.error(f"Erreur dans le pipeline: {e}", exc_info=True)
            # Rollback si nécessaire
            if self.applied_changes and self.backup_enabled:
                logger.warning("Tentative de rollback...")
                try:
                    rollback_result = await self._perform_rollback()
                    error_details["rollback_result"] = rollback_result
                except Exception as rollback_err:
                    logger.error(f"Erreur lors du rollback: {rollback_err}", exc_info=True)
                    error_details["rollback_error"] = str(rollback_err)
            results["status"] = "error"
            results["errors"].append(error_details)
        finally:
            results["duration_seconds"] = round(time.time() - start_time, 2)
            self._save_results(results)
            logger.info(f"Pipeline terminé en {results['duration_seconds']}s avec statut: {results['status']}")
        return results

    async def _collect_node_data(self) -> Dict[str, Any]:
        """
        Collecte dynamique des données du nœud via LNDClient.
        """
        logger.info("1. Collecte des données du nœud...")
        node_info = await self.lnd_client.get_node_info(self.node_pubkey)
        channels = await self.lnd_client.get_channels()
        # Récupérer les métriques globales (à adapter selon l'API)
        metrics = await self.lnd_client.get_node_metrics(self.node_pubkey)
        node_data = {
            "node_id": self.node_pubkey,
            "alias": node_info.get("alias", "unknown"),
            "channels": channels,
            "metrics": metrics
        }
        return node_data

    async def _evaluate_channels(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Évaluation/scoring des canaux via evaluate_node.
        """
        logger.info("2. Évaluation/scoring des canaux...")
        return evaluate_node(node_data)

    async def _select_channels_for_update(self, evaluation_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Sélectionne les canaux à modifier selon la recommandation et la confiance.
        """
        logger.info("3. Sélection des canaux à modifier...")
        channel_scores = evaluation_results.get("channel_scores", [])
        channels_to_update = []
        for channel_score in channel_scores:
            recommendation = channel_score.get("recommendation")
            confidence = channel_score.get("confidence", 0)
            total_score = channel_score.get("total_score", 0)
            channel_id = channel_score.get("channel_id", "unknown")
            # On ne retient que les canaux à ajuster
            if recommendation in [DecisionType.INCREASE_FEES, DecisionType.LOWER_FEES] and confidence >= 0.7:
                # Récupérer les infos du canal
                channel_info = await self.lnd_client.get_channel_info(channel_id)
                channel_info["recommendation"] = recommendation
                channel_info["confidence"] = confidence
                channel_info["score"] = total_score
                channel_info["scores"] = channel_score.get("scores", {})
                channels_to_update.append(channel_info)
        # Limiter le nombre de canaux à modifier
        channels_to_update = sorted(channels_to_update, key=lambda x: x.get("confidence", 0), reverse=True)[:self.max_changes_per_run]
        return channels_to_update

    async def _backup_channel_state(self, channels: List[Dict[str, Any]]) -> str:
        """
        Sauvegarde la politique de frais actuelle de chaque canal via LNDClient.
        """
        logger.info("4. Sauvegarde de l'état initial...")
        backup_data = {"run_id": self.run_id, "timestamp": datetime.now().isoformat(), "node_pubkey": self.node_pubkey, "channels": {}}
        for channel in channels:
            channel_id = channel.get("channel_id", "unknown")
            channel_point = channel.get("channel_point", "unknown")
            policy_dict = await self.lnd_client.get_channel_policy(channel_id)
            # Sélection de la bonne policy selon le sens (on suppose feustey = node1 ou node2)
            channel_info = await self.lnd_client.get_channel_info(channel_id)
            node1_pubkey = channel_info.get("node1_pubkey")
            node2_pubkey = channel_info.get("node2_pubkey")
            if self.local_pubkey == node1_pubkey:
                current_policy = policy_dict.get("node1_policy", {})
            elif self.local_pubkey == node2_pubkey:
                current_policy = policy_dict.get("node2_policy", {})
            else:
                current_policy = policy_dict.get("node1_policy", {})  # fallback
            backup_data["channels"][channel_id] = {"channel_point": channel_point, "policy": current_policy}
            self.original_state[channel_id] = {"channel_point": channel_point, "policy": current_policy}
        backup_file = BACKUP_DIR / f"backup_{self.run_id}.json"
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        logger.info(f"Sauvegarde créée: {backup_file}")
        return str(backup_file)

    async def _apply_fee_changes(self, channels: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Applique les changements de frais via update_channel_fees.
        """
        logger.info(f"5. Application des modifications de frais {'(DRY-RUN)' if self.dry_run else ''}...")
        results = {"successful": [], "failed": []}
        for channel in channels:
            channel_id = channel.get("channel_id", "unknown")
            channel_point = channel.get("channel_point", "unknown")
            recommendation = channel.get("recommendation", DecisionType.NO_ACTION)
            policy_dict = await self.lnd_client.get_channel_policy(channel_id)
            channel_info = await self.lnd_client.get_channel_info(channel_id)
            node1_pubkey = channel_info.get("node1_pubkey")
            node2_pubkey = channel_info.get("node2_pubkey")
            if self.local_pubkey == node1_pubkey:
                current_policy = policy_dict.get("node1_policy", {})
            elif self.local_pubkey == node2_pubkey:
                current_policy = policy_dict.get("node2_policy", {})
            else:
                current_policy = policy_dict.get("node1_policy", {})  # fallback
            current_base_fee = int(current_policy.get("base_fee_msat", 1000))
            current_fee_rate = int(current_policy.get("fee_rate_ppm", 1))
            adjustment = get_fee_adjustment(
                current_base_fee=current_base_fee,
                current_fee_rate=current_fee_rate,
                forward_success_rate=channel.get("scores", {}).get("success_rate", 0.5),
                channel_activity=channel.get("scores", {}).get("activity", 0),
            )
            new_base_fee, new_fee_rate = adjustment
            update_result = await update_channel_fees(
                self.lnd_client, channel_id, new_base_fee, new_fee_rate, self.dry_run
            )
            if update_result["success"]:
                change_info = {
                    "channel_id": channel_id,
                    "channel_point": channel_point,
                    "old_policy": {"base_fee_msat": current_base_fee, "fee_rate_ppm": current_fee_rate},
                    "new_policy": {"base_fee_msat": new_base_fee, "fee_rate_ppm": new_fee_rate},
                    "recommendation": recommendation,
                    "timestamp": datetime.now().isoformat()
                }
                self.applied_changes.append(change_info)
                self.successful_changes.append(change_info)
                results["successful"].append(change_info)
            else:
                failure_info = {
                    "channel_id": channel_id,
                    "channel_point": channel_point,
                    "error": update_result.get("error", "Erreur inconnue"),
                    "recommendation": recommendation
                }
                self.failed_changes.append(failure_info)
                results["failed"].append(failure_info)
        return results

    async def _perform_rollback(self) -> Dict[str, Any]:
        """
        Rollback transactionnel en cas d'échec.
        """
        logger.warning("Exécution du rollback...")
        results = {"successful": [], "failed": [], "total": len(self.applied_changes)}
        for change in self.applied_changes:
            channel_id = change.get("channel_id", "unknown")
            channel_point = change.get("channel_point", "unknown")
            if channel_id in self.original_state:
                original_policy = self.original_state[channel_id]["policy"]
                update_result = await update_channel_fees(
                    self.lnd_client, channel_id, original_policy.get("base_fee_msat", 1000), original_policy.get("fee_rate_ppm", 1), self.dry_run
                )
                if update_result["success"]:
                    results["successful"].append(channel_id)
                else:
                    results["failed"].append({"channel_id": channel_id, "error": update_result.get("error", "Erreur inconnue")})
            else:
                results["failed"].append({"channel_id": channel_id, "error": "Politique originale non trouvée"})
        return results

    def _save_results(self, results: Dict[str, Any]) -> str:
        """
        Sauvegarde les résultats du pipeline dans un fichier.
        """
        reports_dir = Path("data/reports/fee_optimization")
        reports_dir.mkdir(exist_ok=True, parents=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{self.node_pubkey[:8]}_optimization.json"
        filepath = reports_dir / filename
        try:
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Résultats sauvegardés dans {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des résultats: {e}")
            return ""

async def main_async():
    parser = argparse.ArgumentParser(description='Pipeline d\'optimisation des frais Lightning')
    parser.add_argument('--node', type=str, required=True, help='Clé publique du nœud à optimiser')
    parser.add_argument('--dry-run', action='store_true', help='Mode simulation sans application réelle')
    parser.add_argument('--max-changes', type=int, default=5, help='Nombre maximum de canaux à modifier')
    parser.add_argument('--no-backup', action='store_true', help='Désactiver les sauvegardes pour rollback')
    parser.add_argument('--lnd-host', type=str, default=None, help='Host LND REST (ex: https://127.0.0.1)')
    parser.add_argument('--lnd-port', type=int, default=None, help='Port LND REST (ex: 8080)')
    parser.add_argument('--macaroon-path', type=str, default=None, help='Chemin du fichier macaroon')
    parser.add_argument('--tls-cert-path', type=str, default=None, help='Chemin du certificat TLS')
    args = parser.parse_args()
    optimizer = CoreFeeOptimizer(
        node_pubkey=args.node,
        dry_run=args.dry_run,
        max_changes_per_run=args.max_changes,
        backup_enabled=not args.no_backup,
        lnd_host=args.lnd_host,
        lnd_port=args.lnd_port,
        macaroon_path=args.macaroon_path,
        tls_cert_path=args.tls_cert_path
    )
    results = await optimizer.run_pipeline()
    status_emoji = "✅" if results["status"] == "success" else "❌"
    print(f"\n{status_emoji} Optimisation des frais pour {args.node[:8]}: {results['status']}")
    print(f"  - Mode dry-run: {args.dry_run}")
    print(f"  - Canaux modifiés: {results['changes_applied']}/{results['total_channels_processed']}")
    print(f"  - Durée: {results['duration_seconds']} secondes")
    if results["status"] == "error":
        print(f"\n❌ Erreurs rencontrées:")
        for error in results["errors"]:
            print(f"  - {error.get('error_message', 'Erreur inconnue')}")
    return 0 if results["status"] == "success" else 1

def main():
    try:
        exit_code = asyncio.run(main_async())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nInterruption de l'utilisateur. Arrêt du pipeline.")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Erreur critique: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 