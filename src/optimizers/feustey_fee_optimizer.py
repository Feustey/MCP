#!/usr/bin/env python3
import csv
import os
from datetime import datetime
from pathlib import Path
import pandas as pd

# Chemin des fichiers de rapport
INPUT_CSV = Path("rag/RAG_assets/reports/feustey/active-channels-feustey.csv")
OUTPUT_DIR = Path("rag/RAG_assets/reports/feustey")
OUTPUT_FILE = OUTPUT_DIR / "feustey_fees_optimization.md"

def read_channel_data():
    """Lit les données des canaux depuis le fichier CSV."""
    print(f"Lecture des données depuis {INPUT_CSV}")
    
    if not INPUT_CSV.exists():
        print(f"Erreur: Le fichier {INPUT_CSV} n'existe pas.")
        return None
    
    try:
        # Lire le CSV avec pandas pour faciliter les manipulations
        df = pd.read_csv(INPUT_CSV)
        print(f"Données chargées: {len(df)} canaux")
        return df
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier CSV: {e}")
        return None

def optimize_fees(channels_df):
    """Optimise les frais pour chaque canal en fonction de ses caractéristiques."""
    print("Optimisation des frais pour chaque canal...")
    
    if channels_df is None or len(channels_df) == 0:
        return None
    
    # Créer une copie du DataFrame pour les recommandations
    recommendations = channels_df.copy()
    
    # Ajouter des colonnes pour les recommandations
    recommendations['Rec_oRate'] = None
    recommendations['Rec_oBase'] = None
    recommendations['Rec_iRate'] = None
    recommendations['Rec_iBase'] = None
    recommendations['Raison'] = None
    
    # Pour chaque canal, générer des recommandations de frais optimisées
    for index, row in recommendations.iterrows():
        # Extraire les données pertinentes
        capacity = int(str(row['Capacity']).replace(',', ''))
        outbound = int(str(row['Outbound Liquidity']).replace(',', ''))
        inbound = int(str(row['Inbound Liquidity']).replace(',', ''))
        current_oRate = row['oRate']
        current_oBase = row['oBase']
        current_iRate = row['iRate']
        current_iBase = row['iBase']
        peer_alias = row['Peer Alias']
        
        # Calculer pourcentages de liquidité
        outbound_pct = outbound / capacity * 100 if capacity > 0 else 0
        inbound_pct = inbound / capacity * 100 if capacity > 0 else 0
        
        # Logique d'optimisation des frais
        # 1. Canal déséquilibré avec beaucoup de liquidité sortante
        if outbound_pct > 80:
            recommendations.at[index, 'Rec_oRate'] = min(100, current_oRate * 1.5)  # Augmenter frais sortants
            recommendations.at[index, 'Rec_oBase'] = max(1000, current_oBase)
            recommendations.at[index, 'Rec_iRate'] = max(1, current_iRate * 0.7)  # Diminuer frais entrants
            recommendations.at[index, 'Rec_iBase'] = 0  # Éliminer frais de base entrants
            recommendations.at[index, 'Raison'] = "Déséquilibre (liquidité sortante élevée)"
            
        # 2. Canal déséquilibré avec beaucoup de liquidité entrante
        elif inbound_pct > 80:
            recommendations.at[index, 'Rec_oRate'] = max(1, current_oRate * 0.7)  # Diminuer frais sortants
            recommendations.at[index, 'Rec_oBase'] = 0  # Éliminer frais de base sortants
            recommendations.at[index, 'Rec_iRate'] = min(3000, current_iRate * 1.5)  # Augmenter frais entrants
            recommendations.at[index, 'Rec_iBase'] = max(1000, current_iBase)
            recommendations.at[index, 'Raison'] = "Déséquilibre (liquidité entrante élevée)"
            
        # 3. Canal équilibré
        elif 40 <= outbound_pct <= 60:
            # Maintenir un équilibre avec des frais modérés
            recommendations.at[index, 'Rec_oRate'] = 30
            recommendations.at[index, 'Rec_oBase'] = 1000
            recommendations.at[index, 'Rec_iRate'] = 1000
            recommendations.at[index, 'Rec_iBase'] = 0
            recommendations.at[index, 'Raison'] = "Canal bien équilibré"
            
        # 4. Canal avec un pair notable (hubs connus)
        elif any(hub in peer_alias.lower() for hub in ['lnbig', 'bitrefill', 'ln+', 'walletofsatoshi']):
            # Stratégie pour les nœuds importants - optimiser pour le routage
            recommendations.at[index, 'Rec_oRate'] = 25
            recommendations.at[index, 'Rec_oBase'] = 0
            recommendations.at[index, 'Rec_iRate'] = 1500
            recommendations.at[index, 'Rec_iBase'] = 0
            recommendations.at[index, 'Raison'] = "Nœud important (optimisé pour routage)"
            
        # 5. Cas par défaut - ajustement modéré
        else:
            recommendations.at[index, 'Rec_oRate'] = 30
            recommendations.at[index, 'Rec_oBase'] = 500
            recommendations.at[index, 'Rec_iRate'] = 750
            recommendations.at[index, 'Rec_iBase'] = 0
            recommendations.at[index, 'Raison'] = "Ajustement standard"
    
    return recommendations

