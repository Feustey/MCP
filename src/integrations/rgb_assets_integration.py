"""
Intégration RGB++ Assets API pour la gestion des assets Bitcoin/RGB++

Ce module fournit l'intégration complète avec l'API RGB++ Assets pour :
- Gestion des transactions Bitcoin et RGB++
- Récupération des informations blockchain
- Gestion de la queue de transactions
- Automatisation via cron jobs
- Support des environnements testnet et mainnet

Dernière mise à jour: 23 août 2025
"""

import asyncio
import json
import logging
import hashlib
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import os
from urllib.parse import urljoin

# Configuration du logging
logger = logging.getLogger("rgb-assets-integration")

class RGBEnvironment(Enum):
    """Environnements RGB++ supportés"""
    MAINNET = "mainnet"
    TESTNET3 = "testnet3"
    SIGNET = "signet"

class TransactionStatus(Enum):
    """Statuts des transactions RGB++"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    QUEUED = "queued"
    PROCESSING = "processing"

@dataclass
class BitcoinTransaction:
    """Représentation d'une transaction Bitcoin"""
    txid: str
    block_height: Optional[int]
    confirmations: int
    fee: int
    size: int
    vsize: int
    inputs: List[Dict[str, Any]]
    outputs: List[Dict[str, Any]]
    timestamp: datetime
    status: TransactionStatus

@dataclass
class RGBPPTransaction:
    """Représentation d'une transaction RGB++"""
    txid: str
    ckb_txid: Optional[str]  # Nervos CKB transaction ID
    asset_id: str
    from_address: str
    to_address: str
    amount: int
    fee: int
    rgb_data: Dict[str, Any]
    bitcoin_tx: Optional[BitcoinTransaction]
    status: TransactionStatus
    created_at: datetime
    confirmed_at: Optional[datetime]

@dataclass
class RGBAssetInfo:
    """Informations détaillées sur un asset RGB++"""
    asset_id: str
    name: str
    symbol: str
    total_supply: int
    circulating_supply: int
    decimals: int
    issuer: str
    contract_address: str
    metadata: Dict[str, Any]
    created_at: datetime
    last_updated: datetime

@dataclass
class BlockchainInfo:
    """Informations sur la blockchain"""
    chain: str
    blocks: int
    best_block_hash: str
    difficulty: float
    verification_progress: float
    size_on_disk: int
    pruned: bool
    last_updated: datetime

