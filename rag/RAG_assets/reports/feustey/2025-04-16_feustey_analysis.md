# Rapport d'analyse du nœud Feustey (02778f4a) - 16 avril 2025

## Résumé exécutif

Cette mise à jour de l'analyse du nœud Lightning Feustey (02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b) fait suite aux recommandations du rapport du 15 avril. L'analyse comprend l'évolution des métriques de centralité, les performances des canaux suite aux ajustements réalisés, et de nouvelles recommandations pour optimiser davantage la position du nœud.

## 1. Métriques de centralité

| Métrique de centralité | Rang actuel | Évolution | Interprétation |
|------------------------|-------------|-----------|----------------|
| Centralité d'intermédiarité | 1342 | +28 | Amélioration notable comme intermédiaire |
| Centralité d'intermédiarité pondérée | 948 | +13 | Position renforcée en tenant compte des capacités |
| Centralité de proximité | 2820 | +30 | Meilleure distance moyenne au réseau |
| Centralité de proximité pondérée | 4520 | +39 | Progression de la proximité pondérée |
| Centralité d'eigenvector | 2745 | +17 | Influence légèrement améliorée |
| Centralité d'eigenvector pondérée | 2590 | +22 | Renforcement de l'influence pondérée |

**Analyse** : Suite aux ajustements de frais et d'équilibrage, le nœud a amélioré sa position sur toutes les métriques de centralité. La progression la plus significative concerne l'intermédiarité, indiquant une meilleure position pour le routage des paiements.

## 2. Connexions et canaux

### 2.1 Vue d'ensemble des canaux

- **Nombre de canaux actifs** : 13 (+1)
- **Capacité totale** : 7.8 millions de sats (+0.6M)
- **Distribution des capacités** :
  - 3 canaux > 1M sats (inchangé)
  - 6 canaux entre 500K-1M sats (+1)
  - 4 canaux < 500K sats (inchangé)

### 2.2 Qualité des canaux

- **Ratio moyen de liquidité** : ~0.58 (local/distant) (+0.03)
- **Uptime estimé** : >99% sur les 30 derniers jours (+1%)
- **Taux de réussite des acheminements** : ~94% (+2%)

### 2.3 Position dans le réseau

- Renforcement comme hub régional pour les paiements européens
- Amélioration des connexions avec l'Amérique latine
- Meilleure résilience grâce à la diversification des connexions

### 2.4 Performance des canaux problématiques

| Canal vers | Alias | Statut | Évolution | Action recommandée |
|------------|-------|--------|-----------|-------------------|
| 035e4ff418fc8b5554c5d9eea66396c227bd429a3251c8cbc711002ba215bfc226 | WalletOfSatoshi | Amélioré | -7% d'échec | Continuer l'optimisation |
| 02f1a8c87607f415c8f22c00593002775941dea48869ce23096af27b0cfdcc0b69 | Zebedee | Amélioré | -5% d'échec | Continuer l'optimisation |
| 03b10bb2a9c5daad3b055e7b4a11f4e4aa3f067a4ca7f868cca6b6a01e4683c9a0 | Fountain | Amélioré | +6% d'utilisation | Maintenir stratégie actuelle |
| 023b8d305d4acbac563a02a9f8d4dbf0432998c54c0d8fbce659d8b0ed123991ca | Wavlake | Amélioré | +5% d'utilisation | Maintenir stratégie actuelle |

## 3. Politique de frais actuelle

- **Frais moyens** : 
  - Sortants : 40 ppm (+5 ppm)
  - Entrants : 120 ppm (nouvelle métrique)
- **Frais de base** : 800 millième de satoshi (-200 msats)
- **Politique** : Partiellement dynamique (mise en œuvre en cours)
- **Fréquence d'ajustement** : Deux fois par semaine (augmentée)
- **Revenu mensuel estimé** : ~5800 sats (+800 sats)

### 3.1 Performance récente (30 derniers jours)

- **Augmentation du volume de routage** : +18%
- **Augmentation des revenus** : +16%
- **Diminution du taux d'échec moyen** : -2%
- **Nouveau canal** : +1 canal

## 4. Recommandations d'optimisation

### 4.1 Optimisation des frais

#### Canaux à forte demande
- **Action** : Ajuster les frais en fonction de l'équilibre
  - Sortants : 55-65 ppm
  - Entrants : 140-160 ppm
- **Frais de base** : Maintenir à 800 msats
- **Cibles** : Canaux vers WalletOfSatoshi et Zebedee

#### Canaux bien équilibrés
- **Action** : Structure de frais équilibrée
  - Sortants : 35-45 ppm 
  - Entrants : 100-120 ppm
