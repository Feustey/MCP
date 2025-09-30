#!/usr/bin/env python3
"""
Analyse des métriques collectées par le monitoring MCP

Ce script analyse les rapports quotidiens générés par monitor_production.py
et produit des statistiques, graphiques et insights.

Usage:
    python analyze_metrics.py                    # Analyse du jour
    python analyze_metrics.py --days 7           # Analyse 7 derniers jours
    python analyze_metrics.py --date 20250930    # Analyse d'un jour spécifique
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
import argparse

# Configuration
ROOT_DIR = Path(__file__).parent
MONITORING_DIR = ROOT_DIR / "monitoring_data"


class MetricsAnalyzer:
    """Analyseur de métriques MCP"""

    def __init__(self):
        self.data = []
        self.stats = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "response_times": [],
            "errors": [],
            "uptime_pct": 0
        }

    def load_report(self, date_str: str) -> bool:
        """Charge un rapport quotidien"""
        report_file = MONITORING_DIR / f"monitoring_{date_str}.json"

        if not report_file.exists():
            print(f"❌ Rapport non trouvé: {report_file}")
            return False

        try:
            with open(report_file, 'r') as f:
                data = json.load(f)
                self.data.append({
                    "date": date_str,
                    "report": data
                })
            print(f"✅ Chargé: {date_str} ({len(data.get('checks', []))} checks)")
            return True

        except Exception as e:
            print(f"❌ Erreur lecture {date_str}: {e}")
            return False

    def load_date_range(self, days: int = 1) -> int:
        """Charge les rapports des N derniers jours"""
        loaded = 0
        today = datetime.now()

        for i in range(days):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y%m%d")
            if self.load_report(date_str):
                loaded += 1

        return loaded

    def analyze(self):
        """Analyse les données chargées"""
        if not self.data:
            print("❌ Aucune donnée à analyser")
            return

        print("\n" + "="*60)
        print("📊 ANALYSE DES MÉTRIQUES MCP")
        print("="*60)

        # Agrège toutes les checks
        all_checks = []
        for day_data in self.data:
            checks = day_data["report"].get("checks", [])
            all_checks.extend(checks)

        if not all_checks:
            print("❌ Aucun check trouvé")
            return

        # Analyse globale
        total_checks = len(all_checks)
        successful = sum(1 for c in all_checks if c.get("health", {}).get("healthy", False))
        failed = total_checks - successful

        # Response times
        response_times = [
            c.get("health", {}).get("response_time", 0)
            for c in all_checks
            if c.get("health", {}).get("response_time")
        ]

        # Erreurs
        errors = [
            c.get("health", {}).get("error")
            for c in all_checks
            if c.get("health", {}).get("error")
        ]

        # Calculs
        uptime_pct = (successful / total_checks * 100) if total_checks > 0 else 0
        avg_response = sum(response_times) / len(response_times) if response_times else 0
        max_response = max(response_times) if response_times else 0
        min_response = min(response_times) if response_times else 0

        # Affichage
        print(f"\n📅 Période: {len(self.data)} jour(s)")
        print(f"🔍 Total checks: {total_checks}")
        print(f"✅ Succès: {successful}")
        print(f"❌ Échecs: {failed}")
        print(f"📈 Uptime: {uptime_pct:.2f}%")

        print(f"\n⏱️  Temps de réponse:")
        print(f"  Moyenne: {avg_response:.0f}ms")
        print(f"  Min: {min_response:.0f}ms")
        print(f"  Max: {max_response:.0f}ms")

        if errors:
            print(f"\n⚠️  Erreurs uniques ({len(set(errors))}):")
            error_counts = defaultdict(int)
            for err in errors:
                error_counts[err] += 1

            for err, count in sorted(error_counts.items(), key=lambda x: -x[1])[:5]:
                print(f"  {count}x: {err[:80]}...")

        # Analyse par jour
        print(f"\n📆 Détails par jour:")
        print(f"{'Date':<12} {'Checks':<8} {'Uptime':<10} {'Avg RT':<10}")
        print("-" * 45)

        for day_data in sorted(self.data, key=lambda x: x['date']):
            date = day_data['date']
            checks = day_data['report'].get('checks', [])

            if not checks:
                continue

            day_success = sum(1 for c in checks if c.get('health', {}).get('healthy', False))
            day_total = len(checks)
            day_uptime = (day_success / day_total * 100) if day_total > 0 else 0

            day_rts = [
                c.get('health', {}).get('response_time', 0)
                for c in checks
                if c.get('health', {}).get('response_time')
            ]
            day_avg_rt = sum(day_rts) / len(day_rts) if day_rts else 0

            print(f"{date:<12} {day_total:<8} {day_uptime:>6.1f}%    {day_avg_rt:>6.0f}ms")

        # Recommendations
        print(f"\n💡 Recommandations:")

        if uptime_pct < 95:
            print("  ⚠️  Uptime inférieur à 95% - Investiguer les causes")
        elif uptime_pct < 99:
            print("  ℹ️  Uptime acceptable mais peut être amélioré")
        else:
            print("  ✅ Excellent uptime!")

        if avg_response > 2000:
            print("  ⚠️  Temps de réponse élevé (>2s) - Optimisation requise")
        elif avg_response > 1000:
            print("  ℹ️  Temps de réponse acceptable mais surveillez")
        else:
            print("  ✅ Excellents temps de réponse!")

        if failed > total_checks * 0.1:
            print(f"  ⚠️  Taux d'échec élevé ({failed}/{total_checks}) - Action requise")

        # Sauvegarde du rapport
        self.save_analysis_report(all_checks, {
            "total_checks": total_checks,
            "successful": successful,
            "failed": failed,
            "uptime_pct": uptime_pct,
            "avg_response": avg_response,
            "max_response": max_response,
            "min_response": min_response,
            "errors": list(error_counts.items()) if errors else []
        })

    def save_analysis_report(self, checks: List[Dict], stats: Dict):
        """Sauvegarde un rapport d'analyse"""
        report_dir = ROOT_DIR / "data" / "analysis_reports"
        report_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"analysis_{timestamp}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "period_days": len(self.data),
            "statistics": stats,
            "recommendations": self.generate_recommendations(stats)
        }

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n💾 Rapport sauvegardé: {report_file}")

    def generate_recommendations(self, stats: Dict) -> List[str]:
        """Génère des recommandations basées sur les stats"""
        recommendations = []

        if stats["uptime_pct"] < 95:
            recommendations.append("Uptime critique - Vérifier la stabilité de l'API")

        if stats["avg_response"] > 2000:
            recommendations.append("Temps de réponse élevé - Optimiser les performances")

        if stats["failed"] > stats["total_checks"] * 0.1:
            recommendations.append("Taux d'échec élevé - Investiguer les erreurs")

        if stats["uptime_pct"] >= 99 and stats["avg_response"] < 1000:
            recommendations.append("Performance excellente - Continuer la surveillance")

        return recommendations


def main():
    parser = argparse.ArgumentParser(description="Analyse des métriques MCP")
    parser.add_argument("--days", type=int, default=1, help="Nombre de jours à analyser")
    parser.add_argument("--date", help="Date spécifique (YYYYMMDD)")

    args = parser.parse_args()

    analyzer = MetricsAnalyzer()

    if args.date:
        # Analyse d'un jour spécifique
        if not analyzer.load_report(args.date):
            sys.exit(1)
    else:
        # Analyse des N derniers jours
        loaded = analyzer.load_date_range(args.days)
        if loaded == 0:
            print("❌ Aucune donnée disponible")
            sys.exit(1)

    analyzer.analyze()


if __name__ == "__main__":
    main()
