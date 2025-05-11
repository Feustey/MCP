# Protocole de Calibration Rigoureux pour Simulateur

> Dernière mise à jour: 8 mai 2025

## Introduction

Ce document décrit le protocole de calibration rigoureux mis en place pour garantir que le simulateur stochastique de nœuds Lightning reflète fidèlement le comportement des nœuds réels. Cette calibration est essentielle pour obtenir des résultats fiables dans les tests des moteurs de décision et l'optimisation des politiques tarifaires.

## Objectifs du Protocole

1. **Indistinguabilité Statistique** : Garantir que les distributions générées par le simulateur sont statistiquement indistinguables des données réelles.
2. **Robustesse** : Assurer que la calibration est robuste face aux variations naturelles des données.
3. **Reproductibilité** : Permettre de reproduire les résultats de calibration sur différents jeux de données.
4. **Traçabilité** : Maintenir un historique complet des calibrations effectuées et de leurs résultats.
5. **Visualisation Automatique** : Générer automatiquement des visualisations pour faciliter l'analyse des résultats.

## Métriques Clés

Les métriques suivantes sont utilisées pour calibrer le simulateur :

| Métrique | Description | Test statistique | Seuil |
|----------|-------------|------------------|-------|
| `forward_volume_distribution` | Distribution du volume forwardé par canal par jour | Kolmogorov-Smirnov | 0.05 |
| `success_rate_distribution` | Distribution des taux de réussite par canal | Kolmogorov-Smirnov | 0.05 |
| `liquidity_ratio_evolution` | Distribution des variations local_balance/capacity | Jensen-Shannon | 0.1 |
| `fee_elasticity` | Variation du volume suite à une variation des frais | Corrélation de Pearson | 0.6 |

## Nouvelles Fonctionnalités

### 1. Identification et Traçabilité

Chaque calibration est identifiée de manière unique avec un format standardisé :
```
calibration_{timestamp}_{node_id}
```

La traçabilité est assurée par :
- Un hash des données d'entrée pour garantir l'intégrité
- Un archivage systématique de toutes les calibrations
- Un résumé markdown généré automatiquement avec les métriques clés

### 2. Visualisateur Automatique

Un tableau de bord complet est généré automatiquement pour chaque calibration, incluant :
- Histogrammes croisés comparant les distributions réelles et simulées
- Courbes d'évolution des ratios de liquidité
- Heatmaps de divergence par métrique
- Résumé des paramètres optimaux

### 3. Tests de Stabilité et Robustesse

#### Test de Stabilité
Vérifie la stabilité des calibrations en exécutant 5 fois le même processus sur les mêmes données :
- Calcul de l'écart-type des scores entre exécutions
- Verdict : Stable (<0.01), Moyennement stable (<0.05), Instable (≥0.05)
- Rapport détaillé sur la variabilité des paramètres

#### Test de Robustesse
Évalue la robustesse face à des données bruitées ou manquantes :
- Calibration sur données propres vs données corrompues
- Paramétrable : niveau de bruit (0-1) et taux de valeurs manquantes (0-1)
- Comparaison des paramètres et calcul de la différence moyenne

### 4. Mode Replay

Permet de rejouer une calibration précédente sur un nouveau jeu de données :
- Charge les paramètres d'une calibration archivée
- Exécute le simulateur avec ces paramètres sur de nouvelles données
- Compare les distributions et calcule les nouveaux p-values
- Génère un nouveau tableau de bord comparatif

## Processus Complet

1. **Collecte des données** 
   - À partir de LNBits ou fichier externe
   - Prétraitement et nettoyage automatique

2. **Calibration**
   - Grid search paramétrable
   - Tests statistiques pour chaque métrique
   - Optimisation du score global pondéré

3. **Validation**
   - Test final d'indistinguabilité (KS sur volumes)
   - Test optionnel de stabilité (5 exécutions)
   - Test optionnel de robustesse (données bruitées)

4. **Visualisation et Rapport**
   - Tableau de bord automatique avec visualisations
   - Rapport markdown avec verdict et recommandations
   - Archivage pour traçabilité et reproductibilité

## Utilisation

### Calibration Standard

```bash
python3 scripts/run_calibration.py --node-id=<node_id> --days=14 --iterations=100 --output-dir=data/calibration_results
```

### Test de Stabilité

```bash
python3 scripts/run_calibration.py --node-id=<node_id> --days=14 --iterations=50 --output-dir=data/stability_test --stability-check
```

### Test de Robustesse

```bash
python3 scripts/run_calibration.py --node-id=<node_id> --output-dir=data/robust_test --robust-test --noise-level=0.2 --missing-rate=0.2
```

### Replay d'une Calibration

```bash
python3 scripts/run_calibration.py --node-id=<node_id> --replay=calibration_20250508_123456_node123
```

## Indicateurs de Qualité

Le système attribue automatiquement un profil de stabilité à chaque calibration :

| Profil | Critère | Interprétation |
|--------|---------|----------------|
| Stable | Écart-type < 0.1 | Paramètres très fiables |
| Fragile | Écart-type < 0.3 | Paramètres moyennement fiables |
| Incohérent | Écart-type ≥ 0.3 | Paramètres peu fiables |

Pour les tests de robustesse, la différence moyenne entre paramètres propres et bruités :

| Verdict | Critère | Interprétation |
|---------|---------|----------------|
| Très robuste | Différence < 10% | Excellente résistance au bruit |
| Moyennement robuste | Différence < 25% | Bonne résistance au bruit |
| Peu robuste | Différence ≥ 25% | Sensibilité élevée au bruit |

## Conclusion

Ce protocole rigoureux assure que notre simulateur génère des données statistiquement indistinguables des données réelles, avec une traçabilité complète, des visualisations automatiques, et des tests de stabilité et robustesse. Ces améliorations garantissent la fiabilité des résultats et facilitent l'itération rapide sur le modèle. 