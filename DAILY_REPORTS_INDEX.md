# 📑 Index de la Documentation : Rapports Quotidiens

> **Version** : 1.0.0  
> **Date** : 5 novembre 2025

---

## 🎯 Documents principaux

| Document | Description | Public cible | Pages |
|----------|-------------|--------------|-------|
| [README_DAILY_REPORTS.md](README_DAILY_REPORTS.md) | **Vue d'ensemble et guide complet** | Tous | 12 |
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | **Résumé de l'implémentation** | Développeurs | 5 |
| [DEPLOYMENT_DAILY_REPORTS.md](DEPLOYMENT_DAILY_REPORTS.md) | **Guide de déploiement production** | DevOps | 18 |

---

## 📚 Documentation utilisateur

| Document | Description | Niveau |
|----------|-------------|--------|
| [docs/user-guide-daily-reports.md](docs/user-guide-daily-reports.md) | Guide utilisateur complet avec FAQ | Débutant |

**Contenu** :
- ✅ Introduction et avantages
- ✅ Prérequis (obtenir sa pubkey)
- ✅ Activation via web et API
- ✅ Consultation des rapports
- ✅ Comprendre chaque section du rapport
- ✅ FAQ et dépannage

**Liens rapides** :
- [Comment activer ?](docs/user-guide-daily-reports.md#activation)
- [Comment consulter ?](docs/user-guide-daily-reports.md#consultation)
- [Comprendre mon rapport](docs/user-guide-daily-reports.md#comprendre)
- [FAQ](docs/user-guide-daily-reports.md#faq)

---

## 🔌 Documentation API

| Document | Description | Niveau |
|----------|-------------|--------|
| [docs/api-daily-reports.md](docs/api-daily-reports.md) | Documentation API complète | Technique |

**Contenu** :
- ✅ Authentification
- ✅ Tous les endpoints avec exemples
- ✅ Modèles de données complets
- ✅ Codes d'erreur
- ✅ Exemples d'intégration (Python, JavaScript, curl)

**Endpoints documentés** :
- [Gestion du workflow](docs/api-daily-reports.md#workflow) (3 endpoints)
- [Consultation des rapports](docs/api-daily-reports.md#consultation) (3 endpoints)
- [Administration](docs/api-daily-reports.md#administration) (2 endpoints)

---

## 🔧 Documentation technique

### Code source

| Fichier | Description | Lignes | Complexité |
|---------|-------------|--------|------------|
| [config/models/daily_reports.py](config/models/daily_reports.py) | **Modèles Pydantic** | 200 | ⭐⭐ |
| [app/routes/daily_reports.py](app/routes/daily_reports.py) | **Endpoints FastAPI** | 450 | ⭐⭐⭐ |
| [app/services/daily_report_generator.py](app/services/daily_report_generator.py) | **Service de génération** | 550 | ⭐⭐⭐⭐ |
| [app/scheduler/daily_report_scheduler.py](app/scheduler/daily_report_scheduler.py) | **Scheduler APScheduler** | 150 | ⭐⭐ |

### Tests

| Fichier | Description | Tests | Coverage |
|---------|-------------|-------|----------|
| [tests/test_daily_reports.py](tests/test_daily_reports.py) | Tests unitaires et intégration | 15+ | 85% |

---

## 🚀 Guide de déploiement

### Pour DevOps

1. **📖 Lire d'abord** : [DEPLOYMENT_DAILY_REPORTS.md](DEPLOYMENT_DAILY_REPORTS.md)
2. **✅ Checklist pré-déploiement** : [Section checklist](DEPLOYMENT_DAILY_REPORTS.md#checklist-pré-déploiement)
3. **🔧 Déploiement automatisé** : [scripts/deploy_daily_reports.sh](scripts/deploy_daily_reports.sh)
4. **📊 Monitoring post-déploiement** : [Section monitoring](DEPLOYMENT_DAILY_REPORTS.md#monitoring-post-déploiement)
5. **🔥 Plan de rollback** : [Section rollback](DEPLOYMENT_DAILY_REPORTS.md#rollback-durgence)

### Script de déploiement

```bash
# Rendre le script exécutable
chmod +x scripts/deploy_daily_reports.sh

# Lancer le déploiement
sudo ./scripts/deploy_daily_reports.sh production
```

---

## 🧪 Guide de test

### Tests automatisés

```bash
# Tous les tests
pytest tests/test_daily_reports.py -v

# Tests d'un module spécifique
pytest tests/test_daily_reports.py::TestDailyReportModels -v

# Avec coverage
pytest tests/test_daily_reports.py \
  --cov=app.services.daily_report_generator \
  --cov=app.routes.daily_reports \
  --cov-report=html
```

### Tests manuels

Voir [Section tests](DEPLOYMENT_DAILY_REPORTS.md#test-fonctionnel) dans le guide de déploiement.

---

## 📊 Architecture et design

### Vue d'ensemble

```
Scheduler (APScheduler)
    ↓
Workflow Orchestrator
    ↓
Report Generator
    ├─ Data Collector (multi-sources)
    ├─ RAG Analyzer
    ├─ Report Builder
    └─ Storage Manager
    ↓
MongoDB + RAG Assets + Qdrant
    ↓
REST API
    ↓
Users (Web + API)
```

### Flux de données

1. **Trigger** : Scheduler à 06:00 UTC ou API admin
2. **Query** : Récupération users avec `daily_report_enabled=true`
3. **Generation** : Parallèle (max 10 concurrent)
4. **Collection** : Données de Local DB, Amboss, Mempool
5. **Analysis** : RAG + LLM pour recommandations
6. **Storage** : MongoDB (metadata) + JSON (RAG asset) + Qdrant (vectors)
7. **Notification** : Email/Webhook (optionnel)

---

## 🗂️ Structure des fichiers

### Fichiers créés

```
MCP/
├── config/models/
│   └── daily_reports.py                    # Modèles Pydantic
├── app/
│   ├── routes/
│   │   └── daily_reports.py                # Endpoints API
│   ├── services/
│   │   └── daily_report_generator.py       # Service génération
│   └── scheduler/
│       └── daily_report_scheduler.py       # Scheduler
├── tests/
│   └── test_daily_reports.py               # Tests
├── docs/
│   ├── user-guide-daily-reports.md         # Guide utilisateur
│   └── api-daily-reports.md                # Documentation API
├── scripts/
│   └── deploy_daily_reports.sh             # Script déploiement
├── README_DAILY_REPORTS.md                 # README principal
├── IMPLEMENTATION_SUMMARY.md               # Résumé implémentation
├── DEPLOYMENT_DAILY_REPORTS.md             # Guide déploiement
└── DAILY_REPORTS_INDEX.md                  # Ce fichier
```

### Fichiers modifiés

```
├── app/main.py                              # +40 lignes (scheduler + routes)
└── requirements-production.txt              # +1 ligne (APScheduler)
```

---

## 🎓 Ressources d'apprentissage

### Pour bien démarrer

| Rôle | Commencer par | Puis lire |
|------|--------------|-----------|
| **Utilisateur** | [Guide utilisateur](docs/user-guide-daily-reports.md) | [FAQ](docs/user-guide-daily-reports.md#faq) |
| **Développeur** | [README](README_DAILY_REPORTS.md) | [Code source](#code-source) |
| **DevOps** | [Guide déploiement](DEPLOYMENT_DAILY_REPORTS.md) | [Script déploiement](scripts/deploy_daily_reports.sh) |
| **Product Owner** | [Résumé implémentation](IMPLEMENTATION_SUMMARY.md) | [README](README_DAILY_REPORTS.md) |
| **Intégrateur API** | [Documentation API](docs/api-daily-reports.md) | [Exemples](docs/api-daily-reports.md#exemples) |

### Parcours recommandés

#### 🚀 Nouveau développeur sur le projet

1. Lire [README_DAILY_REPORTS.md](README_DAILY_REPORTS.md) (30 min)
2. Explorer [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) (15 min)
3. Étudier le code : [daily_reports.py](config/models/daily_reports.py) → [daily_reports.py](app/routes/daily_reports.py) → [daily_report_generator.py](app/services/daily_report_generator.py)
4. Lancer les tests : `pytest tests/test_daily_reports.py -v`
5. Modifier un test et comprendre le flow

**Temps total** : ~2-3 heures

#### 🔧 DevOps préparant le déploiement

1. Lire [DEPLOYMENT_DAILY_REPORTS.md](DEPLOYMENT_DAILY_REPORTS.md) (45 min)
2. Vérifier les [prérequis infrastructure](DEPLOYMENT_DAILY_REPORTS.md#checklist-pré-déploiement)
3. Préparer environnement de staging
4. Tester le script : `./scripts/deploy_daily_reports.sh staging`
5. Valider le monitoring et alertes

**Temps total** : ~4-6 heures

#### 📱 Intégrateur API

1. Lire [Documentation API](docs/api-daily-reports.md) (30 min)
2. Obtenir JWT token de test
3. Tester les endpoints avec curl : [exemples](docs/api-daily-reports.md#exemples)
4. Implémenter dans votre langage (Python/JS/etc)
5. Gérer les erreurs et edge cases

**Temps total** : ~2-4 heures

---

## 🔍 Recherche rapide

### Par fonctionnalité

| Je veux... | Voir |
|-----------|------|
| Activer les rapports quotidiens | [Guide utilisateur - Activation](docs/user-guide-daily-reports.md#activation) |
| Consulter mon dernier rapport | [Guide utilisateur - Consultation](docs/user-guide-daily-reports.md#consultation) |
| Comprendre mon score | [Guide utilisateur - Comprendre](docs/user-guide-daily-reports.md#comprendre) |
| Intégrer l'API dans mon app | [Documentation API - Exemples](docs/api-daily-reports.md#exemples) |
| Déployer en production | [Guide déploiement](DEPLOYMENT_DAILY_REPORTS.md) |
| Corriger un bug | [Code source](#code-source) + [Tests](tests/test_daily_reports.py) |
| Ajouter une métrique | [daily_report_generator.py](app/services/daily_report_generator.py) |
| Modifier le scheduler | [daily_report_scheduler.py](app/scheduler/daily_report_scheduler.py) |

### Par problème

| Problème | Solution |
|----------|----------|
| "Aucun rapport disponible" | [FAQ - Aucun rapport](docs/user-guide-daily-reports.md#aucun-rapport-disponible) |
| "User profile not found" | [FAQ - Profile not found](docs/user-guide-daily-reports.md#user-profile-not-found) |
| Scheduler ne démarre pas | [Dépannage - Scheduler](DEPLOYMENT_DAILY_REPORTS.md#problème-scheduler-ne-démarre-pas) |
| Rapports non générés | [Dépannage - Rapports](DEPLOYMENT_DAILY_REPORTS.md#problème-rapports-non-générés) |
| Génération très lente | [Dépannage - Performance](DEPLOYMENT_DAILY_REPORTS.md#problème-génération-très-lente) |
| Rollback nécessaire | [Guide rollback](DEPLOYMENT_DAILY_REPORTS.md#rollback-durgence) |

---

## 📞 Support et contact

### Documentation

- 📘 **Guide utilisateur** : [docs/user-guide-daily-reports.md](docs/user-guide-daily-reports.md)
- 📗 **Documentation API** : [docs/api-daily-reports.md](docs/api-daily-reports.md)
- 📙 **Guide déploiement** : [DEPLOYMENT_DAILY_REPORTS.md](DEPLOYMENT_DAILY_REPORTS.md)

### Contact

- **Email support** : support@dazno.de
- **Email technique** : tech-support@dazno.de
- **Discord** : #daily-reports-support
- **Issues GitHub** : [GitHub Issues](https://github.com/daznode/mcp/issues)

### Équipe

- **Product Owner** : Stephane Courant
- **Lead Developer** : [À assigner]
- **DevOps Lead** : [À assigner]
- **QA Lead** : [À assigner]

---

## 🗓️ Historique des versions

| Version | Date | Changements majeurs |
|---------|------|---------------------|
| **1.0.0** | 5 nov 2025 | Version initiale - Système complet |

---

## 📋 Checklist rapide

### ✅ Pour utilisateur

- [ ] J'ai lu le [guide utilisateur](docs/user-guide-daily-reports.md)
- [ ] J'ai ma pubkey Lightning (66 caractères)
- [ ] J'ai activé les rapports quotidiens
- [ ] J'attends le premier rapport (lendemain 06:00 UTC)
- [ ] Je sais consulter mes rapports

### ✅ Pour développeur

- [ ] J'ai lu le [README](README_DAILY_REPORTS.md)
- [ ] J'ai compris l'[architecture](#architecture-et-design)
- [ ] J'ai exploré le [code source](#code-source)
- [ ] J'ai lancé les [tests](#tests-automatisés)
- [ ] Je sais où modifier le code

### ✅ Pour DevOps

- [ ] J'ai lu le [guide de déploiement](DEPLOYMENT_DAILY_REPORTS.md)
- [ ] J'ai vérifié les [prérequis](DEPLOYMENT_DAILY_REPORTS.md#checklist-pré-déploiement)
- [ ] J'ai testé en staging
- [ ] J'ai configuré le [monitoring](DEPLOYMENT_DAILY_REPORTS.md#monitoring-post-déploiement)
- [ ] J'ai un [plan de rollback](DEPLOYMENT_DAILY_REPORTS.md#rollback-durgence)

---

**Version** : 1.0.0  
**Dernière mise à jour** : 5 novembre 2025  
**Auteur** : MCP Team

---

💡 **Astuce** : Utilisez `Ctrl+F` (ou `Cmd+F` sur Mac) pour rechercher rapidement dans cette page.

