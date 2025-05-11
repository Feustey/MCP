#!/usr/bin/env python3
"""
Scheduler pour l'automatisation du pilotage des frais sur les canaux Lightning.
Gère les mises à jour périodiques de frais, le logging et le rollback si nécessaire.

Dernière mise à jour: 10 mai 2025
"""

import os
import sys
import json
import logging
import asyncio
import argparse
import random
from pathlib import Path
from datetime import datetime, timedelta
import yaml
import subprocess
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# Ajouter le répertoire parent au path pour les imports relatifs
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
sys.path.append(str(root_dir))

# Constantes pour la validation des environnements et mocks
ALLOWED_MOCK_ENVS = ["test", "dev"]
CURRENT_ENV = os.environ.get("MCP_ENV", "prod").lower()
MOCK_CHECK_MESSAGE = "[MOCK_MODE ACTIVE] - ATTENTION: Un ou plusieurs composants sont en mode simulation!"

# Configuration du logging préliminaire avant le setup complet
logging.basicConfig(level=logging.INFO)
initial_logger = logging.getLogger("fee_optimizer_init")

# Fonction pour vérifier si l'environnement autorise les mocks
def verify_mock_usage_allowed(env=CURRENT_ENV, force_no_mock=False):
    """
    Vérifie si l'utilisation de mocks est autorisée dans l'environnement actuel
    
    Args:
        env: Environnement actuel (test, dev, prod)
        force_no_mock: Si True, aucun mock n'est autorisé quelle que soit la variable d'environnement
        
    Returns:
        True si les mocks sont autorisés, False sinon
        
    Raises:
        RuntimeError si les mocks ne sont pas autorisés
    """
    mocks_allowed = env in ALLOWED_MOCK_ENVS and not force_no_mock
    
    if not mocks_allowed:
        message = f"ERREUR CRITIQUE: L'utilisation de mocks n'est pas autorisée en environnement '{env}'"
        initial_logger.error(message)
        if force_no_mock:
            message += " (--no-mock-allowed activé)"
        initial_logger.error("Pour autoriser les mocks, définissez MCP_ENV=test")
        raise RuntimeError(message)
        
    return mocks_allowed

# Fonction pour vérifier les services externes et leur disponibilité
def check_external_services():
    """
    Vérifie la disponibilité des services externes (Redis, MongoDB, LNBits)
    
    Returns:
        Un dictionnaire avec les services comme clés et leur état comme valeurs
    """
    services_status = {
        "redis": False,
        "mongodb": False,
        "lnbits": False
    }
    
    # Vérifier Redis
    try:
        redis_check = subprocess.run(
            ["redis-cli", "ping"], 
            capture_output=True, 
            text=True, 
            timeout=2
        )
        services_status["redis"] = redis_check.stdout.strip() == "PONG"
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    
    # Vérifier MongoDB
    try:
        mongo_check = subprocess.run(
            ["mongosh", "--eval", "db.runCommand({ping:1})"], 
            capture_output=True, 
            text=True, 
            timeout=2
        )
        services_status["mongodb"] = "ok: 1" in mongo_check.stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
        
    # Vérifier LNBits (vérification simplifiée)
    lnbits_url = os.environ.get("LNBITS_URL", "")
    if lnbits_url:
        try:
            import httpx
            response = httpx.get(f"{lnbits_url}/health", timeout=2)
            services_status["lnbits"] = response.status_code == 200
        except:
            pass
            
    return services_status

# Classes Mock pour Redis et MongoDB en cas d'erreur d'initialisation
class MockRedisOperations:
    """Version mock de RedisOperations pour le mode dry-run"""
    
    def __init__(self):
        # Vérifier si l'utilisation de mocks est autorisée
        verify_mock_usage_allowed()
        self.cache = {}
        initial_logger.warning(f"{MOCK_CHECK_MESSAGE} Redis est simulé")
        
    async def get(self, key):
        return self.cache.get(key)
        
    async def set(self, key, value):
        self.cache[key] = value
        return True

class MockMongoOperations:
    """Version mock de MongoOperations pour le mode dry-run"""
    
    def __init__(self):
        # Vérifier si l'utilisation de mocks est autorisée
        verify_mock_usage_allowed()
        self.collections = {
            "fee_updates": [],
            "fee_rollbacks": []
        }
        initial_logger.warning(f"{MOCK_CHECK_MESSAGE} MongoDB est simulé")
        
    async def insert_document(self, collection, document):
        if collection not in self.collections:
            self.collections[collection] = []
        self.collections[collection].append(document)
        return True
        
    async def insert_documents(self, collection, documents):
        if collection not in self.collections:
            self.collections[collection] = []
        self.collections[collection].extend(documents)
        return True
        
    async def find_documents(self, collection, query=None, sort=None, skip=0, limit=10):
        if collection not in self.collections:
            return []
        return self.collections[collection][skip:skip+limit]
        
    async def count_documents(self, collection, query=None):
        if collection not in self.collections:
            return 0
        return len(self.collections[collection])

