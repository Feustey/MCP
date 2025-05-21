import os
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv(override=True)  # charge uniquement le fichier .env principal

# Configuration MongoDB via variable d'environnement (utiliser MONGO_URL exclusivement)
MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    raise ValueError("La variable MONGO_URL n'est pas définie dans le fichier .env")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "mcp")

# Configuration Redis (local pour le cache)
REDIS_URL = "redis://localhost:6379/0"
RESPONSE_CACHE_TTL = 3600

# Configuration Ollama (local)
OLLAMA_BASE_URL = "http://umbrel.local:11434"
OLLAMA_MODEL = "mistral:instruct"

# Configuration OpenAI (production)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Configuration LND
LND_HOST = os.getenv("LND_HOST", "localhost:10009")
LND_MACAROON_PATH = os.getenv("LND_MACAROON_PATH", "")
LND_TLS_CERT_PATH = os.getenv("LND_TLS_CERT_PATH", "")
LND_REST_URL = os.getenv("LND_REST_URL", "https://127.0.0.1:8080")

# Configuration LNbits
USE_INTERNAL_LNBITS = os.getenv("USE_INTERNAL_LNBITS", "true").lower() == "true"
LNBITS_URL = os.getenv("LNBITS_URL", "http://127.0.0.1:8000/lnbits")  # URL externe ou interne prefixée
LNBITS_ADMIN_KEY = os.getenv("LNBITS_ADMIN_KEY", "")
LNBITS_INVOICE_KEY = os.getenv("LNBITS_INVOICE_KEY", "")
LNBITS_DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
LNBITS_DATABASE_URL = os.environ.get(
    "LNBITS_DATABASE_URL",
    f"sqlite:///{os.path.join(LNBITS_DATA_FOLDER, 'lnbits.sqlite')}"
)

# Pondérations scoring Lightning
HEURISTIC_WEIGHTS = {
    "centrality": 0.4,
    "capacity": 0.2,
    "reputation": 0.2,
    "fees": 0.1,
    "uptime": 0.1,
    # Ajouter d'autres heuristiques si besoin
}

# Pondération scoring RAG (vectoriel vs lexical)
VECTOR_WEIGHT = float(os.getenv("RAG_VECTOR_WEIGHT", "0.7"))

# Configuration Lightning Address (obligatoire)
LIGHTNING_ADDRESS = os.getenv("LIGHTNING_ADDRESS")
if not LIGHTNING_ADDRESS:
    raise ValueError("La variable LIGHTNING_ADDRESS n'est pas définie dans le fichier .env. Veuillez renseigner une adresse Lightning valide.") 