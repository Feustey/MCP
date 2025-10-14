# 📚 MCP v1.0 - Index Complet du Projet

> **Guide de navigation** pour tous les documents, scripts et ressources du projet MCP
> 
> Dernière mise à jour: 13 octobre 2025  
> Version: 1.0.0

---

## 🚀 DÉMARRAGE RAPIDE

### Pour Déployer MAINTENANT
1. **[DEPLOY_NOW.md](DEPLOY_NOW.md)** - Guide de déploiement ultra-rapide (30 min)
2. **[scripts/deploy_all.sh](scripts/deploy_all.sh)** - Script d'orchestration complet

### Pour Comprendre le Projet
1. **[README.md](README.md)** - Vue d'ensemble du projet
2. **[_SPECS/Roadmap-Production-v1.0.md](_SPECS/Roadmap-Production-v1.0.md)** - Roadmap complète 15 semaines
3. **[docs/backbone-technique-MVP.md](docs/backbone-technique-MVP.md)** - Architecture technique

---

## 📋 DOCUMENTATION PAR THÈME

### 🎯 Roadmap & Planning

| Document | Description | Statut |
|----------|-------------|--------|
| [_SPECS/Roadmap-Production-v1.0.md](_SPECS/Roadmap-Production-v1.0.md) | Roadmap production 15 semaines | ✅ Complet |
| [_SPECS/Plan-MVP.md](_SPECS/Plan-MVP.md) | Plan MVP original | ✅ Référence |
| [PHASE5-STATUS.md](PHASE5-STATUS.md) | Status Phase 5 (Shadow Mode) | ✅ Archive |
| [IMPLEMENTATION_PHASE1_STATUS.md](IMPLEMENTATION_PHASE1_STATUS.md) | Status Phase 1 détaillé | ✅ Actuel |
| [WORK_COMPLETED_20251012.md](WORK_COMPLETED_20251012.md) | Travaux complétés 12 oct | ✅ Archive |

### 🏗️ Architecture & Design

| Document | Description | Statut |
|----------|-------------|--------|
| [docs/backbone-technique-MVP.md](docs/backbone-technique-MVP.md) | Architecture technique consolidée | ✅ Complet |
| [docs/mongodb-atlas-setup.md](docs/mongodb-atlas-setup.md) | Setup MongoDB Atlas | ✅ Guide |
| [docs/redis-cloud-setup.md](docs/redis-cloud-setup.md) | Setup Redis Cloud | ✅ Guide |
| [production_optimization_audit.md](production_optimization_audit.md) | Audit optimisation production | ✅ Référence |

### 🚀 Déploiement

| Document | Description | Usage |
|----------|-------------|-------|
| [DEPLOY_NOW.md](DEPLOY_NOW.md) | Guide déploiement ultra-rapide | 🔥 Prioritaire |
| [DEPLOY_QUICKSTART.md](DEPLOY_QUICKSTART.md) | Quick start déploiement | ✅ Guide |
| [PHASE5-QUICKSTART.md](PHASE5-QUICKSTART.md) | Quick start Phase 5 | ✅ Archive |
| [GUIDE_CONFIGURATION_FINALE.md](GUIDE_CONFIGURATION_FINALE.md) | Guide configuration finale | ✅ Référence |

### 🔧 Configuration

| Fichier | Description | Type |
|---------|-------------|------|
| [env.production.example](env.production.example) | Template .env production | Config |
| [config/decision_thresholds.yaml](config/decision_thresholds.yaml) | Seuils de décision | Config |
| [config/logrotate.conf](config/logrotate.conf) | Configuration logrotate | Config |
| [requirements-production.txt](requirements-production.txt) | Dépendances Python production | Deps |

---

## 🛠️ SCRIPTS & OUTILS

### Scripts de Déploiement

| Script | Description | Durée | Usage |
|--------|-------------|-------|-------|
| [scripts/deploy_all.sh](scripts/deploy_all.sh) | **Déploiement complet orchestré** | 20 min | `sudo ./scripts/deploy_all.sh` |
| [scripts/configure_nginx_production.sh](scripts/configure_nginx_production.sh) | Configuration Nginx + SSL | 30 min | `sudo ./scripts/configure_nginx_production.sh` |
| [scripts/configure_systemd_autostart.sh](scripts/configure_systemd_autostart.sh) | Service systemd auto-restart | 10 min | `sudo ./scripts/configure_systemd_autostart.sh` |
| [scripts/setup_logrotate.sh](scripts/setup_logrotate.sh) | Configuration logrotate | 5 min | `sudo ./scripts/setup_logrotate.sh` |
| [scripts/deploy_docker_production.sh](scripts/deploy_docker_production.sh) | Déploiement Docker Blue/Green | 15 min | `./scripts/deploy_docker_production.sh` |

