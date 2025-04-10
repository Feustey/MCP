import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from typing import Dict, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class MetricsVisualizer:
    def __init__(self, output_dir: str = "evaluation_plots"):
        self.output_dir = output_dir
        plt.style.use('default')
        
    def plot_learning_curves(self, train_scores: List[float], 
                           val_scores: List[float], metric_name: str):
        """
        Trace les courbes d'apprentissage
        """
        try:
            plt.figure(figsize=(10, 6))
            epochs = range(1, len(train_scores) + 1)
            
            plt.plot(epochs, train_scores, 'b-', label='Entraînement')
            plt.plot(epochs, val_scores, 'r-', label='Validation')
            
            plt.title(f'Courbes d\'apprentissage - {metric_name}')
            plt.xlabel('Époques')
            plt.ylabel(metric_name)
            plt.legend()
            
            filename = f"{self.output_dir}/learning_curves_{metric_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filename)
            plt.close()
            
            logger.info(f"Courbes d'apprentissage sauvegardées dans {filename}")
            
        except Exception as e:
            logger.error(f"Erreur lors du tracé des courbes d'apprentissage: {str(e)}")
    
    def plot_confusion_matrix(self, confusion_matrix: Dict[str, int]):
        """
        Trace la matrice de confusion
        """
        try:
            plt.figure(figsize=(8, 6))
            cm_array = np.array([
                [confusion_matrix['true_negatives'], confusion_matrix['false_positives']],
                [confusion_matrix['false_negatives'], confusion_matrix['true_positives']]
            ])
            
            sns.heatmap(cm_array, annot=True, fmt='d', cmap='Blues')
            plt.title('Matrice de confusion')
            plt.xlabel('Prédictions')
            plt.ylabel('Valeurs réelles')
            
            filename = f"{self.output_dir}/confusion_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filename)
            plt.close()
            
            logger.info(f"Matrice de confusion sauvegardée dans {filename}")
            
        except Exception as e:
            logger.error(f"Erreur lors du tracé de la matrice de confusion: {str(e)}")
    
    def plot_roc_curve(self, fpr: List[float], tpr: List[float], auc: float):
        """
        Trace la courbe ROC
        """
        try:
            plt.figure(figsize=(8, 6))
            plt.plot(fpr, tpr, color='darkorange', lw=2, 
                    label=f'ROC curve (AUC = {auc:.2f})')
            plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
            
            plt.xlim([0.0, 1.0])
            plt.ylim([0.0, 1.05])
            plt.xlabel('False Positive Rate')
            plt.ylabel('True Positive Rate')
            plt.title('Courbe ROC')
            plt.legend(loc="lower right")
            
            filename = f"{self.output_dir}/roc_curve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filename)
            plt.close()
            
            logger.info(f"Courbe ROC sauvegardée dans {filename}")
            
        except Exception as e:
            logger.error(f"Erreur lors du tracé de la courbe ROC: {str(e)}")
    
    def plot_metrics_history(self, metrics_history: List[Dict], metric_name: str):
        """
        Trace l'historique des métriques
        """
        try:
            plt.figure(figsize=(10, 6))
            timestamps = [m['timestamp'] for m in metrics_history]
            values = [m['metrics'][metric_name]['mean'] for m in metrics_history]
            std_values = [m['metrics'][metric_name]['std'] for m in metrics_history]
            
            plt.plot(timestamps, values, 'b-', label=metric_name)
            plt.fill_between(timestamps, 
                           np.array(values) - np.array(std_values),
                           np.array(values) + np.array(std_values),
                           alpha=0.2)
            
            plt.title(f'Évolution de {metric_name} dans le temps')
            plt.xlabel('Date')
            plt.ylabel(metric_name)
            plt.xticks(rotation=45)
            plt.legend()
            
            filename = f"{self.output_dir}/metrics_history_{metric_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filename)
            plt.close()
            
            logger.info(f"Historique des métriques sauvegardé dans {filename}")
            
        except Exception as e:
            logger.error(f"Erreur lors du tracé de l'historique des métriques: {str(e)}")
    
    def plot_domain_metrics(self, domain_metrics: Dict[str, float]):
        """
        Trace les métriques spécifiques au domaine
        """
        try:
            plt.figure(figsize=(10, 6))
            metrics = list(domain_metrics.keys())
            values = list(domain_metrics.values())
            
            plt.bar(metrics, values)
            plt.title('Métriques spécifiques au domaine')
            plt.xlabel('Métriques')
            plt.ylabel('Valeurs')
            plt.xticks(rotation=45)
            
            filename = f"{self.output_dir}/domain_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filename)
            plt.close()
            
            logger.info(f"Métriques du domaine sauvegardées dans {filename}")
            
        except Exception as e:
            logger.error(f"Erreur lors du tracé des métriques du domaine: {str(e)}") 