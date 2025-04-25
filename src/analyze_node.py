import asyncio
from src.network_analyzer import NetworkAnalyzer
from src.network_optimizer import NetworkOptimizer
from src.redis_operations import RedisOperations
import os
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv(".env.local")

async def analyze_node(node_id: str):
    """Analyse un nœud et génère des recommandations spécifiques"""
    try:
        # Initialisation des composants
        redis_ops = RedisOperations(redis_url=os.getenv("REDIS_URL"))
        network_analyzer = NetworkAnalyzer(redis_ops)
        network_optimizer = NetworkOptimizer(redis_ops)
        
        # Analyse de la configuration du nœud
        config_analysis = await network_analyzer.analyze_node_configuration(node_id)
        
        # Récupération des suggestions d'optimisation
        optimization_suggestions = await network_optimizer.get_optimization_suggestions(node_id)
        
        # Affichage des résultats
        print("\nAnalyse de la configuration du nœud :")
        print("=====================================")
        
        # Gestion des canaux
        print("\nGestion des canaux :")
        print("-----------------")
        current_state = config_analysis["channel_management"]["current_state"]
        print(f"Capacité totale : {current_state['total_capacity']:,} sats")
        print(f"Nombre de canaux : {current_state['channel_count']}")
        print(f"Ratio de balance : {current_state['balance_ratio']:.2%}")
        print(f"Taille moyenne des canaux : {current_state['avg_channel_size']:,} sats")
        
        for rec in config_analysis["channel_management"]["recommendations"]:
            print(f"- {rec}")
            
        # Structure des frais
        print("\nStructure des frais :")
        print("------------------")
        for rec in config_analysis["fee_structure"]["recommendations"]:
            print(f"- {rec}")
            
        # Optimisation du réseau
        print("\nOptimisation du réseau :")
        print("---------------------")
        for rec in config_analysis["network_optimization"]["recommendations"]:
            print(f"- {rec}")
            
        # Suggestions d'optimisation
        print("\nSuggestions d'optimisation :")
        print("-------------------------")
        for suggestion in optimization_suggestions:
            print(f"\nType : {suggestion['type']}")
            print(f"Action : {suggestion['action']}")
            if 'channel_id' in suggestion:
                print(f"Canal : {suggestion['channel_id']}")
            print("Détails :")
            for key, value in suggestion["details"].items():
                print(f"  - {key}: {value}")
                
    except Exception as e:
        print(f"Erreur lors de l'analyse : {str(e)}")
        
if __name__ == "__main__":
    # ID du nœud à analyser
    NODE_ID = "02aced13b08adcbe1e0897ad3b26e4525e1a9cdb76c86ed4aa42a518045bcb7e9f"
    
    # Exécution de l'analyse
    asyncio.run(analyze_node(NODE_ID)) 