#!/usr/bin/env python3
# anthropic_integration.py

import os
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import anthropic

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/anthropic_integration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AnthropicIntegration:
    """Intégration de l'API Anthropic pour le système RAG"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialisation de l'intégration Anthropic"""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("La clé API Anthropic est requise. Définissez ANTHROPIC_API_KEY dans les variables d'environnement.")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-opus-4-20250514"  # Modèle par défaut
        logger.info("Intégration Anthropic initialisée")

    async def generate_node_analysis(self, node_data: Dict[str, Any], max_tokens: int = 4000) -> str:
        """Génère une analyse détaillée d'un nœud Lightning en utilisant Claude"""
        try:
            # Préparation des données pour le prompt
            node_info = {
                "alias": node_data.get("alias", "Inconnu"),
                "pubkey": node_data.get("pubkey", "Inconnu"),
                "channels": len(node_data.get("channels", [])),
                "metrics": node_data.get("metrics", {}),
                "fees": node_data.get("fees", {})
            }

            # Construction du prompt système
            system_prompt = """Tu es un expert en analyse de nœuds Lightning Network.
            Ta mission est d'analyser les données d'un nœud et de générer un rapport détaillé en français.
            Le rapport doit inclure :
            1. Un résumé exécutif de la position du nœud
            2. Une analyse des métriques de centralité
            3. Une analyse des canaux et de la liquidité
            4. Des recommandations d'optimisation des frais
            5. Un plan d'action concret
            Format ton rapport en Markdown."""

            # Construction du prompt utilisateur
            user_prompt = f"""Analyse le nœud Lightning suivant :
            
            {json.dumps(node_info, indent=2)}
            
            Génère un rapport détaillé en français."""

            # Appel à l'API Anthropic
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt
                            }
                        ]
                    }
                ]
            )

            # Extraction et formatage de la réponse
            analysis = message.content[0].text if isinstance(message.content, list) else message.content
            
            logger.info(f"Analyse générée pour le nœud {node_info['alias']}")
            return analysis

        except Exception as e:
            logger.error(f"Erreur lors de la génération de l'analyse: {str(e)}")
            return f"Erreur lors de l'analyse du nœud: {str(e)}"

    async def generate_market_analysis(self, market_data: Dict[str, Any], max_tokens: int = 4000) -> str:
        """Génère une analyse du marché Lightning Network"""
        try:
            # Construction du prompt système
            system_prompt = """Tu es un expert en analyse du marché Lightning Network.
            Ta mission est d'analyser les données du marché et de générer un rapport détaillé en français.
            Le rapport doit inclure :
            1. Un aperçu global du réseau
            2. Les tendances principales
            3. Les opportunités et risques
            4. Des recommandations stratégiques
            Format ton rapport en Markdown."""

            # Construction du prompt utilisateur
            user_prompt = f"""Analyse les données du marché Lightning Network suivantes :
            
            {json.dumps(market_data, indent=2)}
            
            Génère un rapport détaillé en français."""

            # Appel à l'API Anthropic
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt
                            }
                        ]
                    }
                ]
            )

            # Extraction et formatage de la réponse
            analysis = message.content[0].text if isinstance(message.content, list) else message.content
            
            logger.info("Analyse du marché générée")
            return analysis

        except Exception as e:
            logger.error(f"Erreur lors de la génération de l'analyse du marché: {str(e)}")
            return f"Erreur lors de l'analyse du marché: {str(e)}"

    async def generate_recommendations(self, node_data: Dict[str, Any], market_data: Dict[str, Any], max_tokens: int = 4000) -> str:
        """Génère des recommandations personnalisées basées sur l'analyse du nœud et du marché"""
        try:
            # Construction du prompt système
            system_prompt = """Tu es un expert en optimisation de nœuds Lightning Network.
            Ta mission est de générer des recommandations personnalisées basées sur l'analyse du nœud et du marché.
            Les recommandations doivent inclure :
            1. Optimisation des frais
            2. Gestion de la liquidité
            3. Stratégie de connexion
            4. Plan d'action détaillé
            Format tes recommandations en Markdown."""

            # Construction du prompt utilisateur
            combined_data = {
                "node": node_data,
                "market": market_data
            }

            user_prompt = f"""Génère des recommandations pour le nœud suivant, en tenant compte des conditions du marché :
            
            {json.dumps(combined_data, indent=2)}
            
            Fournis des recommandations détaillées en français."""

            # Appel à l'API Anthropic
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt
                            }
                        ]
                    }
                ]
            )

            # Extraction et formatage de la réponse
            recommendations = message.content[0].text if isinstance(message.content, list) else message.content
            
            logger.info(f"Recommandations générées pour le nœud {node_data.get('alias', 'Inconnu')}")
            return recommendations

        except Exception as e:
            logger.error(f"Erreur lors de la génération des recommandations: {str(e)}")
            return f"Erreur lors de la génération des recommandations: {str(e)}"

    def set_model(self, model_name: str) -> None:
        """Change le modèle Anthropic utilisé"""
        self.model = model_name
        logger.info(f"Modèle changé pour: {model_name}")

    def __str__(self) -> str:
        """Représentation string de l'intégration"""
        return f"AnthropicIntegration(model={self.model})" 