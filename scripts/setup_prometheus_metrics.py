#!/usr/bin/env python3
"""
Configuration et exposition des métriques Prometheus pour MCP
Dernière mise à jour: 10 mai 2025
"""

import os
import sys
import time
import logging
import argparse
from prometheus_client import start_http_server, Counter, Gauge, Enum, Info
from prometheus_client.core import CollectorRegistry
import yaml
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports relatifs
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
sys.path.append(str(root_dir))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("prometheus_metrics")

# Fichier de configuration par défaut
CONFIG_FILE = Path(root_dir, "config", "fee_optimizer.yaml")

class MCPMetricsExporter:
    """
    Exportateur de métriques Prometheus pour MCP
    """
    
    def __init__(self, config_file=None, port=9090):
        """
        Initialise l'exportateur de métriques
        
        Args:
            config_file: Chemin vers le fichier de configuration
            port: Port sur lequel exposer les métriques
        """
        self.config_file = config_file or str(CONFIG_FILE)
        self.config = self._load_config()
        self.port = port or self.config.get("prometheus", {}).get("port", 9090)
        
        # Créer un registre de métriques
        self.registry = CollectorRegistry()
        
        # Initialiser les métriques
        self._setup_metrics()
        
        logger.info(f"Exportateur de métriques initialisé sur le port {self.port}")
    
    def _load_config(self):
        """Charge la configuration depuis un fichier YAML"""
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Configuration chargée depuis {self.config_file}")
                return config
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {e}")
            return {
                "prometheus": {
                    "enabled": True,
                    "port": 9090
                }
            }
            
    def _setup_metrics(self):
        """Configure les métriques Prometheus"""
        # Métrique pour les mocks activés
        self.mock_mode_active = Gauge(
            'mcp_mock_mode_active', 
            'Indique si un mock est activé dans le système (1=actif, 0=inactif)',
            ['module'],
            registry=self.registry
        )
        
        # Métrique pour le comptage des mises à jour de frais
        self.fee_updates_total = Counter(
            'mcp_fee_updates_total',
            'Nombre total de mises à jour de frais',
            ['status', 'action_type'],
            registry=self.registry
        )
        
        # Métrique pour le comptage des rollbacks
        self.rollbacks_total = Counter(
            'mcp_rollbacks_total',
            'Nombre total de rollbacks',
            ['status'],
            registry=self.registry
        )
        
        # Métrique pour la confiance moyenne des mises à jour
        self.fee_update_confidence = Gauge(
            'mcp_fee_update_confidence',
            'Niveau de confiance moyen des mises à jour de frais',
            registry=self.registry
        )
        
        # Métrique pour le mode d'exécution
        self.execution_mode = Enum(
            'mcp_execution_mode',
            'Mode d\'exécution actuel (dry_run, production)',
            states=['dry_run', 'production'],
            registry=self.registry
        )
        
        # Informations sur le système
        self.system_info = Info(
            'mcp_system',
            'Informations sur le système MCP',
            registry=self.registry
        )
        
        # Métrique pour la latence des mises à jour
        self.fee_update_latency = Gauge(
            'mcp_fee_update_latency_seconds',
            'Latence des mises à jour de frais en secondes',
            registry=self.registry
        )
        
        # Initialiser les valeurs par défaut
        self._init_default_values()
    
    def _init_default_values(self):
        """Initialise les valeurs par défaut des métriques"""
        # Vérifier les mocks utilisés
        env = os.environ.get("MCP_ENV", "prod").lower()
        
        # Détecter la présence de mocks dans le module actuel
        try:
            from scripts.fee_optimizer_scheduler import using_mocks, has_real_lnbits, has_real_redis, has_real_mongo
            
            # Mettre à jour les métriques de mock
            self.mock_mode_active.labels(module="any").set(1 if using_mocks else 0)
            self.mock_mode_active.labels(module="lnbits").set(0 if has_real_lnbits else 1)
            self.mock_mode_active.labels(module="redis").set(0 if has_real_redis else 1)
            self.mock_mode_active.labels(module="mongodb").set(0 if has_real_mongo else 1)
        except ImportError:
            logger.warning("Impossible d'importer les informations sur les mocks, utilisation de valeurs par défaut")
            self.mock_mode_active.labels(module="any").set(0)
            self.mock_mode_active.labels(module="lnbits").set(0)
            self.mock_mode_active.labels(module="redis").set(0)
            self.mock_mode_active.labels(module="mongodb").set(0)
        
        # Informations sur le système
        self.system_info.info({
            'environment': env,
            'version': '0.1.0',
            'config_file': self.config_file
        })
        
        # Mode d'exécution (par défaut dry_run)
        self.execution_mode.state('dry_run')
    
    def update_mock_status(self, module, is_mock):
        """
        Met à jour le statut de mock pour un module
        
        Args:
            module: Nom du module
            is_mock: True si le module est un mock, False sinon
        """
        self.mock_mode_active.labels(module=module).set(1 if is_mock else 0)
    
    def update_execution_mode(self, is_dry_run):
        """
        Met à jour le mode d'exécution
        
        Args:
            is_dry_run: True si le mode est dry_run, False pour production
        """
        self.execution_mode.state('dry_run' if is_dry_run else 'production')
    
    def record_fee_update(self, success, action_type):
        """
        Enregistre une mise à jour de frais
        
        Args:
            success: True si la mise à jour a réussi, False sinon
            action_type: Type d'action (increase, decrease, maintain)
        """
        status = "success" if success else "failure"
        self.fee_updates_total.labels(status=status, action_type=action_type).inc()
    
    def record_rollback(self, success):
        """
        Enregistre un rollback
        
        Args:
            success: True si le rollback a réussi, False sinon
        """
        status = "success" if success else "failure"
        self.rollbacks_total.labels(status=status).inc()
    
    def update_confidence(self, confidence):
        """
        Met à jour le niveau de confiance moyen
        
        Args:
            confidence: Niveau de confiance (0-1)
        """
        self.fee_update_confidence.set(confidence)
    
    def start(self):
        """Démarre le serveur Prometheus"""
        start_http_server(self.port, registry=self.registry)
        logger.info(f"Serveur de métriques Prometheus démarré sur le port {self.port}")

def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description="Exporter de métriques Prometheus pour MCP")
    parser.add_argument("--config", help="Chemin vers le fichier de configuration")
    parser.add_argument("--port", type=int, help="Port sur lequel exposer les métriques")
    args = parser.parse_args()
    
    # Créer l'exportateur de métriques
    exporter = MCPMetricsExporter(
        config_file=args.config,
        port=args.port
    )
    
    # Démarrer le serveur
    try:
        exporter.start()
        # Boucle principale
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Arrêt du serveur de métriques")
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du serveur de métriques: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 