import pandas as pd
from typing import Dict, List, Any
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import scipy.stats as stats

class PerformanceDashboard:
    def __init__(self, data_dir: str = "collected_data", tenant_id: str = None):
        if tenant_id:
            self.data_dir = f"{data_dir}/{tenant_id}"
        else:
            self.data_dir = data_dir
        self.metrics_file = f"{self.data_dir}/metrics_comparison.csv"
        
    def load_performance_data(self) -> pd.DataFrame:
        """Charge les données de performance depuis le fichier CSV"""
        df = pd.read_csv(self.metrics_file)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
        
    def calculate_period_stats(self, days: int) -> Dict[str, Any]:
        """Calcule les statistiques pour une période donnée"""
        df = self.load_performance_data()
        cutoff_date = datetime.now() - timedelta(days=days)
        period_data = df[df["timestamp"] >= cutoff_date]
        
        if period_data.empty:
            return {}
            
        # Calculer les multiplicateurs pour chaque stratégie
        heuristic_mult = period_data["heuristic_delta"].mean() / period_data["random_delta"].mean()
        
        # Effectuer un test t pour la significativité statistique
        t_stat, p_value = stats.ttest_ind(
            period_data["heuristic_delta"],
            period_data["random_delta"]
        )
        
        return {
            "period_days": days,
            "sample_size": len(period_data),
            "heuristic_multiplier": heuristic_mult,
            "win_ratio": (period_data["winner"] == "heuristic").mean(),
            "p_value": p_value,
            "is_significant": p_value < 0.05
        }
        
    def generate_performance_plots(self) -> Dict[str, go.Figure]:
        """Génère les visualisations pour différentes périodes"""
        df = self.load_performance_data()
        periods = [3, 7, 14]
        plots = {}
        
        for days in periods:
            cutoff_date = datetime.now() - timedelta(days=days)
            period_data = df[df["timestamp"] >= cutoff_date]
            
            if period_data.empty:
                continue
                
            # Créer un subplot avec multiplicateur et ratio de victoire
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=(f"Multiplicateur sur {days} jours", 
                              f"Ratio de victoire sur {days} jours")
            )
            
            # Tracer le multiplicateur
            multipliers = period_data["heuristic_delta"] / period_data["random_delta"]
            fig.add_trace(
                go.Scatter(x=period_data["timestamp"], y=multipliers,
                          mode="lines+markers", name="Multiplicateur"),
                row=1, col=1
            )
            
            # Tracer le ratio de victoire cumulé
            win_ratio = (period_data["winner"] == "heuristic").cumsum() / \
                       (pd.Series(range(1, len(period_data) + 1)))
            fig.add_trace(
                go.Scatter(x=period_data["timestamp"], y=win_ratio,
                          mode="lines", name="Ratio de victoire"),
                row=2, col=1
            )
            
            # Mise en forme
            fig.update_layout(
                height=800,
                title_text=f"Performance sur {days} jours",
                showlegend=True
            )
            
            plots[f"{days}_days"] = fig
            
        return plots
        
    def generate_statistical_report(self) -> Dict[str, Any]:
        """Génère un rapport statistique complet"""
        periods = [3, 7, 14]
        report = {
            "period_stats": {},
            "overall_assessment": ""
        }
        
        # Calculer les stats pour chaque période
        for days in periods:
            report["period_stats"][days] = self.calculate_period_stats(days)
            
        # Évaluer la significativité globale
        significant_periods = sum(
            1 for stats in report["period_stats"].values()
            if stats.get("is_significant", False)
        )
        
        if significant_periods == len(periods):
            report["overall_assessment"] = (
                "L'heuristique montre une supériorité statistiquement "
                "significative sur toutes les périodes analysées."
            )
        elif significant_periods > 0:
            report["overall_assessment"] = (
                "L'heuristique montre une supériorité statistiquement "
                f"significative sur {significant_periods}/{len(periods)} périodes."
            )
        else:
            report["overall_assessment"] = (
                "Pas de différence statistiquement significative "
                "entre l'heuristique et le random."
            )
            
        return report 