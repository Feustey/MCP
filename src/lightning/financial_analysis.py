"""
Analyse financière et optimisation des frais pour Lightning Network
Calcul des revenus, ROI, optimisation des structures tarifaires
"""

import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from collections import defaultdict
import pandas as pd

logger = logging.getLogger("mcp.financial_analysis")

@dataclass
class ChannelMetrics:
    """Métriques d'un canal pour l'analyse financière"""
    channel_id: str
    capacity: int
    local_balance: int
    remote_balance: int
    fee_rate_ppm: int
    base_fee_msat: int
    volume_7d: int = 0
    volume_30d: int = 0
    revenue_7d: int = 0
    revenue_30d: int = 0
    success_rate: float = 0.0
    avg_payment_size: int = 0

@dataclass
class NodeFinancials:
    """État financier d'un nœud Lightning"""
    total_capacity: int
    total_local_balance: int
    total_remote_balance: int
    total_revenue_7d: int
    total_revenue_30d: int
    total_volume_7d: int
    total_volume_30d: int
    channel_count: int
    avg_success_rate: float

class LightningFinancialAnalyzer:
    """
    Analyseur financier complet pour nœuds Lightning Network
    """
    
    def __init__(self):
        self.btc_price_usd = 45000  # Prix par défaut, à mettre à jour via API
        self.market_data = {}
        
    def set_btc_price(self, price_usd: float):
        """Met à jour le prix BTC pour les calculs USD"""
        self.btc_price_usd = price_usd
        
    def analyze_node_financials(self, 
                               node_pubkey: str,
                               channels: List[Dict],
                               payment_history: List[Dict] = None,
                               timeframe_days: int = 30) -> Dict[str, Any]:
        """
        Analyse financière complète d'un nœud
        """
        try:
            # Parser les données des canaux
            channel_metrics = [self._parse_channel_metrics(ch, payment_history) for ch in channels]
            
            # Calculer les métriques globales du nœud
            node_financials = self._calculate_node_financials(channel_metrics)
            
            # Analyse des revenus
            revenue_analysis = self._analyze_revenue_patterns(channel_metrics, timeframe_days)
            
            # Analyse des frais
            fee_analysis = self._analyze_fee_structure(channel_metrics)
            
            # ROI et rentabilité
            roi_analysis = self._calculate_roi_metrics(node_financials, timeframe_days)
            
            # Recommandations d'optimisation
            optimization_recs = self._generate_financial_recommendations(
                channel_metrics, node_financials, fee_analysis
            )
            
            return {
                'node_pubkey': node_pubkey,
                'node_financials': node_financials.__dict__,
                'revenue_analysis': revenue_analysis,
                'fee_analysis': fee_analysis,
                'roi_analysis': roi_analysis,
                'optimization_recommendations': optimization_recs,
                'btc_price_usd': self.btc_price_usd,
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur analyse financière {node_pubkey}: {str(e)}")
            return {"error": str(e)}
    
    def optimize_fee_structure(self, channels: List[Dict], 
                              target_metrics: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Optimise la structure tarifaire pour maximiser les revenus
        """
        if target_metrics is None:
            target_metrics = {
                'min_success_rate': 0.85,
                'target_volume_increase': 0.20,
                'max_fee_increase': 0.50
            }
        
        try:
            current_metrics = [self._parse_channel_metrics(ch) for ch in channels]
            optimizations = []
            
            for channel in current_metrics:
                optimization = self._optimize_single_channel_fees(channel, target_metrics)
                if optimization['recommended_change']:
                    optimizations.append(optimization)
            
            # Calculer l'impact global
            global_impact = self._calculate_global_fee_impact(optimizations, current_metrics)
            
            return {
                'channel_optimizations': optimizations,
                'global_impact': global_impact,
                'implementation_priority': self._prioritize_fee_changes(optimizations),
                'target_metrics': target_metrics,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur optimisation frais: {str(e)}")
            return {"error": str(e)}
    
    def analyze_liquidity_efficiency(self, channels: List[Dict]) -> Dict[str, Any]:
        """
        Analyse l'efficacité de l'utilisation de la liquidité
        """
        try:
            efficiency_metrics = []
            
            for channel in channels:
                metrics = self._calculate_channel_liquidity_efficiency(channel)
                efficiency_metrics.append(metrics)
            
            # Métriques globales d'efficacité
            total_capacity = sum(m['capacity'] for m in efficiency_metrics)
            weighted_efficiency = sum(
                m['efficiency_score'] * m['capacity'] for m in efficiency_metrics
            ) / total_capacity if total_capacity > 0 else 0
            
            # Identification des canaux sous-performants
            underperforming = [
                m for m in efficiency_metrics 
                if m['efficiency_score'] < 0.3 and m['capacity'] > 1000000  # > 0.01 BTC
            ]
            
            # Recommandations de rééquilibrage
            rebalancing_recs = self._generate_rebalancing_recommendations(efficiency_metrics)
            
            return {
                'channel_efficiencies': efficiency_metrics,
                'global_efficiency_score': weighted_efficiency,
                'underperforming_channels': underperforming,
                'rebalancing_recommendations': rebalancing_recs,
                'liquidity_utilization_stats': self._calculate_liquidity_stats(efficiency_metrics),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur analyse efficacité liquidité: {str(e)}")
            return {"error": str(e)}
    
    def calculate_competitive_analysis(self, node_channels: List[Dict], 
                                     competitor_data: List[Dict] = None) -> Dict[str, Any]:
        """
        Analyse concurrentielle des frais et performance
        """
        try:
            # Analyse des frais du nœud
            node_fee_stats = self._calculate_fee_statistics(node_channels)
            
            # Comparaison avec le marché (si données disponibles)
            market_comparison = {}
            if competitor_data:
                market_fee_stats = self._calculate_market_fee_statistics(competitor_data)
                market_comparison = self._compare_with_market(node_fee_stats, market_fee_stats)
            
            # Positionnement concurrentiel
            competitive_position = self._assess_competitive_position(
                node_fee_stats, market_comparison
            )
            
            # Opportunités d'optimisation
            opportunities = self._identify_fee_opportunities(
                node_channels, market_comparison
            )
            
            return {
                'node_fee_statistics': node_fee_stats,
                'market_comparison': market_comparison,
                'competitive_position': competitive_position,
                'optimization_opportunities': opportunities,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur analyse concurrentielle: {str(e)}")
            return {"error": str(e)}
    
    def project_revenue_scenarios(self, current_metrics: Dict[str, Any],
                                scenarios: List[Dict[str, float]]) -> Dict[str, Any]:
        """
        Projections de revenus selon différents scénarios
        """
        try:
            projections = {}
            
            for i, scenario in enumerate(scenarios):
                scenario_name = scenario.get('name', f'Scenario_{i+1}')
                
                # Calculer l'impact du scénario
                projected_revenue = self._calculate_scenario_revenue(current_metrics, scenario)
                projected_volume = self._calculate_scenario_volume(current_metrics, scenario)
                
                projections[scenario_name] = {
                    'scenario_parameters': scenario,
                    'projected_monthly_revenue_sats': projected_revenue,
                    'projected_monthly_volume_sats': projected_volume,
                    'projected_monthly_revenue_usd': projected_revenue * self.btc_price_usd / 1e8,
                    'revenue_change_percent': (projected_revenue / current_metrics.get('total_revenue_30d', 1) - 1) * 100,
                    'roi_improvement': self._calculate_scenario_roi_improvement(current_metrics, projected_revenue)
                }
            
            # Scénario recommandé
            best_scenario = max(projections.items(), key=lambda x: x[1]['roi_improvement'])
            
            return {
                'current_baseline': {
                    'monthly_revenue_sats': current_metrics.get('total_revenue_30d', 0),
                    'monthly_revenue_usd': current_metrics.get('total_revenue_30d', 0) * self.btc_price_usd / 1e8
                },
                'scenario_projections': projections,
                'recommended_scenario': {
                    'name': best_scenario[0],
                    'details': best_scenario[1]
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur projections revenus: {str(e)}")
            return {"error": str(e)}
    
    def _parse_channel_metrics(self, channel: Dict, payment_history: List[Dict] = None) -> ChannelMetrics:
        """Parse les données d'un canal vers ChannelMetrics"""
        channel_id = channel.get('channel_id', '')
        
        # Calculer volume et revenus depuis l'historique si disponible
        volume_7d = volume_30d = revenue_7d = revenue_30d = 0
        success_rate = 0.0
        avg_payment_size = 0
        
        if payment_history:
            channel_payments = [p for p in payment_history if p.get('channel_id') == channel_id]
            if channel_payments:
                now = datetime.utcnow()
                week_ago = now - timedelta(days=7)
                month_ago = now - timedelta(days=30)
                
                week_payments = [p for p in channel_payments 
                               if datetime.fromisoformat(p.get('timestamp', '2020-01-01')) >= week_ago]
                month_payments = [p for p in channel_payments
                                if datetime.fromisoformat(p.get('timestamp', '2020-01-01')) >= month_ago]
                
                volume_7d = sum(p.get('amount_sats', 0) for p in week_payments)
                volume_30d = sum(p.get('amount_sats', 0) for p in month_payments)
                revenue_7d = sum(p.get('fee_sats', 0) for p in week_payments)
                revenue_30d = sum(p.get('fee_sats', 0) for p in month_payments)
                
                successful_payments = [p for p in month_payments if p.get('status') == 'success']
                success_rate = len(successful_payments) / len(month_payments) if month_payments else 0
                avg_payment_size = np.mean([p.get('amount_sats', 0) for p in successful_payments]) if successful_payments else 0
        
        return ChannelMetrics(
            channel_id=channel_id,
            capacity=channel.get('capacity', 0),
            local_balance=channel.get('local_balance', 0),
            remote_balance=channel.get('remote_balance', 0),
            fee_rate_ppm=channel.get('fee_rate_ppm', 0),
            base_fee_msat=channel.get('base_fee_msat', 0),
            volume_7d=volume_7d,
            volume_30d=volume_30d,
            revenue_7d=revenue_7d,
            revenue_30d=revenue_30d,
            success_rate=success_rate,
            avg_payment_size=int(avg_payment_size)
        )
    
    def _calculate_node_financials(self, channels: List[ChannelMetrics]) -> NodeFinancials:
        """Calcule les métriques financières globales du nœud"""
        return NodeFinancials(
            total_capacity=sum(ch.capacity for ch in channels),
            total_local_balance=sum(ch.local_balance for ch in channels),
            total_remote_balance=sum(ch.remote_balance for ch in channels),
            total_revenue_7d=sum(ch.revenue_7d for ch in channels),
            total_revenue_30d=sum(ch.revenue_30d for ch in channels),
            total_volume_7d=sum(ch.volume_7d for ch in channels),
            total_volume_30d=sum(ch.volume_30d for ch in channels),
            channel_count=len(channels),
            avg_success_rate=np.mean([ch.success_rate for ch in channels if ch.success_rate > 0])
        )
    
    def _analyze_revenue_patterns(self, channels: List[ChannelMetrics], timeframe_days: int) -> Dict[str, Any]:
        """Analyse les patterns de revenus"""
        
        # Revenue par canal
        channel_revenues = [
            {
                'channel_id': ch.channel_id,
                'revenue_30d': ch.revenue_30d,
                'revenue_per_capacity': ch.revenue_30d / ch.capacity if ch.capacity > 0 else 0,
                'volume_to_revenue_ratio': ch.volume_30d / ch.revenue_30d if ch.revenue_30d > 0 else 0
            }
            for ch in channels
        ]
        
        # Top performers
        top_revenue_channels = sorted(channel_revenues, key=lambda x: x['revenue_30d'], reverse=True)[:5]
        top_efficiency_channels = sorted(channel_revenues, key=lambda x: x['revenue_per_capacity'], reverse=True)[:5]
        
        # Tendances temporelles (approximation basée sur 7d vs 30d)
        total_7d = sum(ch.revenue_7d for ch in channels)
        total_30d = sum(ch.revenue_30d for ch in channels)
        
        # Extrapolation simple (7 jours × 4.28 = ~30 jours)
        weekly_run_rate = total_7d * 4.28
        growth_trend = (weekly_run_rate / total_30d - 1) * 100 if total_30d > 0 else 0
        
        return {
            'total_revenue_30d_sats': total_30d,
            'total_revenue_30d_usd': total_30d * self.btc_price_usd / 1e8,
            'revenue_growth_trend_percent': growth_trend,
            'top_revenue_channels': top_revenue_channels,
            'top_efficiency_channels': top_efficiency_channels,
            'revenue_distribution': self._calculate_revenue_distribution(channel_revenues),
            'revenue_concentration_gini': self._calculate_gini([ch['revenue_30d'] for ch in channel_revenues])
        }
    
    def _analyze_fee_structure(self, channels: List[ChannelMetrics]) -> Dict[str, Any]:
        """Analyse la structure tarifaire"""
        
        fee_rates = [ch.fee_rate_ppm for ch in channels if ch.fee_rate_ppm > 0]
        base_fees = [ch.base_fee_msat for ch in channels if ch.base_fee_msat > 0]
        
        return {
            'fee_rate_statistics': {
                'mean_ppm': np.mean(fee_rates) if fee_rates else 0,
                'median_ppm': np.median(fee_rates) if fee_rates else 0,
                'std_ppm': np.std(fee_rates) if fee_rates else 0,
                'min_ppm': min(fee_rates) if fee_rates else 0,
                'max_ppm': max(fee_rates) if fee_rates else 0,
                'percentiles': {
                    f'p{p}': np.percentile(fee_rates, p) for p in [25, 50, 75, 90, 95]
                } if fee_rates else {}
            },
            'base_fee_statistics': {
                'mean_msat': np.mean(base_fees) if base_fees else 0,
                'median_msat': np.median(base_fees) if base_fees else 0,
                'std_msat': np.std(base_fees) if base_fees else 0
            },
            'fee_consistency_score': 1.0 - (np.std(fee_rates) / np.mean(fee_rates)) if fee_rates and np.mean(fee_rates) > 0 else 0,
            'channels_with_zero_fees': len([ch for ch in channels if ch.fee_rate_ppm == 0])
        }
    
    def _calculate_roi_metrics(self, financials: NodeFinancials, timeframe_days: int) -> Dict[str, Any]:
        """Calcule les métriques de ROI"""
        
        # ROI annualisé basé sur la capacité
        capacity_btc = financials.total_capacity / 1e8
        monthly_revenue_btc = financials.total_revenue_30d / 1e8
        annual_revenue_btc = monthly_revenue_btc * 12
        
        roi_percent = (annual_revenue_btc / capacity_btc * 100) if capacity_btc > 0 else 0
        
        # Métriques de performance
        revenue_per_channel = financials.total_revenue_30d / financials.channel_count if financials.channel_count > 0 else 0
        volume_efficiency = financials.total_volume_30d / financials.total_capacity if financials.total_capacity > 0 else 0
        
        return {
            'annual_roi_percent': roi_percent,
            'monthly_revenue_btc': monthly_revenue_btc,
            'monthly_revenue_usd': monthly_revenue_btc * self.btc_price_usd,
            'revenue_per_channel_sats': revenue_per_channel,
            'volume_efficiency_ratio': volume_efficiency,
            'capital_utilization_score': self._calculate_capital_utilization_score(financials),
            'break_even_analysis': self._calculate_break_even_metrics(financials)
        }
    
    def _generate_financial_recommendations(self, channels: List[ChannelMetrics], 
                                          financials: NodeFinancials,
                                          fee_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Génère des recommandations financières"""
        recommendations = []
        
        # Analyser les canaux sous-performants
        underperforming = [ch for ch in channels if ch.revenue_30d < (financials.total_revenue_30d / len(channels) * 0.5)]
        if underperforming:
            recommendations.append({
                'type': 'underperforming_channels',
                'priority': 'high',
                'description': f'{len(underperforming)} canaux génèrent moins de 50% du revenu moyen',
                'action': 'Considérer augmentation des frais ou rééquilibrage',
                'affected_channels': len(underperforming),
                'potential_impact': 'Augmentation revenue 10-30%'
            })
        
        # Analyser la cohérence des frais
        if fee_analysis['fee_consistency_score'] < 0.7:
            recommendations.append({
                'type': 'fee_structure_optimization',
                'priority': 'medium',
                'description': 'Structure tarifaire incohérente détectée',
                'action': 'Harmoniser les frais selon la capacité et performance',
                'potential_impact': 'Amélioration prévisibilité revenus'
            })
        
        # ROI faible
        roi = self._calculate_roi_metrics(financials, 30)['annual_roi_percent']
        if roi < 5:  # ROI annuel < 5%
            recommendations.append({
                'type': 'low_roi',
                'priority': 'high',
                'description': f'ROI annuel faible: {roi:.1f}%',
                'action': 'Optimiser frais et réduire liquidité inactive',
                'potential_impact': 'Target ROI 8-12%'
            })
        
        # Canaux avec zéro frais
        zero_fee_channels = fee_analysis['channels_with_zero_fees']
        if zero_fee_channels > 0:
            recommendations.append({
                'type': 'zero_fee_channels',
                'priority': 'medium',
                'description': f'{zero_fee_channels} canaux sans frais détectés',
                'action': 'Implémenter frais minimums (1-10 ppm)',
                'potential_impact': 'Revenue additionnel sans impact volume'
            })
        
        return recommendations
    
    def _optimize_single_channel_fees(self, channel: ChannelMetrics, targets: Dict[str, float]) -> Dict[str, Any]:
        """Optimise les frais d'un canal individuel"""
        current_ppm = channel.fee_rate_ppm
        
        # Calculer le fee rate optimal basé sur performance
        if channel.success_rate > targets['min_success_rate'] and channel.volume_30d > 0:
            # Canal performant - peut augmenter les frais
            recommended_ppm = min(current_ppm * (1 + targets['max_fee_increase']), current_ppm + 500)
            change_reason = 'Canal performant - augmentation possible'
        elif channel.success_rate < targets['min_success_rate']:
            # Canal problématique - réduire les frais
            recommended_ppm = max(current_ppm * 0.7, 1)
            change_reason = 'Faible taux de succès - réduction recommandée'
        elif channel.volume_30d == 0:
            # Canal inutilisé - frais agressifs pour tester
            recommended_ppm = current_ppm * 1.5 if current_ppm > 0 else 100
            change_reason = 'Canal inutilisé - test frais élevés'
        else:
            recommended_ppm = current_ppm
            change_reason = 'Aucun changement requis'
        
        change_pct = (recommended_ppm / current_ppm - 1) * 100 if current_ppm > 0 else 0
        
        return {
            'channel_id': channel.channel_id,
            'current_fee_ppm': current_ppm,
            'recommended_fee_ppm': int(recommended_ppm),
            'change_percent': change_pct,
            'change_reason': change_reason,
            'recommended_change': abs(change_pct) > 5,  # Seulement si changement >5%
            'expected_impact': self._estimate_fee_change_impact(channel, recommended_ppm)
        }
    
    def _calculate_channel_liquidity_efficiency(self, channel: Dict) -> Dict[str, Any]:
        """Calcule l'efficacité de liquidité d'un canal"""
        capacity = channel.get('capacity', 0)
        local_balance = channel.get('local_balance', 0)
        remote_balance = channel.get('remote_balance', 0)
        volume_30d = channel.get('volume_30d', 0)
        
        # Balance ratio (optimal autour de 50/50)
        balance_ratio = local_balance / capacity if capacity > 0 else 0
        balance_efficiency = 1.0 - abs(0.5 - balance_ratio) * 2  # 1.0 = parfait, 0.0 = tout d'un côté
        
        # Volume efficiency (volume vs capacité)
        volume_efficiency = min(1.0, volume_30d / capacity) if capacity > 0 else 0
        
        # Score composite
        efficiency_score = (balance_efficiency * 0.6 + volume_efficiency * 0.4)
        
        return {
            'channel_id': channel.get('channel_id', ''),
            'capacity': capacity,
            'balance_ratio': balance_ratio,
            'balance_efficiency': balance_efficiency,
            'volume_efficiency': volume_efficiency,
            'efficiency_score': efficiency_score,
            'volume_30d': volume_30d,
            'utilization_category': self._categorize_channel_utilization(efficiency_score)
        }
    
    def _calculate_revenue_distribution(self, channel_revenues: List[Dict]) -> Dict[str, Any]:
        """Calcule la distribution des revenus par canal"""
        revenues = [ch['revenue_30d'] for ch in channel_revenues]
        total_revenue = sum(revenues)
        
        if total_revenue == 0:
            return {'concentration': 'N/A', 'top_10_percent_share': 0}
        
        # Sort descendant
        sorted_revenues = sorted(revenues, reverse=True)
        
        # Part des 10% meilleurs canaux
        top_10_count = max(1, len(sorted_revenues) // 10)
        top_10_revenue = sum(sorted_revenues[:top_10_count])
        top_10_share = top_10_revenue / total_revenue
        
        return {
            'total_revenue': total_revenue,
            'top_10_percent_share': top_10_share,
            'concentration': 'high' if top_10_share > 0.8 else 'medium' if top_10_share > 0.5 else 'low'
        }
    
    def _calculate_gini(self, values: List[float]) -> float:
        """Calcule le coefficient de Gini"""
        if not values or all(v == 0 for v in values):
            return 0.0
            
        sorted_values = sorted([v for v in values if v >= 0])
        n = len(sorted_values)
        cumsum = np.cumsum(sorted_values)
        
        return (n + 1 - 2 * sum(cumsum) / cumsum[-1]) / n if cumsum[-1] > 0 else 0
    
    def _calculate_capital_utilization_score(self, financials: NodeFinancials) -> float:
        """Score d'utilisation du capital (0-1)"""
        if financials.total_capacity == 0:
            return 0.0
        
        # Pondération: 40% volume, 30% revenue, 30% balance distribution
        volume_score = min(1.0, financials.total_volume_30d / financials.total_capacity)
        revenue_score = min(1.0, financials.total_revenue_30d / (financials.total_capacity * 0.001))  # 0.1% monthly
        
        # Balance distribution score (closer to 50/50 is better)
        total_capacity = financials.total_capacity
        balance_ratio = financials.total_local_balance / total_capacity if total_capacity > 0 else 0
        balance_score = 1.0 - abs(0.5 - balance_ratio) * 2
        
        return volume_score * 0.4 + revenue_score * 0.3 + balance_score * 0.3
    
    def _calculate_break_even_metrics(self, financials: NodeFinancials) -> Dict[str, Any]:
        """Analyse break-even et coûts d'opportunité"""
        
        # Coûts estimés (hosting, maintenance, monitoring)
        monthly_fixed_costs_sats = 100000  # ~450 sats/USD * 220 USD
        
        # Break-even volume requis
        avg_fee_rate = 0.001  # 1000 ppm estimé
        break_even_volume = monthly_fixed_costs_sats / avg_fee_rate if avg_fee_rate > 0 else float('inf')
        
        current_profit = financials.total_revenue_30d - monthly_fixed_costs_sats
        profit_margin = current_profit / financials.total_revenue_30d if financials.total_revenue_30d > 0 else 0
        
        return {
            'monthly_fixed_costs_sats': monthly_fixed_costs_sats,
            'break_even_volume_sats': int(break_even_volume) if break_even_volume != float('inf') else None,
            'current_profit_sats': current_profit,
            'profit_margin_percent': profit_margin * 100,
            'months_to_break_even': max(0, -current_profit / max(1, financials.total_revenue_30d)),
            'is_profitable': current_profit > 0
        }
    
    def _estimate_fee_change_impact(self, channel: ChannelMetrics, new_fee_ppm: int) -> Dict[str, Any]:
        """Estime l'impact d'un changement de frais"""
        current_fee = channel.fee_rate_ppm
        fee_change_pct = (new_fee_ppm / current_fee - 1) if current_fee > 0 else 0
        
        # Modèle simple: élasticité de -0.5 (volume diminue de 0.5% par 1% d'augmentation de frais)
        elasticity = -0.5
        expected_volume_change = elasticity * fee_change_pct
        
        new_volume = channel.volume_30d * (1 + expected_volume_change)
        new_revenue = new_volume * new_fee_ppm / 1e6  # Convert ppm to fraction
        
        revenue_change_pct = (new_revenue / max(1, channel.revenue_30d) - 1) * 100
        
        return {
            'expected_volume_change_percent': expected_volume_change * 100,
            'expected_revenue_change_percent': revenue_change_pct,
            'confidence': 'low' if abs(fee_change_pct) > 0.5 else 'medium'
        }
    
    def _categorize_channel_utilization(self, efficiency_score: float) -> str:
        """Catégorise l'utilisation d'un canal"""
        if efficiency_score > 0.8:
            return 'excellent'
        elif efficiency_score > 0.6:
            return 'good'
        elif efficiency_score > 0.4:
            return 'average'
        elif efficiency_score > 0.2:
            return 'poor'
        else:
            return 'very_poor'