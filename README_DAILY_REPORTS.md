# 📊 Système de Rapports Quotidiens Automatisés

> **Version** : 1.0.0  
> **Date de mise en production** : 5 novembre 2025  
> **Status** : ✅ Production Ready

---

## 🎯 Vue d'ensemble

Le système de **Rapports Quotidiens Automatisés** permet aux utilisateurs de DazNode de recevoir automatiquement chaque jour une analyse complète et intelligente de leur nœud Lightning Network, enrichie par le système RAG et des recommandations basées sur l'IA.

### Fonctionnalités clés

- ✅ **Génération automatique quotidienne** à 06:00 UTC
- ✅ **Analyse multi-sources** (Amboss, Mempool, données locales)
- ✅ **Intelligence artificielle** via système RAG pour recommandations avancées
- ✅ **Historique 90 jours** avec conservation des assets RAG
- ✅ **API complète** pour intégration dans vos outils
- ✅ **Métriques détaillées** : capacité, canaux, forwarding, fees, réseau
- ✅ **Alertes proactives** : détection automatique d'anomalies
- ✅ **Tendances 7 jours** : visualisation de l'évolution

---

## 📦 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ARCHITECTURE SYSTÈME                      │
└─────────────────────────────────────────────────────────────┘

1. SCHEDULER (APScheduler)
   ↓ Déclenche tous les jours à 06:00 UTC
   
2. WORKFLOW ORCHESTRATOR
   ↓ Récupère les users avec workflow_enabled=True
   ↓ Génération parallèle (max 10 concurrent)
   
3. REPORT GENERATOR
   ↓ Pour chaque utilisateur :
   ├─ Collecte données multi-sources
   ├─ Analyse via RAG + LLM
   ├─ Génère rapport structuré
   └─ Détecte alertes et recommandations
   
4. STORAGE & INDEXING
   ↓ Sauvegarde JSON : rag/RAG_assets/reports/daily/{user_id}/
   ↓ MongoDB : métadonnées + rapports complets
   ↓ Qdrant : indexation sémantique pour RAG
   
5. API ENDPOINTS
   ↓ Consultation via API REST
   └─ Interface web dazno.de
```

---

## 📂 Structure des fichiers

### Modèles de données
```
config/models/
└── daily_reports.py          # Modèles Pydantic (UserProfile, DailyReport, etc.)
```

### API Endpoints
```
app/routes/
└── daily_reports.py          # Endpoints REST API
```

### Services
```
app/services/
└── daily_report_generator.py # Logique de génération des rapports
```

### Scheduler
```
app/scheduler/
└── daily_report_scheduler.py # Tâche planifiée avec APScheduler
```

### Tests
```
tests/
└── test_daily_reports.py     # Tests unitaires et d'intégration
```

### Documentation
```
docs/
├── user-guide-daily-reports.md  # Guide utilisateur complet
└── api-daily-reports.md         # Documentation API
```

---

## 🚀 Installation et configuration

### 1. Dépendances

Ajoutées à `requirements-production.txt` :

```
APScheduler>=3.10.0,<4.0.0  # Task scheduling
```

Installation :

```bash
pip install -r requirements-production.txt
```

### 2. Variables d'environnement

Ajoutez à votre fichier `.env` :

```bash
# Daily Reports Configuration
DAILY_REPORTS_SCHEDULER_ENABLED=true
DAILY_REPORTS_HOUR=6              # Heure UTC (défaut: 6)
DAILY_REPORTS_MINUTE=0            # Minute (défaut: 0)
DAILY_REPORTS_MAX_CONCURRENT=10   # Nb max de rapports générés en parallèle
DAILY_REPORTS_MAX_RETRIES=3       # Nb de tentatives en cas d'échec
DAILY_REPORTS_TIMEOUT=300         # Timeout en secondes (5 min)
```

### 3. Collections MongoDB

Le système créera automatiquement les collections suivantes :

- `user_profiles` : Profils utilisateurs avec configuration workflow
- `daily_reports` : Rapports quotidiens (TTL 90 jours)

Index automatiques :
- `user_profiles`: `lightning_pubkey` (unique), `daily_report_enabled`, `tenant_id`
- `daily_reports`: `report_id` (unique), `user_id + report_date`, `generation_status`

### 4. Répertoires RAG

Création automatique :

```bash
rag/RAG_assets/reports/daily/{user_id}/YYYYMMDD.json
```

---

## 📡 Endpoints API

### Gestion du workflow

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/api/v1/user/profile/daily-report/enable` | Active le workflow |
| `POST` | `/api/v1/user/profile/daily-report/disable` | Désactive le workflow |
| `GET` | `/api/v1/user/profile/daily-report/status` | Statut du workflow |