### Scripts d'Administration

| Script | Description | Usage |
|--------|-------------|-------|
| [start_api.sh](start_api.sh) | Démarrage API optimisé | `./start_api.sh` |
| [monitor_production.py](monitor_production.py) | Monitoring production 24/7 | `python monitor_production.py --duration 3600` |
| [test_production_pipeline.py](test_production_pipeline.py) | Tests end-to-end | `python test_production_pipeline.py` |
| [scripts/daily_shadow_report.py](scripts/daily_shadow_report.py) | Rapport quotidien shadow mode | `python scripts/daily_shadow_report.py` |

### Scripts de Maintenance

| Script | Description | Usage |
|--------|-------------|-------|
| [topup_wallet.py](topup_wallet.py) | Recharger wallet LNBits | `python topup_wallet.py 50000` |
| [run_test_system.py](run_test_system.py) | Lancer système de test | `python run_test_system.py` |
| [analyze_metrics.py](analyze_metrics.py) | Analyser métriques | `python analyze_metrics.py` |

---

## 💻 CODE SOURCE

### Structure des Répertoires

```
MCP/
├── app/                          # Application FastAPI
│   ├── routes/                   # Endpoints API
│   │   ├── health.py            # Health checks
│   │   ├── shadow_dashboard.py  # Dashboard shadow mode
│   │   └── ...
│   └── services/                 # Services métier
│       ├── fallback_manager.py  # 🆕 Mode dégradé
│       └── lightning_scoring.py # Scoring Lightning
│
├── src/                          # Code source principal
│   ├── auth/                     # 🆕 Authentification
│   │   ├── encryption.py        # Chiffrement AES-256-GCM
│   │   └── macaroon_manager.py  # Gestion macaroons
│   │
│   ├── clients/                  # Clients API
│   │   ├── lnbits_client.py     # Client LNBits
│   │   ├── lnbits_client_v2.py  # Client LNBits v2
│   │   └── amboss_client.py     # Client Amboss
│   │
│   ├── optimizers/               # Moteurs d'optimisation
│   │   ├── core_fee_optimizer.py   # Optimizer principal
│   │   ├── decision_engine.py      # ✅ Moteur de décision
│   │   ├── heuristics_engine.py    # Engine heuristiques
│   │   ├── policy_validator.py     # Validation policies
│   │   └── heuristics/             # 🆕 Heuristiques détaillées
│   │       ├── __init__.py
│   │       ├── centrality.py       # Centralité réseau
│   │       ├── liquidity.py        # Équilibre liquidité
│   │       ├── activity.py         # Activité routage
│   │       ├── competitiveness.py  # Compétitivité fees
│   │       └── reliability.py      # Fiabilité
│   │
│   ├── tools/                    # Outils utilitaires
│   │   ├── node_simulator.py    # Simulateur nœuds
│   │   ├── rollback_manager.py  # Rollback transactionnel
│   │   ├── shadow_mode_logger.py # Logger shadow mode
│   │   └── policy_executor.py   # Exécution policies
│   │
│   └── scanners/                 # Scanners réseau
│       ├── node_scanner.py      # Scanner nœuds
│       └── liquidity_scanner.py # Scanner liquidité
│
├── rag/                          # Système RAG
│   ├── generators/              # Générateurs assets
│   └── RAG_assets/              # Assets RAG
│
├── config/                       # Configurations
│   ├── decision_thresholds.yaml # 🆕 Seuils décision
│   └── logrotate.conf           # 🆕 Rotation logs
│
├── data/                         # Données
│   ├── metrics/                 # Métriques
│   ├── reports/                 # Rapports
│   └── fallback/                # 🆕 Données fallback
│
├── docs/                         # Documentation
│   ├── core/                    # Documentation principale
│   ├── technical/               # Documentation technique
│   └── prompts/                 # Prompts modèles
│
├── scripts/                      # 🆕 Scripts d'administration
│   ├── deploy_all.sh            # Orchestration complète
│   ├── configure_nginx_production.sh
│   ├── configure_systemd_autostart.sh
│   ├── setup_logrotate.sh
│   ├── deploy_docker_production.sh
│   └── daily_shadow_report.py
│
└── tests/                        # Tests
    ├── unit/                    # Tests unitaires
    └── integration/             # Tests d'intégration
```

### Fichiers Clés par Fonctionnalité

#### Optimisation des Fees
- `src/optimizers/core_fee_optimizer.py` - Optimizer principal
- `src/optimizers/decision_engine.py` - Décisions
- `src/optimizers/heuristics/*.py` - Heuristiques (5 modules)
- `config/decision_thresholds.yaml` - Configuration

