"""
Wrapper de configuration centralisée pour LNbits intégré.
Ce module injecte les variables d'environnement nécessaires pour LNbits à partir de la configuration MCP.
"""

import os
from pathlib import Path
import sqlite3
import logging
from typing import Optional

logger = logging.getLogger("lnbits_internal")

# Chemin de la base de données SQLite - Maintenant dans le répertoire data/lnbits_db plus robuste
LNBITS_DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "lnbits_db")
os.makedirs(LNBITS_DATA_FOLDER, exist_ok=True)

# Configuration en mode WAL pour plus de robustesse
LNBITS_DATABASE_URL = os.environ.get(
    "LNBITS_DATABASE_URL",
    f"sqlite:///{os.path.join(LNBITS_DATA_FOLDER, 'lnbits.sqlite')}"
)

# Plus de toggle - intégration complète uniquement
USE_INTERNAL_LNBITS = True 

# Paramètres de connexion à SQLite
SQLITE_PRAGMA = {
    "journal_mode": "WAL",       # Write-Ahead Logging pour performances et robustesse
    "synchronous": "NORMAL",     # Balance entre performance et durabilité
    "temp_store": "MEMORY",      # Utiliser la mémoire pour les tables temporaires
    "mmap_size": "268435456",    # 256MB mmap pour les performances
    "cache_size": "10000"        # 10MB cache
}

def setup_lnbits_environment():
    """
    Configure l'environnement pour LNbits interne avec des paramètres optimisés.
    Cette fonction doit être appelée avant d'initialiser l'application LNbits.
    """
    # Récupération des variables d'environnement MCP
    lnd_host = os.environ.get("LND_HOST", "localhost:10009")
    lnd_macaroon_path = os.environ.get("LND_MACAROON_PATH", "")
    lnd_tls_cert_path = os.environ.get("LND_TLS_CERT_PATH", "")
    lnd_rest_url = os.environ.get("LND_REST_URL", "https://127.0.0.1:8080")
    lnbits_admin_key = os.environ.get("LNBITS_ADMIN_KEY", "")
    lnbits_invoice_key = os.environ.get("LNBITS_INVOICE_KEY", "")

    # Configuration de LNbits
    os.environ["LNBITS_DATA_FOLDER"] = LNBITS_DATA_FOLDER
    os.environ["LNBITS_DATABASE_URL"] = LNBITS_DATABASE_URL
    
    # Définition de la connexion Lightning
    os.environ["LNBITS_BACKEND_WALLET_CLASS"] = "LndRestWallet"
    os.environ["LND_REST_ENDPOINT"] = lnd_rest_url
    os.environ["LND_REST_CERT"] = lnd_tls_cert_path
    os.environ["LND_REST_MACAROON"] = lnd_macaroon_path
    
    # Configurations de sécurité et performance
    os.environ["LNBITS_RATE_LIMIT_NO"] = "true"  # Désactive le rate limiting interne
    os.environ["LNBITS_RESERVE_FEE_MIN"] = "0"   # Contrôlé par notre propre logique
    os.environ["LNBITS_SQLITE_JOURNAL_MODE"] = SQLITE_PRAGMA["journal_mode"]
    os.environ["LNBITS_SQLITE_SYNCHRONOUS"] = SQLITE_PRAGMA["synchronous"]
    
    # Optimisations critiques: désactivation de fonctionnalités non essentielles
    os.environ["LNBITS_EXTENSIONS_DEFAULT_INSTALL"] = ""  # Aucune extension
    os.environ["LNBITS_ADMIN_UI"] = "false"              # Pas d'UI
    os.environ["LNBITS_HIDE_API"] = "false"              # Garder l'API uniquement
    os.environ["LNBITS_ALLOW_PERSIST_JWT"] = "false"     # Désactiver le JWT persistant
    os.environ["LNBITS_DISABLED_EXTENSIONS"] = "*"       # Désactiver toutes les extensions
    
    # Minimiser les tâches de fond et les schedulers
    os.environ["LNBITS_BACKGROUND_TASKS_ENABLED"] = "false"
    os.environ["LNBITS_EXPIRED_INVOICE_CLEANUP_INTERVAL"] = "0"  # Désactiver le nettoyage auto
    
    # Configurations des logs
    os.environ["LNBITS_LOG_LEVEL"] = "WARNING"  # Réduire la verbosité
    
    logger.info("Environnement LNbits configuré avec succès en mode haute performance.")

