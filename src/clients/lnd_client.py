import httpx
import os
from typing import Dict, List, Any, Optional
import base64

class LNDClient:
    """
    Client asynchrone pour interagir avec l'API REST de LND.
    Gère l'authentification macaroon et TLS.
    """
    def __init__(self, host: str = None, port: int = None, macaroon_path: str = None, tls_cert_path: str = None):
        self.host = host or os.getenv("LND_REST_HOST", "https://127.0.0.1")
        self.port = port or int(os.getenv("LND_REST_PORT", 8080))
        self.base_url = f"{self.host}:{self.port}"
        self.macaroon_path = macaroon_path or os.getenv("LND_MACAROON_PATH", "~/.lnd/data/chain/bitcoin/mainnet/admin.macaroon")
        self.tls_cert_path = tls_cert_path or os.getenv("LND_TLS_CERT_PATH", "~/.lnd/tls.cert")
        self._macaroon = self._load_macaroon(self.macaroon_path)
        self._cert = os.path.expanduser(self.tls_cert_path)

    def _load_macaroon(self, path: str) -> str:
        """Charge le macaroon et le convertit en hexadécimal."""
        with open(os.path.expanduser(path), "rb") as f:
            macaroon_bytes = f.read()
        return macaroon_bytes.hex()

    def _headers(self) -> Dict[str, str]:
        return {"Grpc-Metadata-macaroon": self._macaroon}

    async def get_node_info(self, pubkey: str) -> Dict[str, Any]:
        """
        Récupère les infos d'un nœud (GET /v1/graph/node/{pub_key})
        """
        url = f"{self.base_url}/v1/graph/node/{pubkey}"
        async with httpx.AsyncClient(verify=self._cert) as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    async def get_channels(self) -> List[Dict[str, Any]]:
        """
        Récupère la liste des canaux ouverts (GET /v1/channels)
        """
        url = f"{self.base_url}/v1/channels"
        async with httpx.AsyncClient(verify=self._cert) as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
            return data.get("channels", [])

    async def get_node_metrics(self, pubkey: str) -> Dict[str, Any]:
        """
        Récupère des métriques globales du nœud (à adapter selon besoins).
        Peut combiner plusieurs endpoints (GET /v1/graph/node/{pub_key}, /v1/channels, etc.)
        """
        # Exemple minimal : nombre de canaux et total capacity
        node_info = await self.get_node_info(pubkey)
        channels = await self.get_channels()
        total_capacity = sum(int(c.get("capacity", 0)) for c in channels)
        return {
            "num_channels": len(channels),
            "total_capacity": total_capacity,
            "alias": node_info.get("node", {}).get("alias", "unknown")
        }

    async def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """
        Récupère les infos d'un canal (GET /v1/graph/edge/{channel_id})
        """
        url = f"{self.base_url}/v1/graph/edge/{channel_id}"
        async with httpx.AsyncClient(verify=self._cert) as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    async def get_channel_policy(self, channel_id: str) -> Dict[str, Any]:
        """
        Récupère la politique de frais d'un canal (extrait de get_channel_info)
        """
        info = await self.get_channel_info(channel_id)
        # LND retourne "node1_policy" et "node2_policy"; il faut choisir selon le sens
        # Ici, on retourne les deux pour adaptation future
        return {
            "node1_policy": info.get("node1_policy", {}),
            "node2_policy": info.get("node2_policy", {})
        }

    # Ajoute ici d'autres méthodes utiles selon les besoins du pipeline (ex: update_channel_policy) 