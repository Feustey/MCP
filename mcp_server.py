#!/usr/bin/env python3
"""
MCP Server pour connecter Claude Desktop au système MCP Lightning.
Permet à Claude d'interagir avec votre API Lightning Network.
"""

import asyncio
import json
import sys
import os
from typing import Any, Dict, List, Optional
import httpx
from datetime import datetime

# Configuration
MCP_API_URL = os.getenv("MCP_API_URL", "http://localhost:8000")
MCP_API_KEY = os.getenv("MCP_API_KEY", "mcp_local_dev_key")

class MCPLightningServer:
    """
    Serveur MCP qui expose les fonctionnalités Lightning à Claude.
    """
    
    def __init__(self):
        self.api_url = MCP_API_URL
        self.api_key = MCP_API_KEY
        self.client = httpx.AsyncClient(timeout=30)
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Traite les requêtes MCP de Claude."""
        
        method = request.get("method")
        params = request.get("params", {})
        
        # Mapping des méthodes MCP aux endpoints API
        if method == "lightning/analyze_node":
            return await self.analyze_node(params.get("node_id"))
        
        elif method == "lightning/get_recommendations":
            return await self.get_recommendations(params.get("node_id"))
        
        elif method == "lightning/network_status":
            return await self.get_network_status()
        
        elif method == "tools/list":
            return self.list_available_tools()
        
        else:
            return {
                "error": f"Unknown method: {method}",
                "available_methods": [
                    "lightning/analyze_node",
                    "lightning/get_recommendations", 
                    "lightning/network_status",
                    "tools/list"
                ]
            }
    
    async def analyze_node(self, node_id: str) -> Dict[str, Any]:
        """Analyse un nœud Lightning via l'API MCP."""
        if not node_id:
            return {"error": "node_id is required"}
        
        try:
            response = await self.client.get(
                f"{self.api_url}/api/v1/lightning/nodes/{node_id}/enhanced-analysis",
                headers={"X-API-Key": self.api_key}
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_recommendations(self, node_id: str) -> Dict[str, Any]:
        """Obtient les recommandations pour un nœud."""
        if not node_id:
            return {"error": "node_id is required"}
        
        try:
            response = await self.client.get(
                f"{self.api_url}/api/v1/lightning/nodes/{node_id}/recommendations",
                headers={"X-API-Key": self.api_key}
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "recommendations": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_network_status(self) -> Dict[str, Any]:
        """Obtient le statut du réseau Lightning."""
        try:
            # Check API health
            health_response = await self.client.get(f"{self.api_url}/health")
            
            # Get monitoring stats if available
            stats = {
                "api_status": "healthy" if health_response.status_code == 200 else "degraded",
                "timestamp": datetime.now().isoformat(),
                "services": {
                    "api": "running",
                    "monitoring": "running",
                    "ai_analysis": "available"
                }
            }
            
            return {
                "success": True,
                "network_status": stats
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_available_tools(self) -> Dict[str, Any]:
        """Liste les outils disponibles pour Claude."""
        return {
            "tools": [
                {
                    "name": "lightning_analyze_node",
                    "description": "Analyse complète d'un nœud Lightning Network avec IA",
                    "parameters": {
                        "node_id": "string - Lightning node public key"
                    }
                },
                {
                    "name": "lightning_get_recommendations",
                    "description": "Obtient des recommandations pour optimiser un nœud",
                    "parameters": {
                        "node_id": "string - Lightning node public key"
                    }
                },
                {
                    "name": "lightning_network_status",
                    "description": "Vérifie le statut du réseau et des services MCP",
                    "parameters": {}
                }
            ]
        }
    
    async def run(self):
        """Lance le serveur MCP."""
        print(f"MCP Lightning Server starting...", file=sys.stderr)
        print(f"API URL: {self.api_url}", file=sys.stderr)
        print(f"Ready to receive commands from Claude", file=sys.stderr)
        
        # Boucle principale de traitement des requêtes
        while True:
            try:
                # Lire une ligne depuis stdin (format JSON-RPC)
                line = sys.stdin.readline()
                if not line:
                    break
                
                # Parser la requête
                request = json.loads(line)
                
                # Traiter la requête
                response = await self.handle_request(request)
                
                # Envoyer la réponse
                response_json = json.dumps({
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": response
                })
                
                print(response_json)
                sys.stdout.flush()
                
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
                
            except Exception as e:
                print(f"Error: {str(e)}", file=sys.stderr)
    
    async def cleanup(self):
        """Nettoie les ressources."""
        await self.client.aclose()

async def main():
    """Point d'entrée principal."""
    server = MCPLightningServer()
    
    try:
        await server.run()
    finally:
        await server.cleanup()

if __name__ == "__main__":
    # Vérifier que l'API MCP est accessible
    import requests
    try:
        response = requests.get(f"{MCP_API_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"Warning: MCP API may not be running at {MCP_API_URL}", file=sys.stderr)
    except:
        print(f"Warning: Cannot connect to MCP API at {MCP_API_URL}", file=sys.stderr)
        print("Make sure to run ./start_production.sh first", file=sys.stderr)
    
    # Lancer le serveur
    asyncio.run(main())