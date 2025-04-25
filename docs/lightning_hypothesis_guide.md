# Guide d'utilisation pour la validation d'hypothèses sur Lightning Network

Ce guide explique comment utiliser le système de validation d'hypothèses pour tester et évaluer des changements de configuration sur votre nœud Lightning Network.

## Table des matières

1. [Introduction](#introduction)
2. [Gestion des données historiques](#gestion-des-données-historiques)
3. [Validation des hypothèses de frais](#validation-des-hypothèses-de-frais)
4. [Validation des hypothèses de configuration de canaux](#validation-des-hypothèses-de-configuration-de-canaux)
5. [Interprétation des résultats](#interprétation-des-résultats)
6. [API Reference](#api-reference)
7. [Annexes](#annexes)

## Introduction

Le système de validation d'hypothèses permet de tester de manière méthodique l'impact des changements de configuration sur votre nœud Lightning Network. Il s'appuie sur une approche scientifique:

1. Formuler une hypothèse (ex: "Augmenter les frais de 50% augmentera les revenus")
2. Collecter des données de référence avant le changement
3. Appliquer le changement
4. Collecter des données après le changement
5. Comparer et valider l'hypothèse

Ce processus permet de prendre des décisions basées sur des données plutôt que sur des intuitions.

## Gestion des données historiques

### Collecte des métriques

Le système collecte automatiquement les métriques suivantes pour chaque nœud:

- **Capacité totale**: Somme des capacités de tous les canaux
- **Nombre de canaux**: Nombre total de canaux ouverts
- **Taille moyenne des canaux**: Capacité moyenne par canal
- **Frais**: Taux de frais de base et proportionnel
- **Performance de routage**: Nombre de transferts réussis et échoués
- **Revenus**: Frais gagnés grâce au routage

Ces métriques sont stockées dans la collection `metrics_history` avec un horodatage, permettant d'analyser l'évolution dans le temps.

### Archivage automatique

Les données anciennes sont automatiquement archivées selon les paramètres suivants:

- **Métriques historiques**: conservées 90 jours dans la collection principale, archivées pendant 365 jours
- **Historique des requêtes**: conservé 30 jours dans la collection principale, archivé pendant 180 jours

Pour exécuter l'archivage manuellement:

```bash
python scripts/run_archiving.py
```

Pour modifier les paramètres d'archivage, utilisez l'API MongoDB directement:

```javascript
db.archive_settings.updateOne(
  { "collection_name": "metrics_history" },
  { "$set": { "retention_days": 120, "archive_after_days": 730 } }
)
```

## Validation des hypothèses de frais

### Création d'une hypothèse de frais

Une hypothèse de frais permet de tester l'impact d'un changement de frais sur un canal spécifique.

**Via l'API**:

```bash
curl -X POST "http://localhost:8000/lightning/hypotheses/fees" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f",
    "channel_id": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    "new_base_fee": 1000,
    "new_fee_rate": 200,
    "evaluation_period_days": 7
  }'
```

### Application de l'hypothèse

Une fois l'hypothèse créée, vous pouvez l'appliquer pour effectuer le changement de frais:

```bash
curl -X POST "http://localhost:8000/lightning/hypotheses/fees/550e8400-e29b-41d4-a716-446655440000/apply"
```

Cela modifiera les frais du canal et commencera la période d'évaluation.

### Évaluation de l'hypothèse

Après la période d'évaluation (par défaut 7 jours), vous pouvez évaluer les résultats:

```bash
curl "http://localhost:8000/lightning/hypotheses/fees/550e8400-e29b-41d4-a716-446655440000/evaluate"
```

L'évaluation comparera les performances avant et après le changement et générera automatiquement une conclusion.

## Validation des hypothèses de configuration de canaux

### Création d'une hypothèse de configuration

Une hypothèse de configuration permet de tester l'impact de changements plus larges, comme l'ouverture ou la fermeture de canaux.

**Via l'API**:

```bash
curl -X POST "http://localhost:8000/lightning/hypotheses/channels" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f",
    "proposed_changes": {
      "add_channels": [
        {"target_node": "02fc8e97419338c9475c6c06bd8f3ee5c917352809a4024db350a48497036eec86", "capacity": 5000000},
        {"target_node": "0260fab633066d6f9a0ce7c942cb8edf72c254e491232c48867518f8b8a5a559ec", "capacity": 3000000}
      ],
      "close_channels": [
        {"channel_id": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"}
      ],
      "rebalance": true
    },
    "evaluation_period_days": 30
  }'
```

### Application de l'hypothèse

Appliquez l'hypothèse pour effectuer les changements de configuration:

```bash
curl -X POST "http://localhost:8000/lightning/hypotheses/channels/550e8400-e29b-41d4-a716-446655440000/apply"
```

Cela exécutera tous les changements proposés (ouverture/fermeture de canaux, rééquilibrage).

### Évaluation de l'hypothèse

Après la période d'évaluation (par défaut 30 jours), évaluez les résultats:

```bash
curl "http://localhost:8000/lightning/hypotheses/channels/550e8400-e29b-41d4-a716-446655440000/evaluate"
```

## Interprétation des résultats

### Métriques d'impact des frais

Les résultats incluent les métriques d'impact suivantes:

- **forwards_change_pct**: Changement en pourcentage du nombre de transferts
- **revenue_change_pct**: Changement en pourcentage des revenus
- **success_rate_change_pct**: Changement en pourcentage du taux de succès
- **avg_fee_per_forward_before/after**: Frais moyen par transfert avant/après
- **avg_fee_change_pct**: Changement en pourcentage des frais moyens

Une hypothèse est considérée comme validée si `revenue_change_pct > 0`, c'est-à-dire si les revenus ont augmenté.

### Métriques d'impact des canaux

Pour les hypothèses de configuration de canaux:

- **channels_change_pct**: Changement en pourcentage du nombre de canaux
- **capacity_change_pct**: Changement en pourcentage de la capacité totale
- **capacity_efficiency_before/after**: Revenus par unité de capacité
- **channel_efficiency_before/after**: Revenus par canal

## API Reference

### Endpoints pour les hypothèses de frais

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/lightning/hypotheses/fees` | Créer une hypothèse de frais |
| POST | `/lightning/hypotheses/fees/{id}/apply` | Appliquer une hypothèse |
| GET | `/lightning/hypotheses/fees/{id}/evaluate` | Évaluer une hypothèse |
| GET | `/lightning/hypotheses/fees/node/{node_id}` | Lister les hypothèses pour un nœud |

### Endpoints pour les hypothèses de canaux

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/lightning/hypotheses/channels` | Créer une hypothèse de canaux |
| POST | `/lightning/hypotheses/channels/{id}/apply` | Appliquer une hypothèse |
| GET | `/lightning/hypotheses/channels/{id}/evaluate` | Évaluer une hypothèse |
| GET | `/lightning/hypotheses/channels/node/{node_id}` | Lister les hypothèses pour un nœud |

## Annexes

### Exemple de scénario d'utilisation

**Scénario**: Tester l'élasticité des prix sur un canal à fort trafic

1. Identifier un canal avec un volume de transfert élevé
2. Créer une hypothèse pour augmenter les frais de 50%
3. Appliquer l'hypothèse
4. Attendre la période d'évaluation (7 jours)
5. Évaluer les résultats
   - Si la diminution du volume est compensée par l'augmentation des frais, l'hypothèse est validée
   - Sinon, revenir aux frais d'origine

### Bonnes pratiques

- **Ne testez qu'un changement à la fois**: Pour des résultats clairs, ne modifiez qu'un paramètre à la fois
- **Donnez suffisamment de temps**: Évitez les périodes d'évaluation trop courtes (minimum 7 jours)
- **Tenez compte des variations saisonnières**: Le trafic peut varier selon l'heure, le jour ou la semaine
- **Documentez vos hypothèses**: Gardez une trace de vos tests et de leurs résultats

### Architecture technique

Les données sont organisées selon le schéma suivant:

- `metrics_history`: Stockage des métriques historiques
- `fee_hypotheses`: Stockage des hypothèses de frais
- `channel_hypotheses`: Stockage des hypothèses de configuration de canaux
- `archives`: Stockage des métadonnées d'archivage

L'architecture est conçue pour être scalable et permet l'ajout futur de nouveaux types d'hypothèses. 