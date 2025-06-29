import multiprocessing
import os

# Configuration du serveur
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
keepalive = 120
timeout = 120
graceful_timeout = 60

# Configuration des logs
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Configuration des workers
max_requests = 1000
max_requests_jitter = 50
worker_tmp_dir = "/dev/shm"
worker_connections = 1000

# Configuration de la sécurité
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Configuration des hooks
def on_starting(server):
    """Hook exécuté au démarrage du serveur."""
    print("🚀 Démarrage du serveur Gunicorn...")

def on_reload(server):
    """Hook exécuté lors du rechargement du serveur."""
    print("♻️ Rechargement du serveur Gunicorn...")

def on_exit(server):
    """Hook exécuté à l'arrêt du serveur."""
    print("🛑 Arrêt du serveur Gunicorn...")

def worker_int(worker):
    """Hook exécuté lorsqu'un worker est interrompu."""
    worker.log.info("⚠️ Worker interrompu")

def worker_abort(worker):
    """Hook exécuté lorsqu'un worker est abandonné."""
    worker.log.info("❌ Worker abandonné")

def worker_exit(server, worker):
    """Hook exécuté lorsqu'un worker se termine."""
    server.log.info(f"👋 Worker {worker.pid} terminé") 