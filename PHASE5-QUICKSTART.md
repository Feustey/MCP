# 🚀 Phase 5 - Quick Start Guide

> Démarrage rapide en production - Mode Shadow activé
> ⏱️ Temps estimé: 15 minutes

## ✅ Checklist Pré-déploiement

- [ ] Docker & Docker Compose installés
- [ ] Variables d'environnement configurées dans `.env`
- [ ] MongoDB Atlas accessible
- [ ] Redis Upstash configuré
- [ ] Certificat SSL (optionnel en local)
- [ ] LNbits credentials (pour Lightning)

## 🎯 Démarrage Rapide (3 étapes)

### 1. Configuration (5 min)

```bash
# Clone ou pull latest
git pull origin main

# Copie et édite .env
cp .env.example .env
nano .env

# Variables OBLIGATOIRES:
# - MONGO_URL
# - JWT_SECRET
# - ENVIRONMENT=production
# - DRY_RUN=true  ← IMPORTANT
```

### 2. Tests Locaux (5 min)

```bash
# Crée venv si nécessaire
python3 -m venv .venv
source .venv/bin/activate

# Install deps
pip install -r app/requirements.txt python-dotenv

# Test pipeline
python test_production_pipeline.py
# ✅ Attend: 80-100% pass rate

# Test monitoring (5 secondes)
python monitor_production.py --duration 5 --interval 2
```

### 3. Déploiement Production (5 min)

```bash
# Build
docker-compose -f docker-compose.production.yml build

# Start
docker-compose -f docker-compose.production.yml up -d

# Check logs
docker-compose logs -f mcp-api

# Vérifie santé
curl http://localhost:8000/api/v1/health
# ou
curl https://api.dazno.de/api/v1/health
```

## 📊 Monitoring Post-Déploiement

### Monitoring Continu

```bash
# Terminal 1: Logs API
docker-compose logs -f mcp-api

# Terminal 2: Monitoring actif
source .venv/bin/activate
python monitor_production.py
```

Le monitoring affiche:
```
=== Check #1 ===
Health: ✅ (450ms)
Rollback: ✅ (0 recent backups)
Optimizer: ✅ No errors

📊 SUMMARY
Uptime: 100%
Avg response: 450ms
```

### Rapports Générés

```bash
# Rapport du jour
cat monitoring_data/monitoring_$(date +%Y%m%d).json | jq

# Résultats tests
ls -lh data/test_results/
```

## 🧪 Test du Fee Optimizer (Shadow Mode)

```bash
# Crée un script test
cat > test_optimizer.py << 'EOF'
import asyncio
from src.optimizers.core_fee_optimizer import CoreFeeOptimizer

async def test():
    optimizer = CoreFeeOptimizer(
        node_pubkey="02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
        dry_run=True,  # Shadow mode
        max_changes_per_run=3
    )

    print("🔍 Analyzing channels in shadow mode...")
    results = await optimizer.run_pipeline()

    print(f"\n📊 Results:")
    print(f"  Channels analyzed: {results.get('analyzed', 0)}")
    print(f"  Recommendations: {len(results.get('recommendations', []))}")
    print(f"  Would optimize: {results.get('would_optimize', 0)}")

    return results

asyncio.run(test())
EOF

# Execute
python test_optimizer.py
```

## ⚠️ Mode Shadow → Production

**NE PAS désactiver DRY_RUN immédiatement!**

### Timeline Recommandée

| Semaine | Mode | Actions |
|---------|------|---------|
| 1-2 | Shadow (DRY_RUN=true) | Observer les recommandations |
| 3 | Test (1 canal) | Activer sur 1 canal test uniquement |
| 4+ | Production limitée | MAX_CHANGES_PER_RUN=5 max |

### Activation Progressive

```bash
# Semaine 1-2: OBSERVATION UNIQUEMENT
DRY_RUN=true
MAX_CHANGES_PER_RUN=0

# Semaine 3: TEST LIMITÉ (après validation)
DRY_RUN=false
MAX_CHANGES_PER_RUN=1

# Semaine 4+: PRODUCTION (si résultats positifs)
DRY_RUN=false
MAX_CHANGES_PER_RUN=5
```

## 📈 Métriques à Surveiller

