#!/usr/bin/env python3
"""
Test du serveur MCP pour vérifier la connexion.
"""

import json
import subprocess
import os

def test_mcp_server():
    """Test le serveur MCP avec un message d'initialisation."""
    
    # Configuration
    env = {
        **os.environ,
        "MCP_API_URL": "https://api.dazno.de",
        "MCP_API_KEY": "mcp_2f0d711f886ef6e2551397ba90b5152dfe6b23d4",
        "PYTHONPATH": "/Users/stephanecourant/Documents/DAZ/MCP/MCP"
    }
    
    # Lancer le serveur
    process = subprocess.Popen(
        ["python3", "/Users/stephanecourant/Documents/DAZ/MCP/MCP/mcp_server_remote.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    
    # Test 1: Initialisation
    print("Test 1: Initialisation...")
    init_message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {}
        }
    }
    
    process.stdin.write(json.dumps(init_message) + "\n")
    process.stdin.flush()
    
    response = process.stdout.readline()
    if response:
        result = json.loads(response)
        print("✅ Réponse d'initialisation:")
        print(json.dumps(result, indent=2))
    else:
        print("❌ Pas de réponse")
    
    # Test 2: Liste des outils
    print("\nTest 2: Liste des outils...")
    tools_message = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    process.stdin.write(json.dumps(tools_message) + "\n")
    process.stdin.flush()
    
    response = process.stdout.readline()
    if response:
        result = json.loads(response)
        print("✅ Outils disponibles:")
        if "result" in result and "tools" in result["result"]:
            for tool in result["result"]["tools"]:
                print(f"  - {tool['name']}: {tool['description']}")
    else:
        print("❌ Pas de réponse")
    
    # Test 3: Statut réseau
    print("\nTest 3: Statut du réseau...")
    status_message = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "get_network_status",
            "arguments": {}
        }
    }
    
    process.stdin.write(json.dumps(status_message) + "\n")
    process.stdin.flush()
    
    response = process.stdout.readline()
    if response:
        result = json.loads(response)
        print("✅ Statut réseau:")
        print(json.dumps(result, indent=2))
    else:
        print("❌ Pas de réponse")
    
    # Terminer le processus
    process.terminate()
    
    print("\n✅ Test terminé!")

if __name__ == "__main__":
    test_mcp_server()