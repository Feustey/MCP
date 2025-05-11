# Plan d'Action pour le Nœud Feustey

## 1. Ajustements des Frais par Canal

### Vue d'ensemble
- Proposition globale : Réduction de 20% des frais actuels pour stimuler le routage
- Application d'une politique tarifaire adaptée au type de partenaire

### Détail des Modifications par Canal

#### Canaux à Frais Élevés (Priorité Haute)
1. Canal `ogre7 - 886590x1358x0`
   - Base fee : 5 msat → 4 msat
   - Fee rate : 360 ppm → 288 ppm
   - **Action** : Réduction significative des frais pour améliorer la compétitivité

#### Canaux à Frais Standards (Priorité Moyenne)
1. Canal `HIGH-WAY.ME - 891945x2759x1`
   - Base fee : 1200 msat → 960 msat
   - Fee rate : 50 ppm → 40 ppm

2. Canal `Bitrefill - 887341x2057x1`
   - Base fee : 1000 msat → 800 msat
   - Fee rate : 50 ppm → 40 ppm

3. Canal `03cd41d0064852d565d5 - 888180x1067x1`
   - Base fee : 1000 msat → 800 msat
   - Fee rate : 50 ppm → 40 ppm

4. Canal `coincharge - 891928x3068x1`
   - Base fee : 1000 msat → 800 msat
   - Fee rate : 50 ppm → 40 ppm

5. Canal `Babylon-4a - 891928x3068x2`
   - Base fee : 1000 msat → 800 msat
   - Fee rate : 50 ppm → 40 ppm

#### Canaux à Frais Minimaux (Priorité Basse)
1. Canal `LNB4G [Hub-1] - 884789x2864x0`
   - Base fee : 0 msat (maintenu)
   - Fee rate : 50 ppm → 40 ppm

2. Canal `Megalith LSP - 886715x1655x1`
   - Base fee : 1 msat → 0 msat
   - Fee rate : 50 ppm → 40 ppm

3. Canal `Astream - 885074x770x1`
   - Base fee : 0 msat (maintenu)
   - Fee rate : 50 ppm → 40 ppm

4. Canal `HyperSpace⚡Saigon - 885036x2952x1`
   - Base fee : 0 msat (maintenu)
   - Fee rate : 60 ppm → 48 ppm

5. Canal `LightningPlaces.com - 887625x3468x1`
   - Base fee : 1 msat → 0 msat
   - Fee rate : 50 ppm → 40 ppm

## 2. Recommandations pour les Canaux

### Canaux à Optimiser
- `ogre7` : Déséquilibre important (9% out / 89% in) - Réduire davantage les frais pour favoriser l'outbound
- `Bitrefill` : Déséquilibre critique (95% out / 4% in) - Considérer un rebalancement ou une politique spéciale
- `HyperSpace⚡Saigon`, `LightningPlaces.com`, `03cd41d...`, `coincharge`, `Babylon-4a`, `HIGH-WAY.ME` : 
  Tous avec ~98-99% d'outbound - Établir des frais préférentiels pour attirer l'inbound

### Canaux à Surveiller
- Canaux avec ≤1% d'inbound liquidity qui pourraient nécessiter un rebalancement

### Canaux à Ouvrir
- Recommandation d'ouverture de nouveaux canaux avec des nœuds à fort inbound potentiel pour équilibrer le réseau

## 3. Perspectives de Rentabilité

### Estimation sur 1 Mois
- Revenus actuels moyens : À déterminer (données historiques nécessaires)
- Revenus projetés avec nouvelle configuration :
  - Augmentation estimée du volume de 20-30% due aux frais plus compétitifs
  - Compensation de la baisse des frais unitaires par l'augmentation du volume

### Métriques à Surveiller
1. Volume de transactions par canal
2. Revenus des frais par canal
3. Taux de réussite des routes
4. Balance des canaux

## 4. Actions Immédiates

1. Appliquer les réductions de frais recommandées
2. Monitorer l'impact des changements sur 7 jours
3. Rebalancer les canaux fortement déséquilibrés
4. Ajuster si nécessaire en fonction des résultats

## 5. Suivi et Maintenance

- Révision hebdomadaire des métriques
- Ajustement mensuel des frais si nécessaire
- Évaluation trimestrielle de la stratégie globale

## 6. Commandes pour la Mise à Jour des Frais

Exécuter les commandes suivantes sur le nœud Feustey pour appliquer les nouvelles politiques de frais :

```bash
# Canal à Frais Élevés
lncli updatechanpolicy --chan_id=886590x1358x0 --base_fee_msat=4 --fee_rate=288.0

# Canaux à Frais Standards
lncli updatechanpolicy --chan_id=891945x2759x1 --base_fee_msat=960 --fee_rate=40.0
lncli updatechanpolicy --chan_id=887341x2057x1 --base_fee_msat=800 --fee_rate=40.0
lncli updatechanpolicy --chan_id=888180x1067x1 --base_fee_msat=800 --fee_rate=40.0
lncli updatechanpolicy --chan_id=891928x3068x1 --base_fee_msat=800 --fee_rate=40.0
lncli updatechanpolicy --chan_id=891928x3068x2 --base_fee_msat=800 --fee_rate=40.0

# Canaux à Frais Minimaux
lncli updatechanpolicy --chan_id=884789x2864x0 --base_fee_msat=0 --fee_rate=40.0
lncli updatechanpolicy --chan_id=886715x1655x1 --base_fee_msat=0 --fee_rate=40.0
lncli updatechanpolicy --chan_id=885074x770x1 --base_fee_msat=0 --fee_rate=40.0
lncli updatechanpolicy --chan_id=885036x2952x1 --base_fee_msat=0 --fee_rate=48.0
lncli updatechanpolicy --chan_id=887625x3468x1 --base_fee_msat=0 --fee_rate=40.0
```

---

*Note : Ce plan d'action est basé sur l'analyse des canaux actifs du nœud Feustey au 22 avril 2025 et devra être ajusté en fonction des résultats observés.*

*Note concernant les alias : Les noms d'alias indiqués ([LNBIG.com], [LNMarkets], etc.) sont basés sur une estimation des partenaires populaires du réseau Lightning. Vérifiez et corrigez ces informations via la commande `lncli listchannels` sur le nœud Feustey.* 