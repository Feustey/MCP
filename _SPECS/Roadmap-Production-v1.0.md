# Spécifications MCP v1.0 - Roadmap vers Production Stable
> Dernière mise à jour: 12 octobre 2025
> Version: 1.0.0-prod
> Auteur: Équipe MCP

---

## 📋 TABLE DES MATIÈRES

1. [Vue d'ensemble](#vue-densemble)
2. [Priorité 1 - Infrastructure Stable](#priorité-1---infrastructure-stable)
3. [Priorité 2 - Core Engine Complet](#priorité-2---core-engine-complet)
4. [Priorité 3 - Production Contrôlée](#priorité-3---production-contrôlée)
5. [Priorité 4 - Fonctionnalités Avancées](#priorité-4---fonctionnalités-avancées)
6. [Timeline & Ressources](#timeline--ressources)
7. [Critères de Succès](#critères-de-succès)
8. [Annexes](#annexes)

---

## VUE D'ENSEMBLE

### Contexte

MCP (Model Context Protocol) est un système d'optimisation autonome pour nœuds Lightning Network. Suite à la résolution des 828 failures et à la stabilisation de l'API en production (octobre 2025), cette spécification définit la roadmap vers une version 1.0 production-ready.

### Périmètre V1.0

**Inclus** :
- Infrastructure cloud-native stable
- Core Engine d'optimisation de fees complet
- Intégrations Lightning réelles (LNBits, LND)
- Mode Shadow validé et production contrôlée
- Monitoring et observabilité complets
- APIs et services avancés (RAG, Scoring)

**Exclu (reporté en V2)** :
- Packaging Umbrel
- Installation locale-first
- Distribution app store Umbrel

### Objectifs Principaux

1. **Stabilité** : 99% uptime, 0 failures critiques
2. **Fonctionnalité** : Core Engine 100% opérationnel avec LND/LNBits réels
3. **Performance** : < 500ms response time, cache optimisé
4. **Observabilité** : Monitoring complet, métriques temps réel
5. **Sécurité** : Authentification, chiffrement, isolation données

---

## PRIORITÉ 1 - INFRASTRUCTURE STABLE

> **Durée estimée** : 1-2 semaines  
> **Criticité** : 🔴 CRITIQUE  
> **Dépendances** : Aucune

### 1.1 Configuration Serveur Production

#### Objectif
Finaliser la configuration de l'infrastructure serveur pour un déploiement stable et automatisé.

#### Tâches

**1.1.1 Configuration Nginx avec HTTPS**

```yaml
Responsable: DevOps
Durée: 2 heures
Prérequis: Accès sudo sur serveur production

Actions:
  - Exécuter script configure_nginx_production.sh
  - Configurer reverse proxy port 80/443 → 8000
  - Installer certificat SSL Let's Encrypt
  - Tester accès https://api.dazno.de/

Critères de succès:
  - ✅ API accessible via HTTPS
  - ✅ Certificat SSL valide (A+ SSL Labs)
  - ✅ Redirection HTTP → HTTPS automatique
  - ✅ Headers sécurité (HSTS, CSP, etc.)

Fichiers:
  - scripts/configure_nginx_production.sh
  - nginx-simple.conf (template existant)
```

**1.1.2 Service Systemd avec Auto-restart**

```yaml
Responsable: DevOps
Durée: 1 heure
Prérequis: Configuration nginx terminée

Actions:
  - Exécuter script configure_systemd_autostart.sh
  - Créer service mcp-api.service
  - Activer auto-start au boot
  - Configurer restart automatique sur crash

Critères de succès:
  - ✅ Service démarre automatiquement au boot
  - ✅ Restart automatique en cas de crash (< 10s)
  - ✅ Logs systemd accessibles (journalctl)
  - ✅ Status vérifiable (systemctl status mcp-api)

Fichiers:
  - scripts/configure_systemd_autostart.sh
  - /etc/systemd/system/mcp-api.service
  - /home/feustey/mcp-production/start_api.sh
```

**1.1.3 Monitoring Infrastructure**

```yaml
Responsable: DevOps
Durée: 3 heures
Prérequis: Service systemd configuré

Actions:
  - Adapter monitoring pour endpoint / au lieu de /health
  - Configurer alertes Telegram pour service down
  - Implémenter healthcheck avancé systemd
  - Logs rotation et archivage

Critères de succès:
  - ✅ Monitoring détecte correctement l'état API
  - ✅ Alertes envoyées en < 2 min si service down
  - ✅ Logs rotationnés quotidiennement
  - ✅ Historique monitoring persistant (> 30 jours)

Fichiers:
  - monitor_production.py (modifier endpoint)
  - logs/ (configuration rotation)
```

### 1.2 Reconstruction Image Docker

#### Objectif
Créer une image Docker stable et optimisée pour remplacer l'image défectueuse actuelle.

#### Problèmes Actuels
- ❌ Image `feustey/mcp-dazno:latest` crashloop
- ❌ Entrypoint cassé
- ❌ Dépendances manquantes (pandas, numpy)
- ❌ Structure modules incorrecte

#### Tâches

**1.2.1 Audit et Nettoyage Dockerfile**

```yaml
Responsable: Backend Dev
Durée: 1 jour
Prérequis: Accès au code source

Actions:
  - Auditer Dockerfile existant
  - Identifier dépendances manquantes
  - Vérifier structure PYTHONPATH
  - Créer Dockerfile.production propre

Critères de succès:
  - ✅ Build local réussi
  - ✅ Container démarre sans erreur
  - ✅ Healthcheck intégré fonctionnel
  - ✅ Taille image < 1GB

Dépendances à inclure:
  fastapi>=0.104.0
  uvicorn[standard]>=0.24.0
  pydantic>=2.5.0
  pydantic-settings>=2.1.0
  httpx>=0.25.0
  pandas>=2.1.0
  numpy>=1.24.0
  redis>=5.0.0
  pymongo>=4.5.0
  anthropic>=0.7.0
  qdrant-client>=1.7.0
  structlog>=23.2.0
  
Fichiers:
  - Dockerfile.production (nouveau)
  - requirements-production.txt (minimal)
  - docker_entrypoint.sh (corrigé)
```

**1.2.2 Build et Tests Image**

```yaml
Responsable: Backend Dev
Durée: 1 jour
Prérequis: Dockerfile.production créé

Actions:
  - Builder image localement
  - Tests unitaires dans container
  - Tests d'intégration complets
  - Push vers registry (DockerHub ou GCP)

Critères de succès:
  - ✅ Image build en < 10 min
  - ✅ Tous tests passent (100%)
  - ✅ Healthcheck respond < 1s
  - ✅ Memory footprint < 500MB

Commandes:
  docker build -t mcp-api:1.0.0 -f Dockerfile.production .
  docker run --rm mcp-api:1.0.0 pytest tests/
  docker push registry.example.com/mcp-api:1.0.0

Fichiers:
  - Dockerfile.production
  - docker-compose.production.yml (mise à jour)
```

**1.2.3 Déploiement Image Production**

```yaml
Responsable: DevOps
Durée: 2 heures
Prérequis: Image testée et pushée

Actions:
  - Mettre à jour docker-compose.production.yml
  - Déployer nouvelle image sur serveur
  - Migration sans downtime (blue/green)
  - Validation post-déploiement

Critères de succès:
  - ✅ Déploiement sans downtime
  - ✅ Rollback possible en < 1 min
  - ✅ Logs propres (no errors)
  - ✅ Monitoring confirme healthy

Fichiers:
  - docker-compose.production.yml
  - scripts/deploy_docker_production.sh (nouveau)
```

### 1.3 Activation Services Cloud

#### Objectif
Connecter les services cloud réels (MongoDB, Redis) pour sortir du mode dégradé.

#### Tâches

**1.3.1 Configuration MongoDB Atlas**

```yaml
Responsable: Backend Dev
Durée: 4 heures
Prérequis: Compte MongoDB Atlas provisionné

Actions:
  - Créer cluster production MongoDB Atlas
  - Configurer network access et whitelisting
  - Générer connection string sécurisée
  - Créer collections et indexes

Critères de succès:
  - ✅ Connexion stable (< 50ms latency)
  - ✅ Indexes optimisés créés
  - ✅ Backup automatique configuré (daily)
  - ✅ Monitoring Atlas actif

Configuration:
  Tier: M10 (Production, 2GB RAM)
  Region: eu-west-1 (Frankfurt)
  Backup: Daily snapshots, 7 jours retention
  
Collections:
  - nodes (index: node_id, created_at)
  - channels (index: channel_id, node_id, created_at)
  - policies (index: channel_id, applied_at)
  - metrics (index: node_id, timestamp)
  - decisions (index: node_id, decision_type, created_at)

Variables .env:
  MONGODB_URL=mongodb+srv://user:pass@cluster.mongodb.net/mcp_prod
  MONGODB_DATABASE=mcp_prod
  MONGODB_CONNECTION_POOL_SIZE=50
  MONGODB_TIMEOUT_MS=5000
```

**1.3.2 Configuration Redis Cloud**

```yaml
Responsable: Backend Dev
Durée: 3 heures
Prérequis: Compte Redis Cloud ou Upstash

Actions:
  - Provisionner instance Redis Cloud
  - Configurer TLS et authentification
  - Implémenter cache layer dans app
  - Tests de performance cache

Critères de succès:
  - ✅ Latency < 10ms (p95)
  - ✅ Hit rate > 80% après warm-up
  - ✅ TTL configurés par type de donnée
  - ✅ Eviction policy configurée (LRU)

Configuration:
  Provider: Redis Cloud / Upstash
  Tier: 250MB RAM
  Region: eu-west-1
  TLS: Enabled
  
Cache Strategy:
  - Node data: TTL 5 min
  - Channel data: TTL 10 min
  - Metrics: TTL 1 min
  - Scores: TTL 15 min
  - Heavy queries: TTL 30 min

Variables .env:
  REDIS_URL=rediss://default:pass@redis-cluster.cloud.redislabs.com:6379
  REDIS_MAX_CONNECTIONS=50
  REDIS_TIMEOUT=5
```

**1.3.3 Gestion Mode Dégradé**

```yaml
Responsable: Backend Dev
Durée: 1 jour
Prérequis: MongoDB et Redis configurés

Actions:
  - Implémenter fallback gracieux
  - Circuit breaker pour services externes
  - Mode dégradé si service indisponible
  - Tests de résilience

Critères de succès:
  - ✅ API fonctionne si Redis down
  - ✅ API fonctionne si MongoDB down
  - ✅ Dégradation progressive, pas de crash
  - ✅ Alertes envoyées si mode dégradé

Implémentation:
  - Circuit breaker: 5 failures → open (30s)
  - Fallback MongoDB: Logs en fichier
  - Fallback Redis: No cache (direct queries)
  - Health endpoint reflète l'état dégradé

Fichiers:
  - src/tools/circuit_breaker.py (existant)
  - app/services/fallback_manager.py (nouveau)
```

---

## PRIORITÉ 2 - CORE ENGINE COMPLET

> **Durée estimée** : 2-3 semaines  
> **Criticité** : 🔴 CRITIQUE  
> **Dépendances** : Priorité 1 terminée

### 2.1 Intégration LNBits Réelle

#### Objectif
Remplacer les mocks par une intégration complète avec LNBits pour l'exécution réelle des policies de fees.

#### Tâches

**2.1.1 Client LNBits Complet**

```yaml
Responsable: Backend Dev
Durée: 3 jours
Prérequis: Accès LNBits instance production

Actions:
  - Finaliser src/clients/lnbits_client.py
  - Implémenter tous les endpoints nécessaires
  - Authentification macaroon complète
  - Gestion erreurs et retry logic

Endpoints requis:
  GET /api/v1/wallet
  GET /api/v1/payments
  POST /api/v1/payments
  GET /lightning/api/v1/channels
  POST /lightning/api/v1/channel_policy
  GET /lightning/api/v1/node_info

Critères de succès:
  - ✅ Tous endpoints implémentés et testés
  - ✅ Authentification macaroon fonctionnelle
  - ✅ Rate limiting respecté (100 req/min)
  - ✅ Retry automatique (3x avec backoff)
  - ✅ Timeouts configurables
  - ✅ Tests unitaires > 90% coverage

Fichiers:
  - src/clients/lnbits_client.py (compléter)
  - tests/test_lnbits_client.py (nouveau)
  - config.py (ajouter LNBits config)
```

**2.1.2 Authentification Macaroon**

```yaml
Responsable: Backend Dev
Durée: 2 jours
Prérequis: Client LNBits implémenté

Actions:
  - Implémenter génération macaroon
  - Gestion sécurisée des credentials
  - Rotation automatique des tokens
  - Validation et refresh

Critères de succès:
  - ✅ Macaroons stockés chiffrés
  - ✅ Rotation automatique (30 jours)
  - ✅ Révocation possible
  - ✅ Logs audit des accès

Sécurité:
  - Chiffrement: AES-256-GCM
  - Storage: MongoDB (encrypted field)
  - Rotation: Automatique tous les 30j
  - Permissions: Read-only par défaut

Variables .env:
  LNBITS_URL=https://lnbits.example.com
  LNBITS_ADMIN_KEY=encrypted_key_here
  LNBITS_INVOICE_KEY=encrypted_key_here
  MACAROON_ENCRYPTION_KEY=32_bytes_random_key
  MACAROON_ROTATION_DAYS=30

Fichiers:
  - src/auth/macaroon_manager.py (nouveau)
  - src/auth/encryption.py (nouveau)
```

**2.1.3 Exécution Policies Réelles**

```yaml
Responsable: Backend Dev
Durée: 3 jours
Prérequis: LNBits client et auth fonctionnels

Actions:
  - Compléter src/tools/optimize_and_execute.py
  - Implémenter apply_policy() réel
  - Validation avant application
  - Rollback automatique si échec

Workflow:
  1. Génération recommandation par optimizer
  2. Validation règles business
  3. Dry-run simulation
  4. Backup policy actuelle
  5. Application via LNBits API
  6. Vérification post-application
  7. Rollback si échec

Critères de succès:
  - ✅ Application policy réussie (100%)
  - ✅ Backup automatique avant chaque change
  - ✅ Rollback fonctionnel en < 30s
  - ✅ Logs détaillés de chaque action
  - ✅ Notifications Telegram pour chaque change

Sécurité:
  - Mode dry-run par défaut
  - Confirmation manuelle pour prod (v1.0)
  - Limites: max 5 changes/jour par canal
  - Blacklist canaux critiques

Fichiers:
  - src/tools/optimize_and_execute.py (compléter)
  - src/optimizers/policy_validator.py (nouveau)
  - src/tools/rollback_manager.py (nouveau)
```

### 2.2 Core Fee Optimizer

#### Objectif
Finaliser le moteur d'optimisation des fees avec heuristiques complètes et production-ready.

#### Tâches

**2.2.1 Heuristiques Avancées**

```yaml
Responsable: Backend Dev + Data Analyst
Durée: 1 semaine
Prérequis: Données réelles disponibles

Actions:
  - Implémenter toutes les heuristiques définies
  - Calibration des poids sur données historiques
  - Tests A/B sur simulations
  - Documentation algorithmes

Heuristiques implémentées:
  1. Centrality Score (betweenness, closeness)
  2. Liquidity Balance (local/remote ratio)
  3. Forward Activity (success rate, volume)
  4. Fee Competitiveness (vs network median)
  5. Uptime & Reliability
  6. Age & Stability
  7. Peer Quality Score
  8. Network Position (hub vs edge)

Pondérations par défaut:
  centrality: 0.20
  liquidity: 0.25
  activity: 0.20
  competitiveness: 0.15
  reliability: 0.10
  age: 0.05
  peer_quality: 0.03
  position: 0.02

Critères de succès:
  - ✅ Toutes heuristiques implémentées
  - ✅ Tests unitaires > 95% coverage
  - ✅ Calibration sur > 1000 canaux
  - ✅ Performance < 100ms par canal
  - ✅ Documentation complète algorithmes

Fichiers:
  - src/optimizers/core_fee_optimizer.py (améliorer)
  - src/optimizers/heuristics/ (nouveau dossier)
    - centrality.py
    - liquidity.py
    - activity.py
    - competitiveness.py
    - reliability.py
  - docs/heuristics-specification.md (nouveau)
```

**2.2.2 Decision Engine**

```yaml
Responsable: Backend Dev
Durée: 3 jours
Prérequis: Heuristiques implémentées

Actions:
  - Fonction pure evaluate_channel()
  - Règles de décision claires
  - Thresholds configurables
  - Logs explicites pour chaque décision

Types de décisions:
  NO_ACTION: Score optimal (0.7-1.0)
  INCREASE_FEES: Sous-utilisé (score < 0.3)
  DECREASE_FEES: Sur-pricé (score 0.3-0.5, low activity)
  REBALANCE: Déséquilibré (local/remote > 0.8 ou < 0.2)
  CLOSE_CHANNEL: Mort (score < 0.1, no activity 30d)

Thresholds configurables:
  optimal_min: 0.7
  increase_threshold: 0.3
  decrease_threshold: 0.5
  rebalance_ratio_max: 0.8
  rebalance_ratio_min: 0.2
  close_threshold: 0.1
  close_inactivity_days: 30

Critères de succès:
  - ✅ Fonction pure, déterministe
  - ✅ Logs explicites (pourquoi cette décision)
  - ✅ Tests avec cas limites
  - ✅ Performance < 50ms

Fichiers:
  - src/optimizers/decision_engine.py (nouveau)
  - config/decision_thresholds.yaml (nouveau)
  - tests/test_decision_engine.py (nouveau)
```

**2.2.3 Système de Rollback Transactionnel**

```yaml
Responsable: Backend Dev
Durée: 2 jours
Prérequis: Decision engine implémenté

Actions:
  - Backup automatique avant action
  - Transaction log détaillé
  - Rollback manuel et automatique
  - Tests de recovery

Workflow backup:
  1. Snapshot policy actuelle
  2. Store dans MongoDB (collection: policy_backups)
  3. Référence dans decision log
  4. Retention: 90 jours

Rollback automatique si:
  - Échec application policy
  - Error rate spike (> 50% en 5 min)
  - Latency spike (> 2x normale)
  - Manual trigger via API

Critères de succès:
  - ✅ Backup avant chaque change (100%)
  - ✅ Rollback réussi < 30s
  - ✅ Tests de recovery passent
  - ✅ Historique complet traçable

Fichiers:
  - src/tools/rollback_manager.py (améliorer)
  - src/tools/transaction_log.py (nouveau)
```

### 2.3 Lightning Scoring Service

#### Objectif
Activer le système de scoring multicritère pour les nœuds et canaux du réseau Lightning.

#### Tâches

**2.3.1 Intégration Service de Scoring**

```yaml
Responsable: Backend Dev
Durée: 1 semaine
Prérequis: Core optimizer finalisé

Actions:
  - Activer app/services/lightning_scoring.py
  - Endpoints API /api/v1/lightning/scores/
  - Calculs centrality, reliability, performance
  - Cache résultats scoring

Endpoints:
  GET /api/v1/lightning/scores/node/{node_id}
  GET /api/v1/lightning/scores/channel/{channel_id}
  POST /api/v1/lightning/scores/batch
  GET /api/v1/lightning/scores/rankings

Métriques calculées:
  - Node centrality (betweenness, closeness, eigenvector)
  - Node reliability (uptime, success rate, reputation)
  - Channel performance (forward success, fees earned, volume)
  - Channel health (balance, age, activity)

Critères de succès:
  - ✅ Tous endpoints fonctionnels
  - ✅ Cache Redis hit rate > 80%
  - ✅ Response time < 200ms (cached)
  - ✅ Response time < 2s (uncached)
  - ✅ Tests unitaires > 90% coverage

Fichiers:
  - app/services/lightning_scoring.py (activer)
  - app/routes/lightning_scoring.py (nouveau)
  - tests/test_lightning_scoring.py (nouveau)
```

**2.3.2 Intégration Données Réseau**

```yaml
Responsable: Backend Dev
Durée: 3 jours
Prérequis: Scoring service actif

Actions:
  - Sync graph Lightning Network
  - Calculs topologie (NetworkX)
  - Update périodique (cron 6h)
  - Métriques réseau global

Sources de données:
  - Lightning Network Graph (via LND gossip)
  - Amboss API (node stats)
  - 1ML API (rankings)
  - Mempool.space (on-chain data)

Métriques réseau calculées:
  - Total nodes, total channels
  - Network capacity, median channel size
  - Average node degree, clustering coefficient
  - Top hubs (centrality rankings)

Critères de succès:
  - ✅ Graph sync < 5 min
  - ✅ Calculs topologie < 10 min
  - ✅ Update automatique 4x/jour
  - ✅ Métriques persistées MongoDB

Fichiers:
  - src/scanners/network_graph_scanner.py (nouveau)
  - src/analysis/network_topology.py (nouveau)
  - scripts/sync_network_graph.py (nouveau)
```

---

## PRIORITÉ 3 - PRODUCTION CONTRÔLÉE

> **Durée estimée** : 3-4 semaines  
> **Criticité** : 🟡 HAUTE  
> **Dépendances** : Priorité 1 & 2 terminées

### 3.1 Shadow Mode Extended

#### Objectif
Observer le système en mode "observation only" pendant 14-21 jours minimum avant activation réelle.

#### Tâches

**3.1.1 Configuration Shadow Mode**

```yaml
Responsable: Backend Dev + DevOps
Durée: 2 jours
Prérequis: Core engine complet

Actions:
  - Activer mode DRY_RUN=true par défaut
  - Logging détaillé de toutes les recommandations
  - Comparaison recommandations vs actions manuelles
  - Dashboard visualisation décisions

Configuration:
  DRY_RUN=true  # Aucune action réelle
  LOG_LEVEL=DEBUG
  SHADOW_MODE_ENABLED=true
  SHADOW_MODE_LOG_ALL_DECISIONS=true

Logs à capturer:
  - Recommandations générées
  - Score de chaque canal
  - Décision suggérée (avec raison)
  - État actuel vs état recommandé
  - Timestamp et contexte

Critères de succès:
  - ✅ Aucune action réelle exécutée
  - ✅ 100% des recommandations loggées
  - ✅ Dashboard temps réel fonctionnel
  - ✅ Export quotidien des rapports

Fichiers:
  - config.py (ajouter SHADOW_MODE flag)
  - src/tools/shadow_mode_logger.py (nouveau)
  - app/routes/shadow_dashboard.py (nouveau)
```

**3.1.2 Collecte et Analyse Métriques**

```yaml
Responsable: Data Analyst + Backend Dev
Durée: Continu (14-21 jours)
Prérequis: Shadow mode actif

Actions:
  - Collection quotidienne métriques
  - Analyse recommandations vs réalité
  - Identification patterns et anomalies
  - Ajustement heuristiques si nécessaire

Métriques à tracker:
  - Nombre de recommandations par type
  - Distribution des scores
  - Canaux concernés (IDs et stats)
  - Timing des recommandations
  - Corrélation avec events réseau

Analyses quotidiennes:
  - Recommandations alignées avec intuition?
  - Faux positifs / faux négatifs
  - Cas limites identifiés
  - Performance des heuristiques

Critères de succès:
  - ✅ Rapport quotidien généré automatiquement
  - ✅ Taux de faux positifs < 10%
  - ✅ Recommandations "sensées" > 90%
  - ✅ Pas de recommandations aberrantes

Fichiers:
  - scripts/daily_shadow_report.py (nouveau)
  - data/reports/shadow_mode/ (nouveau dossier)
  - docs/shadow-mode-analysis.md (mis à jour quotidien)
```

**3.1.3 Validation avec Experts**

```yaml
Responsable: Product Owner + Node Operators
Durée: 1 semaine (fin de shadow mode)
Prérequis: 14+ jours de données shadow

Actions:
  - Review échantillon de recommandations
  - Comparaison avec décisions manuelles
  - Identification cas à améliorer
  - Validation globale système

Review process:
  - Sélection aléatoire 100 recommandations
  - Évaluation par expert: Agree/Disagree/Unsure
  - Discussion cas de désaccord
  - Ajustement thresholds si nécessaire

Critères d'acceptation:
  - ✅ Agreement rate > 80%
  - ✅ Aucun cas critique manqué
  - ✅ Pas de recommandations dangereuses
  - ✅ Green light pour phase suivante

Fichiers:
  - docs/shadow-mode-validation-report.md (nouveau)
```

### 3.2 Tests avec Nœud Réel

#### Objectif
Valider le système avec un vrai nœud Lightning en conditions réelles.

#### Tâches

**3.2.1 Setup Nœud de Test**

```yaml
Responsable: DevOps + Node Operator
Durée: 2 jours
Prérequis: Shadow mode validé

Actions:
  - Sélection nœud de test (non-critique)
  - Configuration connexion LND/LNBits
  - Isolation du nœud (pas de impact prod)
  - Backup complet de l'état initial

Critères de sélection nœud:
  - Non-critique (pas de routing majeur)
  - Capacité modeste (< 5M sats)
  - Quelques canaux actifs (5-10)
  - Possibilité de rollback complet

Configuration:
  NODE_ID=03abc...
  NODE_TYPE=lnd
  LND_REST_URL=https://node-test.example.com:8080
  LNBITS_URL=https://lnbits-test.example.com
  TEST_MODE=true  # Restrictions supplémentaires

Critères de succès:
  - ✅ Connexion établie et vérifiée
  - ✅ Backup complet effectué
  - ✅ Restrictions de sécurité actives
  - ✅ Monitoring dédié configuré

Fichiers:
  - config/node_test.yaml (nouveau)
  - scripts/backup_node_state.sh (nouveau)
```

**3.2.2 Test Pilote (1 Canal)**

```yaml
Responsable: Backend Dev + Node Operator
Durée: 1 semaine
Prérequis: Nœud de test configuré

Actions:
  - Activation sur 1 canal uniquement
  - Mode semi-automatique (confirmation manuelle)
  - Observation impact pendant 7 jours
  - Rollback si problème

Workflow:
  1. Sélection canal test (critères: faible volume)
  2. MCP génère recommandation
  3. Validation manuelle requise
  4. Application si approuvée
  5. Observation 48h minimum
  6. Mesure impact (forwards, fees earned)

Métriques à comparer (avant/après):
  - Forward success rate
  - Forward volume (sats/jour)
  - Fees earned (sats/jour)
  - Balance stability
  - Peer satisfaction (indirect)

Critères de succès:
  - ✅ Pas de dégradation performance
  - ✅ Amélioration >= 10% sur au moins 2 métriques
  - ✅ Aucun incident ou crash
  - ✅ Rollback fonctionnel si testé

Fichiers:
  - scripts/pilot_test_single_channel.py (nouveau)
  - data/reports/pilot_test/ (résultats)
```

**3.2.3 Expansion Progressive**

```yaml
Responsable: Node Operator
Durée: 2-3 semaines
Prérequis: Test pilote 1 canal réussi

Actions:
  - Expansion à 3 canaux (semaine 1)
  - Expansion à 5 canaux (semaine 2)
  - Expansion à tous canaux nœud test (semaine 3)
  - Évaluation globale

Progression:
  Week 1: 1 canal → 3 canaux (diversifiés)
  Week 2: 3 canaux → 5 canaux
  Week 3: 5 canaux → tous canaux (si ok)

Critères d'expansion:
  - Aucun incident sur phase précédente
  - Amélioration nette confirmée
  - Validation manuelle de chaque étape
  - Monitoring sans alertes critiques

Critères de succès (fin semaine 3):
  - ✅ Tous canaux sous MCP (ou rollback si échec)
  - ✅ Amélioration globale nœud > 15%
  - ✅ Aucun incident critique
  - ✅ Satisfaction node operator

Fichiers:
  - docs/pilot-expansion-report.md (hebdomadaire)
```

### 3.3 Activation Production Limitée

#### Objectif
Activer MCP sur un nombre limité de nœuds production avec garde-fous stricts.

#### Tâches

**3.3.1 Critères de Qualification Nœuds**

```yaml
Responsable: Product Owner
Durée: 1 jour
Prérequis: Tests pilotes concluants

Actions:
  - Définition critères qualification
  - Sélection premiers nœuds candidats
  - Validation par node operators
  - Onboarding et formation

Critères de qualification:
  - Nœud mature (> 6 mois)
  - Capacité modérée (1-10M sats)
  - Nombre canaux gérable (10-50)
  - Node operator expérimenté
  - Acceptation termes (beta, monitoring)

Liste d'attente:
  - Max 5 nœuds pour v1.0 initial
  - Diversité géographique et taille
  - Mix entre hubs et nœuds routeurs

Critères de succès:
  - ✅ Critères documentés et validés
  - ✅ 5 nœuds qualifiés et acceptant
  - ✅ Contrat/termes beta signés

Fichiers:
  - docs/node-qualification-criteria.md (nouveau)
  - data/qualified_nodes.yaml (nouveau)
```

**3.3.2 Mode Semi-Automatique**

```yaml
Responsable: Backend Dev
Durée: 3 jours
Prérequis: Nœuds qualifiés identifiés

Actions:
  - Implémentation workflow approbation
  - Interface confirmation node operator
  - Notifications avant chaque action
  - Timeout si pas de réponse (24h → skip)

Workflow approbation:
  1. MCP génère recommandation
  2. Notification Telegram à node operator
  3. Dashboard affiche détails + contexte
  4. Operator a 24h pour approuver/rejeter
  5. Si approuvé: exécution automatique
  6. Si rejeté: skip + feedback collecté
  7. Si timeout: skip (aucune action)

Interface:
  - Telegram bot avec boutons Approve/Reject
  - Dashboard web avec détails complets
  - Historique décisions passées
  - Feedback form si rejection

Critères de succès:
  - ✅ Workflow approbation fonctionnel
  - ✅ Notifications fiables (100%)
  - ✅ Interface intuitive (UX validée)
  - ✅ Aucune action sans confirmation

Fichiers:
  - src/approval/approval_workflow.py (nouveau)
  - app/routes/approval_dashboard.py (nouveau)
  - src/integrations/telegram_bot.py (améliorer)
```

**3.3.3 Monitoring et Alertes Avancées**

```yaml
Responsable: DevOps + Backend Dev
Durée: 1 semaine
Prérequis: Mode semi-auto implémenté

Actions:
  - Alertes multi-niveaux (info, warning, critical)
  - Dashboard temps réel par nœud
  - Détection anomalies automatique
  - Escalation si problème

Niveaux d'alertes:
  INFO: Action appliquée avec succès
  WARNING: Métrique inhabituelle (pas critique)
  CRITICAL: Dégradation performance, échec action
  
Alertes automatiques si:
  - Forward success rate drop > 20%
  - Fees earned drop > 30%
  - Error rate > 5%
  - Latency spike > 2x normale
  - Service unavailable

Canaux de notification:
  - Telegram (tous niveaux)
  - Email (warning + critical)
  - Slack (critical uniquement)
  - PagerDuty (critical + no response 15min)

Critères de succès:
  - ✅ Détection anomalie < 5 min
  - ✅ Notification < 2 min après détection
  - ✅ Dashboard temps réel fonctionnel
  - ✅ Escalation process testé

Fichiers:
  - src/monitoring/anomaly_detector.py (nouveau)
  - src/monitoring/alert_manager.py (améliorer)
  - app/routes/realtime_dashboard.py (nouveau)
```

---

## PRIORITÉ 4 - FONCTIONNALITÉS AVANCÉES

> **Durée estimée** : 4-6 semaines  
> **Criticité** : 🟢 MOYENNE  
> **Dépendances** : Priorité 3 réussie

### 4.1 Système RAG Lightning Complet

#### Objectif
Activer le système RAG (Retrieval-Augmented Generation) pour analyses contextuelles avancées.

#### Tâches

**4.1.1 Activation RAG Backend**

```yaml
Responsable: ML Engineer + Backend Dev
Durée: 1 semaine
Prérequis: Qdrant configuré, données disponibles

Actions:
  - Activer rag/ system complet
  - Configuration Qdrant vector store
  - Ingestion documents Lightning existants
  - Tests end-to-end RAG pipeline

Documents à ingérer:
  - Documentation Lightning Network (BOLT specs)
  - Analyses historiques nœuds
  - Best practices fee optimization
  - Rapports shadow mode
  - Données réseau agrégées

Pipeline RAG:
  1. Document chunking (512 tokens)
  2. Embedding génération (Anthropic/OpenAI)
  3. Indexation Qdrant
  4. Query expansion
  5. Retrieval (top-k=5)
  6. Reranking
  7. Context injection
  8. LLM generation

Critères de succès:
  - ✅ Qdrant healthy et performant
  - ✅ Documents indexés (> 1000)
  - ✅ Retrieval latency < 500ms
  - ✅ Relevance score > 0.8

Fichiers:
  - rag/ (activer tous modules)
  - rag/ingest_lightning_docs.py (nouveau)
  - config/rag_config.yaml (nouveau)
```

**4.1.2 Endpoints RAG API**

```yaml
Responsable: Backend Dev
Durée: 3 jours
Prérequis: RAG backend actif

Actions:
  - Créer endpoints /api/v1/rag/
  - Query Lightning Network knowledge
  - Analyses contextuelles nœuds/canaux
  - Recommandations enrichies par RAG

Endpoints:
  POST /api/v1/rag/query
    Body: {"query": "How to optimize fees for high-volume channel?"}
    Response: {"answer": "...", "sources": [...], "confidence": 0.95}
  
  POST /api/v1/rag/analyze/node/{node_id}
    Response: Analyse contextuelle complète du nœud
  
  POST /api/v1/rag/analyze/channel/{channel_id}
    Response: Recommandations enrichies RAG

Critères de succès:
  - ✅ Tous endpoints fonctionnels
  - ✅ Response time < 2s (p95)
  - ✅ Answers pertinentes (validation manuelle)
  - ✅ Sources tracées et vérifiables

Fichiers:
  - app/routes/rag.py (compléter)
  - app/services/rag_service.py (améliorer)
  - tests/test_rag_endpoints.py (nouveau)
```

**4.1.3 Intégration RAG dans Optimizer**

```yaml
Responsable: Backend Dev + ML Engineer
Durée: 1 semaine
Prérequis: Endpoints RAG fonctionnels

Actions:
  - Enrichir recommandations avec contexte RAG
  - Explications en langage naturel
  - Confidence scores améliorés
  - Comparaison avec best practices

Workflow enrichi:
  1. Optimizer génère recommandation (score)
  2. Query RAG avec contexte canal
  3. RAG enrichit avec best practices
  4. Génération explication claire
  5. Confidence score ajusté
  6. Retour recommandation + explication

Exemple output:
  {
    "channel_id": "...",
    "current_fee": 1000,
    "recommended_fee": 500,
    "confidence": 0.87,
    "reasoning": "Based on network data, channels with similar characteristics (high volume, reliable peer) perform better with lower fees. Your current fee is 2x the network median for comparable channels.",
    "sources": ["Network stats 2025-10", "Best practices doc"],
    "estimated_impact": "+25% forward volume"
  }

Critères de succès:
  - ✅ Explications claires et actionnables
  - ✅ Confidence scores calibrés
  - ✅ Sources vérifiables
  - ✅ Feedback positif node operators

Fichiers:
  - src/optimizers/rag_enriched_optimizer.py (nouveau)
```

### 4.2 Intégrations Externes Avancées

#### Objectif
Connecter les APIs externes pour enrichissement de données temps réel.

#### Tâches

**4.2.1 Intégration Amboss API Complète**

```yaml
Responsable: Backend Dev
Durée: 1 semaine
Prérequis: Compte Amboss API

Actions:
  - Client Amboss complet (tous endpoints)
  - Sync données nœuds temps réel
  - Récupération métriques avancées
  - Cache intelligent

Endpoints Amboss utilisés:
  - GET /nodes/{pubkey}
  - GET /nodes/{pubkey}/health
  - GET /nodes/{pubkey}/channels
  - GET /network/stats
  - GET /rankings

Données récupérées:
  - Node capacity, channel count
  - Centrality metrics
  - Health score Amboss
  - Rankings position
  - Historical data

Cache strategy:
  - Node data: 1h TTL
  - Health scores: 15min TTL
  - Network stats: 6h TTL
  - Rankings: 24h TTL

Critères de succès:
  - ✅ Tous endpoints implémentés
  - ✅ Rate limit respecté (configuré par tier)
  - ✅ Cache hit rate > 85%
  - ✅ Fallback si API down

Variables .env:
  AMBOSS_API_KEY=your_api_key
  AMBOSS_API_URL=https://api.amboss.space/graphql
  AMBOSS_RATE_LIMIT=100  # req/min

Fichiers:
  - src/clients/amboss_client.py (compléter)
  - tests/test_amboss_client.py (nouveau)
```

**4.2.2 Intégration Mempool.space**

```yaml
Responsable: Backend Dev
Durée: 3 jours
Prérequis: Aucune dépendance externe

Actions:
  - Client Mempool.space API
  - Données on-chain pour nœuds
  - Channel open/close détection
  - Fee estimations on-chain

Endpoints utilisés:
  - GET /api/v1/lightning/nodes/{pubkey}
  - GET /api/v1/lightning/channels/{id}
  - GET /api/v1/fees/recommended

Use cases:
  - Détection channels récents (< 7j)
  - Âge réel des channels (block height)
  - On-chain fees pour close recommendations
  - Network stats globales

Critères de succès:
  - ✅ Client fonctionnel
  - ✅ Données on-chain correctes
  - ✅ Integration avec optimizer
  - ✅ Cache approprié (6h TTL)

Fichiers:
  - src/clients/mempool_client.py (nouveau)
  - src/integrations/onchain_data.py (nouveau)
```

**4.2.3 Intégration 1ML (optionnelle)**

```yaml
Responsable: Backend Dev
Durée: 2 jours
Prérequis: Aucune

Actions:
  - Client 1ML API
  - Rankings et stats alternatives
  - Comparaison multi-sources
  - Enrichissement profils nœuds

Endpoints:
  - GET /node/{pubkey}
  - GET /statistics

Critères de succès:
  - ✅ Client fonctionnel
  - ✅ Données agrégées avec Amboss
  - ✅ Comparaison rankings multi-sources

Fichiers:
  - src/clients/oneml_client.py (nouveau)
```

### 4.3 Monitoring et Observabilité Complets

#### Objectif
Implémenter un système de monitoring production-grade avec métriques détaillées.

#### Tâches

**4.3.1 Prometheus Metrics Complet**

```yaml
Responsable: DevOps + Backend Dev
Durée: 1 semaine
Prérequis: Infrastructure stable

Actions:
  - Instrumenter toute l'application
  - Export métriques Prometheus format
  - Endpoint /metrics optimisé
  - Labels et cardinality appropriés

Métriques à exposer:

  # HTTP Metrics
  http_requests_total{method, endpoint, status}
  http_request_duration_seconds{method, endpoint}
  http_request_size_bytes{method, endpoint}
  http_response_size_bytes{method, endpoint}
  
  # Application Metrics
  mcp_optimizations_total{node_id, decision_type}
  mcp_optimization_duration_seconds{node_id}
  mcp_channels_analyzed_total
  mcp_decisions_applied_total{result}
  mcp_rollbacks_total{reason}
  
  # Lightning Metrics
  lightning_node_score{node_id}
  lightning_channel_score{channel_id}
  lightning_forward_success_rate{node_id}
  lightning_fees_earned_sats{node_id}
  
  # External API Metrics
  external_api_requests_total{provider, endpoint, status}
  external_api_duration_seconds{provider, endpoint}
  external_api_errors_total{provider, error_type}
  
  # Cache Metrics
  cache_hits_total{cache_type}
  cache_misses_total{cache_type}
  cache_hit_rate{cache_type}
  
  # Database Metrics
  db_queries_total{operation, collection}
  db_query_duration_seconds{operation, collection}
  db_connection_pool_size
  db_connection_pool_active

Critères de succès:
  - ✅ > 50 métriques exposées
  - ✅ Endpoint /metrics < 100ms
  - ✅ Cardinality contrôlée (< 1000 labels)
  - ✅ Documentation complète métriques

Fichiers:
  - src/monitoring/prometheus_exporter.py (nouveau)
  - app/middleware/metrics_middleware.py (nouveau)
  - docs/metrics-documentation.md (nouveau)
```

**4.3.2 Grafana Dashboard**

```yaml
Responsable: DevOps
Durée: 1 semaine
Prérequis: Prometheus configuré

Actions:
  - Créer dashboards Grafana
  - Panels pour toutes métriques clés
  - Alertes configurées
  - Templates exportables

Dashboards à créer:

  1. MCP Overview
     - Request rate, error rate, latency
     - Active nodes, channels analyzed
     - Decisions applied, rollbacks
     - Cache hit rate, DB performance
  
  2. Lightning Performance
     - Node scores distribution
     - Channel scores distribution
     - Forward success rates
     - Fees earned evolution
  
  3. External APIs
     - Request rates par provider
     - Latencies par endpoint
     - Error rates
     - Rate limit consumption
  
  4. System Health
     - CPU, Memory, Disk usage
     - Connection pools
     - Queue sizes
     - Circuit breaker states
  
  5. Business Metrics
     - Optimizations per day/week
     - Average improvement per node
     - User satisfaction scores
     - Revenue impact

Alertes Grafana:
  - Error rate > 5% (5min)
  - Latency p95 > 2s (5min)
  - Service down (1min)
  - Database slow queries > 10s
  - External API failures > 20% (10min)

Critères de succès:
  - ✅ 5 dashboards complets
  - ✅ Alertes fonctionnelles
  - ✅ Templates JSON exportés
  - ✅ Documentation usage

Fichiers:
  - monitoring/grafana/dashboards/*.json (nouveau)
  - monitoring/grafana/alerts/*.yaml (nouveau)
  - docs/grafana-setup.md (nouveau)
```

**4.3.3 Log Aggregation et Analysis**

```yaml
Responsable: DevOps + Backend Dev
Durée: 1 semaine
Prérequis: Structured logging en place

Actions:
  - Centraliser logs (ELK ou Loki)
  - Structured logging (JSON)
  - Log levels appropriés
  - Retention policy

Stack logging:
  - Loki (log aggregation)
  - Promtail (log shipper)
  - Grafana (visualization)
  - Ou alternative: ELK Stack

Format logs:
  {
    "timestamp": "2025-10-12T10:30:00Z",
    "level": "INFO",
    "logger": "mcp.optimizer",
    "message": "Optimization completed",
    "node_id": "03abc...",
    "duration_ms": 234,
    "decisions": 3,
    "trace_id": "xyz-123"
  }

Log levels:
  DEBUG: Détails techniques (dev only)
  INFO: Events normaux (optimization start/end)
  WARNING: Situations inhabituelles (high latency)
  ERROR: Erreurs récupérables (API timeout)
  CRITICAL: Erreurs critiques (DB down)

Retention:
  - INFO: 7 jours
  - WARNING: 30 jours
  - ERROR/CRITICAL: 90 jours
  - DEBUG: 1 jour (production off)

Critères de succès:
  - ✅ Tous logs centralisés
  - ✅ Recherche rapide (< 1s)
  - ✅ Alertes sur patterns (error spikes)
  - ✅ Retention respectée

Fichiers:
  - monitoring/loki-config.yaml (nouveau)
  - monitoring/promtail-config.yaml (nouveau)
  - src/logging_config.py (améliorer)
```

### 4.4 Performance et Scaling

#### Objectif
Optimiser les performances et préparer le système pour le scaling.

#### Tâches

**4.4.1 Optimisations Cache Avancées**

```yaml
Responsable: Backend Dev
Durée: 1 semaine
Prérequis: Redis configuré

Actions:
  - Implémentation cache multi-niveaux
  - Cache warming automatique
  - TTL dynamiques basés sur volatilité
  - Cache invalidation intelligente

Architecture cache:

  Level 1 (Memory): In-process LRU
    - Données ultra-fréquentes
    - TTL: 1-5 min
    - Size: 100MB max
    - Use: Config, thresholds
  
  Level 2 (Redis): Distributed cache
    - Données fréquentes
    - TTL: 5min - 6h
    - Size: Illimité (managed)
    - Use: Node data, scores, graphs
  
  Level 3 (DB): Source of truth
    - Données permanentes
    - No TTL
    - Use: Policies, decisions, metrics

Cache warming:
  - Précalcul des top 100 nodes (6h)
  - Network graph (6h)
  - Popular queries (analytics)

TTL dynamiques:
  - Données volatiles (prices): 1min
  - Données stables (node capacity): 1h
  - Données immuables (old decisions): 24h

Invalidation:
  - Event-based (policy applied → invalidate node cache)
  - Time-based (TTL expiration)
  - Manual (API endpoint)

Critères de succès:
  - ✅ Hit rate global > 85%
  - ✅ Latency reduction 60%
  - ✅ Cache memory usage < 500MB
  - ✅ Automatic warming fonctionnel

Fichiers:
  - src/cache/multi_level_cache.py (nouveau)
  - src/cache/cache_warming.py (nouveau)
  - src/cache/invalidation_manager.py (nouveau)
```

**4.4.2 Database Connection Pooling**

```yaml
Responsable: Backend Dev
Durée: 3 jours
Prérequis: MongoDB/Redis actifs

Actions:
  - Configurer connection pools optimaux
  - Monitoring pool utilization
  - Auto-scaling pool size
  - Retry logic et circuit breakers

Configuration MongoDB:
  min_pool_size: 10
  max_pool_size: 100
  max_idle_time_ms: 60000
  wait_queue_timeout_ms: 5000
  
Configuration Redis:
  max_connections: 50
  timeout: 5
  retry_on_timeout: true
  health_check_interval: 30

Critères de succès:
  - ✅ Pool utilization 50-70% moyenne
  - ✅ No connection timeouts
  - ✅ Graceful degradation si saturation
  - ✅ Metrics pool exposées Prometheus

Fichiers:
  - database.py (améliorer)
  - src/db/connection_manager.py (nouveau)
```

**4.4.3 Background Tasks Asynchrones**

```yaml
Responsable: Backend Dev
Durée: 1 semaine
Prérequis: Infrastructure stable

Actions:
  - Implémentation task queue (Celery/RQ)
  - Tâches lourdes en background
  - Scheduling optimisations périodiques
  - Monitoring tasks

Tâches en background:
  - Network graph sync (6h)
  - Score recalculation (1h)
  - Daily reports génération
  - Cleanup old data (24h)
  - Cache warming (6h)

Stack:
  - Celery (task queue)
  - Redis (broker)
  - Flower (monitoring)

Configuration:
  workers: 4
  concurrency: 8 (gevent)
  task_time_limit: 600
  task_soft_time_limit: 300

Critères de succès:
  - ✅ Tâches lourdes n'impactent pas API
  - ✅ Scheduling fiable
  - ✅ Retry automatique sur échec
  - ✅ Monitoring tasks temps réel

Fichiers:
  - src/tasks/ (nouveau dossier)
    - celery_app.py
    - optimization_tasks.py
    - sync_tasks.py
    - report_tasks.py
  - requirements.txt (ajouter celery, flower)
```

**4.4.4 Rate Limiting et Throttling**

```yaml
Responsable: Backend Dev
Durée: 3 jours
Prérequis: Redis actif

Actions:
  - Rate limiting par endpoint
  - Throttling requêtes lourdes
  - Protection contre abuse
  - Documentation limits

Stratégie:
  - Public endpoints: 100 req/min
  - Authenticated: 1000 req/min
  - Heavy endpoints (optimization): 10 req/min
  - Background tasks: No limit

Implémentation:
  - Token bucket algorithm
  - Redis pour state distribué
  - Headers informatifs (X-RateLimit-*)
  - 429 response si exceeded

Headers:
  X-RateLimit-Limit: 1000
  X-RateLimit-Remaining: 987
  X-RateLimit-Reset: 1699876543

Critères de succès:
  - ✅ Rate limiting fonctionnel
  - ✅ Pas d'impact performance légitimes users
  - ✅ Documentation limites API
  - ✅ Metrics rate limit violations

Fichiers:
  - app/middleware/rate_limiter.py (nouveau)
  - docs/api-rate-limits.md (nouveau)
```

---

## TIMELINE & RESSOURCES

### Planning Global

| Phase | Début | Durée | Fin |
|-------|-------|-------|-----|
| **Priorité 1** | S+0 | 2 semaines | S+2 |
| **Priorité 2** | S+2 | 3 semaines | S+5 |
| **Priorité 3** | S+5 | 4 semaines | S+9 |
| **Priorité 4** | S+9 | 6 semaines | S+15 |

### Allocation Ressources

| Phase | Durée | Backend Dev | DevOps | ML Engineer | QA | Total FTE |
|-------|-------|-------------|--------|-------------|----|----|
| **P1** | 2 semaines | 1.0 | 1.0 | 0 | 0.5 | 2.5 |
| **P2** | 3 semaines | 2.0 | 0.5 | 0 | 0.5 | 3.0 |
| **P3** | 4 semaines | 1.0 | 0.5 | 0 | 1.0 | 2.5 |
| **P4** | 6 semaines | 1.5 | 0.5 | 1.0 | 0.5 | 3.5 |
| **Total** | 15 semaines | - | - | - | - | ~3 FTE avg |

### Budget Estimé

```yaml
Services Cloud (mensuel):
  MongoDB Atlas M10: $60/mois
  Redis Cloud 250MB: $10/mois
  Compute (VPS): $40/mois
  Qdrant Cloud: $50/mois (optionnel)
  Total: ~$160/mois

APIs Externes (mensuel):
  Amboss API: $50-200/mois (selon tier)
  Anthropic API: $50-500/mois (usage)
  Total: ~$100-700/mois

Infrastructure:
  Monitoring (Grafana Cloud): $50/mois ou self-hosted
  Backups: $20/mois
  SSL Certs: $0 (Let's Encrypt)
  Total: ~$20-70/mois

TOTAL MENSUEL: $280-930/mois
```

### Milestones Clés

| Date Cible | Milestone | Critère de Succès |
|------------|-----------|-------------------|
| **S+2** | Infrastructure Stable | API HTTPS accessible, systemd configuré, Docker rebuild réussi |
| **S+5** | Core Engine Complet | LNBits intégré, heuristiques finalisées, tests validés |
| **S+9** | Shadow Mode Validé | 21 jours observation, validation experts, > 80% agreement |
| **S+12** | Production Limitée Active | 5 nœuds en production, mode semi-auto, monitoring complet |
| **S+15** | v1.0 Feature Complete | RAG actif, intégrations externes, monitoring Grafana |

---

## CRITÈRES DE SUCCÈS

### Succès par Phase

#### Phase 1 - Infrastructure ✅

```yaml
Critères obligatoires:
  - ✅ API accessible via HTTPS (uptime > 99%)
  - ✅ Service systemd auto-restart fonctionnel
  - ✅ Image Docker stable (0 crashes)
  - ✅ MongoDB & Redis connectés (latency < 50ms)
  - ✅ Mode dégradé fonctionnel (fallback)

Critères optionnels:
  - ⭐ Monitoring infrastructure (Grafana)
  - ⭐ Automated backups configurés
  - ⭐ Multi-region deployment (HA)
```

#### Phase 2 - Core Engine ✅

```yaml
Critères obligatoires:
  - ✅ LNBits client complet (100% endpoints)
  - ✅ Authentification macaroon sécurisée
  - ✅ Heuristiques implémentées (8 heuristiques min)
  - ✅ Decision engine validé (tests > 95%)
  - ✅ Rollback fonctionnel (< 30s)
  - ✅ Lightning scoring actif

Critères optionnels:
  - ⭐ Calibration heuristiques sur > 1000 canaux
  - ⭐ Scoring réseau complet (centrality, etc.)
```

#### Phase 3 - Production Contrôlée ✅

```yaml
Critères obligatoires:
  - ✅ Shadow mode 21 jours minimum
  - ✅ Validation experts (> 80% agreement)
  - ✅ Test pilote 1 canal réussi
  - ✅ Expansion progressive validée
  - ✅ 5 nœuds en production
  - ✅ Mode semi-auto fonctionnel
  - ✅ Alertes actives et testées

Critères optionnels:
  - ⭐ 10+ nœuds en production
  - ⭐ Mode fully-auto (pour nœuds consentants)
```

#### Phase 4 - Fonctionnalités Avancées ✅

```yaml
Critères obligatoires:
  - ✅ RAG système actif (queries fonctionnelles)
  - ✅ Intégration Amboss complète
  - ✅ Monitoring Prometheus + Grafana
  - ✅ Cache multi-niveaux (hit rate > 85%)

Critères optionnels:
  - ⭐ Intégrations multiples (1ML, Sparkseer)
  - ⭐ Background tasks (Celery)
  - ⭐ Rate limiting avancé
```

### Métriques de Succès Globales

```yaml
Performance:
  - API uptime: > 99.5%
  - Response time p95: < 500ms
  - Response time p99: < 2s
  - Error rate: < 0.5%
  - Cache hit rate: > 85%

Fonctionnalité:
  - Optimizations/jour: > 50
  - Nodes actifs: > 5
  - Canaux optimisés: > 100
  - Success rate optimizations: > 95%

Business:
  - Amélioration moyenne fees: > +15%
  - Amélioration forward rate: > +20%
  - Satisfaction node operators: > 80%
  - Faux positifs: < 5%

Qualité:
  - Code coverage: > 85%
  - Tests passing: 100%
  - Sécurité: 0 vulnérabilités critiques
  - Documentation: 100% endpoints documentés
```

---

## ANNEXES

### A. Risques et Mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Image Docker build échoue | Moyenne | Haut | Fallback Python direct, rebuild incrémental |
| MongoDB/Redis indispo | Faible | Moyen | Mode dégradé, fallback local |
| LNBits API rate limit | Moyenne | Moyen | Cache agressif, retry logic |
| Faux positifs recommandations | Moyenne | Haut | Shadow mode extended, validation experts |
| Performance dégradée production | Faible | Haut | Load testing préalable, monitoring alertes |
| Node operators insatisfaits | Moyenne | Haut | Mode semi-auto, feedback continu |

### B. Dépendances Externes

```yaml
Services Cloud:
  - MongoDB Atlas: SLA 99.95%
  - Redis Cloud/Upstash: SLA 99.9%
  - Qdrant Cloud: SLA 99.5% (optionnel)

APIs Externes:
  - LNBits: Disponibilité requise 99%+
  - Amboss API: Rate limits variables (selon tier)
  - Mempool.space: Public API, best effort
  - Anthropic API: SLA 99.9%

Infrastructure:
  - Serveur production: Hostinger VPS
  - Domain & SSL: Let's Encrypt
  - Monitoring: Self-hosted ou Grafana Cloud
```

### C. Checklist Go-Live

```markdown
## Checklist Pre-Production

### Infrastructure
- [ ] HTTPS configuré et testé (SSL A+)
- [ ] Systemd service activé et testé
- [ ] Docker image rebuilt et déployée
- [ ] MongoDB Atlas production ready
- [ ] Redis Cloud production ready
- [ ] Backups automatiques configurés
- [ ] Monitoring alertes actives

### Code
- [ ] Tous tests passent (100%)
- [ ] Code coverage > 85%
- [ ] Code review complété
- [ ] Documentation à jour
- [ ] Security audit passé
- [ ] Performance tests validés

### Intégrations
- [ ] LNBits connexion validée
- [ ] Authentification macaroon testée
- [ ] Amboss API fonctionnelle
- [ ] Mempool.space intégré
- [ ] RAG queries testées

### Monitoring
- [ ] Prometheus metrics exposées
- [ ] Grafana dashboards créés
- [ ] Alertes configurées et testées
- [ ] Logs aggregation active
- [ ] Retention policies configurées

### Sécurité
- [ ] Credentials chiffrées
- [ ] Rate limiting actif
- [ ] CORS configuré
- [ ] Headers sécurité (HSTS, CSP)
- [ ] Audit logs activés

### Validation
- [ ] Shadow mode 21 jours complété
- [ ] Validation experts (> 80%)
- [ ] Test pilote réussi
- [ ] Rollback testé
- [ ] Disaster recovery documenté

### Documentation
- [ ] API documentation (Swagger)
- [ ] Runbooks opérationnels
- [ ] Troubleshooting guide
- [ ] Metrics documentation
- [ ] User guides (node operators)
```

### D. Contacts et Escalation

```yaml
Équipe:
  Backend Lead: [Contact]
  DevOps Lead: [Contact]
  ML Engineer: [Contact]
  Product Owner: [Contact]

Support:
  Niveau 1: Monitoring automatique + Telegram
  Niveau 2: On-call engineer (24/7)
  Niveau 3: Backend Lead + DevOps Lead

Escalation:
  - Incident mineur: Slack notification
  - Incident majeur: Email + Slack + Telegram
  - Incident critique: PagerDuty + Phone call

SLA Réponse:
  - P0 (Critical, production down): 15 min
  - P1 (Major, degraded service): 1h
  - P2 (Minor, workaround exists): 4h
  - P3 (Low, cosmetic): 24h
```

### E. Références

```markdown
Documents Techniques:
  - _SPECS/Plan-MVP.md
  - docs/backbone-technique-MVP.md
  - docs/dictionnaire-donnees.md
  - production_optimization_audit.md

Code:
  - src/optimizers/core_fee_optimizer.py
  - src/clients/lnbits_client.py
  - app/services/lightning_scoring.py
  - rag/ (système RAG)

Scripts:
  - scripts/configure_nginx_production.sh
  - scripts/configure_systemd_autostart.sh
  - monitor_production.py

Rapports:
  - RAPPORT_FINAL_RESOLUTION_10OCT2025.md
  - INVESTIGATION_FINALE_10OCT2025.md
  - PHASE5-STATUS.md
```

---

**Document Version**: 1.0.0  
**Date**: 12 octobre 2025  
**Auteur**: Équipe MCP  
**Statut**: APPROVED

**Prochaine révision**: Fin de chaque phase  
**Approbation**: Product Owner + Tech Lead

---

*Ce document est un plan vivant et sera mis à jour au fur et à mesure de l'avancement du projet.*

