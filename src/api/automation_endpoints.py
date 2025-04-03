from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from src.automation_manager import AutomationManager
import os

# Création du router
router = APIRouter(prefix="/automation", tags=["automation"])

# Modèles de données
class FeeUpdateRequest(BaseModel):
    channel_id: str = Field(..., description="ID du canal à mettre à jour")
    base_fee: int = Field(..., description="Frais de base en msats")
    fee_rate: float = Field(..., description="Taux de frais en ppm")

class RebalanceRequest(BaseModel):
    channel_id: str = Field(..., description="ID du canal à rééquilibrer")
    amount: int = Field(..., description="Montant à rééquilibrer en sats")
    direction: str = Field("outgoing", description="Direction du rééquilibrage (outgoing ou incoming)")

class CustomRebalanceRequest(BaseModel):
    channel_id: str = Field(..., description="ID du canal à rééquilibrer")
    target_ratio: float = Field(0.5, description="Ratio cible pour la balance locale (0.0 à 1.0)")

# Configuration de LNbits
LNBITS_URL = os.environ.get("LNBITS_URL", "https://testnet.lnbits.com")
LNBITS_API_KEY = os.environ.get("LNBITS_API_KEY", None)
USE_LNBITS = os.environ.get("USE_LNBITS", "false").lower() == "true"

# Instance du gestionnaire d'automatisations
automation_manager = AutomationManager(
    lncli_path=os.environ.get("LNCLI_PATH", "lncli"),
    rebalance_lnd_path=os.environ.get("REBALANCE_LND_PATH", "rebalance-lnd"),
    lnbits_url=LNBITS_URL,
    lnbits_api_key=LNBITS_API_KEY,
    use_lnbits=USE_LNBITS
)

@router.post("/fee-update", response_model=Dict)
async def update_fee_rate(request: FeeUpdateRequest):
    """
    Met à jour les frais d'un canal via lncli ou LNbits
    """
    result = await automation_manager.update_fee_rate(
        channel_id=request.channel_id,
        base_fee=request.base_fee,
        fee_rate=request.fee_rate
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.post("/rebalance", response_model=Dict)
async def rebalance_channel(request: RebalanceRequest):
    """
    Rééquilibre un canal via rebalance-lnd ou LNbits
    """
    result = await automation_manager.rebalance_channel(
        channel_id=request.channel_id,
        amount=request.amount,
        direction=request.direction
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.post("/custom-rebalance", response_model=Dict)
async def custom_rebalance(request: CustomRebalanceRequest):
    """
    Applique une stratégie de rééquilibrage personnalisée
    """
    result = await automation_manager.custom_rebalance_strategy(
        channel_id=request.channel_id,
        target_ratio=request.target_ratio
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.get("/history", response_model=List[Dict])
async def get_automation_history(limit: int = Query(10, description="Nombre maximum d'entrées à retourner")):
    """
    Récupère l'historique des automatisations
    """
    return automation_manager.get_automation_history(limit=limit)

@router.get("/config", response_model=Dict)
async def get_automation_config():
    """
    Récupère la configuration actuelle de l'automatisation
    """
    return {
        "backend": "lnbits" if USE_LNBITS else "lncli/rebalance-lnd",
        "lnbits_url": LNBITS_URL,
        "lnbits_api_key_configured": LNBITS_API_KEY is not None,
        "lncli_path": os.environ.get("LNCLI_PATH", "lncli"),
        "rebalance_lnd_path": os.environ.get("REBALANCE_LND_PATH", "rebalance-lnd")
    } 