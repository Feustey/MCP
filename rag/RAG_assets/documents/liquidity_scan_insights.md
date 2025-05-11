# Analyse de Liquidité des Nœuds Lightning Network

## Méthodologie LNRouter pour le Scan de Liquidité

### Critères d'Éligibilité des Nœuds
- **Exigence minimale** : Au moins 15 canaux de 2 500 000 sats minimum de capacité
- Les canaux multiples avec le même pair comptent comme un seul canal
- Au moins 6 canaux doivent avoir 500 000 sats de capacité entrante

### Procédure de Test
- Le test envoie un paiement de 500 000 sats dans les deux directions du canal
- Un paiement réussi indique que cette direction peut effectivement router des sats
- Seul un sous-ensemble de canaux est testé, avec une priorité pour les canaux à plus forte capacité
- L'objectif n'est pas de tester tous les canaux mais d'obtenir un échantillon représentatif

### Intervalle de Scan
- LNRouter mesure chaque nœud éligible dans un intervalle de 4 semaines
- Cette fréquence permet de suivre l'évolution de la liquidité dans le temps

## Interprétation des Résultats

### Types de Canaux Selon la Liquidité
1. **Canaux Bidirectionnels** : Capables de router des paiements dans les deux sens
2. **Canaux Sortants Uniquement** : Peuvent seulement envoyer des paiements
3. **Canaux Entrants Uniquement** : Peuvent seulement recevoir des paiements
4. **Canaux Bloqués** : Ne peuvent router de paiements dans aucune direction

### Score de Liquidité
Le score de liquidité d'un nœud est calculé selon la formule:
```
Score = (BidirectionalChannels × 0.7) + (OutboundOnlyChannels × 0.15) + (InboundOnlyChannels × 0.15)
```
Cette formule:
- Valorise fortement les canaux bidirectionnels (70% du score)
- Accorde une importance modérée aux canaux à sens unique (15% chacun)
- Pénalise les canaux totalement bloqués (0% de contribution)

## Implications pour la Sélection des Pairs

Pour optimiser un nœud Lightning, privilégier les connexions avec:
1. Des nœuds ayant un haut taux de canaux bidirectionnels (>80%)
2. Des nœuds démontrant une stabilité dans les tests de liquidité
3. Des nœuds avec un score de liquidité élevé (>75/100)

## Recommandations pour l'Équilibrage

### Stratégies d'Équilibrage Proactives
- Maintenir une liquidité suffisante dans les canaux pour passer le seuil de 500 000 sats
- Surveiller régulièrement l'évolution de la liquidité bidirectionnelle des canaux
- Prioriser le rééquilibrage des canaux qui ont perdu leur capacité bidirectionnelle

### Exemple d'Objectifs
- Ratio de canaux bidirectionnels: >70%
- Seuil minimal de liquidité par direction: 500 000 sats
- Fréquence de rééquilibrage: Dès que le ratio bidirectionnel passe sous 65%

## Intégration avec d'Autres Métriques

La liquidité des canaux doit être analysée conjointement avec:
- Le temps de réponse HTLC (cible: <0.3s)
- La centralité du nœud dans le réseau
- Le taux de réussite des paiements routés

Cette approche multi-dimensionnelle permet d'optimiser non seulement la capacité à router des paiements, mais aussi la vitesse et la fiabilité du routage.

Source: [LNRouter Liquidity Scan](https://blog.lnrouter.app/liquidity-scan) 