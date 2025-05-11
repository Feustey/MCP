import streamlit as st
import plotly.graph_objects as go
from typing import Dict, Any
from pathlib import Path
import json
import pandas as pd

from app.services.performance_dashboard import PerformanceDashboard
from app.services.network_topology import NetworkTopologyAnalyzer

class PerformanceVisualizer:
    def __init__(self, data_dir: str = "collected_data"):
        self.data_dir = Path(data_dir)
        self.dashboard = PerformanceDashboard(data_dir)
        self.topology_analyzer = NetworkTopologyAnalyzer()
        
    def show_dashboard(self):
        """Affiche le tableau de bord complet dans Streamlit"""
        st.title("Analyse des Performances du Routage Lightning")
        
        # Charger les données
        df = self.dashboard.load_performance_data()
        
        # Afficher les statistiques globales
        self._show_global_stats(df)
        
        # Afficher les graphiques de performance par période
        self._show_performance_plots()
        
        # Afficher l'analyse topologique
        self._show_topology_analysis(df)
        
    def _show_global_stats(self, df: pd.DataFrame):
        """Affiche les statistiques globales"""
        st.header("Statistiques Globales")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            win_ratio = (df["winner"] == "heuristic").mean()
            st.metric("Ratio de Victoire Heuristique", f"{win_ratio:.2%}")
            
        with col2:
            avg_multiplier = (df["heuristic_delta"] / df["random_delta"]).mean()
            st.metric("Multiplicateur Moyen", f"{avg_multiplier:.2f}x")
            
        with col3:
            success_improvement = (
                df["success_rate_after"].mean() - df["success_rate_before"].mean()
            )
            st.metric("Amélioration du Taux de Succès", f"{success_improvement:.2%}")
            
    def _show_performance_plots(self):
        """Affiche les graphiques de performance"""
        st.header("Analyse des Performances")
        
        # Récupérer les graphiques générés par le dashboard
        plots = self.dashboard.generate_performance_plots()
        
        # Afficher les graphiques pour chaque période
        for period, fig in plots.items():
            st.subheader(f"Performance sur {period.split('_')[0]} jours")
            st.plotly_chart(fig, use_container_width=True)
            
        # Afficher le rapport statistique
        report = self.dashboard.generate_statistical_report()
        st.subheader("Évaluation Statistique")
        st.write(report["overall_assessment"])
        
        # Afficher les détails par période
        for days, stats in report["period_stats"].items():
            if stats:
                st.write(f"**Période de {days} jours:**")
                st.write(f"- Taille de l'échantillon: {stats['sample_size']}")
                st.write(f"- Multiplicateur: {stats['heuristic_multiplier']:.2f}x")
                st.write(f"- Significativité: {'✅' if stats['is_significant'] else '❌'}")
                
    def _show_topology_analysis(self, df: pd.DataFrame):
        """Affiche l'analyse topologique"""
        st.header("Analyse Topologique du Réseau")
        
        # Charger les données topologiques depuis le fichier de performance
        perf_log = self.data_dir / "performance_stats.json"
        if perf_log.exists():
            with open(perf_log, "r") as f:
                stats = json.load(f)
                topo_effects = stats.get("topological_effects", {})
                
            if topo_effects:
                # Créer un DataFrame des métriques topologiques
                topo_data = []
                for cycle_id, features in topo_effects.items():
                    topo_data.append({
                        "cycle_id": cycle_id,
                        **features
                    })
                topo_df = pd.DataFrame(topo_data)
                
                # Afficher les corrélations avec les performances
                st.subheader("Impact des Métriques Topologiques")
                
                # Créer une heatmap des corrélations
                corr_matrix = topo_df.corr()
                fig = go.Figure(data=go.Heatmap(
                    z=corr_matrix.values,
                    x=corr_matrix.columns,
                    y=corr_matrix.columns,
                    colorscale="RdBu"
                ))
                fig.update_layout(
                    title="Matrice de Corrélation des Métriques Topologiques",
                    height=600
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Afficher les métriques les plus influentes
                st.subheader("Métriques Topologiques les Plus Influentes")
                for metric, correlation in stats.get("topological_impact", {}).items():
                    st.metric(
                        metric.replace("_", " ").title(),
                        f"{correlation:.2f}",
                        help="Corrélation avec les performances"
                    )

def launch_dashboard():
    """Lance le tableau de bord Streamlit"""
    visualizer = PerformanceVisualizer()
    visualizer.show_dashboard() 