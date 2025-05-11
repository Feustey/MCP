
# Plan-MVP-MCP.mdc

# Plan de Bataille MCP - Phases du MVP

Ce document détaille les 5 phases du Plan MVP pour le déploiement de MCP sur Umbrel, avec les fichiers de référence et composants associés.

## PHASE 1 — Assainissement & Cadrage

**Cartographie modulaire** : ingestion > preprocessing > scoring > decision > action > logs
- [docs/backbone-technique-MVP.md](mdc:docs/backbone-technique-MVP.md) - Architecture technique
- [mcp/](mdc:mcp/) - Modules spécifiques à l'analyse des nœuds Lightning

**Dictionnaire de données** : Structures strictes pour canal, nœud, politique
- [src/](mdc:src/) - Code source principal avec modèles de données

**Objectif fonctionnel** : Détection et ajustement des canaux sous-performants
- [_SPECS/Plan-MVP.md](mdc:_SPECS/Plan-MVP.md) - Spécifications détaillées

## PHASE 2 — Environnement de Dev & Test

**Conteneurisation** : FastAPI + Redis + Mongo + RAG
- [docker-compose.yml](mdc:docker-compose.yml) - Configuration Docker
- [Dockerfile](mdc:Dockerfile) - Configuration de l'image Docker

**Tests** : Tests unitaires et d'intégration
- [tests/](mdc:tests/) - Tests unitaires et d'intégration
- [run_test_system.py](mdc:run_test_system.py) - Point d'entrée pour les tests

**Simulateur de Nœud** : Simulation de différents comportements
- [src/tools/simulator/](mdc:src/tools/simulator/) - Simulateur de nœud Lightning

## PHASE 3 — Core Engine "Pilotage de Fees"

**Heuristiques pondérées** : Centralité, volume, uptime, etc.
- [src/optimizers/](mdc:src/optimizers/) - Algorithmes d'optimisation
- [implement_fee_policy.py](mdc:implement_fee_policy.py) - Implémentation des politiques de frais

**Decision Engine** : Évaluation des canaux et prise de décision
- [data/actions/](mdc:data/actions/) - Actions recommandées
- [src/scanners/](mdc:src/scanners/) - Scanners pour nœuds et liquidité

**Sécurité & Rollback** : Logging et réversibilité des actions
- [data/rollbacks/](mdc:data/rollbacks/) - Données pour rollback
- [logs/](mdc:logs/) - Journaux système

## PHASE 4 — Intégration Umbrel & Automatisation

**Package Umbrel** : Structure compatible avec Umbrel
- [systemd/](mdc:systemd/) - Configuration systemd

**Cron & Trigger** : Déclenchement automatique des analyses
- [scripts/](mdc:scripts/) - Scripts utilitaires pour automatisation

**Observabilité** : Logging et visualisation
- [MCP Prometheus Rules.yml](mdc:MCP%20Prometheus%20Rules.yml) - Règles Prometheus
- [grafana/](mdc:grafana/) - Dashboards Grafana
- [prometheus.yml](mdc:prometheus.yml) - Configuration Prometheus

## PHASE 5 — Production contrôlée

**Shadow Mode** : Observation avant action
- [run_without_liquidity_scan.py](mdc:run_without_liquidity_scan.py) - Exécution sans actions

**Failover Plan** : Résilience et gestion des pannes
- [config/](mdc:config/) - Configuration avec options de fallback

**Release Progressive** : Déploiement contrôlé
- [run_rag_workflow_prod.sh](mdc:run_rag_workflow_prod.sh) - Workflow de production
- [send_to_telegram.py](mdc:send_to_telegram.py) - Notification des actions
