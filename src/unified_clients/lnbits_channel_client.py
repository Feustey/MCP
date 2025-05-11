"""
Client LNBits pour la gestion des canaux et des frais.

Ce client implémente les fonctionnalités liées à:
- Récupération des canaux (via LND)
- Mise à jour des politiques de frais des canaux
- Surveillance de l'état des canaux
"""

from typing import Dict, Any, Optional, List, Union
import logging
from pydantic import BaseModel

from src.unified_clients.lnbits_base_client import LNBitsBaseClient, LNBitsError, LNBitsErrorType
from src.unified_clients.lnbits_client import ChannelInfo

logger = logging.getLogger(__name__)

class ChannelPolicy(BaseModel):
    """Politique de frais pour un canal"""
    base_fee_msat: int = 1000  # Frais de base en millisatoshis
    fee_rate_ppm: int = 1000   # Taux de frais en parties par million
    time_lock_delta: int = 40  # Delta de timelock en blocs
    min_htlc_msat: Optional[int] = 1000  # Montant minimal d'un HTLC en millisatoshis
    max_htlc_msat: Optional[int] = None  # Montant maximal d'un HTLC en millisatoshis
    disabled: bool = False  # Indique si le canal est désactivé pour le routage

class LNBitsChannelClient(LNBitsBaseClient):
    """Client pour la gestion des canaux via LNBits"""
    
    async def list_channels(self, active_only: bool = False) -> List[ChannelInfo]:
        """Liste les canaux du nœud
        
        Args:
            active_only: Si True, renvoie uniquement les canaux actifs
            
        Returns:
            List[ChannelInfo]: Liste des canaux
        """
        try:
            result = await self._execute_with_retry(
                method="get",
                endpoint="api/v1/lnd/channels",
                use_admin_key=True
            )
            
            channels = []
            for chan in result:
                channel = ChannelInfo(
                    id=chan.get("id", ""),
                    short_id=chan.get("short_id"),
                    channel_point=chan.get("channel_point"),
                    remote_pubkey=chan.get("remote_pubkey", ""),
                    capacity=chan.get("capacity", 0),
                    local_balance=chan.get("local_balance", 0),
                    remote_balance=chan.get("remote_balance", 0),
                    active=chan.get("active", False),
                    status=chan.get("status", "unknown"),
                    fee_base_msat=chan.get("fee_base_msat"),
                    fee_rate_ppm=chan.get("fee_rate_ppm")
                )
                
                if not active_only or channel.active:
                    channels.append(channel)
            
            return channels
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des canaux: {str(e)}")
            raise LNBitsError(
                f"Échec de récupération des canaux: {str(e)}",
                error_type=LNBitsErrorType.REQUEST_ERROR
            )

    async def get_channel(self, channel_id: str) -> Optional[ChannelInfo]:
        """Récupère les informations d'un canal spécifique
        
        Args:
            channel_id: Identifiant du canal (channel_point ou short_id)
            
        Returns:
            Optional[ChannelInfo]: Informations du canal ou None si non trouvé
        """
        try:
            channels = await self.list_channels()
            
            # Recherche par id/channel_point
            for channel in channels:
                if channel.id == channel_id or channel.channel_point == channel_id or channel.short_id == channel_id:
                    return channel
            
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du canal {channel_id}: {str(e)}")
            raise LNBitsError(
                f"Échec de récupération du canal {channel_id}: {str(e)}",
                error_type=LNBitsErrorType.REQUEST_ERROR
            )

    async def get_forwarding_history(
        self, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Récupère l'historique des transactions transmises (forwarding)
        
        Args:
            start_date: Date de début au format YYYY-MM-DD
            end_date: Date de fin au format YYYY-MM-DD
            limit: Nombre maximum d'enregistrements à récupérer
            offset: Index à partir duquel commencer
            
        Returns:
            List[Dict[str, Any]]: Liste des transactions de forwarding
        """
        try:
            params = {"limit": limit, "offset": offset}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            
            result = await self._execute_with_retry(
                method="get",
                endpoint="api/v1/lnd/forwarding/history",
                use_admin_key=True,
                params=params
            )
            
            return result
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'historique de forwarding: {str(e)}")
            raise LNBitsError(
                f"Échec de récupération de l'historique de forwarding: {str(e)}",
                error_type=LNBitsErrorType.REQUEST_ERROR
            )

    async def update_channel_policy(
        self, 
        channel_point: str, 
        policy: ChannelPolicy,
        target_node: Optional[str] = None
    ) -> bool:
        """Met à jour la politique de frais d'un canal
        
        Args:
            channel_point: Point du canal au format txid:output_index
            policy: Nouvelle politique à appliquer
            target_node: Clé publique du nœud distant (optionnel)
            
        Returns:
            bool: True si la mise à jour est réussie, False sinon
        """
        try:
            # Construire les données de la requête
            data = {
                "channel_point": channel_point,
                "base_fee_msat": policy.base_fee_msat,
                "fee_rate_ppm": policy.fee_rate_ppm,
                "time_lock_delta": policy.time_lock_delta,
                "disabled": policy.disabled
            }
            
            if policy.min_htlc_msat:
                data["min_htlc_msat"] = policy.min_htlc_msat
                
            if policy.max_htlc_msat:
                data["max_htlc_msat"] = policy.max_htlc_msat
                
            if target_node:
                data["target_node"] = target_node
            
            result = await self._execute_with_retry(
                method="post",
                endpoint="api/v1/lnd/channel/policy",
                use_admin_key=True,
                json_data=data
            )
            
            success = result.get("success", False)
            if not success:
                logger.warning(f"Échec de la mise à jour de la politique: {result.get('message', 'Raison inconnue')}")
                
            return success
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la politique du canal: {str(e)}")
            raise LNBitsError(
                f"Échec de mise à jour de la politique du canal: {str(e)}",
                error_type=LNBitsErrorType.REQUEST_ERROR
            )

    async def get_channel_balances(self) -> Dict[str, Any]:
        """Récupère les soldes globaux des canaux
        
        Returns:
            Dict[str, Any]: Informations sur les soldes des canaux
        """
        try:
            result = await self._execute_with_retry(
                method="get",
                endpoint="api/v1/lnd/balance/channels",
                use_admin_key=True
            )
            
            return {
                "total_balance": result.get("total_balance", 0),
                "confirmed_balance": result.get("confirmed_balance", 0),
                "unconfirmed_balance": result.get("unconfirmed_balance", 0),
                "pending_open_balance": result.get("pending_open_balance", 0),
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des soldes des canaux: {str(e)}")
            raise LNBitsError(
                f"Échec de récupération des soldes des canaux: {str(e)}",
                error_type=LNBitsErrorType.REQUEST_ERROR
            )

    async def get_node_info(self, pubkey: str) -> Dict[str, Any]:
        """Récupère les informations sur un nœud du réseau
        
        Args:
            pubkey: Clé publique du nœud
            
        Returns:
            Dict[str, Any]: Informations sur le nœud
        """
        try:
            result = await self._execute_with_retry(
                method="get",
                endpoint=f"api/v1/lnd/node/{pubkey}",
                use_admin_key=True
            )
            
            return result
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des infos du nœud {pubkey}: {str(e)}")
            raise LNBitsError(
                f"Échec de récupération des infos du nœud: {str(e)}",
                error_type=LNBitsErrorType.REQUEST_ERROR
            )
            
    async def update_all_channel_fees(
        self, 
        base_fee_msat: int = 1000,
        fee_rate_ppm: int = 1000,
        exclude_channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """Met à jour les frais pour tous les canaux actifs
        
        Args:
            base_fee_msat: Frais de base en millisatoshis
            fee_rate_ppm: Taux de frais en parties par million
            exclude_channels: Liste des channel_points à exclure
            
        Returns:
            Dict[str, bool]: Résultats de mise à jour par canal (channel_point: success)
        """
        exclude_channels = exclude_channels or []
        results = {}
        
        try:
            # Récupérer tous les canaux actifs
            channels = await self.list_channels(active_only=True)
            
            policy = ChannelPolicy(
                base_fee_msat=base_fee_msat,
                fee_rate_ppm=fee_rate_ppm
            )
            
            # Mettre à jour chaque canal
            for channel in channels:
                if not channel.channel_point or channel.channel_point in exclude_channels:
                    continue
                
                try:
                    success = await self.update_channel_policy(
                        channel_point=channel.channel_point,
                        policy=policy
                    )
                    results[channel.channel_point] = success
                except Exception as e:
                    logger.error(f"Erreur lors de la mise à jour du canal {channel.channel_point}: {str(e)}")
                    results[channel.channel_point] = False
            
            return results
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour globale des frais: {str(e)}")
            raise LNBitsError(
                f"Échec de la mise à jour globale des frais: {str(e)}",
                error_type=LNBitsErrorType.REQUEST_ERROR
            ) 