"""
Utilitaires pour l'ajustement des frais sur les canaux Lightning

Ce module fournit des fonctions pour calculer et appliquer des modifications
de frais optimales basées sur les performances des canaux.

Dernière mise à jour: 9 mai 2025
"""

import logging
from typing import Dict, Any, List, Tuple, Optional

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fee_update_utils")

class FeeUpdateError(Exception):
    """Exception levée lors d'une erreur de mise à jour des frais"""
    pass

async def update_channel_fees(
    client, 
    channel_id: str, 
    new_base_fee: int, 
    new_fee_rate: int,
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Met à jour les frais d'un canal Lightning
    
    Args:
        client: Client LND ou autre client compatible
        channel_id: Identifiant du canal à mettre à jour
        new_base_fee: Nouveau frais de base (en satoshis)
        new_fee_rate: Nouveau taux de frais (en ppm)
        dry_run: Si True, simule la mise à jour sans l'appliquer
        
    Returns:
        Résultat de la mise à jour des frais
        
    Raises:
        FeeUpdateError: Si la mise à jour échoue
    """
    try:
        logger.info(f"Mise à jour des frais pour le canal {channel_id[:8]}...")
        
        # Version simulée pour le test de charge
        if dry_run:
            logger.info(f"[DRY RUN] Simulation de mise à jour des frais pour {channel_id[:8]}...")
            return {
                "channel_id": channel_id,
                "success": True,
                "dry_run": True,
                "old_base_fee": 1000,
                "old_fee_rate": 500,
                "new_base_fee": new_base_fee,
                "new_fee_rate": new_fee_rate
            }
        
        # Version simulée d'une mise à jour réelle
        logger.info(f"Mise à jour des frais pour {channel_id[:8]}: {new_base_fee} sats, {new_fee_rate} ppm")
        return {
            "channel_id": channel_id,
            "success": True,
            "dry_run": False,
            "old_base_fee": 1000,
            "old_fee_rate": 500,
            "new_base_fee": new_base_fee,
            "new_fee_rate": new_fee_rate
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des frais pour {channel_id}: {str(e)}")
        raise FeeUpdateError(f"Erreur lors de la mise à jour des frais: {str(e)}")

async def batch_update_fees(
    client,
    updates: List[Dict[str, Any]],
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Applique des mises à jour de frais en lot sur plusieurs canaux
    
    Args:
        client: Client LND ou autre client compatible
        updates: Liste de mises à jour à appliquer
        dry_run: Si True, simule les mises à jour sans les appliquer
        
    Returns:
        Résultats des mises à jour
    """
    results = {
        "success": [],
        "failed": [],
        "total": len(updates),
        "success_count": 0,
        "failure_count": 0
    }
    
    for update in updates:
        try:
            channel_id = update.get("channel_id")
            new_base_fee = update.get("new_base_fee")
            new_fee_rate = update.get("new_fee_rate")
            
            if not channel_id or new_base_fee is None or new_fee_rate is None:
                logger.warning(f"Données de mise à jour incomplètes: {update}")
                results["failed"].append({
                    "update": update,
                    "error": "Données incomplètes"
                })
                results["failure_count"] += 1
                continue
                
            # Appliquer la mise à jour
            result = await update_channel_fees(
                client, channel_id, new_base_fee, new_fee_rate, dry_run
            )
            
            # Ajouter aux résultats
            results["success"].append(result)
            results["success_count"] += 1
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du canal {update.get('channel_id', 'inconnu')}: {str(e)}")
            results["failed"].append({
                "update": update,
                "error": str(e)
            })
            results["failure_count"] += 1
    
    return results

def get_fee_adjustment(
    current_base_fee: int,
    current_fee_rate: int,
    forward_success_rate: float,
    channel_activity: int,
    max_increase_pct: int = 30,
    max_decrease_pct: int = 20
) -> Tuple[int, int]:
    """
    Calcule l'ajustement optimal des frais en fonction des performances du canal
    
    Args:
        current_base_fee: Frais de base actuel (sats)
        current_fee_rate: Taux de frais actuel (ppm)
        forward_success_rate: Taux de succès des forwards (0-1)
        channel_activity: Activité du canal (nombre de forwards)
        max_increase_pct: Pourcentage maximum d'augmentation par ajustement
        max_decrease_pct: Pourcentage maximum de diminution par ajustement
    
    Returns:
        Tuple (nouveau frais de base, nouveau taux de frais)
    """
    # Ajustement en fonction du taux de succès
    if forward_success_rate < 0.5:
        # Taux de succès faible = augmenter les frais
        base_adjustment = 1 + (max_increase_pct / 100)
        rate_adjustment = 1 + (max_increase_pct / 100)
    elif forward_success_rate > 0.95 and channel_activity < 50:
        # Taux de succès élevé mais activité faible = baisser les frais
        base_adjustment = 1 - (max_decrease_pct / 100)
        rate_adjustment = 1 - (max_decrease_pct / 100)
    elif forward_success_rate > 0.9 and channel_activity > 100:
        # Canal performant et actif = augmenter légèrement les frais
        base_adjustment = 1 + (max_increase_pct / 200)  # Augmentation plus faible
        rate_adjustment = 1 + (max_increase_pct / 200)
    else:
        # Cas par défaut = ajustement léger
        success_factor = 0.5 - (forward_success_rate - 0.75)  # Négatif si >0.75, positif si <0.75
        base_adjustment = 1 + (success_factor * (max_increase_pct / 100))
        rate_adjustment = 1 + (success_factor * (max_increase_pct / 100))
    
    # Calculer les nouvelles valeurs
    new_base_fee = max(1, int(current_base_fee * base_adjustment))
    new_fee_rate = max(1, int(current_fee_rate * rate_adjustment))
    
    return new_base_fee, new_fee_rate 