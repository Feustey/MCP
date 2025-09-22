#!/usr/bin/env python3
"""
MCP Server pour connecter Claude Desktop au système MCP Lightning sur Hostinger.
"""

import asyncio
import json
import sys
import os
from typing import Any, Dict, List, Optional
import httpx
from datetime import datetime

# Configuration pour serveur distant Hostinger
MCP_API_URL = os.getenv("MCP_API_URL", "https://api.dazno.de")  # Votre domaine Hostinger
MCP_API_KEY = os.getenv("MCP_API_KEY", "mcp_2f0d711f886ef6e2551397ba90b5152dfe6b23d4")

class MCPLightningServer:
    """
    Serveur MCP qui expose les fonctionnalités Lightning à Claude.
    """
    
    def __init__(self):
        self.api_url = MCP_API_URL
        self.api_key = MCP_API_KEY
        self.client = httpx.AsyncClient(timeout=30)
        
    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Traite les appels d'outils MCP."""
        
        if name == "analyze_lightning_node":
            node_id = arguments.get("node_id")
            if not node_id:
                return {"error": "node_id is required"}
            return await self.analyze_node(node_id)
            
        elif name == "get_node_recommendations":
            node_id = arguments.get("node_id")
            if not node_id:
                return {"error": "node_id is required"}
            return await self.get_recommendations(node_id)
            
        elif name == "get_network_status":
            return await self.get_network_status()
            
        else:
            return {"error": f"Unknown tool: {name}"}
    
    async def analyze_node(self, node_id: str) -> Dict[str, Any]:
        """Analyse un nœud Lightning via l'API MCP distante."""
        try:
            response = await self.client.get(
                f"{self.api_url}/api/v1/lightning/nodes/{node_id}/enhanced-analysis",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"API returned {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {
                "error": f"Connection error: {str(e)}"
            }
    
    async def get_recommendations(self, node_id: str) -> Dict[str, Any]:
        """Obtient les recommandations pour un nœud."""
        try:
            response = await self.client.get(
                f"{self.api_url}/api/v1/lightning/nodes/{node_id}/recommendations",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"API returned {response.status_code}"
                }
                
        except Exception as e:
            return {
                "error": f"Connection error: {str(e)}"
            }
    
    async def get_network_status(self) -> Dict[str, Any]:
        """Obtient le statut du réseau Lightning."""
        try:
            response = await self.client.get(
                f"{self.api_url}/health",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            
            return {
                "api_status": "online" if response.status_code == 200 else "offline",
                "status_code": response.status_code,
                "timestamp": datetime.now().isoformat(),
                "api_url": self.api_url
            }
            
        except Exception as e:
            return {
                "api_status": "unreachable",
                "error": str(e),
                "api_url": self.api_url
            }
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Traite les messages entrants selon le protocole MCP."""
        
        # Protocole MCP standard
        method = message.get("method")
        params = message.get("params", {})
        msg_id = message.get("id")
        
        try:
            if method == "initialize":
                # Initialisation du serveur MCP
                return {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "mcp-lightning",
                        "version": "1.0.0"
                    }
                }
                
            elif method == "tools/list":
                # Liste des outils disponibles
                return {
                    "tools": [
                        {
                            "name": "analyze_lightning_node",
                            "description": "Analyse complète d'un nœud Lightning Network",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "node_id": {
                                        "type": "string",
                                        "description": "Public key du nœud Lightning"
                                    }
                                },
                                "required": ["node_id"]
                            }
                        },
                        {
                            "name": "get_node_recommendations",
                            "description": "Recommandations pour optimiser un nœud",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "node_id": {
                                        "type": "string",
                                        "description": "Public key du nœud Lightning"
                                    }
                                },
                                "required": ["node_id"]
                            }
                        },
                        {
                            "name": "get_network_status",
                            "description": "Statut du réseau MCP Lightning",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        }
                    ]
                }
                
            elif method == "tools/call":
                # Appel d'un outil
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                result = await self.handle_tool_call(tool_name, tool_args)
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
                
            else:
                return {
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
                
        except Exception as e:
            return {
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def run(self):
        """Lance le serveur MCP selon le protocole standard."""
        
        while True:
            try:
                # Lire une ligne depuis stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:
                    break
                
                # Parser le message JSON-RPC
                message = json.loads(line.strip())
                
                # Traiter le message
                result = await self.handle_message(message)
                
                # Construire la réponse JSON-RPC
                response = {
                    "jsonrpc": "2.0",
                    "id": message.get("id")
                }
                
                if "error" in result:
                    response["error"] = result["error"]
                else:
                    response["result"] = result
                
                # Envoyer la réponse
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                # Erreur de parsing JSON
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)
                
            except Exception as e:
                # Erreur interne
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)
    
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
    asyncio.run(main())