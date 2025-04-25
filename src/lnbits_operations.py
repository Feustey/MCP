import requests
import json
from typing import Dict, List, Optional
import logging
from datetime import datetime

class LNbitsOperations:
    """Classe pour interagir avec l'API LNbits sur le testnet"""
    
    def __init__(self, api_url: str, admin_key: str, invoice_key: str):
        self.api_url = api_url.rstrip('/')
        self.admin_key = admin_key
        self.invoice_key = invoice_key
        self.headers = {
            "X-Api-Key": admin_key,
            "Content-type": "application/json"
        }
        
    async def create_wallet(self, name: str) -> Dict:
        """Crée un nouveau wallet LNbits"""
        url = f"{self.api_url}/wallet"
        data = {"name": name}
        
        response = requests.post(url, json=data, headers=self.headers)
        return response.json()
        
    async def get_wallet_info(self) -> Dict:
        """Récupère les informations du wallet"""
        url = f"{self.api_url}/wallet"
        response = requests.get(url, headers=self.headers)
        return response.json()
        
    async def create_invoice(self, amount: int, memo: str = "") -> Dict:
        """Crée une facture Lightning"""
        url = f"{self.api_url}/payments"
        data = {
            "out": False,
            "amount": amount,
            "memo": memo
        }
        
        response = requests.post(url, json=data, headers=self.headers)
        return response.json()
        
    async def pay_invoice(self, payment_request: str) -> Dict:
        """Paie une facture Lightning"""
        url = f"{self.api_url}/payments"
        data = {
            "out": True,
            "bolt11": payment_request
        }
        
        response = requests.post(url, json=data, headers=self.headers)
        return response.json()
        
    async def open_channel(self, node_id: str, amount: int, push_amount: int = 0) -> Dict:
        """Ouvre un nouveau canal Lightning"""
        url = f"{self.api_url}/channel"
        data = {
            "node_id": node_id,
            "local_amt": amount,
            "push_amt": push_amount
        }
        
        response = requests.post(url, json=data, headers=self.headers)
        return response.json()
        
    async def list_channels(self) -> List[Dict]:
        """Liste tous les canaux du nœud"""
        url = f"{self.api_url}/channel"
        response = requests.get(url, headers=self.headers)
        return response.json()
        
    async def close_channel(self, channel_id: str, force: bool = False) -> Dict:
        """Ferme un canal Lightning"""
        url = f"{self.api_url}/channel/{channel_id}"
        data = {"force": force}
        
        response = requests.delete(url, json=data, headers=self.headers)
        return response.json()
        
    async def update_channel_policy(self, channel_id: str, fee_rate: int, base_fee: int = 1000) -> Dict:
        """Met à jour la politique de frais d'un canal"""
        url = f"{self.api_url}/channel/{channel_id}/policy"
        data = {
            "fee_rate": fee_rate,
            "base_fee": base_fee
        }
        
        response = requests.put(url, json=data, headers=self.headers)
        return response.json()
        
    async def get_node_info(self) -> Dict:
        """Récupère les informations du nœud"""
        url = f"{self.api_url}/node"
        response = requests.get(url, headers=self.headers)
        return response.json()
        
    async def rebalance_channel(self, channel_id: str, amount: int, target_node: str) -> Dict:
        """Effectue un rebalancing de canal"""
        url = f"{self.api_url}/channel/{channel_id}/rebalance"
        data = {
            "amount": amount,
            "target_node": target_node
        }
        
        response = requests.post(url, json=data, headers=self.headers)
        return response.json() 