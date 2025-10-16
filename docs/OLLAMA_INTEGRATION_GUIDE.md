# Guide d'intégration Ollama/Llama dans MCP RAG

> Dernière mise à jour: 16 octobre 2025

## Vue d'ensemble

Ce guide décrit l'intégration complète d'Ollama avec Llama 3 70B pour le système RAG de MCP, remplaçant OpenAI tout en conservant Anthropic pour le chatbot conversationnel non-RAG.

## Architecture

```
┌─────────────────┐
│  FastAPI MCP    │
│   (app/main)    │
└────────┬────────┘
         │
         ├──────────────┐
         │              │
    ┌────▼────┐    ┌───▼────────┐
    │  RAG    │    │  Chatbot   │
    │ Ollama  │    │ Anthropic  │
    └────┬────┘    └────────────┘
         │
    ┌────▼──────────────┐
    │  Ollama Service   │
    │  (Docker)         │
    │                   │
    │  - Llama 3 70B    │
    │  - Llama 3 8B     │
    │  - nomic-embed    │
    └───────────────────┘
```

## Composants

### 1. Client Ollama (`src/clients/ollama_client.py`)

Client asynchrone HTTP pour communiquer avec Ollama:

- **Embeddings**: `embed()`, `embed_batch()`
- **Génération**: `generate()` (non-streaming), `generate_stream()` (streaming)
- **Retry**: Backoff exponentiel avec 3 tentatives max
- **Erreurs**: `OllamaClientError`, `OllamaTimeoutError`, `OllamaModelNotFoundError`
- **Healthcheck**: Vérifie la disponibilité via `/api/tags`

**Usage:**

```python
from src.clients.ollama_client import ollama_client

# Embedding
embedding = await ollama_client.embed("Lightning routing optimization")

# Génération
response = await ollama_client.generate(
    prompt="Explain Lightning fees",
    model="llama3:70b-instruct-2025-07-01",
    temperature=0.2,
    max_tokens=1536,
)

# Streaming
async for chunk in ollama_client.generate_stream(prompt="..."):
    print(chunk, end="", flush=True)
```

### 2. Adaptateur RAG (`src/rag_ollama_adapter.py`)

Adaptateur qui expose l'interface RAG standard:

- **Formatage prompts**: Conversion messages → format Llama 3 (`<|system|>`, `<|user|>`, `<|assistant|>`)
- **Génération**: Sync/async, streaming/non-streaming
- **Fallback**: Bascule automatique vers Llama 3 8B en cas d'erreur
- **Nettoyage**: Retire les tags Llama, normalise les espaces

**Interface:**

```python
class OllamaRAGAdapter:
    def get_embedding(text: str) -> List[float]
    async def get_embedding_async(text: str) -> List[float]
    
    def generate_completion(messages, temperature, max_tokens, lang) -> str
    async def generate_completion_async(...) -> str
    async def generate_completion_stream(...) -> AsyncIterator[str]
    
    def map_to_rag_response(answer, sources, confidence, degraded) -> Dict
```

### 3. Configuration (`config/rag_config.py`)

Variables d'environnement configurables:

```python
# Provider
LLM_PROVIDER = "ollama"  # "ollama" | "openai" | "anthropic"

# Ollama
OLLAMA_URL = "http://localhost:11434"
OLLAMA_NUM_PARALLEL = 1
OLLAMA_KEEP_ALIVE = "30m"

# Modèles
GEN_MODEL = "llama3:70b-instruct-2025-07-01"
GEN_MODEL_FALLBACK = "llama3:8b-instruct"
EMBED_MODEL = "nomic-embed-text"
EMBED_DIMENSION = 768
EMBED_VERSION = "2025-10-15"

# Génération
GEN_TEMPERATURE = 0.2
GEN_TOP_P = 0.9
GEN_MAX_TOKENS = 1536
GEN_NUM_CTX = 8192

# Retrieval
RAG_TOPK = 8
RAG_CONFIDENCE_THRESHOLD = 0.35

# Cache
CACHE_TTL_RETRIEVAL = 86400  # 24h
CACHE_TTL_ANSWER = 21600     # 6h
CACHE_TTL_EMBED = 604800     # 7j
```

### 4. Workflow RAG (`src/rag.py`)

Le workflow RAG a été mis à jour pour utiliser l'adaptateur Ollama:

