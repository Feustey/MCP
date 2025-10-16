# 🚀 Quick Start: Ollama/Llama 3 dans MCP

> Démarrage rapide en 5 minutes

## 1. Configuration (`.env`)

```bash
LLM_PROVIDER=ollama
OLLAMA_URL=http://ollama:11434
GEN_MODEL=llama3:70b-instruct-2025-07-01
GEN_MODEL_FALLBACK=llama3:8b-instruct
EMBED_MODEL=nomic-embed-text
EMBED_DIMENSION=768
```

## 2. Démarrage

```bash
# Démarrer Ollama
docker-compose -f docker-compose.production.yml up -d ollama

# Attendre 30-60s puis initialiser les modèles
docker exec mcp-ollama /scripts/ollama_init.sh

# Démarrer l'API
docker-compose -f docker-compose.production.yml up -d mcp-api
```

## 3. Vérification

```bash
# Modèles installés
docker exec mcp-ollama ollama list

# Logs
docker logs mcp-ollama
docker logs mcp-api

# Test embedding
docker exec mcp-api python -c "
from src.clients.ollama_client import ollama_client
import asyncio
emb = asyncio.run(ollama_client.embed('test'))
print(f'✅ Embedding OK: dimension={len(emb)}')
"
```

## 4. Tests

```bash
# Tests unitaires
pytest tests/unit/test_ollama_client.py -v
pytest tests/unit/test_rag_ollama_adapter.py -v
```

## 📚 Documentation complète

- **[Guide d'intégration](docs/OLLAMA_INTEGRATION_GUIDE.md)** — Configuration, troubleshooting, performance
- **[Spécification technique](docs/core/spec-rag-ollama.md)** — Architecture, flux RAG, API
- **[Résumé complet](OLLAMA_INTEGRATION_COMPLETE.md)** — Vue d'ensemble de l'intégration

## 🆘 Problèmes courants

### Ollama ne démarre pas
```bash
docker logs mcp-ollama
docker restart mcp-ollama
```

### Modèle non trouvé (404)
```bash
docker exec mcp-ollama ollama pull llama3:70b-instruct-2025-07-01
docker exec mcp-ollama ollama pull llama3:8b-instruct
docker exec mcp-ollama ollama pull nomic-embed-text
```

### Out of Memory
- Utiliser quantisation Q4_K_M
- Réduire `num_ctx` à 4096
- Basculer sur modèle 8B seulement

---

**Statut:** ✅ Production Ready  
**Date:** 16 octobre 2025