def init_lnbits_db(force_init: bool = False) -> bool:
    """
    Initialise la base de données LNbits en mode WAL pour plus de robustesse.
    Retourne True si l'initialisation est réussie, sinon False.
    
    Args:
        force_init: Si True, force la réinitialisation même si la DB existe
    """
    try:
        db_path = LNBITS_DATABASE_URL.replace("sqlite:///", "")
        
        # Vérifie si la base de données existe déjà
        db_exists = os.path.exists(db_path)
        
        if not db_exists or force_init:
            logger.info(f"Initialisation de la base de données LNbits: {db_path}")
            
            # Connexion à la base de données avec des paramètres robustes
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Appliquer les PRAGMAs pour la robustesse
            for pragma_name, pragma_value in SQLITE_PRAGMA.items():
                cursor.execute(f"PRAGMA {pragma_name} = {pragma_value}")
            
            # Création des tables de base (version simplifiée)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dbversions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL
                )
            ''')
            
            if not db_exists:
                # Insertion de la version initiale
                cursor.execute("INSERT INTO dbversions (version) VALUES (?)", (0,))
            
            conn.commit()
            
            # Test de robustesse de la DB
            try:
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()
                if integrity_result and integrity_result[0] == "ok":
                    logger.info("Vérification d'intégrité SQLite: OK")
                else:
                    logger.warning(f"Problème d'intégrité SQLite: {integrity_result}")
            except Exception as e:
                logger.warning(f"Impossible de vérifier l'intégrité: {e}")
                
            conn.close()
            
            logger.info("Base de données LNbits initialisée avec succès en mode WAL.")
        else:
            # Connexion pour vérifier l'état
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Vérifier si le mode WAL est activé
            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
            if journal_mode.upper() != "WAL":
                logger.warning(f"Base de données en mode {journal_mode}, conversion en WAL...")
                cursor.execute("PRAGMA journal_mode = WAL")
                
            # Appliquer les autres paramètres de performance
            for pragma_name, pragma_value in SQLITE_PRAGMA.items():
                if pragma_name != "journal_mode":  # Déjà appliqué
                    cursor.execute(f"PRAGMA {pragma_name} = {pragma_value}")
                
            conn.commit()
            conn.close()
            
            logger.info(f"Base de données LNbits existante, mode journal: {journal_mode}")
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de la base de données LNbits: {e}")
        return False

def disable_background_tasks():
    """
    Désactive explicitement les tâches de fond de LNbits qui pourraient être lancées malgré
    les configurations environnement.
    Cette fonction doit être appelée après avoir monté l'application LNbits.
    """
    try:
        # Import ici pour éviter les imports circulaires
        from lnbits_internal import app as lnbits_app
        
        # Supprimer les tâches de fond qui pourraient s'exécuter
        if hasattr(lnbits_app, "router") and hasattr(lnbits_app.router, "lifespan_context"):
            logger.info("Suppression des tâches de fond LNbits...")
            lnbits_app.router.lifespan_context = None
            
        # Désactivation des schedulers s'ils existent
        if hasattr(lnbits_app, "scheduled_tasks"):
            lnbits_app.scheduled_tasks = []
            
        logger.info("Tâches de fond LNbits désactivées avec succès")
        return True
    except Exception as e:
        logger.error(f"Impossible de désactiver les tâches de fond: {e}")
        return False

def get_admin_key() -> Optional[str]:
    """
    Retourne la clé admin configurée ou stockée dans la base de données.
    """
    return os.environ.get("LNBITS_ADMIN_KEY", None)

def get_invoice_key() -> Optional[str]:
    """
    Retourne la clé invoice configurée ou stockée dans la base de données.
    """
    return os.environ.get("LNBITS_INVOICE_KEY", None)

def get_db_stats() -> dict:
    """
    Retourne des statistiques sur la base de données SQLite.
    Utile pour monitoring et debugging.
    """
    stats = {}
    try:
        db_path = LNBITS_DATABASE_URL.replace("sqlite:///", "")
        if not os.path.exists(db_path):
            return {"error": "Base de données non trouvée"}
            
        db_size = os.path.getsize(db_path) / (1024 * 1024)  # taille en MB
        stats["db_size_mb"] = round(db_size, 2)
        
        # Vérification du journal WAL
        wal_path = db_path + "-wal"
        shm_path = db_path + "-shm"
        
        if os.path.exists(wal_path):
            wal_size = os.path.getsize(wal_path) / (1024 * 1024)  # taille en MB
            stats["wal_size_mb"] = round(wal_size, 2)
            
        if os.path.exists(shm_path):
            shm_size = os.path.getsize(shm_path) / (1024 * 1024)  # taille en MB
            stats["shm_size_mb"] = round(shm_size, 2)
            
        # Informations sur les tables
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Compte le nombre de tables
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
        stats["table_count"] = cursor.fetchone()[0]
        
        # Obtenir la version de la base de données
        cursor.execute("SELECT max(version) FROM dbversions")
        version = cursor.fetchone()[0]
        stats["db_version"] = version
        
        conn.close()
        
        return stats
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques de la DB: {e}")
        return {"error": str(e)} 