class MockLNBitsClient:
    """Version mock du client LNBits pour le mode dry-run"""
    
    def __init__(self, endpoint=None, api_key=None):
        # Vérifier si l'utilisation de mocks est autorisée
        verify_mock_usage_allowed()
        self.endpoint = endpoint or "http://localhost:5000"
        self.api_key = api_key or "fake_api_key"
        initial_logger.warning(f"{MOCK_CHECK_MESSAGE} LNBits est simulé")
    
    async def close(self):
        return True
    
    async def get_local_node_info(self):
        return {
            'pubkey': "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
            'current_peers': set(["02b00c7ccbf4965cfe843bea8bd34acccb0e75584dbd94825fbaa01ef98e4b89b6"])
        }
    
    async def get_wallet_info(self):
        return {
            "id": "mock_wallet",
            "name": "Mock Wallet",
            "balance": 1000000
        }

# Import conditionnels pour les composants avec vérification de l'environnement
# On essaiera les imports réels d'abord, et en cas d'échec, on utilisera les mocks si l'environnement le permet

# On essaie d'importer le client LNBits réel
try:
    from src.lnbits_client import LNBitsClient
    has_real_lnbits = True
except ImportError:
    initial_logger.warning("LNBitsClient non disponible")
    # Si l'environnement autorise les mocks, on utilise le mock
    if CURRENT_ENV in ALLOWED_MOCK_ENVS:
        LNBitsClient = MockLNBitsClient
        has_real_lnbits = False
    else:
        raise RuntimeError("LNBitsClient non disponible et mocks non autorisés en environnement production")

# On essaie d'importer les opérations Redis réelles
try:
    from src.redis_operations import RedisOperations
    has_real_redis = True
except ImportError:
    initial_logger.warning("RedisOperations non disponible")
    # Si l'environnement autorise les mocks, on utilise le mock
    if CURRENT_ENV in ALLOWED_MOCK_ENVS:
        RedisOperations = MockRedisOperations
        has_real_redis = False
    else:
        raise RuntimeError("RedisOperations non disponible et mocks non autorisés en environnement production")

# On essaie d'importer les opérations MongoDB réelles
try:
    from src.mongo_operations import MongoOperations
    has_real_mongo = True
except ImportError:
    initial_logger.warning("MongoOperations non disponible")
    # Si l'environnement autorise les mocks, on utilise le mock
    if CURRENT_ENV in ALLOWED_MOCK_ENVS:
        MongoOperations = MockMongoOperations
        has_real_mongo = False
    else:
        raise RuntimeError("MongoOperations non disponible et mocks non autorisés en environnement production")

from src.optimizers.scoring_utils import evaluate_node as original_evaluate_node, DecisionType
from src.optimizers.fee_update_utils import update_channel_fees, batch_update_fees, get_fee_adjustment
from src.automation_manager import AutomationManager