```python
class RAGWorkflow:
    def __init__(self, redis_ops=None):
        self.ai_adapter = OllamaRAGAdapter(
            embed_model=rag_settings.EMBED_MODEL,
            gen_model=rag_settings.GEN_MODEL,
            dimension=rag_settings.EMBED_DIMENSION,
            num_ctx=rag_settings.GEN_NUM_CTX,
            fallback_model=rag_settings.GEN_MODEL_FALLBACK,
        )
```

## Déploiement

### Docker Compose

Le service Ollama est défini dans `docker-compose.production.yml`:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: mcp-ollama
    restart: always
    expose:
      - "11434"
    environment:
      - OLLAMA_HOST=0.0.0.0
      - OLLAMA_KEEP_ALIVE=30m
      - OLLAMA_NUM_PARALLEL=1
    volumes:
      - ollama_data:/root/.ollama
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

volumes:
  ollama_data:
    driver: local
    name: mcp_ollama_data
```

### Initialisation des modèles

**Script:** `scripts/ollama_init.sh`

```bash
# Démarrer les services
docker-compose -f docker-compose.production.yml up -d ollama

# Attendre que Ollama soit prêt
docker exec mcp-ollama curl -s http://localhost:11434/api/tags

# Initialiser les modèles
docker exec mcp-ollama /scripts/ollama_init.sh

# Vérifier les modèles installés
docker exec mcp-ollama ollama list
```

**Modèles requis:**

1. **llama3:70b-instruct-2025-07-01** (~40 GB) - Génération principale
2. **llama3:8b-instruct** (~4.7 GB) - Fallback
3. **nomic-embed-text** (~274 MB) - Embeddings

### Variables d'environnement

Ajouter dans `.env`:

```bash
# RAG Provider
LLM_PROVIDER=ollama

# Ollama
OLLAMA_URL=http://ollama:11434
GEN_MODEL=llama3:70b-instruct-2025-07-01
GEN_MODEL_FALLBACK=llama3:8b-instruct
EMBED_MODEL=nomic-embed-text
EMBED_DIMENSION=768
EMBED_VERSION=2025-10-15

# Génération
GEN_TEMPERATURE=0.2
GEN_MAX_TOKENS=1536
GEN_NUM_CTX=8192

# Retrieval
RAG_TOPK=8
RAG_CONFIDENCE_THRESHOLD=0.35
```

## Tests

### Tests unitaires

```bash
# Tests client Ollama
pytest tests/unit/test_ollama_client.py -v

# Tests adaptateur RAG
pytest tests/unit/test_rag_ollama_adapter.py -v

# Tous les tests
pytest tests/unit/ -v --cov=src
```

### Tests d'intégration

```bash
# Test end-to-end RAG avec Ollama
pytest tests/integration/test_rag_ollama_e2e.py -v

# Test avec vrai service Ollama
docker-compose up -d ollama
pytest tests/integration/ -v --ollama-url=http://localhost:11434
```

## Performance

### Latences attendues

| Opération | 70B (GPU) | 70B (CPU) | 8B (GPU) | 8B (CPU) |
|-----------|-----------|-----------|----------|----------|
| Embedding | ~100ms | ~200ms | N/A | N/A |
| Génération (1000 tokens) | ~2-5s | ~30-60s | ~0.5-1s | ~5-10s |
| Retrieval (top-8) | ~500ms | ~500ms | ~500ms | ~500ms |
| RAG complet | ~3-7s | ~40-80s | ~1-3s | ~10-20s |

### Recommandations matérielles

**Production (70B):**
- GPU: NVIDIA A100 80GB, H100, ou 2× RTX 4090 (48GB total)
- CPU: 64+ cœurs physiques, 128GB+ RAM
- Quantisation: Q4_K_M (40GB → ~25GB) ou Q5_K_M (~30GB)

**Développement (8B):**
- GPU: RTX 3090 (24GB), RTX 4070 Ti (12GB)
- CPU: 16+ cœurs, 32GB RAM
- Pas de quantisation nécessaire

### Optimisations

1. **Warmup au démarrage**: Charger le modèle en mémoire
2. **Keep-alive**: `OLLAMA_KEEP_ALIVE=30m` (évite reload)
3. **Concurrence**: `OLLAMA_NUM_PARALLEL=1` (70B) ou `2-4` (8B)
4. **Context size**: `num_ctx=8192` (balance mémoire/qualité)
5. **Quantisation**: Q4_K_M pour 70B, aucune pour 8B

## Monitoring

### Métriques Prometheus

```yaml
# Latences
rag_ollama_embed_latency_ms
rag_ollama_generate_latency_ms
rag_ollama_stream_latency_ms

