#!/usr/bin/env python3
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LiquidityScanManager:
    """Gestionnaire de scan de liquidité inspiré par LNRouter pour tester la capacité de routage réelle des canaux."""
    
    def __init__(self, lnbits_client, test_amount_sats=500_000, min_channel_capacity=2_500_000):
        """
        Initialise le scanner de liquidité.
        
        Args:
            lnbits_client: Client LNBits pour interagir avec le nœud
            test_amount_sats: Montant du paiement test (500k sats selon LNRouter)
            min_channel_capacity: Capacité minimale des canaux à tester (2.5M sats selon LNRouter)
        """
        self.lnbits_client = lnbits_client
        self.test_amount_sats = test_amount_sats
        self.min_channel_capacity = min_channel_capacity
        self.scan_results = {}
        self.data_dir = Path("rag/RAG_assets/market_data")
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
    async def is_node_eligible(self, node_pubkey: str) -> bool:
        """
        Vérifie si un nœud est éligible pour le test selon les critères LNRouter.
        
        Critères:
        - Au moins 15 canaux de 2.5M sats (avec des pairs uniques)
        - Au moins 6 canaux avec 500k sats de capacité entrante
        """
        try:
            channels = await self.lnbits_client.get_node_channels(node_pubkey)
            
            # Filtrer les canaux de capacité suffisante
            large_channels = [c for c in channels if c.get("capacity", 0) >= self.min_channel_capacity]
            
            # Regrouper par pair pour éviter de compter les canaux multiples avec le même pair
            unique_peers: Set[str] = set()
            for channel in large_channels:
                remote_pubkey = channel.get("remote_pubkey")
                if remote_pubkey:
                    unique_peers.add(remote_pubkey)
            
            # Vérifier s'il y a au moins 15 canaux uniques de capacité suffisante
            if len(unique_peers) < 15:
                logger.info(f"Nœud {node_pubkey} non éligible: seulement {len(unique_peers)} pairs uniques avec canaux suffisants")
                return False
                
            # Vérifier qu'au moins 6 canaux ont une capacité entrante suffisante
            inbound_channels = [c for c in large_channels if c.get("remote_balance", 0) >= self.test_amount_sats]
            inbound_peers = set([c.get("remote_pubkey") for c in inbound_channels if c.get("remote_pubkey")])
            
            if len(inbound_peers) < 6:
                logger.info(f"Nœud {node_pubkey} non éligible: seulement {len(inbound_peers)} pairs avec capacité entrante suffisante")
                return False
                
            logger.info(f"Nœud {node_pubkey} éligible pour le scan de liquidité")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification d'éligibilité du nœud {node_pubkey}: {e}")
            return False
        
    async def scan_channel_liquidity(self, channel_id: str, source_node: str, target_node: str) -> Dict[str, Any]:
        """
        Teste la liquidité bidirectionnelle d'un canal en envoyant des paiements tests.
        """
        results = {
            "channel_id": channel_id,
            "source": source_node,
            "target": target_node,
            "outbound_success": False,
            "inbound_success": False,
            "scan_time": datetime.now().isoformat()
        }
        
        # Test dans la direction sortante (source -> target)
        try:
            logger.info(f"Test de liquidité sortante pour le canal {channel_id}")
            outbound_result = await self.lnbits_client.send_test_payment(
                source_node, 
                target_node,
                amount_sats=self.test_amount_sats,
                channel_hint=channel_id
            )
            results["outbound_success"] = outbound_result.get("success", False)
            if results["outbound_success"]:
                logger.info(f"Test de liquidité sortante réussi pour le canal {channel_id}")
            else:
                logger.info(f"Test de liquidité sortante échoué pour le canal {channel_id}: {outbound_result.get('error', 'Raison inconnue')}")
        except Exception as e:
            results["outbound_error"] = str(e)
            logger.error(f"Erreur lors du test de liquidité sortante pour le canal {channel_id}: {e}")
        
        # Pause entre les tests pour éviter les problèmes de rate-limiting
        await asyncio.sleep(1)
        
        # Test dans la direction entrante (target -> source)
        try:
            logger.info(f"Test de liquidité entrante pour le canal {channel_id}")
            inbound_result = await self.lnbits_client.send_test_payment(
                target_node,
                source_node,
                amount_sats=self.test_amount_sats,
                channel_hint=channel_id
            )
            results["inbound_success"] = inbound_result.get("success", False)
            if results["inbound_success"]:
                logger.info(f"Test de liquidité entrante réussi pour le canal {channel_id}")
            else:
                logger.info(f"Test de liquidité entrante échoué pour le canal {channel_id}: {inbound_result.get('error', 'Raison inconnue')}")
        except Exception as e:
            results["inbound_error"] = str(e)
            logger.error(f"Erreur lors du test de liquidité entrante pour le canal {channel_id}: {e}")
            
        # Stocker les résultats
        self.scan_results[channel_id] = results
        return results
        
    async def bulk_scan_node_channels(self, node_pubkey: str, sample_size: int = 10) -> Dict[str, Any]:
        """
        Échantillonne et teste un sous-ensemble de canaux d'un nœud.
        
        Args:
            node_pubkey: Clé publique du nœud à tester
            sample_size: Nombre de canaux à tester (max)
            
        Returns:
            Dict contenant les résultats du scan
        """
        logger.info(f"Début du scan pour le nœud {node_pubkey}")
        
        # Vérifier l'éligibilité du nœud
        if not await self.is_node_eligible(node_pubkey):
            logger.info(f"Nœud {node_pubkey} non éligible pour le scan")
            return {"eligible": False, "results": []}
            
        try:
            # Récupérer les canaux du nœud
            channels = await self.lnbits_client.get_node_channels(node_pubkey)
            large_channels = [c for c in channels if c.get("capacity", 0) >= self.min_channel_capacity]
            
            # Prioriser les canaux de plus grande capacité
            large_channels.sort(key=lambda c: c.get("capacity", 0), reverse=True)
            
            # Limiter à l'échantillon demandé
            test_channels = large_channels[:sample_size]
            
            logger.info(f"Lancement du scan pour {len(test_channels)} canaux du nœud {node_pubkey}")
            
            results = []
            for i, channel in enumerate(test_channels):
                channel_id = channel.get("channel_id")
                remote_pubkey = channel.get("remote_pubkey")
                
                if not channel_id or not remote_pubkey:
                    continue
                    
                logger.info(f"Scan du canal {i+1}/{len(test_channels)}: {channel_id}")
                
                channel_result = await self.scan_channel_liquidity(
                    channel_id,
                    node_pubkey,
                    remote_pubkey
                )
                results.append(channel_result)
                
                # Pause entre les tests pour éviter les problèmes de rate-limiting
                await asyncio.sleep(2)
                
            scan_summary = {
                "eligible": True,
                "node_pubkey": node_pubkey,
                "total_channels": len(large_channels),
                "tested_channels": len(results),
                "bidirectional_count": sum(1 for r in results if r["outbound_success"] and r["inbound_success"]),
                "outbound_only_count": sum(1 for r in results if r["outbound_success"] and not r["inbound_success"]),
                "inbound_only_count": sum(1 for r in results if not r["outbound_success"] and r["inbound_success"]),
                "failed_count": sum(1 for r in results if not r["outbound_success"] and not r["inbound_success"]),
                "scan_time": datetime.now().isoformat(),
                "results": results
            }
            
            # Calculer les pourcentages
            if results:
                scan_summary["bidirectional_percent"] = scan_summary["bidirectional_count"] / len(results) * 100
                scan_summary["liquidity_score"] = self.calculate_liquidity_score(scan_summary)
            
            return scan_summary
            
        except Exception as e:
            logger.error(f"Erreur lors du scan du nœud {node_pubkey}: {e}")
            return {
                "eligible": True,
                "node_pubkey": node_pubkey,
                "error": str(e),
                "results": []
            }
    
    def calculate_liquidity_score(self, scan_data: Dict[str, Any]) -> float:
        """
        Calcule un score de liquidité pour un nœud basé sur les résultats du scan.
        
        Args:
            scan_data: Données du scan du nœud
            
        Returns:
            Score de liquidité entre 0 et 100
        """
        if not scan_data.get("results"):
            return 0
            
        # Éléments du score:
        # 1. Pourcentage de canaux bidirectionnels (poids important)
        # 2. Pourcentage de canaux avec liquidité sortante (poids modéré)
        # 3. Pourcentage de canaux avec liquidité entrante (poids modéré)
        
        total_channels = len(scan_data["results"])
        bidirectional = scan_data["bidirectional_count"]
        outbound_only = scan_data["outbound_only_count"]
        inbound_only = scan_data["inbound_only_count"]
        
        # Formule de score pondérée
        score = (
            (bidirectional / total_channels * 100) * 0.7 +  # 70% du poids pour les canaux bidirectionnels
            (outbound_only / total_channels * 100) * 0.15 +  # 15% du poids pour les canaux sortants uniquement
            (inbound_only / total_channels * 100) * 0.15     # 15% du poids pour les canaux entrants uniquement
        )
        
        return min(100, score)
    
    async def save_scan_results(self, node_aliases: Dict[str, str] = None) -> str:
        """
        Sauvegarde les résultats du scan dans un fichier JSON.
        
        Args:
            node_aliases: Dictionnaire des alias des nœuds (pubkey -> alias)
            
        Returns:
            Chemin du fichier de résultats
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self.data_dir / f"liquidity_scan_results_{timestamp}.json"
        
        # Compiler les résultats agrégés par nœud
        node_results = {}
        
        for channel_id, result in self.scan_results.items():
            source = result.get("source", "")
            target = result.get("target", "")
            
            # Agréger les résultats pour le nœud source
            if source not in node_results:
                node_results[source] = {
                    "total_channels_tested": 0,
                    "bidirectional_count": 0,
                    "outbound_only_count": 0,
                    "inbound_only_count": 0,
                    "failed_count": 0,
                    "liquidity_score": 0,
                    "alias": node_aliases.get(source, "Unknown") if node_aliases else "Unknown",
                    "last_scan": result.get("scan_time", "")
                }
            
            # Incrémenter les compteurs
            node_entry = node_results[source]
            node_entry["total_channels_tested"] += 1
            
            outbound = result.get("outbound_success", False)
            inbound = result.get("inbound_success", False)
            
            if outbound and inbound:
                node_entry["bidirectional_count"] += 1
            elif outbound:
                node_entry["outbound_only_count"] += 1
            elif inbound:
                node_entry["inbound_only_count"] += 1
            else:
                node_entry["failed_count"] += 1
        
        # Calculer les scores finaux pour chaque nœud
        for pubkey, data in node_results.items():
            if data["total_channels_tested"] > 0:
                data["bidirectional_ratio"] = data["bidirectional_count"] / data["total_channels_tested"]
                
                # Score de liquidité basé sur la même formule que calculate_liquidity_score
                total = data["total_channels_tested"]
                data["liquidity_score"] = min(100, (
                    (data["bidirectional_count"] / total * 100) * 0.7 +
                    (data["outbound_only_count"] / total * 100) * 0.15 +
                    (data["inbound_only_count"] / total * 100) * 0.15
                ))
        
        # Sauvegarder les résultats
        with open(file_path, "w") as f:
            json.dump({
                "scan_date": datetime.now().isoformat(),
                "test_amount_sats": self.test_amount_sats,
                "min_channel_capacity": self.min_channel_capacity,
                "node_results": node_results,
                "methodology": "LNRouter Liquidity Scan"
            }, f, indent=2)
        
        logger.info(f"Résultats du scan de liquidité sauvegardés dans {file_path}")
        
        # Créer un lien symbolique vers le dernier résultat
        latest_link = self.data_dir / "latest_liquidity_scan.json"
        if latest_link.exists():
            latest_link.unlink()
        latest_link.symlink_to(file_path.name)
        
        return str(file_path)

async def get_popular_lightning_nodes() -> List[Dict[str, Any]]:
    """
    Récupère la liste des nœuds Lightning populaires pour le scan.
    
    Returns:
        Liste des nœuds populaires avec leurs métadonnées
    """
    # Note: Cette fonction est un placeholder - dans une implémentation réelle,
    # elle pourrait interroger une API comme 1ML, Amboss ou LNRouter pour obtenir
    # les nœuds les plus importants du réseau.
    
    # Exemple de nœuds populaires (à remplacer par une requête réelle dans l'implémentation)
    popular_nodes = [
        {
            "pubkey": "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f",
            "alias": "ACINQ",
            "capacity": 170000000000
        },
        {
            "pubkey": "02d4531a2f2e6e5a9033d37d548cff4834a3898e74c3abe1985b237bd54da3bae5",
            "alias": "Kraken",
            "capacity": 150000000000
        },
        {
            "pubkey": "0242a4ae0c5bef18048fbecf995094b74bfb0f7391418d71ed394784373f41e4f3",
            "alias": "CoinGate",
            "capacity": 130000000000
        },
        {
            "pubkey": "03c2abfa93eacec04721c019644584424aab2ba4dff3ac9bdab4e9c97007491dda",
            "alias": "River",
            "capacity": 120000000000
        },
        {
            "pubkey": "033d8656219478701227199cbd6f670335c8d408a92ae88b962c49d4dc0e83e025",
            "alias": "Blixt",
            "capacity": 100000000000
        }
    ]
    
    logger.info(f"Récupération de {len(popular_nodes)} nœuds Lightning populaires")
    return popular_nodes 