# 🚀 Commandes Ollama - Aide-mémoire

## Configuration initiale

```bash
# 1. Créer .env
cp env.ollama.example .env
nano .env  # Éditer les valeurs

# 2. Valider
./scripts/validate_ollama_integration.sh
```

## Déploiement

```bash
# Dev (rapide, 8B seulement)
./scripts/deploy_ollama.sh dev

# Prod (complet, 70B + 8B)
./scripts/deploy_ollama.sh prod

# Manuel
docker-compose -f docker-compose.production.yml up -d ollama
docker exec mcp-ollama /scripts/ollama_init.sh
docker-compose -f docker-compose.production.yml up -d mcp-api
```

## Tests rapides

```bash
# Healthcheck
docker exec mcp-api python3 -c "
from src.clients.ollama_client import ollama_client
import asyncio
print('✅ OK' if asyncio.run(ollama_client.healthcheck()) else '❌ FAIL')
"

# Embedding
docker exec mcp-api python3 -c "
from src.clients.ollama_client import ollama_client
import asyncio
emb = asyncio.run(ollama_client.embed('test'))
print(f'✅ Dimension: {len(emb)}')
"

# Génération
docker exec mcp-api python3 -c "
from src.clients.ollama_client import ollama_client
import asyncio
resp = asyncio.run(ollama_client.generate(
    prompt='Dis: OK',
    model='llama3:8b-instruct',
    max_tokens=5
))
print(f'✅ Réponse: {resp}')
"
```

## Monitoring

```bash
# Services
docker ps --filter name=mcp

# Logs
docker logs -f mcp-ollama
docker logs -f mcp-api

# Modèles
docker exec mcp-ollama ollama list

# Stats
docker stats mcp-ollama mcp-api
```

## Maintenance

```bash
# Redémarrer
docker-compose restart ollama mcp-api

# Arrêter
docker-compose down ollama mcp-api

# Pull modèle
docker exec mcp-ollama ollama pull llama3:8b-instruct

# Purger cache
docker exec <redis> redis-cli FLUSHDB
```

## Tests unitaires

```bash
# Tous les tests
pytest tests/unit/test_ollama_*.py -v

# Client seulement
pytest tests/unit/test_ollama_client.py -v

# Adaptateur seulement
pytest tests/unit/test_rag_ollama_adapter.py -v
```

## Troubleshooting

```bash
# Logs d'erreurs
docker logs mcp-api 2>&1 | grep -i error
docker logs mcp-ollama 2>&1 | grep -i error

# Shell dans conteneur
docker exec -it mcp-api bash
docker exec -it mcp-ollama bash

# Vérifier fichiers
docker exec mcp-api ls -la src/clients/ollama_client.py
docker exec mcp-api ls -la src/rag_ollama_adapter.py

# Syntaxe Python
docker exec mcp-api python3 -m py_compile src/clients/ollama_client.py
```

## Variables .env clés

```bash
LLM_PROVIDER=ollama
OLLAMA_URL=http://ollama:11434
GEN_MODEL=llama3:70b-instruct-2025-07-01
GEN_MODEL_FALLBACK=llama3:8b-instruct
EMBED_MODEL=nomic-embed-text
EMBED_DIMENSION=768
```

## Documentation

- **START_HERE_OLLAMA.md** - Instructions complètes
- **QUICKSTART_OLLAMA.md** - Démarrage 5min
- **docs/OLLAMA_INTEGRATION_GUIDE.md** - Guide complet
- **TODO_NEXT_OLLAMA.md** - Prochaines étapes

---

**Date:** 16 octobre 2025

