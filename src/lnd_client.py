import os
import base64
import requests
from typing import List, Dict, Any
import json

class LNDClient:
    def __init__(self, macaroon_path: str, tls_cert_path: str, lnd_host: str):
        # Read the macaroon file
        with open(macaroon_path, 'rb') as f:
            macaroon_bytes = f.read()
            self.macaroon = base64.b64encode(macaroon_bytes).decode()
        
        # Read the tls cert
        self.cert_path = tls_cert_path
        
        # Set up the base URL
        self.base_url = f"https://{lnd_host}/v1"
        
        # Set up headers
        self.headers = {
            'Grpc-Metadata-macaroon': self.macaroon,
            'Content-Type': 'application/json'
        }
    
    async def get_node_info(self, pub_key: str) -> Dict[str, Any]:
        """Get information about a node"""
        url = f"{self.base_url}/graph/node/{pub_key}"
        response = requests.get(
            url,
            headers=self.headers,
            verify=self.cert_path
        )
        response.raise_for_status()
        return response.json()
    
    async def list_channels(self) -> List[Dict[str, Any]]:
        """List all channels"""
        url = f"{self.base_url}/channels"
        response = requests.get(
            url,
            headers=self.headers,
            verify=self.cert_path
        )
        response.raise_for_status()
        return response.json().get('channels', [])
    
    async def get_channel_info(self, chan_id: str) -> Dict[str, Any]:
        """Get information about a specific channel"""
        url = f"{self.base_url}/graph/edge/{chan_id}"
        response = requests.get(
            url,
            headers=self.headers,
            verify=self.cert_path
        )
        response.raise_for_status()
        return response.json()
    
    async def get_network_info(self) -> Dict[str, Any]:
        """Get information about the Lightning Network"""
        url = f"{self.base_url}/graph/info"
        response = requests.get(
            url,
            headers=self.headers,
            verify=self.cert_path
        )
        response.raise_for_status()
        return response.json()
    
    async def get_node_channels(self, pub_key: str) -> List[Dict[str, Any]]:
        """Get all channels for a specific node"""
        url = f"{self.base_url}/graph/node/channels/{pub_key}"
        response = requests.get(
            url,
            headers=self.headers,
            verify=self.cert_path
        )
        response.raise_for_status()
        return response.json().get('channels', []) 