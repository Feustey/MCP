# Scripts Ollama pour MCP

> Scripts de déploiement, validation et maintenance pour l'intégration Ollama/Llama 3

## 📋 Liste des scripts

### 1. `ollama_init.sh`
**Initialisation des modèles Ollama**

```bash
# Usage (depuis le conteneur Ollama)
docker exec mcp-ollama /scripts/ollama_init.sh
```

**Fonctions:**
- Pull des 3 modèles requis (70B, 8B, embeddings)
- Vérification des modèles existants (skip si déjà présent)
- Warmup du modèle principal
- Logs détaillés avec indicateurs de progression

**Modèles installés:**
- `llama3:70b-instruct-2025-07-01` (~40 GB)
- `llama3:8b-instruct` (~4.7 GB)
- `nomic-embed-text` (~274 MB)

**Durée:** 1-3h selon la connexion (première fois)

---

### 2. `validate_ollama_integration.sh`
**Validation complète de l'intégration**

```bash
# Usage
./scripts/validate_ollama_integration.sh
```

**Vérifications (8 étapes):**
1. ✅ Présence des fichiers source
2. ✅ Configuration .env
3. ✅ Docker Compose
4. ✅ Syntaxe Python
5. ✅ Tests unitaires (29 tests)
6. ✅ Service Ollama (si running)
7. ✅ Service MCP API (si running)
8. ✅ Documentation

**Sortie:** 
- ✅ Validation réussie (exit 0)
- ❌ Erreurs détectées (exit 1)

**Logs:** `/tmp/test_ollama_*.log`

---

### 3. `deploy_ollama.sh`
**Déploiement automatisé complet**

```bash
# Usage
./scripts/deploy_ollama.sh [dev|prod]

# Exemples
./scripts/deploy_ollama.sh dev   # Installe uniquement 8B (rapide)
./scripts/deploy_ollama.sh prod  # Installe 70B + 8B + embeddings (complet)
```

**Étapes (7 au total):**
1. Arrêt des services existants
2. Création/vérification des volumes
3. Démarrage Ollama
4. Attente healthcheck (max 60s)
5. Initialisation des modèles
6. Affichage des modèles installés
7. Démarrage API MCP + tests de validation

**Mode dev:**
- Installe uniquement Llama 3 8B + embeddings
- Rapide (~10 min)
- Idéal pour développement/tests

**Mode prod:**
- Installe Llama 3 70B + 8B + embeddings
- Long (~1-3h première fois)
- Prêt pour production

**Tests automatiques:**
- Import client Ollama
- Import adaptateur RAG
- Healthcheck Ollama depuis API

---

## 🚀 Workflow recommandé

### Première installation

```bash
# 1. Valider l'intégration (code, config, tests)
./scripts/validate_ollama_integration.sh

# 2. Déployer en mode dev (rapide)
./scripts/deploy_ollama.sh dev

# 3. Tester manuellement
docker exec mcp-api python3 -c "
from src.clients.ollama_client import ollama_client
import asyncio
emb = asyncio.run(ollama_client.embed('test'))
print(f'✅ OK: dimension={len(emb)}')
"

# 4. Si OK, upgrader vers prod (optionnel)
docker exec mcp-ollama ollama pull llama3:70b-instruct-2025-07-01
```

### Mise à jour

```bash
# 1. Valider les changements
./scripts/validate_ollama_integration.sh

# 2. Re-déployer
./scripts/deploy_ollama.sh prod

# 3. Vérifier les logs
docker logs -f mcp-api
```

### Troubleshooting

```bash
# Validation complète
./scripts/validate_ollama_integration.sh

# Vérifier les modèles
docker exec mcp-ollama ollama list

# Réinitialiser les modèles
docker exec mcp-ollama /scripts/ollama_init.sh

# Redémarrer les services
docker-compose restart ollama mcp-api
```

---

## 📊 Codes de sortie

| Script | Exit 0 | Exit 1 |
|--------|--------|--------|
| `validate_ollama_integration.sh` | Tous les tests OK | Erreur(s) détectée(s) |
| `deploy_ollama.sh` | Déploiement réussi | Erreur de déploiement |
| `ollama_init.sh` | Modèles installés | Erreur de pull |

---

## 🔧 Variables d'environnement

Ces scripts utilisent `.env` pour la configuration. Créer depuis `env.ollama.example`:

```bash
cp env.ollama.example .env
# Éditer .env avec vos valeurs
```

**Variables clés:**
- `LLM_PROVIDER=ollama`
- `OLLAMA_URL=http://ollama:11434`
- `GEN_MODEL=llama3:70b-instruct-2025-07-01`
- `GEN_MODEL_FALLBACK=llama3:8b-instruct`
- `EMBED_MODEL=nomic-embed-text`

---

## 📚 Ressources

- **[QUICKSTART_OLLAMA.md](../QUICKSTART_OLLAMA.md)** - Démarrage rapide
- **[OLLAMA_INTEGRATION_GUIDE.md](../docs/OLLAMA_INTEGRATION_GUIDE.md)** - Guide complet
- **[TODO_NEXT_OLLAMA.md](../TODO_NEXT_OLLAMA.md)** - Prochaines étapes

---

## ⚠️ Notes importantes

### Ressources requises

**Pour mode dev (8B):**
- Espace disque: ~10 GB
- RAM: 8-16 GB
- GPU: Optionnel (RTX 3060+)

**Pour mode prod (70B):**
- Espace disque: ~50 GB
- RAM: 64+ GB ou GPU avec 48+ GB VRAM
- GPU: Fortement recommandé (A100, H100, 2× RTX 4090)

### Temps d'installation

| Modèle | Taille | Temps (100 Mbps) | Temps (1 Gbps) |
|--------|--------|------------------|----------------|
| 70B | ~40 GB | ~1h | ~10 min |
| 8B | ~4.7 GB | ~6 min | ~1 min |
| Embeddings | ~274 MB | ~20s | ~2s |

### Première utilisation

Le **premier appel** après installation sera lent (chargement en mémoire):
- 70B: 30-60s
- 8B: 5-10s

Ensuite, rapide grâce à `OLLAMA_KEEP_ALIVE=30m`.

---

**Dernière mise à jour:** 16 octobre 2025

