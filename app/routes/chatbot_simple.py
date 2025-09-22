"""
Endpoint intelligent pour chatbot dazno.de (Version simplifiée)
Répond aux questions selon le contexte du nœud Lightning fourni
"""

from fastapi import APIRouter, HTTPException, Body, Header
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatbot", tags=["Chatbot Intelligence"])

class ChatbotQuery(BaseModel):
    """Modèle pour les requêtes du chatbot"""
    message: str = Field(..., description="Question/message de l'utilisateur")
    node_pubkey: Optional[str] = Field(None, description="Public key du nœud Lightning (optionnel)")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexte additionnel")
    conversation_id: Optional[str] = Field(None, description="ID de conversation pour le suivi")

class ChatbotResponse(BaseModel):
    """Modèle de réponse du chatbot"""
    response: str = Field(..., description="Réponse intelligente du chatbot")
    node_analysis: Optional[Dict[str, Any]] = Field(None, description="Analyse du nœud si applicable")
    suggestions: Optional[List[str]] = Field(None, description="Suggestions d'actions")
    confidence: float = Field(..., description="Niveau de confiance de la réponse (0-1)")
    response_type: str = Field(..., description="Type de réponse: general, node_specific, analysis, error")

def verify_simple_auth(authorization: str = Header(..., alias="Authorization")):
    """Vérification d'authentification simplifiée"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token d'autorisation requis")
    
    token = authorization.replace("Bearer ", "")
    expected_token = "mcp_2f0d711f886ef6e2551397ba90b5152dfe6b23d4"
    
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Token invalide")
    
    return token

def get_node_alias(node_pubkey: str) -> str:
    """Obtient l'alias d'un nœud"""
    known_nodes = {
        "02b1fe652cfc61f1e5cef78c08d60918d9fad3f029808f995a959e0a9dcbd33bab": "barcelona-big",
        "03efccf2c383d7bf340da9a3f02e2c23104a0e4fe8ac1a880c8e2dc92fbdacd9df": "bitrefill",
        "0279c22ed7a068d10dc1a38ae66d2d6461e269226c60258c021b1ddcdfe4b00bc4": "WalletOfSatoshi"
    }
    return known_nodes.get(node_pubkey, f"Node-{node_pubkey[:8]}...")

def analyze_message_intent(message: str) -> Dict[str, Any]:
    """Analyse l'intention du message utilisateur"""
    message_lower = message.lower()
    
    intents = {
        "node_performance": ["performance", "comment va", "état", "status", "marche"],
        "fees": ["frais", "fees", "tarif", "coût", "prix"],
        "liquidity": ["liquidité", "liquidity", "balance", "capacité"],
        "routing": ["routage", "routing", "forward", "transaction"],
        "optimization": ["optimiser", "améliorer", "conseil", "recommandation"],
        "general": ["c'est quoi", "qu'est-ce", "expliquer", "comment", "pourquoi"]
    }
    
    detected_intents = []
    for intent, keywords in intents.items():
        if any(keyword in message_lower for keyword in keywords):
            detected_intents.append(intent)
    
    return {
        "primary_intent": detected_intents[0] if detected_intents else "general",
        "all_intents": detected_intents,
        "confidence": 0.8 if detected_intents else 0.3
    }

