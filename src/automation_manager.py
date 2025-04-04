import logging
import subprocess
import json
import asyncio
import aiohttp
from typing import Dict, List, Optional, Union
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutomationManager:
    """Gestionnaire d'automatisations pour Lightning Network"""
    
    def __init__(self, lncli_path: str = "lncli", rebalance_lnd_path: str = "rebalance-lnd", 
                 lnbits_url: str = None, lnbits_api_key: str = None, use_lnbits: bool = False):
        """
        Initialise le gestionnaire d'automatisations
        
        Args:
            lncli_path: Chemin vers l'exécutable lncli
            rebalance_lnd_path: Chemin vers l'exécutable rebalance-lnd
            lnbits_url: URL de l'instance LNbits (ex: https://testnet.lnbits.com)
            lnbits_api_key: Clé API LNbits
            use_lnbits: Utiliser LNbits comme backend au lieu de lncli/rebalance-lnd
        """
        self.lncli_path = lncli_path
        self.rebalance_lnd_path = rebalance_lnd_path
        self.lnbits_url = lnbits_url
        self.lnbits_api_key = lnbits_api_key
        self.use_lnbits = use_lnbits
        self.automation_history = []
        
        if use_lnbits and (not lnbits_url or not lnbits_api_key):
            logger.warning("LNbits est activé mais l'URL ou la clé API n'est pas fournie")
    
    async def update_fee_rate(self, channel_id: str, base_fee: int, fee_rate: float) -> Dict:
        """
        Met à jour les frais d'un canal via lncli ou LNbits
        
        Args:
            channel_id: ID du canal
            base_fee: Frais de base en msats
            fee_rate: Taux de frais en ppm
            
        Returns:
            Dict contenant le résultat de l'opération
        """
        try:
            logger.info(f"Mise à jour des frais pour le canal {channel_id}: base_fee={base_fee}, fee_rate={fee_rate}")
            
            if self.use_lnbits:
                return await self._update_fee_rate_lnbits(channel_id, base_fee, fee_rate)
            else:
                return await self._update_fee_rate_lncli(channel_id, base_fee, fee_rate)
                
        except Exception as e:
            logger.error(f"Exception lors de la mise à jour des frais: {str(e)}")
            return {
                "success": False,
                "message": f"Exception lors de la mise à jour des frais: {str(e)}",
                "details": None
            }
    
    async def _update_fee_rate_lncli(self, channel_id: str, base_fee: int, fee_rate: float) -> Dict:
        """Mise à jour des frais via lncli"""
        # Construction de la commande lncli
        cmd = [
            self.lncli_path,
            "updatechannelpolicy",
            "--chan_point", channel_id,
            "--base_fee_msat", str(base_fee),
            "--fee_rate", str(fee_rate)
        ]
        
        # Exécution de la commande
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        # Enregistrement de l'automatisation
        self.automation_history.append({
            "type": "fee_update",
            "channel_id": channel_id,
            "base_fee": base_fee,
            "fee_rate": fee_rate,
            "timestamp": datetime.now().isoformat(),
            "success": process.returncode == 0,
            "backend": "lncli"
        })
        
        if process.returncode == 0:
            logger.info(f"Frais mis à jour avec succès pour le canal {channel_id}")
            return {
                "success": True,
                "message": f"Frais mis à jour avec succès pour le canal {channel_id}",
                "details": stdout.decode() if stdout else None
            }
        else:
            error_msg = stderr.decode() if stderr else "Erreur inconnue"
            logger.error(f"Erreur lors de la mise à jour des frais: {error_msg}")
            return {
                "success": False,
                "message": f"Erreur lors de la mise à jour des frais: {error_msg}",
                "details": None
            }
    
    async def _update_fee_rate_lnbits(self, channel_id: str, base_fee: int, fee_rate: float) -> Dict:
        """Mise à jour des frais via LNbits API"""
        try:
            # Conversion des frais pour LNbits (ppm en pourcentage)
            fee_rate_percent = fee_rate / 10000  # 1 ppm = 0.0001%
            
            # Préparation de la requête
            headers = {
                "X-Api-Key": self.lnbits_api_key,
                "Content-Type": "application/json"
            }
            
            # Endpoint pour mettre à jour les frais (à adapter selon l'API LNbits)
            url = f"{self.lnbits_url}/api/v1/channels/{channel_id}/fees"
            
            payload = {
                "base_fee_msat": base_fee,
                "fee_rate": fee_rate_percent
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    response_data = await response.json()
                    
                    # Enregistrement de l'automatisation
                    self.automation_history.append({
                        "type": "fee_update",
                        "channel_id": channel_id,
                        "base_fee": base_fee,
                        "fee_rate": fee_rate,
                        "timestamp": datetime.now().isoformat(),
                        "success": response.status == 200,
                        "backend": "lnbits"
                    })
                    
                    if response.status == 200:
                        logger.info(f"Frais mis à jour avec succès pour le canal {channel_id} via LNbits")
                        return {
                            "success": True,
                            "message": f"Frais mis à jour avec succès pour le canal {channel_id}",
                            "details": response_data
                        }
                    else:
                        error_msg = response_data.get("detail", "Erreur inconnue")
                        logger.error(f"Erreur lors de la mise à jour des frais via LNbits: {error_msg}")
                        return {
                            "success": False,
                            "message": f"Erreur lors de la mise à jour des frais via LNbits: {error_msg}",
                            "details": response_data
                        }
        except Exception as e:
            logger.error(f"Exception lors de la mise à jour des frais via LNbits: {str(e)}")
            return {
                "success": False,
                "message": f"Exception lors de la mise à jour des frais via LNbits: {str(e)}",
                "details": None
            }
    
    async def rebalance_channel(self, channel_id: str, amount: int, direction: str = "outgoing") -> Dict:
        """
        Rééquilibre un canal via rebalance-lnd ou LNbits
        
        Args:
            channel_id: ID du canal
            amount: Montant à rééquilibrer en sats
            direction: Direction du rééquilibrage ("outgoing" ou "incoming")
            
        Returns:
            Dict contenant le résultat de l'opération
        """
        try:
            logger.info(f"Rééquilibrage du canal {channel_id}: amount={amount}, direction={direction}")
            
            if self.use_lnbits:
                return await self._rebalance_channel_lnbits(channel_id, amount, direction)
            else:
                return await self._rebalance_channel_rebalance_lnd(channel_id, amount, direction)
                
        except Exception as e:
            logger.error(f"Exception lors du rééquilibrage: {str(e)}")
            return {
                "success": False,
                "message": f"Exception lors du rééquilibrage: {str(e)}",
                "details": None
            }
    
    async def _rebalance_channel_rebalance_lnd(self, channel_id: str, amount: int, direction: str = "outgoing") -> Dict:
        """Rééquilibrage via rebalance-lnd"""
        # Construction de la commande rebalance-lnd
        cmd = [
            self.rebalance_lnd_path,
            "--channel", channel_id,
            "--amount", str(amount),
            "--direction", direction
        ]
        
        # Exécution de la commande
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        # Enregistrement de l'automatisation
        self.automation_history.append({
            "type": "rebalance",
            "channel_id": channel_id,
            "amount": amount,
            "direction": direction,
            "timestamp": datetime.now().isoformat(),
            "success": process.returncode == 0,
            "backend": "rebalance-lnd"
        })
        
        if process.returncode == 0:
            logger.info(f"Rééquilibrage réussi pour le canal {channel_id}")
            return {
                "success": True,
                "message": f"Rééquilibrage réussi pour le canal {channel_id}",
                "details": stdout.decode() if stdout else None
            }
        else:
            error_msg = stderr.decode() if stderr else "Erreur inconnue"
            logger.error(f"Erreur lors du rééquilibrage: {error_msg}")
            return {
                "success": False,
                "message": f"Erreur lors du rééquilibrage: {error_msg}",
                "details": None
            }
    
    async def _rebalance_channel_lnbits(self, channel_id: str, amount: int, direction: str = "outgoing") -> Dict:
        """Rééquilibrage via LNbits API"""
        try:
            # Préparation de la requête
            headers = {
                "X-Api-Key": self.lnbits_api_key,
                "Content-Type": "application/json"
            }
            
            # Endpoint pour rééquilibrer un canal (à adapter selon l'API LNbits)
            url = f"{self.lnbits_url}/api/v1/channels/{channel_id}/rebalance"
            
            payload = {
                "amount": amount,
                "direction": direction
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    response_data = await response.json()
                    
                    # Enregistrement de l'automatisation
                    self.automation_history.append({
                        "type": "rebalance",
                        "channel_id": channel_id,
                        "amount": amount,
                        "direction": direction,
                        "timestamp": datetime.now().isoformat(),
                        "success": response.status == 200,
                        "backend": "lnbits"
                    })
                    
                    if response.status == 200:
                        logger.info(f"Rééquilibrage réussi pour le canal {channel_id} via LNbits")
                        return {
                            "success": True,
                            "message": f"Rééquilibrage réussi pour le canal {channel_id}",
                            "details": response_data
                        }
                    else:
                        error_msg = response_data.get("detail", "Erreur inconnue")
                        logger.error(f"Erreur lors du rééquilibrage via LNbits: {error_msg}")
                        return {
                            "success": False,
                            "message": f"Erreur lors du rééquilibrage via LNbits: {error_msg}",
                            "details": response_data
                        }
        except Exception as e:
            logger.error(f"Exception lors du rééquilibrage via LNbits: {str(e)}")
            return {
                "success": False,
                "message": f"Exception lors du rééquilibrage via LNbits: {str(e)}",
                "details": None
            }
    
    async def custom_rebalance_strategy(self, channel_id: str, target_ratio: float = 0.5) -> Dict:
        """
        Applique une stratégie de rééquilibrage personnalisée
        
        Args:
            channel_id: ID du canal
            target_ratio: Ratio cible pour la balance locale (0.0 à 1.0)
            
        Returns:
            Dict contenant le résultat de l'opération
        """
        try:
            logger.info(f"Application de la stratégie de rééquilibrage pour le canal {channel_id}")
            
            if self.use_lnbits:
                return await self._custom_rebalance_strategy_lnbits(channel_id, target_ratio)
            else:
                return await self._custom_rebalance_strategy_lncli(channel_id, target_ratio)
                
        except Exception as e:
            logger.error(f"Exception lors de l'application de la stratégie de rééquilibrage: {str(e)}")
            return {
                "success": False,
                "message": f"Exception lors de l'application de la stratégie de rééquilibrage: {str(e)}",
                "details": None
            }
    
    async def _custom_rebalance_strategy_lncli(self, channel_id: str, target_ratio: float = 0.5) -> Dict:
        """Stratégie de rééquilibrage personnalisée via lncli"""
        # Récupération des informations du canal
        cmd = [
            self.lncli_path,
            "getchaninfo",
            "--chan_id", channel_id
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Erreur inconnue"
            logger.error(f"Erreur lors de la récupération des informations du canal: {error_msg}")
            return {
                "success": False,
                "message": f"Erreur lors de la récupération des informations du canal: {error_msg}",
                "details": None
            }
        
        # Analyse des informations du canal
        channel_info = json.loads(stdout.decode())
        capacity = int(channel_info["capacity"])
        local_balance = int(channel_info["local_balance"])
        current_ratio = local_balance / capacity
        
        # Calcul du montant à rééquilibrer
        target_balance = int(capacity * target_ratio)
        amount = abs(local_balance - target_balance)
        direction = "outgoing" if local_balance > target_balance else "incoming"
        
        # Si le déséquilibre est faible, ne pas agir
        if amount < capacity * 0.05:  # 5% de la capacité
            logger.info(f"Déséquilibre faible pour le canal {channel_id}, aucune action nécessaire")
            return {
                "success": True,
                "message": f"Déséquilibre faible pour le canal {channel_id}, aucune action nécessaire",
                "details": {
                    "current_ratio": current_ratio,
                    "target_ratio": target_ratio,
                    "amount": amount
                }
            }
        
        # Exécution du rééquilibrage
        return await self.rebalance_channel(channel_id, amount, direction)
    
    async def _custom_rebalance_strategy_lnbits(self, channel_id: str, target_ratio: float = 0.5) -> Dict:
        """Stratégie de rééquilibrage personnalisée via LNbits API"""
        try:
            # Préparation de la requête
            headers = {
                "X-Api-Key": self.lnbits_api_key,
                "Content-Type": "application/json"
            }
            
            # Endpoint pour obtenir les informations du canal (à adapter selon l'API LNbits)
            url = f"{self.lnbits_url}/api/v1/channels/{channel_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        response_data = await response.json()
                        error_msg = response_data.get("detail", "Erreur inconnue")
                        logger.error(f"Erreur lors de la récupération des informations du canal via LNbits: {error_msg}")
                        return {
                            "success": False,
                            "message": f"Erreur lors de la récupération des informations du canal via LNbits: {error_msg}",
                            "details": response_data
                        }
                    
                    channel_info = await response.json()
                    capacity = int(channel_info["capacity"])
                    local_balance = int(channel_info["local_balance"])
                    current_ratio = local_balance / capacity
                    
                    # Calcul du montant à rééquilibrer
                    target_balance = int(capacity * target_ratio)
                    amount = abs(local_balance - target_balance)
                    direction = "outgoing" if local_balance > target_balance else "incoming"
                    
                    # Si le déséquilibre est faible, ne pas agir
                    if amount < capacity * 0.05:  # 5% de la capacité
                        logger.info(f"Déséquilibre faible pour le canal {channel_id}, aucune action nécessaire")
                        return {
                            "success": True,
                            "message": f"Déséquilibre faible pour le canal {channel_id}, aucune action nécessaire",
                            "details": {
                                "current_ratio": current_ratio,
                                "target_ratio": target_ratio,
                                "amount": amount
                            }
                        }
                    
                    # Exécution du rééquilibrage
                    return await self.rebalance_channel(channel_id, amount, direction)
        except Exception as e:
            logger.error(f"Exception lors de l'application de la stratégie de rééquilibrage via LNbits: {str(e)}")
            return {
                "success": False,
                "message": f"Exception lors de l'application de la stratégie de rééquilibrage via LNbits: {str(e)}",
                "details": None
            }
    
    def get_automation_history(self, limit: int = 10) -> List[Dict]:
        """
        Récupère l'historique des automatisations
        
        Args:
            limit: Nombre maximum d'entrées à retourner
            
        Returns:
            Liste des entrées d'historique
        """
        return sorted(
            self.automation_history,
            key=lambda x: x["timestamp"],
            reverse=True
        )[:limit] 