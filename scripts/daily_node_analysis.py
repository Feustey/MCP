#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour analyser quotidiennement le noeud feustey et stocker les données en BDD
Permet de suivre l'évolution des politiques de frais et autres métriques

Usage:
    python daily_node_analysis.py
"""

import os
import json
import asyncio
import logging
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
import httpx

# Ajouter le répertoire parent au chemin Python pour pouvoir importer les modules src
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Importer les modules nécessaires
from src.lnbits_client import LNBitsClient
from src.mongo_operations import MongoOperations
from src.models import NodeData, ChannelData

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

# Constantes et configuration
FEUSTEY_NODE_ID = os.environ.get("FEUSTEY_NODE_ID")
LNBITS_URL = os.environ.get("LNBITS_URL", "http://127.0.0.1:5000")
LNBITS_API_KEY = os.environ.get("LNBITS_API_KEY")
LND_MACAROON = os.environ.get("LND_MACAROON", "")
UMBREL_URL = os.environ.get("UMBREL_URL", "https://umbrel.local:8080")
MOCK_LNBITS = os.environ.get("MOCK_LNBITS", "false").lower() == "true"

class NodeAnalysis:
    """Classe pour analyser un noeud Lightning Network et stocker les données"""
    
    def __init__(self, node_id: str, lnbits_url: str, lnbits_api_key: str, umbrel_url: str = None, macaroon: str = None):
        """
        Initialise l'analyseur de noeud
        
        Args:
            node_id: ID du noeud à analyser
            lnbits_url: URL de l'instance LNbits
            lnbits_api_key: Clé API LNbits
            umbrel_url: URL du nœud Umbrel
            macaroon: Macaroon pour l'authentification avec LND
        """
        self.node_id = node_id
        self.lnbits_client = LNBitsClient(lnbits_url, lnbits_api_key)
        self.mongo_ops = MongoOperations()
        self.umbrel_url = umbrel_url
        self.macaroon = macaroon
        
    async def fetch_from_umbrel(self, endpoint: str) -> Dict:
        """Récupère des données depuis l'API LND Umbrel"""
        headers = {
            "Grpc-Metadata-macaroon": self.macaroon
        }
        
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                f"{self.umbrel_url}{endpoint}",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        
    async def get_node_info(self) -> Dict[str, Any]:
        """Récupère les informations du noeud"""
        try:
            logger.info(f"Récupération des informations pour le noeud {self.node_id}...")
            
            if MOCK_LNBITS:
                logger.info("Mode MOCK_LNBITS activé, utilisation de données simulées")
            
            # Récupérer les informations depuis l'API LND au lieu de LNbits
            if self.umbrel_url and self.macaroon:
                node_info = await self.fetch_from_umbrel("/v1/getinfo")
                
                # Récupérer des informations supplémentaires du wallet LNbits
                try:
                    wallet_info = await self.lnbits_client.get_wallet_info()
                except:
                    wallet_info = {"name": node_info.get("alias", "Feustey Node"), "balance": 0}
                
                # Créer une structure complète pour les données du noeud
                node_data = {
                    "node_id": node_info.get("identity_pubkey", self.node_id),
                    "alias": node_info.get("alias", wallet_info.get("name", "Feustey Node")),
                    "last_update": datetime.now(),
                    "balance": wallet_info.get("balance", 0),
                    "current_peers": [],  # Sera rempli avec get_channels
                }
                
                logger.info(f"Informations du noeud récupérées avec succès: {node_data['alias']}")
                return node_data
            else:
                # Fallback vers l'API LNbits originale
                node_info = await self.lnbits_client.get_local_node_info()
                wallet_info = await self.lnbits_client.get_wallet_info()
                
                # Créer une structure complète pour les données du noeud
                node_data = {
                    "node_id": self.node_id,
                    "alias": wallet_info.get("name", "Feustey Node"),
                    "last_update": datetime.now(),
                    "balance": wallet_info.get("balance", 0),
                    "current_peers": list(node_info.get("current_peers", [])),
                }
                
                logger.info(f"Informations du noeud récupérées avec succès: {node_data['alias']}")
                return node_data
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des informations du noeud: {str(e)}")
            raise
            
    async def get_channels(self) -> List[Dict[str, Any]]:
        """Récupère les informations des canaux du noeud"""
        try:
            logger.info(f"Récupération des canaux pour le noeud {self.node_id}...")
            
            # Récupérer les canaux via l'API LND au lieu de LNbits
            if self.umbrel_url and self.macaroon:
                channels_response = await self.fetch_from_umbrel("/v1/channels")
                
                channels = []
                if "channels" in channels_response and isinstance(channels_response["channels"], list):
                    for chan in channels_response["channels"]:
                        # Adapter les données du canal au format attendu
                        channel_data = {
                            "channel_id": chan.get("chan_id") or chan.get("channel_id"),
                            "capacity": int(chan.get("capacity", 0)),
                            "remote_pubkey": chan.get("remote_pubkey"),
                            "local_balance": int(chan.get("local_balance", 0)),
                            "remote_balance": int(chan.get("remote_balance", 0)),
                            "fee_policy": {
                                "base_fee_msat": int(chan.get("base_fee_msat", 0)),
                                "fee_rate": int(chan.get("fee_per_kw", 0))
                            },
                            "active": chan.get("active", False),
                            "total_satoshis_sent": int(chan.get("total_satoshis_sent", 0)),
                            "total_satoshis_received": int(chan.get("total_satoshis_received", 0)),
                            "last_update": datetime.now()
                        }
                        channels.append(channel_data)
                    
                logger.info(f"{len(channels)} canaux récupérés avec succès")
                return channels
            else:
                # Fallback vers l'API LNbits originale
                try:
                    # Récupérer les canaux via l'API LNbits
                    channels_response = await self.lnbits_client._request("GET", "/api/v1/channels")
                    
                    channels = []
                    if isinstance(channels_response, list):
                        for chan in channels_response:
                            # Adapter les données du canal au format attendu
                            channel_data = {
                                "channel_id": chan.get("chan_id") or chan.get("channel_id"),
                                "capacity": chan.get("capacity", 0),
                                "remote_pubkey": chan.get("remote_pubkey") or chan.get("peer_id"),
                                "local_balance": chan.get("local_balance", 0),
                                "remote_balance": chan.get("remote_balance", 0),
                                "fee_policy": {
                                    "base_fee_msat": chan.get("base_fee_msat", 0),
                                    "fee_rate": chan.get("fee_rate", 0)
                                },
                                "active": chan.get("active", False),
                                "total_satoshis_sent": chan.get("total_satoshis_sent", 0),
                                "total_satoshis_received": chan.get("total_satoshis_received", 0),
                                "last_update": datetime.now()
                            }
                            channels.append(channel_data)
                except Exception as e:
                    logger.warning(f"Erreur lors de la récupération des canaux via LNbits: {str(e)}")
                    channels = []
                
                logger.info(f"{len(channels)} canaux récupérés avec succès")
                return channels
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des canaux: {str(e)}")
            raise
            
    async def store_node_data(self, node_data: Dict[str, Any]) -> None:
        """Stocke les données du noeud en base de données"""
        try:
            logger.info(f"Stockage des données du noeud {self.node_id}...")
            
            # Connexion à MongoDB
            await self.mongo_ops.connect()
            
            # Créer un modèle NodeData pour la validation
            node_model = NodeData(
                node_id=node_data["node_id"],
                alias=node_data["alias"],
                capacity=float(node_data.get("balance", 0)),  # Utiliser le solde comme capacité
                channel_count=len(node_data.get("current_peers", [])),
                last_update=node_data["last_update"],
                reputation_score=1.0,  # Valeur par défaut
                metadata={
                    "current_peers": node_data.get("current_peers", []),
                    "balance": node_data.get("balance", 0)
                }
            )
            
            # Stocker les données du noeud
            await self.mongo_ops.save_node(node_model)
            logger.info(f"Données du noeud {self.node_id} stockées avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors du stockage des données du noeud: {str(e)}")
            raise
            
    async def store_channels_data(self, channels: List[Dict[str, Any]]) -> None:
        """Stocke les données des canaux en base de données"""
        try:
            logger.info(f"Stockage des données de {len(channels)} canaux...")
            
            # Connexion à MongoDB (si pas déjà connecté)
            await self.mongo_ops.ensure_connected()
            
            for channel in channels:
                # Créer un modèle ChannelData pour la validation
                channel_model = ChannelData(
                    channel_id=channel["channel_id"],
                    capacity=float(channel["capacity"]),
                    fee_rate={
                        "base_fee_msat": channel["fee_policy"]["base_fee_msat"],
                        "fee_rate_ppm": channel["fee_policy"]["fee_rate"]
                    },
                    balance={
                        "local": float(channel["local_balance"]),
                        "remote": float(channel["remote_balance"])
                    },
                    age=0,  # Non disponible, à calculer avec la date d'ouverture du canal
                    last_update=channel["last_update"],
                    metadata={
                        "remote_pubkey": channel["remote_pubkey"],
                        "active": channel["active"],
                        "total_satoshis_sent": channel["total_satoshis_sent"],
                        "total_satoshis_received": channel["total_satoshis_received"]
                    }
                )
                
                # Stocker les données du canal
                await self.mongo_ops.save_channel(channel_model)
                
            logger.info(f"Données des canaux stockées avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors du stockage des données des canaux: {str(e)}")
            raise
            
    async def run(self) -> None:
        """Exécute l'analyse complète du noeud"""
        try:
            logger.info(f"Démarrage de l'analyse du noeud {self.node_id}...")
            logger.info(f"Mode MOCK_LNBITS: {MOCK_LNBITS}")
            
            # 1. Récupérer les informations du noeud
            node_data = await self.get_node_info()
            
            # 2. Récupérer les canaux
            channels = await self.get_channels()
            
            # 3. Stocker les données du noeud
            await self.store_node_data(node_data)
            
            # 4. Stocker les données des canaux
            await self.store_channels_data(channels)
            
            # 5. Nettoyer les connexions
            await self.lnbits_client.close()
            await self.mongo_ops.disconnect()
            
            logger.info(f"Analyse du noeud {self.node_id} terminée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du noeud: {str(e)}")
            # Nettoyer les connexions même en cas d'erreur
            try:
                await self.lnbits_client.close()
                await self.mongo_ops.disconnect()
            except:
                pass
            raise

async def main():
    """Fonction principale"""
    try:
        # Vérifier que les variables d'environnement sont définies
        if not FEUSTEY_NODE_ID:
            logger.error("La variable d'environnement FEUSTEY_NODE_ID n'est pas définie.")
            return
        
        # Créer et exécuter l'analyse du noeud
        analyzer = NodeAnalysis(
            FEUSTEY_NODE_ID, 
            LNBITS_URL, 
            LNBITS_API_KEY,
            UMBREL_URL,
            LND_MACAROON
        )
        await analyzer.run()
        
    except Exception as e:
        logger.error(f"Erreur dans l'analyse quotidienne du noeud: {str(e)}")

if __name__ == "__main__":
    # Exécuter la fonction principale de manière asynchrone
    asyncio.run(main()) 