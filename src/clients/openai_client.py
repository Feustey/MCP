"""
Client OpenAI pour la génération de recommandations prioritaires MCP
Version adaptée de mcp-light pour le projet MCP principal
"""

import openai
import os
import logging
import json
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

logger = logging.getLogger("mcp.openai")

class OpenAIClient:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY est requis")
        
        openai.api_key = self.api_key
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.max_retries = 3
        self.timeout = 45.0
    
    async def test_connection(self) -> bool:
        """Test de connexion à l'API OpenAI"""
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5,
                timeout=10.0
            )
            logger.info("Connexion OpenAI réussie")
            return True
        except Exception as e:
            logger.error(f"Erreur de connexion OpenAI: {str(e)}")
            return False
    
    async def generate_priority_actions(
        self, 
        pubkey: str,
        node_info: Dict[str, Any],
        recommendations: Dict[str, Any],
        context: str = "intermediate",
        goals: List[str] = None,
        max_actions: int = 5
    ) -> Dict[str, Any]:
        """Génère les actions prioritaires via OpenAI pour l'optimisation Lightning"""
        
        if goals is None:
            goals = ["routing_revenue", "connectivity", "liquidity"]
        
        prompt = self._build_mcp_prompt(pubkey, node_info, recommendations, context, goals, max_actions)
        
        for attempt in range(self.max_retries):
            try:
                response = await openai.ChatCompletion.acreate(
                    model=self.model,
                    messages=[
                        {
                            "role": "system", 
                            "content": "Tu es un expert en Lightning Network qui aide les opérateurs de nœuds à optimiser leurs performances. Réponds en français avec des recommandations concrètes, priorisées et techniques. Utilise les données MCP pour des analyses précises."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.7,
                    timeout=self.timeout
                )
                
                content = response.choices[0].message.content
                
                # Parser la réponse pour extraire les actions structurées
                return self._parse_mcp_response(content, pubkey)
                
            except Exception as e:
                logger.warning(f"Tentative {attempt + 1} échouée pour {pubkey}: {str(e)}")
                if attempt == self.max_retries - 1:
                    return {
                        "actions": [],
                        "analysis": f"Erreur lors de la génération des recommandations: {str(e)}",
                        "error": True,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                await asyncio.sleep(2 ** attempt)  # Backoff exponentiel
    
    async def analyze_node_performance(
        self, 
        pubkey: str, 
        metrics: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyse détaillée des performances du nœud avec recommandations stratégiques"""
        
        prompt = f"""
Analyse ce nœud Lightning Network et fournis une évaluation complète de ses performances.

NŒUD: {pubkey[:16]}...
MÉTRIQUES ACTUELLES:
{json.dumps(metrics, indent=2)}

DONNÉES HISTORIQUES:
{json.dumps(historical_data or {}, indent=2)}

Fournis une analyse structurée au format suivant:

SCORE GLOBAL: [0-100]
FORCES: [Points forts du nœud]
FAIBLESSES: [Points d'amélioration]
RECOMMANDATIONS STRATÉGIQUES: [3-5 recommandations prioritaires]
PRÉVISIONS: [Évolution probable des performances]
"""
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Tu es un analyste expert en Lightning Network spécialisé dans l'optimisation des nœuds."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.6,
                timeout=self.timeout
            )
            
            return {
                "analysis": response.choices[0].message.content,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": self.model,
                "pubkey": pubkey
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse pour {pubkey}: {str(e)}")
            return {
                "analysis": f"Erreur lors de l'analyse: {str(e)}",
                "error": True,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _build_mcp_prompt(
        self, 
        pubkey: str, 
        node_info: Dict[str, Any], 
        recommendations: Dict[str, Any],
        context: str,
        goals: List[str],
        max_actions: int
    ) -> str:
        """Construit le prompt optimisé pour MCP"""
        
        goals_str = ", ".join(goals)
        
        prompt = f"""
Analyse ce nœud Lightning Network et fournis {max_actions} actions prioritaires pour l'optimisation MCP.

NŒUD: {pubkey[:16]}...
NIVEAU OPÉRATEUR: {context}
OBJECTIFS: {goals_str}

DONNÉES DU NŒUD MCP:
{json.dumps(node_info, indent=2)}

RECOMMANDATIONS TECHNIQUES:
{json.dumps(recommendations, indent=2)}

Fournis exactement {max_actions} actions prioritaires au format suivant:

PRIORITÉ 1: [Action concrète technique]
JUSTIFICATION: [Analyse basée sur les métriques MCP]
IMPACT: [Résultat quantifiable attendu]
DIFFICULTÉ: [easy/medium/hard]
DÉLAI: [immediate/1-2 weeks/1 month]
COMMANDE: [Commande CLI ou API précise si applicable]

[Répéter pour chaque priorité...]

ANALYSE GLOBALE MCP:
[2-3 phrases sur l'état du nœud, stratégie recommandée et points critiques basés sur les données MCP]

MÉTRIQUES CLÉS À SURVEILLER:
[3 métriques importantes à suivre pour mesurer l'amélioration]
"""
        return prompt
    
    def _parse_mcp_response(self, content: str, pubkey: str) -> Dict[str, Any]:
        """Parse la réponse OpenAI avec support des améliorations MCP"""
        
        actions = []
        analysis = ""
        key_metrics = []
        
        try:
            lines = content.split('\n')
            current_action = {}
            in_analysis = False
            in_metrics = False
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('PRIORITÉ'):
                    if current_action:
                        actions.append(current_action)
                    
                    priority = len(actions) + 1
                    action_text = line.split(':', 1)[1].strip() if ':' in line else line
                    current_action = {
                        "priority": priority,
                        "action": action_text,
                        "reasoning": "",
                        "impact": "",
                        "difficulty": "medium",
                        "timeframe": "1-2 weeks",
                        "command": ""
                    }
                    
                elif line.startswith('JUSTIFICATION:'):
                    current_action["reasoning"] = line.split(':', 1)[1].strip()
                elif line.startswith('IMPACT:'):
                    current_action["impact"] = line.split(':', 1)[1].strip()
                elif line.startswith('DIFFICULTÉ:'):
                    current_action["difficulty"] = line.split(':', 1)[1].strip()
                elif line.startswith('DÉLAI:'):
                    current_action["timeframe"] = line.split(':', 1)[1].strip()
                elif line.startswith('COMMANDE:'):
                    current_action["command"] = line.split(':', 1)[1].strip()
                elif line.startswith('ANALYSE GLOBALE MCP:'):
                    in_analysis = True
                    if current_action:
                        actions.append(current_action)
                        current_action = {}
                elif line.startswith('MÉTRIQUES CLÉS À SURVEILLER:'):
                    in_metrics = True
                    in_analysis = False
                elif in_analysis and line and not line.startswith('MÉTRIQUES'):
                    analysis += line + " "
                elif in_metrics and line and line.startswith('-'):
                    key_metrics.append(line[1:].strip())
            
            # Ajouter la dernière action si elle existe
            if current_action and not in_analysis and not in_metrics:
                actions.append(current_action)
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing de la réponse OpenAI pour {pubkey}: {str(e)}")
            analysis = content  # Fallback: retourner le contenu brut
        
        return {
            "actions": actions,
            "analysis": analysis.strip(),
            "key_metrics": key_metrics,
            "timestamp": datetime.utcnow().isoformat(),
            "pubkey": pubkey,
            "total_actions": len(actions)
        } 