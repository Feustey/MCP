from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Dict, List, Optional, Any
from app.services.lnbits import LNbitsService
from app.auth import verify_jwt_and_get_tenant

router = APIRouter(prefix="/node", tags=["Node Management"])

@router.get("/{node_id}/priorities-enhanced")
async def get_node_priorities(
    node_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Récupère les priorités améliorées d'un nœud."""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    lnbits_service = LNbitsService()
    return await lnbits_service.get_node_priorities(node_id)

@router.get("/{node_id}/status/complete")
async def get_node_complete_status(
    node_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Récupère le statut complet d'un nœud."""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    lnbits_service = LNbitsService()
    return await lnbits_service.get_node_complete_status(node_id)

@router.get("/{node_id}/lnd/status")
async def get_node_lnd_status(
    node_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Récupère le statut LND d'un nœud."""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    lnbits_service = LNbitsService()
    return await lnbits_service.get_node_lnd_status(node_id)

@router.get("/{node_id}/info/amboss")
async def get_node_amboss_info(
    node_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Récupère les informations Amboss d'un nœud."""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    lnbits_service = LNbitsService()
    return await lnbits_service.get_node_amboss_info(node_id) 