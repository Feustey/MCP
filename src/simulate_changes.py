import asyncio
import os
from dotenv import load_dotenv
from lnbits_operations import LNbitsOperations
from network_optimizer import NetworkOptimizer
from redis_operations import RedisOperations

# Chargement des variables d'environnement
load_dotenv(".env.local")

async def simulate_changes(node_id: str):
    """Simule les changements recommandés sur le testnet"""
    try:
        # Initialisation des composants
        redis_ops = RedisOperations(redis_url=os.getenv("REDIS_URL"))
        network_optimizer = NetworkOptimizer(redis_ops)
        lnbits = LNbitsOperations(
            api_url=os.getenv("LNBITS_API_URL"),
            admin_key=os.getenv("LNBITS_ADMIN_KEY"),
            invoice_key=os.getenv("LNBITS_INVOICE_KEY")
        )
        
        print("\nRécupération des suggestions d'optimisation...")
        suggestions = await network_optimizer.get_optimization_suggestions(node_id)
        
        # Application des suggestions
        for suggestion in suggestions:
            print(f"\nApplication de la suggestion : {suggestion['type']}")
            
            if suggestion['type'] == "fee_optimization":
                # Ajustement des frais
                channel_id = suggestion['channel_id']
                new_fee_rate = int(suggestion['details']['recommended_fee_rate'].split('-')[0])  # Prend la valeur minimale
                print(f"Mise à jour des frais pour le canal {channel_id}")
                print(f"Nouveau taux de frais : {new_fee_rate} ppm")
                
                try:
                    result = await lnbits.update_channel_policy(
                        channel_id=channel_id,
                        fee_rate=new_fee_rate
                    )
                    print("Résultat :", result)
                except Exception as e:
                    print(f"Erreur lors de la mise à jour des frais : {str(e)}")
                    
            elif suggestion['type'] == "liquidity":
                # Rebalancing de canal
                channel_id = suggestion['channel_id']
                amount = int(suggestion['details']['amount_to_move'].replace(',', ''))
                direction = suggestion['details']['direction']
                print(f"Rebalancing du canal {channel_id}")
                print(f"Montant : {amount:,} sats, Direction : {direction}")
                
                try:
                    # Pour le test, nous utilisons un nœud cible par défaut
                    target_node = "03e7156ae33b0a208d0744199163177e909e80176e55d97a2f221ede0f934dd9ad"
                    result = await lnbits.rebalance_channel(
                        channel_id=channel_id,
                        amount=amount,
                        target_node=target_node
                    )
                    print("Résultat :", result)
                except Exception as e:
                    print(f"Erreur lors du rebalancing : {str(e)}")
                    
            elif suggestion['type'] == "network_growth":
                # Ouverture de nouveaux canaux
                current = suggestion['details']['current_channels']
                recommended = int(suggestion['details']['recommended_channels'].split('-')[0])
                channels_to_open = recommended - current
                
                print(f"Ouverture de {channels_to_open} nouveaux canaux")
                
                for partner in suggestion['details']['suggested_partners'][:channels_to_open]:
                    try:
                        # Pour le test, nous utilisons une capacité de 5M sats
                        amount = 5_000_000
                        result = await lnbits.open_channel(
                            node_id=partner,
                            amount=amount
                        )
                        print(f"Canal ouvert avec {partner}")
                        print("Résultat :", result)
                    except Exception as e:
                        print(f"Erreur lors de l'ouverture du canal : {str(e)}")
                        
        print("\nSimulation terminée !")
        
    except Exception as e:
        print(f"Erreur lors de la simulation : {str(e)}")
        
if __name__ == "__main__":
    # ID du nœud à analyser
    NODE_ID = "02aced13b08adcbe1e0897ad3b26e4525e1a9cdb76c86ed4aa42a518045bcb7e9f"
    
    # Exécution de la simulation
    asyncio.run(simulate_changes(NODE_ID)) 