# Erreurs
rag_ollama_errors_total{type="timeout|model_not_found|client_error"}
rag_ollama_fallback_total

# Utilisation
rag_ollama_requests_total{model="70b|8b"}
rag_ollama_tokens_generated_total
```

### Logs

```json
{
  "timestamp": "2025-10-16T10:30:45Z",
  "level": "INFO",
  "component": "ollama_client",
  "event": "generate",
  "model": "llama3:70b-instruct-2025-07-01",
  "prompt_tokens": 850,
  "generated_tokens": 320,
  "latency_ms": 4250,
  "temperature": 0.2
}
```

## Troubleshooting

### Problème: Ollama n'est pas accessible

**Symptôme:** `OllamaClientError: Connection refused`

**Solution:**
```bash
# Vérifier le service
docker ps | grep ollama
docker logs mcp-ollama

# Redémarrer
docker-compose restart ollama

# Tester la connexion
curl http://localhost:11434/api/tags
```

### Problème: Modèle non trouvé

**Symptôme:** `OllamaModelNotFoundError: model not found (404)`

**Solution:**
```bash
# Lister les modèles
docker exec mcp-ollama ollama list

# Pull le modèle manquant
docker exec mcp-ollama ollama pull llama3:70b-instruct-2025-07-01
```

### Problème: Out of Memory (OOM)

**Symptôme:** Ollama crash, kernel OOM killer

**Solution:**
1. **Quantiser le modèle**: Utiliser Q4_K_M au lieu de F16
2. **Réduire context**: `num_ctx=4096` au lieu de 8192
3. **Utiliser 8B**: Fallback permanent sur modèle 8B
4. **Augmenter swap**: Ajouter 64GB de swap (lent mais évite crash)

### Problème: Génération très lente

**Symptôme:** Timeout fréquents, latences > 60s

**Solution:**
1. **GPU**: Activer support NVIDIA si disponible
2. **Threads**: Augmenter `OLLAMA_NUM_THREADS` (cœurs physiques)
3. **Quantisation**: Utiliser Q4_K_M (trade-off qualité/vitesse)
4. **Modèle**: Basculer sur 8B pour les requêtes non-critiques

## Migration depuis OpenAI

### Checklist

- [ ] Installer Ollama et pull les modèles
- [ ] Mettre à jour `.env` avec `LLM_PROVIDER=ollama`
- [ ] Tester embeddings: `pytest tests/unit/test_ollama_client.py::test_embed_success`
- [ ] Tester génération: `pytest tests/unit/test_ollama_client.py::test_generate_success`
- [ ] Réindexer les documents avec nouveaux embeddings (si changement de dimension)
- [ ] Purger le cache Redis: `redis-cli FLUSHDB`
- [ ] Valider recall@5 sur jeu d'évaluation (≥ 0.8 requis)
- [ ] Déployer en shadow mode (logs uniquement, pas de changements)
- [ ] Monitorer latences p95 (≤ 2.5s retrieval, ≤ 10s génération)
- [ ] Activer en production progressivement (10% → 50% → 100%)

### Rollback

Si problèmes en production:

```bash
# 1. Repasser sur OpenAI
export LLM_PROVIDER=openai

# 2. Redémarrer l'API
docker-compose restart mcp-api

# 3. Vérifier les logs
docker logs -f mcp-api

# 4. Purger cache si nécessaire
docker exec -it mcp-redis redis-cli FLUSHDB
```

## Références

- [Spécification complète RAG Ollama](../docs/core/spec-rag-ollama.md)
- [Documentation Ollama](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Llama 3 Model Card](https://github.com/meta-llama/llama3)
- [nomic-embed-text](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5)

## Support

Pour toute question ou problème:

1. Consulter les logs: `docker logs mcp-api` et `docker logs mcp-ollama`
2. Vérifier les métriques Prometheus
3. Consulter la spec complète: `docs/core/spec-rag-ollama.md`
4. Ouvrir une issue avec les logs complets

---

**Version:** 1.0.0  
**Date:** 16 octobre 2025  
**Auteur:** MCP Team

