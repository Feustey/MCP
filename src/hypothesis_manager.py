#!/usr/bin/env python3
"""
Gestionnaire d'hypothèses pour la validation des changements de frais et de configuration de canaux
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from .models import FeeChangeHypothesis, ChannelConfigHypothesis, LightningMetricsHistory
from .mongo_operations import MongoOperations
from .lnbits_operations import LNbitsOperations
from .network_analyzer import NetworkAnalyzer

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HypothesisManager:
    """
    Gestionnaire d'hypothèses pour la validation des changements sur le réseau Lightning
    """
    
    def __init__(self, mongo_ops: MongoOperations, lnbits_ops: LNbitsOperations = None):
        """
        Initialise le gestionnaire d'hypothèses
        
        Args:
            mongo_ops: Instance de MongoOperations pour l'accès à la base de données
            lnbits_ops: Instance optionnelle de LNbitsOperations pour l'accès à l'API LNbits
        """
        self.mongo_ops = mongo_ops
        self.lnbits_ops = lnbits_ops
        
    async def create_fee_hypothesis(
        self,
        node_id: str,
        channel_id: str,
        new_base_fee: int,
        new_fee_rate: int,
        evaluation_period_days: int = 7
    ) -> FeeChangeHypothesis:
        """
        Crée une nouvelle hypothèse de changement de frais
        
        Args:
            node_id: ID du nœud
            channel_id: ID du canal
            new_base_fee: Nouveaux frais de base (msats)
            new_fee_rate: Nouveau taux de frais (ppm)
            evaluation_period_days: Période d'évaluation en jours
            
        Returns:
            L'hypothèse créée
        """
        # Récupération des données actuelles du canal
        channel_data = await self.mongo_ops.get_channel(channel_id)
        if not channel_data:
            raise ValueError(f"Canal {channel_id} non trouvé")
        
        # Extraction des frais actuels
        current_fee_rate = channel_data.fee_rate
        
        # Statistiques sur les 7 derniers jours
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # Récupération des métriques historiques pour la période "avant"
        history = await self.mongo_ops.get_lightning_metrics_history(
            node_id=node_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Calcul des statistiques avant le changement
        before_stats = self._calculate_node_stats(history)
        
        # Création de l'hypothèse
        hypothesis = FeeChangeHypothesis(
            node_id=node_id,
            channel_id=channel_id,
            before_base_fee=current_fee_rate.get("base_fee", 1000),
            before_fee_rate=current_fee_rate.get("fee_rate", 100),
            before_stats=before_stats,
            new_base_fee=new_base_fee,
            new_fee_rate=new_fee_rate,
            evaluation_period_days=evaluation_period_days
        )
        
        # Sauvegarde de l'hypothèse
        hypothesis_id = await self.mongo_ops.save_fee_hypothesis(hypothesis)
        
        # Mise à jour de l'ID
        hypothesis.hypothesis_id = hypothesis_id
        
        return hypothesis
    
    async def apply_fee_hypothesis(self, hypothesis_id: str) -> bool:
        """
        Applique une hypothèse de changement de frais
        
        Args:
            hypothesis_id: ID de l'hypothèse
            
        Returns:
            Succès de l'opération
        """
        # Récupération de l'hypothèse
        hypothesis = await self.mongo_ops.get_fee_hypothesis(hypothesis_id)
        if not hypothesis:
            raise ValueError(f"Hypothèse {hypothesis_id} non trouvée")
        
        if not self.lnbits_ops:
            raise ValueError("LNbitsOperations non configuré")
        
        try:
            # Application du changement via LNbits
            result = await self.lnbits_ops.update_channel_policy(
                channel_id=hypothesis.channel_id,
                fee_rate=hypothesis.new_fee_rate,
                base_fee=hypothesis.new_base_fee
            )
            
            # Mise à jour de l'hypothèse
            await self.mongo_ops.collections['fee_hypotheses'].update_one(
                {"hypothesis_id": hypothesis_id},
                {"$set": {
                    "change_applied_at": datetime.now()
                }}
            )
            
            logger.info(f"Hypothèse de frais {hypothesis_id} appliquée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'application de l'hypothèse {hypothesis_id}: {str(e)}")
            return False
    
    async def evaluate_fee_hypothesis(self, hypothesis_id: str) -> Dict[str, Any]:
        """
        Évalue une hypothèse de changement de frais
        
        Args:
            hypothesis_id: ID de l'hypothèse
            
        Returns:
            Résultats de l'évaluation
        """
        # Récupération de l'hypothèse
        hypothesis = await self.mongo_ops.get_fee_hypothesis(hypothesis_id)
        if not hypothesis:
            raise ValueError(f"Hypothèse {hypothesis_id} non trouvée")
        
        if not hypothesis.change_applied_at:
            raise ValueError(f"L'hypothèse {hypothesis_id} n'a pas encore été appliquée")
        
        # Vérification de la période d'évaluation
        now = datetime.now()
        evaluation_end = hypothesis.change_applied_at + timedelta(days=hypothesis.evaluation_period_days)
        
        if now < evaluation_end:
            days_remaining = (evaluation_end - now).days
            return {
                "status": "en_cours",
                "message": f"La période d'évaluation n'est pas terminée. {days_remaining} jours restants.",
                "days_remaining": days_remaining
            }
        
        # Statistiques sur la période après le changement
        start_date = hypothesis.change_applied_at
        end_date = now
        
        # Récupération des métriques historiques pour la période "après"
        history = await self.mongo_ops.get_lightning_metrics_history(
            node_id=hypothesis.node_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Calcul des statistiques après le changement
        after_stats = self._calculate_node_stats(history)
        
        # Calcul de l'impact
        impact_metrics = self._calculate_fee_impact_metrics(hypothesis.before_stats, after_stats)
        
        # Détermination si l'hypothèse est validée
        is_validated = impact_metrics.get("revenue_change_pct", 0) > 0
        
        # Génération de la conclusion
        conclusion = self._generate_fee_hypothesis_conclusion(hypothesis, impact_metrics)
        
        # Mise à jour de l'hypothèse
        await self.mongo_ops.update_fee_hypothesis_results(
            hypothesis_id=hypothesis_id,
            after_stats=after_stats,
            is_validated=is_validated,
            conclusion=conclusion,
            impact_metrics=impact_metrics
        )
        
        return {
            "status": "terminé",
            "is_validated": is_validated,
            "conclusion": conclusion,
            "impact_metrics": impact_metrics
        }
    
    async def create_channel_hypothesis(
        self,
        node_id: str,
        proposed_changes: Dict[str, Any],
        evaluation_period_days: int = 30
    ) -> ChannelConfigHypothesis:
        """
        Crée une nouvelle hypothèse de configuration de canaux
        
        Args:
            node_id: ID du nœud
            proposed_changes: Changements proposés
            evaluation_period_days: Période d'évaluation en jours
            
        Returns:
            L'hypothèse créée
        """
        # Récupération des données actuelles du nœud
        node_data = await self.mongo_ops.get_node(node_id)
        if not node_data:
            raise ValueError(f"Nœud {node_id} non trouvé")
        
        # Récupération des canaux du nœud
        channels = await self.mongo_ops.get_node_channels(node_id)
        
        # Configuration initiale
        initial_config = {
            "channel_count": len(channels),
            "total_capacity": sum(channel.capacity for channel in channels),
            "avg_channel_size": sum(channel.capacity for channel in channels) / len(channels) if channels else 0,
            "channel_distribution": self._calculate_channel_distribution(channels)
        }
        
        # Statistiques sur les 30 derniers jours
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Récupération des métriques historiques pour la période "avant"
        history = await self.mongo_ops.get_lightning_metrics_history(
            node_id=node_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Calcul des performances initiales
        initial_performance = self._calculate_node_stats(history)
        
        # Création de l'hypothèse
        hypothesis = ChannelConfigHypothesis(
            node_id=node_id,
            initial_config=initial_config,
            initial_performance=initial_performance,
            proposed_changes=proposed_changes,
            evaluation_period_days=evaluation_period_days
        )
        
        # Sauvegarde de l'hypothèse
        hypothesis_id = await self.mongo_ops.save_channel_hypothesis(hypothesis)
        
        # Mise à jour de l'ID
        hypothesis.hypothesis_id = hypothesis_id
        
        return hypothesis
    
    async def apply_channel_hypothesis(self, hypothesis_id: str) -> bool:
        """
        Applique une hypothèse de configuration de canaux
        
        Args:
            hypothesis_id: ID de l'hypothèse
            
        Returns:
            Succès de l'opération
        """
        # Récupération de l'hypothèse
        hypothesis = await self.mongo_ops.get_channel_hypothesis(hypothesis_id)
        if not hypothesis:
            raise ValueError(f"Hypothèse {hypothesis_id} non trouvée")
        
        if not self.lnbits_ops:
            raise ValueError("LNbitsOperations non configuré")
        
        try:
            changes = hypothesis.proposed_changes
            
            # 1. Ouverture de nouveaux canaux
            if "add_channels" in changes and isinstance(changes["add_channels"], list):
                for channel in changes["add_channels"]:
                    await self.lnbits_ops.open_channel(
                        node_id=channel.get("target_node"),
                        amount=channel.get("capacity", 1000000),
                        push_amount=channel.get("push_amount", 0)
                    )
            
            # 2. Fermeture de canaux
            if "close_channels" in changes and isinstance(changes["close_channels"], list):
                for channel in changes["close_channels"]:
                    await self.lnbits_ops.close_channel(
                        channel_id=channel.get("channel_id"),
                        force=channel.get("force", False)
                    )
            
            # 3. Rééquilibrage si demandé
            if changes.get("rebalance", False):
                # Récupération des canaux pour le rééquilibrage
                channels = await self.mongo_ops.get_node_channels(hypothesis.node_id)
                
                for channel in channels:
                    # Calculer le déséquilibre
                    local = channel.balance.get("local", 0)
                    remote = channel.balance.get("remote", 0)
                    capacity = channel.capacity
                    
                    if local > 0 and remote > 0:
                        # Calculer le ratio idéal (par défaut 50/50)
                        ideal_ratio = changes.get("ideal_balance_ratio", 0.5)
                        current_ratio = local / capacity
                        
                        # Si le déséquilibre est important, rééquilibrer
                        if abs(current_ratio - ideal_ratio) > 0.2:  # Plus de 20% de déséquilibre
                            direction = "outgoing" if current_ratio > ideal_ratio else "incoming"
                            amount = int(abs(current_ratio - ideal_ratio) * capacity)
                            
                            await self.lnbits_ops.rebalance_channel(
                                channel_id=channel.channel_id,
                                amount=amount,
                                direction=direction
                            )
            
            # Mise à jour de l'hypothèse
            await self.mongo_ops.collections['channel_hypotheses'].update_one(
                {"hypothesis_id": hypothesis_id},
                {"$set": {
                    "changes_applied_at": datetime.now()
                }}
            )
            
            logger.info(f"Hypothèse de canaux {hypothesis_id} appliquée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'application de l'hypothèse {hypothesis_id}: {str(e)}")
            return False
    
    async def evaluate_channel_hypothesis(self, hypothesis_id: str) -> Dict[str, Any]:
        """
        Évalue une hypothèse de configuration de canaux
        
        Args:
            hypothesis_id: ID de l'hypothèse
            
        Returns:
            Résultats de l'évaluation
        """
        # Récupération de l'hypothèse
        hypothesis = await self.mongo_ops.get_channel_hypothesis(hypothesis_id)
        if not hypothesis:
            raise ValueError(f"Hypothèse {hypothesis_id} non trouvée")
        
        if not hypothesis.changes_applied_at:
            raise ValueError(f"L'hypothèse {hypothesis_id} n'a pas encore été appliquée")
        
        # Vérification de la période d'évaluation
        now = datetime.now()
        evaluation_end = hypothesis.changes_applied_at + timedelta(days=hypothesis.evaluation_period_days)
        
        if now < evaluation_end:
            days_remaining = (evaluation_end - now).days
            return {
                "status": "en_cours",
                "message": f"La période d'évaluation n'est pas terminée. {days_remaining} jours restants.",
                "days_remaining": days_remaining
            }
        
        # Récupération des canaux du nœud après le changement
        channels = await self.mongo_ops.get_node_channels(hypothesis.node_id)
        
        # Configuration après
        after_config = {
            "channel_count": len(channels),
            "total_capacity": sum(channel.capacity for channel in channels),
            "avg_channel_size": sum(channel.capacity for channel in channels) / len(channels) if channels else 0,
            "channel_distribution": self._calculate_channel_distribution(channels)
        }
        
        # Statistiques sur la période après le changement
        start_date = hypothesis.changes_applied_at
        end_date = now
        
        # Récupération des métriques historiques pour la période "après"
        history = await self.mongo_ops.get_lightning_metrics_history(
            node_id=hypothesis.node_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Calcul des performances après
        after_performance = self._calculate_node_stats(history)
        
        # Calcul de l'impact
        impact_metrics = self._calculate_channel_impact_metrics(
            hypothesis.initial_config,
            hypothesis.initial_performance,
            after_config,
            after_performance
        )
        
        # Détermination si l'hypothèse est validée
        is_validated = impact_metrics.get("revenue_change_pct", 0) > 0
        
        # Génération de la conclusion
        conclusion = self._generate_channel_hypothesis_conclusion(hypothesis, impact_metrics)
        
        # Mise à jour de l'hypothèse
        await self.mongo_ops.update_channel_hypothesis_results(
            hypothesis_id=hypothesis_id,
            after_config=after_config,
            after_performance=after_performance,
            is_validated=is_validated,
            conclusion=conclusion,
            impact_metrics=impact_metrics
        )
        
        return {
            "status": "terminé",
            "is_validated": is_validated,
            "conclusion": conclusion,
            "impact_metrics": impact_metrics
        }
    
    def _calculate_node_stats(self, history: List[LightningMetricsHistory]) -> Dict[str, Any]:
        """
        Calcule les statistiques agrégées à partir de l'historique des métriques
        
        Args:
            history: Liste des métriques historiques
            
        Returns:
            Statistiques agrégées
        """
        if not history:
            return {
                "successful_forwards": 0,
                "failed_forwards": 0,
                "total_fees_earned": 0,
                "avg_daily_forwards": 0,
                "success_rate": 0,
                "data_points": 0
            }
        
        # Calcul des statistiques
        total_successful = sum(h.successful_forwards for h in history)
        total_failed = sum(h.failed_forwards for h in history)
        total_fees = sum(h.total_fees_earned for h in history)
        
        # Nombre de jours couverts
        if len(history) > 1:
            start = min(h.timestamp for h in history)
            end = max(h.timestamp for h in history)
            days = (end - start).total_seconds() / (24 * 3600)
            if days < 1:
                days = 1
        else:
            days = 1
        
        # Moyenne par jour
        avg_daily_forwards = total_successful / days
        
        # Taux de succès
        if total_successful + total_failed > 0:
            success_rate = total_successful / (total_successful + total_failed)
        else:
            success_rate = 0
        
        return {
            "successful_forwards": total_successful,
            "failed_forwards": total_failed,
            "total_fees_earned": total_fees,
            "avg_daily_forwards": avg_daily_forwards,
            "success_rate": success_rate,
            "data_points": len(history)
        }
    
    def _calculate_channel_distribution(self, channels: List[Any]) -> Dict[str, int]:
        """
        Calcule la distribution des canaux par taille
        
        Args:
            channels: Liste des canaux
            
        Returns:
            Distribution par taille
        """
        distribution = {
            "small": 0,    # < 1M sats
            "medium": 0,   # 1M - 5M sats
            "large": 0,    # > 5M sats
        }
        
        for channel in channels:
            capacity = channel.capacity
            if capacity < 1_000_000:
                distribution["small"] += 1
            elif capacity < 5_000_000:
                distribution["medium"] += 1
            else:
                distribution["large"] += 1
        
        return distribution
    
    def _calculate_fee_impact_metrics(
        self, 
        before_stats: Dict[str, Any], 
        after_stats: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calcule les métriques d'impact d'un changement de frais
        
        Args:
            before_stats: Statistiques avant le changement
            after_stats: Statistiques après le changement
            
        Returns:
            Métriques d'impact
        """
        # Calcul des variations en pourcentage
        def pct_change(before, after):
            if before == 0:
                return 100 if after > 0 else 0
            return ((after - before) / before) * 100
        
        # Extraction des valeurs
        before_forwards = before_stats.get("successful_forwards", 0)
        after_forwards = after_stats.get("successful_forwards", 0)
        
        before_fees = before_stats.get("total_fees_earned", 0)
        after_fees = after_stats.get("total_fees_earned", 0)
        
        before_success_rate = before_stats.get("success_rate", 0)
        after_success_rate = after_stats.get("success_rate", 0)
        
        before_daily = before_stats.get("avg_daily_forwards", 0)
        after_daily = after_stats.get("avg_daily_forwards", 0)
        
        # Calcul des métriques
        impact = {
            "forwards_change_pct": pct_change(before_forwards, after_forwards),
            "revenue_change_pct": pct_change(before_fees, after_fees),
            "success_rate_change_pct": pct_change(before_success_rate, after_success_rate),
            "daily_forwards_change_pct": pct_change(before_daily, after_daily),
            "avg_fee_per_forward_before": before_fees / before_forwards if before_forwards > 0 else 0,
            "avg_fee_per_forward_after": after_fees / after_forwards if after_forwards > 0 else 0
        }
        
        # Calcul du changement de frais moyen par transfert
        if before_forwards > 0 and after_forwards > 0:
            before_avg = before_fees / before_forwards
            after_avg = after_fees / after_forwards
            impact["avg_fee_change_pct"] = pct_change(before_avg, after_avg)
        else:
            impact["avg_fee_change_pct"] = 0
        
        return impact
    
    def _calculate_channel_impact_metrics(
        self, 
        before_config: Dict[str, Any], 
        before_performance: Dict[str, Any],
        after_config: Dict[str, Any], 
        after_performance: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calcule les métriques d'impact d'un changement de configuration de canaux
        
        Args:
            before_config: Configuration avant le changement
            before_performance: Performance avant le changement
            after_config: Configuration après le changement
            after_performance: Performance après le changement
            
        Returns:
            Métriques d'impact
        """
        # Calcul des variations en pourcentage
        def pct_change(before, after):
            if before == 0:
                return 100 if after > 0 else 0
            return ((after - before) / before) * 100
        
        # Configuration
        before_channels = before_config.get("channel_count", 0)
        after_channels = after_config.get("channel_count", 0)
        
        before_capacity = before_config.get("total_capacity", 0)
        after_capacity = after_config.get("total_capacity", 0)
        
        before_avg_size = before_config.get("avg_channel_size", 0)
        after_avg_size = after_config.get("avg_channel_size", 0)
        
        # Performance
        before_forwards = before_performance.get("successful_forwards", 0)
        after_forwards = after_performance.get("successful_forwards", 0)
        
        before_fees = before_performance.get("total_fees_earned", 0)
        after_fees = after_performance.get("total_fees_earned", 0)
        
        before_success_rate = before_performance.get("success_rate", 0)
        after_success_rate = after_performance.get("success_rate", 0)
        
        # Calcul des métriques
        impact = {
            # Configuration
            "channels_change_pct": pct_change(before_channels, after_channels),
            "capacity_change_pct": pct_change(before_capacity, after_capacity),
            "avg_size_change_pct": pct_change(before_avg_size, after_avg_size),
            
            # Performance
            "forwards_change_pct": pct_change(before_forwards, after_forwards),
            "revenue_change_pct": pct_change(before_fees, after_fees),
            "success_rate_change_pct": pct_change(before_success_rate, after_success_rate),
            
            # Efficacité
            "capacity_efficiency_before": before_fees / before_capacity if before_capacity > 0 else 0,
            "capacity_efficiency_after": after_fees / after_capacity if after_capacity > 0 else 0,
            "channel_efficiency_before": before_fees / before_channels if before_channels > 0 else 0,
            "channel_efficiency_after": after_fees / after_channels if after_channels > 0 else 0
        }
        
        # Calcul de l'efficacité
        if before_capacity > 0 and after_capacity > 0:
            before_eff = before_fees / before_capacity
            after_eff = after_fees / after_capacity
            impact["capacity_efficiency_change_pct"] = pct_change(before_eff, after_eff)
        else:
            impact["capacity_efficiency_change_pct"] = 0
            
        if before_channels > 0 and after_channels > 0:
            before_eff = before_fees / before_channels
            after_eff = after_fees / after_channels
            impact["channel_efficiency_change_pct"] = pct_change(before_eff, after_eff)
        else:
            impact["channel_efficiency_change_pct"] = 0
        
        return impact
    
    def _generate_fee_hypothesis_conclusion(
        self, 
        hypothesis: FeeChangeHypothesis, 
        impact_metrics: Dict[str, float]
    ) -> str:
        """
        Génère une conclusion pour l'hypothèse de changement de frais
        
        Args:
            hypothesis: Hypothèse de changement de frais
            impact_metrics: Métriques d'impact
            
        Returns:
            Conclusion
        """
        # Récupération des métriques principales
        forwards_change = impact_metrics.get("forwards_change_pct", 0)
        revenue_change = impact_metrics.get("revenue_change_pct", 0)
        success_rate_change = impact_metrics.get("success_rate_change_pct", 0)
        
        # Changement effectué
        fee_change = {
            "base_fee": hypothesis.new_base_fee - hypothesis.before_base_fee,
            "fee_rate": hypothesis.new_fee_rate - hypothesis.before_fee_rate
        }
        
        # Détermination de l'effet du changement
        if revenue_change > 0:
            if forwards_change >= 0:
                conclusion = (
                    f"L'augmentation des revenus de {revenue_change:.1f}% confirme l'hypothèse. "
                    f"Le nombre de transferts a {'augmenté' if forwards_change > 0 else 'été maintenu'} "
                    f"malgré {'l\'' if fee_change['fee_rate'] > 0 else 'la '}{'augmentation' if fee_change['fee_rate'] > 0 else 'diminution'} "
                    f"du taux de frais de {abs(fee_change['fee_rate'])} ppm."
                )
            else:
                conclusion = (
                    f"L'augmentation des revenus de {revenue_change:.1f}% confirme l'hypothèse, "
                    f"malgré une diminution du nombre de transferts de {abs(forwards_change):.1f}%. "
                    f"Les frais plus élevés ont plus que compensé la réduction du volume."
                )
        else:
            if forwards_change > 0:
                conclusion = (
                    f"Malgré l'augmentation du nombre de transferts de {forwards_change:.1f}%, "
                    f"les revenus ont diminué de {abs(revenue_change):.1f}%. "
                    f"L'hypothèse n'est pas validée, la politique de frais doit être ajustée."
                )
            else:
                conclusion = (
                    f"La diminution des revenus de {abs(revenue_change):.1f}% et du nombre de transferts "
                    f"de {abs(forwards_change):.1f}% invalide l'hypothèse. "
                    f"Le marché a réagi négativement à ce changement de frais."
                )
        
        return conclusion
    
    def _generate_channel_hypothesis_conclusion(
        self, 
        hypothesis: ChannelConfigHypothesis, 
        impact_metrics: Dict[str, float]
    ) -> str:
        """
        Génère une conclusion pour l'hypothèse de configuration de canaux
        
        Args:
            hypothesis: Hypothèse de configuration de canaux
            impact_metrics: Métriques d'impact
            
        Returns:
            Conclusion
        """
        # Récupération des métriques principales
        capacity_change = impact_metrics.get("capacity_change_pct", 0)
        revenue_change = impact_metrics.get("revenue_change_pct", 0)
        forwards_change = impact_metrics.get("forwards_change_pct", 0)
        efficiency_change = impact_metrics.get("capacity_efficiency_change_pct", 0)
        
        # Détermination de l'effet du changement
        if revenue_change > 0:
            if efficiency_change > 0:
                conclusion = (
                    f"Les modifications apportées ont été un succès avec une augmentation des revenus "
                    f"de {revenue_change:.1f}% et une amélioration de l'efficacité de la capacité "
                    f"de {efficiency_change:.1f}%. Le nombre de transferts a {'augmenté' if forwards_change > 0 else 'diminué'} "
                    f"de {abs(forwards_change):.1f}%."
                )
            else:
                conclusion = (
                    f"Les modifications ont augmenté les revenus de {revenue_change:.1f}%, "
                    f"mais l'efficacité de la capacité a diminué de {abs(efficiency_change):.1f}%. "
                    f"Considérer une optimisation supplémentaire pour améliorer l'utilisation des ressources."
                )
        else:
            if efficiency_change > 0:
                conclusion = (
                    f"Bien que l'efficacité de la capacité ait augmenté de {efficiency_change:.1f}%, "
                    f"les revenus ont diminué de {abs(revenue_change):.1f}%. "
                    f"Les modifications n'ont pas eu l'effet escompté sur le routage des paiements."
                )
            else:
                conclusion = (
                    f"Les modifications n'ont pas eu l'effet souhaité. Les revenus ont diminué "
                    f"de {abs(revenue_change):.1f}% et l'efficacité de la capacité a diminué "
                    f"de {abs(efficiency_change):.1f}%. Une révision de la stratégie de canaux est nécessaire."
                )
        
        return conclusion 