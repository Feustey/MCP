# 🚀 Guide de Déploiement RAG - Modèles Légers (llama3:8b-instruct)

> **Date:** 20 octobre 2025  
> **Version:** Production v1.0  
> **Modèle principal:** llama3:8b-instruct (~4.7 GB)  
> **Modèle fallback:** phi3:medium (~4.0 GB)  

---

## 📋 Vue d'ensemble

Ce guide décrit le déploiement complet du système RAG MCP avec des modèles Ollama légers, optimisés pour la production avec des ressources limitées.

### Changements par rapport à la version 70B

| Aspect | 70B (Ancien) | 8B (Nouveau) |
|--------|--------------|--------------|
| **Modèle principal** | llama3:70b-instruct | llama3:8b-instruct |
| **Modèle fallback** | qwen2.5:14b-instruct | phi3:medium |
| **RAM requise** | ~45 GB | ~6 GB |
| **Temps de réponse** | 5-15s | 2-5s |
| **Throughput** | ~3 tokens/s | ~12 tokens/s |
| **Précision** | ~95% | ~85-90% |
| **Coût infra/mois** | $200-400 | $50-100 |

---

## ✅ Pré-requis

### Système

- **RAM:** Minimum 8 GB (16 GB recommandé)
- **Stockage:** 15 GB libres minimum
- **CPU:** 4 cores minimum
- **OS:** Linux (Ubuntu 20.04+) ou macOS

### Logiciels

- Docker 24.0+
- Docker Compose 2.0+
- Git
- Curl

### Ports requis

- `8000`: API MCP
- `11434`: Ollama
- `27017`: MongoDB (interne Docker)
- `6379`: Redis (interne Docker)
- `3000`: Grafana (optionnel)
- `9090`: Prometheus (optionnel)

---

## 📥 Étape 1 : Récupération du Code

```bash
# Si pas encore cloné
cd /Users/stephanecourant/Documents/DAZ/MCP/MCP

# Vérifier que les fichiers sont à jour
git status
```

---

## ⚙️ Étape 2 : Configuration

### 2.1 Créer le fichier .env

```bash
# Copier le template
cp env.hostinger.example .env

# Éditer avec vos valeurs
nano .env
```

### 2.2 Valeurs critiques à configurer

```bash
# SECURITY - GÉNÉRER AVEC:
# python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# python3 -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"
SECRET_KEY=CHANGEZ_CETTE_CLE_SECRETE_32_CARACTERES_MINIMUM
ENCRYPTION_KEY=CHANGEZ_CETTE_CLE_CHIFFREMENT_BASE64

# MONGODB (Docker Internal)
MONGODB_PASSWORD=CHANGEZ_CE_MOT_DE_PASSE_MONGODB_123!

# REDIS (Docker Internal)
REDIS_PASSWORD=CHANGEZ_CE_MOT_DE_PASSE_REDIS_123!

# LNBITS
LNBITS_URL=https://your-lnbits-instance.com
LNBITS_ADMIN_KEY=your_lnbits_admin_key_here
LNBITS_INVOICE_KEY=your_lnbits_invoice_key_here

# RAG / OLLAMA - VÉRIFIER CES VALEURS
GEN_MODEL=llama3:8b-instruct
GEN_MODEL_FALLBACK=phi3:medium
EMBED_MODEL=nomic-embed-text
```

### 2.3 Vérifier la configuration

```bash
# Vérifier que GEN_MODEL est bien configuré
grep "GEN_MODEL" .env

# Devrait afficher:
# GEN_MODEL=llama3:8b-instruct
# GEN_MODEL_FALLBACK=phi3:medium
```

---

## 🚀 Étape 3 : Déploiement Automatique

### 3.1 Lancer le déploiement complet

```bash
# Rendre le script exécutable (si pas déjà fait)
chmod +x deploy_rag_production.sh

# Lancer le déploiement
./deploy_rag_production.sh
```

Le script va automatiquement :
1. ✅ Vérifier la présence du fichier `.env`
2. ✅ Builder et démarrer les containers Docker
3. ✅ Vérifier la santé des services (MongoDB, Redis, Ollama, API)
4. ✅ Télécharger les modèles Ollama (llama3:8b-instruct, phi3:medium, nomic-embed-text)
5. ✅ Tester le workflow RAG

**Durée estimée:** 15-30 minutes (selon la connexion internet)

---

## 🔧 Étape 4 : Déploiement Manuel (Alternative)

Si vous préférez un contrôle manuel :

### 4.1 Démarrer les services Docker

```bash
docker-compose -f docker-compose.hostinger.yml up -d --build
```

### 4.2 Attendre le démarrage (30-60s)

