# Phase 2 - Next Steps & TODOs

## ✅ Complété (100%)

Toutes les tâches P2 sont terminées :

- ✅ P2.1.1 - Client LNBits Complet
- ✅ P2.1.2 - Authentification Macaroon
- ✅ P2.1.3 - Exécution Policies Réelles
- ✅ P2.2.1 - Heuristiques Avancées (8 modules)
- ✅ P2.2.2 - Decision Engine
- ✅ P2.2.3 - Système Rollback
- ✅ P2.3.1 - Lightning Scoring Service (API)
- ✅ P2.3.2 - Intégration Données Réseau

---

## 🔜 TODOs avant Phase 3 (Production Contrôlée)

### 1. Tests ⚠️ PRIORITAIRE

#### Tests unitaires (estimé: 2-3 jours)
- [ ] Tests pour chaque heuristique (8 modules)
  - `test_centrality.py`
  - `test_liquidity.py`
  - `test_activity.py`
  - `test_competitiveness.py`
  - `test_reliability.py`
  - `test_age_stability.py`
  - `test_peer_quality.py`
  - `test_network_position.py`

- [ ] Tests DecisionEngine
  - Test calcul composite score
  - Test détermination décisions (5 types)
  - Test batch evaluation
  - Test profils (conservative/aggressive/balanced)

- [ ] Tests PolicyValidator
  - Test limites sécurité
  - Test rate limiting
  - Test cooldowns
  - Test blacklist
  - Test validation rebalance

- [ ] Tests PolicyExecutor
  - Test dry-run vs real
  - Test retry logic
  - Test batch execution
  - Test intégration transaction manager

#### Tests d'intégration (estimé: 1-2 jours)
- [x] Test général (`test_phase2_integration.py`)
- [ ] Test workflow complet end-to-end
- [ ] Test rollback automatique avec vraies métriques
- [ ] Test sync network graph avec LNBits réel

#### Tests de charge (estimé: 1 jour)
- [ ] Load test API scoring (`/scores/node/{id}`)
- [ ] Load test API rankings
- [ ] Load test batch scoring
- [ ] Identifier bottlenecks

**Target**: >85% code coverage

---

### 2. Configuration Production ⚠️ CRITIQUE

#### Variables d'environnement
- [ ] Créer `.env.production` avec valeurs réelles
  ```bash
  LNBITS_URL=https://your-production-lnbits.com
  LNBITS_API_KEY=<secret>
  MACAROON_ENCRYPTION_KEY=<generated>
  MONGODB_URI=mongodb+srv://...
  REDIS_URL=redis://...
  ```

- [ ] Configurer rotation des secrets
- [ ] Setup vault pour secrets (optionnel)

#### Decision Thresholds
- [ ] Calibrer poids des heuristiques avec données réelles
- [ ] Ajuster thresholds basés sur statistiques réseau
- [ ] Créer profil custom pour votre nœud
- [ ] Tester profils conservative/aggressive

#### Safety Limits
- [ ] Vérifier limites de frais (max 1% = 10000 ppm ?)
- [ ] Ajuster cooldowns (actuellement 60 min)
- [ ] Ajouter canaux critiques à blacklist
- [ ] Définir limites de rebalance

---

### 3. Monitoring & Observabilité (estimé: 2-3 jours)

#### Logging
- [ ] Configurer structured logging (JSON)
- [ ] Setup log rotation
- [ ] Centraliser logs (ELK ou Loki)
- [ ] Définir niveaux par environnement (DEBUG dev, INFO prod)

#### Métriques Prometheus
- [ ] Instrumenter avec `prometheus_client`
  - Compteur décisions par type
  - Histogram latence API
  - Gauge nombre transactions actives
  - Compteur rollbacks
- [ ] Créer dashboards Grafana
- [ ] Setup alertes (Alertmanager)

#### Healthchecks
- [ ] Endpoint `/health` pour k8s/docker
- [ ] Vérifier connectivité LNBits
- [ ] Vérifier connectivité MongoDB
- [ ] Vérifier état graphe network

---

### 4. Documentation (estimé: 1-2 jours)

#### API Documentation
- [ ] Compléter docstrings OpenAPI dans `lightning_scoring.py`
- [ ] Ajouter exemples de requêtes/réponses
- [ ] Documenter codes d'erreur
- [ ] Créer Postman collection

#### User Guides
- [ ] Guide configuration pour operators
- [ ] Guide troubleshooting (FAQ)
- [ ] Guide rollback manuel
- [ ] Vidéo démo (optionnel)

