
# project-structure.mdc

# Structure du Projet MCP

Ce projet est un système d'optimisation pour les nœuds Lightning Network utilisant des tests A/B et une boucle de feedback, enrichi par un système RAG (Retrieval-Augmented Generation).

## Fichiers principaux

- [run_test_system.py](mdc:run_test_system.py) - Point d'entrée principal pour exécuter les scénarios de test
- [topup_wallet.py](mdc:topup_wallet.py) - Utilitaire pour alimenter le wallet LNBits
- [test_scenarios.py](mdc:test_scenarios.py) - Gestion des scénarios de test A/B
- [run_rag_workflow.sh](mdc:run_rag_workflow.sh) - Script pour exécuter le workflow RAG
- [implement_fee_policy.py](mdc:implement_fee_policy.py) - Implémentation des politiques de frais

## Répertoires clés

- [/rag/](mdc:rag/) - Système RAG pour l'analyse et collecte de données
- [/data/](mdc:data/) - Données consolidées (métriques, données brutes, rapports)
- [/app/](mdc:app/) - Application principale (services, routes API)
- [/src/](mdc:src/) - Code source principal (API, clients, optimizers)
- [/docs/](mdc:docs/) - Documentation consolidée
- [/scripts/](mdc:scripts/) - Scripts utilitaires pour maintenance et setup
- [/tests/](mdc:tests/) - Tests unitaires et d'intégration

# mvp-phases.mdc

# Plan MVP - Phases de développement

## PHASE 1 — Assainissement & Cadrage
- Cartographie modulaire du système
- Dictionnaire de données strict
- Objectif fonctionnel précis pour le pilotage des fees
- [docs/backbone-technique-MVP.md](mdc:docs/backbone-technique-MVP.md)

## PHASE 2 — Environnement de Dev & Test
- Docker Compose (FastAPI + Redis + Mongo + RAG)
- Tests unitaires et d'intégration
- Simulateur de nœud Lightning
- [docker-compose.yml](mdc:docker-compose.yml)

## PHASE 3 — Core Engine "Pilotage de Fees"
- Heuristiques pondérées (centralité, volume, uptime)
- Decision engine `evaluate_channel()`
- Sécurité et rollback des actions
- [src/optimizers/](mdc:src/optimizers/)

## PHASE 4 — Intégration Umbrel & Automatisation
- Package Umbrel (umbrel-app.yml, docker-compose.yml)
- Cron/trigger pour analyses automatiques
- Observabilité (Prometheus, Grafana)
- [systemd/](mdc:systemd/)

## PHASE 5 — Production contrôlée
- Shadow mode (7 jours d'observation)
- Failover plan et résilience
- Déploiement progressif
- [config/](mdc:config/)

# rag-system.mdc

# Système RAG (Retrieval-Augmented Generation)

Le système RAG permet d'enrichir l'analyse des nœuds Lightning avec des données contextuelles.

## Structure du système RAG
- [/rag/generators/](mdc:rag/generators/) - Générateurs d'assets pour le système RAG
- [/rag/RAG_assets/](mdc:rag/RAG_assets/) - Ressources du système RAG
- [run_rag_workflow.sh](mdc:run_rag_workflow.sh) - Script de workflow RAG (dev)
- [run_rag_workflow_prod.sh](mdc:run_rag_workflow_prod.sh) - Script de workflow RAG (prod)

## Données collectées
- [/rag/RAG_assets/metrics/](mdc:rag/RAG_assets/metrics/) - Métriques collectées
- [/rag/RAG_assets/nodes/](mdc:rag/RAG_assets/nodes/) - Données des nœuds
- [/rag/RAG_assets/reports/](mdc:rag/RAG_assets/reports/) - Rapports générés

## Utilisation
Le système RAG collecte des données, les indexe et les utilise pour enrichir l'analyse et les recommandations d'optimisation des nœuds Lightning.

# mcp-core.mdc

# MCP Core - Moteur d'optimisation

Le cœur du système MCP est un moteur d'optimisation pour les nœuds Lightning Network.

## Composants principaux
- [src/scanners/](mdc:src/scanners/) - Scanners pour nœuds et liquidité
- [src/optimizers/](mdc:src/optimizers/) - Algorithmes d'optimisation
- [src/clients/](mdc:src/clients/) - Clients pour services externes
- [implement_fee_policy.py](mdc:implement_fee_policy.py) - Implémentation des politiques

## Pipeline de données
1. Collecte via scanners
2. Prétraitement des données
3. Analyse et scoring
4. Prise de décision
5. Exécution des actions
6. Logging et monitoring

## Configuration et déploiement
- [docker-compose.yml](mdc:docker-compose.yml) - Configuration Docker
- [.env.example](mdc:.env.example) - Exemple de configuration
- [systemd/](mdc:systemd/) - Configuration pour déploiement
