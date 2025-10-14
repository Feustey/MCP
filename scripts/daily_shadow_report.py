#!/usr/bin/env python3
"""
Daily Shadow Mode Report Generator
Génère un rapport quotidien des décisions shadow mode

Dernière mise à jour: 12 octobre 2025
Usage: python scripts/daily_shadow_report.py [--date YYYY-MM-DD]
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Ajouter le projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.shadow_mode_logger import ShadowModeLogger
import structlog

logger = structlog.get_logger(__name__)


async def generate_report(date: str = None):
    """
    Génère le rapport quotidien
    
    Args:
        date: Date au format YYYY-MM-DD (None = hier)
    """
    # Parse la date
    if date:
        report_date = datetime.strptime(date, "%Y-%m-%d").date()
    else:
        report_date = (datetime.now() - timedelta(days=1)).date()
    
    print(f"╔════════════════════════════════════════════════════════╗")
    print(f"║  📊 SHADOW MODE - RAPPORT QUOTIDIEN                   ║")
    print(f"╚════════════════════════════════════════════════════════╝")
    print(f"")
    print(f"📅 Date: {report_date}")
    print(f"")
    
    # Initialiser le logger
    shadow_logger = ShadowModeLogger(
        log_path="data/reports/shadow_mode",
        enable_daily_reports=True
    )
    
    # Générer le rapport
    print("⏳ Génération du rapport...")
    report = await shadow_logger.generate_daily_report(report_date)
    
    if not report:
        print(f"❌ Aucune donnée disponible pour {report_date}")
        return 1
    
    # Afficher le résumé
    print(f"")
    print(f"✅ Rapport généré avec succès!")
    print(f"")
    print(f"📊 STATISTIQUES")
    print(f"{'─' * 60}")
    print(f"Total décisions:      {report['total_decisions']}")
    print(f"Aurait exécuté:       {report['would_execute_count']}")
    print(f"")
    
    # Décisions par type
    print(f"📋 DÉCISIONS PAR TYPE")
    print(f"{'─' * 60}")
    stats = report.get("statistics", {})
    decision_types = stats.get("decision_types", {})
    
    for decision_type, count in sorted(decision_types.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / report['total_decisions']) * 100
        print(f"{decision_type:20s}: {count:3d} ({percentage:5.1f}%)")
    
    print(f"")
    
    # Distribution des scores
    print(f"🎯 DISTRIBUTION DES SCORES")
    print(f"{'─' * 60}")
    score_dist = report.get("score_distribution", {})
    
    if score_dist:
        print(f"Score moyen:          {score_dist.get('average', 0):.3f}")
        print(f"Score médian:         {score_dist.get('median', 0):.3f}")
        print(f"Score min:            {score_dist.get('min', 0):.3f}")
        print(f"Score max:            {score_dist.get('max', 0):.3f}")
        print(f"")
        
        distribution = score_dist.get("distribution", {})
        for category, count in distribution.items():
            percentage = (count / report['total_decisions']) * 100
            print(f"{category:20s}: {count:3d} ({percentage:5.1f}%)")
    
    print(f"")
    
    # Top recommandations
    print(f"⚠️  TOP 10 RECOMMANDATIONS CRITIQUES")
    print(f"{'─' * 60}")
    top_recs = report.get("top_recommendations", [])
    
    for i, rec in enumerate(top_recs[:10], 1):
        print(f"{i}. Channel: {rec['channel_id'][:8]}...")
        print(f"   Score: {rec['score']:.3f} | Decision: {rec['decision']}")
        print(f"   Confidence: {rec['confidence']}")
        print(f"")
    
    # Path du rapport
    report_file = f"data/reports/shadow_mode/daily_report_{report_date}.json"
    print(f"")
    print(f"📄 Rapport complet: {report_file}")
    print(f"")
    
    # Recommandation
    if report['total_decisions'] > 0:
        actionable = len([d for d in decision_types.items() if d[0] != "no_action"])
        if actionable / report['total_decisions'] > 0.3:
            print(f"⚠️  {(actionable/report['total_decisions']*100):.0f}% des canaux nécessitent une action")
            print(f"   → Review recommandé des top recommandations")
        else:
            print(f"✅ Seulement {(actionable/report['total_decisions']*100):.0f}% des canaux nécessitent une action")
            print(f"   → Système semble bien calibré")
    
    print(f"")
    return 0


def main():
    """Point d'entrée"""
    parser = argparse.ArgumentParser(
        description="Génère un rapport quotidien shadow mode"
    )
    parser.add_argument(
        "--date",
        help="Date au format YYYY-MM-DD (défaut: hier)",
        default=None
    )
    
    args = parser.parse_args()
    
    # Exécuter
    return asyncio.run(generate_report(args.date))


if __name__ == "__main__":
    sys.exit(main())