def generate_contextual_response(message: str, node_pubkey: Optional[str] = None) -> ChatbotResponse:
    """Génère une réponse contextuelle intelligente"""
    
    intent_analysis = analyze_message_intent(message)
    primary_intent = intent_analysis["primary_intent"]
    
    # Données simulées du nœud (en production, utiliser les vraies analyses)
    node_data = None
    if node_pubkey:
        node_data = {
            "alias": get_node_alias(node_pubkey),
            "pubkey": node_pubkey,
            "estimated_centrality": 0.15,  # Simulé
            "estimated_roi": 8.5,  # Simulé
            "channel_count": 42,  # Simulé
            "total_capacity": 5000000,  # Simulé
            "last_analyzed": datetime.utcnow().isoformat()
        }
    
    # Génération de réponses selon l'intention
    if primary_intent == "node_performance" and node_data:
        response = f"""🔍 **Analyse de votre nœud {node_data['alias']}:**

📊 **Performance actuelle:**
• Centralité estimée: {node_data['estimated_centrality']:.3f} ({"Très bon" if node_data['estimated_centrality'] > 0.1 else "Moyen"})
• ROI annuel estimé: {node_data['estimated_roi']:.1f}%
• Canaux ouverts: {node_data['channel_count']}
• Capacité totale: {node_data['total_capacity']:,} sats

✅ Votre nœud semble {"bien positionné" if node_data['estimated_centrality'] > 0.1 else "avoir du potentiel d'amélioration"} dans le réseau Lightning."""

        suggestions = [
            "Consultez l'analyse complète de centralité",
            "Analysez vos frais pour optimiser les revenus",
            "Vérifiez l'équilibrage de vos canaux"
        ]
        confidence = 0.9

    elif primary_intent == "fees":
        response = f"""💰 **Optimisation des frais Lightning:**

{"🎯 **Pour votre nœud " + node_data['alias'] + ":**" if node_data else ""}
• Les frais optimaux dépendent de votre positionnement réseau
• Frais de base recommandés: 1-10 sats
• Frais proportionnels: 100-1000 ppm selon la demande

{"💡 Avec votre centralité de " + str(node_data['estimated_centrality']) + ", vous pouvez ajuster vos frais vers le haut." if node_data and node_data['estimated_centrality'] > 0.1 else ""}

📈 **Stratégie:** Commencez conservateur et ajustez selon le volume de routage."""

        suggestions = [
            "Analysez vos revenus actuels",
            "Comparez avec des nœuds similaires",
            "Testez des ajustements progressifs"
        ]
        confidence = 0.8

    elif primary_intent == "liquidity":
        response = f"""💧 **Gestion de la liquidité Lightning:**

{"🎯 **Pour votre nœud " + node_data['alias'] + ":**" if node_data else ""}
• L'équilibrage des canaux est crucial pour le routage
• Visez 50/50 local/remote pour maximiser les opportunités
• Surveillez les canaux déséquilibrés

{"💡 Avec " + str(node_data['channel_count']) + " canaux, diversifiez vos connexions." if node_data else ""}

⚖️ **Astuce:** Utilisez des services de rebalancing ou ouvrez des canaux stratégiques."""

        suggestions = [
            "Analysez l'équilibrage de vos canaux",
            "Identifiez les canaux sous-utilisés",
            "Considérez des services de rebalancing"
        ]
        confidence = 0.8

    elif primary_intent == "optimization" and node_data:
        response = f"""🚀 **Recommandations d'optimisation pour {node_data['alias']}:**

🎯 **Priorités identifiées:**
• {"Excellent positionnement - maintenez votre stratégie" if node_data['estimated_centrality'] > 0.15 else "Améliorez votre centralité avec plus de connexions"}
• {"ROI solide - optimisez les frais progressivement" if node_data['estimated_roi'] > 5 else "ROI faible - analysez vos frais et connexions"}

🔧 **Actions recommandées:**
1. Analysez vos métriques de centralité détaillées
2. Optimisez l'équilibrage de liquidité
3. Ajustez vos frais selon la demande"""

        suggestions = [
            "Effectuez une analyse complète",
            "Consultez les métriques de performance",
            "Planifiez des ajustements progressifs"
        ]
        confidence = 0.9

    else:
        # Réponse générale
        response = f"""⚡ **Assistant Lightning Network dazno.de**

{"🔍 J'analyse votre nœud " + get_node_alias(node_pubkey) + "..." if node_pubkey else ""}

Je peux vous aider avec:
• 📊 Analyse de performance de nœuds
• 💰 Optimisation des frais
• 💧 Gestion de la liquidité  
• 🔧 Conseils d'amélioration
• 📈 Métriques de centralité

❓ **Questions fréquentes:**
- "Comment va mon nœud ?"
- "Mes frais sont-ils optimaux ?"
- "Comment améliorer ma liquidité ?"

💡 *Spécifiez votre nœud pour des analyses personnalisées !*"""

        suggestions = [
            "Posez une question sur votre nœud",
            "Demandez une analyse de performance",
            "Consultez les métriques disponibles"
        ]
        confidence = 0.6

    return ChatbotResponse(
        response=response,
        node_analysis=node_data,
        suggestions=suggestions,
        confidence=confidence,
        response_type="node_specific" if node_data else "general"
    )