class RGBAssetsAPIClient:
    """
    Client pour l'intégration avec l'API RGB++ Assets
    
    Fournit une interface complète pour :
    - Transactions Bitcoin et RGB++
    - Informations blockchain
    - Gestion des assets
    - Queue de transactions automatisée
    """
    
    def __init__(
        self,
        environment: RGBEnvironment = RGBEnvironment.TESTNET3,
        api_base_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialise le client RGB++ Assets API
        
        Args:
            environment: Environnement cible (mainnet, testnet3, signet)
            api_base_url: URL de base de l'API (optionnel)
            auth_token: Token d'authentification pour mainnet
            timeout: Timeout des requêtes HTTP
        """
        self.environment = environment
        self.api_base_url = api_base_url or self._get_default_api_url()
        self.auth_token = auth_token or os.getenv("RGBPP_AUTH_TOKEN")
        self.timeout = timeout
        
        # Session HTTP
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Cache local
        self._asset_cache: Dict[str, RGBAssetInfo] = {}
        self._blockchain_info_cache: Optional[BlockchainInfo] = None
        self._cache_expiry: Dict[str, datetime] = {}
        
        logger.info(f"RGB++ Assets API Client initialisé pour {environment.value}")
    
    def _get_default_api_url(self) -> str:
        """Retourne l'URL par défaut selon l'environnement"""
        urls = {
            RGBEnvironment.MAINNET: "https://api.rgbpp.io/v1",
            RGBEnvironment.TESTNET3: "https://testnet.rgbpp.io/v1", 
            RGBEnvironment.SIGNET: "https://signet.rgbpp.io/v1"
        }
        return urls.get(self.environment, urls[RGBEnvironment.TESTNET3])
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.disconnect()
    
    async def connect(self):
        """Établit la connexion HTTP"""
        try:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "MCP-RGB++-Client/1.0"
            }
            
            # Ajouter l'authentification pour mainnet
            if self.auth_token and self.environment == RGBEnvironment.MAINNET:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
            
            # Test de connectivité
            await self.health_check()
            
            logger.info("Connexion RGB++ Assets API établie")
            
        except Exception as e:
            logger.error(f"Erreur lors de la connexion: {e}")
            raise
    
    async def disconnect(self):
        """Ferme la connexion HTTP"""
        if self.session:
            await self.session.close()
            self.session = None
        logger.info("Connexion RGB++ Assets API fermée")
    
    async def health_check(self) -> Dict[str, Any]:
        """Vérifie l'état de santé de l'API"""
        try:
            if not self.session:
                raise RuntimeError("Client non connecté")
            
            url = urljoin(self.api_base_url, "health")
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy",
                        "environment": self.environment.value,
                        "api_version": data.get("version", "unknown"),
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status
                    )
                    
        except Exception as e:
            logger.error(f"Health check échoué: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    # Méthodes pour les transactions Bitcoin
    async def submit_bitcoin_transaction(
        self,
        raw_transaction: str,
        broadcast: bool = True
    ) -> Dict[str, Any]:
        """
        Soumet une transaction Bitcoin à l'API
        
        Args:
            raw_transaction: Transaction Bitcoin sérialisée (hex)
            broadcast: Si True, diffuse la transaction sur le réseau
            
        Returns:
            Résultat de la soumission
        """
        try:
            if not self.session:
                raise RuntimeError("Client non connecté")
            
            url = urljoin(self.api_base_url, "bitcoin/v1/transaction")
            
            payload = {
                "raw_transaction": raw_transaction,
                "broadcast": broadcast
            }
            
            async with self.session.post(url, json=payload) as response:
                data = await response.json()
                
                if response.status == 200:
                    logger.info(f"Transaction Bitcoin soumise: {data.get('txid')}")
                    return data
                else:
                    raise HTTPException(
                        status_code=response.status,
                        detail=data.get("error", "Erreur lors de la soumission")
                    )
                    
        except Exception as e:
            logger.error(f"Erreur lors de la soumission Bitcoin: {e}")
            raise
    
    async def get_bitcoin_transaction(self, txid: str) -> Optional[BitcoinTransaction]:
        """
        Récupère les détails d'une transaction Bitcoin
        
        Args:
            txid: ID de la transaction Bitcoin
            
        Returns:
            BitcoinTransaction ou None si non trouvée
        """
        try:
            if not self.session:
                raise RuntimeError("Client non connecté")
            
            url = urljoin(self.api_base_url, f"bitcoin/v1/transaction/{txid}")
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return BitcoinTransaction(
                        txid=data["txid"],
                        block_height=data.get("block_height"),
                        confirmations=data.get("confirmations", 0),
                        fee=data.get("fee", 0),
                        size=data.get("size", 0),
                        vsize=data.get("vsize", 0),
                        inputs=data.get("inputs", []),
                        outputs=data.get("outputs", []),
                        timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
                        status=TransactionStatus(data.get("status", "pending"))
                    )
                elif response.status == 404:
                    return None
                else:
                    data = await response.json()
                    raise HTTPException(
                        status_code=response.status,
                        detail=data.get("error", "Erreur lors de la récupération")
                    )
                    
        except Exception as e:
            logger.error(f"Erreur lors de la récupération Bitcoin tx {txid}: {e}")
            raise
    
    # Méthodes pour les transactions RGB++
    async def submit_rgbpp_transaction(
        self,
        ckb_transaction: str,
        bitcoin_txid: Optional[str] = None,
        asset_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Soumet une transaction RGB++
        
        Args:
            ckb_transaction: Transaction Nervos CKB (hex)
            bitcoin_txid: ID de la transaction Bitcoin associée
            asset_id: ID de l'asset RGB++ concerné
            
        Returns:
            Résultat de la soumission
        """
        try:
            if not self.session:
                raise RuntimeError("Client non connecté")
            
            url = urljoin(self.api_base_url, "rgbpp/v1/transaction/ckb-tx")
            
            payload = {
                "ckb_transaction": ckb_transaction,
                "bitcoin_txid": bitcoin_txid,
                "asset_id": asset_id
            }
            
            async with self.session.post(url, json=payload) as response:
                data = await response.json()
                
                if response.status == 200:
                    logger.info(f"Transaction RGB++ soumise: {data.get('txid')}")
                    return data
                else:
                    raise HTTPException(
                        status_code=response.status,
                        detail=data.get("error", "Erreur lors de la soumission RGB++")
                    )
                    
        except Exception as e:
            logger.error(f"Erreur lors de la soumission RGB++: {e}")
            raise
    
    async def get_rgbpp_transaction(self, txid: str) -> Optional[RGBPPTransaction]:
        """
        Récupère les détails d'une transaction RGB++
        
        Args:
            txid: ID de la transaction RGB++
            
        Returns:
            RGBPPTransaction ou None si non trouvée
        """
        try:
            if not self.session:
                raise RuntimeError("Client non connecté")
            
            url = urljoin(self.api_base_url, f"rgbpp/v1/transaction/{txid}")
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Récupérer la transaction Bitcoin associée si disponible
                    bitcoin_tx = None
                    if data.get("bitcoin_txid"):
                        bitcoin_tx = await self.get_bitcoin_transaction(data["bitcoin_txid"])
                    
                    return RGBPPTransaction(
                        txid=data["txid"],
                        ckb_txid=data.get("ckb_txid"),
                        asset_id=data["asset_id"],
                        from_address=data["from_address"],
                        to_address=data["to_address"],
                        amount=data["amount"],
                        fee=data.get("fee", 0),
                        rgb_data=data.get("rgb_data", {}),
                        bitcoin_tx=bitcoin_tx,
                        status=TransactionStatus(data.get("status", "pending")),
                        created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
                        confirmed_at=datetime.fromisoformat(data["confirmed_at"]) if data.get("confirmed_at") else None
                    )
                elif response.status == 404:
                    return None
                else:
                    data = await response.json()
                    raise HTTPException(
                        status_code=response.status,
                        detail=data.get("error", "Erreur lors de la récupération RGB++")
                    )
                    
        except Exception as e:
            logger.error(f"Erreur lors de la récupération RGB++ tx {txid}: {e}")
            raise
    
    # Méthodes pour les informations blockchain
    async def get_blockchain_info(self, use_cache: bool = True) -> BlockchainInfo:
        """
        Récupère les informations de la blockchain
        
        Args:
            use_cache: Utiliser le cache si disponible et valide
            
        Returns:
            BlockchainInfo: Informations de la blockchain
        """
        try:
            # Vérifier le cache
            if (use_cache and 
                self._blockchain_info_cache and 
                self._cache_expiry.get("blockchain_info", datetime.min) > datetime.now()):
                return self._blockchain_info_cache
            
            if not self.session:
                raise RuntimeError("Client non connecté")
            
            url = urljoin(self.api_base_url, "bitcoin/v1/blockchain/info")
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    blockchain_info = BlockchainInfo(
                        chain=data["chain"],
                        blocks=data["blocks"],
                        best_block_hash=data["bestblockhash"],
                        difficulty=data.get("difficulty", 0.0),
                        verification_progress=data.get("verificationprogress", 0.0),
                        size_on_disk=data.get("size_on_disk", 0),
                        pruned=data.get("pruned", False),
                        last_updated=datetime.now()
                    )
                    
                    # Mettre en cache pour 5 minutes
                    self._blockchain_info_cache = blockchain_info
                    self._cache_expiry["blockchain_info"] = datetime.now() + timedelta(minutes=5)
                    
                    return blockchain_info
                else:
                    data = await response.json()
                    raise HTTPException(
                        status_code=response.status,
                        detail=data.get("error", "Erreur lors de la récupération blockchain info")
                    )
                    
        except Exception as e:
            logger.error(f"Erreur lors de la récupération blockchain info: {e}")
            raise
    
    async def get_block_header(self, block_hash: str) -> Dict[str, Any]:
        """
        Récupère l'en-tête d'un bloc
        
        Args:
            block_hash: Hash du bloc
            
        Returns:
            En-tête du bloc
        """
        try:
            if not self.session:
                raise RuntimeError("Client non connecté")
            
            url = urljoin(self.api_base_url, f"bitcoin/v1/block/header/{block_hash}")
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    data = await response.json()
                    raise HTTPException(
                        status_code=response.status,
                        detail=data.get("error", "Erreur lors de la récupération block header")
                    )
                    
        except Exception as e:
            logger.error(f"Erreur lors de la récupération block header {block_hash}: {e}")
            raise
    
    # Méthodes pour les assets RGB++
    async def get_rgbpp_asset(self, asset_id: str, use_cache: bool = True) -> Optional[RGBAssetInfo]:
        """
        Récupère les informations d'un asset RGB++
        
        Args:
            asset_id: ID de l'asset RGB++
            use_cache: Utiliser le cache si disponible
            
        Returns:
            RGBAssetInfo ou None si non trouvé
        """
        try:
            # Vérifier le cache
            if (use_cache and 
                asset_id in self._asset_cache and
                self._cache_expiry.get(f"asset_{asset_id}", datetime.min) > datetime.now()):
                return self._asset_cache[asset_id]
            
            if not self.session:
                raise RuntimeError("Client non connecté")
            
            url = urljoin(self.api_base_url, f"rgbpp/v1/assets/{asset_id}")
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    asset_info = RGBAssetInfo(
                        asset_id=data["asset_id"],
                        name=data["name"],
                        symbol=data["symbol"],
                        total_supply=data["total_supply"],
                        circulating_supply=data.get("circulating_supply", 0),
                        decimals=data.get("decimals", 8),
                        issuer=data["issuer"],
                        contract_address=data.get("contract_address", ""),
                        metadata=data.get("metadata", {}),
                        created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
                        last_updated=datetime.now()
                    )
                    
                    # Mettre en cache pour 10 minutes
                    self._asset_cache[asset_id] = asset_info
                    self._cache_expiry[f"asset_{asset_id}"] = datetime.now() + timedelta(minutes=10)
                    
                    return asset_info
                elif response.status == 404:
                    return None
                else:
                    data = await response.json()
                    raise HTTPException(
                        status_code=response.status,
                        detail=data.get("error", "Erreur lors de la récupération asset")
                    )
                    
        except Exception as e:
            logger.error(f"Erreur lors de la récupération asset {asset_id}: {e}")
            raise
    
    async def list_rgbpp_assets(
        self, 
        limit: int = 50, 
        offset: int = 0,
        asset_type: Optional[str] = None
    ) -> List[RGBAssetInfo]:
        """
        Liste tous les assets RGB++ disponibles
        
        Args:
            limit: Nombre maximum d'assets
            offset: Décalage pour pagination
            asset_type: Filtrer par type d'asset
            
        Returns:
            Liste des assets RGB++
        """
        try:
            if not self.session:
                raise RuntimeError("Client non connecté")
            
            url = urljoin(self.api_base_url, "rgbpp/v1/assets")
            params = {
                "limit": limit,
                "offset": offset
            }
            if asset_type:
                params["type"] = asset_type
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    assets = []
                    for asset_data in data.get("assets", []):
                        asset_info = RGBAssetInfo(
                            asset_id=asset_data["asset_id"],
                            name=asset_data["name"],
                            symbol=asset_data["symbol"],
                            total_supply=asset_data["total_supply"],
                            circulating_supply=asset_data.get("circulating_supply", 0),
                            decimals=asset_data.get("decimals", 8),
                            issuer=asset_data["issuer"],
                            contract_address=asset_data.get("contract_address", ""),
                            metadata=asset_data.get("metadata", {}),
                            created_at=datetime.fromisoformat(asset_data.get("created_at", datetime.now().isoformat())),
                            last_updated=datetime.now()
                        )
                        assets.append(asset_info)
                        
                        # Mettre en cache
                        self._asset_cache[asset_info.asset_id] = asset_info
                        self._cache_expiry[f"asset_{asset_info.asset_id}"] = datetime.now() + timedelta(minutes=10)
                    
                    return assets
                else:
                    data = await response.json()
                    raise HTTPException(
                        status_code=response.status,
                        detail=data.get("error", "Erreur lors de la liste des assets")
                    )
                    
        except Exception as e:
            logger.error(f"Erreur lors de la liste des assets: {e}")
            raise
    
    # Méthodes pour la queue de transactions
    async def get_transaction_queue_status(self) -> Dict[str, Any]:
        """
        Récupère le statut de la queue de transactions
        
        Returns:
            Statut de la queue
        """
        try:
            if not self.session:
                raise RuntimeError("Client non connecté")
            
            url = urljoin(self.api_base_url, "queue/status")
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "queue_size": data.get("queue_size", 0),
                        "processing": data.get("processing", 0),
                        "completed_24h": data.get("completed_24h", 0),
                        "failed_24h": data.get("failed_24h", 0),
                        "avg_processing_time": data.get("avg_processing_time", 0),
                        "last_updated": datetime.now().isoformat()
                    }
                else:
                    data = await response.json()
                    raise HTTPException(
                        status_code=response.status,
                        detail=data.get("error", "Erreur lors du statut de la queue")
                    )
                    
        except Exception as e:
            logger.error(f"Erreur lors du statut de la queue: {e}")
            raise
    
    async def trigger_queue_processing(self) -> Dict[str, Any]:
        """
        Déclenche manuellement le traitement de la queue
        
        Returns:
            Résultat du déclenchement
        """
        try:
            if not self.session:
                raise RuntimeError("Client non connecté")
            
            url = urljoin(self.api_base_url, "queue/process")
            
            async with self.session.post(url) as response:
                data = await response.json()
                
                if response.status == 200:
                    logger.info("Traitement de la queue déclenché")
                    return {
                        "status": "triggered",
                        "message": data.get("message", "Traitement démarré"),
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    raise HTTPException(
                        status_code=response.status,
                        detail=data.get("error", "Erreur lors du déclenchement")
                    )
                    
        except Exception as e:
            logger.error(f"Erreur lors du déclenchement de la queue: {e}")
            raise
    
    # Méthodes utilitaires
    def clear_cache(self):
        """Vide tous les caches"""
        self._asset_cache.clear()
        self._blockchain_info_cache = None
        self._cache_expiry.clear()
        logger.info("Cache RGB++ Assets vidé")
    
    async def get_api_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques de l'API"""
        try:
            if not self.session:
                raise RuntimeError("Client non connecté")
            
            url = urljoin(self.api_base_url, "stats")
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    # Retourner des stats par défaut en cas d'erreur
                    return {
                        "total_transactions": 0,
                        "total_assets": len(self._asset_cache),
                        "queue_size": 0,
                        "api_version": "1.0.0",
                        "environment": self.environment.value,
                        "last_updated": datetime.now().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"Erreur lors des stats API: {e}")
            raise


# Factory function pour créer le client
async def create_rgb_assets_client(
    environment: RGBEnvironment = RGBEnvironment.TESTNET3,
    **kwargs
) -> RGBAssetsAPIClient:
    """
    Crée et connecte un client RGB++ Assets API
    
    Args:
        environment: Environnement cible
        **kwargs: Arguments supplémentaires pour RGBAssetsAPIClient
        
    Returns:
        Client RGB++ Assets connecté
    """
    client = RGBAssetsAPIClient(environment=environment, **kwargs)
    await client.connect()
    return client


# Exception personnalisée
class HTTPException(Exception):
    """Exception HTTP personnalisée"""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")