#### Architecture
- [ ] Diagrammes de séquence (mermaid)
- [ ] Schéma d'architecture
- [ ] Documentation décisions techniques (ADR)

---

### 5. Sécurité (estimé: 1 jour)

#### Audit
- [ ] Review permissions fichiers (backups, configs)
- [ ] Vérifier pas de secrets hardcodés
- [ ] Scan vulnérabilités dépendances (`safety check`)
- [ ] Audit logs sensibles

#### Hardening
- [ ] Rate limiting API (actuellement 100/min LNBits, mais pas API REST)
- [ ] Authentication API REST (JWT ou API keys)
- [ ] HTTPS obligatoire en production
- [ ] CORS configuration

---

### 6. Intégrations manquantes (optionnel)

#### Notifications
- [ ] Intégrer Telegram bot pour alertes
- [ ] Webhooks pour événements critiques
- [ ] Email notifications (rollbacks, erreurs)

#### Monitoring externe
- [ ] Intégration Amboss API (reputation scores)
- [ ] Intégration 1ML API (network stats)
- [ ] Intégration Mempool API (fees BTC)

#### Rebalancing
- [ ] Implémenter circular rebalance via LNBits
- [ ] Support Balance of Satoshis (bos)
- [ ] Intégration Lightning Loop (submarine swaps)

---

### 7. Performance (estimé: 1-2 jours)

#### Optimisations
- [ ] Cache Redis pour scores (TTL 5 min)
- [ ] Index MongoDB optimisés
- [ ] Batch queries plutôt que N+1
- [ ] Async partout (vérifier)

#### Scalabilité
- [ ] Workers Celery pour calculs lourds
- [ ] Queue système pour jobs background
- [ ] Sharding MongoDB si gros volume
- [ ] CDN pour assets statiques (optionnel)

---

### 8. Infrastructure (estimé: 2-3 jours)

#### Docker
- [ ] Dockerfile optimisé (multi-stage)
- [ ] docker-compose.prod.yml complet
- [ ] Health checks dans compose
- [ ] Volumes pour persistence

#### CI/CD
- [ ] Pipeline GitHub Actions
  - Linting (flake8, black)
  - Tests unitaires
  - Tests intégration
  - Build Docker
  - Deploy staging
- [ ] Rollback automatique si tests fail

#### Deployment
- [ ] Script deploy production
- [ ] Backup avant deploy
- [ ] Zero-downtime deployment
- [ ] Post-deploy checks

---

## 🎯 Priorisation recommandée

### Sprint 1 (3-5 jours) - CRITIQUE ⚠️
1. Tests unitaires (heuristiques + decision engine)
2. Configuration production (.env, thresholds)
3. Sécurité (audit, secrets)

### Sprint 2 (3-5 jours) - IMPORTANT 🔶
1. Monitoring (Prometheus, Grafana, logs)
2. Tests d'intégration + charge
3. Documentation API

### Sprint 3 (2-3 jours) - NICE TO HAVE 🟢
1. Notifications (Telegram)
2. Performance optimisations
3. Infrastructure (CI/CD)

---

## 📊 Estimation totale

- **Travail restant** : ~10-15 jours (1 personne)
- **Critique** : ~5 jours
- **Important** : ~5 jours
- **Optionnel** : ~5 jours

---

## 🚦 Checklist "Production Ready"

Cocher avant passage en Phase 3 (Shadow Mode) :

### Minimum Viable
- [ ] Tests unitaires >80% coverage
- [ ] Configuration production validée
- [ ] Secrets sécurisés
- [ ] Logging structuré
- [ ] Healthchecks fonctionnels
- [ ] Documentation API complète
- [ ] Rollback testé manuellement

### Recommandé
- [ ] Tests charge passés
- [ ] Monitoring Prometheus actif
- [ ] Dashboards Grafana créés
- [ ] Alertes configurées
- [ ] CI/CD pipeline setup
- [ ] Backup automatique configuré
- [ ] Rate limiting API activé

### Nice to Have
- [ ] Notifications Telegram
- [ ] Cache Redis actif
- [ ] Workers Celery
- [ ] Intégrations externes (Amboss, etc.)

---

## 📅 Timeline suggérée

| Semaine | Focus | Livrables |
|---------|-------|-----------|
| S+0 | Tests + Config | Tests unitaires, .env.prod |
| S+1 | Monitoring + Docs | Prometheus, Grafana, API docs |
| S+2 | Sécurité + Infra | Audit, CI/CD, Docker |
| S+3 | Shadow Mode | Déploiement Phase 3 |

---

**Dernière mise à jour** : 15 octobre 2025

