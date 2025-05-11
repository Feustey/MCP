# Évaluation des simulations de nœuds Lightning

Date de l'analyse: 2025-05-10 23:18:54
Simulations analysées: 20250510_181515

## Tableau comparatif des profils

| Profile | Score Global | Forwards | Taux de Succès (%) | Frais/Forward | Frais Totaux | Équilibre (%) | Perf. Index |
| --- | --- | --- | --- | --- | --- | --- | --- |
| routing_hub | 90.57 | 1073 | 91.5 | 765.0 | 820869 | 50.0 | 424.5974 |
| star | 84.46 | 542 | 100.0 | 871.6 | 472393 | 50.0 | 267.0815 |
| aggressive_fees | 68.74 | 129 | 83.4 | 1771.3 | 228502 | 50.0 | 107.7805 |
| normal | 66.03 | 163 | 93.0 | 575.4 | 93790 | 50.0 | 49.3069 |
| unstable | 63.17 | 99 | 85.6 | 782.0 | 77419 | 60.0 | 37.4708 |
| saturated | 58.85 | 282 | 70.7 | 1136.5 | 320483 | 94.4 | 128.1336 |
| inactive | 53.13 | 18 | 86.1 | 193.6 | 3484 | 50.0 | 1.6961 |
| experimental | 50.08 | 146 | 33.6 | 1082.3 | 158010 | 66.5 | 30.0251 |
| abused | 41.90 | 230 | 60.5 | 225.5 | 51867 | 11.0 | 17.7518 |
| dead_node | 33.18 | 4 | 20.4 | 49.5 | 198 | 50.0 | 0.0229 |


## Recommandations par profil

### routing_hub
* Score global: 90.57
* Recommandation: **EXCELLENT: Performance optimale - Maintenir configuration**
* Performance Index: 424.5974

### star
* Score global: 84.46
* Recommandation: **BON: Performance satisfaisante - Optimisations mineures possibles**
* Performance Index: 267.0815

### aggressive_fees
* Score global: 68.74
* Recommandation: **NORMAL: Performance dans la moyenne - Améliorations possibles**
* Performance Index: 107.7805

### normal
* Score global: 66.03
* Recommandation: **NORMAL: Performance dans la moyenne - Améliorations possibles**
* Performance Index: 49.3069

### unstable
* Score global: 63.17
* Recommandation: **NORMAL: Performance dans la moyenne - Améliorations possibles**
* Performance Index: 37.4708

### saturated
* Score global: 58.85
* Recommandation: **ATTENTION: Taux de succès faible malgré l'activité - Réviser la politique tarifaire**
* Performance Index: 128.1336

### inactive
* Score global: 53.13
* Recommandation: **ATTENTION: Activité très faible - Vérifier connectivité ou frais trop élevés**
* Performance Index: 1.6961

### experimental
* Score global: 50.08
* Recommandation: **CRITIQUE: Rééquilibrer les canaux immédiatement et ajuster les frais**
* Performance Index: 30.0251

### abused
* Score global: 41.9
* Recommandation: **ATTENTION: Taux de succès faible malgré l'activité - Réviser la politique tarifaire**
* Performance Index: 17.7518

### dead_node
* Score global: 33.18
* Recommandation: **CRITIQUE: Rééquilibrer les canaux immédiatement et ajuster les frais**
* Performance Index: 0.0229



## Métriques clés à surveiller

1. **Taux de succès** - Objectif: >95%
2. **Équilibre de liquidité** - Objectif: proche de 50%
3. **Performance Index** - Mesure synthétique de l'efficacité du capital

## Classement des profils par score global

```
routing_hub     [########################################] 90.57
star            [#####################################   ] 84.46
aggressive_fees [##############################          ] 68.74
normal          [#############################           ] 66.03
unstable        [###########################             ] 63.17
saturated       [#########################               ] 58.85
inactive        [#######################                 ] 53.13
experimental    [######################                  ] 50.08
abused          [##################                      ] 41.9
dead_node       [##############                          ] 33.18
```