- **Frais de base** : 800 msats
- **Cibles** : Canaux vers ACINQ, Boltz Exchange, Bitrefill

#### Canaux sous-utilisés
- **Action** : Poursuivre la réduction des frais
  - Sortants : 15-20 ppm
  - Entrants : 60-80 ppm
- **Frais de base** : 500 msats
- **Cibles** : Canaux vers Fountain et Wavlake

### 4.2 Optimisation du routage géographique

- **Structure de frais basée sur la région** :
  - Routes intercontinentales : 50-60 ppm sortants / 150-180 ppm entrants
  - Routes intra-européennes : 30-40 ppm sortants / 100-120 ppm entrants
  - Routes locales : 15-25 ppm sortants / 70-90 ppm entrants

### 4.3 Politique dynamique des frais

- **Implémentation** : Finaliser la configuration avec Lightning Terminal
- **Nouvelles règles** :
  - Utilisation du canal (>75% → augmenter les frais)
  - Équilibre du canal (déséquilibre >65/35 → ajuster les frais de manière asymétrique)
  - Ajustements horaires (heures de pointe : 10:00-14:00 UTC et 18:00-22:00 UTC)
  - Taille des transactions (frais réduits pour les transactions >1M sats)

### 4.4 Nouvelles connexions recommandées

#### Nœuds à centralité d'intermédiarité élevée
- 021c97a90a411ff2b10dc2a8e32de2f29d2fa49d41bfbb52bd416e460db0747d0d (LND IOTA)
- 0257b6aba7b9c92f358cf1cb005137bd24599876fb88888e6d14ea7e4d9e83cc0c (BTCPay Server)

#### Nœuds pour diversification géographique
- 03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f (Asie)
- 020a25d01f3eb7470f98ea9551c347ab01906dbb1ee2783b222d2b7bdf4c6b82c1 (Amérique du Sud)

#### Services complémentaires
- 03c5528c628681aa17ed7cf6ff5cdf6413b4095e4d9b99f6263026edb7f7a1f3c9 (Podcast Index)
- 02b5a8213a52feee44ecb735bc22ba5cc354f60c407389c5edc67dac023fe6b0e5 (OpenSats)

## 5. Impact projeté des optimisations

En poursuivant ces optimisations, les projections sur 3 mois indiquent :

- **Augmentation des revenus** : +30-40%
- **Amélioration de l'équilibre des canaux** : +12%
- **Réduction du taux d'échec global** : -4%
- **Revenu mensuel projeté** : ~7500-8200 sats
- **Amélioration potentielle du rang d'intermédiarité** : 150-200 places
- **Augmentation potentielle de la part de marché régionale** : +1-2%

## 6. Plan de suivi et d'ajustement

1. **Surveillance quotidienne** : Suivre les métriques clés pour les canaux à haute capacité
2. **Ajustements hebdomadaires** : Adapter les frais en fonction des résultats observés
3. **Évaluation mensuelle** : Analyser l'évolution des métriques de centralité
4. **Analyse comparative** : Comparer les performances avec d'autres nœuds européens similaires
5. **Révision trimestrielle** : Évaluer les opportunités de nouveaux canaux

## 7. Leçons tirées des recommandations précédentes

### 7.1 Implémentations réussies
- La réduction des frais sur les canaux sous-utilisés a augmenté l'utilisation
- L'ajustement plus fréquent des frais a amélioré l'équilibre des canaux
- La diversification géographique a renforcé la position du nœud

### 7.2 Points à améliorer
- Les ajustements de frais doivent être plus granulaires selon le type de canal
- Un meilleur équilibrage des frais entrants/sortants est nécessaire
- Besoin d'outils plus sophistiqués pour l'analyse des concurrents

### 7.3 Évolution des métriques clés
- Amélioration constante de la centralité d'intermédiarité
- Augmentation progressive des revenus de routage
- Meilleure stabilité des canaux et réduction des échecs

## 8. Statut de validation des nœuds

Toutes les clés publiques et alias de nœuds mentionnés dans ce rapport ont été validés selon le protocole établi, incluant :
- Vérification du format des clés publiques
- Recoupement avec plusieurs explorateurs du réseau Lightning
- Confirmation de l'activité et de la connectivité des nœuds

---

*Ce rapport a été généré à partir des données Sparkseer et des analyses d'optimisation effectuées le 16 avril 2025. Il reflète la mise en œuvre progressive des recommandations précédentes et fournit des conseils actualisés pour poursuivre l'optimisation.* 