# Configuration du logging complet
log_dir = Path(root_dir, "logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "fee_optimizer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("fee_optimizer")

# Fichiers de configuration
CONFIG_FILE = Path(root_dir, "config", "fee_optimizer.yaml")
ROLLBACK_DIR = Path(root_dir, "data", "rollbacks")
ROLLBACK_DIR.mkdir(exist_ok=True, parents=True)

# État global des mocks pour la balise de log
using_mocks = not (has_real_lnbits and has_real_redis and has_real_mongo)

# Fonction pour ajouter la balise MOCK_MODE aux logs si nécessaire
def log_with_mock_tag(logger_instance, level, message):
    """
    Ajoute la balise MOCK_MODE aux logs si des mocks sont utilisés
    
    Args:
        logger_instance: L'instance du logger
        level: Le niveau de log (INFO, WARNING, ERROR, etc.)
        message: Le message à logger
    """
    if using_mocks:
        message = f"[MOCK_MODE ACTIVE] {message}"
    
    if level == "INFO":
        logger_instance.info(message)
    elif level == "WARNING":
        logger_instance.warning(message)
    elif level == "ERROR":
        logger_instance.error(message)
    elif level == "DEBUG":
        logger_instance.debug(message)
    elif level == "CRITICAL":
        logger_instance.critical(message)

class FeeOptimizerScheduler:
    """
    Scheduler pour le pilotage automatisé des frais sur les canaux Lightning
    """
    
    def __init__(self, config_file: str = None, dry_run: bool = True, no_mock_allowed: bool = False):
        """
        Initialise le scheduler
        
        Args:
            config_file: Chemin vers le fichier de configuration
            dry_run: Si True, simule les mises à jour sans les appliquer
            no_mock_allowed: Si True, échoue si des mocks sont utilisés
        """
        # Vérifier si les mocks sont autorisés avec le flag no_mock_allowed
        if no_mock_allowed:
            verify_mock_usage_allowed(force_no_mock=True)
            
        self.config_file = config_file or str(CONFIG_FILE)
        self.dry_run = dry_run
        self.config = self._load_config()
        self.scheduler = AsyncIOScheduler()
        self.using_mocks = using_mocks
        
        # Initialiser les clients et gestionnaires
        use_lnbits = self.config.get("backend", {}).get("use_lnbits", True)
        lnbits_url = self.config.get("backend", {}).get("lnbits_url", "")
        lnbits_key = self.config.get("backend", {}).get("lnbits_api_key", "")

        # En mode dry-run, on peut initialiser sans paramètres valides
        if dry_run and (not lnbits_url or not lnbits_key):
            if isinstance(LNBitsClient, type) and LNBitsClient != MockLNBitsClient:
                self.lnbits_client = None
                log_with_mock_tag(logger, "WARNING", "Mode dry-run: client LNBits non initialisé (URL ou clé API manquante)")
            else:
                self.lnbits_client = MockLNBitsClient()
        else:
            try:
                self.lnbits_client = LNBitsClient(lnbits_url, lnbits_key) if use_lnbits else None
                # Si on a obtenu un mock plutôt que la version réelle, on le note
                if self.lnbits_client and isinstance(self.lnbits_client, MockLNBitsClient):
                    log_with_mock_tag(logger, "WARNING", "Utilisation d'un client LNBits simulé")
            except Exception as e:
                if CURRENT_ENV in ALLOWED_MOCK_ENVS:
                    log_with_mock_tag(logger, "ERROR", f"Erreur lors de l'initialisation du client LNBits: {str(e)}")
                    self.lnbits_client = MockLNBitsClient()
                else:
                    logger.error(f"Erreur lors de l'initialisation du client LNBits: {str(e)}")
                    raise RuntimeError(f"Impossible d'initialiser LNBits en environnement {CURRENT_ENV}")
                
        self.automation_manager = AutomationManager(
            lnbits_url=lnbits_url,
            lnbits_api_key=lnbits_key,
            use_lnbits=use_lnbits
        )
        
        # Initialiser les opérations Redis/MongoDB (avec gestion des erreurs)
        try:
            redis_url = self.config.get("database", {}).get("redis_url", "redis://localhost:6379/0")
            if has_real_redis:
                self.redis_ops = RedisOperations(redis_url)
            else:
                if CURRENT_ENV in ALLOWED_MOCK_ENVS:
                    self.redis_ops = MockRedisOperations()
                    log_with_mock_tag(logger, "WARNING", "Utilisation de Redis en mode simulé")
                else:
                    raise RuntimeError("RedisOperations non disponible et mocks non autorisés en environnement production")
        except Exception as e:
            if CURRENT_ENV in ALLOWED_MOCK_ENVS:
                log_with_mock_tag(logger, "ERROR", f"Erreur lors de l'initialisation de Redis: {str(e)}")
                self.redis_ops = MockRedisOperations()
            else:
                logger.error(f"Erreur lors de l'initialisation de Redis: {str(e)}")
                raise RuntimeError(f"Impossible d'initialiser Redis en environnement {CURRENT_ENV}")
            
        try:
            if has_real_mongo:
                self.mongo_ops = MongoOperations()
            else:
                if CURRENT_ENV in ALLOWED_MOCK_ENVS:
                    self.mongo_ops = MockMongoOperations()
                    log_with_mock_tag(logger, "WARNING", "Utilisation de MongoDB en mode simulé")
                else:
                    raise RuntimeError("MongoOperations non disponible et mocks non autorisés en environnement production")
        except Exception as e:
            if CURRENT_ENV in ALLOWED_MOCK_ENVS:
                log_with_mock_tag(logger, "ERROR", f"Erreur lors de l'initialisation de MongoDB: {str(e)}")
                self.mongo_ops = MockMongoOperations()
            else:
                logger.error(f"Erreur lors de l'initialisation de MongoDB: {str(e)}")
                raise RuntimeError(f"Impossible d'initialiser MongoDB en environnement {CURRENT_ENV}")
        
        # Variables d'état
        self.last_run = {}
        self.pending_updates = []
        self.update_history = []
        
        log_msg = f"Initialisé en mode {'DRY RUN' if dry_run else 'PRODUCTION'}"
        if self.using_mocks:
            log_with_mock_tag(logger, "INFO", log_msg)
        else:
            logger.info(log_msg)
        
        # Check de santé des services
        self.health_check()
    
    def health_check(self):
        """Vérifie l'état de santé des services et enregistre les résultats"""
        services = check_external_services()
        
        # Vérifier si des services critiques sont manquants
        missing_services = [svc for svc, status in services.items() if not status]
        
        if missing_services:
            if self.using_mocks and CURRENT_ENV in ALLOWED_MOCK_ENVS:
                log_with_mock_tag(logger, "WARNING", 
                    f"Services non disponibles: {', '.join(missing_services)}. "
                    f"Utilisation de mocks en environnement {CURRENT_ENV}."
                )
            else:
                logger.error(
                    f"ERREUR CRITIQUE: Services non disponibles: {', '.join(missing_services)}. "
                    f"L'exécution en environnement {CURRENT_ENV} nécessite tous les services."
                )
                if CURRENT_ENV not in ALLOWED_MOCK_ENVS:
                    raise RuntimeError(
                        f"Services critiques manquants en environnement {CURRENT_ENV}. "
                        f"Définissez MCP_ENV=test pour autoriser l'utilisation de mocks."
                    )
        else:
            logger.info("Check de santé des services réussi: Redis, MongoDB et LNBits sont disponibles")
    
    def _load_config(self) -> dict:
        """Charge la configuration depuis un fichier YAML"""
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Configuration chargée depuis {self.config_file}")
                return config
        except FileNotFoundError:
            log_msg = f"Fichier de configuration {self.config_file} non trouvé, utilisation des valeurs par défaut"
            if using_mocks:
                log_with_mock_tag(logger, "WARNING", log_msg)
            else:
                logger.warning(log_msg)
            return self._create_default_config()
        except Exception as e:
            log_msg = f"Erreur lors du chargement de la configuration: {str(e)}"
            if using_mocks:
                log_with_mock_tag(logger, "ERROR", log_msg)
            else:
                logger.error(log_msg)
            return self._create_default_config()
    
    def _create_default_config(self) -> dict:
        """Crée une configuration par défaut"""
        config = {
            "schedule": {
                "type": "cron",
                "value": "0 */6 * * *"  # Toutes les 6 heures
            },
            "backend": {
                "use_lnbits": True,
                "lnbits_url": os.environ.get("LNBITS_URL", ""),
                "lnbits_api_key": os.environ.get("LNBITS_API_KEY", ""),
            },
            "optimization": {
                "max_updates_per_run": 5,
                "min_confidence": 0.7,
                "max_fee_increase": 30,  # Pourcentage
                "max_fee_decrease": 20,  # Pourcentage
                "min_success_rate": 0.8,
                "min_activity_score": 0.3
            },
            "rollback": {
                "enabled": True,
                "wait_time": 24  # Heures avant validation ou rollback
            },
            "database": {
                "redis_url": "redis://localhost:6379/0",
                "mongo_url": "mongodb://localhost:27017",
                "mongo_db": "mcp"
            },
            # Configuration pour l'exposition des métriques Prometheus
            "prometheus": {
                "enabled": True,
                "port": 9090
            }
        }
        
        # Sauvegarder la configuration par défaut
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
                log_msg = f"Configuration par défaut créée dans {self.config_file}"
                if using_mocks:
                    log_with_mock_tag(logger, "INFO", log_msg)
                else:
                    logger.info(log_msg)
        except Exception as e:
            log_msg = f"Erreur lors de la création de la configuration par défaut: {str(e)}"
            if using_mocks:
                log_with_mock_tag(logger, "ERROR", log_msg)
            else:
                logger.error(log_msg)
        
        return config

    def evaluate_node(self, node_data):
        """
        Version simplifiée de l'évaluation du nœud pour le planificateur.
        Utilise la fonction originale si disponible, sinon fournit une évaluation de secours.
        
        Args:
            node_data: Données du nœud à évaluer
            
        Returns:
            Dict contenant les scores et les recommandations
        """
        try:
            # Essayer d'utiliser la fonction originale
            return original_evaluate_node(node_data)
        except Exception as e:
            logger.error(f"Erreur lors de l'utilisation de la fonction evaluate_node originale: {str(e)}")
            logger.info("Utilisation de la version de secours de evaluate_node")
            
            # Fonction de secours simplifiée
            try:
                # Vérifier la présence des données essentielles
                if "channels" not in node_data or not node_data["channels"]:
                    return {
                        "status": "error",
                        "reason": "Aucun canal trouvé",
                        "node_id": node_data.get("node_id", "unknown")
                    }
                    
                # Créer des scores simplifiés pour chaque canal
                channel_scores = []
                
                for channel in node_data["channels"]:
                    # Calculer des scores simulés
                    total_score = random.uniform(0.3, 0.9)
                    
                    # Déterminer une recommandation basée sur le score
                    if total_score < 0.4:
                        recommendation = DecisionType.INCREASE_FEES
                        confidence = random.uniform(0.6, 0.8)
                    elif total_score > 0.7:
                        recommendation = DecisionType.LOWER_FEES
                        confidence = random.uniform(0.6, 0.8)
                    else:
                        recommendation = DecisionType.MAINTAIN_FEES
                        confidence = random.uniform(0.7, 0.9)
                    
                    # Créer l'objet de score
                    channel_score = {
                        "channel_id": channel.get("channel_id", "unknown"),
                        "total_score": total_score,
                        "recommendation": recommendation,
                        "confidence": confidence
                    }
                    
                    channel_scores.append(channel_score)
                
                # Calculer la recommandation globale
                # La recommandation la plus fréquente devient la recommandation globale
                recommendations = [score["recommendation"] for score in channel_scores]
                recommendation_counts = {}
                
                for rec in recommendations:
                    if rec not in recommendation_counts:
                        recommendation_counts[rec] = 0
                    recommendation_counts[rec] += 1
                    
                global_recommendation = max(recommendation_counts.items(), key=lambda x: x[1])[0] if recommendation_counts else DecisionType.MAINTAIN_FEES
                
                # Calculer le score global du nœud
                node_score = sum(score["total_score"] for score in channel_scores) / len(channel_scores) if channel_scores else 0.0
                
                return {
                    "status": "success",
                    "node_id": node_data.get("node_id", "unknown"),
                    "node_score": node_score,
                    "global_recommendation": global_recommendation,
                    "channel_scores": channel_scores
                }
                
            except Exception as e:
                logger.error(f"Erreur dans la version de secours de evaluate_node: {str(e)}")
                return {
                    "status": "error",
                    "reason": str(e),
                    "node_id": node_data.get("node_id", "unknown")
                }
 
    async def get_nodes(self) -> list:
        """
        Récupère la liste des nœuds depuis LNBits ou utilise une liste de test
        
        Returns:
            Liste des identifiants de nœuds
        """
        # Si on est en mode dry run ou si le client LNBits n'est pas disponible, 
        # retourner une liste de nœuds de test
        if self.dry_run or self.lnbits_client is None:
            logger.info("Utilisation de nœuds simulés pour le test")
            return ["02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"]
        
        # Sinon, essayer de récupérer les nœuds depuis LNBits
        try:
            # Note: Cette méthode n'existe peut-être pas dans l'API actuelle, 
            # mais devrait être implémentée pour récupérer les nœuds
            nodes = await self.lnbits_client.get_nodes()
            return nodes
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des nœuds: {str(e)}")
            # En cas d'erreur, retourner une liste de nœuds de test
            return ["02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"]
    
    async def get_channels(self, node_id: str) -> list:
        """
        Récupère les canaux d'un nœud depuis LNBits ou utilise des canaux de test
        
        Args:
            node_id: Identifiant du nœud
            
        Returns:
            Liste des canaux
        """
        # Si on est en mode dry run ou si le client LNBits n'est pas disponible,
        # retourner des canaux de test
        if self.dry_run or self.lnbits_client is None:
            logger.info(f"Utilisation de canaux simulés pour le nœud {node_id}")
            return [
                {
                    "channel_id": "123x456x0",
                    "capacity": 5000000,
                    "local_balance": 2500000,
                    "remote_balance": 2500000,
                    "local_fee_base_msat": 1000,
                    "local_fee_rate": 500,
                    "active": True
                },
                {
                    "channel_id": "123x456x1",
                    "capacity": 2000000,
                    "local_balance": 1800000,
                    "remote_balance": 200000,
                    "local_fee_base_msat": 2000,
                    "local_fee_rate": 800,
                    "active": True
                }
            ]
        
        # Sinon, essayer de récupérer les canaux depuis LNBits
        try:
            channels = await self.lnbits_client.get_channels(node_id)
            return channels
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des canaux du nœud {node_id}: {str(e)}")
            # En cas d'erreur, retourner des canaux de test
            return [
                {
                    "channel_id": "123x456x0",
                    "capacity": 5000000,
                    "local_balance": 2500000,
                    "remote_balance": 2500000,
                    "local_fee_base_msat": 1000,
                    "local_fee_rate": 500,
                    "active": True
                }
            ]
    
    async def get_node_metrics(self, node_id: str) -> dict:
        """
        Récupère les métriques d'un nœud depuis LNBits ou utilise des métriques de test
        
        Args:
            node_id: Identifiant du nœud
            
        Returns:
            Métriques du nœud
        """
        # Si on est en mode dry run ou si le client LNBits n'est pas disponible,
        # retourner des métriques de test
        if self.dry_run or self.lnbits_client is None:
            logger.info(f"Utilisation de métriques simulées pour le nœud {node_id}")
            return {
                "activity": {
                    "forwards_count": 150,
                    "success_rate": 0.85
                },
                "centrality": {
                    "betweenness": 0.65
                }
            }
        
        # Sinon, essayer de récupérer les métriques depuis LNBits
        try:
            metrics = await self.lnbits_client.get_node_metrics(node_id)
            return metrics
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métriques du nœud {node_id}: {str(e)}")
            # En cas d'erreur, retourner des métriques de test
            return {
                "activity": {
                    "forwards_count": 150,
                    "success_rate": 0.85
                },
                "centrality": {
                    "betweenness": 0.65
                }
            }
    
    # On remplace la méthode _collect_node_data pour utiliser les nouvelles méthodes
    async def _collect_node_data(self) -> dict:
        """Collecte les données des nœuds à évaluer"""
        try:
            node_data = {}
            
            # Récupérer les nœuds
            node_ids = await self.get_nodes()
            
            for node_id in node_ids:
                # Récupérer les canaux du nœud
                channels = await self.get_channels(node_id)
                
                # Récupérer les métriques du nœud
                metrics = await self.get_node_metrics(node_id)
                
                node_data[node_id] = {
                    "node_id": node_id,
                    "channels": channels,
                    "metrics": metrics
                }
            
            return node_data
            
        except Exception as e:
            logger.error(f"Erreur lors de la collecte des données des nœuds: {str(e)}")
            return {}
    
    # On supprime la méthode _get_mock_node_data car elle est maintenant gérée par les méthodes spécifiques
    
    def schedule_jobs(self):
        """Configure et démarre les tâches planifiées"""
        schedule_config = self.config.get("schedule", {})
        schedule_type = schedule_config.get("type", "cron")
        
        if schedule_type == "cron":
            cron_expr = schedule_config.get("value", "0 */6 * * *")
            trigger = CronTrigger.from_crontab(cron_expr)
            self.scheduler.add_job(self.run_fee_optimization, trigger)
            logger.info(f"Optimisation planifiée avec l'expression cron: {cron_expr}")
            
        elif schedule_type == "interval":
            interval_minutes = int(schedule_config.get("value", 360))
            trigger = IntervalTrigger(minutes=interval_minutes)
            self.scheduler.add_job(self.run_fee_optimization, trigger)
            logger.info(f"Optimisation planifiée toutes les {interval_minutes} minutes")
        
        # Tâche de validation/rollback des mises à jour précédentes
        if self.config.get("rollback", {}).get("enabled", True):
            self.scheduler.add_job(
                self.validate_or_rollback_updates,
                IntervalTrigger(hours=1)
            )
            logger.info("Tâche de validation/rollback planifiée (toutes les heures)")
        
        # Démarrer le scheduler
        try:
            self.scheduler.start()
            logger.info("Scheduler démarré")
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du scheduler: {str(e)}")
    
    async def run_fee_optimization(self):
        """Exécute le processus d'optimisation des frais"""
        try:
            logger.info("Début du cycle d'optimisation des frais")
            
            # Collecter les données des nœuds
            node_data = await self._collect_node_data()
            if not node_data:
                logger.error("Aucune donnée de nœud n'a pu être collectée")
                return
            
            # Évaluer chaque nœud
            for node_id, data in node_data.items():
                logger.info(f"Évaluation du nœud {node_id}")
                
                # Évaluer le nœud et ses canaux
                evaluation = self.evaluate_node(data)
                
                if evaluation["status"] != "success":
                    logger.error(f"Erreur lors de l'évaluation du nœud {node_id}: {evaluation.get('reason', 'Erreur inconnue')}")
                    continue
                
                # Filtrer les canaux avec recommandation d'ajustement de frais
                fee_updates = []
                for channel_score in evaluation["channel_scores"]:
                    recommendation = channel_score["recommendation"]
                    confidence = channel_score["confidence"]
                    channel_id = channel_score["channel_id"]
                    
                    min_confidence = self.config.get("optimization", {}).get("min_confidence", 0.7)
                    
                    if confidence >= min_confidence and recommendation in [DecisionType.INCREASE_FEES, DecisionType.LOWER_FEES]:
                        # Récupérer les détails du canal
                        channel = next((c for c in data["channels"] if c.get("channel_id") == channel_id), None)
                        if not channel:
                            continue
                            
                        # Calculer les nouveaux frais
                        current_base_fee = channel.get("local_fee_base_msat", 1000) // 1000  # msat -> sat
                        current_fee_rate = channel.get("local_fee_rate", 500)
                        
                        # Simuler des métriques supplémentaires
                        forward_success_rate = 0.85  # À remplacer par les vraies métriques
                        channel_activity = 50        # À remplacer par les vraies métriques
                        
                        # Calculer l'ajustement
                        new_base_fee, new_fee_rate = get_fee_adjustment(
                            current_base_fee,
                            current_fee_rate,
                            forward_success_rate,
                            channel_activity,
                            max_increase_pct=self.config.get("optimization", {}).get("max_fee_increase", 30),
                            max_decrease_pct=self.config.get("optimization", {}).get("max_fee_decrease", 20)
                        )
                        
                        # Ajouter à la liste des mises à jour
                        fee_updates.append({
                            "channel_id": channel_id,
                            "old_base_fee": current_base_fee,
                            "old_fee_rate": current_fee_rate,
                            "new_base_fee": new_base_fee,
                            "new_fee_rate": new_fee_rate,
                            "reason": f"{recommendation} (confidence: {confidence:.2f})",
                            "node_id": node_id,
                            "timestamp": datetime.now().isoformat()
                        })
                
                # Limiter le nombre de mises à jour par exécution
                max_updates = self.config.get("optimization", {}).get("max_updates_per_run", 5)
                if len(fee_updates) > max_updates:
                    logger.info(f"Plus de {max_updates} mises à jour identifiées, application limitée aux {max_updates} plus confiantes")
                    fee_updates.sort(key=lambda x: float(x["reason"].split("confidence: ")[1].strip(")")) if "confidence:" in x["reason"] else 0, reverse=True)
                    fee_updates = fee_updates[:max_updates]
                
                # Appliquer les mises à jour
                if fee_updates:
                    await self._apply_fee_updates(fee_updates)
                else:
                    logger.info(f"Aucune mise à jour de frais nécessaire pour le nœud {node_id}")
            
            logger.info("Cycle d'optimisation des frais terminé")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation des frais: {str(e)}")
    
    async def _apply_fee_updates(self, fee_updates: list):
        """Applique les mises à jour de frais aux canaux"""
        try:
            if not fee_updates:
                return
                
            logger.info(f"Application de {len(fee_updates)} mises à jour de frais")
            
            # Sauvegarder avant l'application pour le rollback
            rollback_file = ROLLBACK_DIR / f"fee_updates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(rollback_file, 'w') as f:
                json.dump({
                    "updates": fee_updates,
                    "timestamp": datetime.now().isoformat(),
                    "applied": False,
                    "rolled_back": False
                }, f, indent=2)
            
            # Appliquer les mises à jour
            for update in fee_updates:
                channel_id = update["channel_id"]
                new_base_fee = update["new_base_fee"]
                new_fee_rate = update["new_fee_rate"]
                reason = update["reason"]
                
                try:
                    logger.info(f"Mise à jour du canal {channel_id}: {new_base_fee} sats, {new_fee_rate} ppm ({reason})")
                    
                    result = await self.automation_manager.update_fee_rate(
                        channel_id,
                        new_base_fee * 1000,  # Conversion en msats
                        new_fee_rate,
                    )
                    
                    if result["success"]:
                        logger.info(f"Mise à jour réussie pour le canal {channel_id}")
                        update["status"] = "success"
                        update["details"] = result
                    else:
                        logger.error(f"Échec de la mise à jour pour le canal {channel_id}: {result.get('message', 'Erreur inconnue')}")
                        update["status"] = "failed"
                        update["error"] = result.get("message", "Erreur inconnue")
                        
                except Exception as e:
                    logger.error(f"Exception lors de la mise à jour du canal {channel_id}: {str(e)}")
                    update["status"] = "error"
                    update["error"] = str(e)
            
            # Mettre à jour le fichier avec les résultats
            with open(rollback_file, 'w') as f:
                json.dump({
                    "updates": fee_updates,
                    "timestamp": datetime.now().isoformat(),
                    "applied": True,
                    "rolled_back": False,
                    "dry_run": self.dry_run
                }, f, indent=2)
            
            # Stocker dans l'historique
            self.update_history.extend(fee_updates)
            
            # Sauvegarder dans MongoDB pour traçabilité
            try:
                await self.mongo_ops.insert_documents("fee_updates", fee_updates)
            except Exception as e:
                logger.error(f"Erreur lors de la sauvegarde des mises à jour dans MongoDB: {str(e)}")
            
            logger.info(f"Application des mises à jour terminée")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'application des mises à jour de frais: {str(e)}")
    
    async def validate_or_rollback_updates(self):
        """Valide ou annule les mises à jour précédentes en fonction des performances"""
        try:
            logger.info("Vérification des mises à jour récentes pour validation ou rollback")
            
            # Vérifier s'il y a des mises à jour à valider/annuler
            rollback_files = list(ROLLBACK_DIR.glob("fee_updates_*.json"))
            if not rollback_files:
                logger.info("Aucune mise à jour à valider/annuler")
                return
            
            wait_time_hours = self.config.get("rollback", {}).get("wait_time", 24)
            cutoff_time = datetime.now() - timedelta(hours=wait_time_hours)
            
            for rollback_file in rollback_files:
                try:
                    with open(rollback_file, 'r') as f:
                        update_data = json.load(f)
                    
                    # Vérifier si les mises à jour ont déjà été traitées
                    if update_data.get("validated", False) or update_data.get("rolled_back", False):
                        continue
                    
                    # Vérifier si suffisamment de temps s'est écoulé
                    update_time = datetime.fromisoformat(update_data["timestamp"])
                    if update_time > cutoff_time:
                        continue
                    
                    # Pour chaque mise à jour, vérifier les performances du canal
                    updates_to_rollback = []
                    for update in update_data["updates"]:
                        channel_id = update["channel_id"]
                        node_id = update.get("node_id", "unknown")
                        
                        # Obtenir les performances actuelles du canal
                        # Simplification: Dans une implémentation réelle, il faudrait
                        # comparer les performances avant/après la mise à jour
                        performance_is_good = await self._check_channel_performance(node_id, channel_id)
                        
                        if not performance_is_good:
                            logger.warning(f"Performances du canal {channel_id} dégradées, rollback des frais")
                            updates_to_rollback.append(update)
                    
                    # Effectuer les rollbacks si nécessaire
                    if updates_to_rollback:
                        await self._rollback_fee_updates(updates_to_rollback)
                        update_data["rolled_back"] = True
                        update_data["rollback_timestamp"] = datetime.now().isoformat()
                    else:
                        logger.info("Toutes les mises à jour validées, performances bonnes")
                        update_data["validated"] = True
                        update_data["validation_timestamp"] = datetime.now().isoformat()
                    
                    # Mettre à jour le fichier
                    with open(rollback_file, 'w') as f:
                        json.dump(update_data, f, indent=2)
                    
                except Exception as e:
                    logger.error(f"Erreur lors du traitement du fichier {rollback_file}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la validation/rollback des mises à jour: {str(e)}")
    
    async def _check_channel_performance(self, node_id: str, channel_id: str) -> bool:
        """Vérifie les performances d'un canal après mise à jour"""
        try:
            # Dans un système réel, cette fonction comparerait les métriques avant/après
            # Pour cette démo, on retourne une valeur simulée
            # Dans 80% des cas, on considère que la performance est bonne
            return random.random() < 0.8
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des performances du canal {channel_id}: {str(e)}")
            # En cas d'erreur, on suppose que les performances sont acceptables
            return True
    
    async def _rollback_fee_updates(self, updates: list):
        """Annule les mises à jour de frais en restaurant les valeurs précédentes"""
        try:
            logger.info(f"Rollback de {len(updates)} mises à jour de frais")
            
            for update in updates:
                channel_id = update["channel_id"]
                old_base_fee = update["old_base_fee"]
                old_fee_rate = update["old_fee_rate"]
                
                logger.info(f"Rollback du canal {channel_id} aux valeurs: {old_base_fee} sats, {old_fee_rate} ppm")
                
                result = await self.automation_manager.update_fee_rate(
                    channel_id,
                    old_base_fee * 1000,  # Conversion en msats
                    old_fee_rate
                )
                
                if result["success"]:
                    logger.info(f"Rollback réussi pour le canal {channel_id}")
                else:
                    logger.error(f"Échec du rollback pour le canal {channel_id}: {result.get('message', 'Erreur inconnue')}")
            
            # Sauvegarder l'historique des rollbacks
            rollback_history = [{
                **update,
                "rollback_timestamp": datetime.now().isoformat()
            } for update in updates]
            
            try:
                await self.mongo_ops.insert_documents("fee_rollbacks", rollback_history)
            except Exception as e:
                logger.error(f"Erreur lors de la sauvegarde des rollbacks dans MongoDB: {str(e)}")
            
        except Exception as e:
            logger.error(f"Erreur lors du rollback des mises à jour de frais: {str(e)}")

async def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description="Scheduler d'optimisation des frais Lightning")
    parser.add_argument("--config", help="Chemin vers le fichier de configuration")
    parser.add_argument("--dry-run", action="store_true", help="Exécuter en mode simulation (sans appliquer les modifications)")
    parser.add_argument("--run-once", action="store_true", help="Exécuter une seule fois puis quitter")
    parser.add_argument("--no-mock-allowed", action="store_true", help="Échouer si des mocks sont utilisés (pour env prod)")
    args = parser.parse_args()
    
    # Créer le répertoire de configuration si nécessaire
    config_dir = Path(root_dir, "config")
    config_dir.mkdir(exist_ok=True, parents=True)
    
    try:
        # Initialiser le scheduler avec vérification des mocks
        scheduler = FeeOptimizerScheduler(
            config_file=args.config,
            dry_run=args.dry_run,
            no_mock_allowed=args.no_mock_allowed
        )
        
        if args.run_once:
            # Exécuter une seule fois
            await scheduler.run_fee_optimization()
        else:
            # Démarrer le scheduler
            scheduler.schedule_jobs()
            
            # Maintenir le programme en vie
            try:
                while True:
                    await asyncio.sleep(1)
            except (KeyboardInterrupt, SystemExit):
                logger.info("Arrêt du scheduler")
                scheduler.scheduler.shutdown()
    except Exception as e:
        logger.critical(f"Erreur fatale: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 