#### Intégration LNBits/LND
- `src/clients/lnbits_client_v2.py` - Client complet
- `src/auth/macaroon_manager.py` - Gestion macaroons
- `src/auth/encryption.py` - Chiffrement
- `src/tools/policy_executor.py` - Exécution

#### Résilience & Fallback
- `app/services/fallback_manager.py` - Mode dégradé
- `src/tools/rollback_manager.py` - Rollback
- `src/tools/circuit_breaker.py` - Circuit breaker

#### Shadow Mode & Monitoring
- `src/tools/shadow_mode_logger.py` - Logger shadow
- `app/routes/shadow_dashboard.py` - Dashboard
- `scripts/daily_shadow_report.py` - Rapports
- `monitor_production.py` - Monitoring

---

## 🐳 DOCKER & INFRASTRUCTURE

### Fichiers Docker

| Fichier | Description | Usage |
|---------|-------------|-------|
| [Dockerfile.production](Dockerfile.production) | 🆕 Image Docker optimisée | Production |
| [docker-compose.production.yml](docker-compose.production.yml) | Compose production | Production |
| [docker_entrypoint.sh](docker_entrypoint.sh) | 🆕 Entrypoint intelligent | Auto |

### Configuration Serveur

| Fichier | Description | Localisation |
|---------|-------------|--------------|
| `/etc/nginx/sites-available/mcp-api` | Config Nginx | Serveur |
| `/etc/systemd/system/mcp-api.service` | Service systemd | Serveur |
| `/etc/logrotate.d/mcp-api` | Logrotate | Serveur |

---

## 📊 RAPPORTS & STATUS

### Rapports d'Implémentation

| Document | Date | Contenu |
|----------|------|---------|
| [IMPLEMENTATION_COMPLETE_REPORT.md](IMPLEMENTATION_COMPLETE_REPORT.md) | 12 oct | Rapport complet Phase 1 |
| [WORK_COMPLETED_20251012.md](WORK_COMPLETED_20251012.md) | 12 oct | Travaux 12 octobre |
| [SPRINT_SUMMARY_20251012.md](SPRINT_SUMMARY_20251012.md) | 12 oct | Résumé sprint |

### Rapports Historiques

| Document | Sujet | Status |
|----------|-------|--------|
| [RAPPORT_FINAL_RESOLUTION_10OCT2025.md](RAPPORT_FINAL_RESOLUTION_10OCT2025.md) | Résolution 828 failures | ✅ Archive |
| [INVESTIGATION_FINALE_10OCT2025.md](INVESTIGATION_FINALE_10OCT2025.md) | Investigation finale | ✅ Archive |
| [PHASE2_COMPLETE_REPORT.md](PHASE2_COMPLETE_REPORT.md) | Phase 2 | ✅ Archive |

---

## 🧪 TESTS

### Scripts de Tests

| Script | Description | Usage |
|--------|-------------|-------|
| [test_production_pipeline.py](test_production_pipeline.py) | Tests end-to-end complets | `python test_production_pipeline.py` |
| [test_production_endpoints.py](test_production_endpoints.py) | Tests endpoints API | `python test_production_endpoints.py` |
| [test_lnbits_integration.py](test_lnbits_integration.py) | Tests intégration LNBits | `python test_lnbits_integration.py` |

### Tests Unitaires

| Répertoire | Description |
|------------|-------------|
| `tests/unit/clients/` | Tests clients API |
| `tests/unit/optimizers/` | Tests optimizers |
| `tests/unit/tools/` | Tests outils |

---

## 📖 GUIDES UTILISATEUR

### Guides de Déploiement

1. **[DEPLOY_NOW.md](DEPLOY_NOW.md)** - 🔥 Guide ultra-rapide (30 min)
2. **[DEPLOY_QUICKSTART.md](DEPLOY_QUICKSTART.md)** - Quick start détaillé
3. **[GUIDE_CONFIGURATION_FINALE.md](GUIDE_CONFIGURATION_FINALE.md)** - Configuration complète

### Guides Techniques

1. **[docs/backbone-technique-MVP.md](docs/backbone-technique-MVP.md)** - Architecture
2. **[docs/mongodb-atlas-setup.md](docs/mongodb-atlas-setup.md)** - MongoDB
3. **[docs/redis-cloud-setup.md](docs/redis-cloud-setup.md)** - Redis

---

## 🆕 NOUVEAUX FICHIERS (13 octobre 2025)

### Scripts
- ✅ `scripts/deploy_all.sh` - Orchestration déploiement complet
- ✅ `start_api.sh` - Démarrage API optimisé
- ✅ `docker_entrypoint.sh` - Entrypoint Docker intelligent

