#!/usr/bin/env python3
"""
Script de démonstration pour l'API DazFlow Index
Illustre les fonctionnalités d'analyse avancée du Lightning Network

Dernière mise à jour: 7 mai 2025
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analytics import DazFlowCalculator, DazFlowAnalysis
from app.services.lnbits import LNBitsService

class DazFlowDemo:
    """Classe de démonstration pour les fonctionnalités DazFlow Index"""
    
    def __init__(self):
        """Initialise la démonstration"""
        self.calculator = DazFlowCalculator()
        self.lnbits_service = LNBitsService()
        
        # Données de démonstration
        self.demo_node_data = {
            "node_id": "demo_node_001",
            "channels": [
                {
                    "channel_id": "demo_channel_1",
                    "peer_alias": "ACINQ",
                    "capacity": 5000000,
                    "local_balance": 2500000,
                    "remote_balance": 2500000,
                    "active": True
                },
                {
                    "channel_id": "demo_channel_2",
                    "peer_alias": "Blockstream",
                    "capacity": 3000000,
                    "local_balance": 2700000,
                    "remote_balance": 300000,
                    "active": True
                },
                {
                    "channel_id": "demo_channel_3",
                    "peer_alias": "Lightning Labs",
                    "capacity": 2000000,
                    "local_balance": 400000,
                    "remote_balance": 1600000,
                    "active": True
                }
            ],
            "historical_success_rate": 0.88,
            "metrics": {
                "centrality": {
                    "betweenness": 0.65
                }
            }
        }
    
    async def run_demo(self):
        """Exécute la démonstration complète"""
        print("🚀 Démonstration DazFlow Index - Analyse Lightning Network")
        print("=" * 60)
        
        try:
            # 1. Analyse DazFlow Index complète
            await self.demo_dazflow_analysis()
            
            # 2. Courbe de fiabilité
            await self.demo_reliability_curve()
            
            # 3. Identification des goulots d'étranglement
            await self.demo_bottlenecks()
            
            # 4. Optimisation de liquidité
            await self.demo_liquidity_optimization()
            
            # 5. Comparaison avec données réelles (si disponibles)
            await self.demo_real_data_comparison()
            
        except Exception as e:
            print(f"❌ Erreur lors de la démonstration: {e}")
            return False
        
        print("\n✅ Démonstration terminée avec succès!")
        return True
    
    async def demo_dazflow_analysis(self):
        """Démonstration de l'analyse DazFlow Index"""
        print("\n📊 1. Analyse DazFlow Index")
        print("-" * 30)
        
        analysis = self.calculator.analyze_dazflow_index(self.demo_node_data)
        
        if analysis:
            print(f"🔍 Nœud analysé: {analysis.node_id}")
            print(f"📈 Indice DazFlow: {analysis.dazflow_index:.4f}")
            print(f"💧 Efficacité liquidité: {analysis.liquidity_efficiency:.4f}")
            print(f"🌐 Centralité réseau: {analysis.network_centrality:.4f}")
            print(f"⚠️  Goulots d'étranglement: {len(analysis.bottleneck_channels)}")
            
            # Analyse des probabilités de succès
            print("\n💰 Probabilités de succès par montant:")
            for amount, prob in zip(analysis.payment_amounts, analysis.success_probabilities):
                print(f"   {amount:,} sats → {prob:.1%}")
        else:
            print("❌ Impossible d'analyser le nœud")
    
    async def demo_reliability_curve(self):
        """Démonstration de la courbe de fiabilité"""
        print("\n📈 2. Courbe de fiabilité des paiements")
        print("-" * 40)
        
        amounts = [1000, 10000, 100000, 1000000, 10000000]
        curve = self.calculator.generate_reliability_curve(self.demo_node_data, amounts)
        
        print(f"📊 Montants testés: {len(curve.amounts)}")
        print(f"🎯 Montants recommandés: {len(curve.recommended_amounts)}")
        
        if curve.recommended_amounts:
            max_reliable = max(curve.recommended_amounts)
            print(f"💪 Montant maximum fiable: {max_reliable:,} sats")
        
        # Afficher la courbe
        print("\n📉 Détail de la courbe:")
        for i, (amount, prob) in enumerate(zip(curve.amounts, curve.probabilities)):
            confidence = curve.confidence_intervals[i]
            status = "✅" if amount in curve.recommended_amounts else "⚠️"
            print(f"   {status} {amount:,} sats → {prob:.1%} [{confidence[0]:.1%}-{confidence[1]:.1%}]")
    
    async def demo_bottlenecks(self):
        """Démonstration de l'identification des goulots d'étranglement"""
        print("\n🔍 3. Identification des goulots d'étranglement")
        print("-" * 45)
        
        bottlenecks = self.calculator.identify_bottlenecks(self.demo_node_data)
        
        if bottlenecks:
            print(f"⚠️  {len(bottlenecks)} goulots d'étranglement identifiés")
            
            high_severity = [b for b in bottlenecks if b["severity"] == "high"]
            medium_severity = [b for b in bottlenecks if b["severity"] == "medium"]
            
            print(f"🔴 Sévérité haute: {len(high_severity)}")
            print(f"🟡 Sévérité moyenne: {len(medium_severity)}")
            
            # Afficher les détails
            for bottleneck in bottlenecks[:3]:  # Limiter à 3 pour la lisibilité
                print(f"\n📋 Canal: {bottleneck['peer_alias']}")
                print(f"   Déséquilibre: {bottleneck['imbalance_ratio']:.1%}")
                print(f"   Problèmes: {', '.join(bottleneck['issues'])}")
                print(f"   Sévérité: {bottleneck['severity']}")
        else:
            print("✅ Aucun goulot d'étranglement détecté")
    
    async def demo_liquidity_optimization(self):
        """Démonstration de l'optimisation de liquidité"""
        print("\n⚡ 4. Optimisation de liquidité")
        print("-" * 30)
        
        target_amount = 500000  # 500k sats
        current_analysis = self.calculator.analyze_dazflow_index(self.demo_node_data)
        
        if current_analysis:
            print(f"🎯 Montant cible: {target_amount:,} sats")
            print(f"📊 Indice DazFlow actuel: {current_analysis.dazflow_index:.4f}")
            print(f"💧 Efficacité actuelle: {current_analysis.liquidity_efficiency:.4f}")
            
            # Simuler des recommandations
            recommendations = self._generate_demo_recommendations()
            
            print(f"\n💡 {len(recommendations)} recommandations générées:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec['action']} sur {rec['peer_alias']}")
                print(f"      Montant: {rec['amount']:,} sats")
                print(f"      Priorité: {rec['priority']}")
                print(f"      Raison: {rec['reason']}")
    
    async def demo_real_data_comparison(self):
        """Démonstration avec comparaison de données réelles"""
        print("\n🌐 5. Comparaison avec données réelles")
        print("-" * 40)
        
        try:
            # Essayer de récupérer des données réelles
            real_nodes = await self.lnbits_service.get_network_data()
            
            if real_nodes and len(real_nodes) > 0:
                print(f"📊 {len(real_nodes)} nœuds réels disponibles")
                
                # Analyser le premier nœud réel
                real_node = real_nodes[0]
                real_analysis = self.calculator.analyze_dazflow_index(real_node)
                
                if real_analysis:
                    print(f"🔍 Nœud réel: {real_analysis.node_id}")
                    print(f"📈 Indice DazFlow réel: {real_analysis.dazflow_index:.4f}")
                    print(f"💧 Efficacité réelle: {real_analysis.liquidity_efficiency:.4f}")
                    
                    # Comparer avec les données de démo
                    demo_analysis = self.calculator.analyze_dazflow_index(self.demo_node_data)
                    if demo_analysis:
                        print(f"\n📊 Comparaison:")
                        print(f"   Démo vs Réel - DazFlow: {demo_analysis.dazflow_index:.4f} vs {real_analysis.dazflow_index:.4f}")
                        print(f"   Démo vs Réel - Efficacité: {demo_analysis.liquidity_efficiency:.4f} vs {real_analysis.liquidity_efficiency:.4f}")
            else:
                print("ℹ️  Aucune donnée réelle disponible pour la comparaison")
                
        except Exception as e:
            print(f"ℹ️  Impossible de récupérer les données réelles: {e}")
    
    def _generate_demo_recommendations(self) -> list:
        """Génère des recommandations de démonstration"""
        return [
            {
                "channel_id": "demo_channel_2",
                "peer_alias": "Blockstream",
                "action": "Réduire liquidité",
                "amount": 1200000,
                "priority": "high",
                "reason": "Déséquilibre de 80%"
            },
            {
                "channel_id": "demo_channel_3", 
                "peer_alias": "Lightning Labs",
                "action": "Augmenter liquidité",
                "amount": 600000,
                "priority": "medium",
                "reason": "Déséquilibre de 60%"
            }
        ]
    
    def print_summary(self):
        """Affiche un résumé des fonctionnalités"""
        print("\n📋 Résumé des fonctionnalités DazFlow Index")
        print("=" * 50)
        print("✅ Analyse complète de la santé des nœuds")
        print("✅ Courbe de fiabilité des paiements")
        print("✅ Identification des goulots d'étranglement")
        print("✅ Optimisation de liquidité")
        print("✅ Métriques de centralité réseau")
        print("✅ Recommandations d'amélioration")
        print("✅ Compatible avec LNBits et Amboss")

async def main():
    """Fonction principale"""
    demo = DazFlowDemo()
    
    # Afficher le résumé
    demo.print_summary()
    
    # Exécuter la démonstration
    success = await demo.run_demo()
    
    if success:
        print("\n🎉 DazFlow Index est prêt pour la production!")
        print("📚 Consultez la documentation pour plus de détails")
    else:
        print("\n❌ La démonstration a échoué")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 