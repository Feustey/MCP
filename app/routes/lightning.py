from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Dict, List, Optional, Any
from app.services.lnbits import LNbitsService
from app.auth import verify_jwt_and_get_tenant

router = APIRouter(prefix="/lightning", tags=["Lightning Network"])

@router.get("/explorer/nodes")
async def get_explorer_nodes(
    authorization: str = Header(..., alias="Authorization")
):
    """Récupère la liste des nœuds du réseau Lightning."""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    lnbits_service = LNbitsService()
    return await lnbits_service.get_network_nodes()

@router.get("/rankings")
async def get_rankings(
    authorization: str = Header(..., alias="Authorization")
):
    """Récupère les classements des nœuds Lightning."""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    lnbits_service = LNbitsService()
    return await lnbits_service.get_node_rankings()

@router.get("/network/global-stats")
async def get_global_stats(
    authorization: str = Header(..., alias="Authorization")
):
    """Récupère les statistiques globales du réseau Lightning."""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    lnbits_service = LNbitsService()
    return await lnbits_service.get_network_stats()

@router.get("/calculator")
async def get_calculator(
    authorization: str = Header(..., alias="Authorization")
):
    """Calculateur de frais Lightning."""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    lnbits_service = LNbitsService()
    return await lnbits_service.get_fee_calculator()

@router.get("/decoder")
async def get_decoder(
    authorization: str = Header(..., alias="Authorization")
):
    """Décodeur d'objets Lightning (factures, etc.)."""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    lnbits_service = LNbitsService()
    return await lnbits_service.get_decoder() 