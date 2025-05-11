#!/usr/bin/env python3
"""
Moteur de calibration pour le simulateur stochastique.
Ce module permet de calibrer automatiquement les paramètres du simulateur
en fonction de données réelles de nœuds Lightning.

Dernière mise à jour: 8 mai 2025
"""

import logging
import numpy as np
import pandas as pd
import json
import hashlib
from datetime import datetime
from pathlib import Path
from scipy import stats
from scipy.spatial import distance
from typing import Dict, Any, List, Tuple, Optional
import itertools

from .calibration_metrics import CalibrationMetrics
from .stochastic_simulator import LightningSimEnvironment

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("calibration_engine")

# Chemin pour stocker les résultats de calibration
CALIBRATION_RESULTS_PATH = Path("data/calibration")
CALIBRATION_CACHE_PATH = Path("data/calibration/.calibration_cache")
CALIBRATION_ARCHIVE_PATH = Path("data/calibration/archive")


class CalibrationConfig:
    """Configuration pour le processus de calibration"""
    
    # Granularité temporelle
    TIME_GRANULARITY = "daily"  # Options: hourly, daily, weekly
    
    # Paramètres de simulation
    SIMULATION_TICKS = 14  # 14 jours par défaut
    SAMPLES_PER_PARAM_SET = 10  # Exécutions multiples pour robustesse
    
    # Seuils et paramètres
    CONVERGENCE_THRESHOLD = None  # Sera calculé à partir des métriques individuelles
    EARLY_STOPPING_MIN_ITERATIONS = 10  # Nombre minimal d'itérations avant early stopping
    
    @staticmethod
    def get_time_delta():
        """Retourne le délai temporel correspondant à la granularité choisie"""
        if CalibrationConfig.TIME_GRANULARITY == "hourly":
            return 1/24  # Fraction de jour
        elif CalibrationConfig.TIME_GRANULARITY == "weekly":
            return 7
        else:  # daily par défaut
            return 1