### Code Source
- ✅ `app/services/fallback_manager.py` - Gestionnaire mode dégradé
- ✅ `src/auth/encryption.py` - Chiffrement AES-256-GCM
- ✅ `src/auth/macaroon_manager.py` - Gestion macaroons
- ✅ `src/optimizers/heuristics/centrality.py` - Heuristique centralité
- ✅ `src/optimizers/heuristics/liquidity.py` - Heuristique liquidité
- ✅ `src/optimizers/heuristics/activity.py` - Heuristique activité
- ✅ `src/optimizers/heuristics/competitiveness.py` - Heuristique compétitivité
- ✅ `src/optimizers/heuristics/reliability.py` - Heuristique fiabilité

### Documentation
- ✅ `DEPLOY_NOW.md` - Guide déploiement immédiat
- ✅ `INDEX.md` - Ce fichier (index complet)

---

## 🎯 PRIORITÉS PAR RÔLE

### DevOps

**Aujourd'hui :**
1. Déployer infrastructure : `sudo ./scripts/deploy_all.sh`
2. Provisionner MongoDB Atlas (M10, eu-west-1)
3. Provisionner Redis Cloud (250MB, eu-west-1)
4. Valider déploiement : `python test_production_pipeline.py`

**Cette semaine :**
5. Monitoring 24/7 : `python monitor_production.py`
6. Backup automatique
7. Alertes Telegram

### Backend Dev

**Aujourd'hui :**
1. Finaliser client LNBits v2 (endpoints manquants)
2. Tests unitaires heuristiques (> 90% coverage)
3. Intégrer fallback_manager dans l'app

**Cette semaine :**
4. Tests d'intégration complets
5. Optimisation performance (cache, pools)
6. Documentation API

### Product Owner

**Aujourd'hui :**
1. Validation des seuils de décision (`config/decision_thresholds.yaml`)
2. Review des heuristiques implémentées
3. Planification Shadow Mode (21 jours)

**Cette semaine :**
4. Sélection nœuds pour tests pilotes
5. Critères de validation experts
6. Communication stakeholders

---

## 📞 SUPPORT & RESSOURCES

### Documentation Externe

- **Lightning Network** : https://lightning.engineering/
- **LNBits** : https://lnbits.com/
- **Amboss** : https://amboss.space/
- **MongoDB Atlas** : https://cloud.mongodb.com/
- **Redis Cloud** : https://redis.com/

### Contacts

- 📧 Email : support@dazno.de
- 💬 Telegram : @mcp_support
- 🐙 GitHub : https://github.com/yourusername/MCP

### Références Rapides

| Besoin | Document |
|--------|----------|
| Déployer maintenant | [DEPLOY_NOW.md](DEPLOY_NOW.md) |
| Comprendre l'architecture | [docs/backbone-technique-MVP.md](docs/backbone-technique-MVP.md) |
| Voir la roadmap | [_SPECS/Roadmap-Production-v1.0.md](_SPECS/Roadmap-Production-v1.0.md) |
| Status actuel | [IMPLEMENTATION_PHASE1_STATUS.md](IMPLEMENTATION_PHASE1_STATUS.md) |
| Troubleshooting | [DEPLOY_NOW.md](DEPLOY_NOW.md#-troubleshooting) |

---

## ✅ CHECKLIST RAPIDE

### Avant de Commencer
- [ ] Accès SSH au serveur (147.79.101.32)
- [ ] Accès sudo
- [ ] Domaine configuré (api.dazno.de)
- [ ] .env configuré avec credentials
- [ ] Documentation lue

### Déploiement
- [ ] `sudo ./scripts/deploy_all.sh` exécuté
- [ ] MongoDB Atlas provisionné
- [ ] Redis Cloud provisionné
- [ ] API répond (HTTP + HTTPS)
- [ ] Tests passent (> 80%)

### Validation
- [ ] Services actifs (nginx, mcp-api)
- [ ] Monitoring lancé
- [ ] Alertes configurées
- [ ] Logs propres
- [ ] Documentation à jour

---

## 🎉 QUICK WINS

### Déploiement en 3 Commandes

```bash
# 1. Se connecter
ssh feustey@147.79.101.32

# 2. Aller au projet
cd /home/feustey/mcp-production

# 3. Déployer !
sudo ./scripts/deploy_all.sh
```

**C'est tout !** ✨

---

**Version** : 1.0.0  
**Dernière mise à jour** : 13 octobre 2025, 20:00 UTC  
**Auteur** : MCP Team  
**Status** : ✅ Production Ready

---

*Pour toute question, consulter [DEPLOY_NOW.md](DEPLOY_NOW.md) ou la [Roadmap](_SPECS/Roadmap-Production-v1.0.md)*
