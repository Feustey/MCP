# 🚀 Guide de Correction Rapide - 20 Octobre 2025

> **Objectif**: Corriger les 3 problèmes identifiés dans le déploiement MCP  
> **Durée estimée**: 30 minutes  
> **Prérequis**: Accès SSH au serveur de production

---

## 📊 Problèmes Identifiés

1. ✅ **Architecture bloquante** → Déjà corrigé dans `app/main.py`
2. 🟡 **Authentification MongoDB** → Nécessite correction (ce guide)
3. 🟡 **Modèles Ollama manquants** → Nécessite téléchargement (si espace suffisant)

---

## 🔧 CORRECTION 1: Authentification MongoDB (10 min)

### Étape 1: Se connecter au serveur

```bash
ssh votre-utilisateur@147.79.101.32
cd /chemin/vers/MCP
```

### Étape 2: Vérifier l'espace disque

```bash
df -h
# Vérifier que /System/Volumes/Data a au moins 20% libre
```

### Étape 3: Exécuter le script de correction

```bash
# Copier le script depuis votre machine locale
scp scripts/fix_mongodb_auth.sh votre-utilisateur@147.79.101.32:/chemin/vers/MCP/scripts/

# Sur le serveur
chmod +x scripts/fix_mongodb_auth.sh
./scripts/fix_mongodb_auth.sh
```

### Étape 4: Redémarrer l'API

```bash
docker-compose -f docker-compose.hostinger.yml restart mcp-api
```

### Étape 5: Valider

```bash
# Attendre 30 secondes
sleep 30

# Tester l'endpoint RAG
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -H "X-API-Version: 2025-10-15" \
  -H "Authorization: Bearer test" \
  -d '{"query": "Test MongoDB", "node_pubkey": "test"}'
```

**Résultat attendu**: Réponse JSON sans erreur d'authentification MongoDB

---

## 🤖 CORRECTION 2: Modèles Ollama (10-60 min selon connexion)

### Option A: Téléchargement Complet (si espace suffisant)

```bash
# Vérifier l'espace disponible (nécessaire: ~10GB)
df -h

# Télécharger les modèles
docker exec mcp-ollama ollama pull llama3.1:8b        # ~4.7GB
docker exec mcp-ollama ollama pull phi3:medium       # ~4.0GB

# Vérifier
docker exec mcp-ollama ollama list
```

### Option B: Modèles Légers (si espace limité)

```bash
# Alternative avec modèles plus petits
docker exec mcp-ollama ollama pull llama3.2:3b       # ~2GB
docker exec mcp-ollama ollama pull phi3:mini         # ~2GB

# Mettre à jour la configuration
cat >> .env << 'EOF'
GEN_MODEL=llama3.2:3b
GEN_MODEL_FALLBACK=phi3:mini
EOF

# Redémarrer
docker-compose -f docker-compose.hostinger.yml restart mcp-api
```

### Option C: Mode Dégradé (espace critique)

```bash
# Utiliser uniquement nomic-embed-text (déjà disponible)
cat >> .env << 'EOF'
GEN_MODEL=nomic-embed-text
GEN_MODEL_FALLBACK=nomic-embed-text
ENABLE_RAG=false
EOF

# Redémarrer
docker-compose -f docker-compose.hostinger.yml restart mcp-api
```

---

## ✅ VALIDATION COMPLÈTE (5 min)

### Test 1: Health Check

```bash
curl http://localhost:8000/health
# Attendu: {"status": "healthy", ...}
```

### Test 2: Health Détaillé

```bash
curl http://localhost:8000/health/detailed
# Vérifier tous les services: mongodb, redis, ollama
```

### Test 3: API Root

```bash
curl http://localhost:8000/
# Attendu: Informations système
```

### Test 4: RAG (si activé)

```bash
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -H "X-API-Version: 2025-10-15" \
  -d '{
    "query": "Comment optimiser les frais Lightning?",
    "node_pubkey": "test"
  }'
# Attendu: Réponse avec recommendations
```

### Test 5: Métriques

```bash
curl http://localhost:8000/metrics/prometheus
# Attendu: Métriques au format Prometheus
```

---

## 📊 Checklist Post-Correction

- [ ] MongoDB: Authentification OK
- [ ] Ollama: Au moins 1 modèle disponible
- [ ] API: Répond sur `/health`
- [ ] RAG: Endpoint accessible (si activé)
- [ ] Logs: Aucune erreur critique

---

## 🔍 Troubleshooting

### MongoDB: "Authentication failed"

```bash
# Vérifier l'utilisateur
docker exec mcp-mongodb mongosh admin --eval "db.getUsers()"

# Recréer si nécessaire
docker exec mcp-mongodb mongosh admin --eval "
db.dropUser('mcpuser');
db.createUser({
  user: 'mcpuser',
  pwd: 'VOTRE_MOT_DE_PASSE',
  roles: [
    {role: 'readWrite', db: 'mcp_prod'},
    {role: 'dbAdmin', db: 'mcp_prod'}
  ]
})
"
```

### Ollama: "Model not found"

```bash
# Lister les modèles disponibles
docker exec mcp-ollama ollama list

# Télécharger un modèle manquant
docker exec mcp-ollama ollama pull llama3.1:8b

# Si connexion timeout, essayer plus tard ou utiliser VPN
```

### API: Ne démarre pas

```bash
# Voir les logs
docker-compose -f docker-compose.hostinger.yml logs -f mcp-api

# Redémarrer complètement
docker-compose -f docker-compose.hostinger.yml down
docker-compose -f docker-compose.hostinger.yml up -d

# Vérifier l'état
docker-compose -f docker-compose.hostinger.yml ps
```

---

## 📈 Métriques de Succès

| Critère | Objectif | Validation |
|---------|----------|------------|
| API Uptime | > 99% | `docker ps` → healthy |
| MongoDB Auth | OK | Pas d'erreur dans logs |
| Ollama Models | ≥ 1 | `ollama list` → au moins nomic-embed-text |
| RAG Endpoint | 200 OK | `curl /api/v1/rag/query` |
| Response Time | < 2s | Headers `X-Response-Time` |

---

## 📞 Support

### Logs Utiles

```bash
# API
docker-compose logs -f mcp-api | grep ERROR

# MongoDB
docker-compose logs -f mcp-mongodb | tail -50

# Ollama
docker-compose logs -f mcp-ollama | tail -50

# Tous
docker-compose logs --tail=100
```

### Commandes de Diagnostic

```bash
# État des services
docker-compose ps

# Utilisation ressources
docker stats --no-stream

# Espace disque
df -h
du -sh ./* | sort -hr | head -20

# Connexions réseau
docker exec mcp-api netstat -tuln
```

---

## 🎯 Prochaines Étapes

Après ces corrections:

1. **Monitoring**: Configurer Grafana (optionnel)
2. **Tests Charge**: Valider performance sous charge
3. **Shadow Mode**: Reprendre observation 21 jours
4. **LNBits**: Finaliser intégration réelle
5. **Production**: Tests avec nœud réel

---

**Date**: 20 octobre 2025  
**Version**: 1.0  
**Auteur**: MCP Team  
**Prochaine mise à jour**: Après validation complète

