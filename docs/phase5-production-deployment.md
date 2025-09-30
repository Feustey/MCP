# Phase 5 - Déploiement Production MCP

> Guide complet pour le déploiement et l'exploitation en production
> Dernière mise à jour: 30 septembre 2025

## 📋 Vue d'ensemble

La Phase 5 concerne le déploiement contrôlé de MCP en production avec:
- Mode **Shadow** activé par défaut (dry-run)
- Monitoring continu sans Grafana
- Alertes Telegram
- Système de rollback opérationnel
- Tests end-to-end automatisés

## 🎯 Objectifs Phase 5

1. ✅ Déployer l'API en production (Hostinger)
2. ✅ Activer le mode shadow pour observation
3. ✅ Monitorer les performances en temps réel
4. ⚠️ Valider le Fee Optimizer sur données réelles
5. 📊 Collecter métriques et feedback
6. 🔄 Itérer basé sur les résultats

## 🏗️ Architecture Production

```
┌─────────────────────────────────────────────────────────┐
│                  Nginx Reverse Proxy                    │
│                    (SSL/TLS)                            │
└───────────────────┬─────────────────────────────────────┘
                    │
        ┌───────────┴──────────┐
        │                      │
┌───────▼─────────┐   ┌───────▼────────┐
│   MCP API       │   │   Qdrant       │
│   (FastAPI)     │◄──┤  (Vector DB)   │
└───────┬─────────┘   └────────────────┘
        │
        ├──► MongoDB Atlas (Cloud)
        ├──► Redis Upstash (Cloud)
        └──► LNbits API (External)
```

## 📦 Prérequis

### Infrastructure
- VPS Hostinger ou équivalent
- Docker & Docker Compose installés
- Domaine avec certificat SSL
- Minimum 2GB RAM, 2 CPU cores

### Services Externes
- MongoDB Atlas (base de données)
- Redis Upstash (cache)
- LNbits (Lightning Network)
- Telegram Bot (alertes - optionnel)

### Variables d'Environnement Requises

```bash
# Environnement
ENVIRONMENT=production
DEBUG=false
DRY_RUN=true  # IMPORTANT: Shadow mode par défaut

# Base de données
MONGO_URL=mongodb+srv://...
REDIS_URL=https://...
REDIS_TOKEN=...

# Sécurité
JWT_SECRET=<généré>
SECRET_KEY=<généré>

# Lightning
LNBITS_URL=https://...
LNBITS_ADMIN_KEY=<secret>

# IA (optionnel)
ANTHROPIC_API_KEY=<secret>
OPENAI_API_KEY=<secret>

# Notifications (optionnel)
TELEGRAM_BOT_TOKEN=<secret>
TELEGRAM_CHAT_ID=<id>
```

## 🚀 Déploiement

### 1. Préparation

```bash
# Clone le repo
git clone https://github.com/yourusername/MCP.git
cd MCP

# Configure l'environnement
cp .env.example .env
nano .env  # Édite les variables

# Vérifie la configuration
docker-compose config
```

### 2. Build et Démarrage

```bash
# Build l'image
docker-compose -f docker-compose.production.yml build

# Démarre les services
docker-compose -f docker-compose.production.yml up -d

# Vérifie les logs
docker-compose logs -f mcp-api
```

### 3. Vérification

```bash
# Test de santé
curl https://api.dazno.de/api/v1/health

# Réponse attendue:
# {"status": "healthy", "timestamp": "2025-09-30T..."}

# Test des endpoints
curl https://api.dazno.de/
```

## 🧪 Tests de Production

### Test End-to-End

```bash
# Active l'environnement virtuel
source .venv/bin/activate

# Lance le test pipeline
python test_production_pipeline.py

# Résultat attendu: 80-100% pass rate
```

### Test Shadow Mode

Le script suivant teste le Fee Optimizer en mode dry-run:

```python
from src.optimizers.core_fee_optimizer import CoreFeeOptimizer

# Initialize avec dry_run=True
optimizer = CoreFeeOptimizer(
    node_pubkey="02778f4a...",
    dry_run=True,
    max_changes_per_run=5
)

# Lance l'optimisation (aucune action réelle)
results = await optimizer.run_pipeline()

# Analyse les recommandations
print(f"Recommended changes: {len(results['recommendations'])}")
```

## 📊 Monitoring Production

### Monitoring Continu

```bash
# Lance le monitoring (intervalle 60s)
python monitor_production.py

# Ou avec configuration custom
python monitor_production.py --interval 30 --duration 3600
```

Le monitoring vérifie:
- ✅ Health de l'API (toutes les 60s)
- ✅ Temps de réponse
- ✅ Logs du Fee Optimizer
- ✅ Disponibilité du système de rollback
- 📱 Alertes Telegram si échecs > 3

### Rapports Générés

Les rapports sont sauvegardés dans:
```
monitoring_data/
  └── monitoring_20250930.json
      ├── checks: []         # Tous les checks
      ├── start_date: ...
      └── summary: {}        # Résumé

data/test_results/
  └── pipeline_test_*.json  # Résultats tests
```

### Analyse des Métriques