```bash
# Vérifier les logs
docker-compose -f docker-compose.hostinger.yml logs -f
```

### 4.3 Récupérer les modèles Ollama

```bash
# Rendre le script exécutable
chmod +x scripts/pull_lightweight_models.sh

# Lancer le téléchargement
./scripts/pull_lightweight_models.sh
```

### 4.4 Vérifier les modèles

```bash
docker exec mcp-ollama ollama list

# Devrait afficher:
# NAME                    ID              SIZE
# llama3:8b-instruct      abc123...       4.7 GB
# phi3:medium             def456...       4.0 GB
# nomic-embed-text        ghi789...       274 MB
```

---

## ✅ Étape 5 : Validation

### 5.1 Vérifier les services

```bash
# Tous les containers doivent être UP
docker-compose -f docker-compose.hostinger.yml ps

# Vérifier l'API
curl http://localhost:8000/health

# Devrait retourner: {"status":"healthy"}
```

### 5.2 Tester le RAG

```bash
# Test simple via API
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Quelles sont les meilleures pratiques pour optimiser les frais Lightning?",
    "node_pubkey": "feustey"
  }'
```

### 5.3 Lancer le workflow RAG complet

```bash
./run_rag_workflow_prod.sh
```

### 5.4 Vérifier les logs

```bash
# Logs API
docker-compose -f docker-compose.hostinger.yml logs -f mcp-api

# Logs Ollama
docker-compose -f docker-compose.hostinger.yml logs -f ollama

# Logs tous services
docker-compose -f docker-compose.hostinger.yml logs --tail=100
```

---

## 📊 Étape 6 : Monitoring

### 6.1 Accès aux interfaces

- **API MCP:** http://localhost:8000
- **Documentation API:** http://localhost:8000/docs
- **Grafana:** http://localhost:3000 (admin/admin)
- **Prometheus:** http://localhost:9090

### 6.2 Métriques à surveiller

```bash
# Utilisation RAM du container Ollama
docker stats mcp-ollama

# Vérifier les performances
docker exec mcp-ollama curl http://localhost:11434/api/tags
```

---

## 🔍 Dépannage

### Problème 1 : Modèle ne se télécharge pas

```bash
# Entrer dans le container
docker exec -it mcp-ollama bash

# Pull manuel
ollama pull llama3:8b-instruct
ollama pull phi3:medium
ollama pull nomic-embed-text

# Sortir
exit
```

### Problème 2 : API ne démarre pas

```bash
# Vérifier les logs
docker-compose -f docker-compose.hostinger.yml logs mcp-api

# Redémarrer le service
docker-compose -f docker-compose.hostinger.yml restart mcp-api
```

### Problème 3 : MongoDB connection failed

```bash
# Vérifier MongoDB
docker-compose -f docker-compose.hostinger.yml exec mongodb mongosh --eval "db.runCommand('ping')"

# Vérifier le mot de passe dans .env
grep MONGODB_PASSWORD .env
```

### Problème 4 : Out of Memory

```bash
# Réduire le contexte dans config/rag_config.py
# GEN_NUM_CTX: int = 4096  # au lieu de 8192

# Réduire la concurrence
# OLLAMA_NUM_PARALLEL: int = 1  # au lieu de 3
```

### Problème 5 : Réponses de mauvaise qualité

```bash
# 1. Essayer le fallback
# Dans .env, inverser:
# GEN_MODEL=phi3:medium
# GEN_MODEL_FALLBACK=llama3:8b-instruct

# 2. Ou passer à un modèle plus gros:
# GEN_MODEL=qwen2.5:14b-instruct

# 3. Ajuster la température dans config/rag_config.py
# GEN_TEMPERATURE: float = 0.2  # Plus conservateur
```

---

## 📈 Optimisations Post-Déploiement

### Optimisation 1 : Ajuster les paramètres RAG

Éditer `config/rag_config.py` :

```python
# Pour des réponses plus rapides mais moins précises
RAG_TOPK: int = 3  # au lieu de 5
RAG_RERANK_TOP: int = 1  # au lieu de 2

# Pour des réponses plus précises mais plus lentes
RAG_TOPK: int = 8
RAG_RERANK_TOP: int = 3
```

### Optimisation 2 : Caching agressif

```python
# Dans config/rag_config.py
CACHE_TTL_RETRIEVAL: int = 172800  # 48h au lieu de 24h
CACHE_TTL_ANSWER: int = 43200  # 12h au lieu de 6h
```

### Optimisation 3 : Warmup automatique

Ajouter au cron :

```bash
# Warmup toutes les heures pour maintenir le modèle en mémoire
0 * * * * docker exec mcp-ollama ollama run llama3:8b-instruct "ping" > /dev/null 2>&1
```