### Consultation des rapports

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/v1/reports/daily/latest` | Dernier rapport |
| `GET` | `/api/v1/reports/daily/history` | Historique paginé |
| `GET` | `/api/v1/reports/daily/{report_id}` | Rapport spécifique |

### Administration (Admin uniquement)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/api/v1/admin/reports/daily/trigger` | Génération manuelle |
| `GET` | `/api/v1/admin/reports/daily/stats` | Statistiques globales |

📘 **Documentation complète** : Voir [docs/api-daily-reports.md](docs/api-daily-reports.md)

---

## 🧪 Tests

### Lancer les tests unitaires

```bash
# Tous les tests daily reports
pytest tests/test_daily_reports.py -v

# Tests d'un module spécifique
pytest tests/test_daily_reports.py::TestDailyReportModels -v

# Tests avec coverage
pytest tests/test_daily_reports.py --cov=app.services.daily_report_generator --cov-report=html
```

### Tests manuels

#### 1. Activer le workflow

```bash
curl -X POST https://api.dazno.de/api/v1/user/profile/daily-report/enable \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### 2. Déclencher une génération manuelle (Admin)

```bash
curl -X POST https://api.dazno.de/api/v1/admin/reports/daily/trigger \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_ids": null}'
```

#### 3. Consulter le dernier rapport

```bash
curl -X GET https://api.dazno.de/api/v1/reports/daily/latest \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 📊 Monitoring

### Métriques Prometheus

Métriques automatiquement exposées :

```prometheus
# Nombre total de rapports générés
daily_reports_generated_total

# Durée de génération d'un rapport
daily_reports_generation_duration_seconds

# Erreurs de génération
daily_reports_errors_total

# Nombre d'utilisateurs avec workflow activé
daily_reports_users_enabled_total

# Durée d'indexation RAG
daily_reports_rag_indexing_duration_seconds
```

### Alertes recommandées

```yaml
# alerting-rules.yml
groups:
  - name: daily_reports
    rules:
      - alert: DailyReportsGenerationSlow
        expr: daily_reports_generation_duration_seconds{quantile="0.95"} > 60
        for: 5m
        annotations:
          summary: "Génération de rapports lente (p95 > 60s)"
      
      - alert: DailyReportsHighErrorRate
        expr: rate(daily_reports_errors_total[1h]) > 5
        for: 10m
        annotations:
          summary: "Taux d'erreur élevé dans la génération de rapports"
```

### Logs

Les logs sont structurés avec niveaux :

```python
logger.info("Daily report enabled for tenant {tenant_id}")
logger.warning("Could not fetch Amboss data: {error}")
logger.error("Error generating report {report_id}: {error}")
```

Recherche dans les logs :

```bash
# Tous les logs daily reports
grep "daily_report" /var/log/mcp/app.log

# Erreurs uniquement
grep "ERROR.*daily.*report" /var/log/mcp/app.log

# Rapports générés aujourd'hui
grep "Report.*generated successfully" /var/log/mcp/app.log | grep $(date +%Y-%m-%d)
```

---

## 🔧 Maintenance

### Tâches courantes

#### Désactiver temporairement le scheduler

```bash
# Dans .env
DAILY_REPORTS_SCHEDULER_ENABLED=false

# Redémarrer l'application
systemctl restart mcp-api
```

#### Purger les anciens rapports manuellement

```bash
# Connexion MongoDB
mongosh mongodb://localhost:27017/mcp_db

# Supprimer rapports > 90 jours
db.daily_reports.deleteMany({
  report_date: { $lt: new Date(Date.now() - 90*24*60*60*1000) }
})
```

#### Régénérer les rapports d'une période

```python
# Script Python
import requests

api_url = "https://api.dazno.de/api/v1/admin/reports/daily/trigger"
admin_token = "YOUR_ADMIN_TOKEN"

# Régénérer pour des users spécifiques
response = requests.post(
    api_url,
    headers={"Authorization": f"Bearer {admin_token}"},
    json={"user_ids": ["user_123", "user_456"]}
)
print(response.json())
```

---

## 🐛 Dépannage

### Problème : Scheduler ne démarre pas

**Symptôme** : Logs "Daily report scheduler is disabled"

