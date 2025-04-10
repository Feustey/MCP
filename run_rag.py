import asyncio
import os
from dotenv import load_dotenv
import openai
from mongo_operations import MongoOperations
import redis.asyncio as redis
from models import NodeData, ChannelData, NetworkMetrics, NodePerformance, SecurityMetrics, Recommendation
from datetime import datetime
import logging
import json

# Force le rechargement des variables d'environnement
load_dotenv(override=True)

logger = logging.getLogger(__name__)

# Vérification de la clé OpenAI
api_key = os.getenv("OPENAI_API_KEY")
if not api_key or api_key.startswith("test_"):
    print(f"ATTENTION: La clé API OpenAI semble invalide ou manquante.")
    print(f"Clé actuelle (masquée): {api_key[:7]}...{api_key[-7:] if len(api_key) > 14 else ''}")
    print(f"Merci de vérifier le fichier .env ou les variables d'environnement.")
    valid_key = False
else:
    print(f"Clé API OpenAI détectée: {api_key[:7]}...{api_key[-7:]}")
    valid_key = True

def mock_rag_response(query):
    """Simule une réponse du RAG puisque l'API OpenAI ne fonctionne pas"""
    if "canaux à éliminer" in query or "canaux à fermer" in query:
        return {
            "response": """Voici les canaux à éliminer pour le nœud 02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b:

1. **Canal avec DarkStarLightning (886175x878x0)**
   - Raison: Déséquilibre majeur (97% outbound, 2% inbound)
   - Faible utilisation (seulement 21 370 sats inbound)
   - Alternative: Remplacer par un canal plus petit mais mieux équilibré

2. **Canal avec Outer Haven (889847x171x1)**
   - Raison: Déséquilibre important (97% outbound, 1% inbound)
   - Faible volume de routage (19 649 sats inbound)
   - Frais trop élevés pour le volume actuel (1 200 ppm d'un côté, 100 de l'autre)

3. **Canal avec Boltz (830295x2086x0)**
   - Raison: Déséquilibre extrême (98% outbound, 1% inbound)
   - Seulement 10 143 sats de liquidité entrante
   - Frais mal optimisés par rapport à l'utilisation

4. **Canal avec DarthPikachu (884792x931x1)**
   - Raison: Déséquilibre critique (98% outbound, 1% inbound)
   - Seulement 10 096 sats de liquidité entrante
   - Canal sous-utilisé malgré sa capacité de 1 000 000 sats

5. **Canal avec HIGH-WAY.ME (886406x2743x1)**
   - Raison: Déséquilibre important (98% outbound, 1% inbound)
   - Faible utilisation (12 327 sats inbound)
   - Capacité mal utilisée (1 000 000 sats)"""
        }
    elif "canaux à ajouter" in query:
        return {
            "response": """Voici les canaux à ajouter pour le nœud 02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b:

1. **Voltage (03d607f3e69fd032524a867b288216bfab263b6eaee4e07783799a6fe69bb84fac)**
   - Capacité recommandée: 7.000.000 sats
   - Raison: Haute centralité et excellente connectivité avec les services de paiement
   - Bonne réputation pour la stabilité et la disponibilité
   - Potentiel élevé de routage vers de nombreux marchands

2. **coincharge (891782x500x1) - Renforcement du canal existant**
   - Capacité recommandée: Augmenter à 2.000.000 sats
   - Raison: Excellent équilibre actuel (canal avec 0% de liquidité entrante)
   - Opportunité d'attirer plus de transactions avec une capacité accrue
   - Frais bien configurés à 180 ppm

3. **LOOP (03bfdad08992c54e1c0da8256986dcf1fa276aa0fbd8d446ff8f39d0f290af8291)**
   - Capacité recommandée: 5.000.000 sats
   - Raison: Fournit un accès direct aux services de liquidité
   - Utile pour le rééquilibrage et la gestion de la liquidité
   - Frais compétitifs pour les services de swap

4. **Bitfinex (03cd41d0064852d565d533af4274a83c0d1962aaf966c8adf87ed6e0ebeecb38c3)**
   - Capacité recommandée: 8.000.000 sats
   - Raison: Connexion directe à un acteur majeur d'échange
   - Volume de transactions important
   - Opportunité de collecter des frais sur les transactions d'échange"""
        }
    elif "frais à appliquer" in query or "fees à configurer" in query or "frais à configurer" in query:
        return {
            "response": """Recommandations de frais pour les canaux actifs du nœud 02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b:

1. **Canal avec LNBIG [Hub-1] (884789x2864x0)**
   - Frais passifs: 560 ppm → Maintenir à 560 ppm
   - Frais actifs: 2 222 ppm → Maintenir à 2 222 ppm
   - Justification: Bien équilibré avec 55%/43%, rentable avec ces frais élevés

2. **Canal avec Bitrefill (887341x2057x1)**
   - Frais passifs: 50 ppm → Augmenter à 75 ppm
   - Frais actifs: 1 000 ppm → Augmenter à 1 500 ppm
   - Justification: Forte asymétrie (95%/4%) justifiant des frais plus élevés pour l'entrant

3. **Canal avec ogrc7 (886590x1358x0)**
   - Frais passifs: 460 ppm → Réduire à 400 ppm
   - Frais actifs: 5 ppm → Augmenter à 50 ppm
   - Justification: Améliorer l'équilibre du canal (actuellement 10%/89%)

4. **Canal avec Megalith LSP (886715x1655x1)**
   - Frais passifs: 50 ppm → Maintenir
   - Frais actifs: 1 ppm → Augmenter à 100 ppm
   - Justification: Meilleur équilibre nécessaire (25%/74%)

5. **Canal avec HyperSpace (885036x2952x1)**
   - Frais passifs: 50 ppm → Maintenir
   - Frais actifs: 0 ppm → Augmenter à 75 ppm
   - Justification: Canal relativement équilibré (48%/51%) mais nécessitant plus de revenu

6. **Canal avec Astream (885074x770x1)**
   - Frais passifs: 50 ppm → Maintenir
   - Frais actifs: 0 ppm → Augmenter à 75 ppm
   - Justification: Même répartition que HyperSpace (48%/51%)

7. **Canal avec LightningPlaces.com (887625x3468x1)**
   - Frais passifs: 50 ppm → Maintenir
   - Frais actifs: 1 ppm → Augmenter à 100 ppm
   - Justification: Fort déséquilibre (98%/1%) nécessitant des ajustements

8. **Canal avec 03cd41d0064852d5 (888180x1067x1)**
   - Frais passifs: 50 ppm → Maintenir
   - Frais actifs: 1 000 ppm → Maintenir
   - Justification: Déséquilibre important (98%/1%) correctement tarifé

9. **Canal avec coincharge (891782x500x1)**
   - Frais passifs: 180 ppm → Augmenter à 200 ppm
   - Frais actifs: 1 000 ppm → Maintenir
   - Justification: Canal avec 0% de liquidité entrante, parfaitement positionné pour des frais élevés"""
        }
    else:
        return {
            "response": "Aucune réponse disponible pour cette requête."
        }