### Jour 1
- ✅ API répond (health check)
- ✅ Pas d'erreurs dans les logs
- ✅ Monitoring actif

### Semaine 1
- 📊 Uptime > 99%
- 📊 Response time < 1000ms
- 📊 Recommandations cohérentes

### Semaine 2-3
- 📈 Analyse des patterns
- 📈 Validation des heuristiques
- 📈 Préparation activation

## 🚨 Alertes & Actions

### Alertes Critiques

**API Down**
```bash
docker-compose restart mcp-api
docker-compose logs --tail=50 mcp-api
```

**Optimizer Errors**
```bash
tail -50 logs/fee_optimizer.log
# Vérifie les credentials LNbits
```

**Performance Dégradée**
```bash
# Vérifie les ressources
docker stats mcp-api-prod
```

## 🔧 Commandes Utiles

```bash
# Status services
docker-compose ps

# Restart API
docker-compose restart mcp-api

# View logs (dernières 100 lignes)
docker-compose logs --tail=100 mcp-api

# Exec dans le container
docker-compose exec mcp-api bash

# Stop tout
docker-compose down

# Start avec rebuild
docker-compose up -d --build

# Cleanup
docker system prune -a
```

## 📱 Alertes Telegram (Optionnel)

```bash
# Configure dans .env
TELEGRAM_BOT_TOKEN=<ton_bot_token>
TELEGRAM_CHAT_ID=<ton_chat_id>

# Test manuel
curl -X POST \
  https://api.telegram.org/bot<TOKEN>/sendMessage \
  -d chat_id=<CHAT_ID> \
  -d text="MCP déployé avec succès ✅"
```

## 🎓 Bonnes Pratiques

1. **Toujours commencer en Shadow Mode**
   - Minimum 7 jours d'observation
   - Valide les recommandations
   - Compare avec ton analyse manuelle

2. **Surveiller activement**
   - Check daily les métriques
   - Lis les logs optimizer
   - Note les patterns

3. **Backups automatiques**
   - Le système crée des backups avant chaque action
   - Vérifie `data/rollbacks/`
   - Teste la restauration

4. **Progressive rollout**
   - 1 canal → 3 canaux → 5 canaux max
   - Attends 48h entre chaque phase
   - Mesure l'impact réel

## 🆘 Support Rapide

### Problème: API ne démarre pas
```bash
# Check config
docker-compose config

# Check env vars
docker-compose config | grep -i mongo

# Force rebuild
docker-compose down
docker-compose up --build
```

### Problème: Tests échouent
```bash
# Check Python version
python --version  # Doit être 3.9+

# Reinstall deps
pip install -r app/requirements.txt

# Check .env
cat .env | grep -E "MONGO|JWT|ENVIRONMENT"
```

### Problème: Monitoring ne marche pas
```bash
# Vérifie l'API URL
echo $API_BASE_URL

# Test manuel
curl -v http://localhost:8000/api/v1/health

# Check les logs
tail -f logs/monitoring.log
```

## 📚 Documentation Complète

- [Phase 5 Deployment Guide](docs/phase5-production-deployment.md)
- [Architecture](docs/core/architecture.md)
- [API Endpoints](docs/api/endpoints-complete.md)
- [Troubleshooting](docs/deploy-hostinger-guide.md)

## ✅ Validation Déploiement

Ton déploiement est réussi si:

- ✅ `docker-compose ps` montre tous les services "Up"
- ✅ `curl localhost:8000/api/v1/health` retourne 200
- ✅ `test_production_pipeline.py` passe à 80%+
- ✅ `monitor_production.py` affiche "Health: ✅"
- ✅ Aucune erreur dans `logs/fee_optimizer.log`

## 🎉 Félicitations!

Tu es maintenant en **Phase 5 - Production (Shadow Mode)** ✨

**Prochaines étapes:**
1. Surveiller pendant 7-14 jours
2. Analyser les recommandations
3. Valider avec des données réelles
4. Activer progressivement (si validation OK)

---

**Questions?** Ouvre une issue sur GitHub ou contacte le support.

**Date:** 30 septembre 2025
**Version:** 0.5.0-shadow
**Status:** 🟢 Production Ready
