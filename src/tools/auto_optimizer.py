#!/usr/bin/env python3
# coding: utf-8
"""
Module d'optimisation automatique des nœuds Lightning.
Applique les recommandations d'actions basées sur l'évaluation des nœuds.

Dernière mise à jour: 10 mai 2025
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger("auto_optimizer")

class NodeOptimizer:
    def __init__(self, client_factory):
        self.client_factory = client_factory
        self.last_action_timestamp = None
        self.action_history = []
        
    def apply_recommendations(self, node_id, evaluation_result, dry_run=False):
        """
        Applique les recommandations automatiquement en fonction du profil détecté
        
        Args:
            node_id: ID du nœud
            evaluation_result: Résultat de l'évaluation du nœud
            dry_run: Mode simulation sans appliquer les changements
            
        Returns:
            Liste des actions effectuées ou simulées
        """
        recommendation = evaluation_result["recommendation"]
        profile = evaluation_result["profile"]
        liquidity_balance = evaluation_result.get("avg_outbound_ratio", 50) / 100.0
        
        actions = []
        
        logger.info(f"Application des recommandations pour le nœud {node_id}")
        logger.info(f"Profil: {profile}, Recommandation: {recommendation}")
        logger.info(f"Équilibre de liquidité: {liquidity_balance:.2f} (idéal: 0.5)")
        
        # Vérifier d'abord l'équilibre de liquidité
        if abs(liquidity_balance - 0.5) > 0.25:  # Déséquilibre significatif (< 25% ou > 75%)
            logger.info(f"Déséquilibre de liquidité détecté: {liquidity_balance:.2f} - rééquilibrage prioritaire")
            actions.append(self._rebalance_channels(node_id, emergency=(abs(liquidity_balance - 0.5) > 0.35), dry_run=dry_run))
        
        # Ensuite traiter les autres problèmes
        if "CRITIQUE" in recommendation:
            # Action prioritaire si pas déjà traitée par le rééquilibrage
            if not actions:  
                logger.info("Action CRITIQUE détectée - rééquilibrage d'urgence")
                actions.append(self._rebalance_channels(node_id, emergency=True, dry_run=dry_run))
            
        if "Taux de succès faible" in recommendation:
            # Ajuster les frais à la baisse
            logger.info("Taux de succès faible détecté - ajustement des frais à la baisse")
            actions.append(self._adjust_fees(node_id, direction=-1, dry_run=dry_run))
            
        if "Fort volume mais faibles frais" in recommendation:
            # Augmenter les frais progressivement
            logger.info("Fort volume avec frais faibles détecté - augmentation des frais")
            actions.append(self._adjust_fees(node_id, direction=1, dry_run=dry_run))
            
        if "Déséquilibre de liquidité" in recommendation and not any(a.get('action', '').startswith('rebalance') for a in actions):
            # Rééquilibrage standard si pas déjà fait
            logger.info("Déséquilibre de liquidité détecté - rééquilibrage standard")
            actions.append(self._rebalance_channels(node_id, emergency=False, dry_run=dry_run))
            
        # Enregistrer les actions pour apprentissage
        if not dry_run and actions:
            self.last_action_timestamp = datetime.now()
            self.action_history.append({
                "timestamp": self.last_action_timestamp,
                "node_id": node_id,
                "profile": profile,
                "actions": actions,
                "evaluation": evaluation_result
            })
            logger.info(f"Actions enregistrées: {len(actions)}")
        elif not actions:
            logger.info("Aucune action à effectuer")
            
        return actions
        
    def _adjust_fees(self, node_id, direction, dry_run=False):
        """
        Ajuste les frais d'un nœud en fonction de sa performance
        
        Args:
            node_id: ID du nœud
            direction: Direction d'ajustement (1=augmenter, -1=diminuer)
            dry_run: Mode simulation
            
        Returns:
            Détails de l'action effectuée
        """
        client = self.client_factory.get_client(node_id)
        
        # Calculer les nouveaux frais
        current_fees = client.get_current_fees()
        adjustment_factor = 1.15 if direction > 0 else 0.85
        
        new_fees = {
            channel_id: {
                "base_fee": int(fee["base_fee"] * adjustment_factor),
                "fee_rate": int(fee["fee_rate"] * adjustment_factor)
            }
            for channel_id, fee in current_fees.items()
        }
        
        if not dry_run:
            logger.info(f"Ajustement des frais pour {len(new_fees)} canaux, facteur: {adjustment_factor}")
            result = client.update_channel_fees(new_fees)
            logger.info(f"Résultat de l'ajustement: {result}")
            return {
                "action": "fee_adjustment",
                "direction": "increase" if direction > 0 else "decrease",
                "channels_updated": len(result.get("updated", [])),
                "success": result.get("success", False),
                "timestamp": datetime.now().isoformat()
            }
        else:
            logger.info(f"Simulation d'ajustement des frais pour {len(new_fees)} canaux")
            return {
                "action": "fee_adjustment_dry_run",
                "direction": "increase" if direction > 0 else "decrease",
                "channels_to_update": len(new_fees),
                "timestamp": datetime.now().isoformat()
            }
    
    def _rebalance_channels(self, node_id, emergency=False, dry_run=False):
        """
        Rééquilibre les canaux d'un nœud
        
        Args:
            node_id: ID du nœud
            emergency: Mode urgence (seuil de déséquilibre plus bas)
            dry_run: Mode simulation
            
        Returns:
            Détails de l'action effectuée
        """
        client = self.client_factory.get_client(node_id)
        
        # Identifier les canaux à rééquilibrer (déséquilibre > 70%)
        channels = client.get_channels()
        unbalanced = []
        
        for channel in channels:
            local = channel.get("local_balance", 0)
            remote = channel.get("remote_balance", 0)
            total = local + remote
            
            if total == 0:
                continue
                
            local_ratio = local / total
            
            # Dans une situation d'urgence, on rééquilibre plus de canaux
            threshold = 0.7 if not emergency else 0.6
            
            if local_ratio > threshold or local_ratio < (1 - threshold):
                unbalanced.append({
                    "channel_id": channel.get("channel_id"),
                    "local_ratio": local_ratio,
                    "capacity": total
                })
        
        if not dry_run:
            logger.info(f"Rééquilibrage de {len(unbalanced)} canaux (emergency={emergency})")
            result = client.rebalance_channels(unbalanced)
            logger.info(f"Résultat du rééquilibrage: {result}")
            return {
                "action": "rebalance",
                "emergency": emergency,
                "channels_rebalanced": len(result.get("rebalanced", [])),
                "success": result.get("success", False),
                "timestamp": datetime.now().isoformat()
            }
        else:
            logger.info(f"Simulation de rééquilibrage pour {len(unbalanced)} canaux")
            return {
                "action": "rebalance_dry_run",
                "emergency": emergency,
                "channels_to_rebalance": len(unbalanced),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_action_history(self, node_id=None, limit=10):
        """
        Récupère l'historique des actions effectuées
        
        Args:
            node_id: Filtrer par ID de nœud (optionnel)
            limit: Nombre maximal d'entrées à retourner
            
        Returns:
            Liste des actions effectuées
        """
        if node_id:
            history = [a for a in self.action_history if a["node_id"] == node_id]
        else:
            history = self.action_history.copy()
            
        # Trier par timestamp décroissant
        history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return history[:limit] 