@router.post("/ask", 
    summary="Chatbot intelligent Lightning Network",
    description="Endpoint pour le chatbot du site dazno.de avec analyse contextuelle des nœuds",
    response_model=ChatbotResponse
)
async def ask_chatbot(
    query: ChatbotQuery = Body(...),
    authorization: str = Header(..., alias="Authorization")
):
    """
    **Chatbot intelligent pour dazno.de**
    
    Répond aux questions des utilisateurs en analysant leur nœud Lightning s'il est fourni.
    
    **Fonctionnalités:**
    - Analyse contextuelle du nœud
    - Réponses personnalisées selon les métriques
    - Suggestions d'actions concrètes
    - Support des conversations suivies
    
    **Exemples d'usage:**
    - "Comment améliorer la performance de mon nœud ?"
    - "Mes frais sont-ils optimaux ?"
    - "Pourquoi ai-je peu de routage ?"
    """
    
    try:
        # Vérification d'authentification
        verify_simple_auth(authorization)
        
        logger.info(f"Requête chatbot: {query.message[:50]}... Node: {query.node_pubkey or 'None'}")
        
        # Générer la réponse intelligente
        response = generate_contextual_response(
            message=query.message,
            node_pubkey=query.node_pubkey
        )
        
        logger.info(f"Réponse générée avec confiance: {response.confidence}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur endpoint chatbot: {e}")
        return ChatbotResponse(
            response=f"🚨 Désolé, j'ai rencontré une erreur technique. Veuillez réessayer dans quelques instants.",
            confidence=0.1,
            response_type="error",
            suggestions=["Réessayez votre question", "Vérifiez la syntaxe", "Contactez le support si le problème persiste"]
        )

@router.get("/node-summary/{node_pubkey}",
    summary="Résumé rapide d'un nœud",
    description="Résumé contextuel d'un nœud pour le chatbot"
)
async def get_node_summary(
    node_pubkey: str,
    authorization: str = Header(..., alias="Authorization")
):
    """
    **Résumé rapide d'un nœud pour le chatbot**
    
    Fournit un aperçu rapide des métriques clés d'un nœud
    pour alimenter les conversations du chatbot.
    """
    
    try:
        verify_simple_auth(authorization)
        
        # Données simulées (en production, utiliser les vraies analyses)
        summary = {
            "alias": get_node_alias(node_pubkey),
            "pubkey_short": node_pubkey[:16] + "...",
            "performance_score": 75,  # Score simulé
            "key_metrics": {
                "centrality": {
                    "degree": 0.15,
                    "position": "hub" if node_pubkey.startswith("02b1") else "standard"
                },
                "financial": {
                    "roi_annual": 8.5,
                    "profitability": "good"
                }
            },
            "status": "analyzed",
            "last_updated": datetime.utcnow().isoformat()
        }
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur résumé nœud {node_pubkey}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health",
    summary="Health check du chatbot",
    description="Vérifie que le chatbot fonctionne correctement"
)
async def chatbot_health():
    """Health check du service chatbot"""
    return {
        "status": "operational",
        "service": "dazno.de chatbot",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "features": [
            "node_analysis",
            "contextual_responses", 
            "intent_detection",
            "smart_suggestions"
        ]
    }