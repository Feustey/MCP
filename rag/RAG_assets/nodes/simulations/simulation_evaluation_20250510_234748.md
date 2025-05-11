# Évaluation des simulations de nœuds Lightning

Date de l'analyse: 2025-05-10 23:47:48
Simulations analysées: 20250510_234748

## Tableau comparatif des profils

| Profile | Score Global | Forwards | Taux de Succès (%) | Frais/Forward | Frais Totaux | Équilibre (%) | Perf. Index |
| --- | --- | --- | --- | --- | --- | --- | --- |
| routing_hub | 90.63 | 1016 | 92.2 | 791.4 | 804084 | 50.0 | 419.0337 |
| star | 84.53 | 544 | 99.3 | 885.0 | 481432 | 50.0 | 270.2064 |
| experimental | 70.15 | 376 | 77.2 | 873.7 | 328503 | 61.7 | 143.3858 |
| aggressive_fees | 68.00 | 129 | 80.3 | 1681.8 | 216948 | 50.0 | 98.4838 |
| normal | 66.99 | 152 | 99.2 | 584.8 | 88882 | 50.0 | 49.8526 |
| unstable | 64.49 | 103 | 88.0 | 790.9 | 81461 | 60.0 | 40.5295 |
| saturated | 58.28 | 315 | 67.6 | 1104.8 | 348029 | 94.4 | 132.9908 |
| inactive | 53.22 | 19 | 88.8 | 166.6 | 3165 | 50.0 | 1.5897 |
| abused | 41.38 | 230 | 58.7 | 222.5 | 51177 | 12.6 | 16.9971 |
| dead_node | 33.17 | 5 | 20.0 | 54.4 | 272 | 50.0 | 0.0308 |


## Recommandations par profil

### routing_hub
* Score global: 90.63
* Recommandation: **EXCELLENT: Performance optimale - Maintenir configuration**
* Performance Index: 419.0337

### star
* Score global: 84.53
* Recommandation: **BON: Performance satisfaisante - Optimisations mineures possibles**
* Performance Index: 270.2064

### experimental
* Score global: 70.15
* Recommandation: **ATTENTION: Taux de succès faible malgré l'activité - Réviser la politique tarifaire**
* Performance Index: 143.3858

### aggressive_fees
* Score global: 68.0
* Recommandation: **NORMAL: Performance dans la moyenne - Améliorations possibles**
* Performance Index: 98.4838

### normal
* Score global: 66.99
* Recommandation: **NORMAL: Performance dans la moyenne - Améliorations possibles**
* Performance Index: 49.8526

### unstable
* Score global: 64.49
* Recommandation: **NORMAL: Performance dans la moyenne - Améliorations possibles**
* Performance Index: 40.5295

### saturated
* Score global: 58.28
* Recommandation: **ATTENTION: Taux de succès faible malgré l'activité - Réviser la politique tarifaire**
* Performance Index: 132.9908

### inactive
* Score global: 53.22
* Recommandation: **ATTENTION: Activité très faible - Vérifier connectivité ou frais trop élevés**
* Performance Index: 1.5897

### abused
* Score global: 41.38
* Recommandation: **CRITIQUE: Rééquilibrer les canaux immédiatement et ajuster les frais**
* Performance Index: 16.9971

### dead_node
* Score global: 33.17
* Recommandation: **CRITIQUE: Rééquilibrer les canaux immédiatement et ajuster les frais**
* Performance Index: 0.0308



## Métriques clés à surveiller

1. **Taux de succès** - Objectif: >95%
2. **Équilibre de liquidité** - Objectif: proche de 50%
3. **Performance Index** - Mesure synthétique de l'efficacité du capital

## Classement des profils par score global

```
routing_hub     [########################################] 90.63
star            [#####################################   ] 84.53
experimental    [##############################          ] 70.15
aggressive_fees [##############################          ] 68.0
normal          [#############################           ] 66.99
unstable        [############################            ] 64.49
saturated       [#########################               ] 58.28
inactive        [#######################                 ] 53.22
abused          [##################                      ] 41.38
dead_node       [##############                          ] 33.17
```
