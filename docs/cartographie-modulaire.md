# Cartographie Modulaire du Système MCP

> Dernière mise à jour: 25 juin 2025

## Diagramme d'Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Ingestion     │────▶│  Preprocessing  │────▶│    Scoring      │
│                 │     │                 │     │                 │
└────────┬────────┘     └─────────────────┘     └────────┬────────┘
         │                                               │
         │                                               ▼
┌────────▼────────┐                           ┌─────────────────┐
│                 │                           │                 │
│     Logs        │◀──────────────────────────│    Decision     │
│                 │                           │                 │
└─────────────────┘                           └────────┬────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │                 │
                                              │    Action       │
                                              │                 │
                                              └─────────────────┘
```

## Modules Fondamentaux

### 1. Module d'Ingestion

**Objectif**: Collecter les données brutes des nœuds Lightning depuis diverses sources.

**Composants**:
- **Connecteurs de sources**:
  - [src/clients/lnbits_client.py](mdc:src/clients/lnbits_client.py) - Client LNBits
  - [src/amboss_scraper.py](mdc:src/amboss_scraper.py) - Scraper Amboss
  - Connecteurs Mempool.space et Sparkseer (à développer)
- **Parseurs de données**:
  - [src/optimizers/parsing_amboss_utils.py](mdc:src/optimizers/parsing_amboss_utils.py) - Parsing Amboss
- **Cache et persistance**:
  - [src/redis_operations.py](mdc:src/redis_operations.py) - Opérations Redis
  - [src/mongo_operations.py](mdc:src/mongo_operations.py) - Opérations MongoDB

**Interfaces**:
- Entrée: APIs externes, fichiers bruts
- Sortie: Données structurées au format JSON unifié

### 2. Module de Preprocessing

**Objectif**: Nettoyer, enrichir et normaliser les données pour le scoring.

**Composants**:
- **Nettoyage de données**:
  - Détection et gestion des valeurs aberrantes
  - Résolution des incohérences entre sources
- **Enrichissement**:
  - Calcul de métriques dérivées (e.g., taux de réussite des forwards)
  - Agrégation des données temporelles
- **Normalisation**:
  - Uniformisation des unités (sats, msats)
  - Normalisation des scores dans une plage standard

**Interfaces**:
- Entrée: Données brutes structurées
- Sortie: Dataset enrichi et normalisé

### 3. Module de Scoring

**Objectif**: Évaluer les performances des canaux et nœuds selon des heuristiques multiples.

**Composants**:
- **Calculateurs d'heuristiques**:
  - [src/optimizers/scoring_utils.py](mdc:src/optimizers/scoring_utils.py) - Utilitaires de scoring
  - [src/optimizers/performance_tracker.py](mdc:src/optimizers/performance_tracker.py) - Suivi des performances
- **Pondération**:
  - Configuration des poids par heuristique
  - Calibrage dynamique selon l'historique
- **Modèles de scoring**:
  - Scoring multicritère pondéré
  - Classification des canaux par type et performance

**Interfaces**:
- Entrée: Dataset enrichi et normalisé
- Sortie: Map `<channel_id>: score` avec détails des sous-scores

### 4. Module de Décision

**Objectif**: Évaluer les scores et déterminer les actions à entreprendre.

**Composants**:
- **Moteur de règles**:
  - Règles de décision hiérarchiques
  - Seuils configurables par type d'action
- **Gestion de la confiance**:
  - Calcul du niveau de confiance des décisions
  - Filtrage des décisions à faible confiance
- **Orchestrateur de décisions**:
  - Résolution des conflits entre décisions
  - Priorisation des actions

**Interfaces**:
- Entrée: Scores de canaux/nœuds
- Sortie: Liste d'actions recommandées (`NO_ACTION`, `INCREASE_FEES`, `LOWER_FEES`, `CLOSE_CHANNEL`)

### 5. Module d'Action

**Objectif**: Exécuter les décisions validées sur les nœuds Lightning.

**Composants**:
- **Exécuteurs d'actions**:
  - [implement_fee_policy.py](mdc:implement_fee_policy.py) - Implémentation des politiques de frais
  - [src/optimizers/fee_update_utils.py](mdc:src/optimizers/fee_update_utils.py) - Utilitaires de mise à jour
- **Vérification de sécurité**:
  - Validation des actions avant exécution
  - Mode dry-run pour test sans exécution
- **Gestionnaire de rollback**:
  - Sauvegarde des états précédents
  - Mécanisme de restauration en cas d'erreur

**Interfaces**:
- Entrée: Liste d'actions validées
- Sortie: Résultats d'exécution avec statuts

### 6. Module de Logs

**Objectif**: Assurer la traçabilité et la transparence de toutes les opérations.

**Composants**:
- **Journalisation**:
  - Logs structurés par niveau (INFO, WARN, ACTION, ERROR)
  - Rotation et archivage automatiques
- **Métriques**:
  - Collecte de métriques d'exécution
  - Export pour Prometheus
- **Rapports**:
  - Génération de rapports d'activité
  - Historique des décisions et actions

**Interfaces**:
- Entrée: Événements système et résultats d'exécution
- Sortie: Logs persistants et métriques exploitables

## Interfaces Transversales

### API RESTful

- **Points d'entrée**:
  - [src/api/main.py](mdc:src/api/main.py)
  - [src/api/network_endpoints.py](mdc:src/api/network_endpoints.py)
  - [src/api/automation_endpoints.py](mdc:src/api/automation_endpoints.py)

### Système RAG (Retrieval-Augmented Generation)

- **Composants**:
  - [rag/rag.py](mdc:src/rag.py)
  - [run_rag_workflow.sh](mdc:run_rag_workflow.sh)
  - [run_rag_workflow_prod.sh](mdc:run_rag_workflow_prod.sh)

## Flux de Données End-to-End

1. **Déclenchement** (cron journalier ou événement)
2. **Ingestion** des données depuis LNBits et Amboss
3. **Preprocessing** pour uniformisation et enrichissement
4. **Scoring** multicritère des canaux
5. **Décision** basée sur les scores et règles configurées
6. **Validation** manuelle ou automatique selon le mode
7. **Exécution** des actions validées
8. **Journalisation** de toutes les étapes et résultats
9. **Reporting** pour visualisation et analyse

Ce flux garantit une approche systématique, traçable et réversible pour l'optimisation des nœuds Lightning. 