```bash
# Voir le dernier rapport
cat monitoring_data/monitoring_$(date +%Y%m%d).json | jq '.checks[-1]'

# Statistiques uptime
cat monitoring_data/monitoring_$(date +%Y%m%d).json | \
  jq '.checks | length as $total |
      ([.[] | select(.health.healthy)] | length) as $success |
      {total: $total, success: $success, uptime: ($success/$total*100)}'
```

## 🔄 Mode Shadow → Production

### Activation Progressive

**Étape 1: Shadow Mode (Semaine 1-2)**
```bash
# .env
DRY_RUN=true
MAX_CHANGES_PER_RUN=0

# Observe les recommandations sans action
```

**Étape 2: Test Limité (Semaine 3)**
```bash
# .env
DRY_RUN=false
MAX_CHANGES_PER_RUN=1  # 1 seul canal à la fois

# Active pour 1 canal test
```

**Étape 3: Production Limitée (Semaine 4+)**
```bash
# .env
DRY_RUN=false
MAX_CHANGES_PER_RUN=5  # 5 canaux maximum

# Surveillance renforcée
```

## 🛡️ Sécurité & Rollback

### Système de Rollback

Le système crée automatiquement des backups avant chaque modification:

```
data/rollbacks/
  ├── 1727719200_02778f4a_backup.json
  └── 1727719300_02778f4a_backup.json
```

### Restauration Manuelle

```python
from src.optimizers.core_fee_optimizer import CoreFeeOptimizer

optimizer = CoreFeeOptimizer(...)
await optimizer.rollback_to_backup("data/rollbacks/xxx.json")
```

### Alertes Critiques

Le système envoie des alertes Telegram pour:
- ❌ API down (3 échecs consécutifs)
- ⚠️ Erreurs dans le Fee Optimizer
- 🔄 Rollback déclenché
- 📈 Performance dégradée

## 📈 Métriques Clés

### KPIs à Surveiller

1. **Disponibilité API**
   - Target: > 99%
   - Alertes si < 95%

2. **Temps de Réponse**
   - Target: < 500ms
   - Alertes si > 2000ms

3. **Fee Optimizer**
   - Recommandations/jour
   - Taux de succès des ajustements
   - Rollbacks déclenchés

4. **Performances Canaux**
   - Forwards avant/après optimisation
   - Revenus générés
   - Score de performance

## 🐛 Debugging Production

### Logs Utiles

```bash
# Logs API
docker-compose logs -f mcp-api

# Logs Fee Optimizer
tail -f logs/fee_optimizer.log

# Logs monitoring
tail -f logs/monitoring.log
```

### Problèmes Courants

**API ne répond pas**
```bash
# Vérifie le container
docker ps -a | grep mcp-api

# Restart si nécessaire
docker-compose restart mcp-api
```

**Fee Optimizer bloqué**
```bash
# Vérifie les credentials LND
ls -la ~/.lnd/data/chain/bitcoin/mainnet/

# Teste la connexion
curl -X GET https://lnbits.../api/v1/wallet
```

**Rollback nécessaire**
```bash
# Liste les backups
ls -lh data/rollbacks/

# Restaure le dernier
python -c "
from src.optimizers.core_fee_optimizer import CoreFeeOptimizer
import asyncio

async def restore():
    opt = CoreFeeOptimizer(...)
    await opt.rollback_to_latest()

asyncio.run(restore())
"
```

## 🎓 Best Practices

1. **Toujours démarrer en Shadow Mode**
   - Observe pendant 7-14 jours minimum
   - Analyse les recommandations
   - Valide la cohérence

2. **Limiter les changements**
   - MAX_CHANGES_PER_RUN faible au début
   - Augmente progressivement
   - Surveille l'impact

3. **Backups réguliers**
   - Backups automatiques avant chaque action
   - Conservation 30 jours minimum
   - Tests de restauration mensuels

4. **Monitoring actif**
   - Alerts Telegram configurées
   - Revue quotidienne des métriques
   - Rapport hebdomadaire

5. **Feedback loop**
   - Compare prédictions vs réalité
   - Ajuste les heuristiques
   - Itère sur les seuils

## 📞 Support & Maintenance

### Healthcheck Automatique

```bash
# Cron job pour monitoring continu
# Ajoute à crontab -e:
*/5 * * * * cd /path/to/MCP && python monitor_production.py --duration 60
```

### Maintenance Hebdomadaire

1. Revue des métriques
2. Analyse des erreurs
3. Nettoyage logs anciens (> 30j)
4. Backup des données importantes
5. Update des dépendances si nécessaire

### Contact

- GitHub Issues: https://github.com/yourusername/MCP/issues
- Telegram: [@mcp_support](https://t.me/mcp_support)
- Email: support@dazno.de

## 📚 Ressources

- [Architecture](docs/core/architecture.md)
- [API Documentation](docs/api/endpoints-complete.md)
- [Fee Optimizer](src/optimizers/core_fee_optimizer.py)
- [Tests](test_production_pipeline.py)
- [Monitoring](monitor_production.py)

---

**Statut Phase 5:** 🟢 Production Ready (Shadow Mode)
**Dernière validation:** 30 septembre 2025
**Version:** 0.5.0-production