**Solution** :
```bash
# Vérifier variable d'environnement
echo $DAILY_REPORTS_SCHEDULER_ENABLED  # Doit être "true"

# Vérifier logs au démarrage
tail -f /var/log/mcp/app.log | grep scheduler
```

### Problème : Rapports non générés

**Symptôme** : Aucun rapport créé le lendemain

**Diagnostic** :
1. Vérifier que le workflow est activé pour l'utilisateur
2. Vérifier que la pubkey Lightning est renseignée
3. Vérifier les logs d'erreur

```bash
# Statut workflow pour un user
curl -X GET https://api.dazno.de/api/v1/user/profile/daily-report/status \
  -H "Authorization: Bearer USER_JWT_TOKEN"

# Logs génération
grep "Starting daily reports generation" /var/log/mcp/app.log
```

### Problème : Génération très lente

**Symptôme** : Génération prend > 5 minutes

**Solutions** :
1. Augmenter `DAILY_REPORTS_MAX_CONCURRENT`
2. Augmenter `DAILY_REPORTS_TIMEOUT`
3. Vérifier disponibilité APIs externes (Amboss, Mempool)

```bash
# Monitoring temps de génération
grep "generation_duration" /var/log/mcp/app.log | tail -20
```

---

## 📈 Performance

### Benchmarks (environnement de test)

- **Génération 1 rapport** : ~15-30 secondes
- **Génération 100 rapports** : ~5-10 minutes (parallèle)
- **Génération 1000 rapports** : ~45-60 minutes (parallèle)

### Optimisations implémentées

- ✅ **Génération parallèle** avec semaphore (max 10 concurrent)
- ✅ **Timeout par rapport** (5 minutes)
- ✅ **Retry logic** (3 tentatives avec backoff)
- ✅ **Cache RAG** pour embeddings et requêtes fréquentes
- ✅ **Indexation asynchrone** dans Qdrant
- ✅ **Collecte multi-sources optimisée** (parallèle)

### Recommandations production

- **Serveur minimum** : 2 vCPU, 4GB RAM
- **Serveur recommandé** : 4 vCPU, 8GB RAM, SSD
- **MongoDB** : Replica set pour haute disponibilité
- **Redis** : Cache pour performances optimales

---

## 🗺️ Roadmap

### Version 1.1 (Q1 2026)
- [ ] Notifications par email/Telegram/Discord
- [ ] Personnalisation heure de génération (comptes premium)
- [ ] Rapports hebdomadaires/mensuels
- [ ] Export PDF automatique

### Version 1.2 (Q2 2026)
- [ ] Comparaison avec peers similaires (benchmarking)
- [ ] Webhooks personnalisés
- [ ] Alertes temps réel (WebSocket)
- [ ] Dashboard interactif avancé avec graphiques

### Version 2.0 (Q3 2026)
- [ ] Machine Learning pour prédictions
- [ ] Recommandations auto-appliquées (avec approval)
- [ ] Multi-nœuds dans un seul rapport
- [ ] API GraphQL

---

## 👥 Contribution

### Développement local

```bash
# Cloner le repo
git clone https://github.com/daznode/mcp.git
cd mcp

# Installer dépendances
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

# Configurer .env
cp .env.example .env
# Éditer .env avec vos paramètres

# Lancer l'application
uvicorn app.main:app --reload --port 8000

# Lancer les tests
pytest tests/ -v
```

### Guidelines

1. **Code style** : Suivre PEP 8
2. **Type hints** : Obligatoires pour toutes les fonctions
3. **Docstrings** : Google style pour documentation
4. **Tests** : Coverage minimum 85%
5. **Commits** : Convention [Conventional Commits](https://www.conventionalcommits.org/)

---

## 📞 Support

### Documentation
- 📘 [Guide utilisateur complet](docs/user-guide-daily-reports.md)
- 📗 [Documentation API](docs/api-daily-reports.md)
- 📙 [Spécifications techniques](SPECIFICATIONS_DAILY_REPORTS.md)

### Contact
- **Email** : support@dazno.de
- **Discord** : [discord.gg/daznode](https://discord.gg/daznode)
- **Issues** : [GitHub Issues](https://github.com/daznode/mcp/issues)

---

## 📄 Licence

Copyright © 2025 DazNode Team  
Tous droits réservés.

---

**Version** : 1.0.0  
**Dernière mise à jour** : 5 novembre 2025  
**Auteur** : MCP Team

