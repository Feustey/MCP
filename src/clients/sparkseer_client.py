"""
Client Sparkseer amélioré pour l'API MCP
Version adaptée de mcp-light avec enrichissement des données
"""

import httpx
import os
import logging
from typing import Optional, Dict, Any, List
import asyncio
from datetime import datetime

logger = logging.getLogger("mcp.sparkseer")

class SparkseerClient:
    def __init__(self):
        self.api_key = os.getenv("SPARKSEER_API_KEY")
        self.base_url = os.getenv("SPARKSEER_BASE_URL", "https://api.sparkseer.space")
        
        if not self.api_key:
            logger.warning("SPARKSEER_API_KEY non configuré - Fonctionnalités Sparkseer désactivées")
            self.enabled = False
        else:
            self.enabled = True
        
        self.headers = {
            "x-api-key": self.api_key or "",
            "Content-Type": "application/json",
            "User-Agent": "MCP-Lightning-Optimizer/1.0"
        }
        
        self.timeout = 30.0
        self.max_retries = 3
    
    async def test_connection(self) -> bool:
        """Test de connexion à l'API Sparkseer"""
        if not self.enabled:
            return False
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v1/network/summary",
                    headers=self.headers,
                    timeout=10.0
                )
                success = response.status_code == 200
                if success:
                    logger.info("Connexion Sparkseer établie")
                else:
                    logger.warning(f"Connexion Sparkseer échouée: {response.status_code}")
                return success
        except Exception as e:
            logger.error(f"Erreur de connexion Sparkseer: {str(e)}")
            return False
    
    async def get_node_info(self, pubkey: str) -> Optional[Dict[str, Any]]:
        """Récupère les informations complètes d'un nœud avec enrichissement"""
        if not self.enabled:
            logger.warning("Sparkseer désactivé - retour de données vides")
            return None
            
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    # Info de base du nœud
                    response = await client.get(
                        f"{self.base_url}/v1/node/{pubkey}",
                        headers=self.headers,
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 404:
                        logger.info(f"Nœud {pubkey[:16]}... non trouvé dans Sparkseer")
                        return None
                    
                    response.raise_for_status()
                    node_data = response.json()
                    
                    # Enrichissement avec données supplémentaires
                    enriched_data = await self._enrich_node_data(client, pubkey, node_data)
                    
                    logger.info(f"Données Sparkseer récupérées pour {pubkey[:16]}...")
                    return enriched_data
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"Erreur HTTP Sparkseer pour {pubkey}: {e.response.status_code}")
                if e.response.status_code == 429:  # Rate limit
                    await asyncio.sleep(2 ** attempt)
                    continue
                return None
            except Exception as e:
                logger.error(f"Tentative {attempt + 1} échouée pour {pubkey}: {str(e)}")
                if attempt == self.max_retries - 1:
                    return None
                await asyncio.sleep(1)
        
        return None
    
    async def _enrich_node_data(self, client: httpx.AsyncClient, pubkey: str, base_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrichit les données de base avec métriques, canaux et recommandations"""
        
        enriched = {
            **base_data,
            "enriched_at": datetime.utcnow().isoformat(),
            "source": "sparkseer_enhanced"
        }
        
        # Récupération parallèle des données supplémentaires
        tasks = [
            self._get_node_metrics(client, pubkey),
            self._get_node_channels(client, pubkey),
            self._get_network_position(client, pubkey)
        ]
        
        try:
            metrics, channels, position = await asyncio.gather(*tasks, return_exceptions=True)
            
            if isinstance(metrics, dict):
                enriched["metrics"] = metrics
            if isinstance(channels, dict):
                enriched["channels"] = channels
            if isinstance(position, dict):
                enriched["network_position"] = position
                
        except Exception as e:
            logger.warning(f"Erreur lors de l'enrichissement pour {pubkey}: {str(e)}")
        
        return enriched
    
    async def _get_node_metrics(self, client: httpx.AsyncClient, pubkey: str) -> Dict[str, Any]:
        """Récupère les métriques détaillées du nœud"""
        try:
            response = await client.get(
                f"{self.base_url}/v1/node/{pubkey}/metrics",
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Métriques non disponibles pour {pubkey}: {str(e)}")
        
        return {}
    
    async def _get_node_channels(self, client: httpx.AsyncClient, pubkey: str) -> Dict[str, Any]:
        """Récupère les informations des canaux"""
        try:
            response = await client.get(
                f"{self.base_url}/v1/node/{pubkey}/channels",
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Canaux non disponibles pour {pubkey}: {str(e)}")
        
        return {}
    
    async def _get_network_position(self, client: httpx.AsyncClient, pubkey: str) -> Dict[str, Any]:
        """Récupère la position dans le réseau"""
        try:
            response = await client.get(
                f"{self.base_url}/v1/node/{pubkey}/position",
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Position réseau non disponible pour {pubkey}: {str(e)}")
        
        return {}
    
    async def get_node_recommendations(self, pubkey: str) -> Dict[str, Any]:
        """Récupère les recommandations techniques pour un nœud"""
        if not self.enabled:
            return {"recommendations": []}
            
        try:
            async with httpx.AsyncClient() as client:
                # Recommandations parallèles
                tasks = [
                    self._get_channel_recommendations(client, pubkey),
                    self._get_fee_recommendations(client, pubkey),
                    self._get_liquidity_recommendations(client, pubkey)
                ]
                
                channel_recs, fee_recs, liquidity_recs = await asyncio.gather(
                    *tasks, return_exceptions=True
                )
                
                recommendations = []
                
                # Traiter les recommandations de canaux
                if isinstance(channel_recs, list):
                    recommendations.extend(channel_recs)
                
                # Traiter les recommandations de frais
                if isinstance(fee_recs, list):
                    recommendations.extend(fee_recs)
                
                # Traiter les recommandations de liquidité
                if isinstance(liquidity_recs, list):
                    recommendations.extend(liquidity_recs)
                
                return {
                    "recommendations": recommendations,
                    "total_count": len(recommendations),
                    "generated_at": datetime.utcnow().isoformat(),
                    "source": "sparkseer"
                }
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des recommandations pour {pubkey}: {str(e)}")
            return {"recommendations": []}
    
    async def _get_channel_recommendations(self, client: httpx.AsyncClient, pubkey: str) -> List[Dict[str, Any]]:
        """Récupère les recommandations de canaux"""
        try:
            response = await client.get(
                f"{self.base_url}/v1/node/{pubkey}/channel-recommendations",
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                recommendations = []
                
                for rec in data.get("recommendations", []):
                    recommendations.append({
                        "type": "channel_management",
                        "category": "connectivity",
                        "action": rec.get("action"),
                        "target_nodes": rec.get("target_nodes", []),
                        "reason": rec.get("reason"),
                        "priority": rec.get("priority", "medium"),
                        "estimated_impact": rec.get("impact", "unknown")
                    })
                
                return recommendations
        except Exception as e:
            logger.debug(f"Recommandations de canaux non disponibles: {str(e)}")
        
        return []
    
    async def _get_fee_recommendations(self, client: httpx.AsyncClient, pubkey: str) -> List[Dict[str, Any]]:
        """Récupère les recommandations de frais"""
        try:
            response = await client.get(
                f"{self.base_url}/v1/node/{pubkey}/suggested-fees",
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                recommendations = []
                
                for channel_id, rec in data.get("suggestions", {}).items():
                    recommendations.append({
                        "type": "fee_adjustment",
                        "category": "revenue",
                        "channel_id": channel_id,
                        "action": rec.get("action"),
                        "current_value": rec.get("current_fee"),
                        "suggested_value": rec.get("suggested_fee"),
                        "reason": rec.get("reason"),
                        "priority": "high" if rec.get("urgent") else "medium",
                        "estimated_revenue_impact": rec.get("revenue_impact")
                    })
                
                return recommendations
        except Exception as e:
            logger.debug(f"Recommandations de frais non disponibles: {str(e)}")
        
        return []
    
    async def _get_liquidity_recommendations(self, client: httpx.AsyncClient, pubkey: str) -> List[Dict[str, Any]]:
        """Récupère les recommandations de liquidité"""
        try:
            response = await client.get(
                f"{self.base_url}/v1/node/{pubkey}/liquidity-analysis",
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                recommendations = []
                
                for rec in data.get("recommendations", []):
                    recommendations.append({
                        "type": "liquidity_management",
                        "category": "operational",
                        "action": rec.get("action"),
                        "channels_affected": rec.get("channels", []),
                        "reason": rec.get("reason"),
                        "priority": rec.get("urgency", "medium"),
                        "amount_suggestion": rec.get("amount"),
                        "direction": rec.get("direction")  # inbound/outbound
                    })
                
                return recommendations
        except Exception as e:
            logger.debug(f"Recommandations de liquidité non disponibles: {str(e)}")
        
        return []
    
    async def get_network_summary(self) -> Dict[str, Any]:
        """Récupère un résumé du réseau Lightning"""
        if not self.enabled:
            return {}
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v1/network/summary",
                    headers=self.headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du résumé réseau: {str(e)}")
        
        return {} 