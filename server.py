import asyncio
from dotenv import load_dotenv
import requests
import os
from rag import RAGWorkflow
from mcp.server.fastmcp import FastMCP
from typing import Optional, Dict, Any

load_dotenv()

mcp = FastMCP('sparkseer-server')
rag_workflow = RAGWorkflow()

def get_headers() -> Dict[str, str]:
    """Get headers with API key for Sparkseer API."""
    api_key = os.getenv('SPARKSEER_API_KEY')
    if not api_key:
        raise ValueError("SPARKSEER_API_KEY not found in environment variables")
    return {
        'api-key': api_key,
        'Content-Type': 'application/json'
    }

@mcp.tool()
def get_network_summary() -> str:
    """Get historical summary information about total capacity, nodes and channels."""
    try:
        response = requests.get(
            'https://api.sparkseer.space/v1/stats/ln-summary-ts',
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return f"Error getting network summary: {str(e)}"

@mcp.tool()
def get_centralities() -> str:
    """Get current centrality information for all publicly visible nodes."""
    try:
        response = requests.get(
            'https://api.sparkseer.space/v1/stats/centralities',
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return f"Error getting centralities: {str(e)}"

@mcp.tool()
def get_node_stats(pubkey: str) -> str:
    """Get current node statistics for a specific node."""
    try:
        response = requests.get(
            f'https://api.sparkseer.space/v1/node/current-stats/{pubkey}',
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return f"Error getting node stats: {str(e)}"

@mcp.tool()
def get_node_history(pubkey: str) -> str:
    """Get historical node statistics for a specific node."""
    try:
        response = requests.get(
            f'https://api.sparkseer.space/v1/node/historical/{pubkey}',
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return f"Error getting node history: {str(e)}"

@mcp.tool()
def get_channel_recommendations() -> str:
    """Get channel recommendations for your node."""
    try:
        response = requests.get(
            'https://api.sparkseer.space/v1/services/channel-recommendations',
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return f"Error getting channel recommendations: {str(e)}"

@mcp.tool()
def get_outbound_liquidity_value() -> str:
    """Get outbound liquidity value based on current channel fees."""
    try:
        response = requests.get(
            'https://api.sparkseer.space/v1/services/outbound-liquidity-value',
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return f"Error getting outbound liquidity value: {str(e)}"

@mcp.tool()
def get_suggested_fees() -> str:
    """Get suggested channel fees for existing channels."""
    try:
        response = requests.get(
            'https://api.sparkseer.space/v1/services/suggested-fees',
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return f"Error getting suggested fees: {str(e)}"

@mcp.tool()
def get_bid_info() -> str:
    """Get the latest bid maximum numbers for different account types."""
    try:
        response = requests.get(
            'https://api.sparkseer.space/v1/sats4stats/bidinfo'
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return f"Error getting bid info: {str(e)}"

@mcp.tool()
async def rag(query: str) -> str:
    """Use a simple RAG workflow to answer queries using documents from data directory about Deep Seek"""
    response = await rag_workflow.query(query)
    return str(response)

if __name__ == "__main__":
    asyncio.run(rag_workflow.ingest_documents("data"))
    mcp.run(transport="stdio") 