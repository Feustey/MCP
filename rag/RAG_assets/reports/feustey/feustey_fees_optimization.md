# Rapport d'optimisation des frais pour le nœud feustey

*Généré le 2025-05-07 à 09:41:09*

## Résumé
Ce rapport présente des recommandations pour optimiser les frais de chaque canal du nœud feustey. L'objectif est d'équilibrer la liquidité et d'améliorer la rentabilité du routage.

## Tableau des recommandations

| Channel ID | Peer Alias | Capacité | Out Liquidity | In Liquidity | Out% | In% | Frais actuels (out) | Frais actuels (in) | Frais recommandés (out) | Frais recommandés (in) | Raison |
|------------|------------|----------|---------------|--------------|------|-----|---------------------|--------------------|--------------------------|-----------------------|--------|
| 8947892864x0 | LNBIG [Hub-1] | 1000000 | 13268 | 985273 | 1.3% | 98.5% | 180 ppm + 0 sats | 700 ppm + 1000 sats | 125.99999999999999 ppm + 0 sats | 1050.0 ppm + 1000 sats | Déséquilibre (liquidité entrante élevée) |
| 885074x7770x1 | Justream | 1000000 | 485550 | 512591 | 48.6% | 51.3% | 30 ppm + 0 sats | 4000 ppm + 0 sats | 30 ppm + 1000 sats | 1000 ppm + 0 sats | Canal bien équilibré |
| 885036x2952x1 | HyperSpace = Saigon | 1000000 | 988637 | 10042 | 98.9% | 1.0% | 30 ppm + 0 sats | 1000 ppm + 0 sats | 45.0 ppm + 1000 sats | 700.0 ppm + 0 sats | Déséquilibre (liquidité sortante élevée) |
| 888180x1067x1 | 03cd4140064852656545 | 1087225 | 1074438 | 11239 | 98.8% | 1.0% | 30 ppm + 0 sats | 1 ppm + 1000 sats | 45.0 ppm + 1000 sats | 1 ppm + 0 sats | Déséquilibre (liquidité sortante élevée) |
| 891645x2759x1 | HIGH WAY ME | 2000000 | 1998453 | 0 | 99.9% | 0.0% | 30 ppm + 0 sats | 1000 ppm + 0 sats | 45.0 ppm + 1000 sats | 700.0 ppm + 0 sats | Déséquilibre (liquidité sortante élevée) |
| 894875x102x1 | 020c8f843f3128386a55 | 2000000 | 1998718 | 0 | 99.9% | 0.0% | 30 ppm + 0 sats | 1 ppm + 1000 sats | 45.0 ppm + 1000 sats | 1 ppm + 0 sats | Déséquilibre (liquidité sortante élevée) |
| 894877x2411x1 | barcelona | 4000000 | 3998453 | 0 | 100.0% | 0.0% | 30 ppm + 0 sats | 940 ppm + 0 sats | 45.0 ppm + 1000 sats | 658.0 ppm + 0 sats | Déséquilibre (liquidité sortante élevée) |
| 894879x2170x1 | Sunny Sarah * | 5000000 | 4998453 | 0 | 100.0% | 0.0% | 30 ppm + 0 sats | 1883 ppm + 0 sats | 45.0 ppm + 1000 sats | 1318.1 ppm + 0 sats | Déséquilibre (liquidité sortante élevée) |
| 894623x3560x1 | HIGH WAY ME | 600000 | 598542 | 0 | 99.8% | 0.0% | 30 ppm + 1200 sats | 1000 ppm + 0 sats | 45.0 ppm + 1200 sats | 700.0 ppm + 0 sats | Déséquilibre (liquidité sortante élevée) |

## Conseils généraux pour l'optimisation des frais

1. **Canaux à liquidité sortante élevée**:
   - Augmenter les frais sortants pour décourager l'utilisation excessive
   - Réduire les frais entrants pour encourager le rééquilibrage

2. **Canaux à liquidité entrante élevée**:
   - Réduire les frais sortants pour encourager l'utilisation
   - Augmenter les frais entrants pour tirer profit de la liquidité disponible

3. **Canaux équilibrés**:
   - Maintenir des frais modérés dans les deux directions
   - Surveiller régulièrement pour maintenir l'équilibre

4. **Canaux avec des nœuds importants**:
   - Réduire les frais sortants pour favoriser le routage
   - Maintenir des frais entrants compétitifs

## Instructions de mise en œuvre

Pour appliquer ces recommandations:

```bash
# Pour chaque canal, exécuter une commande comme:
lncli updatechanpolicy --base_fee_msat [BASE_FEE] --fee_rate [FEE_RATE] --time_lock_delta 40 --chan_point [CHANNEL_ID]
```

Exemple de script pour mettre à jour tous les canaux:

```python
import subprocess

channels = [
    # [channel_id, base_fee_out, fee_rate_out, base_fee_in, fee_rate_in]
    # Les valeurs sont extraites du tableau ci-dessus
]

for channel in channels:
    channel_id, base_fee_out, fee_rate_out, base_fee_in, fee_rate_in = channel
    
    # Mettre à jour les frais sortants
    cmd_out = f"lncli updatechanpolicy --base_fee_msat {base_fee_out*1000} --fee_rate {fee_rate_out/1000000} --time_lock_delta 40 --chan_point {channel_id}"
    
    # Exécuter la commande (à décommenter pour appliquer)
    # subprocess.run(cmd_out, shell=True)
    
    print(f"Frais mis à jour pour le canal {channel_id}")
```

## Suivi et ajustements

Il est recommandé de surveiller les effets de ces changements pendant 2 semaines et d'ajuster les frais en fonction des résultats observés.
