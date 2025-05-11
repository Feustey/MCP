# Évaluation des simulations de nœuds Lightning

Date de l'analyse: 2025-05-10 23:19:50
Simulations analysées: 20250510_231949

## Tableau comparatif des profils

| Profile | Score Global | Forwards | Taux de Succès (%) | Frais/Forward | Frais Totaux | Équilibre (%) | Perf. Index |
| --- | --- | --- | --- | --- | --- | --- | --- |
| routing_hub | 90.76 | 1041 | 92.9 | 751.6 | 782389 | 50.0 | 411.1340 |
| star | 83.53 | 507 | 96.5 | 931.3 | 472150 | 50.0 | 257.6398 |
| aggressive_fees | 66.76 | 129 | 76.5 | 1727.0 | 222788 | 50.0 | 96.3748 |
| normal | 66.68 | 138 | 91.1 | 685.3 | 94571 | 50.0 | 48.7054 |
| unstable | 60.88 | 97 | 85.3 | 637.8 | 61864 | 60.0 | 29.8281 |
| saturated | 58.43 | 318 | 66.6 | 1104.3 | 351169 | 94.4 | 132.2192 |
| experimental | 54.39 | 164 | 42.6 | 1372.7 | 225121 | 59.7 | 54.2334 |
| inactive | 53.43 | 21 | 89.7 | 165.8 | 3481 | 50.0 | 1.7655 |
| abused | 42.57 | 259 | 61.1 | 204.3 | 52905 | 12.8 | 18.2816 |
| dead_node | 33.31 | 4 | 19.7 | 70.0 | 280 | 50.0 | 0.0312 |


## Recommandations par profil

### routing_hub
* Score global: 90.76
* Recommandation: **EXCELLENT: Performance optimale - Maintenir configuration**
* Performance Index: 411.134

### star
* Score global: 83.53
* Recommandation: **BON: Performance satisfaisante - Optimisations mineures possibles**
* Performance Index: 257.6398

### aggressive_fees
* Score global: 66.76
* Recommandation: **ATTENTION: Taux de succès faible malgré l'activité - Réviser la politique tarifaire**
* Performance Index: 96.3748

### normal
* Score global: 66.68
* Recommandation: **NORMAL: Performance dans la moyenne - Améliorations possibles**
* Performance Index: 48.7054

### unstable
* Score global: 60.88
* Recommandation: **NORMAL: Performance dans la moyenne - Améliorations possibles**
* Performance Index: 29.8281

### saturated
* Score global: 58.43
* Recommandation: **ATTENTION: Taux de succès faible malgré l'activité - Réviser la politique tarifaire**
* Performance Index: 132.2192

### experimental
* Score global: 54.39
* Recommandation: **CRITIQUE: Rééquilibrer les canaux immédiatement et ajuster les frais**
* Performance Index: 54.2334

### inactive
* Score global: 53.43
* Recommandation: **NORMAL: Performance dans la moyenne - Améliorations possibles**
* Performance Index: 1.7655

### abused
* Score global: 42.57
* Recommandation: **ATTENTION: Taux de succès faible malgré l'activité - Réviser la politique tarifaire**
* Performance Index: 18.2816

### dead_node
* Score global: 33.31
* Recommandation: **CRITIQUE: Rééquilibrer les canaux immédiatement et ajuster les frais**
* Performance Index: 0.0312



## Métriques clés à surveiller

1. **Taux de succès** - Objectif: >95%
2. **Équilibre de liquidité** - Objectif: proche de 50%
3. **Performance Index** - Mesure synthétique de l'efficacité du capital

## Classement des profils par score global

```
routing_hub     [########################################] 90.76
star            [####################################    ] 83.53
aggressive_fees [#############################           ] 66.76
normal          [#############################           ] 66.68
unstable        [##########################              ] 60.88
saturated       [#########################               ] 58.43
experimental    [#######################                 ] 54.39
inactive        [#######################                 ] 53.43
abused          [##################                      ] 42.57
dead_node       [##############                          ] 33.31
```