class CalibrationEngine:
    """
    Moteur de calibration qui ajuste automatiquement les paramètres du simulateur
    pour qu'ils correspondent aux données réelles.
    """
    
    def __init__(self, node_id="unknown"):
        """
        Initialise le moteur de calibration
        
        Args:
            node_id: Identifiant du nœud pour la traçabilité
        """
        self.metrics = CalibrationMetrics()
        CalibrationConfig.CONVERGENCE_THRESHOLD = self.metrics.get_convergence_threshold()
        self.node_id = node_id
        self.input_data_summary = {}
        self.final_p_values = {}
        
        # Créer les répertoires de résultats si nécessaire
        CALIBRATION_RESULTS_PATH.mkdir(parents=True, exist_ok=True)
        CALIBRATION_CACHE_PATH.mkdir(parents=True, exist_ok=True)
        CALIBRATION_ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
    
    def calibrate_simulator(self, real_node_data: Dict[str, Any], 
                          param_ranges: Dict[str, np.ndarray], 
                          iterations: int = 100) -> Tuple[Dict[str, float], float]:
        """
        Ajuste automatiquement les paramètres du simulateur pour minimiser la divergence avec les données réelles.
        
        Args:
            real_node_data: Données collectées du nœud réel
            param_ranges: Plages de valeurs pour chaque paramètre à tester
            iterations: Nombre d'itérations maximum
            
        Returns:
            Tuple contenant les paramètres optimaux et leur score
        """
        # Prétraitement des données réelles
        logger.info("Prétraitement des données réelles...")
        processed_data = self._preprocess_node_data(real_node_data)
        
        # Créer un résumé des données d'entrée pour traçabilité
        self.input_data_summary = self._create_data_summary(real_node_data)
        
        # Extraction des distributions de référence
        reference_distributions = self._extract_distributions(processed_data)
        
        # Génération des combinaisons de paramètres à tester
        logger.info("Génération des combinaisons de paramètres...")
        param_combinations = self._generate_param_combinations(param_ranges)
        
        # Si trop de combinaisons, utiliser un échantillon aléatoire
        if len(param_combinations) > iterations:
            np.random.shuffle(param_combinations)
            param_combinations = param_combinations[:iterations]
        
        # Initialisation des résultats
        logger.info(f"Démarrage de la calibration avec {len(param_combinations)} combinaisons...")
        best_params = None
        best_score = float('inf')
        results_log = []
        
        # Boucle principale de calibration
        for i, param_dict in enumerate(param_combinations):
            logger.info(f"Itération {i+1}/{len(param_combinations)}: {param_dict}")
            
            # Moyenne des résultats sur plusieurs exécutions pour robustesse
            iteration_divergences = []
            
            for j in range(CalibrationConfig.SAMPLES_PER_PARAM_SET):
                # Configuration du simulateur avec ces paramètres
                sim_config = {
                    "simulation_days": CalibrationConfig.SIMULATION_TICKS,
                    "network_size": len(processed_data),  # Même nombre de canaux
                    "time_granularity": CalibrationConfig.TIME_GRANULARITY,
                    **param_dict
                }
                
                # Exécution du simulateur
                sim_env = LightningSimEnvironment(sim_config)
                sim_env.initialize_evolution_engines()
                
                # Simulation sur la période spécifiée
                dummy_engine = None  # Pas de moteur de décision
                simulated_data = sim_env.run_simulation(
                    steps=CalibrationConfig.SIMULATION_TICKS, 
                    decision_engine=dummy_engine
                )
                
                # Extraction des distributions simulées
                sim_distributions = self._extract_distributions(simulated_data)
                
                # Calcul des divergences
                divergences = self._calculate_divergences(reference_distributions, sim_distributions)
                iteration_divergences.append(divergences)
            
            # Moyennes des divergences sur toutes les exécutions
            avg_divergences = {}
            for metric in self.metrics.get_all_metrics():
                values = [d.get(metric, 1.0) for d in iteration_divergences if metric in d]
                if values:
                    avg_divergences[metric] = sum(values) / len(values)
                else:
                    avg_divergences[metric] = 1.0  # Valeur par défaut (divergence maximale)
            
            # Calcul de la divergence totale pondérée
            metric_weights = self.metrics.get_metric_weights()
            total_divergence = sum(avg_divergences.get(metric, 0) * weight 
                                 for metric, weight in metric_weights.items())
            
            # Log des résultats
            result = {
                "iteration": i,
                "params": param_dict,
                "divergences": avg_divergences,
                "total_divergence": total_divergence,
                "accepted": total_divergence < best_score
            }
            results_log.append(result)
            
            # Mise à jour des meilleurs paramètres
            if total_divergence < best_score:
                best_score = total_divergence
                best_params = param_dict.copy()
                logger.info(f"Nouveaux meilleurs paramètres trouvés: {best_params} (score: {best_score:.4f})")
            
            # Early stopping si convergence après un nombre minimum d'itérations
            if (i >= CalibrationConfig.EARLY_STOPPING_MIN_ITERATIONS and 
                best_score < CalibrationConfig.CONVERGENCE_THRESHOLD):
                logger.info(f"Convergence atteinte après {i+1} itérations, arrêt anticipé.")
                break
        
        # Calculer les p-values finales pour les meilleurs paramètres
        self._calculate_final_p_values(reference_distributions, best_params)
        
        # Sauvegarde des résultats
        self._save_calibration_results(results_log, best_params, best_score)
        
        return best_params, best_score
    
    def _create_data_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée un résumé des données d'entrée pour traçabilité
        
        Args:
            data: Données d'entrée
            
        Returns:
            Résumé des données
        """
        summary = {
            "num_channels": len(data) if isinstance(data, dict) else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Si c'est un dictionnaire de canaux, calculer des statistiques supplémentaires
        if isinstance(data, dict):
            total_records = 0
            avg_channel_days = 0
            
            for channel_id, channel_data in data.items():
                if isinstance(channel_data, list):
                    total_records += len(channel_data)
                    avg_channel_days += len(channel_data)
            
            if len(data) > 0:
                avg_channel_days /= len(data)
                
            summary["total_records"] = total_records
            summary["avg_days_per_channel"] = avg_channel_days
        
        return summary
    
    def _calculate_final_p_values(self, real_dist: Dict[str, np.ndarray], 
                                best_params: Dict[str, float]) -> None:
        """
        Calcule les p-values finales pour les meilleurs paramètres
        
        Args:
            real_dist: Distributions des données réelles
            best_params: Meilleurs paramètres trouvés
        """
        # Exécuter une dernière fois le simulateur avec les meilleurs paramètres
        sim_config = {
            "simulation_days": CalibrationConfig.SIMULATION_TICKS,
            "network_size": 5,  # Valeur par défaut
            "time_granularity": CalibrationConfig.TIME_GRANULARITY,
            **best_params
        }
        
        # Exécution du simulateur
        sim_env = LightningSimEnvironment(sim_config)
        sim_env.initialize_evolution_engines()
        dummy_engine = None
        simulated_data = sim_env.run_simulation(
            steps=CalibrationConfig.SIMULATION_TICKS, 
            decision_engine=dummy_engine
        )
        
        # Extraction des distributions simulées
        sim_dist = self._extract_distributions(simulated_data)
        
        # Calcul des p-values pour chaque métrique
        self.final_p_values = {}
        for metric_name, real_values in real_dist.items():
            if metric_name not in sim_dist:
                continue
                
            sim_values = sim_dist[metric_name]
            
            # Test statistique selon la métrique
            if len(real_values) < 2 or len(sim_values) < 2:
                continue
                
            # Test de Kolmogorov-Smirnov
            _, p_value = stats.ks_2samp(real_values, sim_values)
            self.final_p_values[metric_name] = p_value
    
    def _preprocess_node_data(self, raw_data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """
        Prétraite les données brutes du nœud pour la calibration.
        - Supprime les valeurs aberrantes
        - Impute les valeurs manquantes
        - Agrège selon la granularité définie
        
        Args:
            raw_data: Données brutes du nœud
            
        Returns:
            Données prétraitées
        """
        logger.info("Prétraitement des données du nœud...")
        
        # Détection de valeurs aberrantes (méthode IQR)
        def remove_outliers(series):
            if len(series) < 4:  # Pas assez de données pour l'IQR
                return series
                
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            return series[(series >= lower_bound) & (series <= upper_bound)]
        
        # Traitement des valeurs manquantes
        def impute_missing(df, col):
            if df[col].isna().any():
                # Imputation par moyenne ou médiane selon la distribution
                if stats.normaltest(df[col].dropna())[1] > 0.05:  # Test de normalité
                    df[col] = df[col].fillna(df[col].mean())
                else:
                    df[col] = df[col].fillna(df[col].median())
            return df
        
        # Agrégation temporelle selon la granularité choisie
        if CalibrationConfig.TIME_GRANULARITY == "daily":
            aggregation_func = lambda x: x.resample('D').agg({
                'forward_amount': 'sum',
                'forward_success': 'mean',
                'local_balance': 'last',
                'capacity': 'last'
            })
        elif CalibrationConfig.TIME_GRANULARITY == "hourly":
            aggregation_func = lambda x: x.resample('H').agg({
                'forward_amount': 'sum',
                'forward_success': 'mean',
                'local_balance': 'last',
                'capacity': 'last'
            })
        elif CalibrationConfig.TIME_GRANULARITY == "weekly":
            aggregation_func = lambda x: x.resample('W').agg({
                'forward_amount': 'sum',
                'forward_success': 'mean',
                'local_balance': 'last',
                'capacity': 'last'
            })
        else:
            raise ValueError(f"Granularité temporelle non supportée: {CalibrationConfig.TIME_GRANULARITY}")
        
        # Appliquer les transformations
        cleaned_data = {}
        for channel_id, channel_data in raw_data.items():
            try:
                # Conversion en DataFrame pandas
                df = pd.DataFrame(channel_data)
                
                # Vérifier la présence des colonnes requises
                required_cols = ['timestamp', 'forward_amount', 'forward_success', 
                               'local_balance', 'capacity']
                missing_cols = [col for col in required_cols if col not in df.columns]
                
                if missing_cols:
                    logger.warning(f"Canal {channel_id} manque de colonnes: {missing_cols}")
                    continue
                
                # Convertir la colonne timestamp en datetime et définir comme index
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                
                # Suppression des valeurs aberrantes
                for col in ['forward_amount', 'local_balance']:
                    if col in df.columns:
                        valid_indices = remove_outliers(df[col]).index
                        df = df.loc[df.index.isin(valid_indices)]
                
                # Imputation des valeurs manquantes
                for col in df.columns:
                    if df[col].isna().any():
                        df = impute_missing(df, col)
                
                # Agrégation temporelle
                df = aggregation_func(df)
                
                # Ajout des métriques dérivées
                if 'local_balance' in df.columns and 'capacity' in df.columns:
                    df['liquidity_ratio'] = df['local_balance'] / df['capacity']
                    df['liquidity_ratio_change'] = df['liquidity_ratio'].diff()
                
                cleaned_data[channel_id] = df
            except Exception as e:
                logger.error(f"Erreur lors du prétraitement du canal {channel_id}: {str(e)}")
        
        return cleaned_data
    
    def _extract_distributions(self, data: Dict[str, Any]) -> Dict[str, np.ndarray]:
        """
        Extrait les distributions des différentes métriques à partir des données
        
        Args:
            data: Données prétraitées
            
        Returns:
            Dictionnaire des distributions
        """
        distributions = {}
        
        # Volume de forwarding
        forward_volumes = []
        for channel_id, df in data.items():
            if 'forward_amount' in df.columns:
                forward_volumes.extend(df['forward_amount'].tolist())
        
        if forward_volumes:
            # Filtrer les valeurs négatives ou nulles
            forward_volumes = [v for v in forward_volumes if v > 0]
            distributions["forward_volume_distribution"] = np.array(forward_volumes)
        
        # Taux de succès
        success_rates = []
        for channel_id, df in data.items():
            if 'forward_success' in df.columns:
                success_rates.extend(df['forward_success'].tolist())
        
        if success_rates:
            distributions["success_rate_distribution"] = np.array(success_rates)
        
        # Évolution du ratio de liquidité
        liquidity_changes = []
        for channel_id, df in data.items():
            if 'liquidity_ratio_change' in df.columns:
                liquidity_changes.extend(df['liquidity_ratio_change'].dropna().tolist())
        
        if liquidity_changes:
            distributions["liquidity_ratio_evolution"] = np.array(liquidity_changes)
        
        # Élasticité des frais - requiert des données de changement de frais
        # Ceci est plus complexe et nécessiterait des données supplémentaires
        fee_elasticity_data = self._calculate_fee_elasticity(data)
        if fee_elasticity_data is not None:
            distributions["fee_elasticity"] = fee_elasticity_data
        
        return distributions
    
    def _calculate_fee_elasticity(self, data: Dict[str, pd.DataFrame]) -> Optional[float]:
        """
        Calcule l'élasticité des frais à partir des données
        
        Args:
            data: Données prétraitées
            
        Returns:
            Estimation de l'élasticité des frais ou None
        """
        # Cette fonction nécessiterait des données de changement de frais
        # Pour l'instant, retourne None (implémentation future)
        return None
    
    def _calculate_divergences(self, real_dist: Dict[str, np.ndarray], 
                             sim_dist: Dict[str, np.ndarray]) -> Dict[str, float]:
        """
        Calcule les divergences entre distributions réelles et simulées
        
        Args:
            real_dist: Distributions des données réelles
            sim_dist: Distributions des données simulées
            
        Returns:
            Dictionnaire des divergences par métrique
        """
        divergences = {}
        metrics_config = self.metrics.get_all_metrics()
        
        for metric_name, config in metrics_config.items():
            if (metric_name not in real_dist or metric_name not in sim_dist or
                len(real_dist[metric_name]) < 2 or len(sim_dist[metric_name]) < 2):
                continue
                
            # Appliquer le test statistique approprié
            if config.test == "kolmogorov_smirnov":
                statistic, p_value = stats.ks_2samp(
                    real_dist[metric_name],
                    sim_dist[metric_name]
                )
                # Plus la statistique KS est petite, plus les distributions sont similaires
                # On normalise pour avoir 0 = identiques, 1 = totalement différentes
                divergences[metric_name] = min(1.0, statistic)
                
            elif config.test == "jensen_shannon_divergence":
                # Normaliser les histogrammes pour calculer la divergence JS
                hist_real, _ = np.histogram(real_dist[metric_name], bins=config.bins, density=True)
                hist_sim, _ = np.histogram(sim_dist[metric_name], bins=config.bins, density=True)
                
                # Éviter les valeurs nulles qui poseraient problème
                hist_real = np.maximum(hist_real, 1e-10)
                hist_sim = np.maximum(hist_sim, 1e-10)
                
                # Normaliser
                hist_real = hist_real / np.sum(hist_real)
                hist_sim = hist_sim / np.sum(hist_sim)
                
                # Calculer la divergence de Jensen-Shannon
                js_div = distance.jensenshannon(hist_real, hist_sim)
                divergences[metric_name] = min(1.0, js_div)
                
            elif config.test == "pearson_correlation":
                # Pour l'élasticité des frais, on mesure la corrélation
                if isinstance(real_dist[metric_name], float) and isinstance(sim_dist[metric_name], float):
                    # Si on a des valeurs uniques, comparer directement
                    diff = abs(real_dist[metric_name] - sim_dist[metric_name])
                    # Plus la différence est faible, plus les valeurs sont proches
                    divergences[metric_name] = min(1.0, diff)
                else:
                    # Sinon calculer la corrélation entre séries
                    corr, _ = stats.pearsonr(real_dist[metric_name], sim_dist[metric_name])
                    # Transformer la corrélation en divergence (1 - abs(corr))
                    divergences[metric_name] = 1.0 - min(1.0, abs(corr))
        
        return divergences
    
    def _generate_param_combinations(self, param_ranges: Dict[str, np.ndarray]) -> List[Dict[str, float]]:
        """
        Génère toutes les combinaisons de paramètres à tester
        
        Args:
            param_ranges: Plages de valeurs pour chaque paramètre
            
        Returns:
            Liste de dictionnaires de paramètres
        """
        # Extraire les noms et valeurs des paramètres
        param_names = list(param_ranges.keys())
        param_values = [param_ranges[name] for name in param_names]
        
        # Générer toutes les combinaisons
        combinations = list(itertools.product(*param_values))
        
        # Convertir en liste de dictionnaires
        param_dicts = []
        for combo in combinations:
            param_dict = {name: value for name, value in zip(param_names, combo)}
            param_dicts.append(param_dict)
        
        return param_dicts
    
    def _evaluate_stability(self, results_log: List[Dict[str, Any]]) -> str:
        """
        Évalue le profil de stabilité de la calibration
        
        Args:
            results_log: Log des résultats de calibration
            
        Returns:
            Profil de stabilité: stable, fragile ou incohérent
        """
        # Analyser les 10 meilleures combinaisons (ou moins s'il y en a moins)
        top_n = min(10, len(results_log))
        top_results = sorted(results_log, key=lambda x: x['total_divergence'])[:top_n]
        
        param_stability = {}
        
        # Pour chaque paramètre, calculer l'écart-type normalisé
        for param in top_results[0]['params'].keys():
            values = [run['params'][param] for run in top_results]
            value_range = max(values) - min(values)
            
            if value_range > 0:
                normalized_std = np.std(values) / value_range
            else:
                normalized_std = 0
                
            param_stability[param] = normalized_std
        
        # Déterminer le profil de stabilité
        avg_stability = np.mean(list(param_stability.values()))
        
        if avg_stability < 0.1:
            return "stable"
        elif avg_stability < 0.3:
            return "fragile"
        else:
            return "incohérent"
    
    def _save_calibration_results(self, results_log: List[Dict[str, Any]], 
                                best_params: Dict[str, float], 
                                best_score: float) -> str:
        """
        Sauvegarde les résultats de la calibration
        
        Args:
            results_log: Log des résultats de calibration
            best_params: Meilleurs paramètres trouvés
            best_score: Score des meilleurs paramètres
            
        Returns:
            Identifiant de la calibration
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        node_id = self.node_id
        run_id = f"calibration_{timestamp}_{node_id}"
        
        # Calculer le hash des données d'entrée
        data_hash = hashlib.md5(json.dumps(self.input_data_summary, sort_keys=True).encode()).hexdigest()[:8]
        
        # Évaluer la stabilité
        stability_profile = self._evaluate_stability(results_log)
        
        # Résultat complet
        results_dir = CALIBRATION_RESULTS_PATH / run_id
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarder le log complet
        with open(results_dir / "calibration_log.json", "w") as f:
            json.dump(results_log, f, indent=2)
        
        # Sauvegarder les meilleurs paramètres
        result_data = {
            "run_id": run_id,
            "node_id": node_id,
            "timestamp": timestamp,
            "params": best_params,
            "score": best_score,
            "p_values": self.final_p_values,
            "data_hash": data_hash,
            "stability_profile": stability_profile,
            "convergence_threshold": CalibrationConfig.CONVERGENCE_THRESHOLD,
            "simulation_config": {
                "time_granularity": CalibrationConfig.TIME_GRANULARITY,
                "simulation_ticks": CalibrationConfig.SIMULATION_TICKS,
                "samples_per_param_set": CalibrationConfig.SAMPLES_PER_PARAM_SET
            }
        }
        
        with open(results_dir / "best_params.json", "w") as f:
            json.dump(result_data, f, indent=2)
        
        # Sauvegarder une copie dans l'archive
        with open(CALIBRATION_ARCHIVE_PATH / f"{run_id}.json", "w") as f:
            json.dump(result_data, f, indent=2)
        
        # Créer un résumé markdown dans le cache
        with open(CALIBRATION_CACHE_PATH / f"{run_id}_summary.md", "w") as f:
            f.write(f"# Calibration {run_id}\n\n")
            f.write(f"**Node ID**: {node_id}\n")
            f.write(f"**Timestamp**: {timestamp}\n")
            f.write(f"**Score total**: {best_score:.4f}\n")
            f.write(f"**Profil de stabilité**: {stability_profile}\n\n")
            
            f.write("## Paramètres optimaux\n\n")
            for param, value in best_params.items():
                f.write(f"- **{param}**: {value:.4f}\n")
            
            f.write("\n## Résultats des tests statistiques\n\n")
            f.write("| Métrique | p-value | Verdict |\n")
            f.write("|----------|---------|--------|\n")
            
            for metric, p_value in self.final_p_values.items():
                verdict = "✅ Indistinguable" if p_value > 0.05 else "❌ Distinguable"
                f.write(f"| {metric} | {p_value:.4f} | {verdict} |\n")
        
        logger.info(f"Résultats de calibration sauvegardés avec ID: {run_id}")
        logger.info(f"Profil de stabilité: {stability_profile}")
        
        return run_id
        
    def load_calibration(self, run_id: str) -> Dict[str, Any]:
        """
        Charge une calibration précédente
        
        Args:
            run_id: Identifiant de la calibration
            
        Returns:
            Données de la calibration ou None si non trouvée
        """
        archive_path = CALIBRATION_ARCHIVE_PATH / f"{run_id}.json"
        
        if not archive_path.exists():
            logger.error(f"Calibration {run_id} non trouvée")
            return None
        
        try:
            with open(archive_path, "r") as f:
                calibration_data = json.load(f)
            
            return calibration_data
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la calibration {run_id}: {str(e)}")
            return None 