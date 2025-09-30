"""
Client Anthropic pour la génération de recommandations prioritaires MCP
Version adaptée pour remplacer OpenAI avec Claude
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime
from anthropic import AsyncAnthropic

logger = logging.getLogger("mcp.anthropic")

class AnthropicClient:
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY est requis")
        
        self.client = AsyncAnthropic(api_key=self.api_key)
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        self.max_retries = 3
        self.timeout = 45.0
    
    async def test_connection(self) -> bool:
        """Test de connexion à l'API Anthropic"""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=self._prepare_messages([
                    {"role": "user", "content": "Test"}
                ])
            )
            logger.info("Connexion Anthropic réussie")
            return True
        except Exception as e:
            logger.error(f"Erreur de connexion Anthropic: {str(e)}")
            return False

    async def generate_completion(
        self,
        messages: List[Dict[str, Any]],
        system_message: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """Génère une réponse textuelle via l'API Anthropic (interface générique)."""

        if not messages:
            raise ValueError("La liste des messages ne peut pas être vide")

        formatted_messages = self._prepare_messages(messages)

        for attempt in range(self.max_retries):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    system=system_message,
                    messages=formatted_messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return self._extract_text(response)
            except Exception as e:
                logger.warning(
                    "Erreur génération completion Anthropic (tentative %s/%s): %s",
                    attempt + 1,
                    self.max_retries,
                    str(e)
                )
                if attempt == self.max_retries - 1:
                    logger.error("Échec final génération completion Anthropic: %s", str(e))
                    raise RuntimeError(f"Anthropic completion failed: {e}") from e
                await asyncio.sleep(2 ** attempt)
    
    async def generate_priority_actions(
        self, 
        pubkey: str,
        node_info: Dict[str, Any],
        recommendations: Dict[str, Any],
        context: str = "intermediate",
        goals: List[str] = None,
        max_actions: int = 5
    ) -> Dict[str, Any]:
        """Génère les actions prioritaires via Anthropic pour l'optimisation Lightning"""
        
        if goals is None:
            goals = ["routing_revenue", "connectivity", "liquidity"]
        
        prompt = self._build_mcp_prompt(pubkey, node_info, recommendations, context, goals, max_actions)
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    system="Tu es un expert en Lightning Network qui aide les opérateurs de nœuds à optimiser leurs performances. Réponds en français avec des recommandations concrètes, priorisées et techniques. Utilise les données MCP pour des analyses précises.",
                    messages=self._prepare_messages([
                        {"role": "user", "content": prompt}
                    ]),
                    max_tokens=2000,
                    temperature=0.7
                )

                content = self._extract_text(response)
                
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
            response = await self.client.messages.create(
                model=self.model,
                system="Tu es un analyste expert en Lightning Network spécialisé dans l'optimisation des nœuds.",
                messages=self._prepare_messages([
                    {"role": "user", "content": prompt}
                ]),
                max_tokens=1500,
                temperature=0.6
            )
            
            return {
                "analysis": self._extract_text(response),
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
        """Parse la réponse Anthropic avec support des améliorations MCP"""
        
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
            logger.error(f"Erreur lors du parsing de la réponse Anthropic pour {pubkey}: {str(e)}")
            analysis = content  # Fallback: retourner le contenu brut
        
        return {
            "actions": actions,
            "analysis": analysis.strip(),
            "key_metrics": key_metrics,
            "timestamp": datetime.utcnow().isoformat(),
            "pubkey": pubkey,
            "total_actions": len(actions)
        }

    def _prepare_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Formate les messages pour l'API Anthropic (Messages API)."""
        prepared: List[Dict[str, Any]] = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            if isinstance(content, str):
                formatted_content = [{"type": "text", "text": content}]
            elif isinstance(content, list):
                formatted_content = []
                for block in content:
                    if isinstance(block, dict) and "type" in block:
                        formatted_content.append(block)
                    else:
                        formatted_content.append({"type": "text", "text": str(block)})
            else:
                formatted_content = [{"type": "text", "text": str(content)}]

            prepared.append({
                "role": role,
                "content": formatted_content
            })

        return prepared

    def _extract_text(self, response: Any) -> str:
        """Extrait le texte d'une réponse Anthropic Messages."""
        if not hasattr(response, "content"):
            return ""

        parts: List[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "".join(parts)