def generate_report(recommendations_df):
    """Génère un rapport Markdown avec les recommandations."""
    print("Génération du rapport...")
    
    if recommendations_df is None:
        return False
    
    try:
        # Créer le répertoire de sortie si nécessaire
        OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
        
        # Générer le contenu du rapport
        content = f"""# Rapport d'optimisation des frais pour le nœud feustey

*Généré le {datetime.now().strftime('%Y-%m-%d à %H:%M:%S')}*

## Résumé
Ce rapport présente des recommandations pour optimiser les frais de chaque canal du nœud feustey. L'objectif est d'équilibrer la liquidité et d'améliorer la rentabilité du routage.

## Tableau des recommandations

| Channel ID | Peer Alias | Capacité | Out Liquidity | In Liquidity | Out% | In% | Frais actuels (out) | Frais actuels (in) | Frais recommandés (out) | Frais recommandés (in) | Raison |
|------------|------------|----------|---------------|--------------|------|-----|---------------------|--------------------|--------------------------|-----------------------|--------|
"""
        
        # Ajouter chaque canal au tableau
        for index, row in recommendations_df.iterrows():
            capacity = int(str(row['Capacity']).replace(',', ''))
            outbound = int(str(row['Outbound Liquidity']).replace(',', ''))
            inbound = int(str(row['Inbound Liquidity']).replace(',', ''))
            
            # Calculer pourcentages
            out_pct = outbound / capacity * 100 if capacity > 0 else 0
            in_pct = inbound / capacity * 100 if capacity > 0 else 0
            
            # Formater les frais actuels et recommandés
            current_fees_out = f"{row['oRate']} ppm + {row['oBase']} sats"
            current_fees_in = f"{row['iRate']} ppm + {row['iBase']} sats"
            
            rec_fees_out = f"{row['Rec_oRate']} ppm + {row['Rec_oBase']} sats"
            rec_fees_in = f"{row['Rec_iRate']} ppm + {row['Rec_iBase']} sats"
            
            content += f"| {row['Channel ID']} | {row['Peer Alias']} | {row['Capacity']} | {row['Outbound Liquidity']} | {row['Inbound Liquidity']} | {out_pct:.1f}% | {in_pct:.1f}% | {current_fees_out} | {current_fees_in} | {rec_fees_out} | {rec_fees_in} | {row['Raison']} |\n"
        
        # Ajouter des conseils généraux
        content += """
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
"""
        
        # Écrire le rapport dans le fichier
        with open(OUTPUT_FILE, 'w') as f:
            f.write(content)
            
        print(f"Rapport généré avec succès: {OUTPUT_FILE}")
        return True
    
    except Exception as e:
        print(f"Erreur lors de la génération du rapport: {e}")
        return False

def main():
    """Fonction principale."""
    print("Démarrage du processus d'optimisation des frais...")
    
    # Étape 1: Lire les données des canaux
    channels_df = read_channel_data()
    
    if channels_df is None:
        print("Impossible de continuer sans données de canaux.")
        return 1
    
    # Étape 2: Optimiser les frais pour chaque canal
    recommendations_df = optimize_fees(channels_df)
    
    if recommendations_df is None:
        print("Échec de l'optimisation des frais.")
        return 1
    
    # Étape 3: Générer le rapport
    success = generate_report(recommendations_df)
    
    if not success:
        print("Échec de la génération du rapport.")
        return 1
    
    print("Processus d'optimisation des frais terminé avec succès!")
    return 0

if __name__ == "__main__":
    main() 