#!/usr/bin/env python3
import asyncio
from src.optimizers.core_fee_optimizer import CoreFeeOptimizer

# ID du nœud daznode
NODE_ID = "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"

async def main():
    # Initialiser l'optimiseur avec dry_run=True pour commencer
    optimizer = CoreFeeOptimizer(
        node_pubkey=NODE_ID,
        dry_run=True,  # Mode simulation
        max_changes_per_run=5,  # Limite de 5 changements par exécution
        backup_enabled=True  # Activer les sauvegardes
    )
    
    try:
        # Lancer l'optimisation
        print(f"Démarrage de l'optimisation des frais pour le nœud {NODE_ID[:8]}...")
        channels = await optimizer.get_channels()
        
        if not channels:
            print("Aucun canal trouvé.")
            return
            
        print(f"Analyse de {len(channels)} canaux...")
        
        # Sauvegarder l'état initial
        backup_file = await optimizer._backup_channel_state(channels)
        print(f"État initial sauvegardé dans {backup_file}")
        
        # Appliquer les changements
        results = await optimizer._apply_fee_changes(channels)
        
        # Afficher les résultats
        print("\nRésultats de l'optimisation:")
        print(f"Succès: {len(results['successful'])} canaux")
        print(f"Échecs: {len(results['failed'])} canaux")
        
        for success in results['successful']:
            print(f"\n✅ Canal {success['channel_id']}:")
            print(f"  Ancien: {success['old_fee_rate']} ppm, {success['old_base_fee']} msats")
            print(f"  Nouveau: {success['new_fee_rate']} ppm, {success['new_base_fee']} msats")
            
        for failure in results['failed']:
            print(f"\n❌ Canal {failure['channel_id']}:")
            print(f"  Erreur: {failure.get('error', 'Inconnue')}")
            
    except Exception as e:
        print(f"Erreur lors de l'optimisation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 