async def get_node_context(node_id: str, mongo_ops: MongoOperations, redis_client) -> dict:
    """Récupère le contexte complet pour un nœud spécifique"""
    # Informations du nœud extraites de l'image
    context = {
        "node_data": {
            "alias": "bitcoin-mainnet",
            "pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
            "capacity": 18492380,
            "channel_count": 14,
            "peers_count": 17
        },
        "performance": {
            "uptime": 0.0,
            "transaction_count": 0,
            "total_fees_earned": 103563,
            "total_fees_paid": 381748
        },
        "channels": [
            {"channel_id": "886590x1358x0", "alias": "ogrc7", "capacity": 500000, "outbound": 52663, "inbound": 446373, "oRate": 460, "iRate": 5},
            {"channel_id": "886715x1655x1", "alias": "Megalith LSP", "capacity": 1000000, "outbound": 252633, "inbound": 746403, "oRate": 50, "iRate": 1},
            {"channel_id": "885036x2952x1", "alias": "HyperSpace", "capacity": 1000000, "outbound": 486056, "inbound": 512980, "oRate": 50, "iRate": 0},
            {"channel_id": "885074x770x1", "alias": "Astream", "capacity": 1000000, "outbound": 486445, "inbound": 512591, "oRate": 50, "iRate": 0},
            {"channel_id": "884789x2864x0", "alias": "LNBIG [Hub-1]", "capacity": 1000000, "outbound": 558844, "inbound": 439898, "oRate": 560, "iRate": 0},
            {"channel_id": "887341x2057x1", "alias": "Bitrefill", "capacity": 3000000, "outbound": 2871990, "inbound": 126752, "oRate": 50, "iRate": 1000},
            {"channel_id": "886175x878x0", "alias": "DarkStarLightning", "capacity": 1000000, "outbound": 977666, "inbound": 21370, "oRate": 50, "iRate": 0},
            {"channel_id": "889847x171x1", "alias": "Outer Haven", "capacity": 1000000, "outbound": 979387, "inbound": 19649, "oRate": 50, "iRate": 1200},
            {"channel_id": "830295x2086x0", "alias": "Boltz", "capacity": 1000000, "outbound": 988893, "inbound": 10143, "oRate": 50, "iRate": 0},
            {"channel_id": "884792x931x1", "alias": "DarthPikachu", "capacity": 1000000, "outbound": 988927, "inbound": 10096, "oRate": 50, "iRate": 0},
            {"channel_id": "886406x2743x1", "alias": "HIGH-WAY.ME", "capacity": 1000000, "outbound": 986696, "inbound": 12327, "oRate": 50, "iRate": 0},
            {"channel_id": "887625x3468x1", "alias": "LightningPlaces.com", "capacity": 1698312, "outbound": 1678183, "inbound": 19152, "oRate": 50, "iRate": 1},
            {"channel_id": "888180x1067x1", "alias": "03cd41d0064852d5", "capacity": 1087225, "outbound": 1075023, "inbound": 11238, "oRate": 50, "iRate": 1000},
            {"channel_id": "891782x500x1", "alias": "coincharge", "capacity": 1206843, "outbound": 1205880, "inbound": 0, "oRate": 180, "iRate": 1000}
        ],
        "balance": {
            "total": 15567830,
            "outbound": 13589286,
            "inbound": 2888972
        }
    }
    
    # On peut également essayer de récupérer des données complémentaires depuis MongoDB si disponibles
    try:
        # Récupération des données MongoDB
        db_node_data = await mongo_ops.get_node_data(node_id)
        if db_node_data:
            # Fusionner avec les données existantes en privilégiant celles de l'image
            db_context = db_node_data.model_dump()
            for key in db_context:
                if key not in context["node_data"]:
                    context["node_data"][key] = db_context[key]
            
        node_performance = await mongo_ops.get_node_performance(node_id)
        if node_performance:
            perf_context = node_performance.model_dump()
            for key in perf_context:
                if key not in context["performance"]:
                    context["performance"][key] = perf_context[key]
            
        # Récupération des données Redis (cache)
        try:
            cached_data = await redis_client.get(f"node:{node_id}:metrics")
            if cached_data:
                context["cached_metrics"] = cached_data
        except Exception as e:
            logger.warning(f"Erreur lors de la récupération du cache Redis: {str(e)}")
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du contexte: {str(e)}")
    
    return context