---

## 🔄 Workflow RAG Automatisé

### Configuration Cron pour exécution quotidienne

```bash
# Éditer crontab
crontab -e

# Ajouter (exécution tous les jours à 3h du matin)
0 3 * * * cd /Users/stephanecourant/Documents/DAZ/MCP/MCP && ./run_rag_workflow_prod.sh >> logs/cron_rag.log 2>&1
```

### Exécution manuelle

```bash
# Workflow complet
./run_rag_workflow_prod.sh

# Workflow simplifié
./run_rag_workflow.sh
```

---

## 🛑 Arrêt et Maintenance

### Arrêt propre

```bash
# Arrêter tous les services
docker-compose -f docker-compose.hostinger.yml down

# Arrêter ET supprimer les volumes (⚠️ perte de données)
docker-compose -f docker-compose.hostinger.yml down -v
```

### Redémarrage

```bash
# Redémarrer tous les services
docker-compose -f docker-compose.hostinger.yml restart

# Redémarrer un service spécifique
docker-compose -f docker-compose.hostinger.yml restart mcp-api
```

### Mise à jour

```bash
# Pull la dernière version
git pull origin main

# Rebuild et redémarrer
docker-compose -f docker-compose.hostinger.yml up -d --build
```

### Sauvegarde

```bash
# Sauvegarder MongoDB
docker-compose -f docker-compose.hostinger.yml exec mongodb mongodump --out /data/backup

# Sauvegarder les modèles Ollama
docker exec mcp-ollama tar -czf /tmp/ollama_models.tar.gz /root/.ollama
docker cp mcp-ollama:/tmp/ollama_models.tar.gz ./backup/
```

---

## 📝 Fichiers Modifiés

### Configuration

- ✅ `config/rag_config.py` - Paramètres RAG optimisés pour 8B
- ✅ `env.hostinger.example` - Template avec modèles légers
- ✅ `env.production.example` - Template production avec modèles légers
- ✅ `docker-compose.hostinger.yml` - Configuration Docker avec modèles légers
- ✅ `docker-compose.hostinger-production.yml` - Configuration production avec modèles légers

### Scripts

- ✅ `scripts/pull_lightweight_models.sh` - Téléchargement des modèles légers
- ✅ `deploy_rag_production.sh` - Déploiement automatique complet

---

## 🎯 Métriques de Succès

### Performance attendue

```yaml
Réponse API:
  - P50: < 3s
  - P95: < 5s
  - P99: < 8s

Ressources:
  - RAM Ollama: ~6 GB
  - RAM API: ~512 MB
  - RAM MongoDB: ~256 MB
  - RAM Redis: ~128 MB
  - CPU moyen: < 30%

Qualité:
  - Précision réponses: 85-90%
  - Taux d'erreur: < 5%
  - Cache hit rate: > 70%
```

### Tests de validation

```bash
# 1. Test de latence
time curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Test", "node_pubkey": "feustey"}'

# 2. Test de charge (optionnel, nécessite apache-bench)
ab -n 100 -c 5 http://localhost:8000/health

# 3. Test workflow complet
time ./run_rag_workflow_prod.sh
```

---

## 📞 Support

### En cas de problème

1. **Consulter les logs:**
   ```bash
   docker-compose -f docker-compose.hostinger.yml logs --tail=100
   ```

2. **Vérifier la configuration:**
   ```bash
   cat .env | grep -E "(GEN_MODEL|OLLAMA|MONGODB|REDIS)"
   ```

3. **Restart complet:**
   ```bash
   docker-compose -f docker-compose.hostinger.yml down
   docker-compose -f docker-compose.hostinger.yml up -d
   ```

### Ressources

- [Documentation Ollama](https://ollama.com/docs)
- [Docker Compose Docs](https://docs.docker.com/compose/)
- [Roadmap MCP v1.0](_SPECS/Roadmap-Production-v1.0.md)
- [Backbone Technique](docs/backbone-technique-MVP.md)

---

## ✅ Checklist Finale

Avant de considérer le déploiement terminé :

```
☑ .env configuré avec valeurs réelles
☑ Tous les containers UP et healthy
☑ Les 3 modèles Ollama téléchargés
☑ API répond sur /health
☑ Test RAG query réussi
☑ Workflow RAG exécuté sans erreur
☑ Monitoring accessible (Grafana, Prometheus)
☑ Logs vérifiés, pas d'erreur critique
☑ Backup configuré (optionnel)
☑ Cron configuré pour workflow automatique (optionnel)
```

---

**🎉 Déploiement RAG avec modèles légers terminé !**

> Pour toute question, consulter la roadmap production complète dans `_SPECS/Roadmap-Production-v1.0.md`