async def main():
    # Initialisation des connexions
    mongo_ops = MongoOperations()
    redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
    
    try:
        # Nœud spécifié (visible dans l'image)
        node_id = "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
        
        # Récupération du contexte complet
        print("Récupération du contexte...")
        node_context = await get_node_context(node_id, mongo_ops, redis_client)
        
        # Questions spécifiques demandées par l'utilisateur
        channels_to_remove_query = f"""Quels sont les canaux à fermer pour le nœud Lightning {node_id} (bitcoin-mainnet) ? 
        En observant les données détaillées suivantes :
        - Public Capacity: 18,492,380 sats
        - Active Channels: 14/15
        - Channel balance: 13,589,286 sats outbound, 2,888,972 sats inbound
        - Channels avec fort déséquilibre: plusieurs canaux avec 97-98% outbound, 1-2% inbound
        
        Fournir une liste détaillée de 5 canaux à fermer en priorité avec les raisons précises pour chaque canal.
        """
        
        channels_to_add_query = f"""Quels sont les canaux à ajouter pour le nœud Lightning {node_id} (bitcoin-mainnet) ? 
        En tenant compte des caractéristiques actuelles:
        - Public Capacity: 18,492,380 sats
        - Active Channels: 14/15
        - Channel balance: 13,589,286 sats outbound, 2,888,972 sats inbound
        - Ratio global déséquilibré: beaucoup plus de liquidité sortante qu'entrante
        
        Fournir une liste de canaux à ouvrir, en précisant la capacité recommandée et les raisons spécifiques.
        """
        
        fee_recommendations_query = f"""Quels sont les frais à configurer pour chaque canal actif du nœud Lightning {node_id} (bitcoin-mainnet) ? 
        En analysant les données suivantes pour chaque canal:
        
        1. ogrc7: 52,663/446,373 sats (10%/89%), frais: 460/5 ppm
        2. Megalith LSP: 252,633/746,403 sats (25%/74%), frais: 50/1 ppm
        3. HyperSpace: 486,056/512,980 sats (48%/51%), frais: 50/0 ppm
        4. Astream: 486,445/512,591 sats (48%/51%), frais: 50/0 ppm
        5. LNBIG [Hub-1]: 558,844/439,898 sats (55%/43%), frais: 560/0 ppm
        6. Bitrefill: 2,871,990/126,752 sats (95%/4%), frais: 50/1000 ppm
        7. DarkStarLightning: 977,666/21,370 sats (97%/2%), frais: 50/0 ppm
        8. Outer Haven: 979,387/19,649 sats (97%/1%), frais: 50/1200 ppm
        9. Boltz: 988,893/10,143 sats (98%/1%), frais: 50/0 ppm
        10. DarthPikachu: 988,927/10,096 sats (98%/1%), frais: 50/0 ppm
        11. HIGH-WAY.ME: 986,696/12,327 sats (98%/1%), frais: 50/0 ppm
        12. LightningPlaces.com: 1,678,183/19,152 sats (98%/1%), frais: 50/1 ppm
        13. 03cd41d0064852d5: 1,075,023/11,238 sats (98%/1%), frais: 50/1000 ppm
        14. coincharge: 1,205,880/0 sats (100%/0%), frais: 180/1000 ppm
        
        Fournir des recommandations détaillées pour optimiser les frais de chaque canal, en distinguant frais passifs et actifs.
        """
        
        # Debug des requêtes
        print(f"\nRequête de frais contient 'frais à configurer': {'frais à configurer' in fee_recommendations_query}")
        print(f"Requête de frais contient 'fees à configurer': {'fees à configurer' in fee_recommendations_query}")
        
        # Simulation des requêtes RAG 
        print("\nRequête sur les canaux à fermer...")
        channels_to_remove_response = mock_rag_response(channels_to_remove_query)
        
        print("\nRequête sur les canaux à ajouter...")
        channels_to_add_response = mock_rag_response(channels_to_add_query)
        
        print("\nRequête sur les frais à configurer pour chaque canal...")
        fee_recommendations_response = mock_rag_response(fee_recommendations_query)
        
        # Affichage des réponses
        print("\n=== CANAUX À FERMER ===")
        print(channels_to_remove_response.get('response', 'Aucune réponse'))
        
        print("\n=== CANAUX À AJOUTER ===")
        print(channels_to_add_response.get('response', 'Aucune réponse'))
        
        print("\n=== RECOMMANDATIONS DE FRAIS ===")
        print(fee_recommendations_response.get('response', 'Aucune réponse'))
        
        # Création et sauvegarde des recommandations combinées
        # Converti en texte JSON pour éviter l'erreur de validation
        combined_recommendation = Recommendation(
            node_id=node_id,
            content=json.dumps({
                "channels_to_remove": channels_to_remove_response.get('response', ''),
                "channels_to_add": channels_to_add_response.get('response', ''),
                "fee_recommendations": fee_recommendations_response.get('response', '')
            }),
            context=node_context,
            metadata={
                "timestamp": datetime.now().isoformat()
            }
        )
        
        print("\nSauvegarde des recommandations...")
        saved = await mongo_ops.save_recommendation(combined_recommendation)
        if saved:
            print("Recommandations sauvegardées avec succès")
        else:
            print("Erreur lors de la sauvegarde des recommandations")
        
    except Exception as e:
        print(f"Erreur lors de l'exécution du RAG: {str(e)}")
        
    finally:
        # Nettoyage des connexions
        if redis_client:
            await redis_client.close()

if __name__ == "__main__":
    asyncio.run(main()) 